import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  Modal,
  Table,
  Tag,
  Progress,
  Alert,
  Spin,
  Statistic,
  Descriptions,
  Tooltip,
  Popconfirm,
  message
} from 'antd';
import {
  CloudDownloadOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ClearOutlined,
  ThunderboltOutlined,
  HddOutlined,
  CheckCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useErrorHandler } from '../hooks/useErrorHandler';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

interface ModelInfo {
  device: string;
  auto_device_selection: boolean;
  current_model: string;
  default_model: string;
  cached_models: string[];
  current_cache_size: number;
  whisper_device: string;
  compute_type: string;
  model_path: string;
  available_models: string[];
  quality_mode: string;
  cuda_device_count?: number;
  cuda_current_device?: number;
  cuda_memory_allocated?: number;
  cuda_memory_cached?: number;
  gpu_name?: string;
  gpu_memory_total?: number;
  error?: string;
}

interface ModelDetails {
  name: string;
  size: string;
  memory: string;
  recommended: boolean;
}

interface AvailableModelsResponse {
  success: boolean;
  models: string[];
  model_details: Record<string, ModelDetails>;
  default: string;
  current: string;
}

interface CacheStatus {
  cached_models: string[];
  current_model: string | null;
  cache_count: number;
  estimated_memory_mb: number;
}

const ModelManagement: React.FC = () => {
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModelsResponse | null>(null);
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  const { showSuccess, showError, handleBusinessError } = useErrorHandler();

  // 获取模型信息
  const fetchModelInfo = async () => {
    try {
      const response = await axios.get('/api/v1/system/models/info');
      setModelInfo(response.data);
    } catch (error) {
      console.error('获取模型信息失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    }
  };

  // 获取可用模型列表
  const fetchAvailableModels = async () => {
    try {
      const response = await axios.get('/api/v1/system/models/available');
      setAvailableModels(response.data);
    } catch (error) {
      console.error('获取可用模型失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    }
  };

  // 获取缓存状态
  const fetchCacheStatus = async () => {
    try {
      const response = await axios.get('/api/v1/system/models/cache/status');
      setCacheStatus(response.data);
    } catch (error) {
      console.error('获取缓存状态失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    }
  };

  // 初始化数据
  const initializeData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchModelInfo(),
        fetchAvailableModels(),
        fetchCacheStatus()
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initializeData();
  }, []);

  // 加载模型
  const handleLoadModel = async (modelSize: string) => {
    setActionLoading(`load-${modelSize}`);
    try {
      const response = await axios.post(`/api/v1/system/models/load/${modelSize}`);
      if (response.data.success) {
        showSuccess(response.data.message);
        await Promise.all([fetchModelInfo(), fetchCacheStatus()]);
      } else {
        showError('加载模型失败', '模型加载操作失败');
      }
    } catch (error) {
      console.error('加载模型失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 卸载模型
  const handleUnloadModel = async (modelSize: string) => {
    setActionLoading(`unload-${modelSize}`);
    try {
      const response = await axios.delete(`/api/v1/system/models/cache/${modelSize}`);
      if (response.data.success) {
        showSuccess(response.data.message);
        await Promise.all([fetchModelInfo(), fetchCacheStatus()]);
      } else {
        showError('卸载模型失败', response.data.message || '模型卸载操作失败');
      }
    } catch (error) {
      console.error('卸载模型失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 清空缓存
  const handleClearCache = async () => {
    setActionLoading('clear-cache');
    try {
      const response = await axios.delete('/api/v1/system/models/cache');
      if (response.data.success) {
        showSuccess(response.data.message);
        await Promise.all([fetchModelInfo(), fetchCacheStatus()]);
      } else {
        showError('清空缓存失败', '缓存清理操作失败');
      }
    } catch (error) {
      console.error('清空缓存失败:', error);
      console.error('Error:', error);
      showError('操作失败', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 刷新数据
  const handleRefresh = async () => {
    await initializeData();
    showSuccess('数据已刷新');
  };

  // 格式化内存大小
  const formatMemory = (gb: number | undefined) => {
    if (!gb) return 'N/A';
    return `${gb.toFixed(2)} GB`;
  };

  // 获取设备图标
  const getDeviceIcon = (device: string) => {
    return device === 'cuda' ? <ThunderboltOutlined style={{ color: '#52c41a' }} /> : <HddOutlined />;
  };

  // 获取模型状态标签
  const getModelStatusTag = (modelSize: string) => {
    const isLoaded = cacheStatus?.cached_models.includes(modelSize);
    const isCurrent = modelInfo?.current_model === modelSize;
    
    if (isCurrent) {
      return <Tag color="green" icon={<CheckCircleOutlined />}>当前使用</Tag>;
    } else if (isLoaded) {
      return <Tag color="blue">已缓存</Tag>;
    } else {
      return <Tag color="default">未加载</Tag>;
    }
  };

  // 构建模型表格数据
  const modelTableData = availableModels?.models.map(model => {
    const details = availableModels.model_details[model];
    return {
      key: model,
      model,
      name: details?.name || model,
      size: details?.size || 'N/A',
      memory: details?.memory || 'N/A',
      recommended: details?.recommended || false,
      status: getModelStatusTag(model)
    };
  }) || [];

  const modelTableColumns = [
    {
      title: '模型名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <Space>
          <strong>{text}</strong>
          {record.recommended && <Tag color="gold">推荐</Tag>}
        </Space>
      )
    },
    {
      title: '模型ID',
      dataIndex: 'model',
      key: 'model',
      render: (text: string) => <Text code>{text}</Text>
    },
    {
      title: '质量等级',
      dataIndex: 'size',
      key: 'size'
    },
    {
      title: '内存占用',
      dataIndex: 'memory',
      key: 'memory'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status'
    },
    {
      title: '操作',
      key: 'actions',
      render: (text: any, record: any) => {
        const isLoaded = cacheStatus?.cached_models.includes(record.model);
        const isCurrent = modelInfo?.current_model === record.model;
        
        return (
          <Space>
            {!isLoaded && (
              <Button
                type="primary"
                size="small"
                icon={<CloudDownloadOutlined />}
                loading={actionLoading === `load-${record.model}`}
                onClick={() => handleLoadModel(record.model)}
              >
                加载
              </Button>
            )}
            {isLoaded && !isCurrent && (
              <Popconfirm
                title="确定要卸载这个模型吗？"
                onConfirm={() => handleUnloadModel(record.model)}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  type="default"
                  size="small"
                  icon={<DeleteOutlined />}
                  loading={actionLoading === `unload-${record.model}`}
                  danger
                >
                  卸载
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      }
    }
  ];

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <Spin size="large" tip="正在加载模型管理..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '0 0 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          <DatabaseOutlined /> AI模型管理
        </Title>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
          刷新
        </Button>
      </div>

      {/* 系统信息卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="计算设备"
              value={modelInfo?.device || 'N/A'}
              prefix={getDeviceIcon(modelInfo?.device || 'cpu')}
            />
            {modelInfo?.gpu_name && (
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {modelInfo.gpu_name}
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="当前模型"
              value={modelInfo?.current_model || '未加载'}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="缓存大小"
              value={`${cacheStatus?.estimated_memory_mb || 0} MB`}
              suffix={`/ ${cacheStatus?.cache_count || 0} 模型`}
            />
          </Card>
        </Col>
      </Row>

      {/* GPU信息 */}
      {modelInfo?.device === 'cuda' && (
        <Card title="GPU信息" style={{ marginBottom: 24 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label="GPU名称">{modelInfo.gpu_name}</Descriptions.Item>
            <Descriptions.Item label="设备数量">{modelInfo.cuda_device_count}</Descriptions.Item>
            <Descriptions.Item label="总内存">{formatMemory(modelInfo.gpu_memory_total)}</Descriptions.Item>
            <Descriptions.Item label="已分配内存">{formatMemory(modelInfo.cuda_memory_allocated)}</Descriptions.Item>
            <Descriptions.Item label="已缓存内存">{formatMemory(modelInfo.cuda_memory_cached)}</Descriptions.Item>
            <Descriptions.Item label="计算类型">{modelInfo.compute_type}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* 模型列表 */}
      <Card 
        title="可用模型" 
        extra={
          <Space>
            <Popconfirm
              title="确定要清空所有模型缓存吗？"
              onConfirm={handleClearCache}
              okText="确定"
              cancelText="取消"
            >
              <Button
                icon={<ClearOutlined />}
                loading={actionLoading === 'clear-cache'}
                disabled={!cacheStatus?.cache_count}
              >
                清空缓存
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        <Alert
          message="模型使用说明"
          description="首次加载模型时会自动下载，请确保网络连接正常。推荐使用 large-v3 模型以获得最佳识别效果。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        
        <Table
          columns={modelTableColumns}
          dataSource={modelTableData}
          size="small"
          pagination={false}
        />
      </Card>

      {/* 缓存信息 */}
      {cacheStatus && cacheStatus.cache_count > 0 && (
        <Card title="缓存状态" style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>已缓存模型: </Text>
              <Space wrap>
                {cacheStatus.cached_models.map(model => (
                  <Tag key={model} color={model === modelInfo?.current_model ? 'green' : 'blue'}>
                    {model}
                  </Tag>
                ))}
              </Space>
            </div>
            <div>
              <Text strong>预计内存使用: </Text>
              <Text>{cacheStatus.estimated_memory_mb} MB</Text>
            </div>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default ModelManagement;