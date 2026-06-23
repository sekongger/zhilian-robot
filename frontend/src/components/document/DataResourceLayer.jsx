import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Button, Descriptions, Modal, Table, Space, Input, Tag, message, Typography, Upload, Tabs, Collapse, Tooltip, Progress, Alert } from 'antd'
import { 
  DatabaseOutlined, 
  FileOutlined, 
  CloudServerOutlined, 
  CloudDownloadOutlined,
  UploadOutlined,
  InboxOutlined,
  SearchOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  TableOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { documentPipelineService } from '../../services/documentPipelineApi'
import reportPipelineService from '../../services/reportPipelineApi'
import { dataService, ingestionService } from '../../services/api'

const { Text, Title } = Typography
const { Search } = Input
const { Panel } = Collapse

/**
 * 数据资源层组件
 * 展示数据源管理、采集任务、文件索引、原始资源、标准化文档等统计和详情
 * 集成采集功能（从数据中心迁移）
 */
const DataResourceLayer = ({ docType, docTypeConfig, stats, onRefresh }) => {
  const [activeSubTab, setActiveSubTab] = useState('overview')
  
  // 记录详情弹窗
  const [recordsOpen, setRecordsOpen] = useState(false)
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsData, setRecordsData] = useState([])
  const [recordsTotal, setRecordsTotal] = useState(0)
  const [recordsFields, setRecordsFields] = useState([])
  const [recordsTitle, setRecordsTitle] = useState('')
  const [recordsLayer, setRecordsLayer] = useState(null)
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsPageSize, setRecordsPageSize] = useState(10)
  
  // 表结构弹窗
  const [schemaOpen, setSchemaOpen] = useState(false)
  const [schemaTitle, setSchemaTitle] = useState('')
  const [schemaFields, setSchemaFields] = useState([])
  
  // 采集相关状态
  const [crawlLoading, setCrawlLoading] = useState(false)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [processingId, setProcessingId] = useState(null)
  const [reportImportLoading, setReportImportLoading] = useState(false)
  const [reportProcessLoading, setReportProcessLoading] = useState(false)

  // 表配置（含表结构信息）
  const tableConfig = {
    'resource.ds_basic_info': { 
      title: '数据源基础信息', 
      table: 'ds_basic_info',
      description: '管理数据源登记信息',
      fields: [
        { name: 'ds_id', type: 'VARCHAR(12)', desc: '数据源ID（DS+10位数字）' },
        { name: 'name', type: 'VARCHAR(128)', desc: '数据源名称' },
        { name: 'ds_type', type: 'ENUM', desc: '类型：INTERNET/FILE/API/PRE_DB/FILL' },
        { name: 'data_category', type: 'VARCHAR(64)', desc: '数据分类' },
        { name: 'ds_source', type: 'VARCHAR(256)', desc: '来源地址' },
        { name: 'credibility_score', type: 'DECIMAL(5,2)', desc: '可信度评分' },
        { name: 'is_valid', type: 'BOOLEAN', desc: '是否有效' },
      ]
    },
    'resource.ds_access_task': { 
      title: '数据接入任务', 
      table: 'ds_access_task',
      description: '采集任务配置',
      fields: [
        { name: 'task_id', type: 'VARCHAR(16)', desc: '任务ID' },
        { name: 'ds_id', type: 'VARCHAR(12)', desc: '数据源ID' },
        { name: 'task_name', type: 'VARCHAR(128)', desc: '任务名称' },
        { name: 'access_mode', type: 'ENUM', desc: '模式：FULL/INCREMENT/REAL_TIME' },
        { name: 'schedule_config', type: 'VARCHAR(64)', desc: 'Cron表达式' },
        { name: 'storage_config', type: 'JSON', desc: '存储配置' },
        { name: 'is_valid', type: 'BOOLEAN', desc: '是否有效' },
      ]
    },
    'resource.ds_access_record': { 
      title: '接入执行记录', 
      table: 'ds_access_record',
      description: '任务执行历史',
      fields: [
        { name: 'record_id', type: 'VARCHAR(18)', desc: '记录ID' },
        { name: 'task_id', type: 'VARCHAR(16)', desc: '任务ID' },
        { name: 'exec_status', type: 'ENUM', desc: '状态：RUNNING/SUCCESS/FAILED' },
        { name: 'total_count', type: 'INT', desc: '总数' },
        { name: 'valid_count', type: 'INT', desc: '有效数' },
        { name: 'start_time', type: 'DATETIME', desc: '开始时间' },
        { name: 'end_time', type: 'DATETIME', desc: '结束时间' },
      ]
    },
    'resource.minio_file_index': { 
      title: 'MinIO 文件索引', 
      table: 'minio_file_index',
      description: '文件对象索引',
      fields: [
        { name: 'file_id', type: 'VARCHAR(64)', desc: '文件ID（SHA-256哈希）' },
        { name: 'file_name', type: 'VARCHAR(256)', desc: '文件名' },
        { name: 'file_type', type: 'VARCHAR(16)', desc: '文件类型' },
        { name: 'minio_bucket', type: 'VARCHAR(64)', desc: '存储桶' },
        { name: 'minio_path', type: 'VARCHAR(512)', desc: '存储路径' },
        { name: 'file_size', type: 'BIGINT', desc: '文件大小' },
      ]
    },
    'raw.raw_documents': { 
      title: '原始文档', 
      table: 'resource_*',
      description: '原始采集文档',
      docTypeScope: 'selected',
      fields: [
        { name: 'resource_doc_id', type: 'VARCHAR(21)', desc: '原始文档ID' },
        { name: 'resource_type', type: 'ENUM', desc: '资源类型' },
        { name: 'data_source', type: 'VARCHAR(32)', desc: '数据来源' },
        { name: 'title_raw', type: 'VARCHAR(512)', desc: '原始标题' },
        { name: 'url', type: 'VARCHAR(1024)', desc: '来源URL' },
        { name: 'status', type: 'ENUM', desc: '状态：pending/processed/failed' },
        { name: 'crawl_time', type: 'DATETIME', desc: '采集时间' },
      ]
    },
    'raw.crawled_articles': { 
      title: '历史采集', 
      table: 'crawled_articles',
      description: '历史采集文章',
      docTypeKey: 'news',
      fields: [
        { name: '_id', type: 'ObjectId', desc: '主键' },
        { name: 'title', type: 'String', desc: '标题' },
        { name: 'source', type: 'String', desc: '来源' },
        { name: 'url', type: 'String', desc: 'URL' },
        { name: 'processed', type: 'Boolean', desc: '是否已处理' },
        { name: 'crawled_at', type: 'DateTime', desc: '采集时间' },
      ]
    },
    'resource.source_news': { 
      title: '贴源明细 - 资讯', 
      table: 'resource_news_*',
      description: '资讯类原始资源',
      docTypeKey: 'news',
      fields: []
    },
    'resource.source_report': { 
      title: '贴源明细 - 研报', 
      table: 'resource_report_*',
      description: '研报类原始资源',
      docTypeKey: 'report',
      fields: []
    },
    'resource.inc_document': { 
      title: '标准化文档', 
      table: 'inc_document',
      description: '清洗标准化后的文档',
      docTypeScope: 'selected',
      fields: [
        { name: 'doc_id', type: 'VARCHAR(21)', desc: '文档ID' },
        { name: 'title', type: 'VARCHAR(512)', desc: '标题' },
        { name: 'standard_content', type: 'TEXT', desc: '标准化内容（Markdown）' },
        { name: 'summary', type: 'TEXT', desc: '摘要' },
        { name: 'resource_type', type: 'ENUM', desc: '资源类型' },
        { name: 'status', type: 'ENUM', desc: '状态' },
        { name: 'embedding', type: 'VECTOR', desc: '向量嵌入' },
      ]
    },
  }

  const fetchRecords = async (layer, page = 1, pageSize = 10) => {
    setRecordsLoading(true)
    try {
      const res = await documentPipelineService.getRecords({
        layer,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        doc_type: docType,
      })
      setRecordsData(res.data || [])
      setRecordsTotal(res.total || 0)
      setRecordsFields(res.fields || [])
    } catch (err) {
      message.error(err.message || '获取记录失败')
    } finally {
      setRecordsLoading(false)
    }
  }

  const getDocTypeLabel = (docKey) => {
    if (!docKey) return null
    return docTypeConfig[docKey]?.name || docKey
  }

  const getLayerDocTypeKey = (layerKey) => {
    const config = tableConfig[layerKey]
    if (config?.docTypeKey) return config.docTypeKey
    if (config?.docTypeScope === 'selected') return docType
    return null
  }

  const getLayerDocTypeLabel = (layerKey) => getDocTypeLabel(getLayerDocTypeKey(layerKey))

  const renderDocTypeTag = (docKey, title) => {
    if (!docKey) return null
    const label = getDocTypeLabel(docKey)
    if (title && label && title.includes(label)) return null
    return (
      <Tag color={docTypeConfig[docKey]?.color}>
        {label}
      </Tag>
    )
  }

  const getLayerDisplayTitle = (layerKey) => {
    const config = tableConfig[layerKey]
    const docLabel = getLayerDocTypeLabel(layerKey)
    if (!docLabel) return config?.title || layerKey
    return `${config?.title || layerKey}（${docLabel}）`
  }

  const renderTitleWithDocType = (title, docKey) => {
    if (!docKey) return title
    return (
      <Space size={6} wrap>
        <span>{title}</span>
        {renderDocTypeTag(docKey, title)}
      </Space>
    )
  }

  const openRecords = (layer) => {
    const config = tableConfig[layer]
    setRecordsLayer(layer)
    setRecordsTitle(`${getLayerDisplayTitle(layer)} (${config?.table || layer})`)
    setRecordsPage(1)
    setRecordsPageSize(10)
    setRecordsOpen(true)
    fetchRecords(layer, 1, 10)
  }

  const openSchema = (layer) => {
    const config = tableConfig[layer]
    setSchemaTitle(`表结构：${getLayerDisplayTitle(layer)} (${config?.table})`)
    setSchemaFields(config?.fields || [])
    setSchemaOpen(true)
  }

  const renderValue = (value) => {
    if (value === null || value === undefined) return '--'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  // 采集功能
  const handleCrawlKeyword = async (keyword) => {
    if (!keyword?.trim()) {
      message.warning('请输入关键词')
      return
    }
    setCrawlLoading(true)
    try {
      const response = await dataService.crawlKeyword(keyword.trim())
      message.success(`爬取任务已提交: ${response.task_id}`)
      setTimeout(() => onRefresh?.(), 2000)
    } catch (error) {
      message.error('爬取失败: ' + error.message)
    } finally {
      setCrawlLoading(false)
    }
  }

  const handleUpdateRss = async () => {
    setCrawlLoading(true)
    try {
      const response = await dataService.updateRss()
      message.success(`RSS更新任务已提交: ${response.task_id}`)
      setTimeout(() => onRefresh?.(), 2000)
    } catch (error) {
      message.error('RSS更新失败: ' + error.message)
    } finally {
      setCrawlLoading(false)
    }
  }

  const customUpload = async ({ file, onSuccess, onError }) => {
    try {
      setUploadLoading(true)
      const response = await ingestionService.uploadFile(file, 'file_upload', true)
      onSuccess(response, file)
      message.success(`文件 ${file.name} 上传成功!`)
      onRefresh?.()
    } catch (error) {
      onError(error)
      message.error(`文件上传失败: ${error.message}`)
    } finally {
      setUploadLoading(false)
    }
  }

  const handleBatchProcess = async (limit = 10) => {
    try {
      if (docType === 'report') {
        const res = await reportPipelineService.batchProcess(limit)
        message.success(`已提交 ${res.queued || 0} 篇研报处理`)
      } else {
        const res = await documentPipelineService.batchProcess(limit)
        message.success(`已提交 ${res.queued || 0} 篇文档处理`)
      }
      onRefresh?.()
    } catch (err) {
      message.error(err.message || '批量处理失败')
    }
  }

  const handleReportImport = async (limit = 50) => {
    setReportImportLoading(true)
    try {
      const res = await reportPipelineService.importReports({ limit })
      message.success(`研报导入完成：新增 ${res.imported || 0}，跳过 ${res.skipped || 0}`)
      onRefresh?.()
    } catch (error) {
      message.error(error.message || '研报导入失败')
    } finally {
      setReportImportLoading(false)
    }
  }

  const handleReportBatchProcess = async (limit = 10) => {
    setReportProcessLoading(true)
    try {
      const res = await reportPipelineService.batchProcess(limit)
      message.success(`已提交 ${res.queued || 0} 篇研报处理`)
      onRefresh?.()
    } catch (error) {
      message.error(error.message || '研报批量处理失败')
    } finally {
      setReportProcessLoading(false)
    }
  }

  // 根据文档类型过滤显示的贴源明细
  const getSourceLayerKey = () => {
    return docType === 'report' ? 'resource.source_report' : 'resource.source_news'
  }

  // 渲染表卡片
  const renderTableCard = (layerKey, extraActions) => {
    const config = tableConfig[layerKey]
    const count = layerKey.startsWith('raw.') 
      ? stats?.raw_layer?.[layerKey.split('.')[1]] ?? 0
      : stats?.resource_layer?.[layerKey.split('.')[1]] ?? 0
    
    const docKey = getLayerDocTypeKey(layerKey)
    const docTag = renderDocTypeTag(docKey, config?.title)

    return (
      <Card size="small" style={{ height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Space size={6} wrap>
              <Text strong>{config?.title}</Text>
              {docTag}
            </Space>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>{config?.table}</Text>
          </div>
          <Statistic value={count} valueStyle={{ fontSize: 20 }} />
        </div>
        <div style={{ marginTop: 12 }}>
          <Space size="small">
            <Tooltip title="查看数据">
              <Button size="small" icon={<EyeOutlined />} onClick={() => openRecords(layerKey)}>
                数据
              </Button>
            </Tooltip>
            <Tooltip title="查看表结构">
              <Button size="small" icon={<TableOutlined />} onClick={() => openSchema(layerKey)}>
                结构
              </Button>
            </Tooltip>
            {extraActions}
          </Space>
        </div>
      </Card>
    )
  }

  // 子Tab配置
  const subTabItems = [
    {
      key: 'overview',
      label: '总览',
      children: (
        <div>
          <Row gutter={[16, 16]}>
            {/* 数据源管理 */}
            <Col span={24}>
              <Card title={<><DatabaseOutlined /> 数据源管理</>} size="small">
                <Row gutter={16}>
                  <Col span={6}>{renderTableCard('resource.ds_basic_info')}</Col>
                  <Col span={6}>{renderTableCard('resource.ds_access_task')}</Col>
                  <Col span={6}>{renderTableCard('resource.ds_access_record')}</Col>
                  <Col span={6}>{renderTableCard('resource.minio_file_index')}</Col>
                </Row>
              </Card>
            </Col>

            {/* 原始资源 */}
            <Col span={24}>
              <Card title={<><FileOutlined /> 原始资源（resource_*）</>} size="small">
                <Row gutter={16}>
                  {docType === 'news' && (
                    <Col span={8}>{renderTableCard('raw.raw_documents')}</Col>
                  )}
                  {docType === 'news' && (
                    <Col span={8}>{renderTableCard('raw.crawled_articles')}</Col>
                  )}
                  <Col span={8}>{renderTableCard(getSourceLayerKey())}</Col>
                </Row>
              </Card>
            </Col>

            {/* 标准化文档 */}
            <Col span={24}>
              <Card 
                title={
                  <Space size={6} wrap>
                    <FileOutlined />
                    <span>标准化文档</span>
                    {renderDocTypeTag(docType)}
                  </Space>
                }
                size="small"
                extra={
                  <Button 
                    type="primary" 
                    icon={<ThunderboltOutlined />} 
                    onClick={() => handleBatchProcess(10)}
                  >
                    批量处理(10篇)
                  </Button>
                }
              >
                <Row gutter={16}>
                  <Col span={6}>{renderTableCard('resource.inc_document')}</Col>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title={renderTitleWithDocType('待处理', docType)}
                        value={stats?.resource_layer?.pending ?? 0}
                        valueStyle={{ color: '#faad14' }}
                        prefix={<ClockCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card size="small">
                      <Statistic
                        title={renderTitleWithDocType('已完成', docType)}
                        value={stats?.resource_layer?.completed ?? 0}
                        valueStyle={{ color: '#52c41a' }}
                        prefix={<CheckCircleOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </div>
      ),
    },
    {
      key: 'collect',
      label: '数据采集',
      children: (
        <div>
          <Row gutter={[16, 16]}>
            {/* 采集操作 */}
            <Col span={24}>
              <Card title="快速采集" size="small">
                <Space wrap size="large">
                  {docType === 'news' && (
                    <>
                      <Search
                        placeholder="输入关键词采集"
                        enterButton={<><SearchOutlined /> 开始爬取</>}
                        size="large"
                        onSearch={handleCrawlKeyword}
                        style={{ width: 350 }}
                        loading={crawlLoading}
                      />
                      <Button
                        type="primary"
                        icon={<CloudDownloadOutlined />}
                        size="large"
                        onClick={handleUpdateRss}
                        loading={crawlLoading}
                      >
                        更新RSS订阅
                      </Button>
                    </>
                  )}
                  {docType === 'report' && (
                    <>
                      <Button
                        type="primary"
                        icon={<CloudDownloadOutlined />}
                        size="large"
                        onClick={() => handleReportImport(50)}
                        loading={reportImportLoading}
                      >
                        从ODS导入研报
                      </Button>
                      <Button
                        icon={<ThunderboltOutlined />}
                        size="large"
                        onClick={() => handleReportBatchProcess(10)}
                        loading={reportProcessLoading}
                      >
                        批量处理研报(10篇)
                      </Button>
                    </>
                  )}
                  <Button
                    icon={<SyncOutlined />}
                    size="large"
                    onClick={onRefresh}
                  >
                    刷新统计
                  </Button>
                </Space>
              </Card>
            </Col>

            {/* 文件上传 */}
            <Col span={24}>
              <Card title={<><UploadOutlined /> 文件上传</>} size="small">
                <Upload.Dragger
                  name="file"
                  multiple={false}
                  customRequest={customUpload}
                  accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt,.json,.xml"
                  showUploadList={false}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持 PDF、Excel、CSV、Word、TXT、JSON、XML 格式
                  </p>
                </Upload.Dragger>
                {uploadLoading && (
                  <Progress percent={50} status="active" style={{ marginTop: 16 }} />
                )}
              </Card>
            </Col>

            {/* 采集统计 */}
            <Col span={24}>
              <Card title="采集统计" size="small">
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="数据源"
                      value={stats?.resource_layer?.ds_basic_info ?? 0}
                      prefix={<DatabaseOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="采集任务"
                      value={stats?.resource_layer?.ds_access_task ?? 0}
                      prefix={<PlayCircleOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={renderTitleWithDocType('原始文档', docType)}
                      value={stats?.raw_layer?.raw_documents ?? 0}
                      prefix={<FileOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="文件索引"
                      value={stats?.resource_layer?.minio_file_index ?? 0}
                      prefix={<CloudServerOutlined />}
                    />
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </div>
      ),
    },
  ]

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <DatabaseOutlined style={{ marginRight: 8 }} />
          数据资源层
          <Tag color={docTypeConfig[docType]?.color} style={{ marginLeft: 12 }}>
            {docTypeConfig[docType]?.name}
          </Tag>
        </Title>
        <Text type="secondary">
          管理数据源、采集任务、原始文档和标准化文档。按数据类型筛选，点击可查看表结构和数据。
        </Text>
      </div>

      <Tabs
        activeKey={activeSubTab}
        onChange={setActiveSubTab}
        items={subTabItems}
        size="small"
      />

      {/* 记录详情弹窗 */}
      <Modal
        title={recordsTitle}
        open={recordsOpen}
        onCancel={() => setRecordsOpen(false)}
        footer={null}
        width={1100}
      >
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">字段：{recordsFields.join(', ') || '—'}</Text>
        </div>
        <Table
          rowKey={(record) => record.id || record._id || record.doc_id || JSON.stringify(record)}
          loading={recordsLoading}
          dataSource={recordsData}
          columns={(recordsFields.length ? recordsFields : Object.keys(recordsData?.[0] || {})).map((field) => ({
            title: field,
            dataIndex: field,
            key: field,
            ellipsis: true,
            width: 180,
            render: (value) => <Text>{renderValue(value)}</Text>,
          }))}
          scroll={{ x: 'max-content', y: 420 }}
          pagination={{
            current: recordsPage,
            pageSize: recordsPageSize,
            total: recordsTotal,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (page, pageSize) => {
              setRecordsPage(page)
              setRecordsPageSize(pageSize)
              if (recordsLayer) {
                fetchRecords(recordsLayer, page, pageSize)
              }
            },
          }}
        />
      </Modal>

      {/* 表结构弹窗 */}
      <Modal
        title={schemaTitle}
        open={schemaOpen}
        onCancel={() => setSchemaOpen(false)}
        footer={null}
        width={800}
      >
        <Table
          rowKey="name"
          dataSource={schemaFields}
          columns={[
            { title: '字段名', dataIndex: 'name', key: 'name', width: 180 },
            { title: '类型', dataIndex: 'type', key: 'type', width: 150 },
            { title: '说明', dataIndex: 'desc', key: 'desc' },
          ]}
          pagination={false}
          size="small"
        />
      </Modal>
    </div>
  )
}

export default DataResourceLayer
