import { useState, useEffect } from 'react';

export type ThemeMode = 'light' | 'dark';

export interface UseThemeReturn {
  isDarkMode: boolean;
  themeMode: ThemeMode;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
}

const STORAGE_KEY = 'avd-theme';

export const useTheme = (): UseThemeReturn => {
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    // 从localStorage读取保存的主题，如果没有则根据系统偏好设置
    const savedTheme = localStorage.getItem(STORAGE_KEY);
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }

    // 检查系统偏好
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }

    return 'light';
  });

  const isDarkMode = themeMode === 'dark';

  const setTheme = (mode: ThemeMode) => {
    setThemeMode(mode);
    localStorage.setItem(STORAGE_KEY, mode);
    
    // 更新body类名以便全局样式应用
    document.body.setAttribute('data-theme', mode);
    
    // 更新根元素样式
    if (mode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const toggleTheme = () => {
    setTheme(isDarkMode ? 'light' : 'dark');
  };

  // 监听系统主题变化
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      // 只有在用户没有手动设置过主题时才自动跟随系统
      const savedTheme = localStorage.getItem(STORAGE_KEY);
      if (!savedTheme) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleSystemThemeChange);

    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange);
    };
  }, []);

  // 初始化时设置主题
  useEffect(() => {
    setTheme(themeMode);
  }, []);

  return {
    isDarkMode,
    themeMode,
    toggleTheme,
    setTheme,
  };
}; 