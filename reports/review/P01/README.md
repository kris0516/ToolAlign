# P01 完整候选独立审查 r1

2026-09-06；reviewer R1，独立 App 任务，gpt-6-astra / max。**结论 FAIL：P0=0、P1=2、P2=1。** 被审候选为 `59b3802c81aa6eceaf3609af88f288756bcb1581`，不得以本轮回归或历史功能实验通过代替候选验收。

| 身份 | 精确提交 |
|---|---|
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| R1 范围授权 | `52f9c57a50eaf580a1a90bc5c4b8bd028c83b903` |
| T1 同步授权 | `f2a271be616cdb53c01e8d671029f31ae140c037` |
| 候选中的非强制 merge | `17a003f2678682fd3c6a072eba2b105fafc87102` |
| 原完整候选，保留 | `f97bb0de346c220871962a5689014a379fe19c83` |
| 原实现/证据工具 | `eed03e88d5cc88f6db8b3845f2e7d5c9967c9c02` |

审查分支 `review/p01-r1` 从精确候选建立。契约为 plan-v0.1 / coordination.v1 / toolalign.contracts.v1；读取授权中的 AGENTS、P01 完整任务、PROTOCOL、PROJECT_STATUS、GOAL，以及训练、Apple Silicon、冻结契约、资源锁和验收规格。所有旧审查分支保留。R1 仅新增本目录与 [交接单](../../../coordination/handoffs/P01-review-r1.md)，没有修实现后为自身签通过。

## 完整范围与分项结论

审查覆盖相对同步授权的全部 **27 文件、6,516 新增行**：8 个实现模块、2 个 P01 测试文件、原始及 base-r2 硬件报告/JSON/脚本、两份 T1 交接；同时核对来自 S0 的协调/集成差异。相对生产 base 共38个变更文件。155个候选追踪文件逐一与候选 Git blob 比对，字节未变。P01 旧21个交付文件与 f97bb0d 全部相同；公共 pyproject、uv.lock、契约锁与生产 base 字节一致。

| 分项 | 本轮验收结论 | 证据与范围 |
|---|---|---|
| G1(SFT) | **FAIL，F1待修** | 受限 MLX-LM SFT 的历史加载、训练、保存重载和容量证据可核验；通用监控异常终态仍不完整 |
| G1(DPO) | **FAIL，F1/F2待修** | 唯一备选的限定功能实验有证据，但门槛失败会漏记已完成更新；reference仍是sft_smoke |
| 首选 mlx-tune | **FAIL** | 保留原生 BF16 初始ln2失败；未执行其正式训练更新 |
| 唯一备选功能实验 | 历史受限结果得到支持 | mlx-lm-lora 3.1.2、显式mask、全进程禁编译、冻结完整SFT reference；1536/2048另开原生DPO checkpointing |

上述 G1 状态是当前候选的独立验收意见。它不把历史成功运行改写为算法失败，也不把历史运行说成 R1 新执行的模型实验。

## 问题、复现与最小修复

### F1 · P1 · 监控异常遗失运行终态

位置：`src/toolalign/training/compatibility/execution.py:355–378`，并涉及386–426行的清理及终态写入。

`sysctl` 返回非零或非整数会产生 `CalledProcessError` / `ValueError`。这些异常经 finally 终止、升级kill并回收自有child后继续传播，跳过后面的 `resources.json` 和 run manifest 终态写入。已有 `run.json` 保持 `status=running`、`ended_at=null`、`exit_code=null`；报告生成器又会跳过没有resources文件的目录，导致负结果未进入汇总。

[进程探针](test_p01_processes.py) 使用一个真实、拒绝SIGTERM的惰性CPU child，记录其PID、创建时间及父进程关系；只替换压力读取与模型启动目标。两个错误场景均复现残留running manifest。正常pressure/wall停止均返回124；SIGKILL后 `waitpid` 确认child已回收。测试只缩短清理宽限期，不运行模型或实际GPU作业。

最小修复：在监控失败的异常出口保存可区分的失败原因、真实child退出码、资源记录与终止manifest，完成清理后再返回/传播失败。不能以取消等待代替回收，也不能把不可读压力当正常压力。**阻断合并，适用于SFT与DPO入口。**

### F2 · P1 · ln2失败漏记已完成的训练工作

位置：`src/toolalign/training/compatibility/fallback_probe.py:182–186`；进度与逐步日志在188–205行才写入。

已核对的上游 `mlx_lm_lora/trainer/dpo_trainer.py` 在累积边界先调用 `optimizer.update`，随后求值state并调用训练回调。候选回调在记账前检查ln2。因此第8微步的loss若越过门槛，DPO更新已经完成，回调却直接抛错，遗漏该微步、监督/处理token、实际optimizer计数和具体失败loss。

[原回调隔离探针](test_p01_failure_counters.py) 从被审文件逐字提取Callback类，以CPU依赖替身供给其闭包变量。正常ln2对照通过；第8步注入已出现过的 `0.6945998072624207` 后，真实上游顺序对应的optimizer已到1，而回调仍保留39总微步/4次SFT更新，未记录40总微步/5次总更新。这是**原回调CPU单元证据加已测上游源码顺序**，GPU故障注入为NOT_RUN。

最小修复：失败门槛不能抹去已经执行的工作；先可靠保存实际loss、计数与失败事实，再终止。保持首次真实累积周期逐步ln2检查与2e-6门槛，不用预检替代，不修改原失败数据。**阻断DPO验收。**

### F3 · P2 · math-r2源码来源说明不准确

位置：`reports/hardware/P01_REPORT.md:23`，以及按Git HEAD定位math-r2实现的说明。

原配置如实记录HEAD `aaab75ed5d993f9354f11f74b58edb67d0af45c3`，但其 `numerical.py`、`model_probe.py` 的文件hash不等于该提交的blob。R1已证明**全部8份实际源码hash**完整对应后续 `47c03404bab043e85b417cd8a6d0432dc2f85479`。实际numerical文件也与本候选字节相同，其hash为 `72e1ec30655c4b0bfdff601eb0555fe21d90f3d8936a01f1e051740f22cc8af1`。

应明确这是当时HEAD上的工作树代码，并登记可恢复的源码提交映射；保留原HEAD、source_hash与raw文件。单纯checkout aaab75e无法复现新增的实际备选梯度检查。由于完整源码已经恢复，本项不单独阻断，也不据此请求无必要的GPU重跑。

## 独立证据与实际计数

完整命令、UTC、退出码、日志hash、34项CPU环境清单和审计输出在 [evidence.json](evidence.json)。原始日志只留R1私有目录。索引中的 `<T1_WORKTREE>` / `<R1_WORKTREE>` 替代具体本机路径；未提交原始训练记录、权重、token表或原始日志。

- 适用pytest **217通过** = 58基础 + 41 P01 + 46 P00首轮审查 + 72 P00-r2。历史274中的57项旧shared01结构快照未修改、未计作本轮通过。
- 新独立pytest **4通过、3失败**，对应F1两个场景、F2一个场景。早期同类探针结果保留，不重复相加。
- 新的17组PyTorch float32 CPU数学对照通过；CE loss/梯度最大误差为 `4.0115702804e-7` / `1.9054780642e-8`，DPO为 `8.2231399690e-8` / `3.6295686907e-9`，均小于2e-6。独立stdlib log-sum-exp/解析梯度验证mask、右padding、reference无梯度，以及policy/reference同一tensor时仍保留正确policy梯度。
- T1的base-r2 PyTorch CPU参考脚本在R1新环境实际通过，stdout SHA与T1记录相同。没有调用会导入MLX的完整math入口。

### 历史模型证据只读复核

[独立审计脚本](audit_p01_evidence.py) 未调用生产的token/mask、loss、reference、计数或报告转换函数。它以stdlib、Jinja沙箱和tokenizers处理固定本地文件，完成：

- 10次run的原配置、source hash、日志、185项冻结manifest制品逐项path/size/hash核验；27份原CPU/基线命令日志核对argv、时间、退出码和完整hash。
- 两套公开原模型文件及本地Hub revision/LFS metadata核对。按safetensors头和1MiB流式字节块计算array hash，不构造模型或权重tensor。每个模型run的310个冻结底座array与原文件字节对应；112个声明LoRA array涵盖28层Q/V，保存的SFT adapter与记录的after hash一致，已有DPO adapter也只有对应112个array发生变化。
- 全部256条样本重新渲染并联合tokenize prefix+completion，再核对single EOS、每个token ID/mask、完整history/observation不监督、长度与chosen/rejected共同prefix。容量样本保持完整内容，且是原创synthetic train-only内容。
- reference的底座、adapter、tokenizer、模板及按历史版本登记的source/dependency/compile/checkpoint身份与cache key对应；不是disable adapter后的原始模型。DPO后全reference参数/输出与跨库forward重载的一致性，属于已绑定源码及raw结果中的历史运行证据，未伪称本轮重跑forward。
- 独立重算每微步的监督/逻辑处理/非padding token、累积8的optimizer次数、8暖机与104可测SFT步、均值/样本标准差、checkpoint I/O分项。旧无效smoke06-r2使用共同padding，最终通过配置使用各自长度；审计按实际历史源码区分口径。

生产汇总脚本另在R1目录重建结果，输出与原 `P01_RESULTS.json` 逐字节相同：`d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。该同源重建是辅助核对，不替代上述独立检查。

### 运行结果与限制保持原样

| 历史run | 证据结论 |
|---|---|
| math-r1 | 早期未提交工作树检查，仅保留历史，不作为最终数学证明 |
| math-r2 | float32数学及真实备选函数梯度历史结果可核验；源码映射见F3 |
| smoke06-r1 | 首选BF16初始loss 0.9140625超出ln2±0.02；SFT32/4、DPO0 |
| smoke06-r2 | raw PASS及退出0保留；实际首周期0.6945998/0.6798114，汇总降级FAIL_TRAINING_PATH_LN2 |
| smoke06-r3 | 退出2，reference score gate失败；具体差值NOT_CAPTURED |
| smoke06-r4 | 限定SFT32/4、备选DPO8/1；真实首周期8个loss均0.6931471824645996 |
| calibrate17-1024-r1 | SFT112/14、DPO8/1；8暖机+104可测SFT微步 |
| calibrate17-1536-r1 | pressure=2于约159.98秒停止；退出124、child -15，swap增长33,161,216bytes；已记录SFT112/14、DPO0；不是MLX OOM |
| calibrate17-1536-r2 / 2048-r1 | DPO原生checkpointing开启后受限通过；各SFT112/14、DPO8/1 |

三档最终SFT平均约0.559896/0.886035/1.480036秒/微步；MLX peak约17.649/14.435/17.987GiB，与RSS/系统pressure分别计量，不能相加。1024与较长两档checkpoint配置不同。112微步不等于112次更新；短DPO8微步不能证明稳定正式吞吐。每请求最多32新token的两次小生成不证明256-token完整harness或长时稳定性。

### 已测上游与当前发行包

三个候选库11份关键源码实际hash与公开身份表一致；分别核对MLX-LM和备选的shift、float32 CE/summed logps、梯度累计后除8一次、声明参数更新、冻结reference和实际loader。首选ref_model未被相应训练路径使用、accumulation未应用的判断维持SOURCE_ONLY；未执行其训练器来制造更新次数证据。只选择一个备选。

当前worker在持GPULease的operation内os._exit；CPU异常探针证明failure序列化期间仍持锁，退出后释放。上游wired setter只在局部上下文被抑制、finally恢复。全进程编译模式与reference一致；checkpointing配置纳入后期reference身份。F1/F2指出的异常记录缺口仍须修复。

新两环境实际metadata为69/90 distributions，分别64/85 runtime +4 dev-only+项目；已有runtime版本与旧88包探索环境一致。完整重放仍需p01-replay，不能把mlx-tune审计依赖变成已验收算法后端。默认CPU导入不引入模型库。第三方许可不一致与平台调查沿用已验收共享证据，未重新调查或重标许可。

R1实际构建及验证的sdist为110,865bytes /47文件，其中46项追踪字节相同；wheel为44,037bytes /27文件，其中22项追踪字节相同。SHA分别为 `f74cd964bec2af10f673ac5104a88b9162a7cd27fb4a5e6398a9be621424c508`、`043e5d4508704d5637f7a9fef20dcb236c5223649def73b832750fa94dabd69b`，与T1新基线产物一致，未追踪payload均0。全部8个P01模块和冻结schema在包中。[独立安装核验](verify_p01_package.py) 在默认CPU隔离环境导入全部P01模块并运行CLI帮助；原P00五类契约CLI也通过。原共享241个private canary/18个public对照与三种归档路径检查通过，脚本未改。

## 本轮失败记录与NOT_RUN

保留所有失败日志。除F1/F2探针和F3来源断言外，R1自身有两项已纠正的检查错误：安装时误带P02的tokenizers0.22.2，被P01锁0.23.2拒绝；以及最初把最终无padding计数规则用于旧smoke06-r2，核对45f4670源码后改为其真实共同padding规则。二者不归因于候选实现，不伪装为首次即通过。

R1新环境与缓存实测约1.27GiB，低于2GiB授权；小张量最多2个CPU线程。未在T1工作区执行写入命令、修改raw状态、复制权重、导入模型/MLX或占用GPU。

最终公开内容扫描覆盖163条索引/工作树路径并通过；范围核验确认仅新增8个授权审查文件，155个候选文件字节未变，P02旧审查分支仍指向原提交。公开扫描是启发式检查，另已人工核对新增内容仅含原创探针及去敏元数据。

**NOT_RUN**：R1模型/GPU重放、GPU故障注入、完整锁环境MLX/Torch math replay；P04/P05正式训练、accepted_sft reference、kris至少10条token/mask人工核对、P02数据语义人审、正式偏好生成、P03完整harness、256-token协议、BFCL/最终测试、长时热/功耗稳定性与服务部署。P02人审由kris/S0另行推进，R1不代签。

## 决议

请S0退回F1/F2最小实现修订，并同步修正F3来源说明；保持原始失败与历史制品。本次未发现必须申请GPU才能决定的疑点，因此没有GPU预算申请。修订后的精确候选需重新独立审查；本报告不授权进入P04/P05，不自行合并main。审查提交以本文件所在Git提交及R1原生回报的精确SHA为准。

## 命令日志索引

完整argv和UTC见evidence.json；下表列实际退出码与完整日志hash。失败项含义见前文。

| 检查 | 退出码 | 完整日志 SHA-256 |
|---|---:|---|
| core-sync | 0 | `c1eb46aab57925fbaef75de85964c75d5d8bb98e98d5545c9fbf68c22c9fc957` |
| cpu-regression | 0 | `3eff019f765a9a5c901fb70ec70f80ae9b785e2e880a310a3357964b153af673` |
| locked-cpu-constraints | 0 | `9a9d7a368ef01b18828ac4f18da14d41bad455e2ca3c858ea11cbfcf8081594a` |
| cpu-venv | 0 | `e47600c53b417ea33c0627f97fd148f2684c074822d6bbe130919da5d168b5be` |
| cpu-install | 1 | `3811d56bb19b49977228f41d97a9efdbc45f7a93aa699485221b29800c2d6783` |
| cpu-install-locked | 0 | `2d00fa80c433e2195e5893d8ad530e58e75e3e32b091f09928ee88070d5f2466` |
| supervisor-probes | 1 | `b28c87b03484e38176746ecb4ea8d5bd67e3a8c30fb95452ff0773090aace18b` |
| locked-torch-reference | 0 | `596d33ee397ff90ee0a32090fb127c1627e411a7904184df0d9105187582ad3a` |
| independent-cpu-math | 0 | `17307b5921a3e9089effd2d824e287b872ce23ea8e2a0b0fe6522f3cea8cc26e` |
| historical-evidence | 1 | `7cddbb5b6451f892c6260f711a5bb10c3c34113ae26d92ace5a7c14a88a296c6` |
| contracts-freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| historical-evidence-resolved-source | 0 | `bb818421529398aa175e34c72352e22b2938830bc1d7c8ed3fd53ba4703a3599` |
| independent-failure-probes | 1 | `915869a915dfe6a791b0aac32a761324c405a850ba43fa4dfe662e62468907fa` |
| actual-package-build | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| source-distribution-boundaries | 0 | `2fe77a49ef2ca6f59664fa6e47bc8ad9043c4224616dd51b361b2b08e40fae87` |
| isolated-wheel | 0 | `390edb43abaaf483f0ae93ff2d1a28e1f58a6aa7bc9353ab8a2f95dff03e8f37` |
| rebuilt-worker-summary | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| p01-archive-and-installed-modules | 0 | `fe9038ea66292842050d73dd7368272718b7d01e16768a980d3667514befc3c9` |
| final-historical-evidence | 1 | `1f919e75713080814dc7bf33433e41e3603c61477d24c76435a897f35ce4f4ea` |
| final-lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| complete-historical-evidence | 0 | `4eef09e75863260bde52eebdc65ca059377b144ac6f73ecd0e7a364f8c7086cc` |
| release-lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| public-content | 0 | `15257e072358989f5ac4fbb3ee53704447d20505e87a8e8cd9ddc5282a424176` |
| final-scope | 0 | `632b3e06c8ef7df766c9a12a0cb2c2b9b96c00fc1613de0281f8124dde6e148e` |
