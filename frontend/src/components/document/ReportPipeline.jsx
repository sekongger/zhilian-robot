import React, { useEffect, useState } from 'react'
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Upload, message, Descriptions, Typography, Statistic, Row, Col, Progress, Select, DatePicker } from 'antd'
import { PlusOutlined, SyncOutlined, EyeOutlined, UploadOutlined, FilePdfOutlined, ThunderboltOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { reportPipelineService } from '../../services/reportPipelineApi'

const { TextArea } = Input
const { Paragraph, Text } = Typography

const statusMap = {
  pending: { color: 'default', text: '待处理' },
  parsing: { color: 'processing', text: '解析中' },
  extracting: { color: 'processing', text: '抽取中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
}

const ratingColorMap = {
  '买入': 'red',
  '增持': 'orange',
  '持有': 'blue',
  '减持': 'purple',
  '卖出': 'default',
}

/**
 * 研报处理管道组件
 * 支持研报上传、PDF解析、章节识别、观点提取等功能
 */
const ReportPipeline = ({ stats, onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [formOpen, setFormOpen] = useState(false)
  const [knowledgeOpen, setKnowledgeOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedKnowledge, setSelectedKnowledge] = useState(null)
  const [selectedReport, setSelectedReport] = useState(null)
  const [form] = Form.useForm()
  const [uploadLoading, setUploadLoading] = useState(false)

  const fetchList = async () => {
    setLoading(true)
    try {
      const res = await reportPipelineService.listReports({ limit: 50, offset: 0 })
      setData(res.data || [])
      setTotal(res.total || 0)
    } catch (err) {
      message.error(err.message || '获取研报列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchList()
  }, [])

  const handleUpload = async (info) => {
    if (info.file.status === 'uploading') {
      setUploadLoading(true)
      return
    }
    if (info.file.status === 'done') {
      setUploadLoading(false)
      message.success(`${info.file.name} 上传成功`)
      fetchList()
      onRefresh?.()
    } else if (info.file.status === 'error') {
      setUploadLoading(false)
      message.error(`${info.file.name} 上传失败`)
    }
  }

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        publish_date: values.publish_date ? values.publish_date.format('YYYY-MM-DD') : undefined,
      }
      await reportPipelineService.createReport(payload)
      message.success('研报已入库')
      setFormOpen(false)
      form.resetFields()
      fetchList()
      onRefresh?.()
    } catch (err) {
      if (err?.errorFields) return
      message.error(err.message || '入库失败')
    }
  }

  const handleProcess = async (record) => {
    try {
      await reportPipelineService.processReport(record.id)
      message.success('已启动研报处理')
      fetchList()
      onRefresh?.()
    } catch (err) {
      message.error(err.message || '处理失败')
    }
  }

  const handleBatchProcess = async () => {
    try {
      const res = await reportPipelineService.batchProcess(10)
      message.success(`已提交 ${res.queued || 0} 篇研报处理`)
      fetchList()
      onRefresh?.()
    } catch (err) {
      message.error(err.message || '批量处理失败')
    }
  }

  const handleViewKnowledge = async (record) => {
    try {
      const res = await reportPipelineService.getKnowledge(record.id)
      setSelectedKnowledge(res)
      setKnowledgeOpen(true)
    } catch (err) {
      message.error(err.message || '获取知识失败')
    }
  }

  const handleViewDetail = (record) => {
    setSelectedReport(record)
    setDetailOpen(true)
  }

  const columns = [
    { 
      title: '标题', 
      dataIndex: 'title', 
      key: 'title', 
      ellipsis: true,
      render: (text, record) => (
        <Space>
          <FilePdfOutlined style={{ color: '#ff4d4f' }} />
          <a onClick={() => handleViewDetail(record)}>{text}</a>
        </Space>
      ),
    },
    { 
      title: '机构', 
      dataIndex: 'institution', 
      key: 'institution', 
      width: 120,
      render: (text) => text || '--',
    },
    { 
      title: '分析师', 
      dataIndex: 'analyst', 
      key: 'analyst', 
      width: 100,
      render: (text) => text || '--',
    },
    { 
      title: '行业', 
      dataIndex: 'industry', 
      key: 'industry', 
      width: 100,
      render: (text) => text ? <Tag color="blue">{text}</Tag> : '--',
    },
    {
      title: '发布日期',
      dataIndex: 'publish_date',
      key: 'publish_date',
      width: 120,
      render: (value) => (value ? dayjs(value).format('YYYY-MM-DD') : '--'),
    },
    {
      title: '评级',
      dataIndex: 'rating',
      key: 'rating',
      width: 80,
      render: (val) => val ? <Tag color={ratingColorMap[val] || 'default'}>{val}</Tag> : '--',
    },
    {
      title: '状态',
      dataIndex: 'process_status',
      key: 'process_status',
      width: 100,
      render: (status) => {
        const config = statusMap[status] || statusMap.pending
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          {(record.process_status === 'pending' || record.process_status === 'failed') && (
            <Button size="small" onClick={() => handleProcess(record)}>
              处理
            </Button>
          )}
          {record.process_status === 'completed' && (
            <>
              <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewKnowledge(record)}>
                知识
              </Button>
              <Button size="small" onClick={() => handleViewDetail(record)}>
                详情
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      {/* 快捷统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic title="研报总数" value={total} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic 
              title="待处理" 
              value={data.filter(d => d.process_status === 'pending').length} 
              valueStyle={{ fontSize: 20, color: '#faad14' }} 
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic 
              title="已完成" 
              value={data.filter(d => d.process_status === 'completed').length} 
              valueStyle={{ fontSize: 20, color: '#52c41a' }} 
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="抽取观点" value={stats?.report_layer?.viewpoints ?? 0} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="关联实体" value={stats?.report_layer?.entities ?? 0} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="指标预测" value={stats?.report_layer?.predictions ?? 0} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
      </Row>

      {/* 处理流程说明 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={4}>
            <Text strong>研报处理流程：</Text>
          </Col>
          <Col span={20}>
            <Space size="large">
              <Tag color="blue">1. PDF上传</Tag>
              <span>→</span>
              <Tag color="cyan">2. 页眉页脚去除</Tag>
              <span>→</span>
              <Tag color="green">3. 章节识别</Tag>
              <span>→</span>
              <Tag color="orange">4. 图表分离</Tag>
              <span>→</span>
              <Tag color="purple">5. 观点提取</Tag>
              <span>→</span>
              <Tag color="red">6. 知识入库</Tag>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 操作区 */}
      <Card
        title="研报处理管道"
        extra={
          <Space>
            <Button icon={<SyncOutlined />} onClick={fetchList}>
              刷新
            </Button>
            <Upload
              name="file"
              action="/api/report-pipeline/upload"
              accept=".pdf"
              showUploadList={false}
              onChange={handleUpload}
            >
              <Button icon={<UploadOutlined />} loading={uploadLoading}>
                上传PDF
              </Button>
            </Upload>
            <Button icon={<ThunderboltOutlined />} onClick={handleBatchProcess}>
              批量处理(10篇)
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormOpen(true)}>
              手动录入
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data}
          pagination={{ total, pageSize: 20 }}
        />
      </Card>

      {/* 手动录入弹窗 */}
      <Modal
        title="手动录入研报"
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={handleCreate}
        okText="提交"
        width={600}
      >
        <Form layout="vertical" form={form}>
          <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="请输入研报标题" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="机构" name="institution">
                <Input placeholder="例如 中信证券" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="分析师" name="analyst">
                <Input placeholder="分析师姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="行业" name="industry">
                <Select placeholder="选择行业" allowClear>
                  <Select.Option value="新能源">新能源</Select.Option>
                  <Select.Option value="半导体">半导体</Select.Option>
                  <Select.Option value="医药生物">医药生物</Select.Option>
                  <Select.Option value="消费">消费</Select.Option>
                  <Select.Option value="金融">金融</Select.Option>
                  <Select.Option value="科技">科技</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="评级" name="rating">
                <Select placeholder="选择评级" allowClear>
                  <Select.Option value="买入">买入</Select.Option>
                  <Select.Option value="增持">增持</Select.Option>
                  <Select.Option value="持有">持有</Select.Option>
                  <Select.Option value="减持">减持</Select.Option>
                  <Select.Option value="卖出">卖出</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="发布日期" name="publish_date">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="核心观点" name="core_viewpoint">
            <TextArea rows={3} placeholder="研报核心观点摘要" />
          </Form.Item>
          <Form.Item label="投资建议" name="investment_advice">
            <TextArea rows={2} placeholder="投资建议" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 知识查看弹窗 */}
      <Modal
        title="抽取的知识"
        open={knowledgeOpen}
        onCancel={() => setKnowledgeOpen(false)}
        footer={null}
        width={900}
      >
        {selectedKnowledge && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Descriptions title="核心观点" bordered size="small" column={1}>
              {(selectedKnowledge.viewpoints || []).map((vp, idx) => (
                <Descriptions.Item key={idx} label={`观点 ${idx + 1}`}>
                  <Paragraph style={{ marginBottom: 0 }}>{vp.content}</Paragraph>
                  {vp.confidence && (
                    <Text type="secondary">置信度: {(vp.confidence * 100).toFixed(0)}%</Text>
                  )}
                </Descriptions.Item>
              ))}
            </Descriptions>
            <Descriptions title="投资建议" bordered size="small" column={2}>
              {(selectedKnowledge.recommendations || []).map((rec, idx) => (
                <Descriptions.Item key={idx} label={rec.target || `标的 ${idx + 1}`}>
                  <Tag color={ratingColorMap[rec.rating] || 'default'}>{rec.rating}</Tag>
                  {rec.target_price && <Text> 目标价: {rec.target_price}</Text>}
                </Descriptions.Item>
              ))}
            </Descriptions>
            <Descriptions title="关联实体" bordered size="small" column={2}>
              {(selectedKnowledge.entities || []).map((entity, idx) => (
                <Descriptions.Item key={idx} label={entity.type || '实体'}>
                  {entity.name}
                </Descriptions.Item>
              ))}
            </Descriptions>
            <Descriptions title="指标预测" bordered size="small" column={1}>
              {(selectedKnowledge.predictions || []).map((pred, idx) => (
                <Descriptions.Item key={idx} label={pred.indicator || `指标 ${idx + 1}`}>
                  <Text>{pred.value}</Text>
                  {pred.period && <Text type="secondary"> ({pred.period})</Text>}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </div>
        )}
      </Modal>

      {/* 研报详情弹窗 */}
      <Modal
        title="研报详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={800}
      >
        {selectedReport && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="标题" span={2}>{selectedReport.title}</Descriptions.Item>
            <Descriptions.Item label="机构">{selectedReport.institution || '--'}</Descriptions.Item>
            <Descriptions.Item label="分析师">{selectedReport.analyst || '--'}</Descriptions.Item>
            <Descriptions.Item label="行业">{selectedReport.industry || '--'}</Descriptions.Item>
            <Descriptions.Item label="评级">
              {selectedReport.rating ? (
                <Tag color={ratingColorMap[selectedReport.rating]}>{selectedReport.rating}</Tag>
              ) : '--'}
            </Descriptions.Item>
            <Descriptions.Item label="发布日期">
              {selectedReport.publish_date ? dayjs(selectedReport.publish_date).format('YYYY-MM-DD') : '--'}
            </Descriptions.Item>
            <Descriptions.Item label="处理状态">
              <Tag color={statusMap[selectedReport.process_status]?.color}>
                {statusMap[selectedReport.process_status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="核心观点" span={2}>
              <Paragraph style={{ marginBottom: 0 }}>{selectedReport.core_viewpoint || '--'}</Paragraph>
            </Descriptions.Item>
            <Descriptions.Item label="投资建议" span={2}>
              <Paragraph style={{ marginBottom: 0 }}>{selectedReport.investment_advice || '--'}</Paragraph>
            </Descriptions.Item>
            {selectedReport.quality_metrics && (
              <>
                <Descriptions.Item label="结构完整性">
                  <Progress percent={selectedReport.quality_metrics.structure_completeness || 0} size="small" />
                </Descriptions.Item>
                <Descriptions.Item label="内容准确性">
                  <Progress percent={selectedReport.quality_metrics.content_accuracy || 0} size="small" />
                </Descriptions.Item>
                <Descriptions.Item label="表格还原率">
                  <Progress percent={selectedReport.quality_metrics.table_recovery || 0} size="small" />
                </Descriptions.Item>
                <Descriptions.Item label="图片关联率">
                  <Progress percent={selectedReport.quality_metrics.image_association || 0} size="small" />
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default ReportPipeline
