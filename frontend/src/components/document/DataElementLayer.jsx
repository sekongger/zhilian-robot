import React, { useState } from 'react'
import { Card, Row, Col, Statistic, Button, Modal, Table, Tag, message, Typography, Collapse, Space, Tooltip, Segmented } from 'antd'
import { ApartmentOutlined, NodeIndexOutlined, ApiOutlined, DatabaseOutlined, EyeOutlined, TableOutlined } from '@ant-design/icons'
import { documentPipelineService } from '../../services/documentPipelineApi'

const { Text, Title } = Typography
const { Panel } = Collapse

/**
 * 数据要素层组件
 * 展示本体模型、知识网络、主题数仓三大模块的统计和详情
 */
const DataElementLayer = ({ docType, docTypeConfig, stats, onRefresh, knowledgeScope, onKnowledgeScopeChange }) => {
  const [recordsOpen, setRecordsOpen] = useState(false)
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsData, setRecordsData] = useState([])
  const [recordsTotal, setRecordsTotal] = useState(0)
  const [recordsFields, setRecordsFields] = useState([])
  const [recordsTitle, setRecordsTitle] = useState('')
  const [recordsLayer, setRecordsLayer] = useState(null)
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsPageSize, setRecordsPageSize] = useState(10)

  const resolvedKnowledgeScope = knowledgeScope || 'selected'
  
  // 表结构弹窗
  const [schemaOpen, setSchemaOpen] = useState(false)
  const [schemaTitle, setSchemaTitle] = useState('')
  const [schemaFields, setSchemaFields] = useState([])

  // 表配置（含表结构信息）
  const tableConfig = {
    // 本体模型
    'ontology.classes': { 
      title: '本体类定义', 
      table: 'inc_ontology_classes',
      fields: [
        { name: 'id', type: 'VARCHAR(14)', desc: '本体类ID（OC+12位数字）' },
        { name: 'name', type: 'VARCHAR(128)', desc: '本体类名称' },
        { name: 'entity_category', type: 'ENUM', desc: '五维分类：concept/subject/element/event/document' },
        { name: 'layer', type: 'ENUM', desc: '分层：core/domain/application' },
        { name: 'parent_class_id', type: 'VARCHAR(14)', desc: '父类ID' },
        { name: 'status', type: 'ENUM', desc: '状态' },
      ]
    },
    'ontology.properties': { 
      title: '属性定义', 
      table: 'inc_property_definitions',
      fields: [
        { name: 'id', type: 'VARCHAR(14)', desc: '属性ID（PD+12位数字）' },
        { name: 'name', type: 'VARCHAR(128)', desc: '属性名称' },
        { name: 'domain_class_id', type: 'VARCHAR(14)', desc: '所属类ID' },
        { name: 'range_type', type: 'ENUM', desc: '值类型' },
        { name: 'is_required', type: 'BOOLEAN', desc: '是否必填' },
        { name: 'unit', type: 'VARCHAR(32)', desc: '计量单位' },
      ]
    },
    'ontology.relations': { 
      title: '关系类型', 
      table: 'inc_relation_types',
      fields: [
        { name: 'id', type: 'VARCHAR(14)', desc: '关系ID（RT+12位数字）' },
        { name: 'name', type: 'VARCHAR(128)', desc: '关系名称' },
        { name: 'source_class_id', type: 'VARCHAR(14)', desc: '主体类ID' },
        { name: 'target_class_id', type: 'VARCHAR(14)', desc: '客体类ID' },
        { name: 'cardinality', type: 'ENUM', desc: '基数约束' },
        { name: 'is_symmetric', type: 'BOOLEAN', desc: '是否对称' },
      ]
    },
    'ontology.axioms': { 
      title: '动作规则', 
      table: 'inc_ontology_activities',
      fields: [
        { name: 'id', type: 'VARCHAR(64)', desc: '动作ID' },
        { name: 'name', type: 'VARCHAR(128)', desc: '动作名称' },
        { name: 'constraint_type', type: 'ENUM', desc: '约束类型' },
        { name: 'expression', type: 'TEXT', desc: '动作表达式' },
      ]
    },
    'ontology.versions': { 
      title: '版本记录', 
      table: 'inc_ontology_versions',
      fields: [
        { name: 'id', type: 'VARCHAR(64)', desc: '版本ID' },
        { name: 'version_code', type: 'VARCHAR(32)', desc: '版本号' },
        { name: 'released_at', type: 'DATETIME', desc: '发布时间' },
        { name: 'change_summary', type: 'TEXT', desc: '变更摘要' },
      ]
    },
    // 知识网络
    'knowledge.entities': { 
      title: '实体实例', 
      table: 'entity_instances',
      docTypeScope: 'selected',
      fields: [
        { name: 'entity_id', type: 'VARCHAR(18)', desc: '实体ID（EN+16位数字）' },
        { name: 'class_id', type: 'VARCHAR(14)', desc: '本体类ID' },
        { name: 'entity_category', type: 'ENUM', desc: '五维分类' },
        { name: 'name', type: 'VARCHAR(256)', desc: '实体名称' },
        { name: 'version', type: 'INT', desc: '版本号' },
        { name: 'status', type: 'ENUM', desc: '状态' },
      ]
    },
    'knowledge.contexts': { 
      title: '上下文', 
      table: 'inc_context',
      docTypeScope: 'selected',
      fields: [
        { name: 'context_id', type: 'VARCHAR(18)', desc: 'ContextID（KC+16位数字）' },
        { name: 'context_type', type: 'ENUM', desc: '类型' },
        { name: 'begin_time', type: 'DATETIME', desc: '生效开始时间' },
        { name: 'end_time', type: 'DATETIME', desc: '生效结束时间' },
        { name: 'doc_id', type: 'VARCHAR(21)', desc: '来源文档ID' },
      ]
    },
    'knowledge.statements': { 
      title: '陈述', 
      table: 'inc_statement',
      docTypeScope: 'selected',
      fields: [
        { name: 'statement_id', type: 'VARCHAR(18)', desc: 'StatementID（ST+16位数字）' },
        { name: 'statement_type', type: 'ENUM', desc: '语句类型：type/property/relation' },
        { name: 'subject_id', type: 'VARCHAR(18)', desc: '主体实体ID' },
        { name: 'predicate_id', type: 'VARCHAR(14)', desc: '属性/关系ID' },
        { name: 'object_type', type: 'ENUM', desc: '客体类型' },
        { name: 'confidence', type: 'DECIMAL(5,4)', desc: '置信度' },
        { name: 'context_id', type: 'VARCHAR(18)', desc: '上下文ID' },
      ]
    },
    'knowledge.micro_document': {
      title: '微文档',
      table: 'micro_document',
      docTypeScope: 'selected',
      fields: [
        { name: 'micro_document_id', type: 'VARCHAR(24)', desc: '微文档ID' },
        { name: 'doc_id', type: 'VARCHAR(21)', desc: '来源文档ID' },
        { name: 'block_type', type: 'VARCHAR(32)', desc: '内容块类型' },
        { name: 'block', type: 'TEXT', desc: '内容块文本' },
        { name: 'created_at', type: 'DATETIME', desc: '创建时间' },
      ]
    },
    // 图谱/向量
    'graph.nodes': { 
      title: '图谱节点', 
      table: 'Neo4j Nodes',
      fields: [
        { name: 'id', type: 'STRING', desc: '节点ID' },
        { name: 'labels', type: 'LIST', desc: '节点标签' },
        { name: 'properties', type: 'MAP', desc: '节点属性' },
      ]
    },
    'graph.relations': { 
      title: '图谱关系', 
      table: 'Neo4j Relationships',
      fields: [
        { name: 'id', type: 'STRING', desc: '关系ID' },
        { name: 'type', type: 'STRING', desc: '关系类型' },
        { name: 'startNode', type: 'STRING', desc: '起始节点' },
        { name: 'endNode', type: 'STRING', desc: '终止节点' },
      ]
    },
    'vector.entity_vectors': { 
      title: '实体向量', 
      table: 'Milvus entity_vectors',
      docTypeScope: 'selected',
      fields: [
        { name: 'id', type: 'INT64', desc: '主键' },
        { name: 'entity_id', type: 'VARCHAR', desc: '实体ID' },
        { name: 'embedding', type: 'FLOAT_VECTOR(768)', desc: '向量' },
      ]
    },
    'vector.document_vectors': { 
      title: '文档向量', 
      table: 'Milvus document_vectors',
      docTypeScope: 'selected',
      fields: [
        { name: 'id', type: 'INT64', desc: '主键' },
        { name: 'doc_id', type: 'VARCHAR', desc: '文档ID' },
        { name: 'embedding', type: 'FLOAT_VECTOR(768)', desc: '向量' },
      ]
    },
    // 主题数仓
    'warehouse.indicators': { 
      title: '指标口径', 
      table: 'indicator_dictionary',
      fields: [
        { name: 'indicator_id', type: 'VARCHAR(14)', desc: '指标ID（MI+12位数字）' },
        { name: 'indicator_name', type: 'VARCHAR(128)', desc: '指标名称' },
        { name: 'indicator_type', type: 'ENUM', desc: '指标类型' },
        { name: 'calculation_formula', type: 'TEXT', desc: '计算公式' },
        { name: 'data_source', type: 'VARCHAR(64)', desc: '数据来源' },
      ]
    },
    'warehouse.indicator_mappings': { 
      title: '指标映射', 
      table: 'indicator_ontology_mappings',
      fields: [
        { name: 'mapping_id', type: 'BIGINT', desc: '映射ID' },
        { name: 'indicator_id', type: 'VARCHAR(14)', desc: '指标ID' },
        { name: 'property_id', type: 'VARCHAR(14)', desc: '本体属性ID' },
        { name: 'mapping_rule', type: 'TEXT', desc: '映射规则' },
      ]
    },
    'warehouse.entity_mappings': { 
      title: '实体ID映射', 
      table: 'entity_id_mappings',
      fields: [
        { name: 'mapping_id', type: 'BIGINT', desc: '映射ID' },
        { name: 'entity_id', type: 'VARCHAR(18)', desc: '知识网络实体ID' },
        { name: 'warehouse_id', type: 'VARCHAR(64)', desc: '数仓维度ID' },
        { name: 'entity_type', type: 'VARCHAR(32)', desc: '实体类型' },
      ]
    },
  }

  const getDocTypeLabel = (docKey) => {
    if (!docKey) return null
    return docTypeConfig[docKey]?.name || docKey
  }

  const getLayerDocTypeKey = (layerKey) => {
    const config = tableConfig[layerKey]
    if (layerKey?.startsWith('knowledge.') && resolvedKnowledgeScope === 'all') return null
    if (config?.docTypeKey) return config.docTypeKey
    if (config?.docTypeScope === 'selected') return docType
    return null
  }

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

  const getLayerDisplayTitle = (layerKey, fallbackTitle) => {
    const config = tableConfig[layerKey]
    const baseTitle = config?.title || fallbackTitle || layerKey
    const docLabel = getDocTypeLabel(getLayerDocTypeKey(layerKey))
    if (!docLabel) return baseTitle
    return `${baseTitle}（${docLabel}）`
  }

  const fetchRecords = async (layer, page = 1, pageSize = 10) => {
    setRecordsLoading(true)
    try {
      const shouldApplyDocType = !(layer?.startsWith('knowledge.') && resolvedKnowledgeScope === 'all')
      const res = await documentPipelineService.getRecords({
        layer,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        doc_type: shouldApplyDocType ? docType : undefined,
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

  const openRecords = (layer) => {
    const config = tableConfig[layer]
    setRecordsLayer(layer)
    setRecordsTitle(`${getLayerDisplayTitle(layer, '记录详情')} (${config?.table || layer})`)
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

  // 渲染表卡片（带数据和结构按钮）
  const renderTableCard = (layerKey, statValue, statTitle) => {
    const config = tableConfig[layerKey]
    const docTag = renderDocTypeTag(getLayerDocTypeKey(layerKey), statTitle || config?.title)
    return (
      <Card size="small" style={{ height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Space size={6} wrap>
              <Text strong>{statTitle || config?.title}</Text>
              {docTag}
            </Space>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>{config?.table}</Text>
          </div>
          <Statistic value={statValue ?? 0} valueStyle={{ fontSize: 18 }} />
        </div>
        <div style={{ marginTop: 8 }}>
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
          </Space>
        </div>
      </Card>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <ApartmentOutlined style={{ marginRight: 8 }} />
          数据要素层
          <Tag color={docTypeConfig[docType]?.color} style={{ marginLeft: 12 }}>
            {docTypeConfig[docType]?.name}
          </Tag>
        </Title>
        <Text type="secondary">
          包含本体模型（规范层）、知识网络（实例层）、主题数仓（分析层）三大核心模块。点击可查看表结构和数据。
        </Text>
      </div>

      <Collapse defaultActiveKey={['ontology', 'knowledge', 'warehouse']} ghost>
        {/* 本体模型 */}
        <Panel
          header={
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              <NodeIndexOutlined style={{ marginRight: 8 }} />
              本体模型（规范层）
              <Tag color="purple" style={{ marginLeft: 12 }}>MySQL</Tag>
            </span>
          }
          key="ontology"
        >
          <Card size="small">
            <Row gutter={[16, 16]}>
              <Col span={4}>
                {renderTableCard('ontology.classes', stats?.ontology_layer?.total_classes, '本体类')}
              </Col>
              <Col span={4}>
                {renderTableCard('ontology.properties', stats?.ontology_layer?.total_properties, '属性定义')}
              </Col>
              <Col span={4}>
                {renderTableCard('ontology.relations', stats?.ontology_layer?.total_relations, '关系类型')}
              </Col>
              <Col span={4}>
                {renderTableCard('ontology.axioms', stats?.ontology_layer?.total_axioms, '动作规则')}
              </Col>
              <Col span={4}>
                {renderTableCard('ontology.versions', stats?.ontology_layer?.total_versions, '版本记录')}
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="五维分类" value="5类" valueStyle={{ fontSize: 16 }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    概念/主体/要素/事件/文档
                  </Text>
                </Card>
              </Col>
            </Row>
          </Card>
        </Panel>

        {/* 知识网络 */}
        <Panel
          header={
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              知识网络（实例层）
              <Tag color="blue" style={{ marginLeft: 12 }}>MongoDB + Neo4j + Milvus</Tag>
            </span>
          }
          key="knowledge"
        >
          <Card size="small" style={{ marginBottom: 12 }}>
            <Space size={12} wrap>
              <Text strong>知识网络筛选</Text>
              <Segmented
                options={[
                  { label: '当前文档类型', value: 'selected' },
                  { label: '全部', value: 'all' },
                ]}
                value={resolvedKnowledgeScope}
                onChange={(value) => onKnowledgeScopeChange?.(value)}
              />
            </Space>
          </Card>
          <Row gutter={[16, 16]}>
            {/* 知识网络4大核心 */}
            <Col span={24}>
              <Card title="知识网络核心集合（4大核心）" size="small">
                <Row gutter={16}>
                  <Col span={4}>
                    {renderTableCard('knowledge.entities', stats?.knowledge_layer?.entities, '实体')}
                  </Col>
                  <Col span={4}>
                    {renderTableCard('knowledge.statements', stats?.knowledge_layer?.statements, '陈述')}
                  </Col>
                  <Col span={4}>
                    {renderTableCard('knowledge.contexts', stats?.knowledge_layer?.contexts, '上下文')}
                  </Col>
                  <Col span={4}>
                    {renderTableCard('knowledge.micro_document', stats?.knowledge_layer?.micro_documents, '微文档')}
                  </Col>
                  <Col span={4}>
                    <Card size="small">
                      <Statistic 
                        title="陈述类型" 
                        value="3类" 
                        valueStyle={{ fontSize: 16 }}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>type/property/relation</Text>
                    </Card>
                  </Col>
                </Row>
              </Card>
            </Col>


            {/* 图谱索引 */}
            <Col span={12}>
              <Card title="图谱库（Neo4j）" size="small">
                <Row gutter={16}>
                  <Col span={12}>
                    {renderTableCard('graph.nodes', stats?.graph_layer?.nodes, '图谱节点')}
                  </Col>
                  <Col span={12}>
                    {renderTableCard('graph.relations', stats?.graph_layer?.relations, '图谱关系')}
                  </Col>
                </Row>
              </Card>
            </Col>

            {/* 向量索引 */}
            <Col span={12}>
              <Card title="向量库（Milvus）" size="small">
                <Row gutter={16}>
                  <Col span={8}>
                    {renderTableCard('vector.entity_vectors', stats?.vector_layer?.entity_vectors, '实体向量')}
                  </Col>
                  <Col span={8}>
                    {renderTableCard('vector.document_vectors', stats?.vector_layer?.document_vectors, '文档向量')}
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic 
                        title="向量维度" 
                        value={768} 
                        valueStyle={{ fontSize: 18 }}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>BGE-M3</Text>
                    </Card>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </Panel>

        {/* 主题数仓 */}
        <Panel
          header={
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              <ApiOutlined style={{ marginRight: 8 }} />
              主题数仓（分析层）
              <Tag color="orange" style={{ marginLeft: 12 }}>Doris</Tag>
            </span>
          }
          key="warehouse"
        >
          <Card size="small">
            <Row gutter={16}>
              <Col span={6}>
                {renderTableCard('warehouse.indicators', stats?.warehouse_layer?.indicators, '指标口径')}
              </Col>
              <Col span={6}>
                {renderTableCard('warehouse.indicator_mappings', stats?.warehouse_layer?.indicator_mappings, '指标映射')}
              </Col>
              <Col span={6}>
                {renderTableCard('warehouse.entity_mappings', stats?.warehouse_layer?.entity_mappings, '实体ID映射')}
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="DWD明细层" value="按需构建" valueStyle={{ fontSize: 14, color: '#888' }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>dwd_entity_fact</Text>
                </Card>
              </Col>
            </Row>
          </Card>
        </Panel>
      </Collapse>

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
          rowKey={(record) => record.id || record._id || record.entity_id || record.statement_id || JSON.stringify(record)}
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

export default DataElementLayer
