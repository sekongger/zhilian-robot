export const OPENKS_REPO_BLUEPRINT = ['common', 'kg', 'cross', 'entry', 'tests', 'docs', 'openks.yaml']

export const OPENKS_ENGINE_STACK = ['OpenKS', 'KAG', 'OpenSPG']

export const OPENKS_COLLABORATION_STACK = [...OPENKS_ENGINE_STACK]

export const OPENKS_TRACEABLE_MODULES = ['base_kg', 'news_kg']

export const OPENKS_DEFINITION_LAYERS = [
  {
    name: 'base_kg',
    title: '基础概念词典',
    description: '定义产业网链基础概念、统一 ID 规则和各类要素 KG 的共性词汇骨架。',
    members: ['base_kg'],
  },
  {
    name: 'element_kgs',
    title: '网状事实图谱',
    description: '资讯、研报、百科、企业、政策等事实类 KG 都在 base_kg 之上扩展，形成可交叉挂接的事实图谱网络。',
    members: ['news_kg', 'report_kg', 'encyclopedia_kg', 'enterprise_kg', 'policy_kg', 'patent_kg', 'organization_kg', 'technology_kg', 'product_kg'],
  },
  {
    name: 'chain_kgs',
    title: '链式认知图谱',
    description: '在事实图谱之上继续组织产业链、供应链、创新链、资金链和决策类 KG，形成链式认知与决策结构。',
    members: ['industry_chain', 'supply_chain', 'innovation_chain', 'capital_chain', 'hotspot', 'trend', 'risk_alert', 'recommendation', 'technology_foresight'],
  },
]

export const OPENKS_SUPPORT_MODULES = [
  {
    key: 'common',
    title: '公共层',
    owner: '平台共建',
    path: 'openks/common',
    responsibilities: ['统一 Schema', '公共基类', '注册表', '通用算子与适配器'],
  },
  {
    key: 'cross',
    title: '跨 KG 调度层',
    owner: '云飞',
    path: 'openks/cross',
    responsibilities: ['事实到认知映射', '认知到决策流转', '调度编排', '实体对齐与同步'],
  },
  {
    key: 'entry',
    title: '统一入口层',
    owner: '旭科',
    path: 'openks/entry',
    responsibilities: ['启动装配', 'CLI 调用', 'API 入口', 'Agent 对接输入输出'],
  },
]

export const OPENKS_KG_GROUPS = [
  {
    key: 'fact',
    title: '事实类 KG',
    summary: '沉淀资讯、研报、企业与要素事实，形成产业网链基础知识底座。',
    modules: [
      {
        name: 'base_kg',
        title: '产业网链基础',
        owner: '蔡旭东、陆文韬',
        path: 'openks/kg/fact/base_kg',
        summary: '定义产业网链基础实体、统一 ID 规则和常用要素骨架。',
      },
      {
        name: 'encyclopedia_kg',
        title: '百科知识库',
        owner: '杨辰',
        path: 'openks/kg/fact/encyclopedia_kg',
        summary: '沉淀通用百科类实体知识，为事实与认知层补充背景语义。',
      },
      {
        name: 'news_kg',
        title: '资讯知识库',
        owner: '楼彦炜',
        path: 'openks/kg/fact/news_kg',
        summary: '面向资讯抽取事件、实体、关系和热点事实。',
      },
      {
        name: 'report_kg',
        title: '研报知识库',
        owner: '李奕君',
        path: 'openks/kg/fact/report_kg',
        summary: '面向研报抽取观点、结论、指标和产业覆盖关系。',
      },
      {
        name: 'enterprise_kg',
        title: '企业知识库',
        owner: '陆文韬',
        path: 'openks/kg/fact/enterprise_kg',
        summary: '沉淀企业画像、经营要素和上下游基础信息。',
      },
      {
        name: 'policy_kg',
        title: '政策知识库',
        owner: '陆文韬',
        path: 'openks/kg/fact/policy_kg',
        summary: '抽取政策主体、扶持方向、约束条件和影响对象。',
      },
      {
        name: 'patent_kg',
        title: '专利知识库',
        owner: '林辉',
        path: 'openks/kg/fact/patent_kg',
        summary: '抽取专利主体、技术方向、申请趋势和关联技术。',
      },
      {
        name: 'organization_kg',
        title: '机构知识库',
        owner: '林辉',
        path: 'openks/kg/fact/organization_kg',
        summary: '沉淀机构、园区、联盟和组织协作关系。',
      },
      {
        name: 'technology_kg',
        title: '技术知识库',
        owner: '林辉',
        path: 'openks/kg/fact/technology_kg',
        summary: '提炼技术路线、关键能力、成熟度和依赖关系。',
      },
      {
        name: 'product_kg',
        title: '产品知识库',
        owner: '雅馨',
        path: 'openks/kg/fact/product_kg',
        summary: '沉淀产品谱系、规格能力、应用场景和供给关系。',
      },
    ],
  },
  {
    key: 'cognition',
    title: '认知类 KG',
    summary: '将多类事实挂接成产业链、供应链、创新链、资金链等认知网络。',
    modules: [
      {
        name: 'industry_chain',
        title: '产业链图谱库',
        owner: '杨辰、雅馨',
        path: 'openks/kg/cognition/industry_chain',
        summary: '定义产业网链基础结构，承接事实要素并做链路组织。',
      },
      {
        name: 'supply_chain',
        title: '供应链图谱库',
        owner: '待定',
        path: 'openks/kg/cognition/supply_chain',
        summary: '聚焦供应依赖、上下游关系和替代链路推理。',
      },
      {
        name: 'innovation_chain',
        title: '创新链图谱库',
        owner: '待定',
        path: 'openks/kg/cognition/innovation_chain',
        summary: '聚焦技术演进、成果转化和创新主体协同网络。',
      },
      {
        name: 'capital_chain',
        title: '资金链图谱库',
        owner: '待定',
        path: 'openks/kg/cognition/capital_chain',
        summary: '聚焦投融资、资本流向和产业资金结构。',
      },
    ],
  },
  {
    key: 'decision',
    title: '决策类 KG',
    summary: '将认知层结构转化为热点、趋势、风险和推荐等决策输出。',
    modules: [
      {
        name: 'technology_foresight',
        title: '技术前瞻',
        owner: '林辉、徐梓毓',
        path: 'openks/kg/decision/technology_foresight',
        summary: '分析前沿技术信号、技术路线分叉和长期趋势。',
      },
      {
        name: 'hotspot',
        title: '热点分析',
        owner: '待定',
        path: 'openks/kg/decision/hotspot',
        summary: '聚合热点话题、热度传导和行业关注焦点。',
      },
      {
        name: 'trend',
        title: '趋势分析',
        owner: '待定',
        path: 'openks/kg/decision/trend',
        summary: '形成趋势判断、变化拐点和产业结构演进观察。',
      },
      {
        name: 'risk_alert',
        title: '风险预警',
        owner: '待定',
        path: 'openks/kg/decision/risk_alert',
        summary: '面向供应风险、政策风险和波动异常输出预警。',
      },
      {
        name: 'recommendation',
        title: '推荐决策',
        owner: '待定',
        path: 'openks/kg/decision/recommendation',
        summary: '面向智能体和应用层输出推荐、排序和行动建议。',
      },
    ],
  },
]

export function flattenOpenksModules() {
  return OPENKS_KG_GROUPS.flatMap((group) =>
    group.modules.map((module) => ({
      ...module,
      groupKey: group.key,
      groupTitle: group.title,
    })),
  )
}

export function filterTraceableOpenksModules(modules = []) {
  return modules.filter((item) => OPENKS_TRACEABLE_MODULES.includes(item?.name))
}

export function filterTraceableDefinitionLayers(layers = OPENKS_DEFINITION_LAYERS) {
  return layers
    .map((layer) => ({
      ...layer,
      members: layer.members.filter((member) => OPENKS_TRACEABLE_MODULES.includes(member)),
    }))
    .filter((layer) => layer.members.length > 0)
}
