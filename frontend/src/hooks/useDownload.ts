import { useState, useCallback, useEffect } from 'react';
import { notification } from 'antd';
import { getApiBaseUrl, buildApiUrl, API_ENDPOINTS } from '../config/api';
// 本地类型定义 (替代已删除的types/download.ts)
interface DownloadRequest {
  url: string;
  quality?: string;
  format?: string;
  audio_only?: boolean;
  subtitle?: boolean;
  subtitle_language?: string;
  output_path?: string;
}

interface DownloadRecord {
  id: string;
  url: string;
  title: string | null;
  description?: string;
  thumbnail?: string;
  uploader?: string;
  platform?: string;
  quality?: string;
  format?: string;
  audio_only?: boolean;
  subtitle?: boolean;
  status: 'recorded' | 'completed'; // 简化状态，只有记录状态
  created_at: string;
  completed_at?: string;
}



// 下载服务 - 适配新的API端点
const downloadService = {
  async getSupportedPlatforms() {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.PLATFORMS));
    if (!response.ok) throw new Error('Failed to fetch platforms');
    return response.json();
  },
  
  async getQualityOptions() {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.QUALITY_OPTIONS));
    if (!response.ok) throw new Error('Failed to fetch qualities');
    return response.json();
  },
  
  async getRecords(page: number = 1, size: number = 20) {
    const response = await fetch(buildApiUrl(`${API_ENDPOINTS.DOWNLOADS.RECORDS}?page=${page}&size=${size}`));
    if (!response.ok) throw new Error('Failed to fetch records');
    return response.json();
  },
  
  async getVideoInfo(url: string) {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.INFO), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!response.ok) throw new Error('Failed to get video info');
    return response.json();
  },
  
  async createDownloadRecord(request: DownloadRequest) {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.RECORD), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    if (!response.ok) throw new Error('Failed to create download record');
    const result = await response.json();
    return result.record_id;
  },
  
  async deleteRecord(recordId: string) {
    const response = await fetch(buildApiUrl(`${API_ENDPOINTS.DOWNLOADS.RECORDS}/${recordId}`), {
      method: 'DELETE'
    });
    return response.ok;
  },
  
  async batchDeleteRecords(recordIds: string[]) {
    const response = await fetch(buildApiUrl(`${API_ENDPOINTS.DOWNLOADS.RECORDS}/batch`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(recordIds)
    });
    return response.json();
  }
};

export interface UseDownloadReturn {
  downloadRecords: DownloadRecord[];
  isLoading: boolean;
  loading: boolean;
  platforms: Record<string, any>;
  qualities: Record<string, string>;
  createRecord: (request: DownloadRequest) => Promise<string | null>;
  deleteRecord: (recordId: string) => Promise<boolean>;
  clearAllRecords: () => void;
  refreshRecords: () => Promise<void>;
  getVideoInfo: (url: string) => Promise<any>;
  // 兼容性属性和方法
  activeDownloads: any[];
  startDownload: (request: DownloadRequest) => Promise<string | null>;
  cancelDownload: (recordId: string) => Promise<boolean>;
  clearCompleted: () => void;
  refreshTasks: () => Promise<void>;
  pauseDownload: () => Promise<boolean>;
  resumeDownload: () => Promise<boolean>;
  getProgress: () => null;
  isDownloading: boolean;
}

export const useDownload = (): UseDownloadReturn => {
  const [downloadRecords, setDownloadRecords] = useState<DownloadRecord[]>([]);
  const [platforms, setPlatforms] = useState<Record<string, any>>({});
  const [qualities, setQualities] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 加载支持的平台
  const loadPlatforms = useCallback(async () => {
    try {
      const platformData = await downloadService.getSupportedPlatforms();
      setPlatforms(platformData);
    } catch (error) {
      console.error('Failed to load platforms:', error);
    }
  }, []);

  // 加载质量选项
  const loadQualities = useCallback(async () => {
    try {
      const qualityData = await downloadService.getQualityOptions();
      setQualities(qualityData);
    } catch (error) {
      console.error('Failed to load quality options:', error);
    }
  }, []);

  // 刷新下载记录列表
  const refreshRecords = useCallback(async () => {
    try {
      setLoading(true);
      const response = await downloadService.getRecords();
      const records = response.records || [];
      setDownloadRecords(Array.isArray(records) ? records : []);
    } catch (error) {
      console.debug('Failed to refresh records:', error);
      setDownloadRecords([]);
      if (process.env.NODE_ENV === 'development') {
        console.warn('后端服务未启动或网络连接失败');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取视频信息
  const getVideoInfo = useCallback(async (url: string) => {
    try {
      return await downloadService.getVideoInfo(url);
    } catch (error) {
      console.error('Failed to get video info:', error);
      throw error;
    }
  }, []);

  // 创建下载记录
  const createRecord = useCallback(async (request: DownloadRequest): Promise<string | null> => {
    try {
      // 验证URL
      if (!request.url || !request.url.trim()) {
        notification.error({
          message: '记录创建失败',
          description: '请输入有效的视频URL',
        });
        return null;
      }

      setIsLoading(true);
      // 调用后端API创建记录
      const recordId = await downloadService.createDownloadRecord(request);

      notification.success({
        message: '下载记录已创建',
        description: '记录已保存，可以使用流式下载获取文件',
        duration: 3,
      });

      // 刷新记录列表
      await refreshRecords();

      return recordId;
    } catch (error) {
      console.error('Create record error:', error);
      notification.error({
        message: '记录创建失败',
        description: error instanceof Error ? error.message : '记录创建失败',
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [refreshRecords]);

  // 删除下载记录
  const deleteRecord = useCallback(async (recordId: string): Promise<boolean> => {
    try {
      const success = await downloadService.deleteRecord(recordId);
      
      if (success) {
        notification.info({
          message: '记录已删除',
          description: '下载记录已成功删除',
        });
        
        // 刷新记录列表
        await refreshRecords();
      }
      
      return success;
    } catch (error) {
      console.error('Delete record error:', error);
      notification.error({
        message: '删除失败',
        description: '无法删除下载记录',
      });
      return false;
    }
  }, [refreshRecords]);

  // 清除所有记录
  const clearAllRecords = useCallback(async () => {
    try {
      if (downloadRecords.length === 0) {
        notification.info({
          message: '无需清理',
          description: '没有需要清理的记录',
        });
        return;
      }

      // 调用批量删除API
      const recordIds = downloadRecords.map(record => record.id);
      const result = await downloadService.batchDeleteRecords(recordIds);

      if (result.success) {
        notification.success({
          message: '清理完成',
          description: `已删除 ${result.deleted_count} 个记录`,
        });
        
        // 刷新记录列表
        await refreshRecords();
      } else {
        throw new Error('批量删除失败');
      }
    } catch (error) {
      console.error('Clear records error:', error);
      notification.error({
        message: '清理失败',
        description: '无法清理下载记录',
      });
    }
  }, [downloadRecords, refreshRecords]);

  

  // 初始化加载
  useEffect(() => {
    // 并行加载所有数据
    Promise.all([
      loadPlatforms(),
      loadQualities(),
      refreshRecords()
    ]).catch(error => {
      console.debug('初始化加载失败:', error);
    });
  }, [loadPlatforms, loadQualities, refreshRecords]);

  // 兼容性：为了不破坏现有组件，保留一些旧的属性名和方法
  return {
    downloadRecords,
    // 兼容旧的属性名
    activeDownloads: downloadRecords as any,
    isLoading,
    loading,
    platforms,
    qualities,
    createRecord,
    // 兼容旧的方法名
    startDownload: createRecord as any,
    deleteRecord,
    // 兼容旧的方法名
    cancelDownload: deleteRecord as any,
    clearAllRecords,
    // 兼容旧的方法名
    clearCompleted: clearAllRecords as any,
    refreshRecords,
    // 兼容旧的方法名
    refreshTasks: refreshRecords,
    getVideoInfo,
    // 移除的功能返回默认值以保持兼容性
    pauseDownload: async () => {
      notification.info({
        message: '功能已移除',
        description: '暂停功能已移除，请使用流式下载',
      });
      return false;
    },
    resumeDownload: async () => {
      notification.info({
        message: '功能已移除',
        description: '恢复功能已移除，请使用流式下载',
      });
      return false;
    },
    getProgress: () => null,
    isDownloading: false,
  };
}; 