import { useState, useEffect, useCallback } from 'react';

export interface UserSettings {
  // 下载设置
  defaultQuality: string;
  defaultFormat: string;
  defaultAudioOnly: boolean;
  defaultSubtitle: boolean;
  defaultSubtitleLanguage: string;
  downloadPath: string;
  
  // 界面设置
  theme: 'light' | 'dark' | 'auto';
  language: 'zh-CN' | 'en-US';
  compactMode: boolean;
  
  // 行为设置
  autoRefresh: boolean;
  refreshInterval: number; // 秒
  confirmBeforeDelete: boolean;
  showNotifications: boolean;
  
  // 高级设置
  concurrentDownloads: number;
  retryAttempts: number;
  timeoutDuration: number; // 秒
  enableStream: boolean; // 默认是否启用流式下载
}

const DEFAULT_SETTINGS: UserSettings = {
  // 下载设置
  defaultQuality: 'best',
  defaultFormat: 'mp4',
  defaultAudioOnly: false,
  defaultSubtitle: false,
  defaultSubtitleLanguage: 'auto',
  downloadPath: '',
  
  // 界面设置
  theme: 'light',
  language: 'zh-CN',
  compactMode: false,
  
  // 行为设置
  autoRefresh: true,
  refreshInterval: 5,
  confirmBeforeDelete: true,
  showNotifications: true,
  
  // 高级设置
  concurrentDownloads: 3,
  retryAttempts: 3,
  timeoutDuration: 30,
  enableStream: false,
};

const STORAGE_KEY = 'avd_user_settings';

export const useSettings = () => {
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);

  // 从本地存储加载设置
  const loadSettings = useCallback(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsedSettings = JSON.parse(stored);
        // 合并默认设置，确保新增字段有默认值
        setSettings({ ...DEFAULT_SETTINGS, ...parsedSettings });
      }
    } catch (error) {
      console.error('加载用户设置失败:', error);
      // 如果解析失败，使用默认设置
      setSettings(DEFAULT_SETTINGS);
    } finally {
      setLoading(false);
    }
  }, []);

  // 保存设置到本地存储
  const saveSettings = useCallback((newSettings: UserSettings) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
      setSettings(newSettings);
      return true;
    } catch (error) {
      console.error('保存用户设置失败:', error);
      return false;
    }
  }, []);

  // 更新单个设置项
  const updateSetting = useCallback(<K extends keyof UserSettings>(
    key: K,
    value: UserSettings[K]
  ) => {
    const newSettings = { ...settings, [key]: value };
    return saveSettings(newSettings);
  }, [settings, saveSettings]);

  // 批量更新设置
  const updateSettings = useCallback((updates: Partial<UserSettings>) => {
    const newSettings = { ...settings, ...updates };
    return saveSettings(newSettings);
  }, [settings, saveSettings]);

  // 重置为默认设置
  const resetSettings = useCallback(() => {
    return saveSettings(DEFAULT_SETTINGS);
  }, [saveSettings]);

  // 导出设置
  const exportSettings = useCallback(() => {
    const settingsBlob = new Blob([JSON.stringify(settings, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(settingsBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `avd_settings_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [settings]);

  // 导入设置
  const importSettings = useCallback((file: File): Promise<boolean> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const importedSettings = JSON.parse(content);
          
          // 验证导入的设置是否有效
          const validatedSettings = { ...DEFAULT_SETTINGS, ...importedSettings };
          const success = saveSettings(validatedSettings);
          resolve(success);
        } catch (error) {
          console.error('导入设置失败:', error);
          resolve(false);
        }
      };
      reader.onerror = () => resolve(false);
      reader.readAsText(file);
    });
  }, [saveSettings]);

  // 获取下载表单的默认值
  const getDownloadDefaults = useCallback(() => {
    return {
      quality: settings.defaultQuality,
      format: settings.defaultFormat,
      audio_only: settings.defaultAudioOnly,
      subtitle: settings.defaultSubtitle,
      subtitle_language: settings.defaultSubtitleLanguage,
      stream_download: settings.enableStream,
    };
  }, [settings]);

  // 检查是否为默认设置
  const isDefaultSettings = useCallback(() => {
    return JSON.stringify(settings) === JSON.stringify(DEFAULT_SETTINGS);
  }, [settings]);

  // 初始化时加载设置
  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // 应用主题设置
  useEffect(() => {
    const applyTheme = () => {
      const { theme } = settings;
      const root = document.documentElement;
      
      if (theme === 'auto') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
      } else {
        root.setAttribute('data-theme', theme);
      }
    };

    if (!loading) {
      applyTheme();
      
      // 监听系统主题变化
      if (settings.theme === 'auto') {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', applyTheme);
        return () => mediaQuery.removeEventListener('change', applyTheme);
      }
    }
  }, [settings.theme, loading]);

  return {
    settings,
    loading,
    updateSetting,
    updateSettings,
    resetSettings,
    exportSettings,
    importSettings,
    getDownloadDefaults,
    isDefaultSettings,
    defaultSettings: DEFAULT_SETTINGS,
  };
}; 