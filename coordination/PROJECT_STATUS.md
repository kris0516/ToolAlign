# 项目真实状态

更新：2026-10-26（Asia/Shanghai）。当前入口：[toolalign.md](../toolalign.md)。G3验收已随PR27合入主干 `1267d1a33dfb08bfd9800b80ea97315730748952`，双Python CI 40295329527全部成功；实际SFT执行源码为PR26 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。当前唯一协调者S1，G1–G3已完成，G4开始CPU实现；后续模型运行使用Colab GPU。

| 阶段 | 已支持的结论 | 关键证据 |
|---|---|---|
| P00 | CPU 基础包、冻结契约与互斥 VERIFIED | [main 验证](../reports/P00_MAIN_VERIFICATION.md)，PR2 |
| P01 | Mac 受限 SFT 与唯一 DPO 备选兼容通过；首选 DPO 原 FAIL 保留。这是原平台结论 | [main 验证](../reports/S0_P01_MAIN_VERIFICATION.md)，PR6 |
| P02 | 冻结 v3 数据、来源处置、13 例材料通过技术与 AI 质量审核；G-DATA PASS | [技术 main](../reports/S0_P02_QUALITY_V3_MAIN_VERIFICATION.md)、[Q1](../reports/S0_P02_Q1_V3_ADJUDICATION.md)，PR15 |
| P03 | CPU 工具、oracle、scripted 执行器 VERIFIED；模型评测未运行 | [main 验证](../reports/S0_P03_MAIN_VERIFICATION.md)，PR7 |
| P04 准备 | CPU collator、MLX 原创 toy 数值、固定 Qwen CPU 接口通过 | [CPU](../reports/S0_P04_SFT_CPU_MAIN_VERIFICATION.md)、[toy](../reports/S0_P04_SFT_NATIVE_TOY_MAIN_VERIFICATION.md)、[模型接口](../reports/S0_P04_QWEN_CPU_MAIN_VERIFICATION.md)，PR10/11/17 |
| P04 v3 接口 | R1-r3 PASS；PR19 已合并，main 定点 163 passed | [main 验证](../reports/S0_P04_DATA_V3_MAIN_VERIFICATION.md) |
| P04 真实 v3 消费 | 当前接口一次 prepare 与13例数组转换/导出/回读 PASS；0新编码/模型更新 | [S1消费记录](../reports/S1_P04_DATA_V3_CONSUMPTION.md) |
| P04 CUDA CPU 实现 | 4342af8 经独立R1审查 PASS；17项定点检查及独立数值/恢复通过，真实CUDA待运行 | R1原审查提交 `7d460f2054201c00055a1f924c5c4984be8e6988` |
| P04 CUDA mask 预审 | 13例真实材料与CUDA消费者对应PASS；423项检查、26条原证据绑定通过 | [Q1预审](../reports/reviews/P04_CUDA_MASK_Q1_R1.md)，`82f1e88` |
| P04 Colab CPU 控制 | r3独立PASS；两项控制问题均关闭，S1原失败上下文5项定点检查通过 | [R1-r3](../reports/reviews/P04_COLAB_ENVIRONMENT_R3.md)、[S1集成](../reports/S1_P04_CUDA_INTEGRATION.md) |
| P04 CUDA 容量输入 | 主干920c415的20条编码/回读PASS；独立Q1 531项检查通过，13例身份不变 | [Q1增量](../reports/reviews/P04_CUDA_CAPACITY_ARRAY_Q1_R1.md)，`ed022da` |
| P04 Colab 真实安装 | PR22锁在L4真实安装PASS；48包/pip check通过 | [实测](../reports/S1_P04_CUDA_CAPACITY_R1.md)，原安装失败保留 |
| P04 CUDA容量/恢复 v1 | 最长2048 token三步容量PASS、采样峰值5180MiB；新进程恢复后更新超容差，跨实例未运行 | [实测与数值FAIL](../reports/S1_P04_CUDA_CAPACITY_R1.md)；两份输出已回收，实例已停止 |
| P04 CUDA恢复诊断 | 新实例初始状态严格一致；同进程重复backward差异约0.86%，关闭checkpointing仍存在；零更新 | [实际诊断](../reports/S1_P04_CUDA_RESUME_DIAGNOSTIC_R1.md)，29文件已回收、实例已停止；不构成更新恢复PASS |
| P04 CUDA确定性v2 / G2 | 验收PASS；实际三步、新进程及新实例恢复1,883项通过，672个张量比较差为0；R1/Q1独立终验通过 | [实测及接纳](../reports/S1_P04_CUDA_V2_RECOVERY.md)；65文件已回收、实例已停止 |
| G3 原始验证 CE | CPU实现及独立技术审核PASS；8项实现检查、4项独立检查通过，未改变SFT选模 | [R1审核](../reports/reviews/P04_CUDA_SFT_BASELINE_R1.md)，候选c633bd7、审核fd4ad07 |
| G3 完整输入数组 / Q1 | ACCEPTED；两个profile共7,928行逐行核对通过，原13例材料身份不变 | [Q1完整数组审核](../reports/reviews/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)，`98cf0e1` |
| P04 正式 SFT / G3 | 独立验收PASS；198/743次更新完成，验证CE为0.041494/0.024438；R1 300af3f、Q1 34331c2已接纳 | [实测与曲线](../reports/S1_P04_CUDA_G3_SFT.md)；196文件已回收，实例已停止 |
| P05 偏好与 DPO / G4 | 生成/偏好CPU及Q1语料r2已接纳；首批生成计划冻结；E1实现DPO | [G4协议](tasks/P05_G4_PROTOCOL.md)、[Q1语料审阅](../reports/reviews/P05_G4_CORPUS_Q1_R1.md)、[DPO任务](tasks/P05_G4_DPO_CPU.md) |
| P06–P09 | 模型对照、正式服务、最终复现与研究交付未完成 | [评测规格](../docs/04_EVALUATION_SPEC.md)、[审核规则](REVIEW_POLICY.md) |

89项问题全部关闭。Q1-G4-CORPUS-001经两条提示的JSON字符串约束修订及Q1独立r2 PASS关闭，连续未通过计数1→0，首次REQUEST_CHANGES保留。CUDA-RESUME-001经R1 `be756a1` 的实际完整恢复独立验收关闭，正式修订失败计数0；Q1 `847e0be` 已确认数据身份与说明范围。原FAIL和全部失败历史保留。数据质量、CPU、toy或容量PASS都不是正式模型效果。

## 原 S0 交接记录

合入已独立审查的 PR19；重写接续入口，转向 Colab；复用另一项目的 CLI/ADC/SSH/tmux 方法；整理本地技能；清理停用训练环境与可再生缓存。本机清单在 `.toolalign-local/handoff-2026-10-26/`，公开摘要见[整理记录](../reports/S0_COLAB_HANDOFF.md)。

该次交接没有新模型下载、GPU实例、训练、偏好生成或正式评测。其后S1完成的CUDA实测以上表为准。

## 当前接续

S1 已与 S0 完成协调权和证据交接，冻结数据、来源根及模型缓存已定位；G1准备完成。G2通过当前接口读取真实v3数据，完成CUDA实现、锁定环境和实际容量/恢复；独立审核均已接纳。

按 [GOAL](GOAL.md)依次推进。G2的v2三步容量、新进程和新实例恢复已通过R1/Q1终验；1,883项S1检查通过，672个adapter/Adam张量比较差为0，原v1 FAIL及诊断保留，详见[G2报告](../reports/S1_P04_CUDA_V2_RECOVERY.md)。

G3实际执行PR26主干 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。0.6B/1.7B均完成冻结一轮SFT，完整验证CE从0.739884/1.145230降至0.041494/0.024438，选中step198/743。10段恢复链、941次更新、游标及选模已由S1核对；196文件已回收，唯一L4实例已停止，累计占用9,124.538896秒、余额观测差3.85 CU。[R1技术终验](../reports/reviews/P04_CUDA_G3_FINAL_R1.md) `300af3f` 与[Q1数据及说明终验](../reports/reviews/P04_CUDA_G3_FINAL_Q1_R1.md) `34331c2` 均PASS，S1已回读接纳；PR27合并后G3 App goal实际complete。

G4 App goal现为active。T1交付d1aa1c8，170项受影响检查通过、2项既有pip parser检查跳过，最终回收修补另有18项通过；D1交付147d045及938c471，42项测试、32正向/20反例CPU轨迹通过。实际新语料为20个train任务、12个family、10类别、1个共享工具/schema连通组；完整recipe和原始材料留私有。S1回读源码与证据身份，并通过1项生成恢复到偏好提取的组合检查。固定tokenizer预检中，初始输入最长1,351、scripted轨迹输入最长1,742 tokens，预留256均在2,048上限内；不代表真实生成不会遇到更长历史。

R1提交 `fac9ec5` 对生成与偏好CPU实现均PASS，新增实质问题0；4项独立CPU检查覆盖实际输出到提取、上下文边界、传递分组隔离及外层控制器对真实owned child的回收。S1已回读27份审核证据，当前生产/测试/配置/依赖与受检源码逐字节相同，接纳两包CPU实现。Q1对固定20题的生成前语义/分组审阅r1为REQUEST_CHANGES：18题通过，第10、13项未明确版本答案须为JSON字符串，独立反例确认同值数字被判失败；分组和v3根绑定通过。S1已核对Q1提交 `fd0e8f3` 及30份私有证据，接纳问题Q1-G4-CORPUS-001；D1候选 `76e114f` 已补充两题类型要求及约束依据，4条定点轨迹通过；S1核对34份文件和实际差异，其余18项内容/全部答案策略保持，group身份传导已记录。新tasks SHA `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015` 经Q1 `5044029` 定点复审PASS，S1回读38份证据后接纳，旧包和原FAIL保留。两题的8条脚本请求tokenizer检查最长1,755，含256预留在2,048内。正式偏好池审核另行执行。E1继续独立TRL依赖、原生DPOTrainer与完整恢复的CPU实现；R1生成审查已通过，S1解除控制器三文件保留。G4总上限仍为128任务×4候选、全部GPU分配累计21,600秒/12 CU；本批20题最多80条真实候选，先前12条pilot、按原顺序续跑未启动ID，生成分配上限5,400秒；见[生成计划](../reports/S1_P05_G4_GENERATION_PLAN.md)。具体run待绑定合并主干与实际分配时间。目前未分配G4 GPU，真实候选、DPO、模型语义评测和服务仍NOT_RUN。

完整历史见[迁移前状态](https://github.com/kris0516/ToolAlign/blob/abdc53d468a270cc1bfecbe56980dd34918480e1/coordination/PROJECT_STATUS.md)和各阶段报告。旧 Mac 包的“待派发”状态不覆盖新路线。
