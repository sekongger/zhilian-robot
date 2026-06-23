const path = require("path");

let pptxgen;
try {
  pptxgen = require("pptxgenjs");
} catch (err) {
  pptxgen = require(path.resolve(
    __dirname,
    "..",
    "tmp",
    "dataflow_kag_operatorization_boss_ppt",
    "node_modules",
    "pptxgenjs",
  ));
}
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

const OUT = path.resolve(
  __dirname,
  "..",
  "docs",
  "reports",
  "dataflow_kag_openspg_operatorization_boss_presentation.pptx",
);

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "zhilian-robot";
pptx.subject = "DataFlow 与 OpenSPG/KAG 协同的知识抽取算子化方案";
pptx.title = "知识抽取算子化设计方案";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "PingFang SC",
  bodyFontFace: "PingFang SC",
  lang: "zh-CN",
};

const C = {
  bg: "F5F7FB",
  navy: "132849",
  blue: "2E6ADF",
  teal: "2C8E83",
  cyan: "4AA6C0",
  gold: "D89D33",
  red: "D35D6E",
  text: "263548",
  muted: "68778B",
  white: "FFFFFF",
  line: "D7E0EA",
  paleBlue: "EAF2FF",
  paleTeal: "EAF8F5",
  paleCyan: "EBF8FC",
  paleGold: "FBF4E8",
  paleRose: "FCEEF0",
  paleGray: "EEF2F7",
};

function addBg(slide) {
  slide.background = { color: C.bg };
}

function addTopBar(slide, title, kicker = "") {
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.88,
    line: { color: C.navy, transparency: 100 },
    fill: { color: C.navy },
  });
  slide.addText(title, {
    x: 0.62,
    y: 0.16,
    w: 8.8,
    h: 0.34,
    fontFace: "PingFang SC",
    fontSize: 22,
    bold: true,
    color: C.white,
    margin: 0,
  });
  if (kicker) {
    slide.addText(kicker, {
      x: 9.45,
      y: 0.18,
      w: 3.15,
      h: 0.2,
      fontFace: "PingFang SC",
      fontSize: 10.5,
      color: C.white,
      align: "right",
      margin: 0,
    });
  }
}

function addTitle(slide, title, subtitle = "") {
  slide.addText(title, {
    x: 0.72,
    y: 1.02,
    w: 11.4,
    h: 0.48,
    fontFace: "PingFang SC",
    fontSize: 28,
    bold: true,
    color: C.navy,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.76,
      y: 1.66,
      w: 11.8,
      h: 0.32,
      fontFace: "PingFang SC",
      fontSize: 13,
      color: C.muted,
      margin: 0,
    });
  }
}

function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: "PingFang SC",
    fontSize: opts.fontSize || 16,
    bold: !!opts.bold,
    color: opts.color || C.text,
    margin: opts.margin || 0,
    align: opts.align || "left",
    valign: opts.valign || "top",
    breakLine: false,
  });
}

function addBullets(slide, items, x, y, w, h, fontSize = 15, color = C.text) {
  const runs = [];
  items.forEach((item) => {
    runs.push({
      text: item,
      options: { bullet: { indent: 18 }, breakLine: true },
    });
  });
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    fontFace: "PingFang SC",
    fontSize,
    color,
    margin: 0,
    valign: "top",
  });
}

function addCard(slide, { x, y, w, h, title, lines = [], fill = C.white, titleColor = C.navy }) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: C.line, pt: 1 },
    fill: { color: fill },
    shadow: { type: "outer", color: "AAB7C7", blur: 1, angle: 45, distance: 1, opacity: 0.08 },
  });
  addText(slide, title, x + 0.18, y + 0.14, w - 0.34, 0.24, {
    fontSize: 16,
    bold: true,
    color: titleColor,
  });
  if (lines.length) addBullets(slide, lines, x + 0.16, y + 0.5, w - 0.32, h - 0.62, 13, C.text);
}

function addTag(slide, text, x, y, w, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.36,
    rectRadius: 0.08,
    line: { color: fill, transparency: 100 },
    fill: { color: fill },
  });
  addText(slide, text, x, y + 0.08, w, 0.16, {
    fontSize: 11.5,
    bold: true,
    color: C.navy,
    align: "center",
    valign: "mid",
  });
}

function addStepBox(slide, x, y, w, h, num, title, lines, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: C.line, pt: 1 },
    fill: { color: fill },
  });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: x + 0.18,
    y: y + 0.14,
    w: 0.34,
    h: 0.34,
    line: { color: C.blue, transparency: 100 },
    fill: { color: C.blue },
  });
  addText(slide, String(num), x + 0.18, y + 0.215, 0.34, 0.08, {
    fontSize: 12,
    bold: true,
    color: C.white,
    align: "center",
  });
  addText(slide, title, x + 0.6, y + 0.13, w - 0.8, 0.22, {
    fontSize: 15,
    bold: true,
    color: C.navy,
  });
  addBullets(slide, lines, x + 0.18, y + 0.58, w - 0.32, h - 0.72, 12.5);
}

function addChevron(slide, x, y, color = C.blue) {
  slide.addShape(pptx.ShapeType.chevron, {
    x,
    y,
    w: 0.16,
    h: 0.12,
    line: { color, transparency: 100 },
    fill: { color },
  });
}

function addFooterConclusion(slide, text) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.72,
    y: 6.72,
    w: 11.85,
    h: 0.42,
    rectRadius: 0.06,
    line: { color: C.navy, transparency: 100 },
    fill: { color: C.navy },
  });
  addText(slide, text, 0.95, 6.84, 11.4, 0.12, {
    fontSize: 16,
    bold: true,
    color: C.white,
    align: "center",
  });
}

function validate(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

function cover() {
  const slide = pptx.addSlide();
  addBg(slide);
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 1.02,
    line: { color: C.navy, transparency: 100 },
    fill: { color: C.navy },
  });
  addText(slide, "知识抽取算子化设计方案", 0.76, 1.18, 11.3, 0.62, {
    fontSize: 29,
    bold: true,
    color: C.navy,
  });
  addText(
    slide,
    "基于 DataFlow 思想与 OpenSPG/KAG 协同的具体方案提案",
    0.8,
    1.95,
    10.5,
    0.24,
    { fontSize: 16, color: C.muted },
  );
  addTag(slide, "不是概念宣讲", 0.82, 3.0, 1.8, C.paleRose);
  addTag(slide, "是具体方案提案", 2.8, 3.0, 2.0, C.paleBlue);
  addTag(slide, "聚焦首期设计", 5.0, 3.0, 1.8, C.paleTeal);
  addTag(slide, "支持后续 agent", 7.0, 3.0, 2.0, C.paleGold);
  addBullets(
    slide,
    [
      "回答三件事：为什么现在要做、方案具体怎么设计、第一期先落什么。",
      "核心判断：DataFlow 负责把原始数据整理成标准数据，KAG/OpenSPG 负责把标准数据抽成知识并构图。",
      "目标不是替换现有体系，而是把知识抽取任务本身做成一套标准化算子目录。",
    ],
    0.92,
    4.0,
    11.2,
    1.6,
    18,
  );
  addText(slide, "老板汇报版 | 2026-03-30", 0.82, 6.6, 3.2, 0.16, {
    fontSize: 11,
    color: C.muted,
  });
  validate(slide);
}

function whyNow() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "为什么现在要做这件事", "问题定义");
  addCard(slide, {
    x: 0.7, y: 1.4, w: 3.85, h: 4.9, fill: C.paleBlue, title: "输入越来越多样",
    lines: [
      "常识数据、资讯、研报三类输入同时存在。",
      "结构化表、短文本、长 PDF 的处理方式天然不同。",
      "如果没有统一能力层，后续每接一种数据都要单独补流程。"
    ]
  });
  addCard(slide, {
    x: 4.75, y: 1.4, w: 3.85, h: 4.9, fill: C.paleCyan, title: "现有链路能跑但不够标准",
    lines: [
      "已有资讯抽取、常识层处理、融合链路，但步骤分散。",
      "很多能力已经有边界，却还没有整理成标准算子。",
      "复用、组合、监控、评估都还不够方便。"
    ]
  });
  addCard(slide, {
    x: 8.8, y: 1.4, w: 3.85, h: 4.9, fill: C.paleTeal, title: "未来能力升级会受限",
    lines: [
      "新数据源接入成本会持续上升。",
      "知识抽取难以沉淀成平台能力。",
      "后续如果要支持 agent 自动调用，缺少清晰能力接口。"
    ]
  });
  addFooterConclusion(slide, "结论：我们需要把知识抽取从“分散功能”升级成“标准算子体系”。");
  validate(slide);
}

function dataflowSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "DataFlow 的核心思想", "上游治理");
  addText(slide, "DataFlow 最有价值的不是某个单算子，而是“算子化的数据处理方式”。", 0.78, 1.06, 11.5, 0.24, {
    fontSize: 15, color: C.muted,
  });

  addStepBox(slide, 0.7, 1.6, 2.15, 3.9, 1, "接入原始数据", [
    "文件、URL、网页、PDF、文本等多种来源。",
    "先统一进入标准处理流程。",
  ], C.paleBlue);
  addStepBox(slide, 3.05, 1.6, 2.15, 3.9, 2, "清洗与规范化", [
    "清理噪声、修正文档格式、统一文本表达。",
    "让数据先变得可继续处理。",
  ], C.paleCyan);
  addStepBox(slide, 5.4, 1.6, 2.15, 3.9, 3, "切块与过滤", [
    "把长文拆成可处理的标准块。",
    "同时做去重、质量过滤、结构整理。",
  ], C.paleTeal);
  addStepBox(slide, 7.75, 1.6, 2.15, 3.9, 4, "输出标准数据", [
    "不是直接建图，而是输出更干净的中间数据。",
    "供下游模型或知识系统继续使用。",
  ], C.paleGold);

  addChevron(slide, 2.88, 3.2);
  addChevron(slide, 5.23, 3.2);
  addChevron(slide, 7.58, 3.2);

  addCard(slide, {
    x: 10.2, y: 1.6, w: 2.45, h: 3.9, fill: C.white, title: "对我们的启发",
    lines: [
      "每个步骤都拆成清晰算子。",
      "统一输入输出。",
      "让流程可编排、可复用、可被 agent 调用。"
    ]
  });
  addFooterConclusion(slide, "结论：DataFlow 解决的是“原始数据如何变成标准数据”，它提供的是方法论而不是图谱本身。");
  validate(slide);
}

function processDecompositionSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "我们的知识抽取流程可以拆成几步", "流程拆解");
  addText(slide, "在借鉴 DataFlow 之前，先把自己的知识抽取任务拆清楚，才能判断每一步是否适合算子化。", 0.78, 1.06, 11.8, 0.22, {
    fontSize: 15, color: C.muted,
  });
  addStepBox(slide, 0.68, 1.52, 2.35, 5.0, 1, "文档理解", [
    "输入：资讯正文、PDF、网页、研报。",
    "功能：读取、转文本、保留来源信息。",
    "判断：适合做标准算子。"
  ], C.paleBlue);
  addStepBox(slide, 3.17, 1.52, 2.35, 5.0, 2, "结构整理", [
    "输入：长文或复杂文档。",
    "功能：切块、章节提取、表格结构化。",
    "判断：非常适合算子化。"
  ], C.paleCyan);
  addStepBox(slide, 5.66, 1.52, 2.35, 5.0, 3, "知识抽取", [
    "输入：标准 chunk。",
    "功能：实体、关系、事件抽取，实体标准化。",
    "判断：可拆成核心抽取算子。"
  ], C.paleTeal);
  addStepBox(slide, 8.15, 1.52, 2.35, 5.0, 4, "融合归一", [
    "输入：多源知识种子。",
    "功能：实体融合、事件归一、概念挂载。",
    "判断：需要业务算子。"
  ], C.paleGold);
  addStepBox(slide, 10.64, 1.52, 2.0, 5.0, 5, "统一落图", [
    "输入：已融合结果。",
    "功能：结构化映射、图批次构建、写图。",
    "判断：适合算子化并接 OpenSPG。"
  ], C.paleRose);
  addFooterConclusion(slide, "结论：我们的知识抽取流程至少可拆成 5 步，其中大部分都适合标准算子化。");
  validate(slide);
}

function stepAnalysisSlide({ title, kicker, whyLines, decoupleLines, ioTitle, ioLines, fillA = C.paleBlue, fillB = C.paleCyan, fillC = C.paleGold }) {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, title, kicker);
  addCard(slide, {
    x: 0.72, y: 1.45, w: 3.78, h: 4.95, fill: fillA, title: "为什么适合做成算子",
    lines: whyLines,
  });
  addCard(slide, {
    x: 4.79, y: 1.45, w: 3.78, h: 4.95, fill: fillB, title: "为什么这一步可以与具体任务解耦",
    lines: decoupleLines,
  });
  addCard(slide, {
    x: 8.86, y: 1.45, w: 3.78, h: 4.95, fill: fillC, title: ioTitle,
    lines: ioLines,
  });
  return slide;
}

function docUnderstandingStep() {
  const slide = stepAnalysisSlide({
    title: "步骤一：文档理解为什么适合做成算子",
    kicker: "逐步展开 1/5",
    whyLines: [
      "它处理的是共性问题：文件怎么读、网页怎么转文本、来源信息怎么保留。",
      "这一步不依赖行业 schema，也不依赖具体图谱类型。",
      "无论是资讯、研报还是公告，都要先把原始载体转成标准文档对象。 ",
    ],
    decoupleLines: [
      "它关注的是“格式”和“来源”，不是“知识含义”。",
      "上游换数据源时，只需替换 reader，不必重写后面的抽取逻辑。",
      "下游抽实体、抽关系、做融合都可以共享同一份 DocumentDTO。",
    ],
    ioTitle: "建议输入 / 输出与代表算子",
    ioLines: [
      "输入：DocumentSourceDTO(file_path / url / content / metadata)",
      "输出：DocumentDTO(title / raw_text / source / publish_time)",
      "代表算子：DocumentReaderOperator",
      "可复用能力：KAG reader 系列",
    ],
  });
  addFooterConclusion(slide, "结论：文档理解层天然是公共能力，最适合作为统一入口算子。");
  validate(slide);
}

function structuringStep() {
  const slide = stepAnalysisSlide({
    title: "步骤二：结构整理为什么适合做成算子",
    kicker: "逐步展开 2/5",
    whyLines: [
      "长文切块、章节提取、表格抽离本质上是通用文档处理动作。",
      "这一步直接影响后续抽取质量，但本身不等于知识抽取。",
      "把它做成算子后，切块策略、表格策略可以按文档类型独立调整。",
    ],
    decoupleLines: [
      "它只负责把文档拆成更适合处理的结构单元，不判断知识类型。",
      "同一个 chunk 既可以送给实体抽取，也可以送给摘要、表格解析、证据定位。",
      "因此它和具体任务目标是弱耦合的，是标准中间层。",
    ],
    ioTitle: "建议输入 / 输出与代表算子",
    ioLines: [
      "输入：DocumentDTO",
      "输出：ChunkDTO[] / OutlineDTO / TableSeedDTO[]",
      "代表算子：DocumentChunkSplitOperator / OutlineExtractOperator / TableExtractOperator",
      "可复用能力：KAG splitter、outline_extractor、table_extractor",
    ],
    fillA: C.paleCyan,
    fillB: C.paleTeal,
    fillC: C.paleBlue,
  });
  addFooterConclusion(slide, "结论：结构整理层最适合沉淀成标准中间件生产算子。");
  validate(slide);
}

function extractionStep() {
  const slide = stepAnalysisSlide({
    title: "步骤三：知识抽取为什么适合做成算子",
    kicker: "逐步展开 3/5",
    whyLines: [
      "实体、关系、事件抽取本身就已经是清晰可分的处理动作。",
      "KAG 当前实现里已经把 NER、标准化、关系抽取、事件抽取拆成独立方法。",
      "所以这里不是从零设计，而是把已有能力标准化封装。",
    ],
    decoupleLines: [
      "输入只要是标准 chunk，这一步就能工作，不必绑定具体来源。",
      "它输出的是知识种子，不直接决定最终图里的主实体和最终关系。",
      "因此它可以和后面的实体融合、概念挂载、图谱落地解耦。",
    ],
    ioTitle: "建议输入 / 输出与代表算子",
    ioLines: [
      "输入：ChunkDTO + 可选 SchemaRef",
      "输出：EntitySeedDTO[] / RelationSeedDTO[] / EventSeedDTO[]",
      "代表算子：EntityExtractOperator / EntityStandardizeOperator / RelationExtractOperator / EventExtractOperator",
      "可复用能力：schema_constraint_extractor / schema_free_extractor",
    ],
    fillA: C.paleTeal,
    fillB: C.paleBlue,
    fillC: C.paleGold,
  });
  addFooterConclusion(slide, "结论：知识抽取层适合拆成核心算子目录，是整套体系的能力中心。");
  validate(slide);
}

function fusionStep() {
  const slide = stepAnalysisSlide({
    title: "步骤四：融合归一为什么也要做成算子",
    kicker: "逐步展开 4/5",
    whyLines: [
      "真正进入统一大图之前，必须先解决同名异源、别名、事件重复和概念挂载问题。",
      "这一步虽然业务性更强，但边界其实非常清楚。",
      "如果不算子化，这部分会长期散落在各条链路里，难以复用。 ",
    ],
    decoupleLines: [
      "它不关心文本怎么抽出来，只关心已经抽出的知识种子如何合并。",
      "它也不关心最后落到哪个图库，只关心如何得到 canonical entity / canonical event。",
      "因此它可以独立成融合算子层。 ",
    ],
    ioTitle: "建议输入 / 输出与代表算子",
    ioLines: [
      "输入：EntitySeedDTO[] / EventSeedDTO[] / ConceptSeedDTO[]",
      "输出：CanonicalEntityDTO[] / CanonicalEventDTO[] / enriched concepts",
      "代表算子：EntityResolveOperator / EventResolveOperator / ConceptBindOperator",
      "主要是自研业务算子，KAG 不直接替代这层。",
    ],
    fillA: C.paleGold,
    fillB: C.paleRose,
    fillC: C.paleCyan,
  });
  addFooterConclusion(slide, "结论：融合归一层虽然更业务化，但仍然完全可以标准算子化。");
  validate(slide);
}

function graphBuildStep() {
  const slide = stepAnalysisSlide({
    title: "步骤五：统一落图为什么适合做成算子",
    kicker: "逐步展开 5/5",
    whyLines: [
      "落图本质上是把已整理好的知识对象转换成统一图谱操作。",
      "它需要稳定、可重试、可监控，不应混在抽取逻辑里。",
      "把落图做成独立算子后，图谱底座可以替换，抽取层不必重写。",
    ],
    decoupleLines: [
      "它只依赖标准 graph DTO，不依赖上游具体模型或文本来源。",
      "只要上游输出统一 GraphImportBatchDTO，下游就可以独立写图。",
      "因此它天然适合做成标准 sink operator。",
    ],
    ioTitle: "建议输入 / 输出与代表算子",
    ioLines: [
      "输入：GraphSeedDTO / GraphImportBatchDTO",
      "输出：GraphImportResultDTO",
      "代表算子：StructuredGraphWriteOperator / FusionGraphImportOperator",
      "可复用能力：KGWriter；统一大图导入需要结合自研 importer。",
    ],
    fillA: C.paleRose,
    fillB: C.paleGold,
    fillC: C.paleBlue,
  });
  addFooterConclusion(slide, "结论：统一落图层应当从抽取逻辑中分离出来，作为独立图谱落地算子。");
  validate(slide);
}

function kagSpgSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "KAG / OpenSPG 在这条链里承担什么角色", "知识构建");
  addCard(slide, {
    x: 0.72, y: 1.45, w: 3.05, h: 4.9, fill: C.paleBlue, title: "KAG 的组件能力",
    lines: [
      "reader：读取文档",
      "splitter：切块",
      "extractor：抽实体、关系、事件",
      "mapping：把结构化记录映射成图",
      "writer：写入图谱"
    ]
  });
  addCard(slide, {
    x: 4.1, y: 1.45, w: 4.15, h: 4.9, fill: C.paleCyan, title: "OpenSPG 的平台能力",
    lines: [
      "定义 schema 作为统一知识边界。",
      "承载实体、关系、概念和事件图谱。",
      "提供统一存储、查询与后续推理计算能力。"
    ]
  });
  addCard(slide, {
    x: 8.58, y: 1.45, w: 4.02, h: 4.9, fill: C.paleTeal, title: "为什么要和 DataFlow 思想结合", 
    lines: [
      "KAG / OpenSPG 更像知识构建引擎，而不是原始数据治理框架。",
      "DataFlow 提供的是流程拆解和算子化的方法。",
      "所以我们要做的是：复用 KAG 能力，用 DataFlow 思想统一封装。"
    ]
  });
  addFooterConclusion(slide, "结论：KAG 提供可复用组件，OpenSPG 提供图谱底座，我们要补的是统一算子层。");
  validate(slide);
}

function concreteDesign() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "我们的具体方案总图", "四层结构");
  addStepBox(slide, 0.68, 1.48, 2.9, 4.95, 1, "文档理解层", [
    "对象：PDF、Word、网页、资讯正文。",
    "职责：读取文档、切块、章节提取、表格提取。",
    "代表算子：DocumentReader / ChunkSplit / OutlineExtract / TableExtract。",
  ], C.paleBlue);
  addStepBox(slide, 3.83, 1.48, 2.9, 4.95, 2, "知识抽取层", [
    "对象：chunk、文本片段。",
    "职责：实体、关系、事件抽取与标准化。",
    "代表算子：EntityExtract / EntityStandardize / RelationExtract / EventExtract。",
  ], C.paleCyan);
  addStepBox(slide, 6.98, 1.48, 2.9, 4.95, 3, "结构化映射层", [
    "对象：常识数据表、关系表、概念表。",
    "职责：结构化实体和关系映射、概念层级导入。",
    "代表算子：StructuredEntityMap / StructuredRelationMap / ConceptHierarchyMap。",
  ], C.paleTeal);
  addStepBox(slide, 10.13, 1.48, 2.5, 4.95, 4, "融合落图层", [
    "对象：实体种子、事件种子、概念种子。",
    "职责：实体融合、事件归一、概念挂载、统一落图。",
    "代表算子：EntityResolve / EventResolve / ConceptBind / FusionGraphImport。",
  ], C.paleGold);
  addFooterConclusion(slide, "结论：我们不是泛谈算子化，而是已经形成了清晰的四层方案。");
  validate(slide);
}

function reuseBoundary() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "哪些能力复用 KAG，哪些能力需要新增", "边界清晰");
  addCard(slide, {
    x: 0.72, y: 1.45, w: 3.75, h: 4.95, fill: C.paleBlue, title: "可直接复用或轻包装复用",
    lines: [
      "reader / splitter / extractor / mapping / writer",
      "schema_constraint_extractor、schema_free_extractor、table_extractor",
      "spg_type_mapping、spo_mapping、kg_writer",
    ]
  });
  addCard(slide, {
    x: 4.78, y: 1.45, w: 3.75, h: 4.95, fill: C.paleCyan, title: "需要新增统一包装", 
    lines: [
      "统一 DTO",
      "统一算子注册元数据",
      "统一路由条件",
      "统一运行统计与 agent 调用协议",
    ]
  });
  addCard(slide, {
    x: 8.84, y: 1.45, w: 3.75, h: 4.95, fill: C.paleRose, title: "必须保留的自研融合能力",
    lines: [
      "EntityResolver：主实体融合",
      "EventResolve：事件归一",
      "ConceptBind：概念挂载",
      "统一大图批次构建与导入",
    ]
  });
  addFooterConclusion(slide, "结论：我们不是从零开始，而是在复用 KAG 基础上做统一封装。");
  validate(slide);
}

function phaseOne() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "首期算子目录与三条业务链落位", "先做什么");
  addCard(slide, {
    x: 0.72, y: 1.4, w: 4.2, h: 5.15, fill: C.paleBlue, title: "首期优先落地的 10 个核心算子",
    lines: [
      "DocumentReaderOperator",
      "DocumentChunkSplitOperator",
      "EntityExtractOperator",
      "EntityStandardizeOperator",
      "RelationExtractOperator",
      "EventExtractOperator",
      "StructuredEntityMapOperator",
      "StructuredRelationMapOperator",
      "EntityResolveOperator",
      "ConceptBindOperator",
    ]
  });
  addCard(slide, {
    x: 5.18, y: 1.4, w: 2.28, h: 5.15, fill: C.paleCyan, title: "常识数据链",
    lines: [
      "结构化表",
      "StructuredEntityMap / StructuredRelationMap",
      "EntityResolve / ConceptBind",
      "OpenSPG",
    ]
  });
  addCard(slide, {
    x: 7.66, y: 1.4, w: 2.28, h: 5.15, fill: C.paleTeal, title: "资讯链",
    lines: [
      "资讯正文",
      "Reader / ChunkSplit",
      "Entity / Relation / Event Extract",
      "EventResolve / ConceptBind",
      "OpenSPG",
    ]
  });
  addCard(slide, {
    x: 10.14, y: 1.4, w: 2.46, h: 5.15, fill: C.paleGold, title: "研报链",
    lines: [
      "PDF / 网页研报",
      "Reader / ChunkSplit / Outline / Table",
      "Entity / Relation / Event Extract",
      "EntityResolve / ConceptBind",
      "OpenSPG",
    ]
  });
  addFooterConclusion(slide, "结论：首期不是做大而全，而是先把三条主业务链的核心能力标准化。");
  validate(slide);
}

function valueRoadmap() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "业务价值与落地路径", "收束结论");
  addCard(slide, {
    x: 0.72, y: 1.45, w: 3.78, h: 4.9, fill: C.paleBlue, title: "业务价值",
    lines: [
      "新数据源接入更快。",
      "抽取能力从项目能力升级为平台能力。",
      "不同链路的复用和协同会更容易。",
      "为后续 agent 调用和自动编排打基础。",
    ]
  });
  addCard(slide, {
    x: 4.79, y: 1.45, w: 3.78, h: 4.9, fill: C.paleCyan, title: "技术价值",
    lines: [
      "能力边界清晰，步骤更容易观察和评估。",
      "KAG 复用率更高，自研部分只聚焦融合与语义。",
      "图谱构建链路从脚本驱动转向算子驱动。",
    ]
  });
  addCard(slide, {
    x: 8.86, y: 1.45, w: 3.78, h: 4.9, fill: C.paleGold, title: "落地路径",
    lines: [
      "第一步：梳理现有步骤，形成统一算子目录。",
      "第二步：优先落地首期 10 个核心算子。",
      "第三步：补齐统一注册、观测与 agent 调用协议。",
    ]
  });
  addFooterConclusion(slide, "结论：这项工作本质上是在为知识抽取平台化和智能化打基础。");
  validate(slide);
}

cover();
whyNow();
dataflowSlide();
processDecompositionSlide();
docUnderstandingStep();
structuringStep();
extractionStep();
fusionStep();
graphBuildStep();
kagSpgSlide();
concreteDesign();
reuseBoundary();
phaseOne();
valueRoadmap();

pptx.writeFile({ fileName: OUT });
