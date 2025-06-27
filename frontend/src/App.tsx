import React, { useState, useEffect, Suspense, lazy } from 'react';
import {
  Layout,
  Menu,
  Card,
  Button,
  Input,
  Form,
  Select,
  Progress,
  Typography,
  Space,
  Row,
  Col,
  notification,
  Tag,
  List,
  Empty,
  Spin,
  Tooltip,
  Switch,
  Divider,
  Modal,
  Alert
} from 'antd';
import {
  DownloadOutlined,
  HistoryOutlined,
  SettingOutlined,
  FileTextOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  YoutubeOutlined,
  HomeOutlined,
  ReloadOutlined,
  EyeOutlined,
  AppstoreAddOutlined,
  CloudDownloadOutlined,
  InfoCircleOutlined,
  MenuOutlined
} from '@ant-design/icons';
import { useDownload } from './hooks/useDownload';
import { getApiBaseUrl, buildApiUrl, API_ENDPOINTS, buildFileUrl } from './config/api';
import { useDownloadProgress } from './hooks/useDownloadProgress';
import './App.css';

// 懒加载组件
const HistoryPage = lazy(() => import('./components/HistoryPage'));
const SystemPage = lazy(() => import('./components/SystemPage'));
const SubtitlePage = lazy(() => import('./components/SubtitlePage'));
const SystemInfoPage = lazy(() => import('./components/SystemInfoPage'));
const LogsPage = lazy(() => import('./components/LogsPage'));

const { Header, Content, Sider } = Layout;
const { Title, Paragraph, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// 平台图标和颜色映射
const platformConfig: Record<string, { icon: React.ReactNode; color: string; name: string }> = {
  youtube: { icon: <YoutubeOutlined />, color: 'red', name: 'YouTube' },
  bilibili: { icon: <PlayCircleOutlined />, color: 'pink', name: 'Bilibili' },
  douyin: { icon: <PlayCircleOutlined />, color: 'black', name: '抖音' },
  weixin: { icon: <PlayCircleOutlined />, color: 'green', name: '微信视频号' },
  xiaohongshu: { icon: <PlayCircleOutlined />, color: 'red', name: '小红书' },
  qq: { icon: <PlayCircleOutlined />, color: 'blue', name: '腾讯视频' },
  youku: { icon: <PlayCircleOutlined />, color: 'blue', name: '优酷' },
  iqiyi: { icon: <PlayCircleOutlined />, color: 'green', name: '爱奇艺' },
  generic: { icon: <LinkOutlined />, color: 'default', name: '通用' }
};

// 获取平台标签
const getPlatformTag = (platform?: string) => {
  if (!platform) return null;
  const config = platformConfig[platform.toLowerCase()] || platformConfig.generic;
  return (
    <Tag icon={config.icon} color={config.color}>
      {config.name}
    </Tag>
  );
};

// 主下载页面组件
const DownloadPage: React.FC = () => {
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [videoInfo, setVideoInfo] = useState<any>(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [streamLoading, setStreamLoading] = useState(false);
  const [showBatchDownload, setShowBatchDownload] = useState(false);
  const [batchUrls, setBatchUrls] = useState<string>('');
  const [batchLoading, setBatchLoading] = useState(false);
  // 实时进度状态
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const {
    activeDownloads,
    platforms,
    qualities,
    loading,
    startDownload,
    cancelDownload,
    pauseDownload,
    resumeDownload,
    getVideoInfo,
    refreshTasks,
    clearCompleted,
    isDownloading
  } = useDownload();

  // 实时进度Hook
  const { 
    progressData, 
    isConnected, 
    connectionStatus,
    startProgressTracking,
    stopProgressTracking,
    clearProgress
  } = useDownloadProgress();

  // 获取视频信息
  const handleGetVideoInfo = async (url: string) => {
    if (!url || !url.trim()) {
      notification.error({
        message: '错误',
        description: '请输入有效的视频URL',
      });
      return;
    }

    setLoadingInfo(true);
    try {
      const apiUrl = buildApiUrl(API_ENDPOINTS.DOWNLOADS.INFO);
      console.log('发起获取视频信息请求:', apiUrl, { url });
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      console.log('视频信息响应状态:', response.status, response.statusText);

      if (response.ok) {
        const info = await response.json();
        console.log('获取到视频信息:', info);
        setVideoInfo(info);
        notification.success({
          message: '视频信息获取成功',
          description: `📹 ${info.title}`,
          duration: 3,
        });
      } else {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          console.log('无法解析错误响应为JSON:', e);
        }
        console.error('获取视频信息失败详情:', errorMessage);
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('获取视频信息请求错误:', error);
      
      let userMessage = '请检查URL是否正确，或稍后重试';
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        userMessage = '无法连接到服务器，请检查网络连接或服务器状态';
      } else if (error.message) {
        userMessage = error.message;
      }
      
      notification.error({
        message: '获取视频信息失败',
        description: userMessage,
        duration: 8,
      });
      setVideoInfo(null);
    } finally {
      setLoadingInfo(false);
    }
  };

  // 流式下载视频
  const handleStreamDownload = async (values: any) => {
    setDownloadLoading(true);
    
    try {
      // 生成任务ID
      const taskId = `download_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setCurrentTaskId(taskId);
      
      // 开始进度跟踪
      startProgressTracking(taskId);
      
      const apiUrl = buildApiUrl(API_ENDPOINTS.DOWNLOADS.STREAM);
      console.log('发起下载请求:', apiUrl, values);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation: 'download',
          url: values.url,
          quality: values.quality || 'best',
          format: values.format || 'mp4',
          audio_only: values.audio_only || false,
          subtitle: values.subtitle || false,
          task_id: taskId  // 添加任务ID
        }),
      });

      console.log('下载响应状态:', response.status, response.statusText);

      if (response.ok) {
        // 获取文件名（支持UTF-8编码）
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = videoInfo ? `${videoInfo.title}.${values.format || 'mp4'}` : 'video.mp4';
        
        console.log('Content-Disposition头:', contentDisposition);
        
        if (contentDisposition) {
          // 尝试匹配UTF-8编码的文件名
          const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
          if (utf8Match) {
            try {
              filename = decodeURIComponent(utf8Match[1]);
              console.log('使用UTF-8编码文件名:', filename);
            } catch (e) {
              console.warn('UTF-8解码失败:', e);
              // 如果UTF-8解码失败，尝试简单匹配
              const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
              if (simpleMatch) {
                filename = simpleMatch[1];
                console.log('使用简单匹配文件名:', filename);
              }
            }
          } else {
            // 如果没有UTF-8编码，使用简单匹配
            const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
            if (simpleMatch) {
              filename = simpleMatch[1];
              console.log('使用简单匹配文件名:', filename);
            }
          }
        } else if (videoInfo && videoInfo.title) {
          // 如果没有Content-Disposition头，但有视频信息，使用视频标题
          const safeTitle = videoInfo.title.replace(/[<>:"/\\|?*]/g, '').trim();
          filename = `${safeTitle}.${values.format || 'mp4'}`;
          console.log('使用视频标题作为文件名:', filename);
        }
        
        console.log('最终使用的文件名:', filename);

        // 创建下载
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        notification.success({
          message: '下载完成',
          description: '视频已下载到本地',
        });
        
        // 下载成功后创建记录
        try {
          console.log('创建下载记录...');
          const recordResponse = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.RECORD), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              url: values.url,
              quality: values.quality || 'best',
              format: values.format || 'mp4',
              audio_only: values.audio_only || false,
              subtitle: values.subtitle || false,
              subtitle_language: values.subtitle_language || 'auto',
              output_filename: filename // 使用实际的文件名
            }),
          });
          
          if (recordResponse.ok) {
            const recordData = await recordResponse.json();
            console.log('下载记录创建成功:', recordData.record_id);
          } else {
            console.warn('创建下载记录失败，但下载已完成');
          }
        } catch (recordError) {
          console.warn('创建下载记录时出错:', recordError);
          // 不影响主要的下载流程
        }
        
        // 停止进度跟踪
        if (currentTaskId) {
          setTimeout(() => {
            stopProgressTracking(currentTaskId);
            clearProgress(currentTaskId);
          }, 2000); // 延迟2秒清理，让用户看到完成状态
        }
        
        form.resetFields();
        setVideoInfo(null);
      } else {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          console.log('无法解析错误响应为JSON:', e);
        }
        console.error('下载失败详情:', errorMessage);
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('下载请求错误:', error);
      
      let userMessage = '视频下载过程中出现错误';
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        userMessage = '无法连接到服务器，请检查网络连接或服务器状态';
      } else if (error.message) {
        userMessage = error.message;
      }
      
      notification.error({
        message: '下载失败',
        description: userMessage,
        duration: 8,
      });
      
      // 停止进度跟踪
      if (currentTaskId) {
        stopProgressTracking(currentTaskId);
        clearProgress(currentTaskId);
      }
    } finally {
      setDownloadLoading(false);
      setCurrentTaskId(null);
    }
  };

  // 取消下载
  const handleCancelDownload = async (taskId: string) => {
    Modal.confirm({
      title: '确认取消',
      content: '确定要取消这个下载任务吗？',
      onOk: async () => {
        try {
          await cancelDownload(taskId);
          notification.success({
            message: '取消成功',
            description: '下载任务已取消',
          });
        } catch (error: any) {
          notification.error({
            message: '取消失败',
            description: error.message || '无法取消任务',
          });
        }
      },
    });
  };

  // 批量下载处理
  const handleBatchDownload = async (values: any) => {
    if (!batchUrls.trim()) {
      notification.warning({
        message: '请输入URL',
        description: '请输入要下载的视频链接',
      });
      return;
    }

    setBatchLoading(true);
    const urls = batchUrls
      .split('\n')
      .map(url => url.trim())
      .filter(url => url.length > 0);

    if (urls.length === 0) {
      notification.warning({
        message: '无有效URL',
        description: '请输入有效的视频链接',
      });
      setBatchLoading(false);
      return;
    }

    let successCount = 0;
    let failedCount = 0;

    try {
      // 并发限制：同时最多处理2个下载以避免服务器过载
      const concurrencyLimit = 2;
      for (let i = 0; i < urls.length; i += concurrencyLimit) {
        const batch = urls.slice(i, i + concurrencyLimit);
        
        const promises = batch.map(async (url) => {
          try {
            // 使用流式下载而不是创建记录
            const response = await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.STREAM), {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                url,
                quality: values.quality || 'best',
                format: values.format || 'mp4',
                audio_only: values.audio_only || false,
                subtitle: values.subtitle || false
              }),
            });

            if (response.ok) {
              // 获取文件名
              const contentDisposition = response.headers.get('Content-Disposition');
              let filename = `${new URL(url).hostname}-video.${values.format || 'mp4'}`;
              
              if (contentDisposition) {
                const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
                if (utf8Match) {
                  try {
                    filename = decodeURIComponent(utf8Match[1]);
                  } catch (e) {
                    const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
                    if (simpleMatch) filename = simpleMatch[1];
                  }
                } else {
                  const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
                  if (simpleMatch) filename = simpleMatch[1];
                }
              }

              // 创建下载
              const blob = await response.blob();
              const downloadUrl = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = downloadUrl;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              window.URL.revokeObjectURL(downloadUrl);

              // 创建记录
              try {
                await fetch(buildApiUrl(API_ENDPOINTS.DOWNLOADS.RECORD), {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    url,
                    quality: values.quality || 'best',
                    format: values.format || 'mp4',
                    audio_only: values.audio_only || false,
                    subtitle: values.subtitle || false,
                    output_filename: filename
                  }),
                });
              } catch (recordError) {
                console.warn('批量下载记录创建失败:', recordError);
              }

              successCount++;
              return { url, success: true };
            } else {
              throw new Error(`HTTP ${response.status}`);
            }
          } catch (error: any) {
            failedCount++;
            console.error(`批量下载失败 ${url}:`, error);
            return { url, success: false, error: error.message };
          }
        });

        await Promise.all(promises);
        
        // 添加延迟避免服务器过载
        if (i + concurrencyLimit < urls.length) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

      // 显示结果
      const message = successCount > 0 ? '批量下载完成' : '批量下载失败';
      const description = `成功下载: ${successCount} 个，失败: ${failedCount} 个`;
      
      if (successCount > 0) {
        notification.success({ message, description });
        setBatchUrls('');
        batchForm.resetFields();
        setShowBatchDownload(false);
      } else {
        notification.error({ message, description });
      }

    } catch (error: any) {
      notification.error({
        message: '批量下载失败',
        description: error.message || '发生未知错误',
      });
    } finally {
      setBatchLoading(false);
    }
  };

  // 格式化文件大小
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化时间
  const formatTime = (seconds: number): string => {
    if (!seconds || seconds <= 0) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
      pending: { color: 'blue', text: '等待中', icon: <LoadingOutlined /> },
      processing: { color: 'orange', text: '处理中', icon: <LoadingOutlined /> },
      downloading: { color: 'cyan', text: '下载中', icon: <DownloadOutlined /> },
      completed: { color: 'green', text: '已完成', icon: <CheckCircleOutlined /> },
      failed: { color: 'red', text: '失败', icon: <ExclamationCircleOutlined /> },
      cancelled: { color: 'default', text: '已取消', icon: <StopOutlined /> }
    };
    
    const statusInfo = statusMap[status] || { color: 'default', text: status, icon: null };
    return (
      <Tag color={statusInfo.color} icon={statusInfo.icon}>
        {statusInfo.text}
      </Tag>
    );
  };

  // 获取任务显示标题
  const getTaskTitle = (task: any) => {
    // 如果有标题，直接返回
    if (task.title && task.title.trim() && task.title !== 'best' && task.title !== 'worst') {
      return task.title;
    }
    
    // 如果有文件路径，从路径中提取文件名
    if (task.file_path) {
      const fileName = task.file_path.split('/').pop() || task.file_path.split('\\').pop();
      if (fileName && fileName !== 'undefined') {
        // 移除扩展名
        return fileName.replace(/\.[^/.]+$/, '');
      }
    }
    
    // 尝试从URL中提取更好的名称
    if (task.url) {
      try {
        const url = new URL(task.url);
        if (url.hostname.includes('youtube.com') || url.hostname.includes('youtu.be')) {
          return 'YouTube视频';
        } else if (url.hostname.includes('bilibili.com')) {
          return 'Bilibili视频';
        } else if (url.hostname.includes('douyin.com')) {
          return '抖音视频';
        } else {
          return `${url.hostname}视频`;
        }
      } catch {
        // URL解析失败，继续使用默认名称
      }
    }
    
    // 默认显示
    return '下载任务';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2} className="page-title">
          <YoutubeOutlined /> AVD 全能视频下载器
        </Title>
        <Paragraph className="page-description">
          支持多平台视频下载，包括 YouTube、Bilibili、抖音等主流视频平台
        </Paragraph>
      </div>

      {/* 下载表单 */}
      <Card className="download-form-container" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => {
            // 检查是否已获取视频信息
            if (!videoInfo) {
              notification.warning({
                message: '请先获取视频信息',
                description: '点击"获取信息"按钮获取视频详细信息后再开始下载',
                duration: 4,
              });
              return;
            }
            
            // 直接使用流式下载
            handleStreamDownload(values);
          }}
          initialValues={{
            quality: 'best',
            format: 'mp4',
            audio_only: false,
            subtitle: false,
            subtitle_language: 'auto'
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <Form.Item
                name="url"
                label="视频链接"
                rules={[
                  { required: true, message: '请输入视频链接' },
                  { type: 'url', message: '请输入有效的URL' }
                ]}
              >
                <Input.Search
                  placeholder="请输入视频链接 (支持 YouTube, Bilibili, 抖音等)"
                  enterButton={
                    <Button icon={<LinkOutlined />} loading={loadingInfo}>
                      获取信息
                    </Button>
                  }
                  size="large"
                  onSearch={handleGetVideoInfo}
                  onChange={() => {
                    // URL变化时清除之前的视频信息
                    if (videoInfo) {
                      setVideoInfo(null);
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col xs={12} lg={4}>
              <Form.Item name="quality" label="视频质量">
                <Select placeholder="选择质量">
                  <Option value="best">最佳质量</Option>
                  <Option value="720p">720p</Option>
                  <Option value="480p">480p</Option>
                  <Option value="360p">360p</Option>
                  <Option value="worst">最低质量</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={12} lg={4}>
              <Form.Item name="format" label="格式">
                <Select placeholder="选择格式">
                  <Option value="mp4">MP4</Option>
                  <Option value="mkv">MKV</Option>
                  <Option value="webm">WebM</Option>
                  <Option value="avi">AVI</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[16, 16]} align="middle">
            <Col>
              <Form.Item name="audio_only" valuePropName="checked">
                <Switch checkedChildren="仅音频" unCheckedChildren="视频+音频" />
              </Form.Item>
            </Col>
            <Col>
              <Form.Item name="subtitle" valuePropName="checked">
                <Switch checkedChildren="下载字幕" unCheckedChildren="不下载字幕" />
              </Form.Item>
            </Col>

            <Col flex={1}>
              <Form.Item>
                <Button 
                  type="primary"
                  htmlType="submit"
                  loading={downloadLoading}
                  icon={<CloudDownloadOutlined />}
                  block
                  disabled={loadingInfo}
                >
                  {downloadLoading ? '下载中...' : videoInfo ? '开始下载' : '请先获取视频信息'}
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* 视频信息显示 */}
        {videoInfo && (
          <Card size="small" style={{ marginTop: 16, background: '#f0f9ff', border: '1px solid #1890ff' }}>
            <Row gutter={[16, 8]} align="middle">
              <Col span={2}>
                <CheckCircleOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
              </Col>
              <Col span={22}>
                <div style={{ marginBottom: 8 }}>
                  <Text strong style={{ color: '#1890ff', fontSize: '16px' }}>视频信息获取成功！</Text>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                    现在可以选择质量和格式后开始下载
                  </Text>
                </div>
                <Row gutter={[16, 8]}>
                  <Col span={24}>
                    <Text strong>📹 标题:</Text> <Text>{videoInfo.title}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>🏷️ 平台:</Text> {getPlatformTag(videoInfo.platform)}
                  </Col>
                  <Col span={12}>
                    <Text strong>⏱️ 时长:</Text> <Text>{formatTime(videoInfo.duration)}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>👤 上传者:</Text> <Text>{videoInfo.uploader}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>🎬 可用质量:</Text> <Text>{videoInfo.available_qualities?.join(', ') || '默认'}</Text>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card>
        )}

        {/* 操作提示 */}
        {loadingInfo && (
          <Card size="small" style={{ marginTop: 16, background: '#fff7e6', border: '1px solid #faad14' }}>
            <Row align="middle">
              <Col span={2}>
                <LoadingOutlined style={{ fontSize: '20px', color: '#faad14' }} />
              </Col>
              <Col span={22}>
                <Text style={{ color: '#fa8c16' }}>正在获取视频信息，请稍候...</Text>
              </Col>
            </Row>
          </Card>
        )}

        {(downloadLoading || (currentTaskId && progressData[currentTaskId])) && (
          <Card size="small" style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #52c41a' }}>
            {/* WebSocket连接状态 */}
            {!isConnected && (
              <Row align="middle" style={{ marginBottom: 8 }}>
                <Col span={24}>
                  <Alert
                    message="WebSocket连接断开，实时进度可能不准确"
                    type="warning"
                    showIcon
                  />
                </Col>
              </Row>
            )}
            
            {currentTaskId && progressData[currentTaskId] ? (
              <>
                {/* 实时进度显示 */}
                <Row align="middle" style={{ marginBottom: 8 }}>
                  <Col span={2}>
                    {progressData[currentTaskId].status === 'completed' ? (
                      <CheckCircleOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                    ) : progressData[currentTaskId].status === 'failed' ? (
                      <ExclamationCircleOutlined style={{ fontSize: '20px', color: '#ff4d4f' }} />
                    ) : (
                      <LoadingOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                    )}
                  </Col>
                  <Col span={22}>
                    <Text style={{ color: '#389e0d' }}>
                      {progressData[currentTaskId].status === 'preparing' && '正在准备下载...'}
                      {progressData[currentTaskId].status === 'downloading' && '正在下载'}
                      {progressData[currentTaskId].status === 'completed' && '下载完成'}
                      {progressData[currentTaskId].status === 'failed' && '下载失败'}
                    </Text>
                    {progressData[currentTaskId].filename && (
                      <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                        {progressData[currentTaskId].filename}
                      </Text>
                    )}
                  </Col>
                </Row>
                
                {/* 进度条 */}
                <Row style={{ marginBottom: 8 }}>
                  <Col span={24}>
                    <Progress
                      percent={Math.round(progressData[currentTaskId].progress || 0)}
                      status={
                        progressData[currentTaskId].status === 'failed' ? 'exception' :
                        progressData[currentTaskId].status === 'completed' ? 'success' : 'active'
                      }
                      strokeColor={
                        progressData[currentTaskId].status === 'completed' ? '#52c41a' :
                        progressData[currentTaskId].status === 'failed' ? '#ff4d4f' : '#1890ff'
                      }
                      showInfo={true}
                      format={(percent) => `${Math.round(percent || 0)}%`}
                    />
                  </Col>
                </Row>
                
                {/* 下载详细信息 */}
                {progressData[currentTaskId].status === 'downloading' && (
                  <Row gutter={[16, 8]}>
                    {progressData[currentTaskId].speed && (
                      <Col span={12}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          速度: {progressData[currentTaskId].speed}
                        </Text>
                      </Col>
                    )}
                    {progressData[currentTaskId].eta && (
                      <Col span={12}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          剩余: {progressData[currentTaskId].eta}
                        </Text>
                      </Col>
                    )}
                    {progressData[currentTaskId].downloaded && progressData[currentTaskId].total && (
                      <Col span={24}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          进度: {progressData[currentTaskId].downloaded} / {progressData[currentTaskId].total}
                        </Text>
                      </Col>
                    )}
                  </Row>
                )}
                
                {/* 错误信息 */}
                {progressData[currentTaskId].status === 'failed' && progressData[currentTaskId].error && (
                  <Row style={{ marginTop: 8 }}>
                    <Col span={24}>
                      <Alert
                        message="下载失败"
                        description={progressData[currentTaskId].error}
                        type="error"
                        showIcon
                      />
                    </Col>
                  </Row>
                )}
              </>
            ) : (
              /* 默认加载状态 */
              <Row align="middle">
                <Col span={2}>
                  <LoadingOutlined style={{ fontSize: '20px', color: '#52c41a' }} />
                </Col>
                <Col span={22}>
                  <Text style={{ color: '#389e0d' }}>正在准备下载，请保持网络连接...</Text>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                    文件将直接下载到您的设备
                  </Text>
                </Col>
              </Row>
            )}
          </Card>
        )}
      </Card>

      {/* 批量下载功能 */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button 
              type={showBatchDownload ? "default" : "primary"}
              icon={<AppstoreAddOutlined />}
              onClick={() => setShowBatchDownload(!showBatchDownload)}
            >
              {showBatchDownload ? '单个下载' : '批量下载'}
            </Button>
            <Text type="secondary">
              {showBatchDownload ? '批量下载模式：可同时下载多个视频' : '单个下载模式'}
            </Text>
          </Space>
        </div>

        {showBatchDownload && (
          <Form
            form={batchForm}
            layout="vertical"
            onFinish={handleBatchDownload}
            initialValues={{
              quality: 'best',
              format: 'mp4',
              audio_only: false,
              subtitle: false,
              subtitle_language: 'auto'
            }}
          >
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Form.Item
                  label="视频链接列表"
                  extra="每行一个视频链接，支持多个平台的视频"
                >
                  <TextArea
                    placeholder={`请输入视频链接，每行一个，例如：
https://www.youtube.com/watch?v=example1
https://www.bilibili.com/video/BV1example2
https://www.douyin.com/video/example3`}
                    rows={6}
                    value={batchUrls}
                    onChange={(e) => setBatchUrls(e.target.value)}
                    style={{ fontFamily: 'monospace' }}
                  />
                </Form.Item>
              </Col>
              
              <Col xs={12} lg={6}>
                <Form.Item name="quality" label="视频质量">
                  <Select placeholder="选择质量">
                    <Option value="best">最佳质量</Option>
                    <Option value="720p">720p</Option>
                    <Option value="480p">480p</Option>
                    <Option value="360p">360p</Option>
                    <Option value="worst">最低质量</Option>
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={12} lg={6}>
                <Form.Item name="format" label="格式">
                  <Select placeholder="选择格式">
                    <Option value="mp4">MP4</Option>
                    <Option value="mkv">MKV</Option>
                    <Option value="webm">WebM</Option>
                    <Option value="avi">AVI</Option>
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={12} lg={6}>
                <Form.Item name="audio_only" valuePropName="checked">
                  <Switch checkedChildren="仅音频" unCheckedChildren="视频+音频" />
                </Form.Item>
              </Col>
              
              <Col xs={12} lg={6}>
                <Form.Item name="subtitle" valuePropName="checked">
                  <Switch checkedChildren="下载字幕" unCheckedChildren="不下载字幕" />
                </Form.Item>
              </Col>
            </Row>

            <Row justify="space-between" align="middle">
              <Col>
                <Text type="secondary">
                  📊 {batchUrls.split('\n').filter(url => url.trim()).length} 个链接
                </Text>
              </Col>
              <Col>
                <Space>
                  <Button onClick={() => setBatchUrls('')} disabled={batchLoading}>
                    清空
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    loading={batchLoading}
                    disabled={!batchUrls.trim()}
                    icon={<DownloadOutlined />}
                  >
                    开始批量下载
                  </Button>
                </Space>
              </Col>
            </Row>
          </Form>
        )}
      </Card>

      {/* 下载任务列表已移除 */}
    </div>
  );
};

// 加载组件
const LoadingSpinner: React.FC<{ tip?: string }> = ({ tip = "加载中..." }) => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '200px',
    flexDirection: 'column'
  }}>
    <Spin size="large" />
    <Text type="secondary" style={{ marginTop: 16 }}>
      {tip}
    </Text>
  </div>
);

// 错误边界组件
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('页面组件错误:', error, errorInfo);
    
    // 可以在这里添加错误日志上报
    notification.error({
      message: '页面加载错误',
      description: '页面组件发生错误，请刷新页面重试',
      duration: 0
    });
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ 
          padding: '50px', 
          textAlign: 'center',
          background: '#fff',
          margin: '20px',
          borderRadius: '8px'
        }}>
          <Alert
            message="页面加载失败"
            description={
              <div>
                <p>页面组件发生错误，请尝试以下操作：</p>
                <ul style={{ textAlign: 'left', margin: '10px 0' }}>
                  <li>刷新页面</li>
                  <li>清除浏览器缓存</li>
                  <li>检查网络连接</li>
                </ul>
                <Button 
                  type="primary" 
                  onClick={() => window.location.reload()}
                  style={{ marginTop: 10 }}
                >
                  刷新页面
                </Button>
              </div>
            }
            type="error"
            showIcon
          />
        </div>
      );
    }

    return this.props.children;
  }
}

// 主应用组件
const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState('download');
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      if (mobile) {
        setMobileMenuVisible(false); // 移动端默认隐藏侧边栏
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const menuItems = [
    {
      key: 'download',
      icon: <DownloadOutlined />,
      label: '视频下载',
    },
    {
      key: 'subtitle',
      icon: <FileTextOutlined />,
      label: '字幕处理',
    },
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: '下载历史',
    },
    {
      key: 'system',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      key: 'logs',
      icon: <FileTextOutlined />,
      label: '日志管理',
    },
    {
      key: 'systeminfo',
      icon: <InfoCircleOutlined />,
      label: '系统信息',
    },
  ];

  const renderContent = () => {
    const pageComponents = {
      download: <DownloadPage />,
      subtitle: (
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner tip="加载字幕处理页面..." />}>
            <SubtitlePage />
          </Suspense>
        </ErrorBoundary>
      ),

      history: (
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner tip="加载下载历史..." />}>
            <HistoryPage />
          </Suspense>
        </ErrorBoundary>
      ),
      system: (
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner tip="加载系统设置..." />}>
            <SystemPage />
          </Suspense>
        </ErrorBoundary>
      ),
      logs: (
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner tip="加载日志管理..." />}>
            <LogsPage />
          </Suspense>
        </ErrorBoundary>
      ),
      systeminfo: (
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner tip="加载系统信息..." />}>
            <SystemInfoPage />
          </Suspense>
        </ErrorBoundary>
      ),
    };

    return pageComponents[currentPage] || pageComponents.download;
  };

  return (
    <Layout className="app-layout">
      {/* 移动端汉堡菜单按钮 */}
      {isMobile && (
        <Button
          className="mobile-menu-button"
          icon={<MenuOutlined />}
          onClick={() => setMobileMenuVisible(true)}
        />
      )}
      
      {/* 移动端遮罩层 */}
      {isMobile && mobileMenuVisible && (
        <div 
          className="mobile-overlay show"
          onClick={() => setMobileMenuVisible(false)}
        />
      )}
      
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        width={240}
        className={`app-sider ${isMobile && mobileMenuVisible ? 'mobile-show' : ''}`}
      >
        <div style={{ 
          padding: '16px', 
          textAlign: 'center', 
          borderBottom: '1px solid #f0f0f0',
          background: '#1890ff',
          color: 'white'
        }}>
          <Title level={collapsed ? 5 : 4} style={{ color: 'white', margin: 0 }}>
            {collapsed ? 'AVD' : 'AVD Web'}
          </Title>
          {!collapsed && (
            <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px' }}>
              全能视频下载器
            </Text>
          )}
        </div>
        
        <Menu
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems}
          onClick={({ key }) => {
            setCurrentPage(key);
            if (isMobile) {
              setMobileMenuVisible(false); // 移动端选择菜单后自动关闭
            }
          }}
          style={{ borderRight: 0, paddingTop: 8 }}
        />
      </Sider>

      <Layout className={`app-main-layout ${collapsed ? 'collapsed' : ''}`}>
        <Header className="app-header">
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                {menuItems.find(item => item.key === currentPage)?.label}
              </Title>
            </Col>
            <Col>
              <Space>
                {/* 版本号已移除 */}
              </Space>
            </Col>
          </Row>
        </Header>
        
        <Content className="app-content" style={{ 
          background: '#f5f5f5'
        }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App; 