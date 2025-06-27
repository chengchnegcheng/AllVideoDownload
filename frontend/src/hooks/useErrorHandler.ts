import { useCallback } from 'react';
import { notification } from 'antd';

interface ApiError {
  status?: number;
  message?: string;
  detail?: string;
}

interface ErrorHandlerOptions {
  showNotification?: boolean;
  logToConsole?: boolean;
  reportToService?: boolean;
}

/**
 * 清理错误消息中的特殊字符和格式化内容
 */
const cleanErrorMessage = (message: string): string => {
  if (!message) return '发生未知错误';
  
  // 清理常见的技术错误前缀
  let cleaned = message.replace(/^Error:\s*/i, '');
  cleaned = cleaned.replace(/^Exception:\s*/i, '');
  cleaned = cleaned.replace(/^RuntimeError:\s*/i, '');
  
  // 清理HTTP状态码格式
  cleaned = cleaned.replace(/^HTTP \d+:\s*/i, '');
  
  // 清理yt-dlp相关的技术信息
  cleaned = cleaned.replace(/please report this issue on.*$/i, '');
  cleaned = cleaned.replace(/Confirm you are on the latest version.*$/i, '');
  cleaned = cleaned.replace(/\(caused by.*?\)/gi, '');
  
  // 清理多余的空白字符
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  
  // 如果消息过长，截断并添加省略号
  if (cleaned.length > 200) {
    cleaned = cleaned.substring(0, 197) + '...';
  }
  
  return cleaned || '发生未知错误';
};

/**
 * 根据错误类型提供用户友好的描述
 */
const getErrorDescription = (error: any): string => {
  const message = error?.message || error || '';
  
  if (typeof message !== 'string') {
    return '请检查网络连接或稍后重试';
  }
  
  const lowerMessage = message.toLowerCase();
  
  // 网络相关错误
  if (lowerMessage.includes('network') || lowerMessage.includes('connection') || 
      lowerMessage.includes('timeout') || lowerMessage.includes('failed to fetch')) {
    return '网络连接问题，请检查网络状态后重试';
  }
  
  // JSON解析错误
  if (lowerMessage.includes('json') || lowerMessage.includes('parse')) {
    return '数据解析失败，可能是服务器返回了无效数据';
  }
  
  // 权限相关错误
  if (lowerMessage.includes('unauthorized') || lowerMessage.includes('forbidden') ||
      lowerMessage.includes('access denied')) {
    return '访问权限不足，请检查登录状态';
  }
  
  // 视频不可用
  if (lowerMessage.includes('video unavailable') || lowerMessage.includes('not available') ||
      lowerMessage.includes('private video') || lowerMessage.includes('删除') || lowerMessage.includes('下架')) {
    return '视频不可用，可能已被删除或设为私有';
  }
  
  // 服务器错误
  if (lowerMessage.includes('500') || lowerMessage.includes('internal server error')) {
    return '服务器内部错误，请稍后重试';
  }
  
  // 地区限制
  if (lowerMessage.includes('region') || lowerMessage.includes('country') || 
      lowerMessage.includes('地区') || lowerMessage.includes('限制')) {
    return '内容受地区限制，无法访问';
  }
  
  return '请稍后重试或联系技术支持';
};

export interface UseErrorHandlerReturn {
  showError: (title: string, error: any) => void;
  showSuccess: (title: string, description?: string) => void;
  showInfo: (title: string, description?: string) => void;
  showWarning: (title: string, description?: string) => void;
  handleBusinessError: (error: any, fallbackTitle?: string) => void;
  cleanErrorMessage: (message: string) => string;
}

export const useErrorHandler = (): UseErrorHandlerReturn => {
  const showError = useCallback((title: string, error: any) => {
    const cleanedMessage = cleanErrorMessage(error?.message || error || '');
    const description = getErrorDescription(error);
    
    notification.error({
      message: title,
      description: `${cleanedMessage}${description ? ` - ${description}` : ''}`,
      duration: 8,
    });
  }, []);

  const showSuccess = useCallback((title: string, description?: string) => {
    notification.success({
      message: title,
      description,
      duration: 4,
    });
  }, []);

  const showInfo = useCallback((title: string, description?: string) => {
    notification.info({
      message: title,
      description,
      duration: 6,
    });
  }, []);

  const showWarning = useCallback((title: string, description?: string) => {
    notification.warning({
      message: title,
      description,
      duration: 6,
    });
  }, []);

  const handleBusinessError = useCallback((error: any, fallbackTitle = '操作失败') => {
    console.error('Business error:', error);
    showError(fallbackTitle, error);
  }, [showError]);

  return {
    showError,
    showSuccess,
    showInfo,
    showWarning,
    handleBusinessError,
    cleanErrorMessage,
  };
}; 