import React, { useState, useEffect } from 'react';
import { Card, Table, Tabs, Spin, message, Empty, Tag, Space, Select, DatePicker, Statistic, Row, Col, Button, Dropdown, Tooltip, Modal, Drawer, Descriptions, Timeline, Badge, Divider, Typography, List } from 'antd';
import { FireOutlined, RiseOutlined, FallOutlined, ThunderboltOutlined, ClockCircleOutlined, EyeOutlined, StarOutlined, MoreOutlined, FileTextOutlined, ApartmentOutlined, ExportOutlined, EyeInvisibleOutlined, BellOutlined, DownloadOutlined, RadarChartOutlined, StarFilled, DeleteOutlined } from '@ant-design/icons';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import apiClient from '../utils/api';
import dayjs from 'dayjs';

const { TabPane } = Tabs;
const { RangePicker } = DatePicker;
const { Option } = Select;

// 迷你趋势图组件
const Sparkline = ({ data, color, height = 24 }) => (
  <ResponsiveContainer width="100%" height={height}>
    <LineChart data={data.map((v, i) => ({ val: v }))}>
      <Line type="monotone" dataKey="val" stroke={color} strokeWidth={2} dot={false} />
    </LineChart>
  </ResponsiveContainer>
);

const TemporalAnalysisPage = () => {
  const [loading, setLoading] = useState(false);
  const [topMomentumEntities, setTopMomentumEntities] = useState([]);
  const [momentumStats, setMomentumStats] = useState({});
  const [timeRange, setTimeRange] = useState([dayjs().subtract(30, 'days'), dayjs()]);
  const [entityType, setEntityType] = useState('all');
  const [trendData, setTrendData] = useState([]);
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [hoveredRow, setHoveredRow] = useState(null);
  
  // 情报溯源相关状态
  const [sourceDrawerVisible, setSourceDrawerVisible] = useState(false);
  const [sourceDrawerData, setSourceDrawerData] = useState(null);
  const [sourceDrawerLoading, setSourceDrawerLoading] = useState(false);
  
  // AI简报相关状态
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [reportLoading, setReportLoading] = useState(false);
  const [currentEntity, setCurrentEntity] = useState(null);
  
  // 监控面板相关状态
  const [monitorDrawerVisible, setMonitorDrawerVisible] = useState(false);
  const [monitorList, setMonitorList] = useState([]);
  const [monitorData, setMonitorData] = useState(null); // 保存完整的监控数据（包括summary）
  const [monitorLoading, setMonitorLoading] = useState(false);
  const [hoveredMonitorId, setHoveredMonitorId] = useState(null);
  const [lastUpdateTime, setLastUpdateTime] = useState(null); // 最后更新时间

  // 加载Top动量实体
  const loadTopMomentumEntities = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/graph/momentum/top', {
        params: {
          limit: 100,  // 提高到100条，由前端分页控制显示
          entity_type: entityType === 'all' ? undefined : entityType,
          start_date: timeRange && timeRange[0] ? timeRange[0].format('YYYY-MM-DD') : undefined,
          end_date: timeRange && timeRange[1] ? timeRange[1].format('YYYY-MM-DD') : undefined
        }
      });
      
      // 验证响应数据
      if (!response || typeof response !== 'object') {
        throw new Error('服务器返回数据格式错误');
      }
      
      const entities = response.entities || [];
      const stats = response.stats || {};
      
      setTopMomentumEntities(entities);
      setMomentumStats(stats);
      setLastUpdateTime(dayjs()); // 记录更新时间
      
      if (entities.length === 0) {
        message.info('暂无动量数据，请先添加数据或更新动量');
      }
    } catch (error) {
      console.error('加载动量数据失败:', error);
      // 提取错误消息，处理FastAPI返回的detail数组格式
      let errorMsg = '未知错误';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail) && detail.length > 0) {
          errorMsg = detail[0].msg || JSON.stringify(detail[0]);
        } else if (typeof detail === 'string') {
          errorMsg = detail;
        } else {
          errorMsg = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMsg = error.message;
      }
      message.error(`加载动量数据失败: ${errorMsg}`);
      // 设置默认空数据防止界面报错
      setTopMomentumEntities([]);
      setMomentumStats({});
    } finally {
      setLoading(false);
    }
  };

  // 加载趋势数据
  const loadTrendData = async () => {
    try {
      // 检查 timeRange 是否有效
      if (!timeRange || !timeRange[0] || !timeRange[1]) {
        return;
      }

      const response = await apiClient.get('/api/v1/graph/momentum/trend', {
        params: {
          start_date: timeRange[0].format('YYYY-MM-DD'),
          end_date: timeRange[1].format('YYYY-MM-DD')
        }
      });
      
      const trendData = response.trend || [];
      setTrendData(trendData);
      
      if (trendData.length === 0) {
        // 趋势数据为空，静默失败
      }
    } catch (error) {
      console.error('加载趋势数据失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      message.error(`加载趋势数据失败: ${errorMsg}`);
      setTrendData([]);
    }
  };

  useEffect(() => {
    loadTopMomentumEntities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType, timeRange]); // 实体类型或时间范围变化时重新加载

  useEffect(() => {
    // 延迟加载趋势数据，避免与Top实体请求冲突
    const timer = setTimeout(() => {
      loadTrendData();
    }, 100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange, entityType]); // 时间范围或实体类型变化时重新加载

  // 加载监控列表
  const loadMonitorList = async () => {
    setMonitorLoading(true);
    try {
      const response = await apiClient.get('/api/v1/entity-actions/monitor/list');
      setMonitorData(response); // 保存完整响应（包括summary）
      setMonitorList(response.monitors || []);
    } catch (error) {
      console.error('加载监控列表失败:', error);
      message.error(`加载监控列表失败: ${error.message}`);
      setMonitorData(null);
      setMonitorList([]);
    } finally {
      setMonitorLoading(false);
    }
  };

  // 移除监控
  const handleRemoveMonitor = async (monitorId, entityName) => {
    try {
      await apiClient.post('/api/v1/entity-actions/monitor/remove', {
        monitor_id: monitorId
      });
      message.success(`已将 ${entityName} 移出监控列表`);
      // 重新加载监控列表
      loadMonitorList();
    } catch (error) {
      message.error(`移除失败: ${error.message}`);
    }
  };

  // 打开监控面板时加载数据
  const handleOpenMonitorPanel = () => {
    setMonitorDrawerVisible(true);
    loadMonitorList();
  };

  // 表格列定义
  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      align: 'center',
      render: (text, record, index) => {
        const rank = index + 1;
        if (rank === 1) return <Tag color="gold">👑 {rank}</Tag>;
        if (rank === 2) return <Tag color="silver">🥈 {rank}</Tag>;
        if (rank === 3) return <Tag color="orange">🥉 {rank}</Tag>;
        return <span style={{ fontWeight: 'bold' }}>{rank}</span>;
      }
    },
    {
      title: '实体名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (text, record) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.type && (
            <Tag color={getTypeColor(record.type)}>
              {record.type.toUpperCase()}
            </Tag>
          )}
        </Space>
      )
    },
    {
      title: '当前动量',
      dataIndex: 'current_momentum',
      key: 'current_momentum',
      width: 150,
      align: 'center',
      sorter: (a, b) => a.current_momentum - b.current_momentum,
      render: (value) => {
        const percentage = (value * 100).toFixed(1);
        const color = getMomentumColor(value);
        return (
          <Space>
            <div style={{
              width: '60px',
              height: '8px',
              background: '#e2e8f0',
              borderRadius: '4px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${percentage}%`,
                height: '100%',
                background: color,
                transition: 'width 0.3s'
              }}></div>
            </div>
            <span style={{ color, fontWeight: 'bold' }}>{percentage}%</span>
          </Space>
        );
      }
    },
    {
      title: '动量趋势',
      dataIndex: 'momentum_change',
      key: 'momentum_change',
      width: 120,
      align: 'center',
      sorter: (a, b) => (a.momentum_change || 0) - (b.momentum_change || 0),
      render: (value) => {
        if (!value && value !== 0) return <span style={{ color: '#94a3b8' }}>-</span>;
        const isPositive = value > 0;
        return (
          <Tag color={isPositive ? 'green' : 'red'} icon={isPositive ? <RiseOutlined /> : <FallOutlined />}>
            {isPositive ? '+' : ''}{(value * 100).toFixed(1)}%
          </Tag>
        );
      }
    },
    {
      title: '引用次数',
      dataIndex: 'reference_count',
      key: 'reference_count',
      width: 100,
      align: 'center',
      sorter: (a, b) => a.reference_count - b.reference_count,
      render: (value) => <span style={{ fontWeight: 'bold', color: '#3b82f6' }}>{value || 0}</span>
    },
    {
      title: '最新更新',
      dataIndex: 'last_updated',
      key: 'last_updated',
      width: 180,
      render: (value) => {
        if (!value) return <span style={{ color: '#94a3b8' }}>未知</span>;
        const time = dayjs(value);
        const isRecent = dayjs().diff(time, 'hours') < 24;
        return (
          <Space>
            <ClockCircleOutlined style={{ color: isRecent ? '#10b981' : '#94a3b8' }} />
            <span style={{ color: isRecent ? '#10b981' : '#64748b' }}>
              {time.format('YYYY-MM-DD HH:mm')}
            </span>
            {isRecent && <Tag color="green">最新</Tag>}
          </Space>
        );
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      align: 'center',
      fixed: 'right',
      render: (_, record) => {
        const isHovered = hoveredRow === record.id;
        
        // 下拉菜单项
        const menuItems = [
          {
            key: 'ai-report',
            icon: <FileTextOutlined />,
            label: '生成 AI 简报',
            onClick: () => handleGenerateReport(record)
          },
          {
            key: 'graph-analysis',
            icon: <ApartmentOutlined />,
            label: '关联图谱分析',
            onClick: () => handleGraphAnalysis(record)
          },
          {
            key: 'export',
            icon: <ExportOutlined />,
            label: '导出原始数据',
            onClick: () => handleExportData(record)
          },
          {
            type: 'divider'
          },
          {
            key: 'hide',
            icon: <EyeInvisibleOutlined />,
            label: '屏蔽此实体',
            danger: true,
            onClick: () => handleHideEntity(record)
          }
        ];

        return (
          <Space size="small">
            {/* 高频操作：悬停时显示 */}
            {isHovered && (
              <>
                <Tooltip title="情报溯源 - 查看热度上升的具体证据">
                  <Button
                    type="text"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => handleInvestigate(record)}
                    style={{ color: '#3b82f6' }}
                  />
                </Tooltip>
                <Tooltip title="加入特别关注 - 动量波动时优先提醒">
                  <Button
                    type="text"
                    size="small"
                    icon={<StarOutlined />}
                    onClick={() => handleAddMonitor(record)}
                    style={{ color: '#f59e0b' }}
                  />
                </Tooltip>
              </>
            )}
            
            {/* 低频操作：下拉菜单 */}
            <Dropdown
              menu={{ items: menuItems }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Button
                type="text"
                size="small"
                icon={<MoreOutlined />}
                style={{ color: '#64748b' }}
              />
            </Dropdown>
          </Space>
        );
      }
    }
  ];

  // 操作处理函数
  
  // 1. 情报溯源 - 打开详情抽屉展示证据
  const handleInvestigate = async (record) => {
    setCurrentEntity(record);
    setSourceDrawerVisible(true);
    setSourceDrawerLoading(true);
    
    try {
      const response = await apiClient.post('/api/v1/entity-actions/investigate', {
        entity_id: record.id,
        depth: 2
      });
      
      // 使用排行榜中的动量值，而不是重新查询的值，确保数据一致性
      const dataWithRankingMomentum = {
        ...response,
        entity: {
          ...response.entity,
          current_momentum: record.current_momentum  // 使用排行榜中的缓存值
        }
      };
      
      setSourceDrawerData(dataWithRankingMomentum);
      message.success(`情报溯源完成！找到 ${response.analysis.total_documents} 条相关证据`);
    } catch (error) {
      message.error(`情报溯源失败: ${error.message}`);
      setSourceDrawerVisible(false);
    } finally {
      setSourceDrawerLoading(false);
    }
  };

  // 2. 加入特别关注 - 添加到监控面板
  const handleAddMonitor = async (record) => {
    try {
      const response = await apiClient.post('/api/v1/entity-actions/monitor/add', {
        entity_id: record.id,
        entity_name: record.name,
        entity_type: record.type,
        priority: 'high',  // 特别关注默认高优先级
        reason: '从动量排行榜添加到特别关注'
      });
      
      if (response.success) {
        message.success({
          content: (
            <span>
              <BellOutlined style={{ marginRight: 8, color: '#f59e0b' }} />
              已将 <strong>{record.name}</strong> 加入特别关注！动量剧烈波动时将优先提醒您。
            </span>
          ),
          duration: 4
        });
      } else {
        message.warning(response.message || '该实体已在监控列表中');
      }
    } catch (error) {
      message.error(`添加失败: ${error.message}`);
    }
  };

  // 3. 生成AI简报 - 弹窗展示并提供下载
  const handleGenerateReport = async (record) => {
    setCurrentEntity(record);
    setReportModalVisible(true);
    setReportLoading(true);
    setReportContent('');
    
    try {
      const response = await apiClient.post('/api/v1/entity-actions/generate-report', {
        entity_id: record.id
      });
      
      setReportContent(response.report);
      message.success('AI简报生成完成！');
    } catch (error) {
      message.error(`生成简报失败: ${error.message}`);
      setReportModalVisible(false);
    } finally {
      setReportLoading(false);
    }
  };
  
  // 下载AI简报为Markdown文件
  const downloadReport = () => {
    if (!reportContent || !currentEntity) return;
    
    const blob = new Blob([reportContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentEntity.name}_AI简报_${dayjs().format('YYYYMMDD_HHmmss')}.md`;
    link.click();
    URL.revokeObjectURL(url);
    message.success('简报已下载！');
  };

  // 4. 关联图谱分析 - 跳转到图谱页面并高亮实体
  const handleGraphAnalysis = (record) => {
    message.info({
      content: `正在进入知识图谱视图，将高亮显示 ${record.name} 的关联网络...`,
      duration: 2
    });
    
    // 跳转到图谱页面，传递实体ID作为参数
    setTimeout(() => {
      window.location.href = `/graph?entity=${encodeURIComponent(record.id)}&name=${encodeURIComponent(record.name)}`;
    }, 500);
  };

  // 5. 导出原始数据 - 下载Excel格式
  const handleExportData = async (record) => {
    try {
      message.loading({ content: `正在导出 ${record.name} 的结构化数据...`, key: 'export' });
      
      const response = await apiClient.post('/api/v1/entity-actions/export-data', {
        entity_id: record.id
      });
      
      // 创建详细的数据结构
      const exportData = {
        entity_info: response.data.entity,
        statistics: {
          total_documents: response.data.documents.length,
          momentum_score: response.data.entity.current_momentum,
          reference_count: response.data.entity.reference_count,
          export_time: dayjs().format('YYYY-MM-DD HH:mm:ss')
        },
        documents: response.data.documents
      };
      
      // 下载JSON文件
      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${record.name}_原始数据_${dayjs().format('YYYYMMDD_HHmmss')}.json`;
      link.click();
      URL.revokeObjectURL(url);
      
      message.success({ 
        content: '数据导出成功！包含热度评分历史、提及次数等详细信息。', 
        key: 'export',
        duration: 3
      });
    } catch (error) {
      message.error({ content: `导出失败: ${error.message}`, key: 'export' });
    }
  };

  // 6. 屏蔽此实体 - 从排行榜移除并降低推荐权重
  const handleHideEntity = async (record) => {
    Modal.confirm({
      title: '确认屏蔽实体',
      icon: <EyeInvisibleOutlined style={{ color: '#ef4444' }} />,
      content: (
        <div style={{ marginTop: 16 }}>
          <p>确定要屏蔽实体 <strong>{record.name}</strong> 吗？</p>
          <p style={{ color: '#64748b', fontSize: '13px', marginTop: 8 }}>
            • 该实体将从动量排行榜中移除<br />
            • 未来的算法推荐中将降低其权重<br />
            • 如果这是误判的噪音数据，建议执行此操作
          </p>
        </div>
      ),
      okText: '确认屏蔽',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await apiClient.post('/api/v1/entity-actions/hide-entity', {
            entity_id: record.id
          });
          
          if (response.success) {
            message.success(`${record.name} 已被屏蔽，正在刷新列表...`);
            // 重新加载列表
            setTimeout(() => loadTopMomentumEntities(), 1000);
          }
        } catch (error) {
          message.error(`屏蔽失败: ${error.message}`);
        }
      }
    });
  };

  // 获取类型颜色
  const getTypeColor = (type) => {
    const colorMap = {
      person: 'blue',
      organization: 'purple',
      location: 'green',
      event: 'orange',
      product: 'cyan'
    };
    return colorMap[type?.toLowerCase()] || 'default';
  };

  // 获取动量颜色
  const getMomentumColor = (momentum) => {
    if (momentum >= 0.7) return '#ef4444'; // 红色-高热度
    if (momentum >= 0.5) return '#f59e0b'; // 橙色
    if (momentum >= 0.3) return '#10b981'; // 绿色
    return '#3b82f6'; // 蓝色-低热度
  };

  // 饼图颜色
  const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题和操作按钮 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: 'bold',
          margin: 0,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          <ThunderboltOutlined /> 时序分析
        </h1>
        
        {/* 雷达图标按钮 - 打开监控面板 */}
        <Tooltip title="我的监控面板" placement="left">
          <Button
            type="primary"
            size="large"
            icon={<RadarChartOutlined />}
            onClick={handleOpenMonitorPanel}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            监控雷达
            {monitorList.length > 0 && (
              <Badge 
                count={monitorList.length} 
                style={{ 
                  backgroundColor: '#ef4444',
                  marginLeft: '4px'
                }} 
              />
            )}
          </Button>
        </Tooltip>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总实体数"
              value={momentumStats.total_entities || 0}
              prefix={<FireOutlined />}
              valueStyle={{ color: '#3b82f6' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="高热度实体"
              value={momentumStats.high_momentum_count || 0}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#ef4444' }}
              suffix={`/ ${momentumStats.total_entities || 0}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均动量"
              value={(momentumStats.average_momentum * 100 || 0).toFixed(1)}
              prefix={<ThunderboltOutlined />}
              suffix="%"
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总引用数"
              value={momentumStats.total_references || 0}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选器 */}
      <Card style={{ marginBottom: '24px' }}>
        <Space size="large" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space size="large">
            <div>
              <span style={{ marginRight: '8px', color: '#64748b' }}>实体类型:</span>
              <Select
                value={entityType}
                onChange={setEntityType}
                style={{ width: 150 }}
              >
                <Option value="all">全部类型</Option>
                <Option value="persons">人物</Option>
                <Option value="companies">公司</Option>
                <Option value="products">产品</Option>
                <Option value="technologies">技术</Option>
                <Option value="locations">地点</Option>
              </Select>
            </div>
            <div>
              <span style={{ marginRight: '8px', color: '#64748b' }}>时间范围:</span>
              <RangePicker
                value={timeRange}
                onChange={(dates) => {
                  // 允许清空日期（会设置为null），也允许选择有效日期范围
                  if (dates && dates[0] && dates[1]) {
                    setTimeRange(dates);
                  } else if (!dates) {
                    // 清空时，重置为默认30天
                    setTimeRange([dayjs().subtract(30, 'days'), dayjs()]);
                  }
                }}
                format="YYYY-MM-DD"
                allowClear={true}
              />
            </div>
          </Space>
          <Space>
            {lastUpdateTime && (
              <span style={{ color: '#94a3b8', fontSize: '12px' }}>
                最后更新: {lastUpdateTime.format('HH:mm:ss')}
              </span>
            )}
            <Button 
              icon={<ThunderboltOutlined />} 
              onClick={loadTopMomentumEntities}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        </Space>
      </Card>

      <Tabs defaultActiveKey="ranking">
        {/* 排行榜Tab */}
        <TabPane
          tab={<span><FireOutlined />动量排行榜</span>}
          key="ranking"
        >
          <Card>
            <Spin spinning={loading}>
              {topMomentumEntities.length > 0 ? (
                <Table
                  columns={columns}
                  dataSource={topMomentumEntities.map((item, index) => ({ ...item, key: index }))}
                  pagination={{
                    current: currentPage,
                    pageSize: pageSize,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total) => `共 ${total} 条`,
                    onChange: (page, size) => {
                      setCurrentPage(page);
                      if (size !== pageSize) {
                        setPageSize(size);
                        setCurrentPage(1); // 改变pageSize时重置到第一页
                      }
                    }
                  }}
                  onRow={(record) => ({
                    onMouseEnter: () => setHoveredRow(record.id),
                    onMouseLeave: () => setHoveredRow(null),
                  })}
                  size="middle"
                />
              ) : (
                <Empty description="暂无数据" />
              )}
            </Spin>
          </Card>
        </TabPane>

        {/* 趋势分析Tab */}
        <TabPane
          tab={<span><RiseOutlined />动量趋势</span>}
          key="trend"
        >
          <Card>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorMomentum" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip
                  contentStyle={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="avg_momentum"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorMomentum)"
                  name="平均动量"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabPane>

        {/* 类型分布Tab */}
        <TabPane
          tab={<span><FireOutlined />类型分布</span>}
          key="distribution"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Card title="实体类型分布">
                {momentumStats.type_distribution && Object.keys(momentumStats.type_distribution).length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={Object.entries(momentumStats.type_distribution || {}).map(([name, value]) => ({ name, value }))}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {Object.keys(momentumStats.type_distribution || {}).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="动量等级分布">
                {momentumStats.momentum_levels ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={[
                      { level: '低热度', count: momentumStats.momentum_levels?.low || 0, color: '#3b82f6' },
                      { level: '中等', count: momentumStats.momentum_levels?.medium || 0, color: '#10b981' },
                      { level: '较高', count: momentumStats.momentum_levels?.high || 0, color: '#f59e0b' },
                      { level: '高热度', count: momentumStats.momentum_levels?.very_high || 0, color: '#ef4444' }
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="level" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <RechartsTooltip
                        contentStyle={{
                          background: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '8px'
                        }}
                      />
                      <Bar dataKey="count" fill="#3b82f6">
                        {[0, 1, 2, 3].map((index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Empty description="暂无数据" />
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>
      </Tabs>

      {/* 情报溯源抽屉 */}
      <Drawer
        title={
          <Space>
            <EyeOutlined style={{ color: '#3b82f6' }} />
            <span>情报溯源：{currentEntity?.name}</span>
          </Space>
        }
        placement="right"
        width={720}
        open={sourceDrawerVisible}
        onClose={() => setSourceDrawerVisible(false)}
        loading={sourceDrawerLoading}
      >
        {sourceDrawerData && (
          <div>
            {/* 实体基本信息 */}
            <Card size="small" style={{ marginBottom: 16 }}>
              <Descriptions title="实体信息" column={2} size="small">
                <Descriptions.Item label="名称">{sourceDrawerData.entity?.name}</Descriptions.Item>
                <Descriptions.Item label="类型">
                  <Tag color={getTypeColor(sourceDrawerData.entity?.type)}>
                    {sourceDrawerData.entity?.type}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="当前动量">
                  <Badge 
                    status={(sourceDrawerData.entity?.current_momentum || 0) > 0.5 ? "processing" : "default"} 
                    text={`${((sourceDrawerData.entity?.current_momentum || 0) * 100).toFixed(1)}%`}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="引用次数">
                  {sourceDrawerData.entity?.reference_count || 0}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 分析摘要 */}
            <Card size="small" title="热度分析" style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <strong>关联关系：</strong>
                  <span style={{ marginLeft: 8 }}>
                    {(sourceDrawerData.relations?.length || 0)} 个实体关联
                  </span>
                </div>
                <div>
                  <strong>相关证据：</strong>
                  <span style={{ marginLeft: 8 }}>
                    {(sourceDrawerData.recent_documents?.length || 0)} 条新闻报道/讨论
                  </span>
                </div>
                <div>
                  <strong>趋势方向：</strong>
                  <Tag color={sourceDrawerData.analysis?.momentum_direction === '上升' ? 'red' : 'blue'}>
                    {sourceDrawerData.analysis?.momentum_direction || '平稳'}
                  </Tag>
                </div>
              </Space>
            </Card>

            {/* 动量趋势 */}
            {sourceDrawerData.momentum_trend && sourceDrawerData.momentum_trend.length > 0 && (
              <Card size="small" title="30天动量趋势" style={{ marginBottom: 16 }}>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={sourceDrawerData.momentum_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* 相关文档时间线 */}
            <Card size="small" title={`相关证据 (${sourceDrawerData.recent_documents?.length || 0}条)`}>
              <Timeline
                mode="left"
                items={sourceDrawerData.recent_documents?.slice(0, 10).map((doc, index) => ({
                  color: index < 3 ? 'red' : 'blue',
                  children: (
                    <div>
                      <div style={{ fontWeight: 500, marginBottom: 4 }}>
                        {doc.source_url ? (
                          <a 
                            href={doc.source_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ color: '#3b82f6', textDecoration: 'none' }}
                            onMouseEnter={(e) => e.target.style.textDecoration = 'underline'}
                            onMouseLeave={(e) => e.target.style.textDecoration = 'none'}
                          >
                            {doc.title || '无标题'}
                          </a>
                        ) : (
                          <span>{doc.title || '无标题'}</span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>
                        {dayjs(doc.created_at).format('YYYY-MM-DD HH:mm')}
                      </div>
                    </div>
                  )
                })) || []}
              />
              {sourceDrawerData.recent_documents?.length > 10 && (
                <div style={{ textAlign: 'center', marginTop: 16, color: '#64748b' }}>
                  还有 {sourceDrawerData.recent_documents.length - 10} 条证据未显示
                </div>
              )}
            </Card>
          </div>
        )}
      </Drawer>

      {/* AI简报弹窗 */}
      <Modal
        title={
          <Space>
            <FileTextOutlined style={{ color: '#10b981' }} />
            <span>AI 简报：{currentEntity?.name}</span>
          </Space>
        }
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        width={900}
        footer={[
          <Button key="download" type="primary" icon={<DownloadOutlined />} onClick={downloadReport} disabled={!reportContent}>
            下载 Markdown 文件
          </Button>,
          <Button key="close" onClick={() => setReportModalVisible(false)}>
            关闭
          </Button>
        ]}
        styles={{
          body: { maxHeight: '70vh', overflow: 'auto', padding: '24px' }
        }}
      >
        <Spin spinning={reportLoading} tip="AI 正在深度分析相关资讯，生成专业简报...">
          {reportContent ? (
            <div 
              style={{ 
                background: '#1e293b',
                color: '#e2e8f0',
                borderRadius: '8px',
                border: '1px solid #334155',
                padding: '24px',
                lineHeight: 1.8,
                fontSize: '14px'
              }}
            >
              {reportContent.split('\n').map((line, index) => {
                // 一级标题 ##
                if (line.startsWith('## ')) {
                  return (
                    <h2 key={index} style={{
                      color: '#60a5fa',
                      fontSize: '18px',
                      fontWeight: 'bold',
                      margin: '24px 0 12px 0',
                      paddingBottom: '8px',
                      borderBottom: '2px solid #334155'
                    }}>
                      {line.replace('## ', '')}
                    </h2>
                  );
                }
                // 三级标题 ###
                if (line.startsWith('### ')) {
                  return (
                    <h3 key={index} style={{
                      color: '#34d399',
                      fontSize: '16px',
                      fontWeight: 'bold',
                      margin: '16px 0 8px 0'
                    }}>
                      {line.replace('### ', '')}
                    </h3>
                  );
                }
                // 列表项
                if (line.match(/^[\s]*[-*]\s+/)) {
                  const content = line.replace(/^[\s]*[-*]\s+/, '');
                  return (
                    <div key={index} style={{ marginLeft: '20px', marginBottom: '6px' }}>
                      <span style={{ color: '#60a5fa', marginRight: '8px' }}>•</span>
                      <span style={{ color: '#cbd5e1' }} dangerouslySetInnerHTML={{
                        __html: content
                          .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fbbf24;">$1</strong>')
                          .replace(/`(.*?)`/g, '<code style="background: #374151; padding: 2px 6px; border-radius: 3px; color: #10b981;">$1</code>')
                      }} />
                    </div>
                  );
                }
                // 空行，减少间距
                if (line.trim() === '') {
                  return <div key={index} style={{ height: '8px' }} />;
                }
                // 普通段落
                return (
                  <p key={index} style={{ 
                    margin: '8px 0', 
                    color: '#e2e8f0',
                    textIndent: line.startsWith('分析：') || line.startsWith('新闻') ? '0' : '0'
                  }} dangerouslySetInnerHTML={{
                    __html: line
                      .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fbbf24;">$1</strong>')
                      .replace(/`(.*?)`/g, '<code style="background: #374151; padding: 2px 6px; border-radius: 3px; color: #10b981;">$1</code>')
                      .replace(/【(.*?)】/g, '<span style="color: #a78bfa;">【$1】</span>')
                  }} />
                );
              })}
            </div>
          ) : (
            <Empty description="暂无简报内容" style={{ padding: '40px 0' }} />
          )}
        </Spin>
      </Modal>

      {/* 监控面板抽屉 */}
      <Drawer
        title={
          <Space>
            <RadarChartOutlined style={{ color: '#667eea' }} />
            <span>我的监控面板</span>
          </Space>
        }
        placement="right"
        width={480}
        open={monitorDrawerVisible}
        onClose={() => setMonitorDrawerVisible(false)}
        styles={{
          body: { 
            padding: '16px',
            background: '#0f172a'
          }
        }}
      >
        <Spin spinning={monitorLoading}>
          {/* 今日监控预警 */}
          {monitorList.length > 0 && (() => {
            const activeCount = monitorData?.summary?.active_count || 0;
            const significantEntities = monitorData?.summary?.significant_entities || [];
            const totalCount = monitorData?.summary?.total_count || monitorList.length;
            
            return (
              <Card 
                size="small" 
                style={{ 
                  marginBottom: 16,
                  background: activeCount > 0 
                    ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)'
                    : 'linear-gradient(135deg, rgba(71, 85, 105, 0.1) 0%, rgba(51, 65, 85, 0.1) 100%)',
                  border: activeCount > 0 ? '1px solid #667eea' : '1px solid #475569'
                }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <BellOutlined style={{ color: activeCount > 0 ? '#667eea' : '#94a3b8', fontSize: 16 }} />
                    <Typography.Text strong style={{ color: activeCount > 0 ? '#667eea' : '#94a3b8' }}>
                      今日监控预警
                    </Typography.Text>
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {activeCount > 0 ? (
                      <>
                        监控池中有 <span style={{ color: '#667eea', fontWeight: 500 }}>{activeCount}</span> 个实体今日活跃。
                        {significantEntities.length > 0 && (
                          <>
                            其中 <span style={{ color: '#f59e0b', fontWeight: 500 }}>{significantEntities.join('、')}</span> 出现显著异动，建议重点关注。
                          </>
                        )}
                      </>
                    ) : (
                      `监控池中 ${totalCount} 个实体今日运行平稳，暂无异常波动。`
                    )}
                  </Typography.Text>
                </Space>
              </Card>
            );
          })()}

          {/* 监控实体列表 */}
          {monitorList.length > 0 ? (
            <>
              <List
                dataSource={monitorList}
                renderItem={(item) => {
                  const momentum24h = item.momentum_change_24h || 0;
                  const isIncrease = momentum24h > 0;
                  const isSignificant = Math.abs(momentum24h) > 0.05;
                  const isHovered = hoveredMonitorId === item.id;
                  
                  return (
                    <div 
                      key={item.id} 
                      style={{
                        background: 'rgba(30, 41, 59, 0.3)',
                        border: '1px solid #1e293b',
                        borderRadius: 8,
                        padding: 16,
                        marginBottom: 12,
                        transition: 'all 0.3s',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#475569';
                        setHoveredMonitorId(item.id);
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#1e293b';
                        setHoveredMonitorId(null);
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                        <div>
                          <h4 style={{ color: 'white', fontWeight: 'bold', margin: 0, fontSize: 15 }}>
                            {item.entity_name}
                          </h4>
                          <div style={{ 
                            fontSize: 12, 
                            fontWeight: 500, 
                            marginTop: 2, 
                            display: 'flex', 
                            alignItems: 'center', 
                            gap: 4,
                            color: isIncrease ? '#34d399' : '#f87171'
                          }}>
                            {isIncrease ? <RiseOutlined style={{ fontSize: 12 }} /> : <FallOutlined style={{ fontSize: 12 }} />}
                            <span>24h 变动: {isIncrease ? '+' : ''}{(momentum24h * 100).toFixed(1)}%</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => handleRemoveMonitor(item.id, item.entity_name)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#64748b',
                            cursor: 'pointer',
                            padding: 4,
                            transition: 'color 0.3s'
                          }}
                          title="移除监控"
                        >
                          <StarFilled style={{ 
                            fontSize: 16, 
                            color: isHovered ? '#fbbf24' : 'rgba(234, 179, 8, 0.5)',
                            transition: 'color 0.3s'
                          }} />
                        </button>
                      </div>
                      
                      {/* Mini Sparkline for 24h Trend */}
                      <div style={{ height: 48, marginBottom: 12, marginLeft: -4, marginRight: -4 }}>
                        <Sparkline 
                          data={(() => {
                            const history = item.momentum_history || [];
                            const change24h = item.momentum_change_24h || 0;
                            const changePercent = Math.abs(change24h * 100); // 转为百分比
                            
                            if (history.length < 2) {
                              return change24h > 0 ? [0, 100] : change24h < 0 ? [100, 0] : [50, 50];
                            }
                            
                            // 取最后5个点
                            const recent = history.slice(-5);
                            let values = recent.map(h => h.value || 0);
                            
                            // 归一化到0-100
                            const min = Math.min(...values);
                            const max = Math.max(...values);
                            const range = max - min;
                            
                            let normalized;
                            if (range < 0.0001) {
                              // 变化极小，根据24h变化生成趋势
                              const amplitude = Math.min(changePercent * 3, 40) * 1.2; // 增大20%视觉效果
                              const centerLine = 50;
                              
                              if (change24h > 0) {
                                // 上升：从 (50-幅度) 到 (50+幅度)
                                normalized = Array.from({length: 5}, (_, i) => 
                                  centerLine - amplitude + (amplitude * 2 * i / 4)
                                );
                              } else if (change24h < 0) {
                                // 下降：从 (50+幅度) 到 (50-幅度)
                                normalized = Array.from({length: 5}, (_, i) => 
                                  centerLine + amplitude - (amplitude * 2 * i / 4)
                                );
                              } else {
                                normalized = Array(5).fill(50);
                              }
                            } else {
                              // 有数据，先归一化
                              normalized = values.map(v => ((v - min) / range) * 100);
                              
                              // 检查数据方向与24h变化是否一致
                              const dataDirection = normalized[normalized.length - 1] - normalized[0];
                              const shouldReverse = (change24h < 0 && dataDirection > 0) || (change24h > 0 && dataDirection < 0);
                              
                              if (shouldReverse) {
                                normalized = normalized.reverse();
                              }
                              
                              // 根据24h变化幅度调整振幅
                              // 变化大（如20%）→保持0-100的全幅度
                              // 变化小（如2%）→压缩到更窄的范围
                              const amplitudeFactor = Math.min(changePercent / 20, 1) * 1.2; // 增大20%视觉效果
                              const centerLine = 50;
                              
                              // 调整到合适的振幅
                              normalized = normalized.map(v => {
                                const deviation = (v - 50) * amplitudeFactor;
                                const adjusted = centerLine + deviation;
                                // 确保不超出0-100范围
                                return Math.max(0, Math.min(100, adjusted));
                              });
                            }
                            
                            return normalized;
                          })()}
                          color={isIncrease ? '#34d399' : '#f43f5e'} 
                          height={40} 
                        />
                      </div>

                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'flex-start', 
                        gap: 8, 
                        fontSize: 12, 
                        color: '#94a3b8',
                        background: 'rgba(15, 23, 42, 0.5)',
                        padding: 8,
                        borderRadius: 4
                      }}>
                        <ThunderboltOutlined style={{ fontSize: 12, marginTop: 2, flexShrink: 0, color: '#64748b' }} />
                        <span style={{ 
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          lineHeight: 1.4
                        }}>
                          {item.reason || '监控中'}
                        </span>
                      </div>
                    </div>
                  );
                }}
              />
              
              {/* 底部操作按钮 */}
              <div style={{ 
                marginTop: 16,
                padding: '12px',
                background: '#1e293b',
                borderRadius: 8,
                textAlign: 'center'
              }}>
                <Button 
                  type="primary" 
                  block
                  onClick={() => {
                    setMonitorDrawerVisible(false);
                    // 可以跳转到专门的监控列表页面
                  }}
                  style={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    border: 'none'
                  }}
                >
                  查看全部监控列表
                </Button>
              </div>
            </>
          ) : (
            <Empty 
              description={
                <div>
                  <Typography.Text type="secondary">
                    暂无监控实体
                  </Typography.Text>
                  <div style={{ marginTop: 12 }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      在动量排行榜中点击 <StarOutlined style={{ color: '#f59e0b' }} /> 按钮即可添加特别关注
                    </Typography.Text>
                  </div>
                </div>
              }
              style={{ padding: '60px 0' }}
            />
          )}
        </Spin>
      </Drawer>
    </div>
  );
};

export default TemporalAnalysisPage;
