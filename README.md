# 短剧制作 Agent

[English](#english) | 简体中文

把短剧创意、梗概或完整剧本，转成可执行的前期制作包：剧本诊断、视觉风格、人物与场景一致性、场景拆解、逐镜分镜、声音与剪辑建议、制作风险和替代方案。

> 当前状态：内部验证版本。已验证 Skill 结构、相对链接、配置和压缩包完整性；尚未完成真实创作者测试，不宣称业务效果或平台过审能力。

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
- **质量闸门**：用 10 项硬性检查和 9 类验收场景识别不可交付结果。
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
质量自检与待确认项
```

## 安装

要求：支持读取 `SKILL.md` 的 Codex 环境。

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

## 示例

- [示例输入：原创悬疑短剧](examples/01-demo-input.md)
- [风格方案：等待用户选择](examples/02-demo-style-options.md)
- [风格锁定后的逐镜分镜](examples/03-demo-shot-list.md)

示例是原创虚构内容，仅用于展示交付颗粒度。

## 仓库结构

```text
.
├── README.md
├── .gitignore
├── skill/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── references/
│   │   ├── intake-and-diagnosis.md
│   │   ├── visual-direction.md
│   │   ├── storyboard-spec.md
│   │   ├── production-handoff.md
│   │   ├── quality-gates.md
│   │   └── research-and-rights.md
│   └── assets/
│       ├── production-bible-template.md
│       ├── style-option-template.md
│       └── knowledge-index-template.md
└── examples/
    ├── 01-demo-input.md
    ├── 02-demo-style-options.md
    └── 03-demo-shot-list.md
```

## 质量模型

项目使用两层质量判断：

1. **硬性闸门**：输入忠实、叙事完整、风格关闭、镜头可执行、空间与物料连续、技术规格、权利状态、风险透明和来源可追溯。
2. **质量评分**：忠实度、叙事清晰度、视觉具体度、连续性、可行性、风格统一性、声音剪辑、合规与可用性，每项 1–5 分。

只要任一硬性检查失败，就不能用总分掩盖，也不能标为“可执行交付”。

## 当前边界

- 不直接完成实拍、表演、配音、音乐授权、平台过审或成片渲染。
- 不能保证播放量、涨粉、收益或平台审核结果。
- 平台规则、法律、预算和档期会变化，运行时必须核验。
- AI 生成的手部、口型、文字、反射和复杂动作仍需要单独测试。
- 尚未用真实创作者完成可用性验证，Roadmap 中的指标不能当作已有结果。

## Roadmap

- 使用 2–3 个原创剧本完成端到端演示；
- 记录制作包整理耗时、字段完整率、连续性问题数和返工次数；
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

An independent Codex Skill that turns a short-drama idea or script into a decision-closed pre-production package: script diagnosis, visual direction, character and location consistency, scene breakdown, executable shot list, sound/edit handoff, production risks, and alternatives.

It intentionally stops for user selection when multiple materially different visual directions are viable. The project is an internal validation build, not an official OpenAI product, and does not claim user outcomes, approval, or production completion that has not been verified.
