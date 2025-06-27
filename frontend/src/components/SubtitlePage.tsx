import React, { useState, useRef, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Select,
  Upload,
  Row,
  Col,
  Tabs,
  Progress,
  notification,
  Divider,
  Space,
  Switch,
  InputNumber,
  Alert,
  Typography,
  Spin,
  Tag,
  Tooltip
} from 'antd';
import {
  UploadOutlined,
  DownloadOutlined,
  TranslationOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  LinkOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  ExperimentOutlined,
  CloudDownloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { getApiBaseUrl, buildApiUrl, API_ENDPOINTS, buildFileUrl } from '../config/api';

const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { Text, Title } = Typography;

interface SubtitlePageProps {}

interface ProcessingStatus {
  isProcessing: boolean;
  progress: number;
  message: string;
  operation: string;
  startTime?: number;
  taskId?: string;
  videoTitle?: string;
}

// 任务状态管理工具
const TaskManager = {
  STORAGE_KEY: 'subtitle_task_status',
  
  // 保存任务状态
  saveTask: (status: ProcessingStatus) => {
    try {
      localStorage.setItem(TaskManager.STORAGE_KEY, JSON.stringify(status));
    } catch (error) {
      console.warn('保存任务状态失败:', error);
    }
  },
  
  // 加载任务状态
  loadTask: (): ProcessingStatus | null => {
    try {
      const saved = localStorage.getItem(TaskManager.STORAGE_KEY);
      if (saved) {
        const status = JSON.parse(saved);
        // 检查任务是否过期（根据任务类型设置过期时间）
        const getExpirationTime = () => {
          switch (status.operation) {
            case 'generate': return 60 * 60 * 1000; // 生成字幕：1小时
            case 'translate': return 45 * 60 * 1000; // 翻译字幕：45分钟
            case 'burn': return 90 * 60 * 1000; // 烧录字幕：1.5小时
            default: return 60 * 60 * 1000; // 默认：1小时
          }
        };
        
        if (status.startTime && Date.now() - status.startTime > getExpirationTime()) {
          TaskManager.clearTask();
          return null;
        }
        return status;
      }
    } catch (error) {
      console.warn('加载任务状态失败:', error);
      TaskManager.clearTask();
    }
    return null;
  },
  
  // 清理任务状态
  clearTask: () => {
    try {
      localStorage.removeItem(TaskManager.STORAGE_KEY);
    } catch (error) {
      console.warn('清理任务状态失败:', error);
    }
  },
  
  // 生成任务ID
  generateTaskId: () => {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
};

const SubtitlePage: React.FC<SubtitlePageProps> = () => {
  const [form] = Form.useForm();
  const [generateUrlForm] = Form.useForm();
  const [generateFileForm] = Form.useForm();
  const [translateForm] = Form.useForm();
  const [burnForm] = Form.useForm();
  
  const [loading, setLoading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    isProcessing: false,
    progress: 0,
    message: '',
    operation: ''
  });
  
  const [uploadedFile, setUploadedFile] = useState<any>(null);
  const [videoFile, setVideoFile] = useState<any>(null);
  const [subtitleFile, setSubtitleFile] = useState<any>(null);

  // 任务恢复定时器
  const taskRecoveryTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 更新任务状态并持久化
  const updateProcessingStatus = (status: ProcessingStatus) => {
    setProcessingStatus(status);
    if (status.isProcessing) {
      TaskManager.saveTask(status);
    } else {
      TaskManager.clearTask();
    }
  };

  // 恢复任务状态
  const recoverTaskStatus = () => {
    const savedTask = TaskManager.loadTask();
    if (savedTask && savedTask.isProcessing) {
      console.log('恢复任务状态:', savedTask);
      setProcessingStatus(savedTask);
      
      // 显示任务恢复通知
      notification.info({
        message: '任务状态已恢复',
        description: `继续处理: ${savedTask.videoTitle || '未知任务'}`,
        duration: 4
      });
      
      // 启动模拟进度更新（因为真实进度可能已经变化）
      startProgressSimulation(savedTask);
    }
  };

  // 模拟进度更新（用于任务恢复）
  const startProgressSimulation = (initialStatus: ProcessingStatus) => {
    if (taskRecoveryTimerRef.current) {
      clearInterval(taskRecoveryTimerRef.current);
    }
    
    taskRecoveryTimerRef.current = setInterval(() => {
      setProcessingStatus(prev => {
        if (!prev.isProcessing) {
          if (taskRecoveryTimerRef.current) {
            clearInterval(taskRecoveryTimerRef.current);
            taskRecoveryTimerRef.current = null;
          }
          return prev;
        }
        
        const newProgress = Math.min(prev.progress + 2, 90); // 缓慢增加到90%
        const newStatus = {
          ...prev,
          progress: newProgress,
          message: newProgress < 30 ? '正在处理文件...' : 
                   newProgress < 60 ? '正在生成/翻译内容...' : 
                   newProgress < 85 ? '即将完成...' : '正在收尾工作...'
        };
        
        TaskManager.saveTask(newStatus);
        return newStatus;
      });
    }, 3000); // 每3秒更新一次
  };

  // 检查任务完成状态
  const checkTaskCompletion = async () => {
    if (!processingStatus.isProcessing || !processingStatus.taskId) {
      return;
    }
    
    try {
      // 这里可以添加一个API来检查任务状态
      // const response = await fetch(`${getApiBaseUrl()}/api/v1/subtitles/task/${processingStatus.taskId}/status`);
      // if (response.ok) {
      //   const data = await response.json();
      //   if (data.completed) {
      //     // 任务完成，清理状态
      //     handleTaskCompletion();
      //   }
      // }
    } catch (error) {
      console.warn('检查任务状态失败:', error);
    }
  };

  // 处理任务完成
  const handleTaskCompletion = () => {
    updateProcessingStatus({
      isProcessing: false,
      progress: 100,
      message: '处理完成！',
      operation: processingStatus.operation
    });
    
    if (taskRecoveryTimerRef.current) {
      clearInterval(taskRecoveryTimerRef.current);
      taskRecoveryTimerRef.current = null;
    }
    
    setTimeout(() => {
      updateProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: '',
        operation: ''
      });
    }, 4000);
  };

  // 支持的语言列表
  const languages = [
    { code: 'auto', name: '自动检测' },
    { code: 'zh', name: '中文' },
    { code: 'en', name: '英语' },
    { code: 'ja', name: '日语' },
    { code: 'ko', name: '韩语' },
    { code: 'fr', name: '法语' },
    { code: 'de', name: '德语' },
    { code: 'es', name: '西班牙语' },
    { code: 'it', name: '意大利语' },
    { code: 'pt', name: '葡萄牙语' },
    { code: 'ru', name: '俄语' }
  ];

  // 视频质量选项
  const qualityOptions = [
    { value: 'low', label: '低质量 (快速)' },
    { value: 'medium', label: '中等质量 (推荐)' },
    { value: 'high', label: '高质量 (慢速)' },
    { value: 'original', label: '原始质量' }
  ];

  // 页面可见性检测和状态检查
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && processingStatus.isProcessing) {
        // 页面重新变得可见，检查任务状态
        console.log('页面可见，检查任务状态');
        
        // 检查任务是否超时（根据任务类型设置不同超时时间）
        const getTimeoutDuration = () => {
          switch (processingStatus.operation) {
            case 'generate': return 15 * 60 * 1000; // 生成字幕：15分钟
            case 'translate': return 10 * 60 * 1000; // 翻译字幕：10分钟
            case 'burn': return 20 * 60 * 1000; // 烧录字幕：20分钟
            default: return 10 * 60 * 1000; // 默认：10分钟
          }
        };
        
        if (processingStatus.startTime && 
            Date.now() - processingStatus.startTime > getTimeoutDuration()) {
          console.log('任务可能已超时，清理状态');
          updateProcessingStatus({
            isProcessing: false,
            progress: 0,
            message: '',
            operation: ''
          });
          notification.warning({
            message: '任务状态已重置',
            description: '检测到任务可能已完成或超时，已清理状态',
            duration: 3
          });
        }
      }
    };

    // 添加定期状态检查
    const statusCheckInterval = setInterval(() => {
      if (processingStatus.isProcessing && processingStatus.startTime) {
        const elapsedTime = Date.now() - processingStatus.startTime;
        
        // 根据任务类型和进度判断是否可能已完成但状态未更新
        const getProgressTimeout = () => {
          switch (processingStatus.operation) {
            case 'generate': return 8 * 60 * 1000; // 生成字幕：8分钟
            case 'translate': return 5 * 60 * 1000; // 翻译字幕：5分钟
            case 'burn': return 10 * 60 * 1000; // 烧录字幕：10分钟
            default: return 5 * 60 * 1000; // 默认：5分钟
          }
        };
        
        // 如果任务运行超过阈值且进度超过90%，可能已完成但状态未更新
        if (elapsedTime > getProgressTimeout() && processingStatus.progress >= 90) {
          console.log('检测到可能的状态同步问题，重置任务状态');
          updateProcessingStatus({
            isProcessing: false,
            progress: 0,
            message: '',
            operation: ''
          });
          notification.info({
            message: '任务状态已更新',
            description: '检测到任务可能已完成，请检查下载文件',
            duration: 4
          });
        }
      }
    }, 10000); // 每10秒检查一次

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(statusCheckInterval);
    };
  }, [processingStatus]);

  // 初始化加载
  useEffect(() => {
    // 恢复任务状态
    recoverTaskStatus();
    
    // 组件卸载时清理定时器
    return () => {
      if (taskRecoveryTimerRef.current) {
        clearInterval(taskRecoveryTimerRef.current);
      }
    };
  }, []);

  // 定期检查任务状态
  useEffect(() => {
    if (processingStatus.isProcessing) {
      const statusCheckInterval = setInterval(checkTaskCompletion, 10000); // 每10秒检查一次
      return () => clearInterval(statusCheckInterval);
    }
  }, [processingStatus.isProcessing]);

  // 通用流式处理函数（使用SSE进行真正的实时进度更新）
  const handleStreamProcess = async (operation: string, data: any, videoTitle: string = '视频') => {
    const taskId = TaskManager.generateTaskId();
    
    updateProcessingStatus({
      isProcessing: true,
      progress: 0,
      message: '正在连接服务器...',
      operation,
      startTime: Date.now(),
      taskId,
      videoTitle
    });

    // 先发送POST请求启动任务
    let connectionMonitor: NodeJS.Timeout | null = null;
    
    try {
      const initUrl = buildApiUrl(API_ENDPOINTS.SUBTITLES.STREAM);
      const initResponse = await fetch(initUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation,
          task_id: taskId,
          ...data
        }),
      });

      if (!initResponse.ok) {
        const errorData = await initResponse.json();
        throw new Error(errorData.detail || '启动任务失败');
      }

      // 读取SSE流
      const reader = initResponse.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        throw new Error('无法创建流读取器');
      }

      let downloadData: any = null;
      let buffer = '';
      let lastProgressTime = Date.now();
      let connectionAlive = true;

      // 连接监控定时器
      connectionMonitor = setInterval(() => {
        const now = Date.now();
        const timeSinceLastProgress = now - lastProgressTime;
        
        // 如果超过2分钟没有收到任何数据，认为连接可能断开
        if (timeSinceLastProgress > 2 * 60 * 1000 && connectionAlive) {
          console.warn('SSE连接可能断开，超过2分钟未收到数据');
          connectionAlive = false;
          
          updateProcessingStatus({
            isProcessing: false,
            progress: 0,
            message: '连接断开，请重试',
            operation: ''
          });
          
                     if (connectionMonitor) {
             clearInterval(connectionMonitor);
             connectionMonitor = null;
           }
           reader.cancel();
        }
      }, 30000); // 每30秒检查一次

      while (connectionAlive) {
        const { done, value } = await reader.read();
        
        if (done) {
          if (connectionMonitor) {
            clearInterval(connectionMonitor);
          }
          break;
        }
        
        // 更新最后接收数据的时间
        lastProgressTime = Date.now();
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // 保留最后一个不完整的行
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            
            if (dataStr === '[DONE]') {
              // 处理完成，开始下载
              if (downloadData && downloadData.download_ready) {
                // 触发文件下载
                const downloadUrl = buildApiUrl(`${API_ENDPOINTS.SUBTITLES.DOWNLOAD}/${downloadData.record_id}`);
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = downloadData.filename || 'subtitle.srt';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                notification.success({
                  message: '处理成功',
                  description: `${operation === 'translate' ? '翻译' : operation === 'generate' ? '生成' : '处理'}完成，文件已开始下载`,
                  duration: 4
                });
              }
              
              // 清理状态
              setTimeout(() => {
                setProcessingStatus({
                  isProcessing: false,
                  progress: 0,
                  message: '',
                  operation: ''
                });
                TaskManager.clearTask();
              }, 2000);
              
              return; // 退出函数
            }
            
            if (dataStr && dataStr !== '') {
              try {
                const progressData = JSON.parse(dataStr);
                
                if (progressData.error) {
                  throw new Error(progressData.error);
                }
                
                if (progressData.status === 'processing') {
                  // 更新进度
                  const newStatus = {
                    isProcessing: true,
                    progress: Math.max(progressData.progress || 0, 0),
                    message: progressData.message || '处理中...',
                    operation,
                    startTime: Date.now(),
                    taskId: progressData.task_id || progressData.record_id || taskId,
                    videoTitle
                  };
                  
                  setProcessingStatus(newStatus);
                  TaskManager.saveTask(newStatus);
                  
                  console.log(`进度更新: ${newStatus.progress}% - ${newStatus.message}`);
                } else if (progressData.status === 'completed') {
                  // 处理完成，准备下载
                  downloadData = progressData;
                  
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: 100,
                    message: progressData.message || '处理完成！'
                  }));
                } else if (progressData.status === 'cancelled') {
                  // 任务已被取消
                  updateProcessingStatus({
                    isProcessing: false,
                    progress: 0,
                    message: '任务已取消',
                    operation: ''
                  });
                  
                  notification.info({
                    message: '任务已取消',
                    description: '任务处理已停止',
                    duration: 3
                  });
                  
                  return; // 退出处理
                } else if (progressData.status === 'error') {
                  throw new Error(progressData.error || '处理失败');
                }
                
              } catch (parseError) {
                console.warn('解析SSE数据失败:', parseError, 'raw data:', dataStr);
              }
            }
          }
        }
      }

    } catch (error: any) {
      console.error('流式处理错误:', error);
      
      // 清理连接监控定时器
      if (connectionMonitor) {
        clearInterval(connectionMonitor);
      }
      
      updateProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: `处理失败: ${error.message}`,
        operation
      });

      notification.error({
        message: '处理失败',
        description: error.message || '字幕处理失败，请检查网络连接或稍后重试',
        duration: 5
      });
    }
  };

  // 从URL生成字幕（流式处理）
  const handleGenerateFromUrl = async (values: any) => {
    // 提取视频标题用于显示
    let videoTitle = '在线视频';
    if (values.video_url) {
      const urlMatch = values.video_url.match(/(?:v=|\/embed\/|\/watch\?v=|\/v\/|youtu\.be\/)([^&\n?#]+)/);
      if (urlMatch) {
        videoTitle = `YouTube视频 (${urlMatch[1].substring(0, 8)})`;
      }
    }
    
    await handleStreamProcess('generate', {
      video_url: values.video_url,
      language: values.language || 'auto',
      translate_to: values.translate_to
    }, videoTitle);
    
    generateUrlForm.resetFields();
  };

  // 从文件生成字幕
  const handleGenerateFromFile = async (values: any, file: any) => {
    if (!file) {
      notification.warning({
        message: '请选择视频文件',
        description: '请选择要生成字幕的视频文件',
      });
      return;
    }

    setLoading(true);
    
    try {
      // 先上传视频文件
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadResponse = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.UPLOAD), {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        const uploadError = await uploadResponse.json();
        throw new Error(uploadError.detail || '视频文件上传失败');
      }

      const uploadResult = await uploadResponse.json();
      setLoading(false);

      // 获取视频文件名作为任务标题
      const videoTitle = file.name.replace(/\.[^/.]+$/, '');

      // 然后流式生成字幕
      await handleStreamProcess('generate', {
        video_file_path: uploadResult.file_path,
        language: values.language || 'auto',
        translate_to: values.translate_to,
        original_title: videoTitle,
        prefer_local_filename: true
      }, videoTitle);

      generateFileForm.resetFields();
      setVideoFile(null);
    } catch (error: any) {
      setLoading(false);
      notification.error({
        message: '生成失败',
        description: error.message || '文件字幕生成失败',
      });
    }
  };

  // 翻译字幕（流式）
  const handleTranslate = async (values: any, file: any) => {
    if (!file) {
      notification.warning({
        message: '请选择字幕文件',
        description: '请选择要翻译的字幕文件',
      });
      return;
    }

    setLoading(true);
    
    try {
      // 先上传字幕文件
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadResponse = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.UPLOAD), {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        const uploadError = await uploadResponse.json();
        throw new Error(uploadError.detail || '字幕文件上传失败');
      }

      const uploadResult = await uploadResponse.json();
      setLoading(false);

      // 获取字幕文件名作为任务标题
      const subtitleTitle = file.name.replace(/\.[^/.]+$/, '') + ' (翻译)';

      // 然后流式翻译
      await handleStreamProcess('translate', {
        subtitle_file_path: uploadResult.file_path,
        source_language: values.source_language || 'auto',
        target_language: values.target_language,
        translation_method: 'sentencepiece', // 使用SentencePiece翻译
        original_title: file.name.replace(/\.[^/.]+$/, ''), // 移除文件扩展名
        prefer_local_filename: true
      }, subtitleTitle);

      translateForm.resetFields();
      setSubtitleFile(null);
    } catch (error: any) {
      setLoading(false);
      notification.error({
        message: '翻译失败',
        description: error.message || '字幕翻译失败',
      });
    }
  };

  // 字幕烧录
  const handleBurnSubtitles = async (values: any) => {
    if (!videoFile) {
      notification.warning({
        message: '请选择视频文件',
        description: '请选择要烧录字幕的视频文件',
      });
      return;
    }

    if (!subtitleFile) {
      notification.warning({
        message: '请选择字幕文件',
        description: '请选择要烧录的字幕文件',
      });
      return;
    }

    setLoading(true);
    
    try {
      // 上传视频文件
      const videoFormData = new FormData();
      videoFormData.append('file', videoFile);
      
      const videoUploadResponse = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.UPLOAD), {
        method: 'POST',
        body: videoFormData,
      });

      if (!videoUploadResponse.ok) {
        const videoError = await videoUploadResponse.json();
        throw new Error(videoError.detail || '视频文件上传失败');
      }

      const videoUploadResult = await videoUploadResponse.json();

      // 上传字幕文件
      const subtitleFormData = new FormData();
      subtitleFormData.append('file', subtitleFile);
      
      const subtitleUploadResponse = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.UPLOAD), {
        method: 'POST',
        body: subtitleFormData,
      });

      if (!subtitleUploadResponse.ok) {
        const subtitleError = await subtitleUploadResponse.json();
        throw new Error(subtitleError.detail || '字幕文件上传失败');
      }

      const subtitleUploadResult = await subtitleUploadResponse.json();
      
      setLoading(false);
      
      // 获取任务标题
      const burnTitle = `${videoFile.name.replace(/\.[^/.]+$/, '')} (烧录字幕)`;
      const taskId = TaskManager.generateTaskId();
      
      updateProcessingStatus({
        isProcessing: true,
        progress: 10,
        message: '正在准备烧录...',
        operation: 'burn',
        startTime: Date.now(),
        taskId,
        videoTitle: burnTitle
      });

      // 执行烧录（直接下载，不通过流式处理）
      const progressTimer = setInterval(() => {
        setProcessingStatus(prev => {
          if (!prev.isProcessing) {
            clearInterval(progressTimer);
            return prev;
          }
          
          const newProgress = Math.min(prev.progress + 5, 85);
          const newStatus = {
            ...prev,
            progress: newProgress,
            message: newProgress < 30 ? '正在分析视频...' : 
                     newProgress < 60 ? '正在烧录字幕...' : '即将完成...'
          };
          
          TaskManager.saveTask(newStatus);
          return newStatus;
        });
      }, 2000);

      const response = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.BURN), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_file_path: videoUploadResult.file_path,
          subtitle_file_path: subtitleUploadResult.file_path,
          video_title: videoFile.name.replace(/\.[^/.]+$/, ''),
          original_title: videoFile.name.replace(/\.[^/.]+$/, ''),
          prefer_local_filename: true,
          ...values
        }),
      });

      clearInterval(progressTimer);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '字幕烧录失败');
      }

      updateProcessingStatus({
        ...processingStatus,
        progress: 95,
        message: '正在准备下载...'
      });

      // 处理文件下载
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'video_with_subtitles.mp4';
      
      if (contentDisposition) {
        const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
        if (filenameStarMatch) {
          try {
            filename = decodeURIComponent(filenameStarMatch[1]);
          } catch (e) {
            console.warn('解码UTF-8文件名失败:', e);
          }
        } else {
          const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
      }

      // 创建下载
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);

      updateProcessingStatus({
        isProcessing: false,
        progress: 100,
        message: '烧录完成！文件已开始下载',
        operation: 'burn'
      });

      notification.success({
        message: '烧录成功',
        description: '字幕已烧录到视频中，文件已开始下载',
        duration: 4
      });

      burnForm.resetFields();
      setVideoFile(null);
      setSubtitleFile(null);

      // 清理状态
      setTimeout(() => {
        updateProcessingStatus({
          isProcessing: false,
          progress: 0,
          message: '',
          operation: ''
        });
      }, 4000);

    } catch (error: any) {
      setLoading(false);
      updateProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: `烧录失败: ${error.message}`,
        operation: 'burn'
      });
      
      notification.error({
        message: '烧录失败',
        description: error.message || '字幕烧录失败',
        duration: 5
      });
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <FileTextOutlined /> 字幕处理中心
      </Title>
      
      {processingStatus.isProcessing && (
        <Alert
          message={
            <div>
              <span>正在{processingStatus.operation === 'translate' ? '翻译' : processingStatus.operation === 'burn' ? '烧录' : '生成'}字幕...</span>
              {processingStatus.videoTitle && (
                <Tag color="blue" style={{ marginLeft: 8, fontSize: '12px' }}>
                  {processingStatus.videoTitle}
                </Tag>
              )}
            </div>
          }
          description={
            <div>
              <Progress 
                percent={processingStatus.progress} 
                status={processingStatus.progress === 100 ? "success" : "active"}
                showInfo={true}
                format={(percent) => `${percent}%`}
              />
              <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text type="secondary">{processingStatus.message}</Text>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {processingStatus.startTime && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      已用时: {Math.floor((Date.now() - processingStatus.startTime) / 1000)}秒
                    </Text>
                  )}
                  <Button 
                    size="small" 
                    type="text" 
                    danger 
                    onClick={async () => {
                      const { taskId } = processingStatus;
                      
                      if (taskId) {
                        try {
                          // 调用后端取消API
                          const response = await fetch(buildApiUrl(API_ENDPOINTS.SUBTITLES.CANCEL_TASK), {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ task_id: taskId }),
                          });
                          
                          const result = await response.json();
                          
                          if (result.success) {
                            notification.success({
                              message: '任务已取消',
                              description: '正在停止任务处理...',
                              duration: 3
                            });
                          } else {
                            notification.warning({
                              message: '取消失败',
                              description: result.message || '任务可能已完成或不存在',
                              duration: 3
                            });
                          }
                        } catch (error) {
                          console.error('取消任务失败:', error);
                          notification.error({
                            message: '取消失败',
                            description: '网络错误，请检查连接',
                            duration: 3
                          });
                        }
                      }
                      
                      // 无论后端取消是否成功，都重置前端状态
                      updateProcessingStatus({
                        isProcessing: false,
                        progress: 0,
                        message: '',
                        operation: '',
                        taskId: undefined
                      });
                    }}
                  >
                    取消
                  </Button>
                </div>
              </div>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Tabs defaultActiveKey="generate-url">
        <TabPane
          tab={<span><LinkOutlined />从URL生成</span>}
          key="generate-url"
        >
          <Card title="从视频URL生成字幕">
            <Form
              form={generateUrlForm}
              layout="vertical"
              onFinish={handleGenerateFromUrl}
            >
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item
                    label="视频URL"
                    name="video_url"
                    rules={[{ required: true, message: '请输入视频URL' }]}
                  >
                    <Input
                      placeholder="请输入YouTube、Bilibili等视频链接"
                      prefix={<LinkOutlined />}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="音频语言"
                    name="language"
                    initialValue="auto"
                  >
                    <Select>
                      {languages.map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="翻译到"
                    name="translate_to"
                  >
                    <Select placeholder="可选，选择要翻译的目标语言">
                      {languages.filter(lang => lang.code !== 'auto').map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                label="是否下载视频"
                name="download_video"
                valuePropName="checked"
                initialValue={false}
              >
                <Switch />
              </Form.Item>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  icon={<CloudDownloadOutlined />}
                  size="large"
                  block
                >
                  {processingStatus.isProcessing ? '正在生成...' : '生成并下载字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane
          tab={<span><UploadOutlined />从文件生成</span>}
          key="generate-file"
        >
          <Card title="从视频文件生成字幕">
            <Form
              form={generateFileForm}
              layout="vertical"
              onFinish={(values) => handleGenerateFromFile(values, videoFile)}
            >
              <Form.Item
                label="视频文件"
                required
              >
                <Upload
                  beforeUpload={(file) => {
                    setVideoFile(file);
                    return false;
                  }}
                  onRemove={() => setVideoFile(null)}
                  maxCount={1}
                  accept="video/*"
                >
                  <Button icon={<UploadOutlined />}>
                    选择视频文件
                  </Button>
                </Upload>
                {videoFile && (
                  <Text type="secondary">
                    已选择: {videoFile.name}
                  </Text>
                )}
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="音频语言"
                    name="language"
                    initialValue="auto"
                  >
                    <Select>
                      {languages.map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="翻译到"
                    name="translate_to"
                  >
                    <Select placeholder="可选，选择要翻译的目标语言">
                      {languages.filter(lang => lang.code !== 'auto').map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  icon={<CloudDownloadOutlined />}
                  size="large"
                  disabled={!videoFile}
                  block
                >
                  {loading ? '正在上传...' : processingStatus.isProcessing ? '正在生成...' : '生成并下载字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane
          tab={<span><TranslationOutlined />翻译字幕</span>}
          key="translate"
        >
          <Card title="翻译字幕文件">
            <Form
              form={translateForm}
              layout="vertical"
              onFinish={(values) => handleTranslate(values, subtitleFile)}
            >
              <Form.Item
                label="字幕文件"
                required
              >
                <Upload
                  beforeUpload={(file) => {
                    setSubtitleFile(file);
                    return false;
                  }}
                  onRemove={() => setSubtitleFile(null)}
                  maxCount={1}
                  accept=".srt,.vtt,.ass,.ssa"
                >
                  <Button icon={<UploadOutlined />}>
                    选择字幕文件
                  </Button>
                </Upload>
                {subtitleFile && (
                  <Text type="secondary">
                    已选择: {subtitleFile.name}
                  </Text>
                )}
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="源语言"
                    name="source_language"
                    initialValue="auto"
                  >
                    <Select>
                      {languages.map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="目标语言"
                    name="target_language"
                    rules={[{ required: true, message: '请选择目标语言' }]}
                  >
                    <Select placeholder="选择要翻译到的语言">
                      {languages.filter(lang => lang.code !== 'auto').map(lang => (
                        <Option key={lang.code} value={lang.code}>
                          {lang.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  icon={<TranslationOutlined />}
                  size="large"
                  disabled={!subtitleFile}
                  block
                >
                  {loading ? '正在上传...' : processingStatus.isProcessing ? '正在翻译...' : '翻译并下载字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane
          tab={<span><VideoCameraOutlined />烧录字幕</span>}
          key="burn"
        >
          <Card title="将字幕烧录到视频">
            <Form
              form={burnForm}
              layout="vertical"
              onFinish={handleBurnSubtitles}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label="视频文件"
                    required
                  >
                    <Upload
                      beforeUpload={(file) => {
                        setVideoFile(file);
                        return false;
                      }}
                      onRemove={() => setVideoFile(null)}
                      maxCount={1}
                      accept="video/*"
                    >
                      <Button icon={<VideoCameraOutlined />}>
                        选择视频文件
                      </Button>
                    </Upload>
                    {videoFile && (
                      <Text type="secondary">
                        已选择: {videoFile.name}
                      </Text>
                    )}
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label="字幕文件"
                    required
                  >
                    <Upload
                      beforeUpload={(file) => {
                        setSubtitleFile(file);
                        return false;
                      }}
                      onRemove={() => setSubtitleFile(null)}
                      maxCount={1}
                      accept=".srt,.vtt,.ass,.ssa"
                    >
                      <Button icon={<FileTextOutlined />}>
                        选择字幕文件
                      </Button>
                    </Upload>
                    {subtitleFile && (
                      <Text type="secondary">
                        已选择: {subtitleFile.name}
                      </Text>
                    )}
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="输出质量"
                    name="output_quality"
                    initialValue="medium"
                  >
                    <Select>
                      {qualityOptions.map(option => (
                        <Option key={option.value} value={option.value}>
                          {option.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="保留原始文件"
                    name="preserve_original"
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="字体大小"
                    name={['subtitle_style', 'font_size']}
                    initialValue={24}
                  >
                    <InputNumber min={12} max={72} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    label="字体颜色"
                    name={['subtitle_style', 'font_color']}
                    initialValue="white"
                  >
                    <Select>
                      <Option value="white">白色</Option>
                      <Option value="black">黑色</Option>
                      <Option value="red">红色</Option>
                      <Option value="yellow">黄色</Option>
                      <Option value="blue">蓝色</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="描边颜色"
                    name={['subtitle_style', 'outline_color']}
                    initialValue="black"
                  >
                    <Select>
                      <Option value="black">黑色</Option>
                      <Option value="white">白色</Option>
                      <Option value="red">红色</Option>
                      <Option value="blue">蓝色</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="描边宽度"
                    name={['subtitle_style', 'outline_width']}
                    initialValue={2}
                  >
                    <InputNumber min={0} max={10} />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  icon={<PlayCircleOutlined />}
                  size="large"
                  disabled={!videoFile || !subtitleFile}
                  block
                >
                  {loading ? '正在上传...' : processingStatus.isProcessing ? '正在烧录...' : '烧录并下载视频'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>

      <Divider />
      
      <Card 
        title={<span><ExperimentOutlined /> 使用说明</span>} 
        size="small"
        style={{ marginTop: 24 }}
      >
        <Row gutter={16}>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <LinkOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <Title level={5}>从URL生成</Title>
              <Text type="secondary">
                支持YouTube、Bilibili等主流视频平台，输入URL即可自动生成字幕
              </Text>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <UploadOutlined style={{ fontSize: 24, color: '#52c41a' }} />
              <Title level={5}>从文件生成</Title>
              <Text type="secondary">
                上传本地视频文件，使用AI模型自动识别语音并生成字幕
              </Text>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <TranslationOutlined style={{ fontSize: 24, color: '#faad14' }} />
              <Title level={5}>翻译字幕</Title>
              <Text type="secondary">
                支持多种语言互译，智能识别源语言，准确翻译到目标语言
              </Text>
            </div>
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <VideoCameraOutlined style={{ fontSize: 24, color: '#722ed1' }} />
              <Title level={5}>烧录字幕</Title>
              <Text type="secondary">
                将字幕永久烧录到视频中，可自定义字体样式和位置
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default SubtitlePage; 