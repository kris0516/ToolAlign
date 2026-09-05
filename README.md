# ToolAlign

**Reliable tool-use post-training and evaluation on Apple Silicon.**

ToolAlign 是一个以 Apple Silicon 为主要实验环境的开源研究工程项目：把小型语言模型的工具选择、参数生成、无需工具判断与有限故障恢复，做成可复现、可审计的训练—评测—推理闭环。

> **当前状态：P00 基础实现，待独立审查合并。** 已有 CPU 可安装包、版本化契约、模块接口、跨 worktree GPU 锁与基础测试；没有训练好的模型、已执行的 benchmark 或已经上线的推理服务。十天是目标工作安排，不是完成承诺。结果栏在实测前必须保持 `NOT_RUN`。

## CPU 基础检查

```bash
uv sync --locked --python 3.14
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv run --locked toolalign validate tests/fixtures/contracts/example.json
```

仅安装 CPU 基础依赖，不加载模型。离线运行需要事先安装锁定依赖。契约和文件所有权见 [P00 契约说明](docs/12_CONTRACTS_V1.md)；锁定依赖见 `uv.lock`。历史 `MANIFEST.sha256` 仅对应原始规划包，当前发布依据为 Git commit 与阶段证据。

## 研究问题

在固定数据、计算预算和评测协议下，`Qwen3-1.7B` 经量化 LoRA SFT，再经基于执行反馈的 DPO，能否提高工具调用的**语义任务成功率**？增加重试、量化和 prefix cache 后，准确性、延迟、内存的变化能否被分别归因？

`Qwen3-0.6B` 用于兼容性冒烟和小容量对照。这里的 **baseline / 原始 checkpoint** 不是“未经指令训练的 pretrained base model”。准确的模型身份、revision 与模板必须记录。

## 从哪里开始

| 阅读者 | 入口 |
|---|---|
| 项目负责人 kris | [总计划](docs/00_MASTER_PLAN.md)、[十天任务表](coordination/BOARD.md) |
| Supervisor Codex 独立对话 | **[SUPERVISOR_START_HERE.md](SUPERVISOR_START_HERE.md)** |
| 所有独立实现/审查对话 | [AGENTS.md](AGENTS.md)、[协作协议](coordination/PROTOCOL.md) |
| 训练负责人 | [训练规格](docs/03_TRAINING_SPEC.md)、[Mac 资源方案](docs/05_APPLE_SILICON.md) |
| 评测负责人 | [数据治理](docs/02_DATA_GOVERNANCE.md)、[评测规格](docs/04_EVALUATION_SPEC.md) |
| 部署负责人 | [分阶段部署路线](docs/06_DEPLOYMENT_ROADMAP.md) |
| 接收文档包后创建 GitHub 仓库 | [发布运行手册](docs/11_REPOSITORY_BOOTSTRAP.md) |

## 首版边界

核心：数据审计与分组切分；可执行工具环境；原始模型/SFT/DPO 对照；可核验的错误分析；Mac 资源实测；受限本地推理接口；一次受控 prefix-cache 实验。

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

当前公开仓库为 `kris0516/ToolAlign`。规划基线已通过 GitHub 写入并读回验证；Supervisor 接手后仍需在 [项目状态](coordination/PROJECT_STATUS.md) 登记领取信息与后续实现 commit。

原创代码和文档采用 [MIT](LICENSE)。模型、数据和第三方依赖各自保留原许可，见 [第三方来源与发布边界](THIRD_PARTY_NOTICES.md)。不复制 LiDARFoodAgent 私有源码、真实用户数据或任何云端凭据。

[参考来源](docs/09_SOURCES.md) · [风险登记](docs/07_RISKS.md) · [发布验收](docs/08_ACCEPTANCE.md) · [个人学习与答辩](docs/10_LEARNING_DEFENSE.md)
