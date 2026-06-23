import React from 'react'
import {
  Card,
  Tabs,
  Table,
  Tag,
  Row,
  Col,
  Typography,
  Divider,
  List,
  Collapse,
  Space
} from 'antd'
import {
  ApartmentOutlined,
  DatabaseOutlined,
  SafetyCertificateOutlined,
  NodeIndexOutlined,
  FileTextOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

const architectureColumns = [
  { title: '架构层级', dataIndex: 'layer', key: 'layer', width: 140 },
  { title: '核心功能', dataIndex: 'function', key: 'function' },
  { title: '决策支撑', dataIndex: 'decision', key: 'decision' },
  { title: '可扩展要点', dataIndex: 'extend', key: 'extend' }
]

const architectureData = [
  {
    key: 'class',
    layer: '类体系层',
    function: '定义核心实体类型及层级关系，明确“产业网基底”与“产业链主线”划分。',
    decision: '界定决策分析核心要素范围。',
    extend: '预留新兴子类扩展位与属性继承重定义。'
  },
  {
    key: 'property',
    layer: '属性体系层',
    function: '定义对象属性与数据属性，区分复用、场景、扩展三类属性。',
    decision: '刻画要素支撑与价值传导逻辑。',
    extend: '扩展属性组与约束可配置。'
  },
  {
    key: 'instance',
    layer: '实例体系层',
    function: '以“实体实例+Statement（内嵌Context）”组织事实数据。',
    decision: '提供结构化、可追溯事实依据。',
    extend: '支持语句类型与上下文维度扩展。'
  },
  {
    key: 'axiom',
    layer: '公理体系层',
    function: '定义运行规律与推理规则，分核心与扩展公理。',
    decision: '推理隐性知识，形成可信判断。',
    extend: '公理模块可启停与场景化扩展。'
  },
  {
    key: 'decision',
    layer: '决策适配层',
    function: '封装推理接口与分析模板，提供场景化插件。',
    decision: '输出可信决策建议与洞察。',
    extend: '兼容多决策系统协议与插件新增。'
  }
]

const storageLayerColumns = [
  { title: '层级', dataIndex: 'layer', key: 'layer', width: 160 },
  { title: '组件', dataIndex: 'components', key: 'components' },
  { title: '说明', dataIndex: 'desc', key: 'desc' }
]

const storageLayerData = [
  {
    key: 'service',
    layer: '数据服务层',
    components: 'GraphQL、REST API、SPARQL、向量检索',
    desc: '统一查询与CRUD、语义查询与相似度检索入口。'
  },
  {
    key: 'master',
    layer: '主数据层',
    components: '元数据库、实例存储、图数据层、向量索引层',
    desc: '本体定义与实例三层结构协同，支撑关系与向量检索。'
  },
  {
    key: 'resource',
    layer: '数据资源层',
    components: 'MongoDB、MySQL结构化源、MinIO、Redis',
    desc: '原始数据、结构化数据源、对象存储与缓存支撑。'
  }
]

const masterModules = [
  {
    key: 'metadata',
    title: '元数据库（Metadata DB）',
    content: 'inc_ontology_classes / inc_property_definitions / inc_relation_types'
  },
  {
    key: 'instance',
    title: '实例存储三层结构',
    content: 'entity_instances / statements（内嵌Context字段）'
  },
  {
    key: 'graph',
    title: '图数据层（Neo4j）',
    content: '仅存储实体关系，节点为实体ID引用。'
  },
  {
    key: 'vector',
    title: '向量索引层（Milvus）',
    content: '实体与Statement语义向量索引与检索。'
  }
]

const resourceModules = [
  {
    key: 'mongo',
    title: 'MongoDB 非结构化数据',
    items: ['raw_documents_*', 'crawler_data', 'api_responses']
  },
  {
    key: 'mysql',
    title: 'MySQL 结构化数据源',
    items: ['source_companies', 'source_products', 'source_patents']
  },
  {
    key: 'minio',
    title: 'MinIO 对象存储',
    items: ['文件、图片、附件']
  },
  {
    key: 'redis',
    title: 'Redis 缓存层',
    items: ['热点数据、会话、临时状态']
  }
]

const techStack = [
  'MySQL 8.0+：元数据与实例存储',
  'MongoDB 6.0+：原始数据与文档',
  'Neo4j 5.0+：关系图谱（仅关系）',
  'Milvus 2.3+：语义向量索引',
  'Redis 7.0+：缓存与会话',
  'MinIO：对象存储'
]

const coreClassColumns = [
  { title: '顶层类', dataIndex: 'name', key: 'name', width: 140 },
  { title: '核心定义', dataIndex: 'definition', key: 'definition' },
  { title: '核心子类', dataIndex: 'sub', key: 'sub' },
  { title: 'CIDOC CRM映射', dataIndex: 'mapping', key: 'mapping', width: 160 }
]

const coreClassData = [
  {
    key: 'concept',
    name: '产业概念类',
    definition: '描述产业网链的抽象结构与分类属性，是决策分析语义锚点。',
    sub: '产业网、产业链、产业节点、产业价值环节',
    mapping: 'E28 Conceptual Object'
  },
  {
    key: 'actor',
    name: '产业主体类',
    definition: '参与产业网链活动的异质性角色。',
    sub: '企业、科研机构、政府/监管主体、金融机构等',
    mapping: 'E39 Actor'
  },
  {
    key: 'object',
    name: '产业对象类',
    definition: '支撑产业网链运行的资源与规则。',
    sub: '物质对象、技术对象、资金对象、人力资源等',
    mapping: 'E70 Thing'
  },
  {
    key: 'event',
    name: '产业事件类',
    definition: '记录主体与对象的动态交互过程。',
    sub: '交易、合作、创新、投融资、政策发布事件等',
    mapping: 'E5 Event'
  },
  {
    key: 'document',
    name: '产业文档类',
    definition: '记录实体与事件的凭证性文档。',
    sub: '资讯、专利、研报、政策、标准文档等',
    mapping: 'E31 Document'
  }
]

const supportClasses = [
  {
    key: 'identifier',
    title: '标识要素',
    mapping: 'E41 Appellation',
    description: '标识编码、名称、称谓等，保障跨系统唯一识别与溯源。'
  },
  {
    key: 'type',
    title: '类型要素',
    mapping: 'E55 Type',
    description: '基于产业分类标准构建的专业化分类术语。'
  },
  {
    key: 'time',
    title: '时间要素',
    mapping: 'E52 Time-Span',
    description: '刻画产业网链实体的周期、发生时点与时间跨度。'
  },
  {
    key: 'space',
    title: '空间要素',
    mapping: 'E53 Place',
    description: '定位产业实体地理或物理位置，支持空间层级表达。'
  }
]

const conceptCards = [
  {
    key: 'network',
    title: '产业网（1网）',
    tag: '基底',
    content: '全域要素集成基底，整合主体、资源、技术与制度规则。'
  },
  {
    key: 'chain',
    title: '产业链（N链）',
    tag: '主线',
    content: '围绕核心产品/服务的价值传导谱系，依托产业网获取要素。'
  },
  {
    key: 'node',
    title: '产业节点',
    tag: '枢纽',
    content: '产业网与多条产业链的交汇单元，承载细分产业功能。'
  },
  {
    key: 'value',
    title: '产业价值环节',
    tag: '价值单元',
    content: '研发、原材料、制造、营销、服务等核心价值流程。'
  }
]

const objectPropertyData = [
  { key: 'p2', property: 'P2 has type', scenario: '产业节点与细分产业类型关联' },
  { key: 'p4', property: 'P4 has time-span', scenario: '实体与时间跨度关联' },
  { key: 'p7', property: 'P7 took place at', scenario: '事件与空间位置关联' },
  { key: 'p11', property: 'P11 had participant', scenario: '主体参与事件' },
  { key: 'supports', property: 'supportsIndustryChain', scenario: '产业网支撑产业链' },
  { key: 'feedback', property: 'feedsBackToIndustryNetwork', scenario: '产业链反哺产业网' },
  { key: 'contains', property: 'containsIndustryNode', scenario: '产业网包含产业节点' },
  { key: 'transmit', property: 'transmitsValueTo', scenario: '产业链价值传导' }
]

const dataPropertyData = [
  {
    key: 'actor',
    type: '产业主体类',
    core: '主体编码、名称、类型、业务范围、技术实力等级、专利数量',
    extend: '跨境合作经验、数字化能力、碳足迹'
  },
  {
    key: 'object',
    type: '产业对象类',
    core: '资源编码、名称、类型、所属领域、技术成熟度、市场价值',
    extend: '数字资产价值、绿色认证等级'
  },
  {
    key: 'concept',
    type: '产业概念类',
    core: '网链/节点编码、名称、核心功能描述、覆盖范围',
    extend: '数字化水平、绿色发展程度'
  },
  {
    key: 'event',
    type: '产业事件类',
    core: '事件编码、名称、开始/结束时间、规模、结果',
    extend: '跨境合作规模、数字仿真结果'
  },
  {
    key: 'document',
    type: '产业文档类',
    core: '文档编码、名称、发布时间、格式、存储地址',
    extend: '可信度评分、跨境适配标注'
  }
]

const axiomPanels = [
  {
    key: 'basic',
    label: '基础约束公理（规则底线）',
    content: [
      '产业网链实例必须包含1个产业网实例与≥1条产业链实例。',
      '产业节点必须与细分类型一一对应，且关联≥1个要素挂接关系。',
      '要素挂接事件开始时间必须早于结束时间。'
    ]
  },
  {
    key: 'decision',
    label: '决策场景公理（推理核心）',
    content: [
      '挂接优先级：关键环节 + 需求强 + 覆盖率低 + 技术成熟度高 → 优先级最高。',
      '适配性：领域匹配度≥85%且成本/周期满足约束 → 适配等级为优。',
      '协同预判：核心技术要素≥2且协同度≥90% → 价值创造效率提升40%。'
    ]
  },
  {
    key: 'evolution',
    label: '演化适配公理（动态扩展）',
    content: [
      '数字要素适配度≥95% → 自动匹配数字要素需求标签。',
      '核心技术要素占比≥70%且持续运营≥2年 → 升级为核心产业节点。',
      '新增绿色政策文档 → 绿色要素挂接优先级提升与补贴。'
    ]
  }
]

const instanceLayers = [
  {
    key: 'entity',
    title: '实体实例层',
    desc: '按类体系生成实例，遵循唯一编码+核心元信息规范。'
  },
  {
    key: 'statement',
    title: 'Statement层',
    desc: '类型、属性、关系语句结构化表达实例语义，并内嵌上下文字段。'
  }
]

const modelingFlow = [
  '明确产业网链细分领域与核心产品方向。',
  '梳理1张产业网的要素构成与覆盖范围。',
  '识别N条产业链并拆解价值环节。',
  '确定产业节点并建立链-网嵌入关系。',
  '复用属性体系并实例化实体与关系。',
  '验证多链协同与要素支撑逻辑，迭代优化。'
]

const decisionScenarios = [
  {
    key: 'tech',
    title: '技术攻关决策',
    desc: '基于产业链痛点与产业网资源，确定攻关方向与主体匹配。'
  },
  {
    key: 'invest',
    title: '投资决策评估',
    desc: '评估企业在产业链地位与资源关联度，输出投资优先级。'
  },
  {
    key: 'cooperate',
    title: '产业合作决策',
    desc: '基于需求互补与链网协同，匹配合作主体与合作模式。'
  },
  {
    key: 'transform',
    title: '成果转化决策',
    desc: '评估技术成果产业化适配性与产业网支撑潜力。'
  }
]

const constraints = [
  '产业网链必须包含1个产业网与至少1条产业链。',
  '产业节点与细分类型一一对应，且至少挂接1条要素关系。',
  '核心类实例必须包含编码、名称、时间跨度必选属性。',
  '属性默认量化规则为多对多（0,n:0,n）。'
]

const extensionRules = [
  '新增子类需继承父类语义与属性并完成兼容性测试。',
  '扩展属性需明确定义域、值域并标注产业扩展标签。',
  '新增公理需通过专家评审并接入扩展模块。'
]

const toolSupport = [
  'MySQL：本体建模与结构化管理',
  'ArangoDB：知识图谱存储与检索',
  'Apache Jena：语义推理与规则执行',
  'RDF / JSON-LD：数据交换与系统集成'
]

const OntologyPage = () => {

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} xl={16}>
          <Card style={{ height: '100%' }}>
            <Title level={2} style={{ marginBottom: 8 }}>
              <ApartmentOutlined style={{ marginRight: 12 }} />
              产业网链存储架构
            </Title>
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              基于 CIDOC CRM 标准与“1张产业网 + N条产业链”的协同逻辑，构建可信、可扩展的知识存储与推理架构，支撑产业网链的语义建模、决策推理与动态演化。
            </Paragraph>
            <Space style={{ flexWrap: 'wrap' }}>
              <Tag color="geekblue">三层存储架构</Tag>
              <Tag color="cyan">Statement（内嵌Context）</Tag>
              <Tag color="purple">多数据库协同</Tag>
              <Tag color="gold">本体驱动</Tag>
              <Tag color="green">状态可追溯</Tag>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="建模目标与原则" style={{ height: '100%' }}>
            <List
              size="small"
              dataSource={[
                '本体与实例分离，元数据与实例数据独立管理。',
                'Statement 中心化表达属性，支持多值与时态。',
                '上下文字段内嵌到 Statement，简化溯源、置信度与审核状态管理。',
                '数据全生命周期状态可管理，支持扩展演化。'
              ]}
              renderItem={(item) => (
                <List.Item>
                  <Text>{item}</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="architecture"
        items={[
          {
            key: 'storage',
            label: <span><DatabaseOutlined /> 存储架构</span>,
            children: (
              <>
                <Card title="三层存储架构" style={{ marginBottom: 16 }}>
                  <Table
                    columns={storageLayerColumns}
                    dataSource={storageLayerData}
                    pagination={false}
                    rowKey="key"
                  />
                </Card>
                <Card title="主数据层核心模块" style={{ marginBottom: 16 }}>
                  <Row gutter={[16, 16]}>
                    {masterModules.map((module) => (
                      <Col xs={24} md={12} key={module.key}>
                        <Card size="small">
                          <Title level={5} style={{ marginBottom: 8 }}>{module.title}</Title>
                          <Text type="secondary">{module.content}</Text>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
                <Card title="数据资源层组件">
                  <Row gutter={[16, 16]}>
                    {resourceModules.map((module) => (
                      <Col xs={24} md={12} key={module.key}>
                        <Card size="small">
                          <Title level={5} style={{ marginBottom: 8 }}>{module.title}</Title>
                          <List
                            size="small"
                            dataSource={module.items}
                            renderItem={(item) => (
                              <List.Item>
                                <Text>{item}</Text>
                              </List.Item>
                            )}
                          />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
              </>
            )
          },
          {
            key: 'architecture',
            label: <span><ClusterOutlined /> 本体架构</span>,
            children: (
              <>
                <Card title="五层可扩展架构" style={{ marginBottom: 16 }}>
                  <Table
                    columns={architectureColumns}
                    dataSource={architectureData}
                    pagination={false}
                    rowKey="key"
                  />
                </Card>
                <Card title="1网N链核心概念">
                  <Row gutter={[16, 16]}>
                    {conceptCards.map((card) => (
                      <Col xs={24} md={12} xl={6} key={card.key}>
                        <Card size="small" style={{ height: '100%' }}>
                          <Tag color="purple" style={{ marginBottom: 12 }}>{card.tag}</Tag>
                          <Title level={5} style={{ marginBottom: 8 }}>{card.title}</Title>
                          <Text type="secondary">{card.content}</Text>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
                <Card title="技术栈" style={{ marginTop: 16 }}>
                  <List
                    size="small"
                    dataSource={techStack}
                    renderItem={(item) => (
                      <List.Item>
                        <Text>{item}</Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </>
            )
          },
          {
            key: 'classes',
            label: <span><ApartmentOutlined /> 类体系</span>,
            children: (
              <>
                <Card title="五大顶层核心类" style={{ marginBottom: 16 }}>
                  <Table
                    columns={coreClassColumns}
                    dataSource={coreClassData}
                    pagination={false}
                    rowKey="key"
                  />
                </Card>
                <Card title="四大通用支撑类">
                  <Row gutter={[16, 16]}>
                    {supportClasses.map((item) => (
                      <Col xs={24} md={12} key={item.key}>
                        <Card size="small">
                          <Title level={5} style={{ marginBottom: 4 }}>{item.title}</Title>
                          <Text type="secondary">CIDOC 映射：{item.mapping}</Text>
                          <Divider style={{ margin: '12px 0' }} />
                          <Text>{item.description}</Text>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
              </>
            )
          },
          {
            key: 'properties',
            label: <span><FileTextOutlined /> 属性体系</span>,
            children: (
              <>
                <Card title="对象属性（核心关联关系）" style={{ marginBottom: 16 }}>
                  <Table
                    columns={[
                      { title: '属性', dataIndex: 'property', key: 'property', width: 220 },
                      { title: '应用场景', dataIndex: 'scenario', key: 'scenario' }
                    ]}
                    dataSource={objectPropertyData}
                    pagination={false}
                    rowKey="key"
                  />
                </Card>
                <Card title="数据属性（核心特征与扩展）">
                  <Table
                    columns={[
                      { title: '实体类型', dataIndex: 'type', key: 'type', width: 140 },
                      { title: '核心属性', dataIndex: 'core', key: 'core' },
                      { title: '扩展属性', dataIndex: 'extend', key: 'extend' }
                    ]}
                    dataSource={dataPropertyData}
                    pagination={false}
                    rowKey="key"
                  />
                </Card>
              </>
            )
          },
          {
            key: 'axioms',
            label: <span><SafetyCertificateOutlined /> 公理与推理</span>,
            children: (
              <>
                <Card title="公理体系" style={{ marginBottom: 16 }}>
                  <Collapse
                    items={axiomPanels.map((panel) => ({
                      key: panel.key,
                      label: panel.label,
                      children: (
                        <List
                          size="small"
                          dataSource={panel.content}
                          renderItem={(item) => (
                            <List.Item>
                              <Text>{item}</Text>
                            </List.Item>
                          )}
                        />
                      )
                    }))}
                    defaultActiveKey={['basic']}
                  />
                </Card>
                <Card title="典型决策推理场景">
                  <Row gutter={[16, 16]}>
                    {decisionScenarios.map((scenario) => (
                      <Col xs={24} md={12} key={scenario.key}>
                        <Card size="small">
                          <Title level={5} style={{ marginBottom: 8 }}>{scenario.title}</Title>
                          <Text type="secondary">{scenario.desc}</Text>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
              </>
            )
          },
          {
            key: 'instances',
            label: <span><NodeIndexOutlined /> 实例与落地</span>,
            children: (
              <>
                <Card title="实例体系三层结构" style={{ marginBottom: 16 }}>
                  <Row gutter={[16, 16]}>
                    {instanceLayers.map((layer) => (
                      <Col xs={24} md={8} key={layer.key}>
                        <Card size="small" style={{ height: '100%' }}>
                          <Title level={5}>{layer.title}</Title>
                          <Text type="secondary">{layer.desc}</Text>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
                <Row gutter={[16, 16]}>
                  <Col xs={24} xl={12}>
                    <Card title="建模落地流程">
                      <List
                        size="small"
                        dataSource={modelingFlow}
                        renderItem={(item) => (
                          <List.Item>
                            <Text>{item}</Text>
                          </List.Item>
                        )}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} xl={12}>
                    <Card title="约束与扩展规则">
                      <Divider orientation="left">核心约束</Divider>
                      <List
                        size="small"
                        dataSource={constraints}
                        renderItem={(item) => (
                          <List.Item>
                            <Text>{item}</Text>
                          </List.Item>
                        )}
                      />
                      <Divider orientation="left">扩展规则</Divider>
                      <List
                        size="small"
                        dataSource={extensionRules}
                        renderItem={(item) => (
                          <List.Item>
                            <Text>{item}</Text>
                          </List.Item>
                        )}
                      />
                    </Card>
                  </Col>
                </Row>
                <Card title="工具支持" style={{ marginTop: 16 }}>
                  <List
                    size="small"
                    dataSource={toolSupport}
                    renderItem={(item) => (
                      <List.Item>
                        <Text>{item}</Text>
                      </List.Item>
                    )}
                  />
                </Card>
              </>
            )
          }
        ]}
      />
    </div>
  )
}

export default OntologyPage
