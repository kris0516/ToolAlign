# P05-g4-preference-r1 — D1 交接

状态：READY_FOR_REVIEW。工作分支 `codex/d1-p05-g4-preference-r1`；实现提交 `147d0450447a7ad543a7a913f2a9084b039b849d`。生产基线 `1267d1a33dfb08bfd9800b80ea97315730748952`，范围授权 `6d5df60591dda6c5e63b8d8c8b8f45bbb828d022`，协议补充 `8b84a524c55bdb31edc9425814ce8eb2575e9f48`。完整交接提交由本分支 HEAD 和最终回复给出；报告与本单不修改实现。

交付仅新增 `src/toolalign/data/preferences/`、`tests/data/preferences/`、本单及[本包报告](../../reports/P05_G4_PREFERENCE_CPU.md)。公共契约保持 v1，工具/数据 split/模型模板/训练/依赖和共享协调状态没有改动。

- 私有任务：20 个原创 train、12 family、10 类、1 个六工具/schema 连通组；P02 held-out 冲突 0、隔离 0。P03 开发例仍为原 validation 诊断，共享 schema 已披露。同组不能作为未来独立 held-out。
- 构建从私有 authoring 输入读取完整 recipe，公开仅通用实现和 5 个独立 synthetic 测试例。`tasks.json` 的文件 SHA256 为 `d9fc455fa667bc323249bc5907571f1e38b446bc97f4f4b3da24a813d9649030`；规范 task list hash 为 `270bd53db823baeb0ae9a1193a427313c9ad4a5b6947505c5e7658c0901d2803`。
- 偏好：绑定实际完整前缀和 raw 决策；重算完整 oracle 判定并单独证明当前错误。合法替代、未证明错误、未来失败、格式/长度/基础设施和缺失/interrupted 都有处置。每任务按预先固定 ID 顺序至多一对，双方 seed/参数均保留。
- Q1：预注册分层抽样，材料留空待实际 reviewer；原分母不变、unknown 计错、严格 >5% 阻断、所有已确认误标/unknown 排除训练。synthetic 不可进入正式训练。
- 验证：最终 42 pytest；52 条真实 CPU 工具正/反轨迹符合预期且自有进程回收；最终 CLI 保留 40 条 scripted 测试候选、提取 20 对 synthetic 偏好。ruff、契约冻结、公开内容和 diff 检查通过。命令/退出码及证据复用说明见报告。

私有根为本工作树的 `.toolalign-local/p05-g4-preference-r1/`：

| 材料 | 路径 |
|---|---|
| 精确 authoring 输入 | `authoring-input.json`，SHA256 `919a6056464498291bdecf12545e14c53578d33e96c63d4857e721706ed0ad82` |
| 最终任务、authoring、分组及绑定 | `package-final/manifest.json` 及其 artifacts |
| 原始 CPU 正/反执行、实际请求、进程记录 | `cpu-validation/runs/` |
| 预先固定的 synthetic plan/40 条候选 | `cpu-validation/plan.json`、`cpu-validation/candidates.jsonl` |
| 最终提取与空白 Q1 材料 | `extraction-final/manifest.json` 及其 artifacts |
| 完整命令、源码指纹及拆分复用证明 | `commands.jsonl`、`tested-source-private-split.json`、`private-split-verification.json` |
| 精确路径/hash/提交接收索引 | `handoff-index.json` |

S1 可将 `package-final/tasks.json` 交给 T1；共享任务和候选结构未扩展。实际候选执行前，S1/T1 用同一批候选 ID/参数与实际完整模型身份生成 P05 `freeze_plan` sidecar，并在执行前冻结。authoring 的约束/真值只供父进程审阅和提取，不是模型请求字段。

R1 复核当前实现及关键反例；Q1 检查私有约束与提示一致性、所有合法替代、同组关系及首分歧归因。正式生成、真实 tokenizer 长度/模型前向、正式偏好质量和 DPO 均 NOT_RUN。无剩余自测失败，无新增 GPU/安装/模型数据上传/服务；本包不自签独立 PASS。
