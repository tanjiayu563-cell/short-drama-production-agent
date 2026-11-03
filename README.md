# 短剧制作 Agent

[English](#english) | 简体中文

把短剧创意、梗概、完整剧本或小说选区，转成可执行的前期制作包：剧本诊断、视觉风格、人物与场景一致性、逐镜分镜、MiniMax H3/Seedance 等模型的视频提示词、生成视频质检和版本迭代。

> 当前状态：内部验证版本。已验证 Skill 结构、相对链接、配置和质检脚本语法；尚未完成真实创作者和真实视频样本的规模化验证，不宣称业务效果、模型成功率或平台过审能力。

## 它解决什么问题

短剧前期制作常见的问题不是“没有分镜”，而是分镜无法直接执行：

- 风格停留在“高级、电影感、唯美”等形容词；
- 镜头只有景别和台词，缺少机位、动作、声音和连续性；
- 人物外观、服装、道具在镜头之间无故变化；
- 多个视觉方向都可行，但没有明确决策点，导致反复返工；
- 平台规则、版权、预算和危险拍摄风险到后期才暴露。

本项目把这些环节组织成一套可审计、可复用的 Agent 工作流。

## 核心能力

- **剧本诊断**：检查前提、因果、人物动机、冲突升级、信息控制、节奏和集尾钩子。
- **风格闸门**：存在多个实质不同的风格时，先给 2–3 个完整方案并询问用户，不静默替用户决定。
- **Style Lock**：锁定色彩、饱和度、对比度、灯光、镜头、构图、剪辑、声音和人物一致性锚点。
- **视觉制作圣经**：建立人物、场景、服化道和关键道具卡。
- **逐镜分镜**：每镜包含叙事功能、景别、机位、焦段、运动、构图、动作、台词、声音、转场、连续性和备选方案。
- **视频提示词包**：支持 T2V、I2V、R2V、V2V、视频延长和定向编辑；先核验模型能力，再生成模型适配提示词。
- **Seedance 适配**：包含 Seedance 2.0/2.5 的已核实能力、时间分段、多模态参考和长视频延长写法。
- **MiniMax H3 适配**：支持 T2V、图片/首尾帧、图片/视频/音频参考、原生声音、4–15 秒输出和角色/场景一致性锁定。
- **小说选区工作台**：导入 `.txt` / `.md` / `.epub` 小说文本，鼠标选中一个区域，自动匹配人物/场景/道具资产，生成 H3 单镜提示词。
- **画面/旁白判断**：逐节拍判断哪些信息应直接可见、哪些用对白、画外声、文字插入，只有无法视觉化时才用短旁白。
- **人物关系图**：记录亲属、权力、信任、隐瞒、空间阻隔和场景内变化，用站位、距离、视线和道具呈现关系。
- **镜头去重复**：避免连续三个节拍同一景别，不把每句台词拍成同一种近景，并为每个镜头要求明确叙事功能。
- **生成视频质检**：提取元数据、抽样帧、联系表和技术事件，再由 Agent 对照原镜头任务做语义质检。
- **迭代闭环**：输出带时间点的问题、根因、P0/P1/P2 分级、下一版完整提示词和单变量回归记录。
- **质量闸门**：用 10 项硬性检查和 18 类验收场景识别不可交付结果。
- **来源与权利索引**：只保存链接、原创摘要和授权状态，不批量复制受版权保护的教程或素材。
- **多制作方式**：支持实拍、AI 生成、动画及混合制作，并明确各自的高风险镜头。

## 工作流

```text
创意 / 梗概 / 剧本
        ↓
剧本诊断与信息补全
        ↓
2–3 个视觉风格方案
        ↓
用户选择 / 明确授权
        ↓
Style Lock
        ↓
人物、场景、道具一致性卡
        ↓
逐镜分镜与制作风险
        ↓
小说选区 + 人物/背景资产锁定
        ↓
模型档案 + 视频生成提示词
        ↓
生成视频 → 技术检查 + 语义质检
        ↓
问题定位 → 单变量修改 → 下一版
        ↓
质量自检与待确认项
```

## 安装

要求：支持读取 `SKILL.md` 的 Codex 环境。视频质检脚本建议安装 Python 3.9+ 和 `ffmpeg`；`ffprobe` 可选，缺少时会从 FFmpeg 输入摘要读取基础元数据。macOS 在缺少 FFmpeg 时可尝试用 `xcrun clang` 和 AVFoundation 提取元数据与关键帧；黑帧、冻结帧和场景切点检测仍需要 FFmpeg。

```bash
git clone <your-repo-url> short-drama-production-agent
mkdir -p "$HOME/.codex/skills/short-drama-production"
cp -R short-drama-production-agent/skill/. "$HOME/.codex/skills/short-drama-production/"
```

重新打开 Codex 或新建任务后，可通过 `$short-drama-production` 显式调用。`skill/agents/openai.yaml` 已开启自动匹配调用。

## 使用

```text
使用 $short-drama-production，把我的以下短剧剧本制作成完整制作包。

平台/画幅：
单集时长/集数：
制作方式：实拍 / AI / 动画 / 混合
目标受众：
必须保留：
不能出现：
预算或周期约束：

剧本：
……
```

如果暂时没有这些参数，至少提供一句创意或一段剧本。Agent 应明确假设，不得把推断伪装成用户设定。

生成视频质检：

```text
使用 $short-drama-production 分析这段生成视频。

原镜头任务：
模型与版本：
原提示词：
目标时长/画幅：
参考素材：
上一版视频（可选）：
视频文件：
```

Agent 应先提取技术证据和关键帧，再判断是否达标；没有看到实际视频或关键帧时，不得声称完成质检。

模型名称或版本不明确时，应先核验。例如“Muse”存在多个不相关产品命名，当前检索到的 Meta Muse 是个人 AI Agent，不是已核实的视频生成模型。必须拿到具体产品链接或版本后才能写专属提示词。

## 小说选区工作台

打开 [`workbench/index.html`](workbench/index.html)，或使用任务输出中的 `minimax-h3-storyboard-workbench.html`。

支持：

- 导入或粘贴 `.txt` / `.md` / `.epub` 小说文本；EPUB 在浏览器本地解析；
- 用鼠标选中任意区域，捕获原文选区；
- 建立人物、场景和道具资产库；
- 每个资产可导入图片，或只写文字描述和一致性锁；
- 根据选区自动匹配名称/别名；
- 自动拆解为最多 6 个叙事节拍，标注画面、对白、旁白、声音和关系调度；
- 自动给出不同景别/机位/运镜建议，并检查连续重复；
- 生成 MiniMax H3 单镜提示词；
- 提示 7000 字符上限、9 张图片上限和总参考文件上限；
- 导出项目 JSON、提示词 Markdown 和版本记录。

当前工作台是本地单文件应用，不上传文本或图片到第三方；EPUB 在浏览器本地解压和提取正文。复杂 `.docx` 请先转换为文本或直接粘贴正文。带 DRM 的 EPUB 暂不支持。

## 示例

- [示例输入：原创悬疑短剧](examples/01-demo-input.md)
- [风格方案：等待用户选择](examples/02-demo-style-options.md)
- [风格锁定后的逐镜分镜](examples/03-demo-shot-list.md)
- [Seedance 2.5 提示词示例](examples/04-demo-seedance-prompt.md)
- [MiniMax H3 选区提示词示例](examples/05-demo-minimax-h3-prompt.md)

示例是原创虚构内容，仅用于展示交付颗粒度。

## 仓库结构

```text
.
├── README.md
├── CHANGELOG.md
├── .gitignore
├── skill/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── references/
│   │   ├── intake-and-diagnosis.md
│   │   ├── visual-direction.md
│   │   ├── storyboard-spec.md
│   │   ├── video-model-prompting.md
│   │   ├── seedance-prompting.md
│   │   ├── minimax-h3-prompting.md
│   │   ├── adaptation-and-shot-variety.md
│   │   ├── generated-video-qc.md
│   │   ├── production-handoff.md
│   │   ├── quality-gates.md
│   │   └── research-and-rights.md
│   ├── assets/
│   │   ├── production-bible-template.md
│   │   ├── video-prompt-pack-template.md
│   │   ├── minimax-h3-shot-template.md
│   │   ├── scene-adaptation-template.md
│   │   ├── video-qc-report-template.md
│   │   ├── iteration-log-template.md
│   │   ├── style-option-template.md
│   │   └── knowledge-index-template.md
│   └── scripts/
│       ├── video_qc.py
│       └── video_qc_macos.m
├── workbench/
│   ├── README.md
│   └── index.html
└── examples/
    ├── 01-demo-input.md
    ├── 02-demo-style-options.md
    ├── 03-demo-shot-list.md
    ├── 04-demo-seedance-prompt.md
    └── 05-demo-minimax-h3-prompt.md
```

## 质量模型

项目使用两层质量判断：

1. **硬性闸门**：输入忠实、叙事完整、风格关闭、镜头可执行、空间与物料连续、技术规格、权利状态、风险透明和来源可追溯。
2. **质量评分**：忠实度、叙事清晰度、视觉具体度、连续性、可行性、风格统一性、声音剪辑、合规与可用性，每项 1–5 分。

只要任一硬性检查失败，就不能用总分掩盖，也不能标为“可执行交付”。

生成视频还需单独通过：

- P0 必须为 0；
- 提示词遵循、身份一致性、动作与物理、时间稳定性、连续性等关键维度原则上不低于 4/5；
- P1 必须有明确的后期修补或重生成计划；
- 脚本运行成功不等于视频通过质检。

## 当前边界

- 不直接完成实拍、表演、配音、音乐授权、平台过审或成片渲染。
- 不能保证播放量、涨粉、收益或平台审核结果。
- 平台规则、法律、预算和档期会变化，运行时必须核验。
- MiniMax H3、Seedance 等模型的 UI、API、地区能力和限制会变化，使用前必须重新核验。
- 选区工作台支持 `.txt` / `.md` / 无 DRM `.epub`，不直接解析复杂 `.docx` 排版、表格或批注。
- AI 生成的手部、口型、文字、反射和复杂动作仍需要单独测试。
- 模型官方页面、产品 UI 和 API 能力可能不同，使用前必须核验版本和地区。
- “Muse”等名称存在歧义；未确认具体产品前，不提供虚构的模型专属提示词语法。
- 视频质检脚本负责技术证据；语义判断仍需 Agent 或人工查看画面。
- 尚未用真实创作者和真实生成视频完成规模化可用性验证，Roadmap 中的指标不能当作已有结果。

## Roadmap

- 使用 2–3 个原创剧本和真实生成视频完成端到端演示；
- 记录生成通过率、平均迭代次数、连续性问题数和后期修补工时；
- 添加前后对比截图和演示视频；
- 邀请短剧创作者或制作人员做 1–5 分可用性评价；
- 根据真实失败案例迭代风格闸门和镜头卡；
- 为 AI、动画等不同制作方式增加独立示例。

## 兼容性与声明

本项目是独立开发的 Codex Skill，不代表 OpenAI 官方产品。Codex 及相关名称归其权利人所有。

## License

尚未选择开源许可证。在没有添加 `LICENSE` 文件前，默认保留所有权利，其他人可以查看但不能据此复制、修改或再分发。

发布前若希望允许复用，应明确选择：

- 代码/配置：MIT 或 Apache-2.0；
- 文档/模板：CC BY 4.0、CC BY-NC 4.0 或自定义条款。

---

## English

An independent Codex Skill and local workbench that turns a short-drama idea, script, or selected novel passage into a decision-closed pre-production package: script diagnosis, visual direction, character and location consistency, executable shot list, MiniMax H3/Seedance-aware video prompts, generated-video QC, and a versioned refinement loop.

It intentionally stops for user selection when multiple materially different visual directions are viable. Video-model capabilities are verified before model-specific prompting. The project is an internal validation build, not an official OpenAI product, and does not claim user outcomes, model success rates, approval, or production completion that has not been verified.
