import React, { useState } from 'react'
import { Card, Tabs, Table, Tag, Row, Col, Typography, Space, Alert, Timeline, Divider, Badge } from 'antd'
import {
    DatabaseOutlined, ApartmentOutlined, CloudServerOutlined, ApiOutlined, SyncOutlined,
    CheckCircleOutlined, ArrowRightOutlined, ClusterOutlined, FileTextOutlined,
    NodeIndexOutlined, GlobalOutlined, ThunderboltOutlined, SafetyCertificateOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

const StorageArchitecturePage = () => {
    const [activeTab, setActiveTab] = useState('overview')

    // 三层架构定义
    const architectureLayers = [
        {
            key: 'service', title: '数据服务层', subtitle: '检索/推理/场景',
            icon: <ApiOutlined />, color: '#8b5cf6',
            components: ['ES统一索引', 'Redis缓存', 'API网关', '查询编排', '向量检索'],
            description: '对外服务接口，提供统一查询、推理与场景输出能力'
        },
        {
            key: 'element', title: '数据要素层', subtitle: '语义与知识',
            icon: <DatabaseOutlined />, color: '#3b82f6',
            components: ['本体模型库', '实例知识库', '主题数仓', '图谱/向量索引'],
            description: '核心数据存储，承载本体规范、实例知识与主题分析'
        },
        {
            key: 'resource', title: '数据资源层', subtitle: '原始与贴源',
            icon: <CloudServerOutlined />, color: '#10b981',
            components: ['多源接入', '贴源明细', '对象存储', '元数据管理'],
            description: '原始数据采集与标准化，提供可治理的数据底座'
        }
    ]

    // 三库关系
    const threeLibraries = [
        {
            key: 'ontology', name: '本体模型库', nameEn: 'Ontology Schema Registry',
            role: '规范层', icon: <ApartmentOutlined />, color: '#6366f1',
            content: '领域概念/关系词汇表、概念层级/逻辑关系、公理与约束（TBox）',
            nature: '低频变化、稳定、规模小', users: '建模专家与标准制定',
            operations: '建模、版本控制、发布/回滚、校验与映射规则生成'
        },
        {
            key: 'instance', name: '实例知识库', nameEn: 'Instance Knowledge Base',
            role: '实例层', icon: <ClusterOutlined />, color: '#3b82f6',
            content: '具体实体、事实三元组/Statement、带上下文的动态记录（ABox）',
            nature: '高频变化、规模大', users: '业务应用与分析',
            operations: '高吞吐写入、幂等插入、溯源查询、图谱/向量派生索引'
        },
        {
            key: 'warehouse', name: '主题数仓', nameEn: 'Subject Data Warehouse',
            role: '分析层', icon: <NodeIndexOutlined />, color: '#10b981',
            content: '主题化结构化指标与维度，指标口径映射本体属性',
            nature: '按主题组织、面向分析', users: '数据分析与决策支持',
            operations: '指标计算、维度聚合、口径对齐、实例ID绑定'
        }
    ]

    // 数据流闭环
    const dataFlowSteps = [
        { title: '原始保真', desc: '多源接入 → 文档/对象/结构化贴源库', icon: <FileTextOutlined /> },
        { title: '标准明细', desc: '形成可治理的宽表/文档集合', icon: <CheckCircleOutlined /> },
        { title: '语义对齐', desc: '本体模型驱动映射与全局ID对齐', icon: <SyncOutlined /> },
        { title: '知识沉淀', desc: 'Entity/Statement（含Context）入库', icon: <DatabaseOutlined /> },
        { title: '推理检索', desc: 'ES/向量/图谱推理面向场景输出', icon: <ThunderboltOutlined /> },
        { title: '反馈闭环', desc: '推理结果回写知识库/指标口径', icon: <ArrowRightOutlined /> }
    ]

    // 五大核心类
    const coreClasses = [
        { key: '1', id: 'ont:IndustryConcept', name: '产业概念类', nameEn: 'Industrial Concept',
          cidoc: 'E28 Conceptual Object', subClasses: '产业网、产业链、产业节点、产业价值环节',
          role: '决策分析的语义锚点' },
        { key: '2', id: 'ont:IndustrySubject', name: '产业主体类', nameEn: 'Industrial Actor',
          cidoc: 'E39 Actor', subClasses: '企业、科研机构、政府/监管主体、金融机构、行业协会',
          role: '价值创造与决策的核心参与载体' },
        { key: '3', id: 'ont:IndustryObject', name: '产业对象类', nameEn: 'Industrial Object',
          cidoc: 'E70 Thing', subClasses: '物质对象、技术对象、资金对象、人力资源、信息资源、制度规则',
          role: '决策分析的核心要素载体' },
        { key: '4', id: 'ont:IndustryEvent', name: '产业事件类', nameEn: 'Industrial Event',
          cidoc: 'E5 Event', subClasses: '交易事件、合作事件、创新事件、投融资事件、政策发布事件',
          role: '决策分析的动态依据' },
        { key: '5', id: 'ont:IndustryDocument', name: '产业文档类', nameEn: 'Industrial Document',
          cidoc: 'E31 Document', subClasses: '资讯文档、专利文档、研报文档、政策文档、标准文档',
          role: '决策分析的可信依据' }
    ]

    // 四大支撑类
    const supportClasses = [
        { key: '1', name: '标识要素', cidoc: 'E41 Appellation', desc: '唯一识别产业实体的编码、名称、称谓' },
        { key: '2', name: '类型要素', cidoc: 'E55 Type', desc: '产业实体对应的分类术语' },
        { key: '3', name: '时间要素', cidoc: 'E52 Time-Span', desc: '刻画产业网链相关实体的时间属性' },
        { key: '4', name: '空间要素', cidoc: 'E53 Place', desc: '定位产业网链相关实体的地理或物理位置' }
    ]

    // 核心表结构
    const coreTableSchemas = {
        entity: [
            { field: 'id', type: 'VARCHAR(64)', desc: '实体实例ID，格式: {class_prefix}:{uuid}' },
            { field: 'class_id', type: 'VARCHAR(64)', desc: '所属本体类ID' },
            { field: 'canonical_name', type: 'VARCHAR(512)', desc: '规范名称（用于显示和搜索）' },
            { field: 'status', type: 'ENUM', desc: 'pending, active, merged, deprecated, deleted' },
            { field: 'quality_score', type: 'DECIMAL(5,4)', desc: '数据质量分数 0-1' }
        ],
        statement: [
            { field: 'id', type: 'BIGINT', desc: '主键' },
            { field: 'subject_id', type: 'VARCHAR(64)', desc: '主体实体ID' },
            { field: 'predicate_id', type: 'VARCHAR(64)', desc: '谓词（属性定义ID）' },
            { field: 'object_type', type: 'ENUM', desc: 'literal, entity_ref' },
            { field: 'context_time_value', type: 'VARCHAR(32)', desc: '上下文时间值（内嵌）' },
            { field: 'context_source_id', type: 'VARCHAR(64)', desc: '上下文数据源ID（内嵌）' },
            { field: 'confidence', type: 'DECIMAL(5,4)', desc: '综合置信度 0-1' }
        ]
    }

    // 存储技术栈
    const storageStack = [
        { key: '1', layer: '本体模型库', tech: 'MySQL', usage: '本体类/属性/关系定义、版本管理', reason: '结构化、事务性强' },
        { key: '2', layer: '实例知识库', tech: 'MySQL + MongoDB', usage: 'Entity/Statement主存', reason: '高吞吐、幂等写入' },
        { key: '3', layer: '图谱索引', tech: 'Neo4j', usage: '实体关系图谱', reason: '图查询、推理' },
        { key: '4', layer: '向量索引', tech: 'Milvus', usage: '语义向量检索', reason: '相似度搜索' },
        { key: '5', layer: '文档存储', tech: 'MongoDB', usage: '原始文档、非结构化数据', reason: '灵活schema' },
        { key: '6', layer: '对象存储', tech: 'MinIO', usage: 'PDF、图片等文件', reason: 'S3兼容' },
        { key: '7', layer: '缓存层', tech: 'Redis', usage: '热点数据、会话', reason: '高性能读取' },
        { key: '8', layer: '检索服务', tech: 'Elasticsearch', usage: '全文检索、聚合分析', reason: '强大的搜索能力' }
    ]

    // 一致性机制
    const consistencyMechanisms = [
        { key: '1', mechanism: '全局ID贯穿', desc: '实体ID、StatementID、文档ID全链路一致' },
        { key: '2', mechanism: '语义映射联动', desc: '本体版本变更同步到实例库与数仓' },
        { key: '3', mechanism: '增量同步', desc: '资源层→要素层→服务层异步同步' },
        { key: '4', mechanism: '幂等写入', desc: '基于全局ID保证重复写入不冲突' },
        { key: '5', mechanism: '一致性校验', desc: '定期核验本体约束、实例与指标口径一致性' }
    ]

    // 渲染架构总览
    const renderOverview = () => (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card>
                <Title level={4}><GlobalOutlined style={{ marginRight: 8, color: '#6366f1' }} />设计目标与范围</Title>
                <Alert message="围绕产业网链「规范-实例-分析」的三位一体闭环" description={
                    <ul style={{ marginTop: 12, marginBottom: 0 }}>
                        <li>明确三库边界与职责：本体模型库（规范层）/ 实例知识库（实例层）/ 主题数仓（分析层）协同但不混存</li>
                        <li>坚持本体先行：先定义语义规范与约束，再实例化沉淀，最后按语义映射加工分析</li>
                        <li>三个统一：统一ID体系、统一语义标准、统一同步机制</li>
                        <li>兼容既有主题数仓：最小改造接入，完成指标口径与本体属性对齐</li>
                        <li>轻量闭环优先：先保证检索/推理/分析最小可用，提供清晰的迭代升级路径</li>
                    </ul>
                } type="info" showIcon />
            </Card>

            <Card>
                <Title level={4}><DatabaseOutlined style={{ marginRight: 8, color: '#3b82f6' }} />三层架构总览</Title>
                <Row gutter={[16, 16]}>
                    {architectureLayers.map((layer) => (
                        <Col span={8} key={layer.key}>
                            <Card style={{ background: `linear-gradient(135deg, ${layer.color}15 0%, ${layer.color}05 100%)`,
                                border: `1px solid ${layer.color}40`, height: '100%' }}>
                                <Space direction="vertical" style={{ width: '100%' }}>
                                    <div style={{ fontSize: 32, color: layer.color, textAlign: 'center' }}>{layer.icon}</div>
                                    <Title level={5} style={{ textAlign: 'center', margin: '8px 0', color: '#e2e8f0' }}>
                                        {layer.title}
                                    </Title>
                                    <Text type="secondary" style={{ textAlign: 'center', display: 'block', fontSize: 12 }}>
                                        {layer.subtitle}
                                    </Text>
                                    <Divider style={{ margin: '12px 0' }} />
                                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                        {layer.components.map((comp, i) => (
                                            <Tag key={i} color={layer.color} style={{ margin: 2 }}>{comp}</Tag>
                                        ))}
                                    </Space>
                                    <Text style={{ fontSize: 12, color: '#94a3b8', marginTop: 8 }}>{layer.description}</Text>
                                </Space>
                            </Card>
                        </Col>
                    ))}
                </Row>
            </Card>

            <Card>
                <Title level={4}><ArrowRightOutlined style={{ marginRight: 8, color: '#10b981' }} />数据流向示意</Title>
                <div style={{ background: '#1e293b', padding: 24, borderRadius: 8, border: '1px solid #334155' }}>
                    <Timeline items={dataFlowSteps.map(step => ({
                        dot: step.icon,
                        children: (<div><Text strong style={{ color: '#e2e8f0' }}>{step.title}</Text><br />
                            <Text type="secondary" style={{ fontSize: 12 }}>{step.desc}</Text></div>)
                    }))} />
                </div>
            </Card>
        </Space>
    )

    // 渲染三库关系
    const renderThreeLibraries = () => (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card>
                <Title level={4}><ApartmentOutlined style={{ marginRight: 8, color: '#6366f1' }} />三库关系（规范-实例-分析闭环）</Title>
                <Alert message="核心理念" description='本体模型库定义语义规范 → 实例知识库实例化沉淀 → 主题数仓按语义映射加工与分析。反向：主题数仓分析发现新规律 → 审核后回写实例知识库 → 触发本体模型库迭代与版本发布。'
                    type="success" showIcon style={{ marginBottom: 16 }} />
                <Row gutter={[16, 16]}>
                    {threeLibraries.map((lib) => (
                        <Col span={8} key={lib.key}>
                            <Card style={{ background: `linear-gradient(135deg, ${lib.color}15 0%, ${lib.color}05 100%)`,
                                border: `1px solid ${lib.color}40`, height: '100%' }}>
                                <Space direction="vertical" style={{ width: '100%' }} size="small">
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: 36, color: lib.color }}>{lib.icon}</div>
                                        <Title level={5} style={{ margin: '8px 0', color: '#e2e8f0' }}>{lib.name}</Title>
                                        <Tag color={lib.color}>{lib.role}</Tag>
                                        <Text type="secondary" style={{ display: 'block', fontSize: 11, marginTop: 4 }}>{lib.nameEn}</Text>
                                    </div>
                                    <Divider style={{ margin: '12px 0' }} />
                                    <div><Text strong style={{ fontSize: 12, color: '#94a3b8' }}>存储内容：</Text>
                                        <Paragraph style={{ fontSize: 12, marginTop: 4, marginBottom: 8, color: '#cbd5e1' }}>{lib.content}</Paragraph></div>
                                    <div><Text strong style={{ fontSize: 12, color: '#94a3b8' }}>数据性质：</Text>
                                        <Paragraph style={{ fontSize: 12, marginTop: 4, marginBottom: 8, color: '#cbd5e1' }}>{lib.nature}</Paragraph></div>
                                    <div><Text strong style={{ fontSize: 12, color: '#94a3b8' }}>使用者：</Text>
                                        <Paragraph style={{ fontSize: 12, marginTop: 4, marginBottom: 8, color: '#cbd5e1' }}>{lib.users}</Paragraph></div>
                                    <div><Text strong style={{ fontSize: 12, color: '#94a3b8' }}>核心操作：</Text>
                                        <Paragraph style={{ fontSize: 12, marginTop: 4, marginBottom: 0, color: '#cbd5e1' }}>{lib.operations}</Paragraph></div>
                                </Space>
                            </Card>
                        </Col>
                    ))}
                </Row>
            </Card>

            <Card>
                <Title level={5}>数据流向链路</Title>
                <Row gutter={16}>
                    <Col span={12}>
                        <Card size="small" style={{ background: '#1e293b', border: '1px solid #10b981' }}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <Text strong style={{ color: '#10b981' }}><CheckCircleOutlined /> 正向链路</Text>
                                <Text style={{ fontSize: 12, color: '#cbd5e1' }}>
                                    本体模型库定义语义规范 → 实例知识库实例化沉淀 → 主题数仓按语义映射加工与分析
                                </Text>
                            </Space>
                        </Card>
                    </Col>
                    <Col span={12}>
                        <Card size="small" style={{ background: '#1e293b', border: '1px solid #f59e0b' }}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <Text strong style={{ color: '#f59e0b' }}><SyncOutlined /> 反向链路</Text>
                                <Text style={{ fontSize: 12, color: '#cbd5e1' }}>
                                    主题数仓分析发现新规律 → 审核后回写实例知识库 → 触发本体模型库迭代与版本发布
                                </Text>
                            </Space>
                        </Card>
                    </Col>
                </Row>
            </Card>
        </Space>
    )

    // 渲染本体模型
    const renderOntologyModel = () => (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card>
                <Title level={4}><ClusterOutlined style={{ marginRight: 8, color: '#6366f1' }} />五大顶层核心类（CIDOC CRM映射）</Title>
                <Table dataSource={coreClasses} columns={[
                    { title: '类ID', dataIndex: 'id', width: 180, render: text => <Text code style={{ fontSize: 11 }}>{text}</Text> },
                    { title: '名称', dataIndex: 'name', width: 120, render: text => <Text strong>{text}</Text> },
                    { title: '英文名', dataIndex: 'nameEn', width: 140, render: text => <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text> },
                    { title: 'CIDOC CRM', dataIndex: 'cidoc', width: 160, render: text => <Tag color="purple">{text}</Tag> },
                    { title: '核心子类', dataIndex: 'subClasses', render: text => <Text style={{ fontSize: 12 }}>{text}</Text> },
                    { title: '决策支撑定位', dataIndex: 'role', render: text => <Text style={{ fontSize: 12, color: '#10b981' }}>{text}</Text> }
                ]} pagination={false} size="small" />
            </Card>

            <Card>
                <Title level={4}><NodeIndexOutlined style={{ marginRight: 8, color: '#3b82f6' }} />四大通用支撑类</Title>
                <Row gutter={[16, 16]}>
                    {supportClasses.map(cls => (
                        <Col span={6} key={cls.key}>
                            <Card size="small" style={{ background: '#1e293b', border: '1px solid #334155', height: '100%' }}>
                                <Space direction="vertical" style={{ width: '100%' }} size="small">
                                    <Text strong style={{ color: '#e2e8f0' }}>{cls.name}</Text>
                                    <Tag color="purple" style={{ fontSize: 10 }}>{cls.cidoc}</Tag>
                                    <Text style={{ fontSize: 11, color: '#94a3b8' }}>{cls.desc}</Text>
                                </Space>
                            </Card>
                        </Col>
                    ))}
                </Row>
            </Card>
        </Space>
    )

    // 渲染存储技术
    const renderStorageTech = () => (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card>
                <Title level={4}><DatabaseOutlined style={{ marginRight: 8, color: '#3b82f6' }} />存储技术栈</Title>
                <Table dataSource={storageStack} columns={[
                    { title: '存储层', dataIndex: 'layer', width: 150, render: text => <Text strong>{text}</Text> },
                    { title: '技术选型', dataIndex: 'tech', width: 180, render: text => <Tag color="blue">{text}</Tag> },
                    { title: '用途', dataIndex: 'usage', render: text => <Text style={{ fontSize: 12 }}>{text}</Text> },
                    { title: '选型原因', dataIndex: 'reason', width: 150, render: text => <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text> }
                ]} pagination={false} size="small" />
            </Card>

            <Card>
                <Title level={4}><ClusterOutlined style={{ marginRight: 8, color: '#6366f1' }} />核心表结构</Title>
                <Row gutter={16}>
                    <Col span={12}>
                        <Card size="small" title={<Text strong>Entity（实体实例表）</Text>}
                            style={{ background: '#1e293b', border: '1px solid #334155' }}>
                            <Table dataSource={coreTableSchemas.entity} columns={[
                                { title: '字段', dataIndex: 'field', width: 140, render: text => <Text code style={{ fontSize: 11 }}>{text}</Text> },
                                { title: '类型', dataIndex: 'type', width: 120, render: text => <Tag color="cyan" style={{ fontSize: 10 }}>{text}</Tag> },
                                { title: '说明', dataIndex: 'desc', render: text => <Text style={{ fontSize: 11 }}>{text}</Text> }
                            ]} pagination={false} size="small" showHeader={false} />
                        </Card>
                    </Col>
                    <Col span={12}>
                        <Card size="small" title={<Text strong>Statement（陈述表，内嵌Context）</Text>}
                            style={{ background: '#1e293b', border: '1px solid #334155' }}>
                            <Table dataSource={coreTableSchemas.statement} columns={[
                                { title: '字段', dataIndex: 'field', width: 160, render: text => <Text code style={{ fontSize: 11 }}>{text}</Text> },
                                { title: '类型', dataIndex: 'type', width: 100, render: text => <Tag color="cyan" style={{ fontSize: 10 }}>{text}</Tag> },
                                { title: '说明', dataIndex: 'desc', render: text => <Text style={{ fontSize: 11 }}>{text}</Text> }
                            ]} pagination={false} size="small" showHeader={false} />
                        </Card>
                    </Col>
                </Row>
            </Card>
        </Space>
    )

    // 渲染一致性机制
    const renderConsistency = () => (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card>
                <Title level={4}><SafetyCertificateOutlined style={{ marginRight: 8, color: '#10b981' }} />跨层联动与一致性机制</Title>
                <Alert message="核心原则" description="通过全局ID、语义映射、增量同步、幂等写入和定期校验，确保三层架构和三库之间的数据一致性与可追溯性。"
                    type="info" showIcon style={{ marginBottom: 16 }} />
                <Row gutter={[16, 16]}>
                    {consistencyMechanisms.map((item, index) => (
                        <Col span={24} key={item.key}>
                            <Card size="small" style={{ background: '#1e293b', border: '1px solid #334155' }}>
                                <Space>
                                    <Badge count={index + 1} style={{ backgroundColor: '#6366f1' }} />
                                    <div>
                                        <Text strong style={{ color: '#e2e8f0' }}>{item.mechanism}</Text><br />
                                        <Text type="secondary" style={{ fontSize: 12 }}>{item.desc}</Text>
                                    </div>
                                </Space>
                            </Card>
                        </Col>
                    ))}
                </Row>
            </Card>

            <Card>
                <Title level={5}>数据同步策略</Title>
                <Timeline items={[
                    { color: 'green', children: (<div><Text strong>MongoDB → MySQL (source_db)</Text><br />
                        <Text type="secondary" style={{ fontSize: 12 }}>触发：ETL完成 | 模式：异步批量 | 用途：原始数据结构化</Text></div>) },
                    { color: 'blue', children: (<div><Text strong>MySQL (instance_db) → Neo4j</Text><br />
                        <Text type="secondary" style={{ fontSize: 12 }}>触发：Statement创建（entity_ref类型）| 模式：实时 | 用途：关系同步到图谱</Text></div>) },
                    { color: 'purple', children: (<div><Text strong>MySQL (instance_db) → Milvus</Text><br />
                        <Text type="secondary" style={{ fontSize: 12 }}>触发：实体/Statement创建或更新 | 模式：异步批量（5分钟）| 用途：向量化索引</Text></div>) },
                    { color: 'orange', children: (<div><Text strong>MySQL (instance_db) → Redis</Text><br />
                        <Text type="secondary" style={{ fontSize: 12 }}>触发：热点数据访问 | 模式：按需 | 用途：缓存穿透</Text></div>) }
                ]} />
            </Card>
        </Space>
    )

    // 主渲染
    return (
        <div style={{ padding: '0 0 24px 0' }}>
            <Card style={{ marginBottom: 24 }}>
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <Title level={3} style={{ margin: 0 }}>
                        <ApartmentOutlined style={{ marginRight: 12, color: '#6366f1' }} />
                        产业网链数据海平台架构设计
                    </Title>
                    <Text type="secondary">围绕「规范-实例-分析」三位一体闭环，构建三层平台架构与三库协同体系</Text>
                </Space>
            </Card>

            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
                { key: 'overview', label: (<span><GlobalOutlined />架构总览</span>), children: renderOverview() },
                { key: 'three-libraries', label: (<span><ApartmentOutlined />三库关系</span>), children: renderThreeLibraries() },
                { key: 'ontology', label: (<span><ClusterOutlined />本体模型</span>), children: renderOntologyModel() },
                { key: 'storage', label: (<span><DatabaseOutlined />存储技术</span>), children: renderStorageTech() },
                { key: 'consistency', label: (<span><SafetyCertificateOutlined />一致性机制</span>), children: renderConsistency() }
            ]} size="large" tabBarStyle={{ background: '#1e293b', padding: '0 16px', borderRadius: '8px 8px 0 0', marginBottom: 0 }} />
        </div>
    )
}

export default StorageArchitecturePage
