import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  Modal,
  Tabs,
  InputNumber,
  Alert,
  Spin,
  Table,
  Tag
} from 'antd';
import {
  SettingOutlined,
  DownloadOutlined,
  BgColorsOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  ClearOutlined,
  ReloadOutlined,
  FileTextOutlined,
  FolderOpenOutlined
} from '@ant-design/icons';
import { useSystemSettings, SystemSettings } from '../hooks/useSystemSettings';
import { useErrorHandler } from '../hooks/useErrorHandler';
import NetworkSettings from './NetworkSettings';
import ModelManagement from './ModelManagement';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// 格式化字节数
const formatBytes = (bytes: number | undefined) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  if (isNaN(bytes)) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  // 确保不超出数组范围
  const sizeIndex = Math.min(i, sizes.length - 1);
  const formattedValue = (bytes / Math.pow(k, sizeIndex)).toFixed(2);
  
  return `${formattedValue} ${sizes[sizeIndex]}`;
};

const SystemPage: React.FC = () => {
  const [downloadForm] = Form.useForm();
  const [storageForm] = Form.useForm();
  const [serverForm] = Form.useForm();
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupDays, setCleanupDays] = useState(7);

  const {
    settings,
    systemInfo: systemInfoFromHook,
    taskStats,
    systemConfig,
    // logsInfo,  // 暂时移除，避免404错误
    loading: loadingFromHook,
    saving,
    saveSettings,
    cleanupSystem,
    // loadLogsInfo,  // 暂时移除，避免404错误
    refreshData
  } = useSystemSettings();

  const { showSuccess, showInfo, handleBusinessError } = useErrorHandler();

  // 初始化表单数据
  useEffect(() => {
    if (settings) {
      downloadForm.setFieldsValue({
        max_concurrent_downloads: settings.max_concurrent_downloads,
        max_file_size_mb: settings.max_file_size_mb,
        default_quality: settings.default_quality,
        default_format: settings.default_format,
      });

      storageForm.setFieldsValue({
        files_path: settings.files_path,
        auto_cleanup_days: settings.auto_cleanup_days,
      });

      serverForm.setFieldsValue({
        server_host: settings.server_host,
        backend_port: settings.backend_port,
        frontend_port: settings.frontend_port,
      });
    }
  }, [settings, downloadForm, storageForm, serverForm]);

  // 处理下载设置保存
  const handleDownloadSettingsSave = async (values: any) => {
    if (!settings) return;
    
    const newSettings: SystemSettings = {
      ...settings,
      ...values
    };
    
    await saveSettings(newSettings);
  };

  // 处理存储设置保存
  const handleStorageSettingsSave = async (values: any) => {
    if (!settings) return;
    
    const newSettings: SystemSettings = {
      ...settings,
      ...values
    };
    
    await saveSettings(newSettings);
  };

  // 处理服务器设置保存
  const handleServerSettingsSave = async (values: any) => {
    if (!settings) return;
    
    const newSettings: SystemSettings = {
      ...settings,
      ...values
    };
    
    // 检查端口是否发生变化
    const backendPortChanged = settings.backend_port !== values.backend_port;
    const frontendPortChanged = settings.frontend_port !== values.frontend_port;
    
    const success = await saveSettings(newSettings);
    
    if (success && (backendPortChanged || frontendPortChanged)) {
      let message = '端口设置已更新';
      let description = '';
      
      if (backendPortChanged && frontendPortChanged) {
        description = '前端和后端端口都已更改，需要分别重启前端和后端服务才能生效。';
      } else if (backendPortChanged) {
        description = '后端端口已更改，需要重启后端服务才能生效。';
      } else if (frontendPortChanged) {
        description = '前端端口已更改，需要重启前端开发服务器才能生效。';
      }
      
      Modal.info({
        title: message,
        content: description,
        okText: '我知道了',
      });
    }
  };

  // 系统清理
  const handleCleanup = (type: string) => {
    Modal.confirm({
      title: '确认清理',
      content: `确定要清理${type}吗？此操作将删除${cleanupDays}天前的文件。`,
      onOk: async () => {
        setCleanupLoading(true);
        try {
          const options = {
            days_old: cleanupDays,
            cleanup_temp: type === '临时文件',
            cleanup_downloads: type === '下载文件',
            cleanup_logs: type === '日志文件'
          };
          
          await cleanupSystem(options);
          await refreshData();
        } finally {
          setCleanupLoading(false);
        }
      },
    });
  };

  if (loadingFromHook) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <Spin size="large" tip="正在加载系统设置..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '0 0 20px' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SettingOutlined /> 系统设置
      </Title>

      <Tabs 
        defaultActiveKey="download" 
        size="large"
        tabBarStyle={{ marginBottom: '16px' }}
        items={[
          {
            key: 'download',
            label: (
              <span>
                <DownloadOutlined />
                <span className="tab-label">下载设置</span>
              </span>
            ),
            children: (
              <Card>
                <Form
                  form={downloadForm}
                  layout="vertical"
                  onFinish={handleDownloadSettingsSave}
                >
                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="max_concurrent_downloads" 
                        label="最大并发下载数"
                        tooltip="同时进行的最大下载任务数"
                        rules={[{ required: true, type: 'number', min: 1, max: 10 }]}
                      >
                        <InputNumber min={1} max={10} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="max_file_size_mb" 
                        label="最大文件大小(MB)"
                        tooltip="允许下载的最大文件大小"
                        rules={[{ required: true, type: 'number', min: 100, max: 10240 }]}
                      >
                        <InputNumber min={100} max={10240} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="default_quality" 
                        label="默认视频质量"
                        tooltip="新建下载任务时的默认质量选择"
                        rules={[{ required: true }]}
                      >
                        <Select>
                          {systemConfig?.quality_options && Object.entries(systemConfig.quality_options).map(([key, value]) => (
                            <Option key={key} value={key}>{value}</Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="default_format" 
                        label="默认格式"
                        tooltip="新建下载任务时的默认格式选择"
                        rules={[{ required: true }]}
                      >
                        <Select>
                          {systemConfig?.supported_formats?.map((format) => (
                            <Option key={format} value={format}>{format.toUpperCase()}</Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Divider />
                  
                  <Button type="primary" htmlType="submit" loading={saving}>
                    保存下载设置
                  </Button>
                </Form>
              </Card>
            )
          },
          {
            key: 'storage',
            label: (
              <span>
                <DatabaseOutlined />
                <span className="tab-label">存储设置</span>
              </span>
            ),
            children: (
              <Card>
                <Form
                  form={storageForm}
                  layout="vertical"
                  onFinish={handleStorageSettingsSave}
                >
                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={24} md={24} lg={24} xl={24}>
                      <Form.Item 
                        name="files_path" 
                        label="文件目录"
                        tooltip="文件存储目录"
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="/path/to/files" />
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="auto_cleanup_days" 
                        label="自动清理天数"
                        tooltip="自动删除多少天前的文件，0表示不自动清理"
                        rules={[{ required: true, type: 'number', min: 0, max: 365 }]}
                      >
                        <InputNumber min={0} max={365} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                  
                  <Divider />
                  
                  <Button type="primary" htmlType="submit" loading={saving}>
                    保存存储设置
                  </Button>
                </Form>
              </Card>
            )
          },
          {
            key: 'network',
            label: (
              <span>
                <BgColorsOutlined />
                <span className="tab-label">网络设置</span>
              </span>
            ),
            children: <NetworkSettings onSave={refreshData} />
          },
          {
            key: 'models',
            label: (
              <span>
                <DatabaseOutlined />
                <span className="tab-label">模型管理</span>
              </span>
            ),
            children: <ModelManagement />
          },
          {
            key: 'server',
            label: (
              <span>
                <FileTextOutlined />
                <span className="tab-label">服务器设置</span>
              </span>
            ),
            children: (
              <Card>
                {/* 当前服务器状态 */}
                {systemInfoFromHook && (
                  <Alert
                    message="当前服务器状态"
                    description={
                      <div>
                        <p><strong>运行地址:</strong> {systemInfoFromHook.environment?.host || '0.0.0.0'}:{systemInfoFromHook.environment?.port || 8000}</p>
                        <p><strong>进程ID:</strong> {systemInfoFromHook.processes?.current_pid}</p>
                        <p><strong>内存使用:</strong> {formatBytes(systemInfoFromHook.processes?.current_memory)}</p>
                        <p><strong>版本:</strong> {systemInfoFromHook.environment?.version || 'N/A'}</p>
                      </div>
                    }
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                )}

                <Form
                  form={serverForm}
                  layout="vertical"
                  onFinish={handleServerSettingsSave}
                >
                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="server_host" 
                        label="服务器地址"
                        tooltip="服务器绑定的主机地址，0.0.0.0表示监听所有网卡"
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="0.0.0.0" />
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="backend_port" 
                        label="后端端口"
                        tooltip="服务器监听的端口号，范围: 1-65535"
                        rules={[
                          { required: true, message: '请输入端口号' },
                          { type: 'number', min: 1, max: 65535, message: '端口号必须在1-65535之间' }
                        ]}
                      >
                        <InputNumber 
                          min={1} 
                          max={65535} 
                          placeholder="8000"
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                    
                    <Col xs={24} sm={24} md={12} lg={12} xl={12}>
                      <Form.Item 
                        name="frontend_port" 
                        label="前端端口"
                        tooltip="前端开发服务器端口号，范围: 1-65535"
                        rules={[
                          { required: true, message: '请输入前端端口号' },
                          { type: 'number', min: 1, max: 65535, message: '端口号必须在1-65535之间' }
                        ]}
                      >
                        <InputNumber 
                          min={1} 
                          max={65535} 
                          placeholder="3000"
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Alert
                    message="重要提示"
                    description="更改端口设置后，需要手动重启后端服务才能生效。请确保新端口未被其他程序占用。"
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Divider />
                  
                  <Space>
                    <Button type="primary" htmlType="submit" loading={saving}>
                      保存服务器设置
                    </Button>
                    <Button onClick={() => refreshData()}>
                      <ReloadOutlined /> 刷新状态
                    </Button>
                  </Space>
                </Form>
              </Card>
            )
          }
        ]}
      />
    </div>
  );
};

export default SystemPage; 