# 决策记录

仅 S0 更新。每项后续变更应包含日期、基线 commit、备选、理由、影响、验证与回滚，不覆盖历史决定。

## ADR-0001｜Mac 原生优先

状态：规划已采纳。主训练为 MLX；PyTorch CPU 提供独立数学参考。CUDA 是未来可选，不默认产生云费用。

## ADR-0002｜独立对话，不使用子代理

状态：用户明确要求。S0 与 worker/reviewer 使用独立对话和独立 worktree。缺原生线程管理时由用户转交分发词，不用 sub-agent 替代。

## ADR-0003｜先有效实验，再复杂部署

状态：规划已采纳。SFT/DPO/数据隔离/oracle 是核心。首版不默认公网、复杂前端、多租户、GRPO 或投机解码。

## ADR-0004｜DPO 技术门

状态：规划已采纳，backend 尚未锁定。社区实现仅是候选；SFT reference、mask、数值、保存加载和适配兼容验收后才能正式使用。

## ADR-0005｜结果与许可诚实

状态：规划已采纳。负结果允许；无实测不填数字。原创内容 MIT，模型/数据/第三方代码分别核对许可，不复制私有毕设源码。

## ADR-0006｜GitHub 规划基线已远端发布

状态：已完成。用户创建公开仓库 `kris0516/ToolAlign` 后，规划内容通过 GitHub 连接写入 `planning/bootstrap-v0.1` 并进行提交级核对。首次建仓脚本保留为历史交付工具，不再用于当前仓库。

## ADR-0007｜S0 领取与持久独立对话协作

日期：2026-09-06；基线 `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`；状态：已执行。

本地 Codex 项目已 clone；S0 建立 P00–P09 长期 goal 和本对话每 30 分钟跟进。已发现原生独立对话 create/send/read/wait 能力，后续只通过这些真实能力派发，返回 ID 保存本机私有映射；不使用 sub-agent。遵从用户选择，当前所有 worker/reviewer 和 S0 固定 gpt-6-astra / max（最高）；最新用户要求见 ADR-0014，原先 xhigh 仅为历史配置。备选为手动分发文本，仅在原生能力不可用时采用。

影响：最多两个活跃实现对话，R1 纯 CPU 审查独立；P00 冻结合并验证前不发 P01–P03。验证：本机 Git clone/push dry-run、GitHub 权限/public read-back、长期 goal/自动跟进工具返回成功。回退：停用跟进不删除提交或未合并 worktree，按 handoff 手动继续。

## ADR-0008｜CPU 契约、离线 schema 子集与冻结摘要

日期：2026-09-06；基线同 ADR-0007；状态：VERIFIED；R1-r2 已独立通过，已合并并完成 main 集成验证。

选择 Python 3.11–3.14 + jsonschema Draft 2020-12，五类严格 wire record、六个独立 Protocol，额外检查字段关联。备选 Pydantic 或手写完整 validator 未采用；保持数据/接口可用 JSON 跨 backend 使用，并避免基础包导入 MLX/PyTorch。依赖用 uv.lock 固定。schema、validator、interfaces、protocol config 以 contracts.v1.lock.json 记录精确字节。

工具参数只允许闭合且有界的有限子集，拒绝 refs/正则/远程引用；支持范围外的来源记录隔离计数，后续如需扩展由 S0 通过 ADR 与新证据调整。GPU 使用 Git common dir 的 flock，锁文件不删除，元数据留私有目录。这保证同仓库 worktree 协作互斥，不声称阻止其他仓库或不合作进程使用 GPU。

验证：P00 正反样例、CPU 无 MLX 安装、跨进程/跨 worktree 竞争与异常退出、wheel 独立安装、公开扫描；具体退出码/日志由 handoff 记录。回退：S0 以非强制 revert 修复并重新冻结版本，不让已分发任务自行降级。

## ADR-0009｜偏好抽检阈值与运行预算候选

日期：2026-09-06；基线同 ADR-0007；状态：在采样/实验前预注册，随 P00 审查。

数据规范原有最少抽样规则保留；有效对抽检误标率严格大于 5% 时阻断正式 DPO，unknown 计入误标。选择 5% 是项目质量门的工程判断，非实测结论；更严格阈值会增加小样本返工，更宽松阈值会引入更多偏好噪声。实际误标率与原始分母都保留，不能看过结果后提高阈值。

首版最多 3 次模型决策、2 次工具轮次；256 输出 token / 30 秒仅是 P01 校准前的配置候选，未用于性能承诺。影响 P02/P05 抽检和 P03/P07 预算接口。验证/回退：配置与文档一致；如 P01 不可行，S0 预先登记新配置和理由再运行，保留原规则记录。


## ADR-0010｜P00 独立审查后的冻结候选修正

日期：2026-09-06；首轮被审候选 `15706079c9516197b67dd59a19a0d0c4aa5adea8`；状态：修复后已独立复核 PASS。

R1 原始审查提交 `66521f8`，结论 FAIL：两项 P1（类型不适用关键词可隐藏禁用 schema、公开扫描只读取工作副本）和三项 P2（自由映射键回显、身份 regex 末尾换行、目标调用 ID 与历史碰撞）。实际独立 probes 为 36 PASS / 10 FAIL；未发现本次候选真实秘密泄漏、联网或任意执行。S0 保留原始报告，不能把原有基础测试通过当作 R1 已通过。

采用最小修复：按 type 限定 schema 关键词；扫描 index blob 与工作副本；错误只显示可信 schema 路径；所有身份/时间 pattern 严格完整匹配；历史/目标 call ID 联合查重。全部五项修复，不仅处理 P1。新增对应负例与正向多步衔接测试。既有 wire 字段和六个 Protocol 不变，修复发生在首次冻结/合并之前，保留 v1 候选并重新记录字节摘要。

备选为接受 P2 并记录限制；未采用，因为这些问题可以小范围修复且直接影响后续数据一致性。验证：基础 tests、原始 R1 probes、公开扫描、冻结摘要、wheel 与 CI；精确结果记入后续 handoff，再由独立任务复核。回退：保留未合并分支和原始失败报告，若复核失败继续阻塞 P00，禁止派发 P01–P03。

复核结果：R1-r2 对 `5d30e1b4bd5e2284abbe59a5f16b2966f85feb87` 给出 PASS，独立证据提交 `441d31bebd5ca4d46755642f94966c07bbcc4ad1`；58 + 46 + 72 项 CPU 检查及独立 wheel 安装通过，五类问题全部关闭。S0 以 fast-forward 保留该审查提交原 SHA；其后只有 S0 验收文档登记，生产实现与被审候选一致。合并 main 后仍需集成检查才允许下一批。

集成结果：最终 head `708642448395be91357275a9a26def981a9f4110` 的 Python 3.11/3.14 CI 通过；PR #2 合并为 `cd091e3a53986b59b170baf5b746644f369135d1`。S0 在该 main 提交重验 176 项 CPU 测试、lint、冻结摘要、公开扫描与 CLI，均退出 0；P00 达到 VERIFIED。

## ADR-0011｜P01 兼容性依赖作为可选环境

日期：2026-09-06；基线 `4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`；状态：VERIFIED，R1 PASS、最终 CI 与 main 集成验证均通过。

T1 在私有 Python 3.14.7 环境完成候选安装，尚未给出正式训练验收。S0 独立核对 PyPI 固定版元数据后，选择 `compatibility` extra：mlx 0.32.2、mlx-lm 0.31.3、torch 2.14.0、psutil 7.2.2；前三级仅 Darwin arm64 生效。保留默认 CPU 基础包；不用整份私有 87 包 freeze 取代项目锁。传递依赖由 uv 实际解析。模型任务依然需要 GPULease、预算与本机证据。

备选为将 MLX/Torch 设为默认依赖；未采用，因为数据/契约 CPU CI 不应要求这些包或误装 Linux CUDA 依赖。mlx-tune 仍为探索候选；T1 的 mask/reference/内存限制风险另由 P01 实测，不随本决定批准正式 DPO。影响是 P01 可在审查后使用固定可复现兼容环境；不更改任何冻结 wire/Protocol。

验证：锁定解析、默认 CPU 环境无 MLX/Torch、Darwin arm64 可选环境的 metadata、跨平台解析计划、契约/lint/公开扫描与原 CPU 回归；具体结果在 S0 交接。回滚：停止依赖此环境的运行，非强制 revert 本次 optional/lock 变更，保留日志与已生成制品，不擅自清除缓存。

## ADR-0012｜ToolACE 历史工具的显式适配与无执行绑定

日期：2026-09-06；基线同 ADR-0011；状态：VERIFIED，R1 PASS、最终 CI 与 main 集成验证均通过。

D1 先审计前 32 条/142 个真实工具，全部缺项目副作用字段且根类型为 dict；S0 阅读代表记录并核对来源卡。直接把来源当冻结 wire 将无法产出有效数据；静默放宽 validator 会破坏 P00 门。选择独立、版本化的来源政策，保留冻结契约字节，明确记录类型别名、项目主动收窄、默认值 annotation、工具改名及来源 lineage。

ToolACE 只作为历史监督数据，其原始副作用信息为 unknown。wire 的 sandbox_only 表示本项目最多允许另行实现/审查的本地 fixture，而非原始 API 的事实分类；dataset manifest 必须同时登记 historical_supervision_only 与 execution_binding=none。使用 ta_ 名称空间，不从数据注册执行器，不把潜在写入 API 标为 read_only。P03 必须验证未绑定工具被拒绝。规则与具体排除条件见 docs/13_TOOLACE_SOURCE_POLICY.md 和 configs/source_toolace.v1.json。

备选为新增更宽 wire 类型、丢弃全部 ToolACE 或随意移除写工具；未采用，因为本轮观察到的主要差异可显式适配，而真实执行权限仍由独立 registry 控制。不是无损转换：补闭合/长度边界主动缩小允许集合，所有受影响原记录必须计数并通过新边界；不删除未知约束来提高留存率。来源许可、人工审查与 G-DATA 仍分别验收。

验证：R1 检查规则与冻结语义/任务边界的关系；D1 后续实现必须对规定负例和两次重建留证，人工包展示转换前后；P03 后续验证无自动注册。回滚：停止该政策对应数据版本，恢复严格隔离，保留原始输入/变更日志与排除分母，不用未审的新 policy 替换已有实验身份。


## ADR-0013｜S0 最高推理设置与子任务消息参数分离（已被 ADR-0014 取代）

日期：2026-09-06；状态：历史决定，已由 ADR-0014 全部取代，不再作为配置指令。S0 当时要求保持 gpt-6-astra 与用户当前设置的「最高」推理等级；子任务保持 gpt-6-astra / xhigh（极高）。旧协作协议中的「创建与后续消息统一 xhigh」存在被误用于发回 S0 的风险，现改为根据接收方区分。

所有给 S0 的原生消息完全省略 model/thinking，保留接收方设置；不能再用工具尝试重设用户已恢复的 S0 等级。S0 发给已确认 worker/reviewer 的消息才可以显式指定子任务参数。AGENTS、PROTOCOL、Supervisor 入口、分发模板与自动跟进同步记录；当前三个独立任务已收到即时修正通知。长期目标范围与阶段门不变，补充执行约束存 coordination/GOAL.md。

验证：逐项检查提示词的角色/消息方向、自动跟进保存字段；不调用 S0 设置变更来测试。回退不得恢复会覆盖 S0 的统一消息参数，只能由用户明确修改本项偏好。

## S0-SHARED-01 独立验收记录

R1 对精确候选 `e4127d9a0e6e30b091cba9b9e22a5fbb7091e9a2` 给出 PASS，P0/P1/P2 均为 0；独立报告提交 `8ceea3fbdd476ef0a5583e82e38473f1038dc650`。176 项既有 CPU 回归与 57 项新增边界探针全部通过。S0 fast-forward 保留报告原 SHA；后续仅追加协调文档及用户消息设置保护，不改被审依赖、政策或冻结实现。通过候选 CI/合并/main 验证后再正式发布新基线；本 PASS 不验收 P01 模型后端、P02 实现/人工质量或 P03 执行器。

S0-SHARED-01 集成结果：最终 head e9b33b0 的 CI 两个 Python jobs 全通过，PR #3 合并为 18fc8475476f6becf684ba817480caeb96a7cfb9。该 main 上 233 项 CPU 检查、lint/冻结/公开扫描与独立 wheel 验证全部通过，ADR-0011/0012 达到 VERIFIED。详见 reports/S0_SHARED_01_MAIN_VERIFICATION.md。


## ADR-0014｜所有任务统一 6 Astra 最高推理

日期：2026-09-06；状态：已采纳；来源为用户最新明确指令及其随后更新的活动 goal。S0、T1、D1、R1 及后续所有独立任务一律 gpt-6-astra / thinking=max；此前子任务 xhigh/极高规则作废。App 本机中文标签确认 max 对应「最高」，不猜测其他枚举。用户已亲自将进行中目标正文改为 max，S0 的 get_goal 已读回，原目标继续 ACTIVE。

执行：已向 S0 和当前三个独立任务分别提交原生 gpt-6-astra/max 设置调用；同步 AGENTS/GOAL/PROTOCOL、分发模板、私有分发词/身份策略与自动跟进。普通给 S0 的回报省略 model/thinking，不能重发旧 xhigh 参数。过去实际 xhigh 派发/实验记录保留历史事实，不能作为未来设置规则。

此前按发送方向省略参数的保护未达到用户观察到的预期，不能把已写文档当作设置已受保护。现统一使用用户核实的 max，并保留真实工具返回，不声称能改变已发生的推理或重新计算已完成工作。现有 P00–P09 范围、并发/资源/独立审查与公开边界不变。


## ADR-0015｜P01 备选依赖与完整失败重放分组

日期：2026-09-06；状态：ACCEPTED，独立R1-r3已PASS，待最终CI/合并/main验证。P01 具体申请新增 mlx-lm-lora3.1.2；完整探针仍依赖 mlx-tune0.6.0 来复现失败首选。分别设置 dpo 与 p01-replay 可选组，配合原 compatibility 使用；datasets固定实际3.6.0，保留真实传递依赖变化。不将失败首选纳入正式 DPO 选择，不为去掉审计依赖改写已测 GPU 路径。许可 metadata 与 wheel LICENSE 分别核对，mlx-lm-lora声明不一致如实保留。验证和回退见 S0_SHARED_02 报告；共享依赖通过不等于P01模型或正式训练验收。

## ADR-0016｜源码包采用显式文件范围

日期：2026-09-06；状态：ACCEPTED，独立R1-r3已PASS，待最终CI/合并/main验证。T1实际文件选择暴露私有目录，S0独立定位为Hatchling1.27.0在项目绝对根匹配.gitignore的.codex/规则时丢弃VCS排除。使用only-include选择发行所需源码/测试/配置/根文件，加实际App布局归档回归和CI检查。保留旧失败证据，不打包或上传真实私有文件做复现。冻结wire和已有代码接口不变；此缺陷不授权训练/评测绕过既定阶段门。若回滚共享依赖，仍保留打包边界修复，不能恢复已知不安全的源码包选择。

首轮 R1 对 55a330b 发现允许目录内部的忽略文件仍可泄入，公开扫描也未覆盖这些文件。修订同时采用公共 build 显式私有排除与 sdist 目录范围；85 个合成探针检查真实 sdist、重建 wheel 和直接 wheel。只修根目录范围不足以放行。D1 在旧配置产生过一次已隔离、未上传的失败归档，保留为私有证据，不能再笼统写所有任务均未产生归档。

第二轮 R1 对 8148929 发现 Git 的 Mac 大小写忽略语义与普通 Hatch glob 不一致。后续修订通过 ASCII 大小写字符类匹配同类私有路径，保留公开 `.env.example` 例外，不改变实际 Git/OS 配置。临时合成仓库以固定 ignorecase 条件检查 241 私有探针和 18 公开对照的三种真实归档；仍需新精确 SHA 独立复审，不以旧 CI 绿色替代。

R1-r3最终对f8ec7ff独立PASS，审查ad3b519确认两轮P1关闭且P0/P1/P2均为0。原反例、241/18回归及新增45/21近边界反例通过，旧FAIL保留原文。仅共享包达到ACCEPTED；最终CI、合并和main验证完成前不发布给worker。

ADR-0015/0016集成结果：最终head7541e0d双Python CI成功，PR4合并37c00de9abe92e6fb24a0c0e0b7361aa4bb90385；main176CPU、实际归档边界/构建及隔离wheel安装通过，现均VERIFIED。详见reports/S0_SHARED_02_MAIN_VERIFICATION.md。允许按最多两个worker同步已验证base，保留全部旧候选/失败；不由此提前验收P01/P02/P03或授权正式训练。
