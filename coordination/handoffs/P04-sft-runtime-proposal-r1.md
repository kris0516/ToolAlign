# P04-SFT-RUNTIME-PROPOSAL r1 — T1 → S0

状态：`READY_FOR_REVIEW`；交付的是 **PROPOSED_NOT_AUTHORIZED** 方案及静态自查，不是生产实现或真实模型验收。

T1，`gpt-6-astra / max`，原独立 Codex 任务和隔离 worktree。任务/主机真实标识、绝对工作路径和最终完整 candidate SHA、parents/tree 通过本机记录与原生交接提供；不在公共文件写入私有任务身份。

- code base：`d3e56f68ebd67cc576d912b6f06636682b4170ab`，PR14 已验收 main。
- 完整授权：`8929cbbef0b24f9a4053adfe778bb4ef76147293`；新分支 `codex/p04-sft-runtime-proposal-r1`。
- 读取契约：`plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0025`；模型格式 `toolalign.action-json.qwen3-message-roles.v1`。
- 固定 input manifest：`eb5f25bd164c1394c0d82350a1f1d0ccc09ddb1306dac3977403b695d7f1ac02`，10 份副本 / 166,598 bytes；完整授权文件 18 份。
- 原 native-toy 分支仍为 `f7326d1823c4cf132ae44525f4755c96c88ec159`；旧 P04-CPU/P01 refs 与原私有封存保持。没有 pull/reset/rebase 旧分支。

本次仅新增以下三份公共文件；没有生产代码、测试、配置、契约、依赖、构建、CI 或 S0 协调文件改动：

| 文件 | 本轮内容与 SHA-256 |
|---|---|
| [运行接口方案](../../reports/experiments/P04_SFT_RUNTIME_PROPOSAL.md) | 32,914 bytes；`a50babe5b96526e98ee8b4472c008d4230356c4b5757c7b19f0cdd0d210356a2` |
| [结构化对应件](../../reports/experiments/P04_SFT_RUNTIME_PROPOSAL.json) | 66,167 bytes；`bc57cd61092f32eb6de489372fca910da0f4df8a31a62886f24a479a70c7bbc8`；不是可执行训练配置 |
| 本交接单 | 最终 hash 随 candidate 原生交接和本机 final seal 提供，避免自引用 |

方案明确了新 v3 只读消费/13 例数组绑定与旧 CPU 入口的边界、固定原始 Qwen revision/LoRA/Adam 默认、原生公开 train/evaluate 接口、实际状态和 checkpoint 身份、有限容量候选、原始/SFT 同格式生成及 P03 注册工具边界。没有读取 D1/Q1 变化中的结果或重新裁定质量语义。

投影 smoke `1583 = 197×8 + 7 → 198 updates`，formal `5938 = 742×8 + 2 → 743 updates`，各分四次原生 train 调用。三次完整 post-update validation 分别绑定实际 step `66/132/198` 和 `250/500/743`；另有原生强制保存的尾段前状态。模型/optimizer/RNG 连续，compiled closure、局部 it 与 iterator 每次新建；验证恢复模式，不能把末次内置 validation、yielded rank 或文件名当成已完成更新证据。

0.6B 容量候选是 15 个唯一 train + 8 validation，8+7 后对固定 8 例重复 8 遍，累计 79 微步 / 10 更新；建议最多 1 个 GPU child、0 重试、900 秒、24GiB MLX / 30GiB RSS、512MiB 新制品。选例 ID、数组、配置和输出 hash 均 PENDING，全部额度尚未授权。原生 0.6B 1536 与 1.7B 2048 的新路径证据、真实保存重载、P03 冷启动/停止条件等保持 NOT_RUN。

源码静态核对覆盖 35 份文件 / 80 个准确行区间，含四份从原有环境只读取得的 MLX 源码。全文及区间 hash 在结构化件 `source_evidence`；repo 文件绑定 d3 基线。特别记录 Adam 默认 `bias_correction=False`、LoRA FP32 / 底座 BF16、目录缺失触发下载和 config 自定义模型代码的入口、非严格 adapter loader、每次 train 的 wired setter 以及生成恢复 setter。方案提议沿用已审抑制守卫；其合成返回 0 不是实测旧 wired 上限。本轮没有执行 device_info 或任何 setter。

静态验证使用现有 `.venv` 的 Python 3.14 标准库和 Ruff。原 recorder 为 `reports/experiments/P04_SFT_CPU_COMMAND.py`；每条实测命令分别保存真实 argv、source head/tree、前后公共文件 hash、时间、退出码和 stdout/stderr。私有辅助脚本只做文档构造、AST/JSON、hash、算术和所有权核对，没有框架或生产模块导入。

| 已执行核对 | 退出码 / 证据 |
|---|---|
| `intake.py`，切换前旧资料与固定输入 | 0；stdout `e0e7d0aa7a19c5d32f17d329b95bde0a39e05a0bf2ea8a67941b9dbd719b6648` |
| `collect_sources.py` 最终来源区间核对 r3 | 0；stdout `2e5d634d4846502c3691552cd2092cc7c643b1633e474abc333d97969745069e` |
| `audit_proposal.py --output proposal-audit-r2.json` | 0；stdout `115d877f1d47f4103b868ad3a74b45e239b55e2a5bcda8ccb6fe798b0d629a73`；两份方案 hash 与本交接表相同 |
| Ruff，仅当时三份自有私有辅助脚本 | 0；stdout `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |

上述 r2 核对确认 d3 全部 553 份原文件不变、仅两份当时新增方案文件，5,416 个旧证据路径和 197 个链接身份通过；其中旧 checkout 的 408 个公共路径按原 f732 Git 字节绑定，18 个当前内容差异来自已授权切换至 d3，不能称为物理内容未变。原私有证据和旧 refs 则实际复核不变。

包含本交接单的最终 `--require-handoff` 核对、公开扫描、暂存 diff、提交/普通推送/远端一致性回执，均继续在同一私有 scope 独立保存，最终 seal 的实际路径/hash 随完整 candidate 原生交接。最终状态以这些回执为准，不把本交接成文前的检查称为在最终 commit 上重跑。

保留的辅助失败有两次：`source-identities-r1` 因引用区间超出 `format.py` 实际末行而退出 1，stderr `b88bbc367770cb8d6dcc92c432fe423b0fe2427be40eabdcc8a58a91de299590`；`proposal-audit-r1` 因辅助检查误期望 16 个执行计数字段、实际定义为 14 个而退出 1，stderr `f6f8a24ddb75aeb3b13673f4f92dc7be9f85722e4b7f90468bdec6ccd25674fa`。原日志和失败版 helper 保留，分别修正行区间及显式字段集合后在新输出通过；没有删去或重命名失败为 PASS。另有探索性路径/metadata 查找失败单独记录，未产生模型或数据执行。

本轮新增环境/依赖/下载/数据构建/分词/框架导入/模型加载/GPU/optimizer updates/生成/业务 API/浏览器/费用全部为 **0**；pytest/build/install 未运行，符合本范围。Git 普通 candidate 推送与已授权原生协调另行计入回执，不算模型或业务网络调用。私有新增上限 128MiB，实占在最终 seal 核对。

请 S0 复核四段步数和 rank 完整性、验证状态与保存重载身份、wired 限制抑制与观测区分、容量预算，以及 CPU/容量/smoke/formal/P05 的分离门槛，再冻结下一实施包。当前没有本方案的独立 R1 结论，不自行判定 P0/P1/P2 或关闭正式 issue。完整 v3 与 Q1/R1/S0 绑定、G-DATA、实际模型容量和后续预算仍待相应任务证据；本交付不阻断其他已授权工作，也不自行领取新模型运行。普通推送及原生交接后结束，由 S0 决定后续范围与 main 集成。
