const pptxgen = require("pptxgenjs");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

const path = require("path");

const OUT = path.resolve(
  __dirname,
  "dataflow_openspg_preprocessing_boss_presentation_v2.pptx",
);

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "zhilian-robot";
pptx.subject = "DataFlow 与 OpenSPG 前置处理层方案";
pptx.title = "DataFlow 与 OpenSPG 结合的前置处理层方案";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "PingFang SC",
  bodyFontFace: "PingFang SC",
  lang: "zh-CN",
};

const C = {
  bg: "F4F7FB",
  navy: "152C52",
  blue: "2D6CDF",
  cyan: "4EA8C7",
  mint: "55B59A",
  gold: "D89B2B",
  text: "283547",
  muted: "6B7788",
  line: "D7E0EA",
  white: "FFFFFF",
  paleBlue: "EAF2FF",
  paleMint: "EAF8F4",
  paleCyan: "EAF7FB",
  paleGold: "FBF4E8",
  paleRose: "FBEFF1",
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
    x: 0.6,
    y: 0.16,
    w: 8.8,
    h: 0.35,
    fontFace: "PingFang SC",
    fontSize: 22,
    bold: true,
    color: C.white,
    margin: 0,
  });
  if (kicker) {
    slide.addText(kicker, {
      x: 9.5,
      y: 0.19,
      w: 3.2,
      h: 0.25,
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
    y: 1.05,
    w: 11.2,
    h: 0.52,
    fontFace: "PingFang SC",
    fontSize: 28,
    bold: true,
    color: C.navy,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.76,
      y: 1.7,
      w: 11.6,
      h: 0.42,
      fontFace: "PingFang SC",
      fontSize: 13,
      color: C.muted,
      margin: 0,
    });
  }
}

function addCard(slide, opts) {
  const {
    x,
    y,
    w,
    h,
    title,
    fill = C.white,
    titleColor = C.navy,
    lines = [],
  } = opts;
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: C.line, pt: 1 },
    fill: { color: fill },
    shadow: { type: "outer", color: "B8C6D9", blur: 1, angle: 45, distance: 1, opacity: 0.08 },
  });
  slide.addText(title, {
    x: x + 0.2,
    y: y + 0.14,
    w: w - 0.35,
    h: 0.24,
    fontFace: "PingFang SC",
    fontSize: 15.5,
    bold: true,
    color: titleColor,
    margin: 0,
  });
  if (lines.length) {
    const runs = [];
    lines.forEach((line) => {
      runs.push({
        text: line,
        options: {
          bullet: { indent: 14 },
          breakLine: true,
        },
      });
    });
    slide.addText(runs, {
      x: x + 0.18,
      y: y + 0.48,
      w: w - 0.34,
      h: h - 0.62,
      fontFace: "PingFang SC",
      fontSize: 12.5,
      color: C.text,
      margin: 0,
      breakLine: false,
      valign: "top",
    });
  }
}

function addTag(slide, text, x, y, w, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.38,
    rectRadius: 0.08,
    line: { color: fill, transparency: 100 },
    fill: { color: fill },
  });
  slide.addText(text, {
    x,
    y: y + 0.07,
    w,
    h: 0.14,
    fontFace: "PingFang SC",
    fontSize: 11.5,
    bold: true,
    color: C.navy,
    align: "center",
    margin: 0,
  });
}

function addBullets(slide, x, y, w, h, items, fontSize = 17, color = C.text) {
  const runs = [];
  items.forEach((item) => {
    runs.push({
      text: item,
      options: {
        bullet: { indent: 18 },
        breakLine: true,
      },
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

function addArrow(slide, x, y, w = 0.32, h = 0.18, color = C.blue) {
  slide.addShape(pptx.ShapeType.chevron, {
    x,
    y,
    w,
    h,
    line: { color, transparency: 100 },
    fill: { color },
  });
}

function validateSlide(slide) {
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

  slide.addText("DataFlow 与 OpenSPG 结合的前置处理层方案", {
    x: 0.75,
    y: 1.2,
    w: 11.2,
    h: 0.75,
    fontFace: "PingFang SC",
    fontSize: 28,
    bold: true,
    color: C.navy,
    margin: 0,
  });
  slide.addText("老板汇报版 | 重点回答三件事：为什么要做、两套能力分别解决什么、结合后能带来什么价值", {
    x: 0.8,
    y: 2.02,
    w: 11.5,
    h: 0.4,
    fontFace: "PingFang SC",
    fontSize: 14,
    color: C.muted,
    margin: 0,
  });

  addTag(slide, "DataFlow：算子化数据治理", 0.82, 3.05, 2.45, C.paleBlue);
  addTag(slide, "OpenSPG/KAG：schema 驱动知识处理", 3.48, 3.05, 3.2, C.paleMint);
  addTag(slide, "新方案：统一前置处理层", 6.95, 3.05, 2.6, C.paleCyan);
  addTag(slide, "目标：服务统一产业大图", 9.8, 3.05, 2.55, C.paleGold);

  addCard(slide, {
    x: 0.82,
    y: 4.0,
    w: 11.65,
    h: 1.95,
    title: "一句话结论",
    fill: C.white,
    lines: [
      "DataFlow 更适合做原始数据治理和预处理，OpenSPG/KAG 更适合做 schema 驱动知识抽取与图谱构建。",
      "把两者结合起来，可以在不改变现有大图主架构的前提下，显著提升资讯、研报、常识数据的接入质量与处理效率。",
      "最终目标不是多一条处理脚本，而是建设一层可复用、可编排、可被 agent 调用的前置处理算子体系。",
    ],
  });
  validateSlide(slide);
}

function conclusion() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "结论先行", "为什么值得做");
  addCard(slide, {
    x: 0.72,
    y: 1.25,
    w: 3.95,
    h: 4.95,
    title: "为什么现在需要做",
    fill: C.paleBlue,
    lines: [
      "原始输入越来越复杂，既有结构化常识数据，也有大量资讯、PDF 研报和网页内容。",
      "目前前置治理能力分散在不同脚本和流程里，复用差、可解释性弱、扩展成本高。",
      "如果没有统一前置层，后续概念层、事件层和大图融合的质量会被输入质量直接限制。",
    ],
  });
  addCard(slide, {
    x: 4.84,
    y: 1.25,
    w: 3.95,
    h: 4.95,
    title: "我们准备怎么做",
    fill: C.paleMint,
    lines: [
      "用 DataFlow 的算子思想，把文档接入、清洗、去重、切块、预分类、seed 构造拆成标准步骤。",
      "用 OpenSPG/KAG 继续承担 schema 驱动抽取、知识映射和统一落图。",
      "在二者之间增加一层统一前置处理层，输出标准化 Document、Chunk、Seed 中间件。",
    ],
  });
  addCard(slide, {
    x: 8.96,
    y: 1.25,
    w: 3.65,
    h: 4.95,
    title: "能带来什么价值",
    fill: C.paleGold,
    lines: [
      "提升输入质量，减少后续抽取噪声和图谱污染。",
      "把一次性的处理逻辑沉淀为算子资产，便于多场景复用。",
      "为后续 agent 动态编排提供标准接口，降低新来源接入成本。",
    ],
  });
  validateSlide(slide);
}

function dataflowProcess() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "DataFlow：利用算子实现数据处理", "上游数据治理");
  addTitle(
    slide,
    "DataFlow 的核心思想：把数据处理拆成一串可复用算子",
    "每个算子只做一类动作，数据在算子之间按统一结构流转，最终形成可重用 pipeline。",
  );

  const steps = [
    ["接入", "文件/URL/PDF 进入统一输入结构"],
    ["清洗", "去 HTML 噪声、格式杂质、重复内容"],
    ["过滤", "剔除低质量文本、异常样本、无效内容"],
    ["切块", "把长文切成更适合后续处理的 chunk"],
    ["增强", "补充摘要、分类、质量评分等辅助信息"],
    ["输出", "形成高质量中间数据供下游继续使用"],
  ];
  let x = 0.55;
  steps.forEach((s, idx) => {
    addCard(slide, {
      x,
      y: 2.35,
      w: 1.92,
      h: 2.0,
      title: s[0],
      fill: idx % 2 === 0 ? C.white : C.paleBlue,
      lines: [s[1]],
    });
    if (idx < steps.length - 1) {
      addArrow(slide, x + 1.96, 3.13, 0.16, 0.16, C.blue);
    }
    x += 2.12;
  });

  addCard(slide, {
    x: 0.85,
    y: 5.05,
    w: 11.65,
    h: 1.35,
    title: "对我们的启发",
    fill: C.paleCyan,
    lines: [
      "DataFlow 的价值不在于某一个模型，而在于把“原始数据治理过程”标准化为算子；这正适合放在我们知识抽取之前。",
    ],
  });
  validateSlide(slide);
}

function openspgProcess() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "OpenSPG/KAG：实现知识处理的过程", "下游知识构建");
  addTitle(
    slide,
    "OpenSPG/KAG 的核心思想：以 schema 为边界，把数据转成可查询、可推理的图",
    "它们更擅长知识对象建模、实体/关系/事件抽取和统一落图，而不是原始文档治理。",
  );

  addCard(slide, {
    x: 0.72,
    y: 2.28,
    w: 2.25,
    h: 2.35,
    title: "Schema 定义",
    fill: C.paleMint,
    lines: [
      "先定义实体、关系、事件和概念边界。",
      "让抽取结果有统一语义归属。",
    ],
  });
  addArrow(slide, 3.02, 3.13, 0.16, 0.16);
  addCard(slide, {
    x: 3.35,
    y: 2.28,
    w: 2.25,
    h: 2.35,
    title: "KAG 处理",
    fill: C.white,
    lines: [
      "reader / splitter / extractor / mapping。",
      "把文档或结构化记录转成知识对象。",
    ],
  });
  addArrow(slide, 5.65, 3.13, 0.16, 0.16);
  addCard(slide, {
    x: 5.98,
    y: 2.28,
    w: 2.25,
    h: 2.35,
    title: "对齐与融合",
    fill: C.paleBlue,
    lines: [
      "按 schema 对属性、关系、概念和事件进行统一表达。",
      "避免图谱结构失控。",
    ],
  });
  addArrow(slide, 8.28, 3.13, 0.16, 0.16);
  addCard(slide, {
    x: 8.61,
    y: 2.28,
    w: 2.25,
    h: 2.35,
    title: "OpenSPG 落图",
    fill: C.white,
    lines: [
      "统一写入图谱，形成可查询、可追溯、可推理的大图。",
    ],
  });
  addArrow(slide, 10.91, 3.13, 0.16, 0.16);
  addCard(slide, {
    x: 11.24,
    y: 2.28,
    w: 1.45,
    h: 2.35,
    title: "应用",
    fill: C.paleGold,
    lines: [
      "问答",
      "分析",
      "推理",
    ],
  });

  addCard(slide, {
    x: 0.85,
    y: 5.0,
    w: 11.6,
    h: 1.45,
    title: "对我们的启发",
    fill: C.paleCyan,
    lines: [
      "OpenSPG/KAG 的强项在“知识表示和图谱构建”，但对研报/PDF/资讯等原始输入的治理还需要一层更轻、更灵活的前置处理体系来配合。",
    ],
  });
  validateSlide(slide);
}

function whyCombine() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "为什么要把 DataFlow 和 OpenSPG 结合起来", "能力互补");
  addTitle(slide, "一个偏上游数据治理，一个偏下游知识构建", "单独使用任何一方都不够完整，结合后才能形成稳定的数据到知识闭环。");

  addCard(slide, {
    x: 0.72,
    y: 2.55,
    w: 3.7,
    h: 3.95,
    title: "只用 DataFlow 的问题",
    fill: C.paleBlue,
    lines: [
      "能把原始数据整理得更干净，但缺少统一 schema 和图谱承载边界。",
      "更像高质量中间数据工厂，不是最终知识大图系统。",
      "难以直接支撑概念层、事件层和图推理。",
    ],
  });
  addCard(slide, {
    x: 4.82,
    y: 2.55,
    w: 3.7,
    h: 3.95,
    title: "只用 OpenSPG/KAG 的问题",
    fill: C.paleMint,
    lines: [
      "知识抽取和建图能力强，但原始输入治理成本高。",
      "PDF、网页、研报、资讯在进入抽取前仍需要大量预处理工作。",
      "没有统一算子层，难以支持后续 agent 灵活编排。",
    ],
  });
  addCard(slide, {
    x: 8.92,
    y: 2.55,
    w: 3.7,
    h: 3.95,
    title: "结合后的结果",
    fill: C.paleGold,
    lines: [
      "DataFlow 思想负责把原始输入变成高质量中间件。",
      "OpenSPG/KAG 负责把中间件变成可查询、可推理的知识图谱。",
      "中间层再统一输出给 IncCore 融合大图，形成闭环。",
    ],
  });
  validateSlide(slide);
}

function targetArchitecture() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "我们的结合思路与总体设计", "统一前置处理层");
  addTitle(slide, "在现有大图主架构之前增加一层“算子化前置处理层”", "这一层不替代现有 KAG / OpenSPG / IncCore，而是把原始数据整理成统一可消费的中间件。");

  addCard(slide, {
    x: 0.45,
    y: 2.45,
    w: 2.15,
    h: 2.1,
    title: "输入源",
    fill: C.white,
    lines: ["常识数据", "研报/PDF", "资讯/网页"],
  });
  addArrow(slide, 2.7, 2.95);

  addCard(slide, {
    x: 3.05,
    y: 2.45,
    w: 3.45,
    h: 2.9,
    title: "前置处理算子层",
    fill: C.paleBlue,
    lines: [
      "adapter",
      "normalize",
      "clean & dedup",
      "chunking & structuring",
      "enrichment",
      "seed builder",
    ],
  });
  addArrow(slide, 6.63, 2.95);

  addCard(slide, {
    x: 6.95,
    y: 2.45,
    w: 2.45,
    h: 2.9,
    title: "统一中间件",
    fill: C.paleMint,
    lines: [
      "Document",
      "Chunk",
      "EntitySeed",
      "EventSeed",
      "ConceptSeed",
    ],
  });
  addArrow(slide, 9.52, 3.23, 0.16, 0.14);
  addArrow(slide, 9.52, 4.16, 0.16, 0.14);

  addCard(slide, {
    x: 9.82,
    y: 2.45,
    w: 2.95,
    h: 1.35,
    title: "KAG / OpenSPG",
    fill: C.white,
    lines: ["schema 抽取", "知识映射", "统一落图"],
  });
  addCard(slide, {
    x: 9.82,
    y: 4.08,
    w: 2.95,
    h: 1.35,
    title: "IncCore Fusion",
    fill: C.white,
    lines: ["实体融合", "概念挂载", "事件归一"],
  });

  addCard(slide, {
    x: 0.72,
    y: 5.72,
    w: 12.0,
    h: 1.15,
    title: "设计要点",
    fill: C.paleCyan,
    lines: [
      "前置层负责把“原始数据”变成“高质量中间件”；知识抽取和统一大图仍由现有 OpenSPG/KAG/IncCore 主链承接。",
    ],
  });
  validateSlide(slide);
}

function threeDataLanes() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "三类数据怎么接入这套新方案", "面向现有业务");
  addTitle(slide, "前置层不求一套流程跑天下，而是按数据类型走不同算子链", "这样既能复用，又不会破坏现有主链路。");

  addCard(slide, {
    x: 0.55,
    y: 2.25,
    w: 4.0,
    h: 4.25,
    title: "常识数据",
    fill: C.paleBlue,
    lines: [
      "更偏结构化：筛选、标准化、别名归一、结构化 seed 构造。",
      "重点价值：把现有事实库处理逻辑沉淀为标准算子。",
      "下游进入 IncCore fusion 或 KAG structured mapping。",
    ],
  });
  addCard(slide, {
    x: 4.67,
    y: 2.25,
    w: 4.0,
    h: 4.25,
    title: "研报数据",
    fill: C.paleMint,
    lines: [
      "更偏文档型：PDF 转 Markdown、清洗、大纲结构化、表格结构化、切块。",
      "重点价值：先把复杂文档整理干净，再交给 KAG 做 schema 抽取。",
      "这是最适合引入 DataFlow 思想的一类输入。",
    ],
  });
  addCard(slide, {
    x: 8.79,
    y: 2.25,
    w: 4.0,
    h: 4.25,
    title: "资讯数据",
    fill: C.paleGold,
    lines: [
      "更偏事件型：去重、规范化、质量过滤、chunk 和 event seed 前移。",
      "重点价值：把噪声留在前置层，不把低质量事件直接送入大图。",
      "下游仍由 IncCore 的事件解析和融合主线接管。",
    ],
  });
  validateSlide(slide);
}

function businessValue() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "这套方案能带来什么价值", "老板最关心");
  addTitle(slide, "价值不只是“多一层处理”，而是把输入治理能力沉淀成长期资产", "");

  addCard(slide, {
    x: 0.72,
    y: 1.9,
    w: 2.9,
    h: 3.55,
    title: "质量更稳",
    fill: C.paleBlue,
    lines: [
      "前置去重、清洗、过滤后，再进入抽取链，能显著降低图谱噪声和错误关系。",
    ],
  });
  addCard(slide, {
    x: 3.88,
    y: 1.9,
    w: 2.9,
    h: 3.55,
    title: "接入更快",
    fill: C.paleMint,
    lines: [
      "新来源不必每次重新写一条大脚本，只需组合已有算子或新增少量业务算子。",
    ],
  });
  addCard(slide, {
    x: 7.04,
    y: 1.9,
    w: 2.9,
    h: 3.55,
    title: "能力可复用",
    fill: C.paleCyan,
    lines: [
      "算子可以跨资讯、研报、常识三类数据复用，处理经验能持续沉淀。",
    ],
  });
  addCard(slide, {
    x: 10.2,
    y: 1.9,
    w: 2.4,
    h: 3.55,
    title: "面向 Agent",
    fill: C.paleGold,
    lines: [
      "清晰的算子定义和运行统计，为后续 agent 自动编排打基础。",
    ],
  });

  addCard(slide, {
    x: 0.72,
    y: 5.75,
    w: 11.9,
    h: 0.95,
    title: "一句话总结",
    fill: C.white,
    lines: [
      "这套方案把“临时处理能力”升级成“标准算子能力”，把“单次接入”升级成“长期可扩展的数据处理底座”。",
    ],
  });
  validateSlide(slide);
}

function roadmap() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTopBar(slide, "建议落地路径", "先做能见效的部分");
  addTitle(slide, "先把前置层做成最小可运行骨架，再逐步增强算子与 agent 化能力", "");

  addCard(slide, {
    x: 0.72,
    y: 2.0,
    w: 3.75,
    h: 3.95,
    title: "Phase 1：先打通",
    fill: C.paleBlue,
    lines: [
      "建立统一 DTO 和算子注册机制。",
      "优先打通资讯、研报、常识三类 adapter。",
      "先实现去重、清洗、切块、seed 构造的最小链路。",
    ],
  });
  addCard(slide, {
    x: 4.8,
    y: 2.0,
    w: 3.75,
    h: 3.95,
    title: "Phase 2：补业务算子",
    fill: C.paleMint,
    lines: [
      "增加企业分类、行业概念预绑定、事件影响预分类。",
      "增强研报的大纲、表格结构化处理。",
      "形成更贴合产业场景的前置能力库。",
    ],
  });
  addCard(slide, {
    x: 8.88,
    y: 2.0,
    w: 3.75,
    h: 3.95,
    title: "Phase 3：接 Agent",
    fill: C.paleGold,
    lines: [
      "把算子目录、参数、路由条件、统计信息暴露给 agent。",
      "支持 agent 按输入类型动态拼接前置 pipeline。",
      "最终形成可持续扩展的数据到知识处理底座。",
    ],
  });

  slide.addText("最终目标：让“原始数据进来”这件事更标准、更快、更稳，并直接服务统一产业大图。", {
    x: 0.82,
    y: 6.45,
    w: 11.8,
    h: 0.3,
    fontFace: "PingFang SC",
    fontSize: 17,
    bold: true,
    color: C.navy,
    margin: 0,
  });
  validateSlide(slide);
}

async function main() {
  cover();
  conclusion();
  dataflowProcess();
  openspgProcess();
  whyCombine();
  targetArchitecture();
  threeDataLanes();
  businessValue();
  roadmap();
  await pptx.writeFile(OUT);
  console.log(`saved:${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
