# ToolAlign

**Reliable small-model tool-use post-training and evaluation.**

ToolAlign 是一个使用 Colab GPU 训练、在 Mac 开发与控制的开源研究工程项目：把小型语言模型的工具选择、参数生成、无需工具判断与有限故障恢复，做成可复现、可审计的训练—评测—推理闭环。

> **当前状态（2026-10-26）：CUDA 容量与完整恢复已验收；0.6B 冒烟和 1.7B 一轮正式 SFT 已完成，并通过 R1/Q1 独立终验。** 各自完整验证 CE 从 0.739884/1.145230 降至 0.041494/0.024438，全部产物已回收，Colab 已停止，见[结果与曲线](reports/S1_P04_CUDA_G3_SFT.md)。DPO 和模型语义评测保持 `NOT_RUN`。接续入口为 **[toolalign.md](toolalign.md)**，阶段证据见[真实状态](coordination/PROJECT_STATUS.md)。

## CPU 基础检查

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv run --locked toolalign validate tests/fixtures/contracts/example.json
uv run --locked python -m toolalign.data --help
uv run --locked python -m toolalign.tools --help
uv run --locked python -m toolalign.training.compatibility --help
```

仅安装 CPU 基础依赖，不加载模型。离线运行需要事先安装锁定依赖。契约和文件所有权见 [P00 契约说明](docs/12_CONTRACTS_V1.md)；锁定依赖见 `uv.lock`。历史 `MANIFEST.sha256` 仅对应原始规划包，当前发布依据为 Git commit 与阶段证据。

数据流程的固定来源、转换政策、复现命令和真实 tokenizer 依赖见 [P02 使用说明](reports/data/README.md)。数据与人审制品仅保留本地；历史工具调用是监督数据，未绑定可执行工具。技术审查通过不表示数据语义或模型训练已验收。

## 研究问题

在固定数据、计算预算和评测协议下，`Qwen3-1.7B` 经 LoRA SFT，再经基于执行反馈的 DPO，能否提高工具调用的**语义任务成功率**？增加重试、量化和 prefix cache 后，准确性、延迟、内存的变化能否被分别归因？

`Qwen3-0.6B` 用于兼容性冒烟和小容量对照。这里的 **baseline / 原始 checkpoint** 不是“未经指令训练的 pretrained base model”。准确的模型身份、revision 与模板必须记录。

## 从哪里开始

| 阅读者 | 入口 |
|---|---|
| 项目负责人 kris | [总计划](docs/00_MASTER_PLAN.md)、[十天任务表](coordination/BOARD.md) |
| Supervisor Codex 独立对话 | **[toolalign.md](toolalign.md)** |
| 所有独立实现/审查对话 | [AGENTS.md](AGENTS.md)、[协作协议](coordination/PROTOCOL.md) |
| 训练负责人 | [训练规格](docs/03_TRAINING_SPEC.md)、[Colab 工作流与显存预算](docs/16_COLAB_WORKFLOW.md) |
| 评测负责人 | [数据治理](docs/02_DATA_GOVERNANCE.md)、[评测规格](docs/04_EVALUATION_SPEC.md) |
| 部署负责人 | [分阶段部署路线](docs/06_DEPLOYMENT_ROADMAP.md) |
| 接收文档包后创建 GitHub 仓库 | [发布运行手册](docs/11_REPOSITORY_BOOTSTRAP.md) |

## 首版边界

核心：数据审计与分组切分；可执行工具环境；原始模型/SFT/DPO 对照；可核验的错误分析；Colab GPU 资源实测；受限推理接口；一次受控 prefix-cache 实验。

不在十天核心范围：全量 BFCL V4 总榜复现、多机多卡、PPO/GRPO、无人监督自我改权重、五个自治 Agent、商业多租户服务、公开公网推理、完整前端。Speculative decoding 与高级 batching 是后续候选，不承诺提速。

## 协作方式

一个 Supervisor + 多个**独立 Codex 对话**；每个实现对话拥有独立 branch/worktree。通过任务包、Git 提交和交接文档交换状态。**不使用 sub-agent、Agents SDK 编排、`spawn_agent` 或嵌套代理。** 当前环境没有对话创建能力时，由 kris 手动创建独立对话并粘贴已准备的分发词，不能冒称已经派发。

## 结果登记

| 对照项 | 语义任务成功率 | 原始格式正确率 | 恢复成功率 | P95 端到端延迟 | 内存 |
|---|---|---|---|---|---|
| 1.7B 原始 checkpoint | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| 1.7B + SFT | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| 1.7B + SFT + DPO | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

官方 BFCL 分类成绩与自建执行环境结果必须分表；AST 匹配不能冒充真实外部 API 执行。完整 benchmark 与子集不能同名报告。

## 开源与部署状态

当前公开仓库为 `kris0516/ToolAlign`。S1 已接班并按分组目标继续推进；[项目状态](coordination/PROJECT_STATUS.md)记录实际提交、独立审查、集成与尚未满足的验收门。

原创代码和文档采用 [MIT](LICENSE)。模型、数据和第三方依赖各自保留原许可，见 [第三方来源与发布边界](THIRD_PARTY_NOTICES.md)。不复制 LiDARFoodAgent 私有源码、真实用户数据或任何云端凭据。

[参考来源](docs/09_SOURCES.md) · [风险登记](docs/07_RISKS.md) · [发布验收](docs/08_ACCEPTANCE.md) · [个人学习与答辩](docs/10_LEARNING_DEFENSE.md)
