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

## ADR-0017｜共用 Action JSON 与保留 Message 角色的投影

日期：2026-09-06；状态：SELECTED_FOR_IMPLEMENTATION，尚未实现验收或启用正式训练。决策基线 main `201e3a1f697a567f843754e465e57d8227660264`。规范见 [docs/16_MODEL_IO_FORMAT.md](../docs/16_MODEL_IO_FORMAT.md)，机器描述见 [model_io.action-json.v1.json](../configs/model_io.action-json.v1.json)。

S0 实际证明旧 P02 原生 tool-call completion 不能直接通过 P03 Action JSON parser，且同 content 的 final/clarify/refuse 丢失 kind 区别。D1 的完整 CPU 比较候选 `6c3d330e4b28be0fbc93c273bb2576f7317c69a8` 在同 12 个原创/公开例上保留 ModelInput/Action 值；S0完整读取实现、报告和结果，核对68项证据hash及167份不变原文件。选择 B：固定 system 格式指令与工具 catalog，各原 Message 作为可逆 JSON record 保留模板输入 role，完整 Action 作为输出；官方模板、non-thinking 与冻结契约不变。tool 仍由官方模板转为 user/tool_response，历史 Message 不补 kind，模型 raw 不作生成后修复。

备选 A 单 user envelope 也可值往返，但丢失原 system/assistant 控制段；B 保留这些结构，因此采用 B。B 的 JSON 引用内容和追加协议是否被模型正确理解仍需后续实测；CPU 不证明质量等价或提升。B 在小样本多39–93个prompt token，此差异并非纯角色消融或全量统计。正式版本仅将提案格式标记和指令首句的 v1-proposal 改为 v1，故新 prompt/sequence hash 必须重算。模板/tokenizer来源小文件已在固定0.6B/1.7B间只读核对一致，没有加载模型。

影响：D1 新增纯共用 model_io 模块、CPU边界证明和完整8,228例的新序列审计，逐项绑定新格式/源码/模板/依赖/原数据身份；上下文1024/1536/2048与当前256响应上限分开计数，超限和失败仍计入完整分母。原数据代码、两遍18项产物、split/标签、原长度表及人审材料均保持。旧技术PASS对应旧实现，不能改写成新格式PASS。D1只在新的明确授权后实施，R1独立审查、S0集成验证后才可成为P04依赖。

验证与回退：真实固定tokenizer对最终v1的同12例进行新跨实现CPU对照，验证原始字节/角色/prefix/EOS/mask/raw及独立负例；新全量长度仅为派生审计，不是训练选集或模型评分。G-DATA、G1、P03及P04人工/真实模型门仍独立。若实现或后续模型不满足目标，停止该格式后续实验、保留所有原证据，以新ADR/版本修订，不覆盖旧身份或隐去失败。

## ADR-0018｜P01 分项兼容验收与唯一 DPO 备选

日期：2026-09-06；状态：VERIFIED（限定 P01 已记录配置）；生产合并 `d10722e491d6a8efe26b8248efb9c19cc2216742`。原始 R1-r3 `7e207060539df682691b4d149e68b7ab4ffc3175` 对精确9fe3cbe正式PASS；最终双Python CI与main655CPU/21条隔离安装命令通过，详见 [S0主干与G1验收](../reports/S0_P01_MAIN_VERIFICATION.md)。

G1-SFT 单独标 PASS：MLX-LM 0.31.3 的固定mask/身份、保存重载及受限0.6B/1.7B校准证据有效。G1-DPO 的首选 mlx-tune 0.6.0 保持 FAIL；按既有最多一次备选规则，接受 mlx-lm-lora 3.1.2 在已审显式collator/mask、完整SFT-smoke frozen reference、禁用编译及指定checkpointing下的受限兼容性PASS。容差、原始失败、pressure停止及历史源码映射保持，未通过换标签或降低数值门关闭问题。

影响：P01工程阻断关闭，P03已验证；后续T1只能在相应精确授权中使用已锁环境和这些身份/停止原则。不会因G1通过自动启动正式训练或采用未审新格式；P02人审、ADR-0017实现与新序列/配置绑定仍需分别通过。P05的reference必须来自后续真正验收的SFT checkpoint，当前smoke reference不能冒用。长时训练、量化对照和完整真实harness仍按后续任务实测。

备选为继续修首选DPO或新增第三个训练库；均未采用，因为既定唯一备选已有独立数值和受限模型证据，继续扩展会偏离计划。回退：若后续真实配置与校准假设不相容，停止对应运行、保留原制品和负结果，重新给出具体修订/授权；不得自行抬高预算、重写原G1证据或引入第三个backend。


ADR-0017实现验收补记：原R1 b9f7567对修复8c439f6正式PASS，随PR8合并36b6988，最终双Python CI34029892077及main843CPU/2 HF-only skipped与实际归档绑定通过。该格式实现现为VERIFIED，原规范/描述符字节与旧FAIL/测量均保持；G-DATA和P04训练门槛独立，见[主干证据](../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)。

## ADR-0019｜固定训练选择与人工token/mask材料的CPU准备

日期：2026-09-06；状态：VERIFIED（训练绑定CPU技术范围），PR9实际合并42eaa50；原R1 PASS40252f8、最终双Python CI与main919CPU/2跳过及归档绑定通过，见[主干证据](../reports/S0_P02_TRAINING_BINDING_MAIN_VERIFICATION.md)。原选择规则及[精确配置原件](tasks/P02_TRAINING_BINDING_CONFIG.v1.json)保持，training_authorized=false。实际材料页面观察、语义/token-mask人审、G-DATA和模型/训练门槛仍未通过；以下规则和原算术保持其原决策范围。

使用原已验收ToolACE数据及原v1表示审计，仅从train/validation生成新的私有派生选择。每行须保持Example、source/group/split/目标身份，表示成功、总长P+C+唯一EOS不超过profile cap、C含EOS不超过256。正式1.7B数据规则为2048档全部合格行；0.6B smoke为1536档按固定seed42的稳定hash排名取1600条train，validation分别使用各档全部合格行。排名键为canonical_hash(["toolalign.training-selection.v1",42,example_id])，hash升序、同hash按example_id升序；输出顺序固定，无放回。不得按模型分数、最终测试或BFCL选样本。

已有train/validation只读算术为2048档6013/217、1536档3618/197；这些只是既有统计的核对值，实际新选集及输出hash须由本轮生成后验收。1024档只有985条train，无法达到原1k–2k不重复smoke目标；因此选择1536档1600条，保留正式6k–10k目标。0.6B在1536的新格式真实容量尚未测量，正式训练前另做有租约与预算的小型前置检查，不能套用1.7B速度或按此CPU决定启动模型。

所选每行记录最小可容纳的1024/1536/2048右padding桶，保持顺序，不截断/packing/重复或静默丢尾批；这里只绑定数据，不实现trainer。以未来microbatch1/累积8作算术时，1600条为200组；6013条为751组加5尾微步，真实尾批缩放与checkpoint验证仍由P04另行实现验收。P+目标长度合格不保证P+预留256生成token也合格，另列该计数，不能据此修改推理协议或评测分母。

原8228条目标实际全为tool_calls，新选择保持该覆盖限制，不声称包含final/clarify/refuse监督。准备10条实际已选train样本的CPU token/mask材料，并另列三类原创协议检查例；原创补充例不进入训练选集。材料展示完整目标/边界/唯一EOS/shift/右padding及空白人工判定；不能把模型自查写成kris审阅，也不能用这次离线材料代替未来真实trainer的mask核验。

原8,228行native测量和R1一次reference全量仍保留旧代码/环境/时间；本轮只读旧指标选择并用少量明确样本实际核对当前格式，禁止无差异全量重跑。公开仅代码、配置、去敏hash/统计及原创fixtures，所有选中原文/IDs/token数组和人工材料私有保存。G-DATA语义人审与训练配置绑定分别待验收，配置training_authorized固定false。若输入/表示身份不符或后续人工要求修数据，停止该绑定的使用，以新版本/新授权处理，保留旧选择及失败；不改写原数据或抬高预算。


## ADR-0020｜已验收训练绑定后的SFT接口CPU准备

日期：2026-09-06；状态：CPU_PREPARATION_VERIFIED，原R1 PASS800480b保持，PR10实际合并e28f1db；最终双Python CI与main1014CPU/2跳过及三归档/57安装包文件绑定通过，详见[主干证据](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)。完整原生trainer入口仍BLOCKED，上游/数据/人工边界保持。代码基线为PR9实际main `42eaa50a9519efe96d60b49f07cfbd106b36778c`；P00/P01受限G1/P03/共用格式/训练绑定的CPU前提已验证，语义与token/mask人工、实际页面、真实0.6B容量及正式模型门槛继续待完成。S0将可独立进行的CPU数据/collator/数值适配拆为[P04-SFT-CPU](tasks/P04_SFT_CPU_PREPARATION.md)，不把完整P04改名或登记完成。

本机已锁MLX-LM 0.31.3的trainer源码hash为ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe，datasets源码hash为fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17。S0重新读取原件：默认iterator按长度排序/重排并允许截断；default_loss的padding额外监督已有P01真实反例；train只在完整累积周期更新，内置最后validation发生在最后微步之前。源码依据和旧负结果不改写为新模型运行。

选择利用原生iterate_batches/loss参数与分段TrainingArgs，复用共用Sequence/pad_sequence；固定原rank顺序、microbatch1、累积8、右padding且不截断。单微步按有效completion token平均CE，更新按周期内各微步等权平均，最后不足8的周期按实际微步数除；同一model/optimizer/RNG连续使用。smoke1600→200、formal6013→751+1=752是当前计划算术，CPU样例不冒称实际跑完这两套训练。validation单列采用总CE/总有效监督token，并绑定post-update的实际参数内容hash、保存文件hash和步数；选择规则为最小finite CE、同值较早optimizer step、再按checkpoint hash，真实评估频率另待正式配置。

本轮允许已核对的原13例通过新collator及极小原创MLX/PyTorch CPU数值模块对照。框架replay实际持共享租约、强制CPU、独立自有进程和≤300秒/4GiB RSS/2线程/2次更新的每次上限；不加载预训练模型、不对P02真实数据优化、不创建环境或下载依赖。该数值许可不改变原training_authorized=false或人工门槛。精确参数仅来自[S0配置原件](tasks/P04_SFT_CPU_CONFIG.v1.json)，T1在唯一新配置例外中逐字节复制。

备选为等待人工后再实现全部衔接，或直接沿用默认dataset/loss/循环；前者把可独立验证的代码也挂起，后者不满足已选数据顺序、mask和尾周期要求。当前选择只提前完成必要CPU实现，未来真实model/optimizer/生成仍须按完整P04独立验收。若实际上游注入点不能满足边界，保留最小反例并交S0具体处理，不fork通用训练框架、改vendor、降数值门或隐去失败。

ADR-0020接收补记（2026-09-07）：默认prepare不依赖框架入口，固定数据/视图/collator与纯结构接口可独立接收。原生train_toy_segments/post_update_score的实际更新、尾周期、evaluate与保存重载未通过，不作为已验收trainer使用；保留原KeyError，后续兼容修订须另定精确范围，不由CPU部分PASS自动放行正式P04。

ADR-0020主干补记：CPU准备已按原SHA独立审查、普通合并并完成最终CI/main验证；完整原生trainer入口、真实更新/尾周期/checkpoint、人工与正式模型门仍独立未完成。


## ADR-0021｜原生 GPU 上的固定原创 SFT 数值验证

日期：2026-09-07；状态：VERIFIED（固定原创数值范围）。P04-SFT-NATIVE-TOY固定原创数值部分VERIFIED；PR11已普通合并b2247d8，原候选f7326d1与原R1 PASS67976fd保持。最终双Python CI各14步骤及main1084CPU/2 HF-only跳过、三份现存归档/58份安装包绑定通过。[主干证据](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)。原授权与资源上限如下保留；旧CPU入口KeyError与人工/正式模型门槛保持。

S0选择在规划中的MLX GPU设备验证同一小型原创数值问题。新增[P04-SFT-NATIVE-TOY](tasks/P04_SFT_NATIVE_TOY.md)及[精确S0配置](tasks/P04_SFT_NATIVE_TOY_CONFIG.v1.json)，复用旧13例/8词表/64参数初值和SGD0.07，真实运行8+5两次更新、native evaluate和checkpoint保存重载，与独立Torch CPU参考对照；另一次单段13微步的上游尾批丢失作为负例。验证集复用原创样例只检查状态记账，不宣称真实模型质量或泛化效果。

这是一项新限域GPU许可，不改原CPU配置及入口默认CPU限制，不伪造Metal设备属性来宣称CPU成功。只在原生公开注入点做有限适配，保留上游train/evaluate/compile；P01的wired-limit抑制上下文可原样复用，不能调用系统setter或改其源码。新的score scope必须显式TOY_NATIVE_GPU并拒绝跨scope混选，原CPU/formal门槛保持。

现有replay环境只读，先实际取得共享OS租约再导入框架、明确GPU stream/Torch CPU；每个子进程最多2更新/300秒/4GiB RSS/1GiB MLX peak memory，私有新增2GiB、Torch最多2线程。T1最多5次框架子进程启动（失败计入），预期三次分别为源码正例/源码负例/安装版正例，另外两次仅用于真实失败修订。每次保留原始数值/源码/命令/资源/终态，租约持有至真实进程退出；R1的新运行须后续独立授权。

不加载预训练模型，不优化P02真实数据，不新增实际13例或全量tokenization，不改训练选择，不开展baseline/容量/SFT/DPO正式模型任务。配置training_authorized=false、实际页面与kris语义/token-mask人工待审保持。旧P01/P04分支、原CPU两次失败与R1审查原SHA/制品均保全，新的执行时间与源码身份独立记录。此子包PASS仍须独立R1、S0普通合并、CI/main验证，不能直接登记完整P04完成。

ADR-0021中间证据补记：S0已核对534445b的两次原GPU运行：13例完整数值、8+5实际更新/两个checkpoint及原单段丢尾反例通过；fae3d60监督器终态缺陷的CPU定点回归通过。完整候选/安装版独立核验、R1、最终CI/main仍待完成；人工与正式P04门槛保持。原成功源码数值保持534445b epoch；监督器修订形成fae3d60新epoch，不能将历史成功运行改写为修复后重跑。原13 rank/12种数值载荷、负结果和shutdown warning保留，见[S0中间证据](../reports/S0_P04_SFT_NATIVE_TOY_INTERMEDIATE.md)。

ADR-0021独立审查已于19:36:51 UTC按完整482f899实际派发，并核验R1新轮ACTIVE；原轮completed/notLoaded与干净800480b在派发前再次核对。T1精确f7326d1和原生completed/idle已核验，S0完整交接证明见[报告](../reports/S0_P04_SFT_NATIVE_TOY_HANDOFF.md)。[R1新范围](tasks/P04_SFT_NATIVE_TOY_REVIEW.md)IN_PROGRESS；独立新安装target至少一次原13例GPU segmented复核，本轮R1最多两次框架启动，第二次仅真实失败修订或有明确必要的原尾批反例。每次仍先共享OS租约/最多2更新/300秒/4GiB RSS/1GiB MLX，真实owner记R1；不使用T1未用额度，不改原配置，不放行正式P04。

ADR-0021独立验收与集成补记：原R1 67976fd正式PASS已按完整来源/数值/资源/封存核验，S0普通merge a1c467a通过1084CPU/2跳过、新三归档及默认安装/native守卫。R1框架2/2已用完，S0新增框架0；原13 rank、上游compile、原配置、历史负例/警告及人工门槛保持。见[集成证据](../reports/S0_P04_SFT_NATIVE_TOY_INTEGRATION.md)；最终CI/main前不登记VERIFIED，不把固定原创数值扩大为真实模型能力。

ADR-0021主干补记：最终CI34061081859双Python各14步骤通过，PR11以精确head397102c普通合并b2247d8并在实际main完成1084CPU/2跳过与现存归档/安装绑定。本数值子包VERIFIED，S0框架新增0；不改原CPU支持结论，不解释为真实P04模型训练或人工审核通过。

## ADR-0022｜接收委托AI审阅，按新版本整改质量问题

日期：2026-09-07；状态：CPU整改范围已确定，D1/E1待原生分发，G-DATA未通过。基线86b80bada50ac7c8f4b3910e3831a397ed65a853；[交接核验与范围](../reports/S0_P02_DELEGATED_REVIEW_INTAKE.md)。

kris在侧对话明确委托AI审查并填写两套P02材料、反馈不合格内容及处理建议，随后要求重发给S0。S0接收原生交接及追加来源引文记录；来源接口不可列出临时对话turn，记录这一限制而不编造消息凭证。将本批审阅方式登记为kris委托的Codex-AI，既有副本直接使用，不要求本人重复抄填，也不写成kris本人或独立R1已通过。此项只调整本批P02语义及token/mask内容审阅方式，不废止P05偏好抽检规则或kris最终学习检查。

实际浏览器观察0页/NOT_RUN及既有URL安全拒绝保持，禁止绕过。委托AI消费结构化来源与完整token数组，静态HTML内容另核对；本轮CPU内容整改不以用户页面实显为前置条件。页面体验验证独立保留未完成，不能用此决定声称浏览器已显示或普遍放宽工具策略。

报告标记的20个fail和12个unknown来源全部先暂挂。D1实现新的质量修订视图和原选择的有序子集，不改变原数据/同组其他来源/split、旧证据或已冻结v1算法；新配置仅为CPU候选。两条重标草案有parent与新身份、完整序列和后继风险说明，先staging不进有效训练。参数变动后的合成观察不冒充真实重跑；无法证明的后继继续隔离。

E1在另一独立worktree复核32来源并进行固定扩展审计：先随机train96/validation24，再六种诊断模式各最多10个，去重并排除旧审来源，最多180个新来源。模式仅取样，不作自动fail或全库过滤器；未知约定与明确矛盾分开。样本身份在判定前冻结，随机和定向分母分开，不将最终test/ood_test内容用于训练整改。新发现由S0另冻结给D1，不消费变化中的标签。

G-DATA仍须问题处理、新数据/选择/配置绑定及独立复核；未审部分不得标质量认证。正式P04/GPU/模型/费用/发布无新增许可，training_authorized=false。最多两个实现D1/E1，R1留作后续独立验收；无需启动新角色或重复已完成基础包。

01:17 UTC实际接续：D1/E1原生新轮ACTIVE已核验，均按完整2aa0cf4授权并显式gpt-6-astra/max发送。固定配置/代码基线不变；此时intake与候选尚待交付，GPU空闲。


## ADR-0023｜全部后续审核交独立AI，同一问题第五次未通过再整体暂停

日期：2026-09-07；状态：用户已明确授权，Q1/R1精确任务READY待原生派发。用户要求单独派发一个对话完成后续审核，人工彻底退出，只有一个问题反复未通过5次才暂停整个目标并通知其介入。

建立专门Q1 App独立任务及隔离worktree，gpt-6-astra/max，接管P02语义/token-mask、P05分层偏好和全部后续原人工审核、最终说明/答辩材料检查。R1保留独立技术审查，S0负责冻结范围、问题台账和验收；不能代签kris或把AI说明写成其个人能力。此决策取代ADR-0022仅限本批的参与限制，不降低质量、复现、许可与训练门。

[审核规则](REVIEW_POLICY.md)定义稳定问题及真实修订计数：首次正式未通过1次；同问题每次实质整改后独立审核仍未通过才递增；重复命令/同候选复读/其他问题不累计。第1–4次自主修复，第5次安全收尾、停止整个P00–P09主动推进与新派发并通知kris；PASS关闭且保留历史。既有无关授权、费用、隐私、外部发布限制保持。

当前D1完整9b7cf01与S0交接核验已成立，先由R1审精确技术候选；Q1先处理已冻结14来源15决策的11项等级分歧/2重标/新PDF问题。E1完成原180来源及16材料后按精确seal接续Q1，不重做固定抽样或实时改D1输入。原生goal已读回ACTIVE，不重建或清空已验收进度。G-DATA仍CHANGES_REQUESTED、正式P04未授权。

ADR-0022/0023技术接收补记：R1原1e45cf2对9b7cf01的CPU技术PASS已由S0完整接收：14,011路径、42原命令、14源码快照、三现存归档及60安装包文件绑定通过；1,186CPU/2跳过为R1实际结果。PR12隔离集成/最终CI/main待完成。R1下一5270审计技术包CLAIMED待原生派发，Q1固定50来源/60决策继续ACTIVE；G-DATA和正式P04未授权。旧review原SHA及公开文件副本保留，R1新checkout不伪称旧公开路径不变；旧私有封存继续只读。

ADR-0022/0023隔离集成补记：P02质量修订原R1 PASS1e45cf2已接收，普通集成f90be60实际1,186CPU/2跳过、三份新归档及60安装包文件通过；27条命令均符合预期，包含八次预期输入拒绝。PR12最终CI/main待完成。R1已按完整769f9ff原生接续精确5270审计技术复核/ACTIVE，intake待交付；Q1固定50来源/60决策继续，G-DATA和正式P04未授权。原候选/review保持原SHA，S0未新增框架或完整16例材料编码。

ADR-0022/0023主干技术验收补记：P02质量修订CPU技术子包VERIFIED；PR12普通合并6c81dfc，原候选9b7cf01/R1 PASS1e45cf2保持。最终双Python CI各14步骤及实际main1,186CPU/2跳过、三现存归档/60安装包绑定通过；[主干证据](../reports/S0_P02_QUALITY_MAIN_VERIFICATION.md)。R1精确5270审计技术轮ACTIVE，8,658路径intake通过；Q1固定50来源/60决策裁定继续。新版数据/选择/配置绑定、G-DATA和正式P04尚未通过。旧失败及审核轮次保持，无新模型/框架许可。

ADR-0022/0023审计修复接续：R1在PR13原5270中间复现JSON false/0混同，S0确认delta漏项并保存438原公开文件，见[中间证据](../reports/S0_P02_AUDIT_TYPE_FINDING.md)。E1限域类型保真修复CLAIMED待原生派发；原R1继续冻结候选并核定实际影响，尚非整包正式结论。根因单列P02-AUDIT-TYPE-001，正式审核计数待原review交接，不把三个测试失败计为三轮。

## ADR-0024｜将固定独立裁定纳入新的有效数据视图

日期：2026-09-07；状态：CPU实现范围CLAIMED，完整输入已冻结，尚未生成/验收新版。原Q1 5100/42d9裁定、原R1技术FAIL9645055及E1修复候选da22分别保留。当前最高连续正式失败1次，整体目标继续。

采用Q1两轮固定判断与原32来源保留隔离，形成83来源处置：3个已获PASS的原始来源恢复，其他80来源/98决策排除。使用完整来源/必要历史的训练适用性；UNKNOWN保持未知，不将Action局部PASS自动当作整条前缀可用于训练。通过明确隔离关闭数据使用问题是REVIEW_POLICY允许的处理方式，无须把残缺来源补造成正例。

从原始数据和原选择名单形成新版本，按原rank恢复和过滤、不补选、不重新切分或修改同group其他来源。预计formal/train5,940，比原6k规划下限少60条；S0明确接收这一数量偏差作为下一版实验计划输入，后续P04配置和报告记录实际数量，完整数据与训练仍须独立验收。为达到旧整数下限增加未选来源会改变已冻结选择规则，当前不采用。

保留旧v1模块/配置/manifest和全部原材料，新增有限adjudication模块与精确v2配置；复用现有纯数据、格式及sequence函数，不扩展成通用审阅平台。旧两直接草案和一后继继续staging，无新重标或晋升。仅对新有效选择按原代表规则形成10例，加原三类协议例共13例，两已有CPU tokenizer路径核验；R1技术与Q1材料/实际整来源排除核验后由S0处理G-DATA，不新增无界全库人工审查或重抽180例。

新绑定保持training_authorized=false；已存在SFT准备仍绑定旧配置，未来T1消费适配、真实0.6B容量与baseline/SFT另定精确范围。页面实显保持NOT_RUN，固定13例之外无新分词，无模型/框架/GPU/业务API/费用或上传。若独立审核发现该修订仍未满足同问题，按原稳定ID登记真实新修订结论，前四次自主整改、第五次才整体暂停。

ADR-0022/0023审计主干补记：原R1 0cefe771对da22正式PASS，PR13普通合并1887feb且最终双Python CI/main55pytest及15页面检查通过，审计CPU技术VERIFIED。TYPE-001关闭、原9645055首次FAIL及反例保留；D1冻结217项输入与Q1原判断不追溯改写，G-DATA/P04待新版及独立审核，见[证据](../reports/S0_P02_AUDIT_MAIN_VERIFICATION.md)。

ADR-0024候选接收补记：D1完整1c47e6a已普通推送/原生空闲，S0核验21,424路径、57原命令、15源码epoch及三实际归档/6安装命令通过。新版实际80来源98决策排除、3来源恢复、formal5,940条；原字节/rank及材料13例静态重封装绑定已核验。Draft PR14候选双Python CI通过，R1精确技术范围CLAIMED待派发，Q1实际处置与新材料包准备中；未修改原台账、未合并候选或放行G-DATA/P04，见[接收证据](../reports/S0_P02_QUALITY_V2_HANDOFF.md)。

ADR-0024独立审核接续：R1已按完整d9e5622原生接续精确1c47候选/ACTIVE，Q1新346项输入绑定同一候选、83来源实际处置和14唯一语义目标/13材料，范围CLAIMED待原生派发。Q1处置PASS可按稳定issue关闭训练使用问题，原语义FAIL/UNKNOWN不改写；不扩大为新的180来源或全库语义审查。

12:15 UTC实际接续：Q1上一轮原生completed/notLoaded、干净42d9已再次核验；S0按完整d31ca701派发Q1-P02-v2-r3并确认新轮ACTIVE，gpt-6-astra/max。既定346输入、83来源处置与14语义目标/13材料范围保持；新branch/intake与独立结论待交付，无新语义样本/编码/训练授权。

## ADR-0025｜定点排除新来源，复用旧编码并先审替换来源

日期：2026-09-07；状态：D1 v3与Q1两来源审核CLAIMED，待原生派发。代码基线为PR14已验证main d3e56f68ebd67cc576d912b6f06636682b4170ab；[范围与冻结证据](../reports/S0_P02_QUALITY_V3_SCOPE.md)。

Q1原8a738ab确认旧83来源处置和13材料mask，通过实际隔离关闭77旧问题；新增P02-Q-081是一个完整来源历史字面字符数矛盾，首次正式失败计1。下一版本整来源排除两条原决策，旧80来源排除及3原字节恢复保持。当前Action的PASS不改变前缀/整来源适用性，UNKNOWN子发现保持原记录。无需kris介入，也不扩大为全库重新审阅。

沿用原固定选择，不补选，预计formal5,938条、较原6k计划少62条；后续P04按实际数量配置。新增有限v3 wrapper及精确配置，复用已验收父输入验证和纯函数，旧v1/v2代码、配置、数据与所有失败保持。新版rank区分当前、v2及原v1；训练绑定仍training_authorized=false。

原代表材料算法会复用11例并选出两个新来源例。先由独立Q1审完整两来源/三有效目标，同时D1完成CPU过滤与复用实现；S0按精确Q1结论再放行两个新例的两engine编码。11例沿用实际旧sequence/padding/token_texts和原编码时间/源码/run，另核对新case/revision/rank和HTML。另一旧PASS例退出代表材料但仍保留训练资格，不增加来源排除。三协议fixture保持训练外与行为适用性边界。

来源预审不提前关闭P02-Q-081或签token/mask，完整候选交付后仍由R1技术独立复核、Q1实际排除/材料核验和S0 main验收。资源为现有CPU、D1新增≤1GiB、Q1新增≤128MiB、仅两新例/engine；无全库重分词、模型/框架/GPU/新依赖或费用。浏览器NOT_RUN及正式训练门槛保持。

13:55:51 UTC实际接续：S0核对D1/Q1旧轮completed及空闲、16,049文件路径/327链接后，按完整3e18145原生派发两新范围并确认ACTIVE，gpt-6-astra/max；实际新branch/intake待交付。固定配置/输入不变，新编码仍待S0按Q1精确来源结论放行。

ADR-0025并行只读准备：T1的P04-SFT-RUNTIME-PROPOSAL现CLAIMED，固定10份源码/元数据166,598 bytes及已验证d3基线，待原生派发。范围只提交真实Qwen消费/原生训练、尾批/检查点/容量与同配置基线的可落实方案，新增生产实现/框架/模型运行均0；D1加T1最多两个实现/准备任务，Q1保持独立来源审核。实际v3数据与质量门槛不因方案放行。

14:15:28 UTC实际派发T1只读方案：原轮completed/notLoaded和干净f732、5,416原文件/197链接再次核验后，按完整8929cbb原生派发并确认ACTIVE，gpt-6-astra/max。新branch/intake待交付；D1/Q1的实际新branch和完整输入现均经S0核验通过，原3e18145范围继续。

ADR-0025主干与质量验收补记（2026-09-08）：PR15普通合并90c4da9，原R1 dbd11d0、最终双Python CI/main技术VERIFIED；原Q1 7941已接收并普通合并10a22a0，84来源实际处置和13材料PASS。P02-Q-081第2次正式审核PASS后关闭并归零，82问题全部关闭，旧FAIL/UNKNOWN和全部历史事件保持。S0批准G-DATA的冻结v3范围，见[数据批准](approvals/P02_DATA_V3.json)与[接收](../reports/S0_P02_Q1_V3_ADJUDICATION.md)。原candidate pending字段不回写；正式模型配置/容量和CPU trainer适配独立接续，training_authorized=false。


## ADR-0026｜冻结v3数据与审阅数组的CPU消费适配

日期：2026-09-08；状态：已采纳，T1任务CLAIMED待原生派发。G-DATA已通过冻结v3，PR15/R1/Q1及S0批准保持。先用新精确配置接入既有只读verifier与四个SelectionView，将13份已审数组转换到原Sequence/Batch并做有限导出/回读；不以修改旧v1配置校验来接受任意manifest。新模块独立，旧公共代码/契约/锁文件/默认CLI和toy保持，配置由S0固定。[任务](tasks/P04_SFT_DATA_V3_CPU.md)、[配置](../configs/sft-data-v3.v1.json)和[冻结证据](../reports/S0_P04_DATA_V3_CPU_DISPATCH.md)。

选择已封存数组衔接是因为格式、语义与mask已经独立审核，当前未知是实际CPU消费者的身份、rank/类型和数据接入。此步骤不需要再编码或认证未审全库。D1历史pending/FAIL及原时间保持，新S0数据批准单独绑定；3原创协议例继续训练外。源/安装版各一组固定消费，新增真实编码/模型/框架/GPU/优化0；独立R1与main验证后才准备真实runtime和容量范围。正式训练授权继续false。

## ADR-0027｜数据无关的固定Qwen加载接口并行CPU实现

日期：2026-09-08；状态：已采纳，E1任务CLAIMED待原生派发。T1继续原v3数据/数组CPU范围；将固定本地Qwen文件验证、延迟loader和LoRA参数身份拆为独立 `model_io/qwen_model.py`，供后续训练和推理共同使用。此接口不依赖变化中的数据适配，因此可以在最多两个实现任务内并行推进；不提前实现训练循环、评测生成或扩大GPU许可。[任务](tasks/P04_QWEN_MODEL_CPU.md)、[固定metadata](../configs/qwen-models.v1.json)、[原字节与冻结证据](../reports/S0_P04_QWEN_MODEL_CPU_PREPARATION.md)。

两个已在本机的原模型及现有库/源码由S0固定，metadata只绑定身份、不提供执行许可。明确区分311个序列化BF16 tensor、sanitize后的预期310底座叶和112个LoRA A/B；记录双EOS及原采样默认值。E1仅做CPU测试与有限真实文件hash/header核对，不导入框架或反序列化tensor。T1当前 data_v3.py 与旧公共代码/配置不变，不要求T1提前消费E1候选。两包分别经R1与main验收后，T1真实runtime应复用此共同接口，避免另写加载/adapter身份逻辑。旧只读方案作为历史提案保留，新所有权以本ADR和完整任务授权为准。

R1按两包完整候选的实际交付和资源状态逐包接续；仅在各worker原生终态后分发精确候选。S0后续冻结容量与运行配置；本包模型/框架/GPU/新编码和正式训练额度为0，原费用、隐私与单一共享租约边界保持。

## ADR-0028｜容量诊断先固定同例前向与数值判定

日期：2026-09-08；状态：仅计划已冻结，无运行授权。当前R1审模型CPU、数据修订r2 READY；两个包及后续原生runtime仍须独立R1/最终CI/main。S0将已接收方案的64例次诊断上限收敛为[固定60例次清单](plans/P04_QWEN_CAPACITY_DIAGNOSTICS.v1.json)，沿用原23例cohort，原15例/8+7与前8例重复8遍保持79微步/10计划更新。该清单在任何新模型输出前固定，见[元数据证据](../reports/S0_P04_CAPACITY_READINESS.md)。

raw validation8、raw/零LoRA的padding两对共4、step2/10/reload各16，逐个绑定原rank/数据身份；padding对照取已选1536 bucket中最长且实际有padding的原例，不扩大23个唯一例。CE、同例重载、冻结底座/adapter身份和过拟合阈值按计划固定；未列4次不作为调试/重试额度。失败须保留并按具体原因调整后续独立范围，不能看到输出后改阈值或增步凑PASS。

本计划与cohort都不是运行配置，实际编码/框架/模型/GPU/优化0。T1后续CPU实现保存并只用原创模拟验证规则；未来S0运行授权还须绑定已验收runtime源码、实际23例数组、单一物理GPU租约及准确wall/RSS/MLX/swap/制品预算。grad_checkpoint固定False、native compile保持，与原方案相同；旧toy/P01守卫不修改，完整smoke/formal不继承容量adapter。

## ADR-0029｜固定CPU运行规则与后续实际授权分别绑定

日期：2026-09-08；状态：CPU规则已冻结，任务PLANNED未派发。精确配置 `configs/sft-qwen-runtime-cpu.v1.json` 为24,039B，SHA `fa9e52b4f91be9e7d3a444df95229120204fdfb408521c42ef91e916ec605875`；见[准备证据](../reports/S0_P04_QWEN_RUNTIME_CPU_PREPARATION.md)。模型CPU主干已验收，数据CPU仍待d806独立R3及最终CI/main；满足后才给T1正式code_base和固定输入。

采用已接收方案的1583/5938单遍rank、198/743更新及固定容量79微步/10更新/60诊断前向规则，保留原生compile及grad_checkpoint=False、Adam和分段连续状态。CPU包只实现接口和原创模拟，不将这些计划数写成真实完成。真实609输入、13材料、23例编码、模型/框架/GPU额度全部0。

后续数组准备和数值运行使用分别冻结的S0 grant；预期grant hash必须从可信调用方提供，文件不能自我授权。数组只允许固定23例cohort或完整已批准profile；数值grant绑定已验收代码、数组、输出owner、启动与调用reservation及无默认值的资源预算。两类active grant目前都为空，所有旧training_authorized=false逐字保留。CPU worker不得靠改生产常量或跳过验证启用运行。

GPU child先无框架验证固定来源及输入、持物理租约，经已审loader环境检查和实际加载后才导入trainer/optimizer，seed仅在LoRA初始化前一次。监督记录采样最大值及实际同步更新，未知进度保持unknown；不宣称覆盖瞬时峰值或把yield等同完成。全部真实调用、容量验收、正式SFT、评测与部署另按证据登记。
