export const OPENKS_WORKBENCH_BLOCKS = [
  {
    key: 'schema',
    title: 'Schema',
    subtitle: '统一定义本体、实体、关系与约束',
    summary: '先看定义层，不做运行态操作。Schema 负责把 OpenKS 的知识骨架、命名口径和演进边界先稳定下来。',
    accent: '定义层',
    items: [
      '本体定义：base_kg 与 news_kg 的共同骨架',
      '关系约束：实体、属性、边类型和继承层次',
      '版本口径：以静态前台展示方式先对齐 Schema 视图',
    ],
    tags: ['OpenKS', 'Schema DSL', '定义优先'],
  },
  {
    key: 'kg-modules',
    title: 'KG模块',
    subtitle: '按事实、认知、决策三层组织模块',
    summary: '这里展示 OpenKS 的模块分层和承接关系，先把 KG 模块的归属、职责和覆盖范围摆清楚。',
    accent: '模块层',
    items: [
      '事实类 KG：新闻、研报、企业、专利等',
      '认知类 KG：产业链、供应链、创新链、资金链',
      '决策类 KG：热点、趋势、风险预警、推荐',
    ],
    tags: ['事实类', '认知类', '决策类'],
  },
  {
    key: 'production-chain',
    title: '生产主链',
    subtitle: '只展示 kag_openspg 正式生产链',
    summary: '这里不再展示合同化 build-jobs，而是把 workflow、schema sync、bridge 导出、OpenSPG 写图和 runtime binding 作为唯一主线。',
    accent: '主链层',
    items: [
      '编排入口：workflow 与 step APIs',
      '执行链：schema sync -> bridge export -> graph materialize',
      '运行态口径：Run、Artifact、Release',
    ],
    tags: ['Workflow', 'OpenSPG', 'Runtime'],
  },
  {
    key: 'graph-results',
    title: '图谱结果',
    subtitle: '面向前台的知识产出结果',
    summary: '最终结果以图谱视角收束，突出可见的结构、版本和覆盖范围，方便在工作台里直接汇报。',
    accent: '结果层',
    items: [
      '图谱范围：事实图谱、产业链图谱、决策图谱',
      '结果视角：结构、覆盖、版本与更新时间',
      '展示方式：静态前台卡片，不接入实时图服务',
    ],
    tags: ['图谱', '版本', '覆盖范围'],
  },
]

export function getOpenksWorkbenchBlockByKey(key) {
  return OPENKS_WORKBENCH_BLOCKS.find((item) => item.key === key) || OPENKS_WORKBENCH_BLOCKS[0]
}
