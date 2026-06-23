export const PARAM_META = {
  project_id: {
    label: '项目 ID',
    help: '默认使用项目 1。只有在多项目场景下才需要调整。',
    defaultValue: 1,
    advanced: true,
  },
  runtime_profile: {
    label: '运行时',
    help: '工作台主入口固定使用 kag_openspg 主链；openks_direct 仅保留后端兼容与排障，不再在页面上暴露。',
    defaultValue: 'kag_openspg',
  },
  hours_ago: {
    label: '时间范围',
    help: '采集、应用和问答联动默认看最近 24 小时的数据。',
    defaultValue: 24,
    unit: '小时',
  },
  max_entries_per_feed: {
    label: '单源采集上限',
    help: '每个资讯源最多抓取多少条，默认 5 条，通常不需要修改。',
    defaultValue: 5,
  },
  bridge_limit: {
    label: '处理上限',
    help: '本次进入抽取和入图阶段的资讯条数上限，默认 200 条。',
    defaultValue: 200,
  },
  headlines_top_n: {
    label: '输出条数',
    help: '应用阶段最终展示多少条头条结果，默认 20 条。',
    defaultValue: 20,
  },
  builder_command: {
    label: 'Builder 命令',
    help: '默认使用后端内置命令。只有排查特殊导入问题时才需要覆盖。',
    defaultValue: '',
    advanced: true,
  },
  submit_builder: {
    label: '提交 Builder',
    help: '默认开启。关闭后只执行到 bridge 导出，不会进入 OpenSPG Builder 与图物化。',
  },
  apply_schema: {
    label: '应用 Schema',
    help: '默认开启。会在运行前把 OpenKS 编译出的当前 Schema 提交并激活。',
  },
  force_full: {
    label: '全量导出',
    help: '默认开启。关闭后只处理增量数据，适合常规日常运行。',
  },
}

export const ADVANCED_PARAM_KEYS = ['project_id', 'builder_command']
