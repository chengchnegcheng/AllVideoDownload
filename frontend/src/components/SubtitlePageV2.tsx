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
  Space,
  Alert,
  Typography,
  Spin,
  Tag,
  Tooltip,
  Divider
} from 'antd';
import {
  UploadOutlined,
  DownloadOutlined,
  TranslationOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  ExperimentOutlined,
  CloudDownloadOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  CrownOutlined
} from '@ant-design/icons';
import { getApiBaseUrl } from '../config/api';

const { Option } = Select;
const { TabPane } = Tabs;
const { Text, Title } = Typography;

interface SubtitlePageV2Props {}

interface ProcessingStatus {
  isProcessing: boolean;
  progress: number;
  message: string;
  operation: string;
  startTime?: number;
  downloadFilename?: string;
  subtitleFile?: string;
}

// 支持的语言列表
const SUPPORTED_LANGUAGES = {
  'zh': '中文',
  'zh-cn': '简体中文', 
  'zh-tw': '繁体中文',
  'en': '英语',
  'ja': '日语',
  'ko': '韩语',
  'fr': '法语',
  'de': '德语',
  'es': '西班牙语',
  'ru': '俄语',
  'ar': '阿拉伯语',
  'hi': '印地语',
  'pt': '葡萄牙语',
  'it': '意大利语',
  'th': '泰语',
  'vi': '越南语'
};

const SubtitlePageV2: React.FC<SubtitlePageV2Props> = () => {
  const [urlForm] = Form.useForm();
  const [fileForm] = Form.useForm();
  const [translateForm] = Form.useForm();
  
  const [loading, setLoading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    isProcessing: false,
    progress: 0,
    message: '',
    operation: ''
  });
  
  const [videoFile, setVideoFile] = useState<any>(null);
  const [subtitleFile, setSubtitleFile] = useState<any>(null);
  
  const eventSourceRef = useRef<EventSource | null>(null);

  // 清理EventSource连接
  const cleanupEventSource = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  // 处理流式响应
  const handleStreamResponse = (url: string, operation: string) => {
    cleanupEventSource();
    
    setProcessingStatus({
      isProcessing: true,
      progress: 0,
      message: '正在初始化...',
      operation,
      startTime: Date.now()
    });
    
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.status === 'processing') {
          setProcessingStatus(prev => ({
            ...prev,
            progress: data.progress || 0,
            message: data.message || ''
          }));
        } else if (data.status === 'completed') {
          setProcessingStatus(prev => ({
            ...prev,
            progress: 100,
            message: data.message || '处理完成！',
            downloadFilename: data.download_filename,
            subtitleFile: data.subtitle_file
          }));
          
          // 自动下载文件
          if (data.subtitle_file && data.download_filename) {
            setTimeout(() => {
              downloadSubtitleFile(data.subtitle_file, data.download_filename);
            }, 1000);
          }
          
          // 延迟重置状态
          setTimeout(() => {
            setProcessingStatus({
              isProcessing: false,
              progress: 0,
              message: '',
              operation: ''
            });
          }, 3000);
          
          cleanupEventSource();
        } else if (data.status === 'error') {
          notification.error({
            message: '处理失败',
            description: data.error,
            duration: 5
          });
          
          setProcessingStatus({
            isProcessing: false,
            progress: 0,
            message: '',
            operation: ''
          });
          
          cleanupEventSource();
        }
      } catch (error) {
        console.error('解析SSE数据失败:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error);
      notification.error({
        message: '连接错误',
        description: '与服务器的连接出现问题，请重试',
        duration: 3
      });
      
      setProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: '',
        operation: ''
      });
      
      cleanupEventSource();
    };
  };

  // 下载字幕文件
  const downloadSubtitleFile = (filePath: string, filename: string) => {
    try {
      // 创建下载链接
      const downloadUrl = `${getApiBaseUrl()}/api/v2/subtitles/download/${encodeURIComponent(filePath.split('/').pop() || '')}`;
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      notification.success({
        message: '下载开始',
        description: `正在下载: ${filename}`,
        duration: 3
      });
    } catch (error) {
      console.error('下载文件失败:', error);
      notification.error({
        message: '下载失败',
        description: '无法下载文件，请重试',
        duration: 3
      });
    }
  };

  // 从URL生成字幕
  const handleGenerateFromUrl = async (values: any) => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams({
        video_url: values.video_url,
        target_language: values.target_language
      });
      
      const url = `${getApiBaseUrl()}/api/v2/subtitles/stream-generate-from-url?${params.toString()}`;
      
      // 构建请求数据
      const requestData = {
        video_url: values.video_url,
        target_language: values.target_language
      };
      
      // 发送POST请求到流式端点
      const response = await fetch(`${getApiBaseUrl()}/api/v2/subtitles/stream-generate-from-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }
      
      // 读取流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法读取响应流');
      }
      
      setProcessingStatus({
        isProcessing: true,
        progress: 0,
        message: '正在初始化...',
        operation: 'generate-url',
        startTime: Date.now()
      });
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.status === 'processing') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: data.progress || 0,
                    message: data.message || ''
                  }));
                } else if (data.status === 'completed') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: 100,
                    message: data.message || '处理完成！',
                    downloadFilename: data.download_filename,
                    subtitleFile: data.subtitle_file
                  }));
                  
                  // 自动下载文件
                  if (data.subtitle_file && data.download_filename) {
                    setTimeout(() => {
                      downloadSubtitleFile(data.subtitle_file, data.download_filename);
                    }, 1000);
                  }
                  
                  // 延迟重置状态
                  setTimeout(() => {
                    setProcessingStatus({
                      isProcessing: false,
                      progress: 0,
                      message: '',
                      operation: ''
                    });
                  }, 3000);
                  
                  return; // 完成处理
                } else if (data.status === 'error') {
                  throw new Error(data.error);
                }
              } catch (parseError) {
                console.warn('解析数据失败:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
      
    } catch (error: any) {
      console.error('从URL生成字幕失败:', error);
      notification.error({
        message: '生成字幕失败',
        description: error.message || '请检查URL或网络连接',
        duration: 5
      });
      
      setProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: '',
        operation: ''
      });
    } finally {
      setLoading(false);
    }
  };

  // 从文件生成字幕
  const handleGenerateFromFile = async (values: any) => {
    if (!videoFile) {
      notification.error({
        message: '文件错误',
        description: '请先选择视频文件',
        duration: 3
      });
      return;
    }
    
    try {
      setLoading(true);
      
      const formData = new FormData();
      formData.append('file', videoFile);
      formData.append('target_language', values.target_language);
      
      const response = await fetch(`${getApiBaseUrl()}/api/v2/subtitles/stream-generate-from-file`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }
      
      // 读取流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法读取响应流');
      }
      
      setProcessingStatus({
        isProcessing: true,
        progress: 0,
        message: '正在上传文件...',
        operation: 'generate-file',
        startTime: Date.now()
      });
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.status === 'processing') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: data.progress || 0,
                    message: data.message || ''
                  }));
                } else if (data.status === 'completed') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: 100,
                    message: data.message || '处理完成！',
                    downloadFilename: data.download_filename,
                    subtitleFile: data.subtitle_file
                  }));
                  
                  // 自动下载文件
                  if (data.subtitle_file && data.download_filename) {
                    setTimeout(() => {
                      downloadSubtitleFile(data.subtitle_file, data.download_filename);
                    }, 1000);
                  }
                  
                  // 延迟重置状态
                  setTimeout(() => {
                    setProcessingStatus({
                      isProcessing: false,
                      progress: 0,
                      message: '',
                      operation: ''
                    });
                    setVideoFile(null);
                  }, 3000);
                  
                  return; // 完成处理
                } else if (data.status === 'error') {
                  throw new Error(data.error);
                }
              } catch (parseError) {
                console.warn('解析数据失败:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
      
    } catch (error: any) {
      console.error('从文件生成字幕失败:', error);
      notification.error({
        message: '生成字幕失败',
        description: error.message || '请检查文件格式',
        duration: 5
      });
      
      setProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: '',
        operation: ''
      });
    } finally {
      setLoading(false);
    }
  };

  // 翻译字幕文件
  const handleTranslateSubtitle = async (values: any) => {
    if (!subtitleFile) {
      notification.error({
        message: '文件错误',
        description: '请先选择字幕文件',
        duration: 3
      });
      return;
    }
    
    try {
      setLoading(true);
      
      const formData = new FormData();
      formData.append('file', subtitleFile);
      formData.append('target_language', values.target_language);
      
      const response = await fetch(`${getApiBaseUrl()}/api/v2/subtitles/stream-translate-subtitle`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }
      
      // 读取流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法读取响应流');
      }
      
      setProcessingStatus({
        isProcessing: true,
        progress: 0,
        message: '正在上传字幕文件...',
        operation: 'translate',
        startTime: Date.now()
      });
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.status === 'processing') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: data.progress || 0,
                    message: data.message || ''
                  }));
                } else if (data.status === 'completed') {
                  setProcessingStatus(prev => ({
                    ...prev,
                    progress: 100,
                    message: data.message || '翻译完成！',
                    downloadFilename: data.download_filename,
                    subtitleFile: data.subtitle_file
                  }));
                  
                  // 自动下载文件
                  if (data.subtitle_file && data.download_filename) {
                    setTimeout(() => {
                      downloadSubtitleFile(data.subtitle_file, data.download_filename);
                    }, 1000);
                  }
                  
                  // 延迟重置状态
                  setTimeout(() => {
                    setProcessingStatus({
                      isProcessing: false,
                      progress: 0,
                      message: '',
                      operation: ''
                    });
                    setSubtitleFile(null);
                  }, 3000);
                  
                  return; // 完成处理
                } else if (data.status === 'error') {
                  throw new Error(data.error);
                }
              } catch (parseError) {
                console.warn('解析数据失败:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
      
    } catch (error: any) {
      console.error('翻译字幕失败:', error);
      notification.error({
        message: '翻译字幕失败',
        description: error.message || '请检查文件格式',
        duration: 5
      });
      
      setProcessingStatus({
        isProcessing: false,
        progress: 0,
        message: '',
        operation: ''
      });
    } finally {
      setLoading(false);
    }
  };

  // 文件上传配置
  const videoUploadProps = {
    name: 'file',
    multiple: false,
    accept: '.mp4,.avi,.mov,.mkv,.flv,.wmv,.mp3,.wav,.m4a,.flac',
    beforeUpload: (file: any) => {
      setVideoFile(file);
      return false; // 阻止自动上传
    },
    onRemove: () => {
      setVideoFile(null);
    },
  };

  const subtitleUploadProps = {
    name: 'file',
    multiple: false,
    accept: '.srt,.vtt,.ass,.ssa',
    beforeUpload: (file: any) => {
      setSubtitleFile(file);
      return false; // 阻止自动上传
    },
    onRemove: () => {
      setSubtitleFile(null);
    },
  };

  // 清理
  useEffect(() => {
    return () => {
      cleanupEventSource();
    };
  }, []);

  const renderLanguageSelector = (fieldName: string = "target_language") => (
    <Form.Item
      label={
        <span>
          目标语言 
          <Tooltip title="选择要翻译到的目标语言">
            <InfoCircleOutlined style={{ marginLeft: 4, color: '#1890ff' }} />
          </Tooltip>
        </span>
      }
      name={fieldName}
      initialValue="zh"
      rules={[{ required: true, message: '请选择目标语言' }]}
    >
      <Select placeholder="选择目标语言">
        {Object.entries(SUPPORTED_LANGUAGES).map(([code, name]) => (
          <Option key={code} value={code}>
            {name}
          </Option>
        ))}
      </Select>
    </Form.Item>
  );

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ textAlign: 'center', marginBottom: '30px' }}>
        <Title level={2}>
          <CrownOutlined style={{ color: '#f5222d', marginRight: '8px' }} />
          高品质字幕处理中心 v2
          <Tag color="red" style={{ marginLeft: '12px' }}>最高品质</Tag>
        </Title>
        <Text type="secondary" style={{ fontSize: '16px' }}>
          采用最新AI技术，提供最高品质的字幕生成和翻译服务
        </Text>
        
        <Alert
          message="高品质特性"
          description={
            <div>
              <div>🚀 使用 Whisper Large-v3 最高品质语音识别模型</div>
              <div>🧠 采用先进的 AI 翻译模型，支持多语言高质量翻译</div>
              <div>🔄 自动文件管理和清理，无需手动操作</div>
              <div>📱 支持流式进度显示，实时查看处理状态</div>
            </div>
          }
          type="info"
          showIcon
          style={{ marginTop: '20px', textAlign: 'left' }}
        />
      </div>

      {/* 处理进度显示 */}
      {processingStatus.isProcessing && (
        <Card style={{ marginBottom: '20px' }}>
          <div style={{ textAlign: 'center' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Progress 
                percent={Math.round(processingStatus.progress)} 
                status={processingStatus.progress === 100 ? "success" : "active"}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              <Text style={{ display: 'block', marginTop: '8px', fontSize: '16px' }}>
                {processingStatus.message || '正在处理...'}
              </Text>
            </div>
          </div>
        </Card>
      )}

      <Tabs defaultActiveKey="1" type="card">
        {/* 从URL生成字幕 */}
        <TabPane 
          tab={
            <span>
              <LinkOutlined />
              从URL生成
            </span>
          } 
          key="1"
        >
          <Card 
            title={
              <span>
                <VideoCameraOutlined style={{ marginRight: '8px' }} />
                从视频URL生成字幕
                <Tag color="gold" style={{ marginLeft: '8px' }}>最高品质</Tag>
              </span>
            }
          >
            <Alert
              message="处理流程"
              description="视频下载到服务器 → 音频提取 → Whisper Large-v3 语音识别 → AI翻译 → 自动下载 → 自动清理"
              type="info"
              showIcon
              style={{ marginBottom: '20px' }}
            />
            
            <Form 
              form={urlForm} 
              layout="vertical" 
              onFinish={handleGenerateFromUrl}
              disabled={processingStatus.isProcessing}
            >
              <Form.Item
                label="视频URL"
                name="video_url"
                rules={[
                  { required: true, message: '请输入视频URL' },
                  { type: 'url', message: '请输入有效的URL' }
                ]}
              >
                <Input 
                  placeholder="请输入YouTube、B站等视频URL" 
                  prefix={<LinkOutlined />}
                />
              </Form.Item>

              {renderLanguageSelector()}

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  icon={<CloudDownloadOutlined />}
                  size="large"
                  block
                >
                  {processingStatus.isProcessing ? '正在处理中...' : '开始生成字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        {/* 从文件生成字幕 */}
        <TabPane 
          tab={
            <span>
              <UploadOutlined />
              从文件生成
            </span>
          } 
          key="2"
        >
          <Card 
            title={
              <span>
                <PlayCircleOutlined style={{ marginRight: '8px' }} />
                从视频文件生成字幕
                <Tag color="gold" style={{ marginLeft: '8px' }}>最高品质</Tag>
              </span>
            }
          >
            <Alert
              message="处理流程"
              description="文件上传到服务器 → 音频提取 → Whisper Large-v3 语音识别 → AI翻译 → 自动下载 → 自动清理"
              type="info"
              showIcon
              style={{ marginBottom: '20px' }}
            />
            
            <Form 
              form={fileForm} 
              layout="vertical" 
              onFinish={handleGenerateFromFile}
              disabled={processingStatus.isProcessing}
            >
              <Form.Item
                label="视频文件"
                required
              >
                <Upload {...videoUploadProps}>
                  <Button icon={<UploadOutlined />} disabled={processingStatus.isProcessing}>
                    选择视频文件
                  </Button>
                </Upload>
                {videoFile && (
                  <Text style={{ marginTop: '8px', display: 'block' }}>
                    已选择: {videoFile.name}
                  </Text>
                )}
              </Form.Item>

              {renderLanguageSelector()}

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  disabled={!videoFile}
                  icon={<ThunderboltOutlined />}
                  size="large"
                  block
                >
                  {processingStatus.isProcessing ? '正在处理中...' : '开始生成字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        {/* 翻译字幕文件 */}
        <TabPane 
          tab={
            <span>
              <TranslationOutlined />
              翻译字幕
            </span>
          } 
          key="3"
        >
          <Card 
            title={
              <span>
                <FileTextOutlined style={{ marginRight: '8px' }} />
                翻译字幕文件
                <Tag color="gold" style={{ marginLeft: '8px' }}>最高品质</Tag>
              </span>
            }
          >
            <Alert
              message="处理流程"
              description="字幕文件上传到服务器 → AI高品质翻译 → 自动下载 → 自动清理"
              type="info"
              showIcon
              style={{ marginBottom: '20px' }}
            />
            
            <Form 
              form={translateForm} 
              layout="vertical" 
              onFinish={handleTranslateSubtitle}
              disabled={processingStatus.isProcessing}
            >
              <Form.Item
                label="字幕文件"
                required
              >
                <Upload {...subtitleUploadProps}>
                  <Button icon={<UploadOutlined />} disabled={processingStatus.isProcessing}>
                    选择字幕文件
                  </Button>
                </Upload>
                {subtitleFile && (
                  <Text style={{ marginTop: '8px', display: 'block' }}>
                    已选择: {subtitleFile.name}
                  </Text>
                )}
              </Form.Item>

              {renderLanguageSelector()}

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading || processingStatus.isProcessing}
                  disabled={!subtitleFile}
                  icon={<TranslationOutlined />}
                  size="large"
                  block
                >
                  {processingStatus.isProcessing ? '正在翻译中...' : '开始翻译字幕'}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>
      </Tabs>

      <Divider />

      <div style={{ textAlign: 'center', marginTop: '20px' }}>
        <Text type="secondary">
          💡 提示：所有处理完成后，字幕文件将自动下载到您的设备，服务器临时文件会自动清理
        </Text>
      </div>
    </div>
  );
};

export default SubtitlePageV2;