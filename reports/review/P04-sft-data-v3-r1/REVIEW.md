# P04-SFT-DATA-V3-R1 独立技术审查

**FAIL；P0=0、P1=0、P2=1。** 审查对象为完整 candidate `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`（tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`），生产基线 `48be4352bbad53ced5af84186edac036dd0ff2ca`、实现 checkpoint `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`。独立 Codex-AI(R1) 使用 gpt-6-astra/max，按完整授权 `4ea69e1339c6b0efb14d0149b77b2442601ddd9c`、plan-v0.1、coordination.v1、toolalign.contracts.v1 和 ADR-0026 审查。结论冻结于该候选，未修改被审实现或纳入后续修订。

## F1 · P2 · 非普通文件在类型校验之前阻塞

[`data_v3.py:90–92`](../../../src/toolalign/training/sft/data_v3.py#L90) 先以 `O_RDONLY | O_NOFOLLOW` 打开输入，再以 `fstat` 检查普通文件。对没有 writer 的 FIFO，`os.open` 会等待 writer，普通文件检查和 hash 检查均无法执行。`prepare_v3` 的配置、manifest/成员以及数组回读共用这个读取函数，因此异常本地路径能够使受限 CPU 入口一直等待，违反本包对文件类型的拒绝边界。

原创[最小探针](probe_nonregular.py)仅创建一个权限 0600 的空 FIFO；child 在完成导入并报告即将读取后，超过一秒仍未退出。信号栈定位到上述 `os.open`。parent 随后打开并关闭空 writer，未写入任何数据，child 才抛出 `v3_regular_file_budget`。探针最终 exit=1，child exit=0 且已回收；原 FIFO 保留，仅以 `lstat` 封存类型/权限/inode，不打开或计算其内容 hash。

修订应让非普通文件在任何可阻塞读取之前及时失败，同时保持对实际打开 descriptor 的 `fstat` 校验以及 no-follow、大小/hash 和路径边界；只增加一次提前 `lstat` 不能独自消除检查到打开之间的替换窗口。复审需证明无 writer 的 FIFO 能及时拒绝、不会遗留 child，且正常普通文件读取和既有拒绝边界保持。F1 是本次唯一阻断项；问题台账与连续修订计数由 S0 登记。

## 已验证的范围

候选相对生产基线只新增 6 个授权文件；618 个候选文件和原 612 个基线文件逐字绑定，原 data/config/CLI、collator/plan/model_io、v1–v3 生产器、toy/runtime、依赖与 CI 保持。新配置逐字匹配授权 SHA `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。

首次 intake 核对 11,572 个文件路径、370 个链接、16 份授权、609 个固定输入（603 原引用和 6 份共 320,921 bytes 的副本）、40 条 T1 原命令及实际归档。独立固定消费使用一次离线、无依赖安装的新 target；外部 cwd、`-B -I -S` 和明确绑定的既有默认依赖验证了 65 个包文件与 32 个已载入 ToolAlign 模块的来源，无源码回退。

| 独立验证 | 结果与界限 |
|---|---|
| 与改动相关的既有测试 | 135 passed；未重跑历史 HF、真实 tokenizer 或原生 toy 数值组 |
| [原创反例与正常对照](test_adversarial.py) | 27 passed；包括同 group 的另一来源保留、三代 rank/原行、EOS/shift/右 padding、严格数值类型、token_texts 与 Q1 绑定、重算摘要后的 provenance 变更、部分发布和错误 consumer |
| 非普通文件探针 | F1 复现，exit=1；不属于上述通过测试 |
| 固定安装版调用 | `prepare_v3`、v3 verifier、13 例 rebind/export/readback 各 1 次；均成功，无剩余额度 |
| 四个 view 的独立逐行核对 | formal 5,938/213，smoke 1,583/194，共 7,928 个成员；逐原行、Example/sidecar、split/group 与 v1/v2/v3 rank 核对，有效全集 7,419/230 |
| 固定材料与磁盘回读 | 13 个唯一例、双引擎 26 条完整记录；类型、Example/Action/messages/audit、P/C 文本、全部 IDs/attention/loss/causal 数组、EOS/padding 和所有 token_texts 逐项核对 |
| 既有来源链 | 11 个沿用例、2 个新例保留各自 producer/run/source/Q1 记录；3 个 protocol fixture 不进入四个 view，重新封装没有登记为新编码 |
| 一遍 CPU 计划 | smoke `197×8+7=198`，formal `742×8+2=743`；实际模型更新 0 |
| 归档 | 直接 wheel、重建 wheel 各 70 个成员，sdist 143 个成员；完整源载荷、metadata、entry points、LICENSE、RECORD 与原构建时点一致；R1 新构建 0 |
| 静态检查 | ruff 与契约冻结通过；最终公开扫描及提交/推送结果另在终态封存记录 |

安装版导出为 2,030,656 bytes，SHA `9b711be1ba6b301e6efb8c9853c0c6b98fdaa2db9db2e2cd2fa348739ca6ba0b`。独立读取磁盘数组后与原记录、转换出的 Batch 和期望完整绑定分别比较，结果也与 T1 已封存的两个成功运行一致。最终 test/ood/BFCL 的指定载荷仅 hash，没有创建内容 view 或用于构造反例。输出仍为 `REVIEW_ARRAY_ADAPTATION_ONLY`，`new_sequence_calls=0`、`optimization_authorized=false`。

## 原始运行与证据限制

逐条核对 T1 40 个 receipt/原生运行绑定、两种日志 schema 和 12 个源码时点；34 条字面命令与 6 条有限数组循环命令均可追溯。原生截断输出没有被当作完整日志，完整 stdout/stderr 以原文件核对。原 source/installed 首次失败、追加复测授权 `8c8aff8300bfa564db7d47be79e6c3f764360a8b`、两组实际归档及最终各一次成功的完整消费均保留。

首轮 source 失败没有持久化终态 counter，登记为 `ABSENT_NOT_RECONSTRUCTED`；traceback 仅支持其停止于 verifier 之前，不将推断写成实测计数。首轮 installed 失败有实测 `prepare_v3=1`、其余相关 API 为 0；后续 source 与 installed 成功记录各为五项调用 1 次。旧失败没有由新结果覆盖。

R1 自身的两次 intake 解析假设错误、一次原创 fixture 缺字段、两次原命令绑定脚本假设错误，以及一次封存脚本摘要抄录错误均保留原脚本、源码快照、stdout/stderr 和 exit；定点修正后相应检查通过。这些是 R1 检查脚本失败，不计作候选的额外缺陷，也没有触发新的实际固定消费。

证据封存核对 64,500 个现存文件、1,628 个链接、1 个 FIFO 类型记录及 1,189 项历史公开 Git 绑定。旧 989 个 scope 文件、571 个公开 Git/快照、根身份和私有历史提交保持；不同源码时点按对应 Git/快照验证。此前已登记的 30 个临时文件原路径和 1 个链接仍缺失，30 份等价内容与原封存及 S0 留存副本一致；没有恢复为原件或声称所有原路径仍在。

完整证据 seal 为 `cdd2a826a40066d2c570d83dfb862dc0e21b09392ef09fccb5e13bfc1ec006be`（20,426,676 bytes），去敏索引见 [EVIDENCE.json](EVIDENCE.json)。封存前本轮新增文件及四个独占外部目录共 91,761,661 bytes；seal、后续公开材料和提交日志另纳入终态总量，仍须满足 1 GiB 上限。最终封存还绑定本次报告、审查提交、普通推送及全部 child 回收记录。

本轮实际安装、固定 prepare 和固定 13 例转换/导出/回读均已用完一次额度；新环境、依赖、下载、归档构建、真实 tokenizer、全数据 build、框架、模型、GPU、优化、生成和 API 均为 0。G-DATA 的冻结 v3 批准保持其既定范围；本次 FAIL 不验收 P04 实际 trainer、容量、baseline/SFT、正式评测或服务。实际浏览器和真实模型训练均为 `NOT_RUN`。
