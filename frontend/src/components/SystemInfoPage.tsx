import React, { useState, useEffect } from 'react';
import {
  Card,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Tag,
  Button,
  Tooltip,
  Descriptions,
  Alert,
  Spin,
  Divider
} from 'antd';
import {
  InfoCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  WifiOutlined,
  ApiOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useSystemSettings } from '../hooks/useSystemSettings';
import { getApiBaseUrl, buildApiUrl, API_ENDPOINTS } from '../config/api';

const { Title, Text } = Typography;

// 格式化字节数
const formatBytes = (bytes: number | undefined) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  if (isNaN(bytes)) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  const sizeIndex = Math.min(i, sizes.length - 1);
  const formattedValue = (bytes / Math.pow(k, sizeIndex)).toFixed(2);
  
  return `${formattedValue} ${sizes[sizeIndex]}`;
};



const SystemInfoPage: React.FC = () => {
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [connectionTest, setConnectionTest] = useState<{
    api: boolean | null;
    websocket: boolean | null;
    testing: boolean;
  }>({
    api: null,
    websocket: null,
    testing: false
  });

  const { taskStats, refreshData } = useSystemSettings();

  // 测试API连接
  const testApiConnection = async () => {
    try {
      const response = await fetch(buildApiUrl('/health'), {
        method: 'GET',
        timeout: 5000
      } as any);
      
      if (response.ok) {
        const data = await response.json();
        return data.status === 'healthy';
      }
      return false;
    } catch (error) {
      console.error('API连接测试失败:', error);
      return false;
    }
  };

  // 测试WebSocket连接
  const testWebSocketConnection = async (): Promise<boolean> => {
    return new Promise((resolve) => {
      try {
        const wsUrl = getApiBaseUrl().replace('http', 'ws') + '/ws';
        const ws = new WebSocket(wsUrl);
        
        const timeout = setTimeout(() => {
          ws.close();
          resolve(false);
        }, 5000);
        
        ws.onopen = () => {
          clearTimeout(timeout);
          ws.close();
          resolve(true);
        };
        
        ws.onerror = () => {
          clearTimeout(timeout);
          resolve(false);
        };
      } catch (error) {
        console.error('WebSocket连接测试失败:', error);
        resolve(false);
      }
    });
  };

  // 运行连接测试
  const runConnectionTest = async () => {
    setConnectionTest(prev => ({ ...prev, testing: true }));
    
    const [apiResult, wsResult] = await Promise.all([
      testApiConnection(),
      testWebSocketConnection()
    ]);
    
    setConnectionTest({
      api: apiResult,
      websocket: wsResult,
      testing: false
    });
  };

  // 获取系统信息
  const fetchSystemInfo = async () => {
    setLoading(true);
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.SYSTEM.INFO));
      if (response.ok) {
        const data = await response.json();
        setSystemInfo(data);
      }
    } catch (error) {
      console.error('获取系统信息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemInfo();
    runConnectionTest();
    refreshData();
  }, []);

  const getStatusTag = (status: boolean | null) => {
    if (status === null) return <Tag>未测试</Tag>;
    return status ? 
      <Tag color="green" icon={<CheckCircleOutlined />}>正常</Tag> : 
      <Tag color="red" icon={<ExclamationCircleOutlined />}>失败</Tag>;
  };

  const refreshAll = async () => {
    await Promise.all([
      fetchSystemInfo(),
      runConnectionTest(),
      refreshData()
    ]);
  };

  return (
    <div style={{ padding: '0 0 20px' }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>
          <InfoCircleOutlined /> 系统信息
        </Title>
        <Button 
          icon={<ReloadOutlined />}
          onClick={refreshAll}
          loading={loading || connectionTest.testing}
        >
          刷新信息
        </Button>
      </div>

      <Row gutter={[24, 24]}>
        {/* 连接测试 */}
        <Col span={24}>
          <Card title="网络连接测试">
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Alert
                  message="网络诊断"
                  description={`当前访问地址: ${window.location.origin} | API地址: ${getApiBaseUrl()}`}
                  type="info"
                  style={{ marginBottom: 16 }}
                />
              </Col>
              <Col span={12}>
                <Descriptions column={1} bordered>
                  <Descriptions.Item label="API连接">
                    {getStatusTag(connectionTest.api)}
                  </Descriptions.Item>
                  <Descriptions.Item label="WebSocket连接">
                    {getStatusTag(connectionTest.websocket)}
                  </Descriptions.Item>
                </Descriptions>
              </Col>
              <Col span={12}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button 
                    type="primary" 
                    icon={<WifiOutlined />}
                    loading={connectionTest.testing}
                    onClick={runConnectionTest}
                    block
                  >
                    重新测试连接
                  </Button>
                  <Button 
                    icon={<ApiOutlined />}
                    onClick={() => window.open(`${getApiBaseUrl()}/docs`, '_blank')}
                    block
                  >
                    查看API文档
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 系统状态 */}
        <Col span={24}>
          <Card title="系统状态" loading={loading}>
            {systemInfo && (
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Statistic title="CPU核心数" value={systemInfo?.cpu?.count || 0} />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="内存总量" 
                    value={formatBytes(systemInfo?.memory?.total)} 
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="可用内存" 
                    value={formatBytes(systemInfo?.memory?.available)} 
                  />
                </Col>
                <Col span={6}>
                  <Statistic 
                    title="磁盘剩余空间" 
                    value={formatBytes(systemInfo?.disk?.free)} 
                  />
                </Col>
              </Row>
            )}
          </Card>
        </Col>

        {/* 任务统计 */}
        {taskStats && (
          <Col span={24}>
            <Card title="任务统计">
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Statistic title="总下载任务" value={taskStats.total_downloads} />
                </Col>
                <Col span={6}>
                  <Statistic title="活跃下载" value={taskStats.active_downloads} />
                </Col>
                <Col span={6}>
                  <Statistic title="完成下载" value={taskStats.completed_downloads} />
                </Col>
                <Col span={6}>
                  <Statistic title="失败下载" value={taskStats.failed_downloads} />
                </Col>
              </Row>
            </Card>
          </Col>
        )}

        {/* 系统详细信息 */}
        <Col span={24}>
          <Card title="系统详细信息" loading={loading}>
            {systemInfo ? (
              <>
                <Row gutter={[16, 8]}>
                  <Col span={6}><Text strong>应用版本:</Text></Col>
                  <Col span={18}>{systemInfo?.environment?.app_name || 'AVD'} v{systemInfo?.environment?.version || '2.0'}</Col>
                  
                  <Col span={6}><Text strong>平台:</Text></Col>
                  <Col span={18}>{systemInfo?.platform || '未知'}</Col>
                  
                  <Col span={6}><Text strong>Python版本:</Text></Col>
                  <Col span={18}>{systemInfo?.python_version || '未知'}</Col>
                  
                  <Col span={6}><Text strong>服务地址:</Text></Col>
                  <Col span={18}>{systemInfo?.environment?.host || 'localhost'}:{systemInfo?.environment?.port || 8000}</Col>
                  
                  <Col span={6}><Text strong>调试模式:</Text></Col>
                  <Col span={18}>
                    <Tag color={systemInfo?.environment?.debug ? 'orange' : 'green'}>
                      {systemInfo?.environment?.debug ? '开启' : '关闭'}
                    </Tag>
                  </Col>
                  
                  <Col span={6}><Text strong>网络状态:</Text></Col>
                  <Col span={18}>
                    <Tag color={navigator.onLine ? 'green' : 'red'}>
                      {navigator.onLine ? '在线' : '离线'}
                    </Tag>
                  </Col>
                </Row>
                
                <Divider />
                
                <Title level={5}>网络流量统计</Title>
                <Row gutter={[16, 16]}>
                  <Col span={6}>
                    <Statistic 
                      title="发送流量" 
                      value={formatBytes(systemInfo?.network?.bytes_sent)} 
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="接收流量" 
                      value={formatBytes(systemInfo?.network?.bytes_recv)} 
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="发送包数" 
                      value={systemInfo?.network?.packets_sent?.toLocaleString() || '0'} 
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="接收包数" 
                      value={systemInfo?.network?.packets_recv?.toLocaleString() || '0'} 
                    />
                  </Col>
                </Row>
              </>
            ) : (
              <Alert message="无法获取系统信息，请检查网络连接" type="warning" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemInfoPage;
