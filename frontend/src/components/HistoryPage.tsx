import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Typography,
  Tag,
  notification,
  Modal,
  Tooltip,
  Row,
  Col,
  Statistic,
  Empty
} from 'antd';
import { getApiBaseUrl, buildApiUrl, API_ENDPOINTS } from '../config/api';
import {
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  YoutubeOutlined,
  LinkOutlined,
  CloudDownloadOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Paragraph, Text } = Typography;
const { Option } = Select;
const { confirm } = Modal;

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



// 下载记录接口定义
interface DownloadRecord {
  id: string;
  url: string;
  title?: string;
  description?: string;
  thumbnail?: string;
  uploader?: string;
  platform?: string;
  quality: string;
  format: string;
  audio_only: boolean;
  subtitle: boolean;
  status: 'recorded' | 'completed';
  created_at: string;
  completed_at?: string;
}

// 字幕记录接口定义
interface SubtitleRecord {
  id: string;
  video_url?: string;
  video_file_path?: string;
  subtitle_file_path?: string;
  language: string;
  model_size: string;
  translate_to?: string;
  source_language?: string;
  target_language?: string;
  task_type: string;
  status: 'recorded' | 'completed';
  created_at: string;
  completed_at?: string;
}

const HistoryPage: React.FC = () => {
  const [downloadRecords, setDownloadRecords] = useState<DownloadRecord[]>([]);
  const [subtitleRecords, setSubtitleRecords] = useState<SubtitleRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'downloads' | 'subtitles'>('downloads');
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  
  // 分页
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // 加载数据
  useEffect(() => {
    loadRecords();
  }, [selectedTab, statusFilter, pagination.current, pagination.pageSize]);

  const loadRecords = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: pagination.current.toString(),
        size: pagination.pageSize.toString(),
      });
      
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const endpoint = selectedTab === 'downloads' 
        ? `${API_ENDPOINTS.DOWNLOADS.RECORDS}?${params}`
        : `${API_ENDPOINTS.SUBTITLES.RECORDS}?${params}`;
      
      const response = await fetch(buildApiUrl(endpoint));
      
      if (response.ok) {
        const data = await response.json();
        
        if (selectedTab === 'downloads') {
          setDownloadRecords(data.records || []);
        } else {
          setSubtitleRecords(data.records || []);
        }
        
        setPagination(prev => ({
          ...prev,
          total: data.total || 0
        }));
      } else {
        throw new Error('记录加载失败');
      }
    } catch (error: any) {
      notification.error({
        message: '记录加载失败',
        description: `${selectedTab === 'downloads' ? '视频下载' : '字幕处理'}记录加载失败`,
      });
    } finally {
      setLoading(false);
    }
  };

  // 删除记录
  const handleDeleteRecord = (recordId: string, type: 'downloads' | 'subtitles') => {
    confirm({
      title: '确认删除',
      content: '确定要删除这条记录吗？此操作无法撤销。',
      onOk: async () => {
        try {
          const endpoint = type === 'downloads' 
            ? `${API_ENDPOINTS.DOWNLOADS.RECORDS}/${recordId}`
            : `${API_ENDPOINTS.SUBTITLES.RECORDS}/${recordId}`;
          
          const response = await fetch(buildApiUrl(endpoint), {
            method: 'DELETE',
          });
          
          if (response.ok) {
            notification.success({
              message: '删除成功',
              description: '记录已成功删除',
            });
            loadRecords();
          } else {
            throw new Error('删除失败');
          }
        } catch (error: any) {
          notification.error({
            message: '删除失败',
            description: error.message || '无法删除记录',
          });
        }
      },
    });
  };

  // 流式处理函数
  const handleStreamProcess = async (operation: string, params: any, type: 'video' | 'subtitle') => {
    try {
      const endpoint = type === 'video' 
        ? buildApiUrl(API_ENDPOINTS.DOWNLOADS.STREAM)
        : buildApiUrl(API_ENDPOINTS.SUBTITLES.STREAM);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation,
          ...params
        }),
      });

      if (response.ok) {
        // 获取文件名（支持UTF-8编码）
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = type === 'video' ? 'video.mp4' : 'subtitle.srt';
        
        // 如果是下载操作且有参数，尝试构建更好的默认文件名
        if (type === 'video' && params && params.url) {
          try {
            // 从downloadRecords中找到匹配的记录
            const matchingRecord = downloadRecords.find(record => record.url === params.url);
            if (matchingRecord && matchingRecord.title) {
              const safeTitle = matchingRecord.title.replace(/[<>:"/\\|?*]/g, '').trim();
              filename = `${safeTitle}.${params.format || 'mp4'}`;
            }
          } catch (e) {
            console.warn('构建默认文件名失败:', e);
          }
        }
        
        if (contentDisposition) {
          // 尝试匹配UTF-8编码的文件名
          const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
          if (utf8Match) {
            try {
              filename = decodeURIComponent(utf8Match[1]);
            } catch (e) {
              console.warn('UTF-8解码失败:', e);
              // 如果UTF-8解码失败，回退到简单匹配
              const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
              if (simpleMatch) {
                filename = simpleMatch[1];
              }
            }
          } else {
            // 如果没有UTF-8编码，使用简单匹配
            const simpleMatch = contentDisposition.match(/filename="([^"]+)"/);
            if (simpleMatch) {
              filename = simpleMatch[1];
            }
          }
        }

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
          message: '处理完成',
          description: '文件已下载到本地',
        });
      } else {
        const error = await response.json();
        throw new Error(error.detail || '处理失败');
      }
    } catch (error: any) {
      notification.error({
        message: '处理失败',
        description: error.message || '流式处理过程中出现错误',
      });
    }
  };

  // 流式下载视频
  const handleStreamDownload = async (record: DownloadRecord) => {
    await handleStreamProcess('download', {
      url: record.url,
      quality: record.quality,
      format: record.format,
      audio_only: record.audio_only,
      subtitle: record.subtitle
    }, 'video');
  };

  // 流式处理字幕
  const handleStreamSubtitle = async (record: SubtitleRecord) => {
    // 尝试获取有意义的标题信息
    let originalTitle = '';
    
    // 从视频URL或文件路径提取标题
    if (record.video_url) {
      try {
        // 尝试从下载记录中找到对应的视频，优先使用本地文件名
        const matchingDownload = downloadRecords.find(dr => dr.url === record.video_url);
        if (matchingDownload) {
          // 检查是否存在本地文件，如果存在则提取文件名
          if (matchingDownload.id) {
            // 尝试构建本地文件名（基于下载ID和格式）
            const localFileName = `${matchingDownload.id}.${matchingDownload.format || 'mp4'}`;
            // 从标题中提取有意义的部分，但使用本地文件标识
            const cleanTitle = matchingDownload.title ? 
              matchingDownload.title.replace(/[<>:"/\\|?*]/g, '').trim() : 
              '下载视频';
            originalTitle = cleanTitle;
            console.log(`使用本地文件对应的标题: ${originalTitle}`);
          } else {
            originalTitle = matchingDownload.title || '视频';
          }
        } else {
          // 如果找不到匹配的下载记录，从URL中提取域名作为标题
          const url = new URL(record.video_url);
          originalTitle = url.hostname.replace('www.', '') + '视频';
        }
      } catch (e) {
        originalTitle = '视频';
      }
    } else if (record.video_file_path) {
      // 从文件路径提取文件名作为标题，这是最准确的本地文件名
      const fileName = record.video_file_path.split('/').pop() || record.video_file_path.split('\\').pop();
      if (fileName) {
        // 移除扩展名，这就是本地保存的文件名
        originalTitle = fileName.replace(/\.[^/.]+$/, '');
        console.log(`使用本地文件名: ${originalTitle}`);
      } else {
        originalTitle = '视频';
      }
    } else if (record.subtitle_file_path) {
      // 对于字幕翻译，尝试从文件名中提取有意义的信息
      const fileName = record.subtitle_file_path.split('/').pop() || record.subtitle_file_path.split('\\').pop();
      if (fileName) {
        let baseName = fileName.replace(/\.[^/.]+$/, ''); // 移除扩展名
        
        // 如果是UUID格式，使用默认标题
        const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
        if (uuidPattern.test(baseName)) {
          // 检查是否有其他有用信息
          if (baseName.includes('_')) {
            const parts = baseName.split('_');
            for (const part of parts) {
              if (!uuidPattern.test(part) && part.length > 3 && part !== 'subtitles') {
                originalTitle = part;
                break;
              }
            }
          }
          if (!originalTitle) {
            originalTitle = '字幕';
          }
        } else {
          originalTitle = baseName;
        }
      } else {
        originalTitle = '字幕';
      }
    }

    // 添加调试信息
    console.log(`字幕处理请求 - 原始标题: ${originalTitle}, 记录类型: ${record.video_url ? 'URL' : record.video_file_path ? 'FILE' : 'SUBTITLE'}`);

    if (record.video_url) {
      await handleStreamProcess('generate', {
        video_url: record.video_url,
        language: record.language,
        ai_model_size: record.model_size,
        translate_to: record.translate_to,
        original_title: originalTitle,  // 传递处理后的标题
        prefer_local_filename: true     // 新增参数，指示优先使用本地文件名
      }, 'subtitle');
    } else if (record.video_file_path) {
      await handleStreamProcess('generate', {
        video_file_path: record.video_file_path,
        language: record.language,
        ai_model_size: record.model_size,
        translate_to: record.translate_to,
        original_title: originalTitle,  // 传递处理后的标题
        prefer_local_filename: true     // 新增参数，指示优先使用本地文件名
      }, 'subtitle');
    } else if (record.subtitle_file_path && record.target_language) {
      await handleStreamProcess('translate', {
        subtitle_file_path: record.subtitle_file_path,
        source_language: record.source_language || 'auto',
        target_language: record.target_language,
        original_title: originalTitle,  // 传递处理后的标题
        prefer_local_filename: true     // 新增参数，指示优先使用本地文件名
      }, 'subtitle');
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      recorded: { color: 'blue', text: '已记录' },
      completed: { color: 'green', text: '已完成' },
      pending: { color: 'orange', text: '等待中' },
      processing: { color: 'cyan', text: '处理中' },
      failed: { color: 'red', text: '失败' },
      cancelled: { color: 'default', text: '已取消' }
    };
    
    const statusInfo = statusMap[status] || { color: 'default', text: status };
    return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
  };

  // 下载记录表格列
  const downloadColumns: ColumnsType<DownloadRecord> = [
    {
      title: '视频信息',
      dataIndex: 'title',
      key: 'title',
      ellipsis: { showTitle: false },
      render: (text: string, record: DownloadRecord) => (
        <Tooltip title={record.url}>
          <div>
            <Space>
              <Text strong>{text || (() => {
                try {
                  return new URL(record.url).hostname;
                } catch {
                  return '未知标题';
                }
              })()}</Text>
              {record.platform && getPlatformTag(record.platform)}
            </Space>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.quality} · {record.format.toUpperCase()}
              {record.audio_only && ' · 仅音频'}
              {record.subtitle && ' · 含字幕'}
            </Text>
          </div>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => (
        <div>
          <div>{new Date(date).toLocaleDateString()}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {new Date(date).toLocaleTimeString()}
          </Text>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_, record: DownloadRecord) => (
        <Space>
          <Tooltip title="流式下载">
            <Button 
              type="primary" 
              size="small" 
              icon={<CloudDownloadOutlined />}
              onClick={() => handleStreamDownload(record)}
            />
          </Tooltip>
          <Tooltip title="删除记录">
            <Button 
              danger 
              size="small" 
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteRecord(record.id, 'downloads')}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 字幕记录表格列
  const subtitleColumns: ColumnsType<SubtitleRecord> = [
    {
      title: '任务信息',
      key: 'info',
      render: (_, record: SubtitleRecord) => (
        <div>
          <Text strong>
            {record.task_type === 'translate' ? '字幕翻译' : 
             record.task_type === 'burn' ? '字幕烧录' : 'AI字幕生成'}
          </Text>
          <br />
          {record.video_url && (
            <Text type="secondary" ellipsis style={{ fontSize: '12px' }}>
              URL: {record.video_url.length > 50 ? record.video_url.substring(0, 50) + '...' : record.video_url}
            </Text>
          )}
          {record.video_file_path && (
            <Text type="secondary" ellipsis style={{ fontSize: '12px' }}>
              文件: {record.video_file_path.split('/').pop()}
            </Text>
          )}
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.language} · {record.model_size?.toUpperCase()}
            {record.translate_to && ` → ${record.translate_to}`}
            {record.target_language && ` → ${record.target_language}`}
          </Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => (
        <div>
          <div>{new Date(date).toLocaleDateString()}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {new Date(date).toLocaleTimeString()}
          </Text>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_, record: SubtitleRecord) => (
        <Space>
          <Tooltip title="流式处理">
            <Button 
              type="primary" 
              size="small" 
              icon={<CloudDownloadOutlined />}
              onClick={() => handleStreamSubtitle(record)}
            />
          </Tooltip>
          <Tooltip title="删除记录">
            <Button 
              danger 
              size="small" 
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteRecord(record.id, 'subtitles')}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 过滤数据
  const getFilteredData = () => {
    const data = selectedTab === 'downloads' ? downloadRecords : subtitleRecords;
    
    return data.filter(record => {
      // 状态过滤
      if (statusFilter !== 'all' && record.status !== statusFilter) {
        return false;
      }
      
      // 平台过滤（仅下载记录）
      if (selectedTab === 'downloads' && platformFilter !== 'all') {
        const downloadRecord = record as DownloadRecord;
        if (downloadRecord.platform?.toLowerCase() !== platformFilter.toLowerCase()) {
          return false;
        }
      }
      
      // 搜索过滤
      if (searchText) {
        const searchLower = searchText.toLowerCase();
        let recordText = '';
        
        if (selectedTab === 'downloads') {
          const downloadRecord = record as DownloadRecord;
          recordText = `${downloadRecord.title || ''} ${downloadRecord.url || ''}`.toLowerCase();
        } else {
          const subtitleRecord = record as SubtitleRecord;
          recordText = `${subtitleRecord.video_url || ''} ${subtitleRecord.language || ''}`.toLowerCase();
        }
        
        if (!recordText.includes(searchLower)) {
          return false;
        }
      }
      
      return true;
    });
  };

  // 统计信息
  const getStats = () => {
    const data = selectedTab === 'downloads' ? downloadRecords : subtitleRecords;
    const recorded = data.filter(t => t.status === 'recorded').length;
    const completed = data.filter(t => t.status === 'completed').length;
    
    return { total: data.length, recorded, completed };
  };

  const stats = getStats();

  // 清空所有记录
  const handleClearAllRecords = async () => {
    confirm({
      title: '确认清空',
      content: `确定要清空所有${selectedTab === 'downloads' ? '下载' : '字幕'}记录吗？此操作不可恢复。`,
      onOk: async () => {
        try {
          const data = selectedTab === 'downloads' ? downloadRecords : subtitleRecords;
          if (data.length === 0) return;
          
          const recordIds = data.map(record => record.id);
          
          // 显示进度提示
          notification.info({
            message: '正在清空记录',
            description: `正在删除 ${recordIds.length} 条记录，请稍候...`,
            duration: 3, // 3秒后自动关闭
          });
          
          let deletedCount = 0;
          let failedCount = 0;
          
          // 逐个删除记录（更可靠的方法）
          for (const recordId of recordIds) {
            try {
              const endpoint = selectedTab === 'downloads' 
                ? `/api/v1/downloads/records/${recordId}`
                : `/api/v1/subtitles/files/records/${recordId}`;
              
              const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
                method: 'DELETE',
              });

              if (response.ok) {
                deletedCount++;
              } else {
                failedCount++;
              }
            } catch (error) {
              failedCount++;
            }
          }
          
          if (deletedCount > 0) {
            notification.success({
              message: '清空完成',
              description: `成功删除 ${deletedCount} 条记录${failedCount > 0 ? `，${failedCount} 条记录删除失败` : ''}`,
            });
            loadRecords();
          } else {
            notification.error({
              message: '清空失败',
              description: '没有记录被删除，请检查网络连接',
            });
          }
        } catch (error: any) {
          notification.error({
            message: '清空失败',
            description: error.message || '无法清空记录',
          });
        }
      },
    });
  };

  return (
    <div style={{ padding: '20px' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Title level={2}>
              <HistoryOutlined /> 历史记录
            </Title>
            <Paragraph>
              查看和管理视频下载与字幕处理的历史记录，支持重新执行流式处理操作。
            </Paragraph>
          </Card>
        </Col>

        {/* 统计卡片 */}
        <Col span={24}>
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="总记录数"
                  value={stats.total}
                  prefix={<EyeOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="已记录"
                  value={stats.recorded}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="已完成"
                  value={stats.completed}
                  prefix={<DownloadOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
          </Row>
        </Col>

        {/* 筛选工具栏 */}
        <Col span={24}>
          <Card>
            <Row gutter={[16, 16]} align="middle">
              <Col>
                <Space>
                  <Button 
                    type={selectedTab === 'downloads' ? 'primary' : 'default'}
                    icon={<DownloadOutlined />}
                    onClick={() => setSelectedTab('downloads')}
                  >
                    下载记录
                  </Button>
                  <Button 
                    type={selectedTab === 'subtitles' ? 'primary' : 'default'}
                    icon={<FileTextOutlined />}
                    onClick={() => setSelectedTab('subtitles')}
                  >
                    字幕记录
                  </Button>
                </Space>
              </Col>
              
              <Col flex={1}>
                <Row gutter={[8, 8]} justify="end">
                  <Col>
                    <Input
                      placeholder="搜索记录..."
                      prefix={<SearchOutlined />}
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                      style={{ width: 200 }}
                    />
                  </Col>
                  <Col>
                    <Select
                      value={statusFilter}
                      onChange={setStatusFilter}
                      style={{ width: 120 }}
                      placeholder="状态筛选"
                    >
                      <Option value="all">全部状态</Option>
                      <Option value="recorded">已记录</Option>
                      <Option value="completed">已完成</Option>
                    </Select>
                  </Col>
                  {selectedTab === 'downloads' && (
                    <Col>
                      <Select
                        value={platformFilter}
                        onChange={setPlatformFilter}
                        style={{ width: 140 }}
                        placeholder="平台筛选"
                      >
                        <Option value="all">全部平台</Option>
                        <Option value="youtube">YouTube</Option>
                        <Option value="bilibili">Bilibili</Option>
                        <Option value="douyin">抖音</Option>
                        <Option value="weixin">微信视频号</Option>
                        <Option value="xiaohongshu">小红书</Option>
                        <Option value="qq">腾讯视频</Option>
                        <Option value="youku">优酷</Option>
                        <Option value="iqiyi">爱奇艺</Option>
                      </Select>
                    </Col>
                  )}
                  <Col>
                    <Button 
                      icon={<ReloadOutlined />}
                      onClick={loadRecords}
                      loading={loading}
                    >
                      刷新
                    </Button>
                  </Col>
                  <Col>
                    <Button 
                      danger
                      icon={<DeleteOutlined />}
                      onClick={handleClearAllRecords}
                      disabled={(selectedTab === 'downloads' ? downloadRecords : subtitleRecords).length === 0}
                    >
                      清空记录
                    </Button>
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 记录表格 */}
        <Col span={24}>
          <Card>
            {getFilteredData().length === 0 && !loading ? (
              <Empty
                description={
                  searchText || statusFilter !== 'all' || platformFilter !== 'all'
                    ? '没有找到符合条件的记录'
                    : `暂无${selectedTab === 'downloads' ? '下载' : '字幕'}记录`
                }
                style={{ padding: '40px 0' }}
              />
            ) : (
              <Table
                dataSource={getFilteredData()}
                columns={selectedTab === 'downloads' ? downloadColumns : subtitleColumns as any}
                loading={loading}
                rowKey="id"
                pagination={{
                  ...pagination,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) => `第 ${range[0]}-${range[1]} 项，共 ${total} 项`,
                  onChange: (page, pageSize) => {
                    setPagination(prev => ({
                      ...prev,
                      current: page,
                      pageSize: pageSize!
                    }));
                  },
                }}
                scroll={{ x: 800 }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HistoryPage; 