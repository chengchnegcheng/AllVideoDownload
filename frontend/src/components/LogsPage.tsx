import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Alert,
  Spin,
  Tag,
  InputNumber,
  Tabs,
  Input,
  Tooltip,
  Divider
} from 'antd';
import {
  SettingOutlined,
  FileTextOutlined,
  ReloadOutlined,
  EyeOutlined,
  SearchOutlined,
  ClearOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  SaveOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useSystemSettings, SystemSettings } from '../hooks/useSystemSettings';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { getApiBaseUrl, buildApiUrl } from '../config/api';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

// 日志条目接口
interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

// 系统日志配置组件
const SystemLogConfig: React.FC = () => {
  const [logForm] = Form.useForm();

  const {
    settings,
    systemConfig,
    loading,
    saving,
    saveSettings,
    refreshData
  } = useSystemSettings();

  const { showSuccess, showInfo, handleBusinessError } = useErrorHandler();

  // 初始化表单数据
  useEffect(() => {
    if (settings) {
      logForm.setFieldsValue({
        log_level: settings.log_level,
        log_retention_days: settings.log_retention_days,
      });
    }
  }, [settings, logForm]);

  // 处理日志设置保存
  const handleSaveSettings = async (values: any) => {
    if (!settings) return;
    
    const newSettings: SystemSettings = {
      ...settings,
      ...values
    };
    
    try {
    await saveSettings(newSettings);
      showSuccess('日志配置已保存', '新的日志配置将在系统重启后生效');
    } catch (error) {
      handleBusinessError(error, '保存日志配置失败');
    }
  };

  // 重置表单
  const handleReset = () => {
    if (settings) {
      logForm.setFieldsValue({
        log_level: settings.log_level,
        log_retention_days: settings.log_retention_days,
      });
      showInfo('表单已重置', '已恢复到当前保存的配置');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <Spin size="large" tip="正在加载日志配置..." />
      </div>
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 配置说明 */}
      <Alert
        message="系统日志配置说明"
        description={
          <div>
            <Paragraph style={{ marginBottom: 12 }}>
              <Text strong>系统日志级别</Text>：控制系统向日志文件中记录什么级别的信息，级别越高记录的信息越少。
            </Paragraph>
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li><Text strong>DEBUG</Text>：记录所有信息（包括调试信息）</li>
                  <li><Text strong>INFO</Text>：记录一般信息及以上级别</li>
                  <li><Text strong>WARNING</Text>：仅记录警告及以上级别</li>
                </ul>
              </Col>
              <Col span={12}>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li><Text strong>ERROR</Text>：仅记录错误及以上级别</li>
                  <li><Text strong>CRITICAL</Text>：仅记录严重错误</li>
                </ul>
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Space>
              <InfoCircleOutlined style={{ color: '#faad14' }} />
              <Text type="warning">修改系统日志级别后需要重启服务才能完全生效</Text>
            </Space>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 日志配置表单 */}
      <Card 
        title={
          <Space>
            <SettingOutlined />
            日志记录配置
          </Space>
        }
        extra={
          <Button 
            icon={<ReloadOutlined />} 
            onClick={refreshData}
            loading={loading}
          >
            刷新配置
          </Button>
        }
      >
        <Form
          form={logForm}
          layout="vertical"
          onFinish={handleSaveSettings}
          size="large"
        >
          <Row gutter={[24, 24]}>
            <Col lg={12} md={24}>
              <Form.Item 
                name="log_level" 
                label={
                  <Space>
                    <Text strong>系统日志记录级别</Text>
                    <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  </Space>
                }
                tooltip="决定系统向日志文件中记录什么级别的信息，级别越高记录的信息越少"
                rules={[{ required: true, message: '请选择日志级别' }]}
              >
                <Select 
                  placeholder="选择日志记录级别"
                  style={{ height: '48px' }}
                >
                  {systemConfig?.log_levels && Object.entries(systemConfig.log_levels).map(([key, value]) => (
                    <Option key={key} value={key}>
                      <strong>{key.toUpperCase()}</strong> - {value}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            
            <Col lg={12} md={24}>
              <Form.Item 
                name="log_retention_days" 
                label={
                  <Space>
                    <Text strong>日志文件保留天数</Text>
                    <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  </Space>
                }
                tooltip="系统自动清理多少天前的日志文件，范围：1-365天"
                rules={[
                  { required: true, message: '请输入保留天数' },
                  { type: 'number', min: 1, max: 365, message: '保留天数必须在1-365之间' }
                ]}
              >
                <InputNumber 
                  min={1} 
                  max={365} 
                  style={{ width: '100%', height: '48px' }}
                  placeholder="输入保留天数 (1-365)"
                  addonAfter="天"
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 当前配置状态 */}
          {settings && (
            <Alert
              message="当前配置状态"
              description={
                <Row gutter={[16, 8]}>
                  <Col span={12}>
                    <Text>日志级别：</Text>
                    <Text strong style={{ color: '#1890ff' }}>
                      {settings.log_level?.toUpperCase() || '未设置'}
                    </Text>
                  </Col>
                  <Col span={12}>
                    <Text>保留天数：</Text>
                    <Text strong style={{ color: '#1890ff' }}>
                      {settings.log_retention_days || '未设置'} 天
                    </Text>
                  </Col>
                </Row>
              }
              type="success"
              showIcon
              style={{ marginTop: 16, marginBottom: 24 }}
            />
          )}
          
          {/* 操作按钮 */}
          <Space size="large">
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={saving}
              icon={<SaveOutlined />}
              size="large"
            >
              保存日志配置
            </Button>
            <Button 
              onClick={handleReset}
              size="large"
            >
              重置表单
            </Button>
          </Space>
        </Form>
      </Card>

      {/* 配置生效说明 */}
      <Card 
        title="配置生效说明"
        size="small"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            message="配置生效时间"
            description={
              <div>
                <p>• <Text strong>日志级别</Text>：需要重启后端服务才能完全生效</p>
                <p>• <Text strong>保留天数</Text>：立即生效，系统会在下次清理时应用新设置</p>
              </div>
            }
            type="info"
            showIcon
          />
          
          <Alert
            message="重要提示"
            description={
              <div>
                <p>• DEBUG级别会产生大量日志，建议仅在开发调试时使用</p>
                <p>• 生产环境推荐使用INFO或WARNING级别</p>
                <p>• 日志文件会占用磁盘空间，请根据实际情况设置保留天数</p>
              </div>
            }
            type="warning"
            showIcon
          />
        </Space>
      </Card>
    </Space>
  );
};

// 实时日志查看器组件
const RealTimeLogViewer: React.FC = () => {
  // 日志查看相关状态
  const [selectedLogLevel, setSelectedLogLevel] = useState<string>('');
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [filteredEntries, setFilteredEntries] = useState<LogEntry[]>([]);
  const [loadingLogContent, setLoadingLogContent] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  const { systemConfig } = useSystemSettings();
  const { showSuccess, showInfo, handleBusinessError } = useErrorHandler();

  // 自动刷新效果
  useEffect(() => {
    if (autoRefresh && selectedLogLevel) {
      const interval = setInterval(() => {
        loadLogContent(selectedLogLevel);
      }, 5000); // 每5秒刷新一次
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, selectedLogLevel]);

  // 搜索过滤效果
  useEffect(() => {
    if (!searchKeyword.trim()) {
      setFilteredEntries(logEntries);
    } else {
      const filtered = logEntries.filter(entry =>
        entry.message.toLowerCase().includes(searchKeyword.toLowerCase()) ||
        entry.level.toLowerCase().includes(searchKeyword.toLowerCase())
      );
      setFilteredEntries(filtered);
    }
  }, [logEntries, searchKeyword]);

  // 处理日志级别变化
  const handleLogLevelChange = (level: string) => {
    setSelectedLogLevel(level);
    loadLogContent(level);
  };

  // 加载日志内容
  const loadLogContent = async (level: string) => {
    setLoadingLogContent(true);
    try {
      const response = await fetch(buildApiUrl(`/api/v1/system/logs/content?level=${level}`));
      
      if (response.ok) {
        const data = await response.json();
        setLogEntries(data.entries || []);
      } else {
        console.error('加载日志内容失败');
        setLogEntries([]);
        handleBusinessError('加载日志失败', '请检查网络连接或服务器状态');
      }
    } catch (error) {
      console.error('加载日志内容失败:', error);
      setLogEntries([]);
      handleBusinessError('加载日志失败', '网络请求失败');
    } finally {
      setLoadingLogContent(false);
    }
  };

  // 刷新日志内容
  const refreshLogContent = () => {
    if (selectedLogLevel) {
      loadLogContent(selectedLogLevel);
      showSuccess('日志已刷新', '已获取最新的日志内容');
    }
  };

  // 清空搜索
  const clearSearch = () => {
    setSearchKeyword('');
  };

  // 获取日志级别颜色
  const getLogLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'DEBUG':
        return '#108ee9';
      case 'INFO':
        return '#87d068';
      case 'WARNING':
        return '#f7b731';
      case 'ERROR':
        return '#ff6b6b';
      case 'CRITICAL':
        return '#ff4757';
      default:
        return '#fff';
    }
  };

  // 生成测试日志
  const generateTestLogs = async () => {
    try {
      const response = await fetch(buildApiUrl('/api/v1/system/logs/test'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        showSuccess('测试日志已生成', '包含所有级别的测试日志，请选择日志级别查看');
        // 如果当前已选择级别，自动刷新
        if (selectedLogLevel) {
          loadLogContent(selectedLogLevel);
        }
      } else {
        handleBusinessError('生成测试日志失败', '请检查服务器状态');
      }
    } catch (error) {
      console.error('生成测试日志失败:', error);
      handleBusinessError('生成测试日志失败', '网络请求失败');
    }
  };

  // 导出日志
  const exportLogs = () => {
    const logText = filteredEntries
      .map(entry => `[${entry.timestamp}] [${entry.level}] ${entry.message}`)
      .join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${selectedLogLevel}_${dayjs().format('YYYYMMDD_HHmmss')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess('日志已导出', '日志文件已下载到本地');
  };

  return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 使用说明 */}
          <Alert
        message="日志查看器使用说明"
            description={
              <div>
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <p><Text strong>查看过滤级别</Text>：选择要查看的日志级别，会显示该级别及更高级别的所有日志</p>
                <p><Text strong>实时刷新</Text>：开启后每5秒自动刷新日志内容</p>
              </Col>
              <Col span={12}>
                <p><Text strong>搜索过滤</Text>：可以按关键词搜索日志内容</p>
                <p><Text strong>导出功能</Text>：可以将当前显示的日志导出为文本文件</p>
              </Col>
            </Row>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          
      {/* 控制面板 */}
      <Card title="日志查看控制面板">
        <Row gutter={[16, 16]}>
          <Col lg={6} md={12} sm={24}>
              <div>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                <FileTextOutlined /> 选择查看级别：
              </Text>
                <Select 
                  style={{ width: '100%' }}
                  placeholder="选择要查看的日志级别"
                  value={selectedLogLevel || undefined}
                  onChange={handleLogLevelChange}
                  size="large"
                >
                  {systemConfig?.log_levels && Object.entries(systemConfig.log_levels).map(([key, value]) => (
                    <Option key={key} value={key}>
                      {key.toUpperCase()} - 显示{value}及以上
                    </Option>
                  ))}
                </Select>
              </div>
            </Col>
          
          <Col lg={6} md={12} sm={24}>
            <div>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                <SearchOutlined /> 搜索过滤：
              </Text>
              <Input
                placeholder="输入关键词搜索"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                size="large"
                suffix={
                  searchKeyword && (
                    <Button 
                      type="text" 
                      size="small" 
                      icon={<ClearOutlined />}
                      onClick={clearSearch}
                    />
                  )
                }
              />
            </div>
          </Col>
          
          <Col lg={6} md={12} sm={24}>
              {selectedLogLevel && (
                <div>
                <Text strong style={{ marginBottom: 8, display: 'block' }}>
                  📊 当前状态：
                </Text>
                <Space direction="vertical" size="small">
                  <Tag color="blue" style={{ fontSize: '13px', padding: '4px 8px' }}>
                      {selectedLogLevel.toUpperCase()}
                    </Tag>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    显示 {filteredEntries.length} / {logEntries.length} 条
                  </Text>
                  </Space>
                </div>
              )}
            </Col>
          
          <Col lg={6} md={12} sm={24}>
              <div>
              <Text strong style={{ marginBottom: 8, display: 'block' }}>
                🛠️ 操作功能：
              </Text>
              <Space wrap>
                <Tooltip title="生成包含各级别的测试日志">
                  <Button 
                    onClick={generateTestLogs}
                    icon={<span>🧪</span>}
                  >
                    生成测试
                  </Button>
                </Tooltip>
                <Tooltip title="手动刷新日志内容">
                  <Button 
                    icon={<ReloadOutlined />} 
                    onClick={refreshLogContent}
                    disabled={!selectedLogLevel}
                    loading={loadingLogContent}
                  >
                    刷新
                  </Button>
                </Tooltip>
                <Tooltip title={autoRefresh ? '关闭自动刷新' : '开启自动刷新（每5秒）'}>
                  <Button 
                    icon={<ClockCircleOutlined />}
                    type={autoRefresh ? 'primary' : 'default'}
                    onClick={() => setAutoRefresh(!autoRefresh)}
                    disabled={!selectedLogLevel}
                  >
                    {autoRefresh ? '停止' : '自动'}
                  </Button>
                </Tooltip>
                <Tooltip title="导出当前显示的日志">
                  <Button 
                    icon={<DownloadOutlined />}
                    onClick={exportLogs}
                    disabled={filteredEntries.length === 0}
                  >
                    导出
                  </Button>
                </Tooltip>
                </Space>
              </div>
            </Col>
          </Row>
      </Card>

      {/* 日志内容显示区域 */}
      <Card 
        title={
          <Space>
            <FileTextOutlined />
            日志内容显示
            {autoRefresh && <Tag color="green">自动刷新中</Tag>}
          </Space>
        }
        extra={
          selectedLogLevel && (
            <Space>
              <Text type="secondary">
                级别: {selectedLogLevel.toUpperCase()} | 
                总数: {logEntries.length} | 
                显示: {filteredEntries.length}
              </Text>
            </Space>
          )
        }
      >
          <div 
            style={{ 
            height: '500px', 
              border: '2px solid #d9d9d9', 
              borderRadius: '8px',
              padding: '16px',
              backgroundColor: '#1a1a1a',
              color: '#fff',
              fontFamily: 'Monaco, Consolas, "Courier New", monospace',
              fontSize: '13px',
              lineHeight: '1.6',
              overflow: 'auto',
              position: 'relative'
            }}
          >
            {!selectedLogLevel ? (
              <div style={{ 
                textAlign: 'center', 
              paddingTop: '150px', 
                color: '#888',
                fontSize: '16px'
              }}>
                <FileTextOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                <div style={{ marginBottom: '8px' }}>请先选择查看级别</div>
                <div style={{ fontSize: '12px' }}>
                  选择上方的日志级别来查看对应的日志内容
                </div>
              </div>
            ) : loadingLogContent ? (
            <div style={{ textAlign: 'center', paddingTop: '150px' }}>
                <Spin size="large" />
                <div style={{ marginTop: '16px', color: '#888' }}>正在加载日志内容...</div>
              </div>
          ) : filteredEntries.length > 0 ? (
              <>
                <div style={{ 
                  position: 'sticky', 
                  top: 0, 
                  backgroundColor: '#1a1a1a', 
                  padding: '8px 0',
                  borderBottom: '1px solid #333',
                  marginBottom: '8px'
                }}>
                  <Text style={{ color: '#888', fontSize: '12px' }}>
                  显示 {selectedLogLevel.toUpperCase()} 级别及以上的日志 | 
                  {searchKeyword && ` 搜索: "${searchKeyword}" | `}
                  共 {filteredEntries.length} 条记录
                  {autoRefresh && ' | 🔄 自动刷新中'}
                  </Text>
                </div>
              {filteredEntries.map((entry, index) => (
                  <div 
                    key={index} 
                    style={{ 
                      marginBottom: '6px',
                    padding: '6px 10px',
                      backgroundColor: entry.level === 'ERROR' || entry.level === 'CRITICAL' ? 'rgba(255, 107, 107, 0.1)' : 'transparent',
                      borderRadius: '4px',
                      borderLeft: `4px solid ${getLogLevelColor(entry.level)}`,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                    }}
                  >
                    <Text style={{ color: '#666', fontSize: '11px' }}>[{entry.timestamp}]</Text>
                    <Text style={{ 
                      color: getLogLevelColor(entry.level), 
                      marginLeft: '8px',
                      fontWeight: 'bold'
                    }}>
                      [{entry.level}]
                    </Text>
                    <Text style={{ color: '#e0e0e0', marginLeft: '8px' }}>
                      {entry.message}
                    </Text>
                  </div>
                ))}
              </>
            ) : (
              <div style={{ 
                textAlign: 'center', 
              paddingTop: '150px', 
                color: '#888',
                fontSize: '16px'
              }}>
                <div style={{ marginBottom: '16px' }}>📄</div>
                <div style={{ marginBottom: '8px' }}>
                {searchKeyword ? `没有找到包含 "${searchKeyword}" 的日志` : `暂无 ${selectedLogLevel.toUpperCase()} 级别的日志`}
                </div>
                <div style={{ fontSize: '12px', marginBottom: '16px' }}>
                {searchKeyword ? '尝试使用其他关键词搜索' : '当前日志文件中没有找到相关级别的日志记录'}
                </div>
              {!searchKeyword && (
                <Button 
                  type="primary" 
                  onClick={generateTestLogs}
                  icon={<span>🧪</span>}
                >
                  生成测试日志
                </Button>
              )}
              </div>
            )}
          </div>
        </Card>
      </Space>
  );
};

// 主日志管理页面
const LogsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('config');

  return (
    <div style={{ padding: '0 0 20px' }}>
      <div className="page-header">
        <Title level={2} className="page-title">
          <FileTextOutlined /> 日志管理
        </Title>
        <Paragraph className="page-description">
          系统日志配置与实时日志查看，统一管理日志相关功能
        </Paragraph>
      </div>

      <Card style={{ minHeight: '70vh' }}>
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          size="large"
          tabPosition="top"
        >
          <TabPane 
            tab={
              <Space>
                <SettingOutlined />
                系统日志配置
              </Space>
            } 
            key="config"
          >
            <SystemLogConfig />
          </TabPane>
          
          <TabPane 
            tab={
              <Space>
                <EyeOutlined />
                实时日志查看器
              </Space>
            } 
            key="viewer"
          >
            <RealTimeLogViewer />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default LogsPage; 