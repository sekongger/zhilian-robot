import React from 'react';
import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend } from 'recharts';
import { Card, Row, Col, Statistic } from 'antd';
import { DeploymentUnitOutlined, RiseOutlined, DatabaseOutlined } from '@ant-design/icons';

const DashboardStats = ({ data }) => {
  // 处理数据进行图表展示
  const typeCount = data.nodes.reduce((acc, node) => {
    const type = node.type || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {});

  const COLOR_MAP = {
    'companies': '#3b82f6',
    'products': '#10b981',
    'technologies': '#f59e0b',
    'persons': '#ef4444',
    'locations': '#06b6d4',
    'unknown': '#94a3b8'
  };

  const pieData = Object.keys(typeCount).map(type => ({
    name: type,
    value: typeCount[type],
    color: COLOR_MAP[type] || '#888'
  }));

  const linkCount = data.edges?.length || 0;
  const nodeCount = data.nodes?.length || 0;
  const density = nodeCount > 0 ? (linkCount / nodeCount).toFixed(2) : 0;

  // 计算连接度最高的节点
  const nodeConnections = data.nodes.map(n => ({
    name: n.name.length > 10 ? n.name.substring(0, 10) + '...' : n.name,
    connections: data.edges.filter(l => l.source === n.id || l.target === n.id).length
  })).sort((a, b) => b.connections - a.connections).slice(0, 6);

  return (
    <div className="dashboard-stats">
      {/* 关键指标卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="图谱实体节点"
              value={nodeCount}
              prefix={<DeploymentUnitOutlined style={{ color: '#6366f1' }} />}
              suffix="个"
              valueStyle={{ color: '#fff', fontSize: '28px', fontWeight: 'bold' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="产业链关系"
              value={linkCount}
              prefix={<RiseOutlined style={{ color: '#22c55e' }} />}
              suffix="条"
              valueStyle={{ color: '#3b82f6', fontSize: '28px', fontWeight: 'bold' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="图谱密度"
              value={density}
              prefix={<DatabaseOutlined style={{ color: '#10b981' }} />}
              valueStyle={{ color: '#10b981', fontSize: '28px', fontWeight: 'bold' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card className="chart-card" title="实体分布">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    borderColor: '#334155', 
                    color: '#fff',
                    borderRadius: '8px'
                  }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        
        <Col xs={24} lg={14}>
          <Card className="chart-card" title="连接度最高的节点">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={nodeConnections}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  stroke="#94a3b8" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  angle={-15}
                  textAnchor="end"
                  height={60}
                />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  cursor={{fill: '#334155', opacity: 0.4}}
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    borderColor: '#334155', 
                    color: '#fff',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="connections" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <style jsx>{`
        .stat-card {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
          border-radius: 12px;
        }
        .stat-card :global(.ant-statistic-title) {
          color: #94a3b8;
          font-size: 13px;
        }
        .chart-card {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
          border-radius: 12px;
        }
        .chart-card :global(.ant-card-head-title) {
          color: #e2e8f0;
          font-weight: 600;
        }
        .chart-card :global(.ant-card-body) {
          padding: 16px;
        }
      `}</style>
    </div>
  );
};

export default DashboardStats;
