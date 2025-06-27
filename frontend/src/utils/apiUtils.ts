import { notification } from 'antd';
import { buildApiUrl } from '../config/api';

// API响应接口
interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  success: boolean;
  message?: string;
}

// 请求选项接口
interface RequestOptions extends RequestInit {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  showErrorNotification?: boolean;
  enableCache?: boolean;
  cacheKey?: string;
  cacheDuration?: number; // 缓存持续时间（秒）
}

// 请求缓存
class RequestCache {
  private cache = new Map<string, { data: any; expires: number }>();
  
  set(key: string, data: any, duration: number = 300): void {
    const expires = Date.now() + duration * 1000;
    this.cache.set(key, { data, expires });
  }
  
  get(key: string): any | null {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }
  
  clear(): void {
    this.cache.clear();
  }
  
  delete(key: string): void {
    this.cache.delete(key);
  }
}

const requestCache = new RequestCache();

// 延迟函数
const delay = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

// 带超时的fetch
const fetchWithTimeout = async (
  url: string, 
  options: RequestInit & { timeout?: number }
): Promise<Response> => {
  const { timeout = 10000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`请求超时 (${timeout}ms)`);
    }
    throw error;
  }
};

// 统一的API请求函数
export const apiRequest = async <T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> => {
  const {
    timeout = 10000,
    retries = 3,
    retryDelay = 1000,
    showErrorNotification = true,
    enableCache = false,
    cacheKey,
    cacheDuration = 300,
    ...fetchOptions
  } = options;

  const url = buildApiUrl(endpoint);
  const finalCacheKey = cacheKey || `${options.method || 'GET'}:${endpoint}`;

  // 检查缓存（仅对GET请求且启用缓存时）
  if (enableCache && (!options.method || options.method === 'GET')) {
    const cachedData = requestCache.get(finalCacheKey);
    if (cachedData) {
      console.log(`使用缓存数据: ${finalCacheKey}`);
      return { success: true, data: cachedData };
    }
  }

  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      console.log(`API请求: ${url} (尝试 ${attempt + 1}/${retries})`);
      
      const response = await fetchWithTimeout(url, {
        timeout,
        headers: {
          'Content-Type': 'application/json',
          ...fetchOptions.headers,
        },
        ...fetchOptions,
      });

      // 处理HTTP错误状态
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        // 尝试解析错误响应
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (parseError) {
          console.warn('无法解析错误响应:', parseError);
        }
        
        // 对于404错误，提供更友好的提示
        if (response.status === 404) {
          errorMessage = '请求的功能暂未实现或端点不存在';
        }
        
        throw new Error(errorMessage);
      }

      // 解析响应数据
      let data: T;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text() as any;
      }

      // 缓存成功的GET请求结果
      if (enableCache && (!options.method || options.method === 'GET')) {
        requestCache.set(finalCacheKey, data, cacheDuration);
        console.log(`缓存数据: ${finalCacheKey} (${cacheDuration}s)`);
      }

      return { success: true, data };

    } catch (error) {
      lastError = error as Error;
      console.error(`API请求失败 (尝试 ${attempt + 1}):`, error);
      
      // 如果不是最后一次尝试，等待后重试
      if (attempt < retries - 1) {
        console.log(`等待 ${retryDelay}ms 后重试...`);
        await delay(retryDelay * (attempt + 1)); // 指数退避
      }
    }
  }

  // 所有重试都失败了
  const errorMessage = lastError?.message || '网络请求失败';
  
  if (showErrorNotification) {
    notification.error({
      message: 'API请求失败',
      description: errorMessage,
      duration: 5,
    });
  }

  return {
    success: false,
    error: errorMessage,
    message: errorMessage
  };
};

// 便捷的HTTP方法
export const apiGet = <T = any>(
  endpoint: string,
  options: Omit<RequestOptions, 'method'> = {}
): Promise<ApiResponse<T>> => {
  return apiRequest<T>(endpoint, { ...options, method: 'GET', enableCache: true });
};

export const apiPost = <T = any>(
  endpoint: string,
  data?: any,
  options: Omit<RequestOptions, 'method' | 'body'> = {}
): Promise<ApiResponse<T>> => {
  return apiRequest<T>(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
};

export const apiPut = <T = any>(
  endpoint: string,
  data?: any,
  options: Omit<RequestOptions, 'method' | 'body'> = {}
): Promise<ApiResponse<T>> => {
  return apiRequest<T>(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
};

export const apiDelete = <T = any>(
  endpoint: string,
  options: Omit<RequestOptions, 'method'> = {}
): Promise<ApiResponse<T>> => {
  return apiRequest<T>(endpoint, { ...options, method: 'DELETE' });
};

// 批量请求函数
export const apiBatch = async <T = any>(
  requests: Array<{ endpoint: string; options?: RequestOptions }>,
  concurrency: number = 3
): Promise<Array<ApiResponse<T>>> => {
  const results: Array<ApiResponse<T>> = [];
  
  for (let i = 0; i < requests.length; i += concurrency) {
    const batch = requests.slice(i, i + concurrency);
    const batchPromises = batch.map(({ endpoint, options }) =>
      apiRequest<T>(endpoint, options)
    );
    
    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults);
  }
  
  return results;
};

// 清除所有缓存
export const clearApiCache = (): void => {
  requestCache.clear();
  console.log('API缓存已清除');
};

// 清除特定缓存
export const clearSpecificCache = (key: string): void => {
  requestCache.delete(key);
  console.log(`缓存已清除: ${key}`);
};

// 预加载关键数据
export const preloadCriticalData = async (): Promise<void> => {
  console.log('开始预加载关键数据...');
  
  const criticalEndpoints = [
    '/api/v1/system/info',
    '/api/v1/downloads/platforms',
    '/api/v1/downloads/quality-options',
    '/api/v1/subtitles/info/languages'
  ];
  
  const preloadPromises = criticalEndpoints.map(endpoint =>
    apiGet(endpoint, { 
      enableCache: true, 
      cacheDuration: 600, // 10分钟缓存
      showErrorNotification: false 
    })
  );
  
  try {
    await Promise.allSettled(preloadPromises);
    console.log('关键数据预加载完成');
  } catch (error) {
    console.warn('预加载过程中出现错误:', error);
  }
};

// 网络状态监控
export const setupNetworkMonitoring = (): void => {
  // 监听网络状态变化
  window.addEventListener('online', () => {
    notification.success({
      message: '网络已连接',
      description: '网络连接已恢复，可以正常使用功能',
      duration: 3,
    });
    
    // 网络恢复后预加载关键数据
    preloadCriticalData();
  });
  
  window.addEventListener('offline', () => {
    notification.warning({
      message: '网络已断开',
      description: '网络连接已断开，部分功能可能无法使用',
      duration: 0, // 不自动关闭
    });
  });
  
  // 初始检查网络状态
  if (!navigator.onLine) {
    notification.warning({
      message: '网络未连接',
      description: '检测到网络未连接，请检查网络设置',
      duration: 0,
    });
  }
};

export default {
  apiRequest,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiBatch,
  clearApiCache,
  clearSpecificCache,
  preloadCriticalData,
  setupNetworkMonitoring
}; 