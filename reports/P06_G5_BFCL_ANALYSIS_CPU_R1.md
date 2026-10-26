# P06 G5 BFCL 与分析 CPU 包 r1

2026-10-27，E1。固定 BFCL 范围的 **150 题中，0 题可按当前冻结契约无损表达**，三类均为 `NO_ELIGIBLE_INPUTS`。所有题目都缺少契约要求的对象闭合声明；没有补加约束、扩展扫描范围或读取官方答案。本包交付官方评分接入、完整分母分析和排除证据，供 R1/Q1 审核。S1 可继续 L1/A1/A2 的独立验收；当前 L2 不产生模型计划或分数，也不需要分配推理预算。

授权基线为 `e580eb663b5658e611ce30a1bf7d1232ccba3917`，分支 `codex/e1-p06-g5-bfcl-analysis-r1`。范围为[任务包](../coordination/tasks/P06_G5_BFCL_ANALYSIS_CPU.md)及[G5协议](../coordination/tasks/P06_G5_PROTOCOL.md)。T1 reader/plan 使用该基线中的 `evaluation/cuda_eval/protocol.py`。本次没有真实模型加载或生成、GPU、训练、提供商 API 调用；M0/M1 正式结果和 M2 均为 NOT_RUN。

## 固定来源与筛选结果

源码、三个问题文件均固定 [gorilla f7cf7359b7ac615a0b294831c5ba2bc95ee4a000](https://github.com/ShishirPatil/gorilla/tree/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/berkeley-function-call-leaderboard)。私有源码目录保留上游 [LICENSE](https://github.com/ShishirPatil/gorilla/blob/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/LICENSE)；`source_identity` 核对提交及每个使用的源码/问题文件与 Git blob 的一致性，并保存 URL、SHA256、长度。公开仓库未复制官方题目、答案或 scorer 源码。

按文件原序各检查前 50 项，每类至多保留前 20 项。只允许参数类型拼写 `dict→object`、`float→number` 的可逆映射；函数名采用序号加名称的无碰撞映射，保存正向/逆向表。schema 字段和约束完整保留，不添加 `additionalProperties:false`、字符串/数组上界，不丢弃 `default` 或其他无法表示的字段。模型输入只有 messages/tools；外部声明不进入本地执行 registry。

| 类别 | 已检查 | 保留 | 缺少显式对象闭合 | 已知分组重叠 | 距 20 题上限 |
|---|---:|---:|---:|---:|---:|
| simple_python | 50 | 0 | 50 | 8 | 20 |
| multiple | 50 | 0 | 50 | 11 | 20 |
| irrelevance | 50 | 0 | 50 | 9 | 20 |

排除原因可同时成立。三类另分别有 22/32/26 题包含没有契约支持长度上界的字符串，2/9/6 题包含没有支持数量上界的数组；全部详细路径、字段和原因保存在逐题 ledger。150 个候选形成 111 个实际连通 component，其中 7 个 component、28 个候选触及旧分组。所有扫描候选都参与传递连接，包括本身 schema 不合格的桥接题。此审计使用现有 tool/schema、规范化 schema、词法 template 和 source 键，不声称穷尽语义重复。

隔离输入为 P02 **policy-a 分组 metadata**，manifest SHA256 `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`；仅读取经 hash 绑定的 assignments/tool-lineage，共 11,300 条、覆盖全部 split。未读取 P02 held-out prompt/答案。G4 为已接纳的 20 题 train 包，tasks SHA256 `b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`；P03 为公开 10 题开发 fixture。实际 metadata、G4 manifest 和开发文件身份均在 isolation.json 中。

固定 Qwen3-1.7B tokenizer revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` 已按本地字节核验。由于所有候选先在无损表达检查中排除，150 项长度均为 `NOT_APPLICABLE_UNREPRESENTABLE`，input_tokens=null；没有声称它们通过 2048 token 预检。对可表示输入的实现使用当前 prompt formatter，按 input+256≤2048 筛选，原创边界检查已验证 1792 可保留、1793 排除。

实际冻结 selection SHA256 为 `4014d0c8d3ca46dc2def17f32b38cc1bbb3b67f0889f0fd48820fa7e93b24b69`。私有 `selection/` 包含 source、isolation、tokenizer、selection 和 manifest；没有 inputs.json、官方答案或空运行计划。读取答案的独立入口要求已保存、hash 匹配且非空的 selection，然后按原始文件 ordinal 读取所选官方答案。

## 官方评分与分母

`OfficialScorer` 直接调用固定源码的 `_evaluate_single_ast_entry` / `_evaluate_single_relevance_entry`，使用真实 `qwen3-1.7b` profile，其 `underscore_to_dot=false`。本地接口仅严格解码原始 Action，并在评分前还原函数名；不实例化官方模型 handler，不改写 AST 参数匹配逻辑。未知工具名保留为调用，不能通过抛解码异常被 irrelevance 当作无需工具。

每个冻结 ID×M0/M1 均保留一行，包括 not_started/interrupted。每行保存原 raw_text、运行状态、独立 Action 合法性、完整官方结果、official raw valid、严格结果及门控原因。严格成功条件为 `status=completed AND parse_action(raw_text)合法 AND official.valid=true`；backend 声称合法不替代独立解析。scorer 未调用为 NOT_RUN、数值 null；scorer 异常另记 ERROR，不产生匹配值。

独立 Python 3.12.14 CPU venv 安装 [专用锁](../requirements/bfcl-scorer-py312.lock.txt)，默认项目/CUDA/SFT/DPO 依赖未改。依赖来自实际官方入口的 import 链，共 119 个包，不含 Torch/Transformers。首次真实 import 因 qwen-agent 的未声明 soundfile 依赖失败；保留原 stderr，仅补充该依赖后成功。最终 19 个原创案例调用真实 scorer，覆盖正确/错误参数、错误函数、多工具选择及多调用错误、合法 final/clarify/refuse、坏 Action、空输出、未知工具、超时、取消、基础设施错误、interrupted/not_started；包括“状态声称 completed、backend 声称 raw 有效但实际 Action 无效”的独立反例。调用期间 socket audit 记录 0 次连接尝试，模型框架模块列表为空。

真实 scorer 确认：坏 Action、空文本、not_started 的 irrelevance raw 分为真，严格结果为假；合法无需工具且 completed 才能通过。这验证了官方 raw 分与执行成功必须分别保留。AST 结果不代表 API 执行成功，也不称官方 overall。

## 分析接口和原创验算

`toolalign.evaluation.analysis` 读取 T1 batch、原始终态和固定输入文件，校验输入 hash、计划顺序、seed、condition、group 和每行身份，拒绝重复/外来行与变更后的输入。缺失终态补为 not_started，存在 started journal 时为 interrupted。replay 的 host 中断仍保留已经写出的单请求终态；未结束的后续请求保留相应状态。L2 另绑定独立 score artifact、source、selection 和原始文本。

L1/L2 分别报告 M0/M1 成功数/全部计划数、M1−M0 配对差及分类。L2 另报告官方 raw 指标。按真实连通 group 进行 10,000 次配对 cluster bootstrap，seed42，每次抽取完整 group，保留所有任务及任务权重；同时给逐组效应、leave-one-group-out。少于 2 组时两种不确定性分析均为 NOT_ESTIMABLE。区间描述当前 group 经验分布的稳定性，不估计总体覆盖或训练 seed 方差。

原创反例中，3 题的 +1 组和 1 题的 −1 组得到任务加权差 **+0.5**，95% bootstrap 区间 **[−1,+1]**；分别留出两组后的差为 −1/+1。单组只保留点估计。缺失轨迹计未成功；缺失 scorer 分数保持未知，不产生百分比。

L1 诊断复用 trace 与允许策略，记录 raw format、工具名/语义参数前缀、完成执行、未知工具、多余调用、恢复及预算耗尽。策略长度内但无法判断是否冗余的调用为 unknown。L2 保留官方综合错误；AST 通过支持工具/参数匹配，不能从失败明细拆开的项为 unknown，真实执行/恢复为 N/A。每项都带可判定分母。

A1 只取固定 recovery_task_ids，比较 M1 recovery on−off。A2 保留每个固定请求位置、原始输出相同/不同/未知、实际 prefix 命中及 prefill/TTFT/decode；失败请求也进入表。冷加载在 unit 资源表，预检和完整段时间单列，GPU allocation/CU 仍由 S1 controller 账目提供。token 缺失为 null，host RSS 与 CUDA allocated/reserved 分列；少于 100 个测量值的尾延迟标探索性。均值明确报告已知/缺失数量，不把成功子集均值当总体性能。

端到端原创 fixture 使用 T1 真实 owned child，3 个自造输入×2 条件共 6 行，实际执行 5 行、1 行未启动，5 个 child 全部回收。真实 scorer 对全部 6 行评分；M0/M1 严格均为 1/3，官方 raw 均为 2/3，单组区间不计算。4 个真实 fixture 失败覆盖 4 个类别/原因组合，索引全部保留，未补造 20 例。JSON、CSV 和质量—成本图均由 CLI 生成并回读；图明确标 `ORIGINAL_SCRIPTED_CPU_FIXTURE`、n=3、实际计时覆盖 3/3 与 2/3、unit 成本范围。这些数值仅验证处理链路，不是模型结果。

## 复算入口与交付证据

```sh
uv venv --python 3.12 "$BFCL_ENV"
uv pip sync --python "$BFCL_ENV/bin/python" --require-hashes requirements/bfcl-scorer-py312.lock.txt
PYTHONPATH=src "$BFCL_ENV/bin/python" -m toolalign.evaluation.bfcl fetch --output "$BFCL_SOURCE"
PYTHONPATH=src "$BFCL_ENV/bin/python" -m toolalign.evaluation.bfcl select \
  --source-root "$BFCL_SOURCE" --p02-manifest "$P02_MANIFEST" \
  --p02-sha256 c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5 \
  --g4-package "$G4_PACKAGE" --development tests/fixtures/tools/development.json \
  --tokenizer-root "$TOKENIZER_ROOT" --output "$BFCL_SELECTION"
PYTHONPATH=src "$BFCL_ENV/bin/python" tests/evaluation/bfcl_original_cases.py --source-root "$BFCL_SOURCE"
```

上述路径由 S1 的私有资料提供。非空 selection 才使用 `bfcl answers --source-root ... --selection ... --selection-sha256 ... --output ...`；对应模型终态通过 `bfcl score --source-root ... --selection ... --selection-sha256 ... --inputs ... --run-root ... --answers ... --output ...` 评分。当前零题包不执行这两条命令。

```sh
PYTHONPATH=src "$BFCL_ENV/bin/python" -m toolalign.evaluation.analysis \
  --inputs "$FIXED_INPUTS" --run-root "$T1_RUN_ROOT" \
  --bfcl-scores "$BFCL_SCORES" --output "$ANALYSIS_OUTPUT" --plot
```

L1/replay 省略 `--bfcl-scores`；分析不调用模型。输出为 analysis.json、requests/resources/failures/categories/group-effects/a2-pairs CSV，以及可选 quality-cost.png。官方失败明细可能包含原题/答案；写出入口复用项目现有私有目录检查，解析后的路径须位于 `.toolalign-local` 中，公开或逃出该命名空间的符号链接路径会被拒绝。

私有证据根为 `.toolalign-local/p06-g5-bfcl-analysis-r1/`；`evidence-index.json` 绑定最终提交、受检文件、命令 argv/退出码、stdout/stderr、19 项官方案例、实际筛选包、环境版本、JUnit 及端到端 fixture。首轮新增测试 27 passed/1 failed 的 CSV 断言错误保留；更正为按字段回读后通过。最终默认 CPU 环境为 Python3.14.7，新增 **32 项全部通过、无跳过**；其中最后2项验证私有写出边界，定点复验未重跑已通过的无关检查。

| 已执行检查 | 实际结果 |
|---|---|
| 默认 CPU 全库 pytest（命令016） | 1,396 passed / 4 failed / 78 skipped，139.53秒 |
| 上述4项定点复验（命令019） | 4 passed，0.25秒；未改生产代码或原测试 |
| 最终新增适配/分析检查（命令028） | 32 passed，0.80秒；包括真实T1原创CPU输出、私有路径/符号链接拒绝 |
| P00 独立检查（命令021） | 46 passed，0.98秒 |
| 官方 scorer 原创案例（命令017） | 19 passed，实际官方输出保留 |
| 专用环境 uv pip check（命令020） | 119 packages compatible |
| 官方评分及分析 CLI（命令014/018；私有入口复验029/030） | 6/6评分行保留；JSON/CSV/图表生成成功 |
| 全库 Ruff / 冻结契约（命令022/023） | PASS；4个冻结文件保持 |
| 公开内容扫描（命令024） | 924个路径的index及工作区检查PASS |
| 离线分发检查（命令025） | sdist、直接/重建wheel排除241个私有canary，18个公开fixture及冻结schema保留 |

命令016的4个失败均由本轮命令把 pytest 临时根设在 `.toolalign-local` 引起：测试刻意构造的“public”子路径也因此被现有规则认作私有。以默认临时根复验4项后全部通过；原失败日志和JUnit均保留。两次共覆盖1,400个通过的测试项，未把首轮重写为全绿。78项跳过来自默认环境缺少可选 Torch/numpy/pip 或未提供私有 tokenizer，不作为数值/模型执行证据。另有2条既有JUnit record_property兼容提示。初始118包锁的完整字节保存在命令002 stdout，hash与首次import失败时的锁完全一致；补 soundfile 后的119包锁 SHA256 为 `86e17fc2850f34e9ca908fb593713e7f798231e06405ece09588a835aacf4da3`。

本包只新增 BFCL、analysis、原创测试、专用依赖和本报告/交接。contracts、prompt、T1 执行器、D1 data/evaluation、tools、训练代码/锁和共享状态未改。正式运行前仍由 R1 审核技术实现、Q1 审核零题处置与说明，S1 接纳；若后续要扩展 schema 可表达范围，需在新结果产生前另行冻结协议。
