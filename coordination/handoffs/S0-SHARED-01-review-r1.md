# S0-SHARED-01｜独立复核 r1

reviewer：R1；日期：2026-09-06；结论：**PASS**。

- 精确 base：`4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`。
- 精确被审 candidate：`e4127d9a0e6e30b091cba9b9e22a5fbb7091e9a2`。
- 来源：`origin/work/shared-compat-source-policy`，本次 fetch 后读回一致。
- 分支：`review/shared-01-r1`；沿用 App 中同一个 R1 独立 worktree，任务标题/私有身份已更新。
- 契约：`coordination.v1`、已冻结 `toolalign.contracts.v1`；新增候选来源政策 `toolalign.source_toolace.v1`、ADR-0011/0012。
- 剩余 P0：**0**；P1：**0**；P2：**0**。本轮无外部阻塞。

## 范围与实际验证

阅读候选 AGENTS、PROTOCOL、PROJECT_STATUS、任务包、S0 handoff/self-check、ADR-0011/0012、docs/01/12/13/14、来源配置和全部 12 文件 diff。独立检查确认候选未修改 src、原测试、冻结摘要、运行协议或 CI，原有 CPU 锁定依赖逐条保持相同；uv.lock 新增部分的来源/制品 hash 与依赖图已检查。

本 R1 运行 **176 项 CPU 回归 + 57 项新增边界探针，全部通过**；lint、冻结摘要、公开扫描、构建、新 wheel 在临时环境安装和 CLI 检查均退出 0。实际默认环境为 Python 3.14.7、12 个 distributions，无 MLX/MLX-Metal/MLX-LM/Torch/psutil。只读 S0 兼容环境 metadata 的 50 个 distributions，核对直接 pins、Python 要求、激活的依赖闭包及未安装 mlx-tune；未运行该环境的 Python 或导入任何 ML 后端。

独立执行 Darwin arm64 / Linux x86_64 / Intel macOS 的 extra dry-run，结果分别为 50 / 13 / 13 个包；后两种没有 MLX/Torch/CUDA。另以 Python 3.11–3.14、五种平台/架构和 extra 开关组成 40 组 marker/锁依赖图探针。**这些是解析/静态检查，不是对应平台的实际安装或后端运行。** R1 没有重新安装整套 ML extra；实际兼容环境安装来自 S0，本轮独立读取了其日志字节及现存 metadata。

新获取的四份固定版 PyPI JSON 与候选 pins/许可一致；逐一核对四个直接包在锁中的 **46 个制品**的 URL、大小、SHA-256 和未 yanked 状态。S0 十份原始验证日志的 hash 与其索引一致；这些只作为来源证据，不能代替上述 R1 独立运行。

逐命令退出码、日志 hash、初次审查脚本错误、来源/政策/锁/wheel 摘要见 [本轮证据说明](../../reports/review/S0-SHARED-01/README.md)。实际完整命令、绝对路径、原始日志和任务 ID 仅私有保存。

## 两项申请的判定

**兼容环境：接受。** optional extra 仅四个直接精确 pin；三项 ML 依赖同时受 Darwin 与 arm64 marker 限制，psutil 仅随 extra 选择。默认 CPU 依赖没有漂移；新 wheel 的 METADATA 保留 extra 条件，没有把它们变为默认要求。numpy 的 Python 3.11/3.12+ 分支在锁中可区分。mlx-tune、整份 T1 私有环境及 DPO 路线均未被本包批准；安装/metadata 成功不能证明训练或 Metal 正确性。

**ToolACE 来源政策：接受，范围为待实现的历史监督适配规则。** 本政策没有放宽冻结 validator。`sandbox_only` 仍把项目许可限定为隔离本地行为，不能凭这个 wire 字段获得执行能力；原始副作用 `unknown`、`historical_supervision_only` 和 `execution_binding=none` 必须保留在 manifest/lineage。此解释已由 S0 的 ADR 与 docs/01/12/13 明文登记，与冻结接口中“ValidatedCall 不是授权凭据、executor 须重新绑定 registry/version/hash”的边界一致；它不声称原始外部 API 已只读或已沙箱化。

政策明确禁止数据注册执行器、访问历史工具 URL 或重放业务操作；`ta_` 名称本身也不提供权限。只有另行实现、独立审查并登记的本地 fixture 才可能绑定，且不能沿用历史 observation 充当当前执行证据。P03/P07 对未知/未绑定工具的真实拒绝测试仍为后续门槛，本 R1 没有把尚未实现的行为签为通过。

| 审查面 | 政策及冻结边界的判断 |
|---|---|
| 类型/约束 | 仅三个明确别名；参数值不强制转换。补闭合/长度上限是有记录的主动收窄；已有更严格边界保留，明确更宽/开放、缺 items 和未知约束隔离。历史或目标调用不符合新边界时隔离整条记录，不靠增加留存率修改规则。 |
| default | 原始位置、类型、有限值/hash及对应参数 description 均保留；不填参、不改 required。默认值本身须符合类型、enum/范围/项目边界；冲突隔离。default 的例外不能推广到 pattern/format/examples 或任意未知关键词。 |
| 真实负例 | 原数据中有字符串形式的 boolean/float/int default，且存在 pattern/format/examples；候选规则要求隔离，不允许转换值或删约束。新增合成探针验证冻结入口会拒绝这些未知关键词及类型冲突，并保持 optional 参数省略。 |
| 名称与身份 | 固定公式最长 63 字符，符合 wire 的 64 字符限制。可逆性依赖原名/完整原工具 hash/规范化名称旁账及冲突拒绝，不能只靠截短 slug/hash12 还原；历史/目标/observation 必须一致重建关联。 |
| 可追溯与输入模板 | 原始记录/工具私有保留；字段级理由、原始 system hash、精确模板变更、policy hash、normalized hash 和原分组关联均需保存。不得删除用户任务内容、截断描述或利用改名绕过去重。 |

`validate_record` 本身不能证明转换无损、原始约束已保留、source default 已正确处理或历史参数全部符合收窄后的工具；P02 必须另行实现政策要求的转换前后检查。本文与新增探针仅验证规则可与冻结契约共存，**不是 D1 normalizer 的实现验收**。

## 原始来源证据

R1 对已授权的私有 ToolACE 文件独立核对 SHA-256、37,154,735 bytes、11,300 records；新读回固定 revision API 的 SHA/gated/private/license 元数据。前 32 条的 142 个工具与 S0 说明一致。

新增只读抽查脚本只识别明确的英文 JSON 工具列表格式，得到 10,534 个非空列表记录、33,690 次工具出现、120,900 个 schema 节点；工具参数根均为 dict，副作用字段全部缺失。default 11,213、pattern 1,336、format 418、examples 59，及 boolean/string 68、float/string 373、int/string 63 共 504 个指定 default 类型冲突，与 D1 catalog 的工具/节点统计一致。另将 12 个 annotation 示例逐字段与原文件对应位置核对。

D1 catalog 的“可解析记录”数为 10,782；R1 的显式格式/非空列表口径不同，不把两个记录分母强行视为一致。脚本输出分别标明 R1 抽查口径与 D1 原报计数。这些计数不是适配后留存率，不证明任何 P02 样本合格；没有审核 D1 未提交实现，也没有使用“0 有效样本”推断政策实施结果。

## NOT_RUN 与可合并范围

**NOT_RUN**：R1 自建 ML extra 完整安装、任何 ML 包导入/模型加载/张量/重 GPU 作业、T1 的 SFT/DPO/MLX-Tune 路线、Linux/Intel/Windows 实机验证、D1 normalizer/全量重建/人工质量门、P03 registry/executor 实现与执行隔离验收、候选 GitHub CI 读回、main 合并与集成验证。没有新增模型/数据下载、付费资源、业务调用、GitHub 写入或其他 worktree 修改。

建议 S0 仅接受精确 candidate 的公共 dependency/policy 申请与本审查证据；CI、合并和 main 验证后再发布 T1/D1 新 base。P01 功能/数学/资源和 P02 数据质量仍按原任务验收，不能因本 PASS 提前放行后续实验。

本 R1 仅提交本交接单及 `reports/review/S0-SHARED-01/` 下的说明/三个小脚本。未修被审实现、修改公共状态、合并 main、推送或创建嵌套代理/新任务；审查 commit 与任务身份由最终回复私有交回。
