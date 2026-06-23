-- 企业库
CREATE TABLE `dw_company_info_tyc` (
  `id` VARCHAR(100) NULL COMMENT '企业ID',
  `name` VARCHAR(700) REPLACE_IF_NOT_NULL NULL COMMENT '企业名称',
  `name_en` VARCHAR(500) REPLACE_IF_NOT_NULL NULL COMMENT '企业英文名称',
  `used_name` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '企业历史名称，多个用;隔开',
  `credit_code` VARCHAR(50) REPLACE_IF_NOT_NULL NULL COMMENT '统一社会信用代码',
  `legal_person` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '法人',
  `logo` VARCHAR(1000) REPLACE_IF_NOT_NULL NULL COMMENT '自己logo处理后OSS链接地址',
  `logo_source` VARCHAR(1000) REPLACE_IF_NOT_NULL NULL COMMENT '采集的原始logo链接',
  `employee_size` VARCHAR(100) REPLACE_IF_NOT_NULL NULL COMMENT '员工数量',
  `insured_number` INT REPLACE_IF_NOT_NULL NULL COMMENT '参保人数',
  `valid_phone` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '有效联系电话',
  `tel` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '联系电话',
  `email` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '电子邮件',
  `website` VARCHAR(1200) REPLACE_IF_NOT_NULL NULL COMMENT '网址',
  `address` VARCHAR(3000) REPLACE_IF_NOT_NULL NULL COMMENT '企业地址',
  `contact_address` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '通信地址',
  `establish_date` date REPLACE_IF_NOT_NULL NULL COMMENT '企业建立时间',
  `nation` VARCHAR(60) REPLACE_IF_NOT_NULL NULL COMMENT '所属国家',
  `province` VARCHAR(60) REPLACE_IF_NOT_NULL NULL COMMENT '所属省份',
  `city` VARCHAR(100) REPLACE_IF_NOT_NULL NULL COMMENT '所属城市',
  `area` VARCHAR(100) REPLACE_IF_NOT_NULL NULL COMMENT '所属区域',
  `nation_code` VARCHAR(20) REPLACE_IF_NOT_NULL NULL COMMENT '国家代码',
  `province_code` VARCHAR(20) REPLACE_IF_NOT_NULL NULL COMMENT '省份代码',
  `city_code` VARCHAR(20) REPLACE_IF_NOT_NULL NULL COMMENT '城市代码',
  `area_code` VARCHAR(20) REPLACE_IF_NOT_NULL NULL COMMENT '区域代码',
  `lng` VARCHAR(30) REPLACE_IF_NOT_NULL NULL COMMENT '经度',
  `lat` VARCHAR(30) REPLACE_IF_NOT_NULL NULL COMMENT '纬度',
  `check_date` date REPLACE_IF_NOT_NULL NULL COMMENT '核准日期',
  `status` VARCHAR(200) REPLACE_IF_NOT_NULL NULL COMMENT '企业状态',
  `pay_capi` VARCHAR(50) REPLACE_IF_NOT_NULL NULL COMMENT '实缴资本描述',
  `pay_capi_value` DECIMAL(24, 4) REPLACE_IF_NOT_NULL NULL COMMENT '实缴资本数值',
  `pay_capi_unit` VARCHAR(50) REPLACE_IF_NOT_NULL NULL COMMENT '实缴资本币种单位',
  `pay_capi_value_cal` DECIMAL(24, 4) REPLACE_IF_NOT_NULL NULL COMMENT '实缴资本数值（以人民币计算）',
  `regist_capi` VARCHAR(50) REPLACE_IF_NOT_NULL NULL COMMENT '注册资本描述',
  `regist_capi_value` DECIMAL(24, 4) REPLACE_IF_NOT_NULL NULL COMMENT '注册资本数值',
  `regist_capi_unit` VARCHAR(30) REPLACE_IF_NOT_NULL NULL COMMENT '注册资本币种单位',
  `regist_capi_value_cal` DECIMAL(24, 4) REPLACE_IF_NOT_NULL NULL COMMENT '注册资本数值（以人民币计算）',
  `org_no` VARCHAR(30) REPLACE_IF_NOT_NULL NULL COMMENT '组织机构代码',
  `company_type` VARCHAR(200) REPLACE_IF_NOT_NULL NULL COMMENT '公司类型',
  `company_scale` VARCHAR(200) REPLACE_IF_NOT_NULL NULL COMMENT '企业规模',
  `business_term` VARCHAR(100) REPLACE_IF_NOT_NULL NULL COMMENT '营业期限',
  `taxpayer_no` VARCHAR(50) REPLACE_IF_NOT_NULL NULL COMMENT '纳税人识别号',
  `nation_industry_1` VARCHAR(500) REPLACE_IF_NOT_NULL NULL COMMENT '国民经济行业分类-门类',
  `nation_industry_2` VARCHAR(500) REPLACE_IF_NOT_NULL NULL COMMENT '国民经济行业分类-大类',
  `nation_industry_3` VARCHAR(500) REPLACE_IF_NOT_NULL NULL COMMENT '国民经济行业分类-中类',
  `nation_industry_4` VARCHAR(500) REPLACE_IF_NOT_NULL NULL COMMENT '国民经济行业分类-小类',
  `nation_industry_code` VARCHAR(100) REPLACE_IF_NOT_NULL NULL COMMENT '国民经济行业分类代码',
  `belong_org` VARCHAR(200) REPLACE_IF_NOT_NULL NULL COMMENT '登记机关',
  `registration_id` VARCHAR(255) REPLACE_IF_NOT_NULL NULL COMMENT '工商注册号',
  `business_scope` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '经营范围',
  `description` TEXT REPLACE_IF_NOT_NULL NULL COMMENT '企业简介',
  `is_valid` TINYINT REPLACE_IF_NOT_NULL NULL COMMENT '数据是否有效',
  `create_time` datetime MIN NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime MAX NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间',
  INDEX idx_dw_company_info_tyc_id (`id`) USING INVERTED COMMENT ''
) ENGINE=OLAP
AGGREGATE KEY(`id`)
COMMENT 'OLAP'
DISTRIBUTED BY HASH(`id`) BUCKETS 32
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);

-- 科研机构/高校
CREATE TABLE `dw_institution_2026` (
  `id` VARCHAR(500) NOT NULL COMMENT '主键, name',
  `support_org_id` VARCHAR(100) NULL COMMENT '依托单位/所属企业cid',
  `name` VARCHAR(255) NOT NULL COMMENT '机构名称',
  `support_org_name` VARCHAR(500) NULL COMMENT '依托单位/所属企业',
  `domain` TEXT NULL COMMENT '研究领域',
  `address` VARCHAR(500) NULL COMMENT '地址',
  `type_1` VARCHAR(200) NULL COMMENT '一级类型',
  `type_2` VARCHAR(200) NULL COMMENT '二级类型',
  `type_3` VARCHAR(200) NULL COMMENT '三级类型',
  `email` VARCHAR(500) NULL COMMENT '邮箱',
  `tel` VARCHAR(500) NULL COMMENT '电话',
  `linkman` VARCHAR(200) NULL COMMENT '联系人',
  `website` VARCHAR(1000) NULL COMMENT '网站链接',
  `description` TEXT NULL COMMENT '简介',
  `establish_year` VARCHAR(10) NULL COMMENT '获批年份',
  `source` VARCHAR(50) NULL COMMENT '数据来源',
  `is_valid` TINYINT NULL DEFAULT "1" COMMENT '数据是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间',
  `province` VARCHAR(50) NULL COMMENT '省',
  `city` VARCHAR(50) NULL COMMENT '市',
  `area` VARCHAR(50) NULL COMMENT '区',
  `achievement` TEXT NULL COMMENT '成果',
  `rating_agency` VARCHAR(500) NULL COMMENT '评定机构',
  `level` VARCHAR(50) NULL COMMENT '级别'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '研究机构表'
DISTRIBUTED BY HASH(`id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 金融机构 （目前只有投资机构数据）
CREATE TABLE `dw_investor` (
  `id` VARCHAR(100) NULL COMMENT '主键id,投资机构名称md5加密',
  `name` VARCHAR(500) NULL COMMENT '投资机构名称',
  `capital_scale` VARCHAR(100) NULL COMMENT '管理规模单位:亿人民币',
  `current_year_invest_amount` INT NULL COMMENT '今年投资数',
  `exit_invest_amount` INT NULL COMMENT '退出事件数量',
  `intro` VARCHAR(3000) NULL COMMENT '投资机构简介',
  `next_round_count` INT NULL COMMENT '进入下一轮数量',
  `next_round_ratio` DOUBLE NULL COMMENT '进入下一轮率',
  `total_invest_amount` INT NULL COMMENT '总投资数',
  `type` ARRAY<VARCHAR(500)> NULL COMMENT '机构类型',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT 'OLAP'
DISTRIBUTED BY HASH(`id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 政府机关
暂无
-- 行业协会
暂无
-- 人物
CREATE TABLE `dw_expert_new` (
  `id` VARCHAR(100) NOT NULL COMMENT '主键ID',
  `uuid` VARCHAR(100) NULL COMMENT '众包数据ID',
  `name` VARCHAR(100) NULL COMMENT '姓名',
  `gender` VARCHAR(10) NULL COMMENT '性别',
  `org` TEXT NULL COMMENT '主聘机构',
  `department` TEXT NULL COMMENT '主聘机构所在学院',
  `orgs` TEXT NULL COMMENT '任职机构列表',
  `prof_title` TEXT NULL COMMENT '职称',
  `country` TEXT NULL COMMENT '所属国家',
  `address` TEXT NULL COMMENT '地址',
  `resume` TEXT NULL COMMENT '简历',
  `birth_year` SMALLINT NULL COMMENT '出生年份',
  `image` TEXT NULL COMMENT '人物图片链接',
  `url` TEXT NULL COMMENT '人物详情信息链接',
  `position` TEXT NULL COMMENT '工作职位',
  `tel` TEXT NULL COMMENT '联系电话',
  `email` TEXT NULL COMMENT '邮箱地址',
  `research_fields` TEXT NULL COMMENT '研究领域',
  `final_edu_degree` TEXT NULL COMMENT '最终学历',
  `birthplace` TEXT NULL COMMENT '籍贯',
  `honors` TEXT NULL COMMENT '荣誉奖项',
  `awards` TEXT NULL COMMENT '所获奖项',
  `patents` TEXT NULL COMMENT '专利',
  `articles` TEXT NULL COMMENT '论文',
  `projects` TEXT NULL COMMENT '项目',
  `language` TEXT NULL COMMENT '语种',
  `province` TEXT NULL COMMENT '省',
  `city` TEXT NULL COMMENT '市',
  `area` TEXT NULL COMMENT '区',
  `status` SMALLINT NULL COMMENT '状态，0去世，1在世',
  `is_valid` SMALLINT NULL COMMENT '是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
DISTRIBUTED BY HASH(`id`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"function_column.sequence_col" = "update_time",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 商品 只有企业主要产品表，以企业为维度的产品/服务，没有具体型号的商品
CREATE TABLE `dw_company_main_product` (
  `id` VARCHAR(100) NULL COMMENT '企业ID',
  `main_product` VARCHAR(6000) NULL,
  `name` VARCHAR(700) NULL COMMENT '企业名称',
  `credit_code` VARCHAR(50) NULL COMMENT '统一社会信用代码',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT 'OLAP'
DISTRIBUTED BY HASH(`id`) BUCKETS 16
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 项目 （国家自然科学基金项目）
CREATE TABLE `dw_project` (
  `id` VARCHAR(100) NOT NULL COMMENT '主键ID',
  `name` VARCHAR(500) NULL COMMENT '项目名称',
  `url` VARCHAR(500) NULL COMMENT '项目来源',
  `approval_num` VARCHAR(50) NULL COMMENT '批准号',
  `category` VARCHAR(50) NULL COMMENT '项目类型',
  `apply_code` VARCHAR(20) NULL COMMENT '申请代码',
  `abstract_zh` TEXT NULL COMMENT '中文摘要',
  `abstract_en` TEXT NULL COMMENT '英文摘要',
  `approval_year` INT NULL COMMENT '批准年份',
  `funding_amount` VARCHAR(200) NULL COMMENT '资助经费（万元）',
  `funding_value` DECIMAL(24, 4) NULL COMMENT '资助经费数值',
  `funding_unit` VARCHAR(50) NULL COMMENT '资助经费比重单位',
  `participants` TEXT NULL COMMENT '参与者标准化',
  `project_leader` VARCHAR(100) NULL COMMENT '领导者',
  `org` VARCHAR(100) NULL COMMENT '依托单位',
  `resources` TEXT NULL COMMENT '产出成果',
  `keywords` VARCHAR(500) NULL COMMENT '项目关键词',
  `start_date` date NULL COMMENT '项目开始时间',
  `end_date` date NULL COMMENT '项目结题时间',
  `is_valid` TINYINT NULL COMMENT '是否有效',
  `create_time` datetime NULL COMMENT '创建时间',
  `update_time` datetime NULL COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '项目表'
DISTRIBUTED BY HASH(`id`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 专利
CREATE TABLE `dw_patent_china` (
  `id` VARCHAR(60) NOT NULL COMMENT '专利唯一ID',
  `apply_date` date NULL COMMENT '申请日期',
  `public_date` date NULL COMMENT '公开（公告）日',
  `title` TEXT NULL COMMENT '标题原文',
  `title_cn` TEXT NULL COMMENT '标题中文',
  `title_en` TEXT NULL COMMENT '标题英文',
  `abstract` TEXT NULL COMMENT '摘要原文',
  `abstract_cn` TEXT NULL COMMENT '摘要中文',
  `abstract_en` TEXT NULL COMMENT '摘要英文',
  `patent_type` VARCHAR(100) NULL COMMENT '专利类型',
  `apply_code` VARCHAR(100) NULL COMMENT '申请号',
  `initial_public_code` VARCHAR(100) NULL COMMENT '首次公开号',
  `initial_public_date` date NULL COMMENT '首次公开日期',
  `grant_code` VARCHAR(100) NULL COMMENT '授权公开号',
  `grant_date` date NULL COMMENT '授权公开日期',
  `public_code` VARCHAR(100) NULL COMMENT '公开（公告）号',
  `first_claim` TEXT NULL COMMENT '首项权利声明',
  `claims_num` INT NULL COMMENT '权力声明数量',
  `agent` VARCHAR(3000) NULL,
  `agency` VARCHAR(3000) NULL,
  `inventors` ARRAY<TEXT> NULL COMMENT '发明人',
  `inventors_num` INT NULL COMMENT '发明人数量',
  `applicants` ARRAY<TEXT> NULL COMMENT '申请人',
  `applicants_num` INT NULL COMMENT '申请人数量',
  `applicant_type` ARRAY<VARCHAR(200)> NULL COMMENT '申请人类型',
  `applicants_country` ARRAY<VARCHAR(200)> NULL COMMENT '申请人国别',
  `public_country` VARCHAR(200) NULL COMMENT '专利公开国家',
  `applicants_norm` ARRAY<TEXT> NULL COMMENT '标准化申请人',
  `patentees` ARRAY<TEXT> NULL COMMENT '当前权利人',
  `patentees_norm` ARRAY<TEXT> NULL COMMENT '标准化权利人',
  `first_applicant` TEXT NULL COMMENT '第一申请人',
  `patentee_address` ARRAY<TEXT> NULL COMMENT '当前专利权人地址',
  `ipc` ARRAY<VARCHAR(500)> NULL COMMENT 'IPC',
  `main_ipc` VARCHAR(200) NULL COMMENT '主IPC分类号',
  `cpc` ARRAY<VARCHAR(200)> NULL COMMENT 'CPC',
  `nec` ARRAY<VARCHAR(200)> NULL COMMENT '国民经济行业分类编码',
  `sec` ARRAY<VARCHAR(200)> NULL COMMENT '战略新兴产业分类编码',
  `status` VARCHAR(200) NULL COMMENT '状态',
  `address` TEXT NULL COMMENT '申请人地址',
  `province` VARCHAR(100) NULL COMMENT '中国省份',
  `city` VARCHAR(100) NULL COMMENT '中国城市',
  `area` VARCHAR(100) NULL COMMENT '中国区县',
  `ct` ARRAY<VARCHAR(1000)> NULL COMMENT '引证专利号',
  `ctfw` ARRAY<VARCHAR(1000)> NULL COMMENT '被引用专利号',
  `ct_times` INT NULL COMMENT '专利引证个数',
  `ctfw_times` INT NULL COMMENT '专利被引用次数',
  `fct` ARRAY<VARCHAR(1000)> NULL COMMENT '家族引证',
  `fctfw` ARRAY<VARCHAR(1000)> NULL COMMENT '家族被引证',
  `fct_times` INT NULL COMMENT '家族引证数量',
  `fctfw_times` INT NULL COMMENT '家族被引次数',
  `simple_family` ARRAY<VARCHAR(1000)> NULL COMMENT '简单同族专利',
  `simple_family_num` INT NULL COMMENT '简单同族个数',
  `priority_code` ARRAY<VARCHAR(1000)> NULL COMMENT '优先权号',
  `priority_date` ARRAY<DATEV2> NULL COMMENT '优先权日',
  `pct_apply_code` VARCHAR(200) NULL COMMENT 'PCT国际申请号',
  `pct_public_code` VARCHAR(200) NULL COMMENT 'PCT国际公布号',
  `maturity_date` date NULL COMMENT '预估专利到期日',
  `pdf_url` VARCHAR(500) NULL COMMENT 'PDF查看地址',
  `is_valid` TINYINT NULL COMMENT '是否有效',
  `source` VARCHAR(200) NULL COMMENT '来源',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
  `page` INT NULL COMMENT '文献页数',
  `cite_self_times` INT NULL COMMENT '自引次数',
  `cite_other_times` INT NULL COMMENT '他引次数',
  `cited_self_times` INT NULL COMMENT '被自引次数',
  `cited_other_times` INT NULL COMMENT '被他引次数',
  `complete_family` ARRAY<VARCHAR(200)> NULL COMMENT '扩展同族',
  `complete_family_num` INT NULL COMMENT '扩展同族个数',
  `reexamine_invalid_decision_date` ARRAY<DATEV2> NULL COMMENT '复审无效决定日',
  `reexamine_times` INT NULL COMMENT '复审无效决定次数',
  `assign_times` INT NULL COMMENT '转让次数',
  `licence_times` INT NULL COMMENT '许可次数',
  `pledge_times` INT NULL COMMENT '质押次数',
  `pledgor` ARRAY<VARCHAR(5000)> NULL COMMENT '出质人',
  `pledgee` ARRAY<VARCHAR(5000)> NULL COMMENT '质权人',
  `current_pledgee` VARCHAR(5000) NULL COMMENT '当前质权人',
  `expiry_date` date NULL COMMENT '失效日',
  `protection_scope` INT NULL COMMENT '保护范围',
  `estimated_maturity_date` date NULL COMMENT '预估到期日',
  INDEX index_bitmap_apply_date (`apply_date`) USING INVERTED COMMENT '申请日期索引',
  INDEX index_bitmap_patent_type (`patent_type`) USING INVERTED COMMENT '专利类型索引',
  INDEX index_bitmap_status (`status`) USING INVERTED COMMENT '专利状态索引',
  INDEX index_bitmap_public_date (`public_date`) USING INVERTED COMMENT '发布日期索引',
  INDEX index_bitmap_initial_public_date (`initial_public_date`) USING INVERTED COMMENT '首次公开日期索引',
  INDEX index_bitmap_province (`province`) USING INVERTED COMMENT '专利中国省份索引'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '专利表'
DISTRIBUTED BY HASH(`id`) BUCKETS 32
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"bloom_filter_columns" = "apply_code, public_code",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "true",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 文献
CREATE TABLE `dw_article` (
  `id` VARCHAR(100) NOT NULL COMMENT '记录主键',
  `title` TEXT NULL COMMENT '标题',
  `abstract` TEXT NULL COMMENT '摘要',
  `keywords` TEXT NULL COMMENT '关键词',
  `authors` TEXT NULL COMMENT '作者列表',
  `language` VARCHAR(20) NULL COMMENT '语言',
  `year` INT NULL COMMENT '年份',
  `applicants` TEXT NULL COMMENT '申请机构',
  `subject` VARCHAR(200) NULL COMMENT '所属学科',
  `journal` VARCHAR(500) NULL COMMENT '所属期刊',
  `doi` VARCHAR(300) NULL COMMENT 'doi编码',
  `issn` VARCHAR(100) NULL COMMENT 'issn编码',
  `publisher` VARCHAR(300) NULL COMMENT '发表机构',
  `url` VARCHAR(300) NULL COMMENT '原文公开链接',
  `resource_code` VARCHAR(20) NULL COMMENT '文章类型J表示期刊论文，C表示会议论文，D表示',
  `is_valid` TINYINT NULL COMMENT '1表示有效0表示无效',
  `create_time` datetime NULL COMMENT '创建时间',
  `update_time` datetime NULL COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT 'OLAP'
DISTRIBUTED BY HASH(`id`) BUCKETS 16
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 招投标
CREATE TABLE `dw_company_bidder` (
  `id` VARCHAR(100) NULL COMMENT '逐渐',
  `title` VARCHAR(1500) NULL COMMENT '标题',
  `money` VARCHAR(600) NULL COMMENT '金额-公布值',
  `deal_money` DECIMAL(24, 6) NULL COMMENT '金额-处理值',
  `currency` VARCHAR(30) NULL COMMENT '货币名称',
  `public_time` datetime NULL COMMENT '发布时间',
  `public_date` date NULL COMMENT '发布日期',
  `tender` VARCHAR(700) NULL COMMENT '采购人',
  `bidder` VARCHAR(4500) NULL COMMENT '中标人',
  `agency` VARCHAR(200) NULL COMMENT '代理机构',
  `project_address` VARCHAR(200) NULL COMMENT '项目所属地区',
  `zip_code` VARCHAR(10) NULL COMMENT '项目行政区号',
  `project_person` VARCHAR(200) NULL COMMENT '项目联系人',
  `project_tel` VARCHAR(200) NULL COMMENT '项目联系方式',
  `owner_name` VARCHAR(700) NULL COMMENT '业主联系人',
  `owner_tel` VARCHAR(50) NULL COMMENT '业主联系方式',
  `agency_name` VARCHAR(100) NULL COMMENT '代理机构联系人',
  `agency_tel` VARCHAR(50) NULL COMMENT '代理机构联系方式',
  `project_name` VARCHAR(500) NULL COMMENT '项目名称',
  `tender_type` VARCHAR(200) NULL COMMENT '招采分类',
  `bidder_type` VARCHAR(200) NULL COMMENT '中标类型',
  `industry` VARCHAR(200) NULL COMMENT '所属行业',
  `tender_method` VARCHAR(200) NULL COMMENT '招标方式',
  `registration_start_time` datetime NULL COMMENT '报名开始时间',
  `registration_end_time` datetime NULL COMMENT '报名截止时间',
  `opening_time` datetime NULL COMMENT '开标时间',
  `is_valid` TINYINT NULL COMMENT '数据是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT 'OLAP'
DISTRIBUTED BY HASH(`id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
--技术成果
CREATE TABLE `dw_achievement_info` (
  `id` VARCHAR(100) NOT NULL COMMENT '记录唯一标识',
  `name` VARCHAR(700) NULL COMMENT '名称',
  `type` VARCHAR(255) NULL COMMENT '成果类型',
  `publish_time` date NULL COMMENT '公布日期',
  `unit` VARCHAR(1000) NULL COMMENT '所属单位',
  `person` VARCHAR(1000) NULL COMMENT '完成人',
  `location` VARCHAR(1000) NULL COMMENT '所属地区',
  `province` VARCHAR(1000) NULL COMMENT '省份',
  `channel` VARCHAR(1000) NULL COMMENT '所属方向',
  `technology_maturity` TEXT NULL COMMENT '技术成熟度',
  `cooperate_mode` VARCHAR(1000) NULL COMMENT '合作方式',
  `pricing_type` VARCHAR(255) NULL COMMENT '定价方式',
  `softening_price` VARCHAR(255) NULL COMMENT '转化价格',
  `technical_field` VARCHAR(1000) NULL COMMENT '所属领域',
  `application_field` TEXT NULL COMMENT '应用领域',
  `contact` VARCHAR(1000) NULL COMMENT '联系人',
  `phone` VARCHAR(1000) NULL COMMENT '联系电话',
  `email` VARCHAR(1000) NULL COMMENT '邮箱',
  `content` TEXT NULL COMMENT '成果简介',
  `content_html` TEXT NULL COMMENT '成果简介html',
  `html` TEXT NULL COMMENT 'html',
  `site_id` VARCHAR(1000) NULL COMMENT '站点',
  `desired_result` TEXT NULL COMMENT '效益分析',
  `img_url` ARRAY<TEXT> NULL COMMENT '图片链接',
  `source` VARCHAR(1000) NULL COMMENT '来源',
  `url` VARCHAR(1000) NULL COMMENT '链接',
  `is_valid` TINYINT NULL COMMENT '数据是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间',
  `technical_advantages` TEXT NULL COMMENT '技术优势',
  `ipr` TEXT NULL COMMENT '知识产权',
  `honors` TEXT NULL COMMENT '荣誉',
  `content_md` TEXT NULL COMMENT '正文内容MARKDOWN格式',
  `code` VARCHAR(255) NULL COMMENT '成果号'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '成果转化表'
DISTRIBUTED BY HASH(`id`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 标准
CREATE TABLE `dw_standard_local` (
  `id` VARCHAR(100) NOT NULL COMMENT '主键',
  `publish_date` date NULL COMMENT '发布日期',
  `standard_code` VARCHAR(100) NOT NULL COMMENT '标准编码/标准号',
  `standard_name` VARCHAR(500) NULL COMMENT '标准名称中文',
  `standard_name_en` VARCHAR(500) NULL COMMENT '标准名称英文',
  `standard_level` VARCHAR(100) NULL COMMENT '级别-地方标准',
  `local_name` VARCHAR(100) NULL COMMENT '省市区名',
  `effective_date` date NULL COMMENT '生效日期',
  `abolish_date` date NULL COMMENT '废止日期',
  `record_no` VARCHAR(200) NULL COMMENT '备案号',
  `record_date` date NULL COMMENT '备案日期',
  `industry_class` VARCHAR(200) NULL COMMENT '行业分类',
  `standard_type` VARCHAR(200) NULL COMMENT '标准类别',
  `standard_make_type` VARCHAR(100) NULL COMMENT '标准制订/修订',
  `standard_number_cn` VARCHAR(200) NULL COMMENT '中国标准分类号',
  `standard_number_in` VARCHAR(200) NULL COMMENT '国际标准分类号',
  `publish_department` VARCHAR(200) NULL COMMENT '批准发布部门',
  `drafter` TEXT NULL COMMENT '起草人',
  `drafting_unit` TEXT NULL COMMENT '起草单位',
  `url_link` VARCHAR(200) NULL COMMENT '源链接',
  `details` TEXT NULL COMMENT '详细描述',
  `source` VARCHAR(200) NULL COMMENT '来源',
  `status` VARCHAR(200) NULL COMMENT '状态',
  `is_valid` TINYINT NULL COMMENT '是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`, `publish_date`)
COMMENT '地方标准表'
DISTRIBUTED BY HASH(`publish_date`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);

CREATE TABLE `dw_standard_industry` (
  `id` VARCHAR(100) NOT NULL COMMENT '主键',
  `publish_date` date NULL COMMENT '发布日期',
  `standard_code` VARCHAR(100) NOT NULL COMMENT '标准编码/标准号',
  `standard_name` VARCHAR(500) NULL COMMENT '标准名称中文',
  `standard_name_en` VARCHAR(500) NULL COMMENT '标准名称英文',
  `standard_level` VARCHAR(100) NULL COMMENT '级别-行业标准',
  `domain_code` VARCHAR(200) NULL COMMENT '领域代码',
  `domain_name` VARCHAR(200) NULL COMMENT '领域名称',
  `industry_class` VARCHAR(200) NULL COMMENT '行业分类',
  `record_no` VARCHAR(200) NULL COMMENT '备案号',
  `record_date` date NULL COMMENT '备案日期',
  `effective_date` date NULL COMMENT '生效日期',
  `abolish_date` date NULL COMMENT '废止日期',
  `standard_type` VARCHAR(200) NULL COMMENT '标准类别',
  `standard_make_type` VARCHAR(100) NULL COMMENT '标准制订/修订',
  `standard_replace` TEXT NULL COMMENT '代替标准',
  `standard_number_cn` VARCHAR(200) NULL COMMENT '中国标准分类号',
  `standard_number_in` VARCHAR(200) NULL COMMENT '国际标准分类号',
  `publish_department` VARCHAR(200) NULL COMMENT '批准发布部门',
  `drafter` TEXT NULL COMMENT '起草人',
  `drafting_unit` TEXT NULL COMMENT '起草单位',
  `url_link` VARCHAR(200) NULL COMMENT '源链接',
  `details` TEXT NULL COMMENT '详细描述',
  `source` VARCHAR(200) NULL COMMENT '来源',
  `status` VARCHAR(200) NULL COMMENT '状态',
  `is_valid` TINYINT NULL COMMENT '是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`, `publish_date`)
COMMENT '行业标准表'
DISTRIBUTED BY HASH(`publish_date`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);

CREATE TABLE `dw_standard_nation` (
  `id` VARCHAR(100) NOT NULL COMMENT '主键',
  `publish_date` date NULL COMMENT '发布日期',
  `standard_code` VARCHAR(100) NOT NULL COMMENT '标准编码/标准号',
  `standard_name` VARCHAR(500) NULL COMMENT '标准名称中文',
  `standard_name_en` VARCHAR(500) NULL COMMENT '标准名称英文',
  `standard_level` VARCHAR(100) NULL COMMENT '级别-国家标准',
  `effective_date` date NULL COMMENT '生效日期',
  `abolish_date` date NULL COMMENT '废止日期',
  `standard_type` VARCHAR(200) NULL COMMENT '标准类别',
  `standard_number_cn` VARCHAR(200) NULL COMMENT '中国标准分类号',
  `standard_number_in` VARCHAR(200) NULL COMMENT '国际标准分类号',
  `technical_unit` VARCHAR(200) NULL COMMENT '归口单位',
  `effect_unit` VARCHAR(200) NULL COMMENT '执行单位',
  `competent_department` VARCHAR(200) NULL COMMENT '主管部门',
  `drafter` TEXT NULL COMMENT '起草人',
  `drafting_unit` TEXT NULL COMMENT '起草单位',
  `url_link` VARCHAR(200) NULL COMMENT '源链接',
  `details` TEXT NULL COMMENT '详细描述',
  `source` VARCHAR(200) NULL COMMENT '来源',
  `nature` VARCHAR(200) NULL COMMENT '特性',
  `status` VARCHAR(200) NULL COMMENT '状态',
  `is_valid` TINYINT NULL COMMENT '是否有效',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`id`, `publish_date`)
COMMENT '国家标准表'
DISTRIBUTED BY HASH(`publish_date`) BUCKETS 4
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "true",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
-- 榜单
CREATE TABLE `dw_list` (
  `id` VARCHAR(64) NOT NULL COMMENT '主键name+publish_orgnazation+publish_time',
  `name` VARCHAR(255) NOT NULL COMMENT '榜单名称',
  `description` VARCHAR(1000) NULL COMMENT '榜单介绍',
  `url` VARCHAR(1000) NULL COMMENT 'URL',
  `publish_organization` VARCHAR(255) NULL COMMENT '发布方',
  `publish_time` date NOT NULL COMMENT '发布时间',
  `first_sort` VARCHAR(255) NULL COMMENT '一级分类',
  `second_sort` VARCHAR(255) NULL COMMENT '二级分类',
  `is_official` TINYINT NULL COMMENT '是否官方发布',
  `indicator` VARCHAR(2000) NULL COMMENT '榜单排名依据',
  `lz_industry_chain` VARCHAR(255) NULL COMMENT '所属产业链',
  `is_valid` TINYINT NOT NULL DEFAULT "1" COMMENT '有效标识符（1 有效，0 无效，默认有效）',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '榜单数据表'
DISTRIBUTED BY HASH(`id`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);
CREATE TABLE `dw_list_detail` (
  `id` VARCHAR(64) NOT NULL COMMENT '主键md5(concat(company_name,pid))',
  `pid` VARCHAR(64) NOT NULL COMMENT '榜单id',
  `name` VARCHAR(255) NOT NULL COMMENT '榜单名称',
  `sort_order` VARCHAR(50) NULL COMMENT '排序',
  `cid` VARCHAR(255) NULL COMMENT '企业id',
  `company_name` VARCHAR(255) NOT NULL COMMENT '企业名称',
  `credit_code` VARCHAR(255) NULL COMMENT '统一社会信用代码',
  `main_product` VARCHAR(1000) NULL COMMENT '核心产品',
  `industry` VARCHAR(255) NULL COMMENT '所属赛道',
  `indicator_value` VARCHAR(2000) NULL COMMENT '值',
  `indicator_unit` VARCHAR(255) NULL COMMENT '指标单位',
  `is_valid` TINYINT NOT NULL DEFAULT "1" COMMENT '有效标识符（1 有效，0 无效，默认有效）',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据修改时间'
) ENGINE=OLAP
UNIQUE KEY(`id`)
COMMENT '榜单详情表'
DISTRIBUTED BY HASH(`id`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 3",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"binlog.enable" = "false",
"binlog.ttl_seconds" = "86400",
"binlog.max_bytes" = "9223372036854775807",
"binlog.max_history_nums" = "9223372036854775807",
"enable_single_replica_compaction" = "false"
);