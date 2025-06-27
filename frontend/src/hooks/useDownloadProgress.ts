import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';

export interface DownloadProgress {
  taskId: string;
  status: 'preparing' | 'downloading' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  speed?: string;
  eta?: string;
  downloaded?: string;
  total?: string;
  filename?: string;
  error?: string;
  timestamp: number;
}

export interface UseDownloadProgressReturn {
  progressData: Record<string, DownloadProgress>;
  isConnected: boolean;
  connectionStatus: string;
  startProgressTracking: (taskId: string) => void;
  stopProgressTracking: (taskId: string) => void;
  clearProgress: (taskId: string) => void;
  clearAllProgress: () => void;
}

export const useDownloadProgress = (): UseDownloadProgressReturn => {
  const [progressData, setProgressData] = useState<Record<string, DownloadProgress>>({});
  const trackingTasksRef = useRef<Set<string>>(new Set());
  
  // 处理接收到的WebSocket消息
  const handleWebSocketMessage = useCallback((data: any) => {
    if (data.type === 'download_progress' && data.task_id) {
      const taskId = data.task_id;
      
      // 只处理正在追踪的任务
      if (!trackingTasksRef.current.has(taskId)) {
        return;
      }

      // 从嵌套的data字段中获取进度数据
      const progressData = data.data || {};
      
      // 格式化速度
      const formatSpeed = (bytesPerSec: number): string => {
        if (!bytesPerSec || bytesPerSec === 0) return '';
        if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
        if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
        return `${(bytesPerSec / 1024 / 1024).toFixed(1)} MB/s`;
      };
      
      // 格式化ETA
      const formatETA = (seconds: number): string => {
        if (!seconds || seconds === 0) return '';
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}小时${minutes}分`;
      };
      
      // 格式化字节数
      const formatBytes = (bytes: number): string => {
        if (!bytes || bytes === 0) return '0 B';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
        return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
      };

      const progressInfo: DownloadProgress = {
        taskId,
        status: progressData.status || 'downloading',
        progress: Math.min(100, Math.max(0, progressData.progress || 0)),
        speed: formatSpeed(progressData.speed),
        eta: formatETA(progressData.eta),
        downloaded: formatBytes(progressData.downloaded_bytes),
        total: formatBytes(progressData.total_bytes),
        filename: progressData.title || progressData.filename || '',
        error: progressData.error || '',
        timestamp: data.timestamp || Date.now()
      };

      setProgressData(prev => ({
        ...prev,
        [taskId]: progressInfo
      }));

      // 如果任务完成或失败，自动停止追踪
      if (progressInfo.status === 'completed' || progressInfo.status === 'failed') {
        setTimeout(() => {
          trackingTasksRef.current.delete(taskId);
        }, 2000); // 2秒后清理
      }
    }
  }, []);
  
  const { isConnected, connectionStatus, sendMessage } = useWebSocket({
    url: `ws://${window.location.hostname}:8000/ws`,
    onMessage: handleWebSocketMessage
  });

  // 监听WebSocket消息
  useEffect(() => {
    const ws = (window as any).webSocketConnection;
    if (ws) {
      ws.addEventListener('message', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      });
    }
  }, [handleWebSocketMessage]);

  const startProgressTracking = useCallback((taskId: string) => {
    trackingTasksRef.current.add(taskId);
    
    // 初始化进度数据
    setProgressData(prev => ({
      ...prev,
      [taskId]: {
        taskId,
        status: 'preparing',
        progress: 0,
        timestamp: Date.now()
      }
    }));
  }, []);

  const stopProgressTracking = useCallback((taskId: string) => {
    trackingTasksRef.current.delete(taskId);
  }, []);

  const clearProgress = useCallback((taskId: string) => {
    setProgressData(prev => {
      const newData = { ...prev };
      delete newData[taskId];
      return newData;
    });
    trackingTasksRef.current.delete(taskId);
  }, []);

  const clearAllProgress = useCallback(() => {
    setProgressData({});
    trackingTasksRef.current.clear();
  }, []);

  return {
    progressData,
    isConnected,
    connectionStatus,
    startProgressTracking,
    stopProgressTracking,
    clearProgress,
    clearAllProgress
  };
}; 