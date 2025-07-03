import React, { useState, useEffect, useRef } from 'react';
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

    // 添加定期状态检查 - 降低频率减少对其他页面的影响
    const statusCheckInterval = setInterval(() => {
      if (processingStatus.isProcessing && processingStatus.startTime) {
        const elapsedTime = Date.now() - processingStatus.startTime;
        
        // 根据任务类型和进度判断是否可能已完成但状态未更新
        const getProgressTimeout = () => {
          switch (processingStatus.operation) {
            case 'generate': return 10 * 60 * 1000; // 生成字幕：10分钟
            case 'translate': return 7 * 60 * 1000; // 翻译字幕：7分钟
            case 'burn': return 15 * 60 * 1000; // 烧录字幕：15分钟
            default: return 8 * 60 * 1000; // 默认：8分钟
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
    }, 30000); // 每30秒检查一次，减少频率

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

  // 定期检查任务状态 - 仅在必要时进行
  useEffect(() => {
    if (processingStatus.isProcessing && processingStatus.progress < 95) {
      // 只有在任务进行中且进度未达到95%时才进行检查
      const statusCheckInterval = setInterval(checkTaskCompletion, 15000); // 每15秒检查一次，减少频率
      return () => clearInterval(statusCheckInterval);
    }
  }, [processingStatus.isProcessing, processingStatus.progress]);

  // 统一处理异步任务
  const handleAsyncProcess = async (operation: string, data: any, videoTitle: string = '视频') => {
    try {
      // 1. 发送异步处理请求
      const processUrl = buildApiUrl(API_ENDPOINTS.SUBTITLES.PROCESS);
      const processResponse = await fetch(processUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation,
          ...data
        }),
      });

      if (!processResponse.ok) {
        const errorData = await processResponse.json();
        throw new Error(errorData.detail || `${operation}请求失败`);
      }

      const processData = await processResponse.json();
      const backendTaskId = processData.task_id;
      const frontendTaskId = Date.now().toString();

      // 2. 设置初始状态
      updateProcessingStatus({
        isProcessing: true,
        progress: 0,
        message: '任务已提交，开始处理...',
        operation,
        startTime: Date.now(),
        taskId: frontendTaskId,
        videoTitle
      });

      // 轮询状态检查函数
      let isCompleted = false; // 添加标志防止重复通知
      const pollStatus = async () => {
        try {
          const statusUrl = buildApiUrl(`${API_ENDPOINTS.SUBTITLES.STATUS}/${backendTaskId}`);
          const statusResponse = await fetch(statusUrl);
          
          if (!statusResponse.ok) {
            throw new Error('获取任务状态失败');
          }
          
          const statusData = await statusResponse.json();
          
          // 更新前端状态
          updateProcessingStatus({
            isProcessing: statusData.status === 'running' || statusData.status === 'pending',
            progress: statusData.progress,
            message: statusData.message || '处理中...',
            operation,
            startTime: Date.now(),
            taskId: frontendTaskId,
            videoTitle
          });

          if (statusData.status === 'completed' && !isCompleted) {
            isCompleted = true; // 设置标志防止重复处理
            
            // 任务完成，触发下载
            if (statusData.result && statusData.result.subtitle_file) {
              const subtitleFilename = statusData.result.subtitle_file.split('/').pop() || statusData.result.subtitle_file;
              const downloadUrl = buildApiUrl(`${API_ENDPOINTS.SUBTITLES.DOWNLOAD}/${subtitleFilename}`);
             
              const link = document.createElement('a');
              link.href = downloadUrl;
              link.download = subtitleFilename;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              
              notification.success({
                message: '处理成功',
                description: `${operation === 'translate' ? '翻译' : operation === 'generate_from_url' || operation === 'generate_from_file' ? '生成' : '处理'}完成，文件已开始下载`,
                duration: 4
              });
            }
            
            // 清理状态
            setTimeout(() => {
              updateProcessingStatus({
                isProcessing: false,
                progress: 0,
                message: '',
                operation: ''
              });
            }, 2000);
            
            return true; // 停止轮询
          } else if (statusData.status === 'failed' && !isCompleted) {
            isCompleted = true; // 防止重复处理错误
            throw new Error(statusData.error || '任务处理失败');
          } else if (statusData.status === 'cancelled' && !isCompleted) {
            isCompleted = true; // 防止重复处理取消
            updateProcessingStatus({
              isProcessing: false,
              progress: 0,
              message: '任务已取消',
              operation: ''
            });
            return true; // 停止轮询
          }
          
          return false; // 继续轮询
        } catch (error) {
          throw error;
        }
      };

      // 3. 开始轮询状态 - 使用指数退避策略
      let pollIntervalTime = 2000; // 初始2秒
      let pollAttempts = 0;
      const maxPollInterval = 10000; // 最大10秒
      
      const scheduleNextPoll = () => {
        setTimeout(async () => {
          try {
            pollAttempts++;
            const shouldStop = await pollStatus();
            if (shouldStop) {
              return; // 停止轮询
            }
            
            // 指数退避：每次增加间隔时间，减少服务器压力
            if (pollAttempts > 5) {
              pollIntervalTime = Math.min(pollIntervalTime * 1.2, maxPollInterval);
            }
            
            scheduleNextPoll(); // 递归调度下次轮询
          } catch (error) {
            console.error('轮询状态检查失败:', error);
            // 出错时也继续轮询，但延长间隔
            pollIntervalTime = Math.min(pollIntervalTime * 2, maxPollInterval);
            scheduleNextPoll();
          }
        }, pollIntervalTime);
      };

      // 启动优化后的轮询调度
      scheduleNextPoll();

    } catch (error: any) {
      console.error('异步任务处理错误:', error);
      
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

  // 从URL生成字幕（异步任务模式）
  const handleGenerateFromUrl = async (values: any) => {
    // 提取视频标题用于显示
    let videoTitle = '在线视频';
    if (values.video_url) {
      const urlMatch = values.video_url.match(/(?:v=|\/embed\/|\/watch\?v=|\/v\/|youtu\.be\/)([^&\n?#]+)/);
      if (urlMatch) {
        videoTitle = `YouTube视频 (${urlMatch[1].substring(0, 8)})`;
      }
    }
    
    await handleAsyncProcess('generate_from_url', {
      video_url: values.video_url,
      language: values.language || 'auto',
      target_language: values.translate_to
    }, videoTitle);
    
    generateUrlForm.resetFields();
  };

  // 从文件生成字幕（异步任务模式）
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

      // 然后异步生成字幕
      await handleAsyncProcess('generate_from_file', {
        video_file_path: uploadResult.file_path,
        language: values.language || 'auto',
        target_language: values.translate_to
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

  // 翻译字幕（异步任务模式）
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

      // 然后异步翻译
      await handleAsyncProcess('translate', {
        subtitle_file_path: uploadResult.file_path,
        source_language: values.source_language || 'auto',
        target_language: values.target_language,
        translation_method: values.translation_method || 'optimized'
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

  // 字幕烧录（暂时禁用）
  const handleBurnSubtitles = async (values: any) => {
    // 烧录功能暂时不可用
    notification.warning({
      message: '功能暂时不可用',
      description: '字幕烧录功能正在开发中，敬请期待后续更新',
      duration: 4
    });
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