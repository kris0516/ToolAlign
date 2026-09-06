# P02｜完整候选独立技术审查 r1

R1；2026-09-06；结论：**PASS（技术范围）**。未发现 P0/P1/P2 实现缺陷，分别为 **0 / 0 / 0**。**P02 整包与 G-DATA 仍 PENDING**：本报告没有替 kris 判定数据语义，没有批准训练。

| 身份 | 精确值 |
|---|---|
| 完整被审候选 | `b0d8d83750c48cd951c16b50cfa28a7898976e72` |
| R1 授权提交 | `c44739ac1e2fe282f5f51f80c5ea099687051ff3` |
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| D1 同步授权 | `f2a271be616cdb53c01e8d671029f31ae140c037` |
| D1 同步后受测 merge | `9bbd7d732cb9f84be2f1ca065beed9c9178801bc` |
| 实际数据构建实现 | `9be07a5b88d1dac1a6e1fea30358af1049b1119a` |
| R1 分支 | `review/p02-r1`，从完整候选新建 |
| 契约 | `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1` |
| 来源政策 | `toolalign.source_toolace.v1`；SHA-256 `b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7` |

审查 commit 为本报告所在提交，完整 SHA 随原生交接提供。R1 仅新增本目录和指定交接单，候选的 **167 个追踪文件逐字节未变**。未修改公共配置、冻结契约、D1 工作区、人审表或正式状态，也未创建嵌套代理。

**完整审查范围。** 已读授权版本 AGENTS、P02 任务包、PROTOCOL、PROJECT_STATUS、GOAL、数据治理/契约/来源政策规格，以及完整数据实现、测试、来源 manifest、历次 P02 报告与交接。相对同步授权 f2a271b 的 **40 个 P02 文件**均纳入审查；没有把本轮缩成仅审三个基线同步报告。当前 11 个数据模块字节与真实构建 manifest 中的模块 hash 完全相同。P01/P03 全包实现不在本次范围。

**独立性与主要证据。** [40 个原创反例](test_p02_boundaries.py)直接测试候选的拒收与保留行为。[实际产物审计](audit_real_artifacts.py)使用独立的分隔符扫描器和严格 JSON 解码，从原始文本重建调用、参数与完整历史前缀；不导入 D1 parser、SourcePolicy、分组函数或 LocalTokenizer，只使用冻结 P00 验证器判断 wire/参数合法性。[证据与包审计](audit_evidence_metadata.py)检查实际文件、运行记录、依赖元数据和归档成员。D1 自查脚本的 PASS 不作为这三项工作的替代。

| 检查 | 独立实测结果 |
|---|---|
| 当前适用 CPU 回归 | **298 passed / 0 skipped**：180 个仓库测试（含 17 个真实 tokenizer 测试）+ P00 46 个 + P00-r2 72 个 |
| 新增原创反例 | **40 passed**，单独一次调用；与 298 项合计 338 项，默认核心测试不重复累加 |
| 默认核心环境 | 163 passed / 17 明确 skip；该环境没有 tokenizer 可选依赖 |
| 固定 tokenizer | R1 私有环境 27 个依赖逐项等于固定清单，Python 3.14.7；未安装或导入 Torch/MLX |
| 完整工具转换 | 16,650 个去重工具逐项对照来源与公布政策；5,282 条 default 原值、类型、路径和 hash 保留 |
| 字段级 lineage | 每项 before/after、存在性、改名/别名/收窄/annotation 理由与源/目标值相符；四种统计分母独立复算 |
| 目标与前缀 | 8,228 个 example；15,073 个目标调用、632 个前缀调用及完整历史消息独立重建一致；JSON 比较区分 1、1.0 和 true |
| 整条来源约束 | 7,662 个最终来源的全部调用均验证，包含已接受决策之后的调用；原始参数未补填或强转 |
| 数据 A/B | 两边 18 项实际文件重新读取、hash 校验及字节比较一致；未重新运行全量数据 build |
| 完全重复排除 | 33 个被排除候选从原始来源重建，内容确与保留项相同 |
| 实际长度复验 | 独立调用官方 Jinja 模板和 tokenizers 对 **226** 条真实决策重新渲染/整体编码，含全部 113 条超过 2048 的样本；序列 hash 和长度完全一致 |
| 人审材料 | 100 个不同有效来源、114 个决策、34 个分层标记；抽样、身份、数据对应、500 个 HTML 内容区逐项核对 |
| 实际浏览器 | 本机默认桌面视口下观察说明页和展开样本；无横向溢出，DOM 中无脚本/外部资源；检查后关闭临时页面与回环服务器 |
| 包与安装 | 新 sdist→wheel 构建、实际成员字节及 P00 隔离安装/五类 CLI fixture/无 ML 检查通过 |

**策略与解析边界。** 原创反例覆盖 nullable/union、类型不适用关键词、开放对象、无效/过宽边界、嵌套 default、bool 与 integer 混淆、未知系统条件、名称与 observation 歧义、源 JSON 重复键、表达式/尾随文本、深度和调用文本预算，以及先前/后续调用违反项目收窄时的整来源排除。default 仅进入带类型的 annotation 和说明；required 与实际参数保持。源码只接受已审计 boilerplate/hash 和确切时间/语法上下文，未知附加条件被隔离；实际用户消息逐字保留，目标及未来 observation 不进入其输入前缀。源工具/observation 从未执行；原副作用仍 unknown，wire `sandbox_only`/1000ms 是项目限制，执行绑定为 none。

**分组、排除与长度。** 独立重新构造来源/tool/schema/词法模板键并核对组 ID、固定 seed 的 split、规范化 schema 键与有效交集。原 **3,517 组**及最大 **6,716 个来源**的组保持；assignments 字节 hash 与旧严格检查点记录相同。规范化 schema 去掉 annotation，保留真实属性名，排序 required/enum 并统一已约定的空集合/零下界，查得 **11 个跨旧组键、其中 4 个跨 split、涉及 64 个来源**；全部相关来源隔离，不重分组或只保留其中一边。最终所有被检查原始键和规范化 schema 键跨 split 交集为 0。MinHash LSH/Jaccard 是有说明的近重复启发式，未声称穷尽语义等价。

| 数量口径 | 独立核对 |
|---|---:|
| 原始来源 / assistant 决策 | 11,300 / 13,819 |
| 规范化前排除 / 合法候选 | 5,505 / 8,314 |
| 跨原组 schema 排除 / 完全重复排除 | 53 / 33 |
| 最终 example / 不同来源 / 不同工具 | 8,228 / 7,662 / 15,105 |
| train / validation / test / ood_test | 7,515 / 234 / 215 / 264 |
| 可转换工具出现次数 | 31,822，不能当最终工具数 |
| 长度 ≤2048 / 2049–4096 / >4096 | 8,115 / 113 / 0 |
| 总长度 P50 / P90 / P95 / P99 | 938 / 1,520 / 1,725 / 2,136 |

会计闭合：13,819 = 5,505 + 8,314；8,314 = 53 + 33 + 8,228。互斥主排除、重叠理由，以及去重工具/工具出现/来源记录/assistant 决策四种字段变更分母均复算匹配。全部最终标签为有源调用的 tool_calls；未把无真值的自然语言编成 final/clarify/refuse。

训练长度口径是 `qwen3_non_thinking_concat_one_eos_v1`：整体 encode(prompt+completion)，要求 prompt token 前缀稳定，再额外追加一个 EOS，无尾换行；字面 EOS 不被删除。计数是未 padding 的序列长度，旧 raw 来源表示长度单列。R1 复核了 D1 已留存的 16 个原创 HF API 参考样例完整字符串/IDs，与本地采集对应一致；当前 17 个真实 tokenizer 测试亲自重跑。没有重新安装 HF 参考环境。P02 的 8192 数据上限不授权训练窗口；P01 当前上限 2048 下的 **113 个长样本**仍须由后续训练配置明确处理，并绑定同一 manifest/序列化口径。

**来源、构建与包。** [ToolACE 固定来源](https://huggingface.co/datasets/Team-ACE/ToolACE/tree/6bda777c88d21e5a204703c1ee45597a8fa4f734)的原始 data/README 和 [Qwen 固定 tokenizer](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)的三个必要文件实际字节与锁一致。已保存官方 API/access 文件 hash 互相匹配，记录当时公开、非 gated、无认证。ToolACE 许可证据是 README Apache-2.0 标记及当时树中无单独 LICENSE；Qwen 的实际 LICENSE 为 Apache 2.0。本轮 web 工具拒绝两个固定 API URL，未绕过；不把已保存的访问记录声称为新一次联网查验。

49 份 worker 原始日志及其元数据与已提交报告对应一致，另核对两份早期失败日志 hash。A/B 的不同配置、输出目录、启动 UTC、实际耗时、退出码及代码提交均核实。历史 strict 的零样本报告与日志保留，未重新读取旧严格包的全部 14 个文件。此前私有内容 sdist 事故及其详细失败日志保持不读、不解包；报告中原失败事实和 hash 保留，当前已修复基线另以真实新包验证。

| 核心产物 | Bytes / 数量 | SHA-256 |
|---|---|---|
| canonical data build manifest | 18 项 artifact | `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756` |
| examples.jsonl | 8,228 条 | `d45c815e9b775249c642cd3c9f624c28e7ab6505425cd6c009bfb06402c8f21f` |
| lineage.jsonl | 8,314 条候选 | `3f6a8db88a77b6df02c58c538471bbfb157a3fd9655c6a79160c0ae345a38f5c` |
| assignments.jsonl | 11,300 条来源 | `51ce05ecbd8a986c3ea1b585f1a1b186dd6e94d2bcc3ce5b498ccdcf40ded3db` |
| R1 新构建 sdist | 135,139 / 60 文件 | `d7ee2db8d9ce257db9a035adbee389316f4a89d91832494117336e859c84a241` |
| R1 新构建 wheel | 51,140 / 29 文件 | `78ad37239a3d1023295d2e7a73be19583bcd335a8f50b47ca1cefb61f86b4672` |

sdist 除生成的 PKG-INFO 外均为追踪公开文件且字节相同；wheel 的 24 个源码/资源逐项相同，其余仅 dist-info。当前 241 个私有合成探针和 18 个公开对照在 sdist、重建 wheel、直接 wheel 检查通过。未以模拟归档替代实际正常构建/安装。

**人工审阅仍待定。** 冻结人审包与填写副本均保持全空，身份列 canonical hash 为 `b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`，CSV 文件 hash 为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。有效 examples、样本和 manifest 互相绑定；排除代表不算有效样本。R1 检查浏览器可用性和六个真实来源的转换对应关系，没有填写或签署人工判定，accepted_examples_reviewed 仍 0，mislabel_rate 为 null。P05 偏好对的抽检阈值不套用为本次 P02 的已通过判断。

一个具体待决点供 kris 定位：来源索引 **61**，source hash `01934139e5914ea2edf537f242acf4fa1b266fc0295241e682f9245f0e8648fc`，原始 turn **5** 的工具调用接在谈话性评论之后；请在语义审查中判断该上下文是否需要再次调用工具。源调用和转换结果一致，这不是已证实的转换缺陷，也没有计作人工误标或 pass。公开报告不复制原始对话。

**实际命令与失败记录。** 完整 argv、环境、UTC、退出码、原始日志 SHA-256 和所有产物 hash 见 [机器证据](evidence.json)。具体本机路径仅留私有映射；表中日志均由 R1 自己的执行器捕获，并重新读取校验 hash。

<!-- COMMAND_TABLE_BEGIN -->
| 命令记录 / 结果 | 退出码 | 原始日志 SHA-256 |
|---|---:|---|
| cpu-sync — 默认 CPU 同步 | 0 | `91597704bc5423f7afefaab3d3c5ab7d38c8be9f1d71cf184914e6ec7d31d837` |
| tokenizer-venv — 私有 CPU 环境创建 | 0 | `d45e67906cfcd3e42a43f6f2c81fc9461380bc2415cccbabe2512f06313c882e` |
| tokenizer-install — 27 个固定 CPU 依赖 | 0 | `e63c1b3e2eddb349289477e5e333d185b1abac54a7e3e9fc27885868ea9f18f0` |
| cpu-default — 默认核心 163 PASS / 17 skip | 0 | `39a99322756e64d756472c514ddc78755641dfa7901cd4079a322ccda18dd6d0` |
| cpu-tokenizer — 首次调用：文件名错误，无测试 | 4 | `93cad389d9ae5f56d2e9698e3febf14758b5cb7ac9e4404a83ed92078b525b51` |
| cpu-tokenizer-corrected — 298 PASS，含 17 个真实 tokenizer 测试 | 0 | `a779b841d89a47c095c6de0ec44d00ae401f7a0e0a17aa97c0bdc3a411e62c76` |
| independent-counterexamples — 首次收集：新增探针引号错误 | 2 | `adec6a0b6bf2f1a7d999c91eafcff1488957a591c70093b132e0476d4a83838c` |
| independent-counterexamples-corrected — 40 个原创反例 PASS | 0 | `2ab79feebcb72c3b3eb8a53d5d7916cd834c221a2e7c943c0de5cfd7d3b4d20e` |
| review-lint-initial — 新增反例与首版审计 lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| candidate-lint — 全仓 lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| contract-freeze — 四文件冻结契约 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| source-boundary — 241 私有 / 18 公开归档对照 | 0 | `fa46036763aaeaa49eaadf707ca303cd79a39ac54e843d15934a5f9a3febc24e` |
| real-artifact-audit — 首次实际审计：HTML 对象显示顺序断言 | 1 | `3ab1ca1e2ba5491b5c3ddafa49a1182855617959e6fdc358c3e03a8425c5f295` |
| package-build — 实际 sdist→wheel | 0 | `c6a5193571b8f7b176af40873ab373d70e558c22d876735abb56d6ef8b5a3a75` |
| isolated-wheel-install — P00 隔离安装与 CLI | 0 | `f116a443c64367b8688e49c72243b21917169f1af8c7e208d2acb85d4d9b8047` |
| real-artifact-audit-corrected — 完整源对应/分组/人审/226 条分词 | 0 | `025fecd03b25618b208cbc6043fe039d7ad8c2dda6688596b739609fc5a3e812` |
| real-artifact-audit-final — 新增逐字段 lineage、四种分母与 33 项去重核查 | 0 | `aa3621dc2f795a081b6c037786c138b4792a277b8f61491ca6f8725e480c59aa` |
| review-lint-final — 最终新增三个探针 lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| core-environment — 默认 12 个 distributions | 0 | `6a95fa9e03f931d459ef548ee4c10cd812993ebb320881b15def0a3f6071cddb` |
| evidence-metadata — 来源、49 份 worker 日志、环境与真实包 | 0 | `82da584ddaa9a86b54230c61124229be89a143b171716634af92b269fa72a3a3` |
| data-cli-help — 数据 CLI 入口 | 0 | `8b4d9d0f1ab206691f2448f39d00d91eb957ef040131acfa11b6fc59591a1e34` |
| real-artifact-audit-type-exact — 最终类型保真比较的实际产物审计 | 0 | `aa3621dc2f795a081b6c037786c138b4792a277b8f61491ca6f8725e480c59aa` |
| final-lint — 最终全仓 lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| public-staged — 完整审查文件暂存后公开扫描 | 0 | `a1b028a00bc5b0948702a13c571a0891f2b2e9b47dce209eda98bb9c6c427603` |
| scope-final — 候选和新增范围最终逐字节校验 | 0 | `f64a971d66471d84d535a63dfaeefb7b003b438260b9c136752b89850b481252` |
| public-final — 最终证据重新暂存后公开扫描 | 0 | `a1b028a00bc5b0948702a13c571a0891f2b2e9b47dce209eda98bb9c6c427603` |
<!-- COMMAND_TABLE_END -->

本轮三个非零测试命令均来自 R1 审计准备，原日志及相应初始脚本保留：首次 298 项调用使用了错误的旧测试文件名，退出 4、未运行测试；新增反例文件有一处引号错误，收集退出 2；首版 HTML 核对把对象显示顺序当作值差异，退出 1。分别修正调用、新增测试文件、审计值比较后通过；HTML 改用严格 JSON 解码及类型保真的规范化字节比较，未放宽任何候选条件，也未改候选实现。后续加强字段 lineage、四种分母、重复排除和数值类型检查的实际重跑均通过。临时页面服务器的 interrupt/130 是完成预览后的主动清理，不是数据测试失败。

**复现与限制。** 在精确候选代码树中运行，使用自己的私有环境并将 `D1_PRIVATE_ROOT` 设置为 S0 授权的只读制品根；脚本不执行 D1 环境、不下载模型。精确实际 argv 在机器证据，以下只表示可移植参数映射：

```bash
uv sync --locked --python 3.14
uv venv --python 3.14 .toolalign-local/review-p02/tokenizer-env
uv pip install --python .toolalign-local/review-p02/tokenizer-env/bin/python -r reports/data/tokenizer-audit-environment.txt
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$D1_PRIVATE_ROOT/verified-source/qwen" .toolalign-local/review-p02/tokenizer-env/bin/python -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py
PYTHONPATH=src .toolalign-local/review-p02/tokenizer-env/bin/python -m pytest -q reports/review/P02/test_p02_boundaries.py
PYTHONPATH=src TOKENIZERS_PARALLELISM=false .toolalign-local/review-p02/tokenizer-env/bin/python reports/review/P02/audit_real_artifacts.py "$D1_PRIVATE_ROOT" .toolalign-local/review-p02/reproduced-artifacts.json
uv build
uv run --locked python reports/review/P00/verify_wheel.py
PYTHONPATH=src .toolalign-local/review-p02/tokenizer-env/bin/python reports/review/P02/audit_evidence_metadata.py "$D1_PRIVATE_ROOT" .toolalign-local/review-p02/reproduced-metadata.json
```

新增 R1 私有环境、缓存和证据约 **77.4 MiB**，另有约 182 KiB 新包，低于授权 2 GiB。没有加载模型、使用 GPU、执行历史工具、生成训练样本或写入其他工作区。

**NOT_RUN / 待后续：** kris 真实语义验收、G-DATA 放行、训练配置/manifest/窗口绑定、数据增强/偏好挖掘、SFT/DPO、BFCL/正式评测、推理服务、模型或数据上传、P01/P03 全包审查、新一轮两遍全量数据 build、HF 参考环境重新安装/执行、旧严格包全部 14 文件再次审计、此前失败私有归档/详细日志、当前线上来源重新确认、最终 GitHub CI/main 合并与集成验证。S0 可据本技术 PASS 继续其集成流程；技术通过不能把 P02/G-DATA 状态改为 VERIFIED。
