import { useState, useEffect, useCallback } from 'react';
import { notification } from 'antd';

// 系统设置接口，与后端 SystemSettings 模型对应
export interface SystemSettings {
  // 服务器设置
  server_host: string;
  backend_port: number;
  frontend_port: number;
  
  // 下载设置
  max_concurrent_downloads: number;
  max_file_size_mb: number;
  default_quality: string;
  default_format: string;
  
  // 存储设置
  files_path: string;
  auto_cleanup_days: number;
  
  // 网络设置
  http_proxy?: string;
  https_proxy?: string;
  rate_limit_per_minute: number;
  
  // 日志设置
  log_level: string;
  log_retention_days: number;
}

// 系统信息接口，与后端API返回的数据结构对应
export interface SystemInfo {
  platform: string;
  python_version: string;
  cpu: {
    count: number;
    usage: number;
    load_average?: number[];
  };
  memory: {
    total: number;
    available: number;
    used: number;
    percentage: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    percentage: number;
  };
  network: {
    bytes_sent: number;
    bytes_recv: number;
    packets_sent: number;
    packets_recv: number;
  };
  processes: {
    count: number;
    current_pid: number;
    current_memory: number;
  };
  environment: {
    app_name: string;
    version: string;
    debug: boolean;
    host: string;
    port: number;
  };
}

// 任务统计接口
export interface TaskStats {
  total_downloads: number;
  active_downloads: number;
  completed_downloads: number;
  failed_downloads: number;
  total_subtitles: number;
  active_subtitles: number;
  completed_subtitles: number;
  failed_subtitles: number;
}

// 系统配置选项
export interface SystemConfig {
  supported_platforms: Record<string, any>;
  quality_options: Record<string, string>;
  subtitle_languages: Record<string, string>;
  supported_formats: string[];
  whisper_models: Record<string, string>;
  devices: Record<string, string>;
  log_levels: Record<string, string>;
}

// 日志文件信息
export interface LogFileInfo {
  name: string;
  size: number;
  size_formatted: string;
  modified_time: string;
  modified_time_formatted: string;
  is_log_file: boolean;
  extension: string;
}

// 日志目录信息
export interface LogsInfo {
  path: string;
  exists: boolean;
  total_size: number;
  total_size_formatted: string;
  file_count: number;
  files: LogFileInfo[];
  last_updated: string;
}

// 获取API基础URL
const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // 如果是开发环境（3000端口），使用8000端口作为API
    if (port === '3000') {
      return `${protocol}//${hostname}:8000`;
    }
    
    // 生产环境或其他情况，使用同样的域名和端口
    return `${protocol}//${hostname}${port ? ':' + port : ''}`;
  }
  return 'http://127.0.0.1:8000';
};

export const useSystemSettings = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  // const [logsInfo, setLogsInfo] = useState<LogsInfo | null>(null); // 暂时移除，避免404错误
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 加载系统设置
  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/v1/system/settings`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSettings(data);
    } catch (error: any) {
      console.error('加载系统设置失败:', error);
      notification.error({
        message: '加载失败',
        description: `无法加载系统设置: ${error.message}`,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // 保存系统设置
  const saveSettings = useCallback(async (newSettings: SystemSettings) => {
    try {
      setSaving(true);
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/v1/system/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSettings),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      setSettings(newSettings);
      
      notification.success({
        message: '保存成功',
        description: result.note || '系统设置已更新',
      });

      return true;
    } catch (error: any) {
      console.error('保存系统设置失败:', error);
      notification.error({
        message: '保存失败',
        description: `无法保存系统设置: ${error.message}`,
      });
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  // 加载系统信息
  const loadSystemInfo = useCallback(async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/v1/system/info`);
      
      if (response.ok) {
        const data = await response.json();
        setSystemInfo(data);
      }
    } catch (error) {
      console.error('加载系统信息失败:', error);
    }
  }, []);

  // 加载任务统计
  const loadTaskStats = useCallback(async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/v1/system/stats`);
      
      if (response.ok) {
        const data = await response.json();
        setTaskStats(data);
      }
    } catch (error) {
      console.error('加载任务统计失败:', error);
    }
  }, []);

  // 加载系统配置
  const loadSystemConfig = useCallback(async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/v1/system/config`);
      
      if (response.ok) {
        const data = await response.json();
        setSystemConfig(data);
      }
    } catch (error) {
      console.error('加载系统配置失败:', error);
    }
  }, []);

  // 加载日志信息 - 暂时注释掉，因为后端没有这个API端点
  // const loadLogsInfo = useCallback(async () => {
  //   try {
  //     const baseUrl = getApiBaseUrl();
  //     const response = await fetch(`${baseUrl}/api/v1/system/logs/info`);
  //     
  //     if (response.ok) {
  //       const data = await response.json();
  //       setLogsInfo(data);
  //     }
  //   } catch (error) {
  //     console.error('加载日志信息失败:', error);
  //   }
  // }, []);

  // 系统清理
  const cleanupSystem = useCallback(async (options: {
    cleanup_downloads?: boolean;
    cleanup_logs?: boolean;
    cleanup_temp?: boolean;
    days_old?: number;
  }) => {
    try {
      const baseUrl = getApiBaseUrl();
      const params = new URLSearchParams();
      
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, String(value));
        }
      });

      const response = await fetch(`${baseUrl}/api/v1/system/cleanup?${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      
      notification.success({
        message: '清理完成',
        description: `${result.message}\n清理项目: ${result.cleaned_items.join(', ')}`,
      });

      return result;
    } catch (error: any) {
      console.error('系统清理失败:', error);
      notification.error({
        message: '清理失败',
        description: `系统清理失败: ${error.message}`,
      });
      return null;
    }
  }, []);

  // 刷新所有数据
  const refreshData = useCallback(async () => {
    await Promise.all([
      loadSettings(),
      loadSystemInfo(),
      loadTaskStats(),
      loadSystemConfig(),
      // loadLogsInfo(),  // 暂时移除，避免404错误
    ]);
  }, [loadSettings, loadSystemInfo, loadTaskStats, loadSystemConfig]); // 移除loadLogsInfo依赖

  // 初始化加载
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  return {
    // 数据
    settings,
    systemInfo,
    taskStats,
    systemConfig,
    // logsInfo,  // 暂时移除
    
    // 状态
    loading,
    saving,
    
    // 方法
    loadSettings,
    saveSettings,
    loadSystemInfo,
    loadTaskStats,
    loadSystemConfig,
    // loadLogsInfo,  // 暂时移除
    cleanupSystem,
    refreshData,
  };
}; 