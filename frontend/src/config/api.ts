// API配置
export const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    // 在浏览器环境中，根据当前域名构建API URL
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
  
  // 服务器端渲染或其他情况的默认值
  return 'http://127.0.0.1:8000';
};

// 统一文件访问路径配置
export const FILE_ACCESS_PATHS = {
  // 新的统一访问路径（推荐）
  UNIFIED: '/files',
  
  // 向后兼容的路径
  UPLOADS: '/uploads',
  DOWNLOADS: '/downloads'
};

// API端点配置
export const API_ENDPOINTS = {
  // 字幕相关 - 新版模块化API (version 2.0)
  SUBTITLES: {
    // 基本信息
    LANGUAGES: '/api/v1/subtitles/info/languages',
    MODELS: '/api/v1/subtitles/info/models',
    TRANSLATION_METHODS: '/api/v1/subtitles/info/translation-methods',
    
    // 文件上传
    UPLOAD: '/api/v1/subtitles/upload',
    
    // 文件管理 - 修正为实际可用的端点  
    RECORDS: '/api/v1/subtitles/records',
    DOWNLOAD: '/api/v1/subtitles/files/download',
    
    // 任务管理
    CANCEL_TASK: '/api/v1/subtitles/tasks/cancel-task',
    TASK_STATUS: '/api/v1/subtitles/tasks/task-status',
    
    // 核心处理
    STREAM: '/api/v1/subtitles/processor/stream',
    GENERATE_FROM_URL: '/api/v1/subtitles/processor/generate-from-url',
    GENERATE_FROM_FILE: '/api/v1/subtitles/processor/generate-from-file',
    BURN: '/api/v1/subtitles/processor/burn',
    
    // 设置管理
    AI_SETTINGS: '/api/v1/subtitles/settings/ai-settings',
    AI_SETTINGS_TEST: '/api/v1/subtitles/settings/ai-settings/test',
    TRANSLATION_SETTINGS: '/api/v1/subtitles/settings/translation-settings',
    TEST_TRANSLATION: '/api/v1/subtitles/settings/test-translation',
    
    // 向后兼容的旧端点别名
    TRANSLATE: '/api/v1/subtitles/settings/test-translation'
  },
  
  // 上传相关 - 注意：这些端点可能不存在，需要使用字幕上传端点
  UPLOADS: {
    VIDEO: '/api/v1/subtitles/upload', // 使用字幕模块的上传端点
    SUBTITLE: '/api/v1/subtitles/upload' // 使用字幕模块的上传端点
  },
  
  // 下载相关
  DOWNLOADS: {
    PLATFORMS: '/api/v1/downloads/platforms',
    QUALITY_OPTIONS: '/api/v1/downloads/quality-options',
    RECORDS: '/api/v1/downloads/records',
    INFO: '/api/v1/downloads/info',
    RECORD: '/api/v1/downloads/record',
    STREAM: '/api/v1/downloads/stream'
  },
  
  // 系统相关
  SYSTEM: {
    INFO: '/api/v1/system/info',
    SETTINGS: '/api/v1/system/settings',
    STATS: '/api/v1/system/stats',
    CONFIG: '/api/v1/system/config'
  }
};

// 构建完整的API URL
export const buildApiUrl = (endpoint: string): string => {
  return `${getApiBaseUrl()}${endpoint}`;
};

// 构建文件访问URL
export const buildFileUrl = (filename: string, useUnifiedPath: boolean = true): string => {
  const basePath = useUnifiedPath ? FILE_ACCESS_PATHS.UNIFIED : FILE_ACCESS_PATHS.DOWNLOADS;
  return `${getApiBaseUrl()}${basePath}/${filename}`;
};

// HTTP请求配置
export const REQUEST_CONFIG = {
  timeout: 0, // 取消超时限制
  headers: {
    'Content-Type': 'application/json',
  },
};

// 文件上传配置
export const UPLOAD_CONFIG = {
  maxSize: 500 * 1024 * 1024, // 500MB
  acceptedVideoTypes: ['video/mp4', 'video/avi', 'video/mkv', 'video/mov', 'video/wmv'],
  acceptedSubtitleTypes: ['text/srt', 'text/vtt', 'application/x-subrip'],
  chunkSize: 1024 * 1024, // 1MB chunks for large file upload
}; 