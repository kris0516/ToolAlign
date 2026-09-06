# P02 → P04｜完整 Action JSON 输出格式提案

2026-09-06，D1，`gpt-6-astra / max`。**CPU_PROPOSAL_PROBE_PASS；尚未选定生产格式。** 建议由 S0 定稿一个完整 Action JSON 格式，并让训练与推理调用同一输入投影。当前生产序列、冻结契约和数据均未修改；本报告不授予 G-DATA、P04 或模型效果验收。

版本说明：第 1–8 节是提交 `429ff90d3c806398389f575d937dde7af2d845e0` 的原提案及 r3 原结果记录；原提交、源码快照和日志均保留。第 9 节按 S0 同轮追加授权比较逐条保留 Message 角色的方案，基线为含原交接的 `c23b5136e596379000fcf4a9c2d1ce4bc9e27aec`。**输入投影现在有两个明确候选；不因单 envelope 易于往返就把它选作默认，也不能由往返 PASS 推定角色语义等价。**

本轮 task 为 `P02-format-proposal-r1`；本地基线 `b0d8d83750c48cd951c16b50cfa28a7898976e72`，分支 `work/p02-data`，授权 `fd67511ef4cb7853bb75b0b106ec4692a9d36be8`。已读取该授权的 AGENTS、P02 任务包、PROTOCOL、PROJECT_STATUS 和 S0_P04_READINESS；契约为 `toolalign.contracts.v1`，协作协议为 `coordination.v1`。本轮仅新增本报告、[原创探针](P02_OUTPUT_FORMAT_PROBE.py)和[交接单](../../coordination/handoffs/P02-format-proposal-r1.md)，没有接入新 main。

## 1. 已复现的问题与范围

S0 的表示层证据已按 SHA-256 `f880bd901b58814ecc5ff834b355f75d25e2c4d50a2e278dcf2225c65d13c46f` 核对。本次又用公开契约 fixture 与固定 tokenizer 实际复现：

| 路径 | CPU 结果 | 影响 |
|---|---|---|
| 当前 `LocalTokenizer.training_sequence()` 的工具 completion | 精确字节送入 P03 原 `parse_action()`，得到 `ContractError: Invalid JSON` | 原生 XML 包裹的 name/arguments 不是完整 Action raw |
| 相同 content 的 final / clarify / refuse | 旧 completion 完全相同 | 训练序列未编码 kind |
| 原模板传非空 tools | 插入原生 tool_call 格式说明 | 仅改 completion 会留下指令冲突 |
| 原模板直接处理 assistant 历史的字面 `</think>` | 原创 KEEP_PREFIX 丢失，KEEP_SUFFIX 保留 | 不能假定历史文本逐字保留 |
| 原模板直接处理两次历史调用及反序返回 observation | 输出 native tool_call/tool_response，但两个历史 ID 都消失 | 模板文本没有保留显式关联 |
| 原模板直接处理用户内容中的特殊 token 字面量 | 编码出的 EOS 数量增加 | 原始内容可能变成分词控制符 |

这些是固定模板、serializer、parser 的 CPU 事实；没有运行模型。P03 原候选的独立 FAIL `f34f7c5a4eac54b18a2b092495f4ce8eaa334f98` 是独立的收尾/因果问题，不能把本提案写成它的新整包 FAIL，也不能由本探针签发 P03 PASS。

## 2. 建议格式及精确投影

提案名称为 `toolalign.action-json.qwen3-envelope.v1-proposal`。正式名称、常量和指令正文须由 S0 在 ADR 中冻结；目前没有注册新生产版本。

采用有限 native JSON 的排序键、紧凑 UTF-8 序列化：`ensure_ascii=False`、`sort_keys=True`、`separators=(",", ":")`、`allow_nan=False`，数组顺序不变。然后将 JSON 文本中的所有字面 `<`、`>` 分别替换成 JSON Unicode escape `\u003c`、`\u003e`，包括对象键中的尖括号。普通 JSON 解码即可恢复原值；这不是 HTML 转义，也不做 Unicode 归一化。字面反斜杠字符串 `\u003c` 与真正字符 `<` 的编码不同，原始换行、引号、空串、布尔值、数字及 null 均保留。

输入只接受 `ModelInput = {messages, tools}`。训练端先使用冻结的 `model_input_from_example()` 白名单投影；推理端从 `ModelBackend.generate(request: ModelInput, ...)` 接收同一内容。向官方模板传入且仅传入两个消息：

1. 固定 system 协议指令：正文就是探针中的 `SYSTEM`，SHA-256 为 `2934f1e26d820b03d27565ec026c1dda38a236e33e22ab7f4477b37afdfbbb05`。
2. user 消息：上述编码得到的 `{"format_version": "…", "model_input": {"messages": […], "tools": […]}}`，实际序列使用紧凑 JSON。

保持官方 `chat_template` 原字节，`enable_thinking=False`、`add_generation_prompt=True`；**不向模板传 native tools，也不把原历史映射成 native assistant/tool 消息**。所有工具定义仍完整存在于 envelope 的 `model_input.tools`，包含 schema/version/side-effect/timeout 等全部冻结字段；这是原有数据，不是新的执行授权。实际执行仍须绑定本地注册工具。

这样模板不会新增原生 tool_call 格式说明，也不会对 envelope 内的 assistant 历史做 think 文本分割。固定模板照常输出自己的 role 控制 token 和 non-thinking generation prefix；原数据中的控制 token 被编码为普通 JSON 字符串。探针核验固定配置中全部 14 个 special token 在 payload/completion 分词中均未出现对应 special ID。

恢复 envelope 的 `model_input` 后，其 canonical hash 必须等于原输入。每个 Message 的 role、content、tool_calls、tool_call_id 均保留，数组保持原顺序；两次 observation 反序返回仍由 ID 关联到对应调用。**Message v1 本来没有历史 Action.kind，投影继续保留这个缺失状态。** 不根据 content 猜造过去的 final/clarify/refuse；当前预测 Action 的四种 kind 则显式编码。

固定指令要求按 role 字段理解原对话，并遵守原 system 任务约束；只对另一个输出语法的指令规定协议优先。这是一项需要 S0 选定的解释规则：原 system 文本（包括旧格式要求）完整保存在 JSON 中，却不再作为模板原生 system turn 出现。**值可逆不等于模型条件分布或指令遵循不变。** 本提案优先保证表示完整；role 解释、额外 token 成本以及小模型是否能稳定学会这种 envelope 都尚未实测。尖括号转义解决的是模板/分词控制字符冲突，不是对任意任务文本的语义安全证明。

prompt 的静态指令和格式版本不携带答案，动态工具 schema 仅来自 ModelInput。顶层 expected_action/oracle/split 传入投影会被拒绝；替换合法 example 的 target 和 split，prompt 不变。合法用户文本或参数里恰好出现这些字段名则应保留，不能按关键词删数据。小探针的输入已通过冻结 example 校验；它不是生产用的 standalone ModelInput validator，后者仍待实现和独立审查。

## 3. Completion 与 raw 的约定

completion 是上述可逆编码后的**完整 Action 对象**，无 XML、代码围栏、前后说明或第二层字符串。版本名存在输入协议和 manifest 中，不能给冻结 Action 增加 `schema_version` 等额外字段。例如公开 fixture 的完整 completion 为：

```json
{"content":"","kind":"tool_calls","tool_calls":[{"arguments":{"build_id":"demo-01"},"call_id":"call-1","name":"read_fixture"}]}
```

tool_calls 的 content 可以非空；每个调用保留 call_id、name、完整 arguments。final/clarify/refuse 使用各自 kind、空 tool_calls 和非空 content。原内容仅含空白但满足冻结长度规则的样例也不被悄悄改写；本探针不据此判断其语义质量。

本次将 `completion.encode("utf-8")` 直接交给 SHA 已核对的 P03 原 `parse_action()`；比较完整结构及 canonical hash，后者也区分 true/1/1.0 等不同 JSON 表示。没有 strip、XML unwrap、补 kind、补 call_id 或重新包装 raw。解析成功只证明 Action 结构/重复调用 ID 检查通过，工具注册和参数授权仍是后续独立边界。

建议实际后端对生成 token 记录精确 ID、结束原因和解码策略：仅把作为停止信号实际消费的终止 EOS 从内容 token 边界排除，其他 token 用 `skip_special_tokens=False` 解码，形成 `ModelOutput.raw_text` 并直接送原 parser。不能把删除任意字符串标记或把自由文本包装成 Action 称为 raw 通过；length/timeout/cancel 也不能补尾 JSON。训练采用规范字节，parser 对合法 JSON 的键顺序或空白接受能力仍按原实现，不强制进行生成后规范化。上述真实生成/停止行为本轮 **NOT_RUN**。

## 4. Token、EOS、loss 边界

令 `P` 为官方模板输出的完整 prompt，`C` 为完整 Action JSON；`p=len(encode(P))`，`T=encode(P+C, add_special_tokens=False)`，`S=T+[eos_token_id]`。要求 `T[:p] == encode(P)`，不得分别编码 P/C 再拼接冒充连接编码，也不能以截断 prompt 修复 prefix 变化。EOS 不附带换行。本轮 EOS ID 为 `151645`。

`S` 有 n 个 token 时，未移位的监督标签在 `[0,p)` 忽略，在 `[p,n)` 保留真实 token（包括唯一追加 EOS）。在常见 causal shift 中：`input_ids=S[:-1]`、`target_ids=S[1:]`，loss mask 在 `[0,p-1)` 为 0，在 `[p-1,n-1)` 为 1；因此最后一个 prompt 位置预测第一个 completion token，最后一个 completion 位置预测 EOS。探针保存了 token/label 数组和两端位置，并验证 completion token 解码恰好等于 C。

探针的 `-100` 只是未移位标签的诊断约定；不能假定 MLX trainer 接受该表示。P04 必须把同一边界映射到锁定 trainer 的真实 mask 语义，并实际验证 padding、batch、packing、causal shift 和 EOS 的 loss 参与。已有 prompt 内的两个模板终止 EOS 是正常内容边界；“一个 EOS”指**仅追加一个**，并且 completion 监督区域只有这一个 EOS，不是要求整条序列只有一个 EOS。

全部 12 例 prefix 稳定、raw 往返、序列解码、completion-only 索引检查通过。下表 completion 数包含追加 EOS；完整 SHA 用冻结 `canonical_hash(sequence_ids)` 计算。

| 原创/公开样例 | Prompt | Completion | Total | Sequence SHA-256 |
|---|---:|---:|---:|---|
| public_contract_tool_call | 450 | 35 | 485 | `935caf2c322056ed4be1b65592294533eb162d0e96679e01255547f67495ff8f` |
| same_content_final | 367 | 36 | 403 | `ff26cc26cfd94a249fe1d86c3bb69d13d59e3ec0c5be07516d7ff367105caf6c` |
| same_content_clarify | 367 | 37 | 404 | `d0fdb155f5c8d2e39ceab83aefd14ea46fb313fc09a87701272c6f62d4556036` |
| same_content_refuse | 367 | 37 | 404 | `765782fae7fef10f4b43d39682bc45a1c590823aaec8c27988ac427989678f0c` |
| leading_newlines | 367 | 19 | 386 | `7d195a27cb0986c8876e5fbe458e05016b98684021b2ff3972ff76c317dc4426` |
| whitespace_content | 367 | 17 | 384 | `89aa3772e3e083eb070c92ef5dd5aefe4b70b0193c54d9d503e50929ce06350d` |
| nested_two_tools | 761 | 207 | 968 | `5784bc2211c9df4be561cf22fbadf014c0f5820244915c6d57521bcec84e8e7e` |
| history_observations_reversed | 1050 | 204 | 1254 | `7171d588ee42c2374af7565592ec249f6978ec02f0f9af3adfe5bb789363e18d` |
| history_without_kind | 406 | 16 | 422 | `cd9408394231f5d37faa9a41e4e3b9d592727860216df3d2ddb2e498d514641d` |
| literal_think_history | 434 | 38 | 472 | `95505f97e76ff487c047d303c21e3ae10ff92100e0be505484fb5eedd31e53cb` |
| literal_control_tokens | 904 | 277 | 1181 | `e652bf1ef9c148617ff089f236d12a4a82607048c0688296b898367849c4bc7f` |
| legitimate_metadata_words | 376 | 20 | 396 | `02783f9093a39b6a71423e733b830f021dade71ec8ab2aee9749e2b35353becd` |

这组小例长度不代表全量分布。原格式的 113 条超 2,048-token 样本统计不能沿用到新格式，也没有依据本表选择窗口、过滤或截断。

## 5. 实测限制：raw 字节、复杂度与 token 预算须分别绑定

五个负向原样例都按预期被原 parser 拒绝：缺 kind（31 bytes）、重复 JSON key（62）、Markdown 包裹（58）、重复 call_id（599）、转义后超 raw 字节上限（132,045）。它们是预期拒绝，不是通过样例中的失败。

最后一例先通过原 `validate_part(action, "action")`：content 含 22,000 个 `<`；完整转义后，传 bytes 的 `parse_action()` 报 `ContractError: JSON byte limit`。P03 原 `MODEL_BYTES=131072`、8,192 JSON 值节点及 depth 24 是额外接收边界；冻结 content 字符数上限和 tokenizer 上下文窗口不能替代这些检查。新序列审计应记录 UTF-8 completion 字节数及 parser 接收状态；原始 ModelInput 边界与投影后 prompt 的字节/token 长度也须分别检查。超限保持明确结果，由 S0 决定后续窗口或选择规则，本轮未删数据或修改 parser 上限。

## 6. 后续共用实现入口与迁移要求（均待授权）

建议新增一个不导入模型框架的公共纯函数模块，例如 `src/toolalign/model_io/action_json_v1.py`，提供验证后的 ModelInput→prompt messages、Action→completion、格式身份；分别由数据长度计算、SFT/DPO 数据适配器、真实 ModelBackend 调用。序列构建通过最小 tokenizer 接口封装连接编码、prefix、EOS 和 mask 元数据；不在三个任务中各复制 serializer。

不能让 P04 直接复用当前严格限定 `tokenizers==0.22.2` 的 `LocalTokenizer` 环境门禁，或偷偷放宽该门禁。纯投影函数与 tokenizer 适配层应分开：P02/P01 各自锁定环境，独立构造相同 P/C，然后比较实际字符串、连接 token IDs、EOS、mask 与 sequence hash。本轮只运行既有 0.6B tokenizer 环境。新格式在 P01 的 0.23.2/真实训练适配器以及正式 1.7B tokenizer revision 上的对照均为 **NOT_RUN**，不能由旧格式 16 例 PASS 或“同属 Qwen3”推定。若后续 tokenizer/template/特殊 token 发生不同，需拒绝身份错配或另行冻结版本。

建议在保留原 data-build manifest 的前提下，另建序列 manifest（拟名 `toolalign.sequence-manifest.v1`）。至少绑定：

- 原数据 manifest ID、每个 split 的文件 hash、example ID 列表及契约 hash；输入/Action 的 canonical hash。
- 输出格式版本、共用模块 commit/内容 hash、固定指令 hash、JSON/尖括号编码规则。
- tokenizer repo/revision/文件 hash、官方 template hash、包版本、special/EOS 身份、模板开关、`add_special_tokens=False`。
- 每例 prompt/completion/连接 token/最终 sequence hash、prefix 状态、prompt/target/总长度、raw UTF-8 bytes、parser/复杂度检查结果；失败记录不能漏行。
- 唯一追加 EOS、completion-only/shift/padding/packing 策略；训练选择 manifest、窗口、seed、generation/stop 规则由各训练或评测 run 显式引用。

新版本的全量长度/序列审计应从**同一份不可变 examples/split 产物**读取，不必重新抓源或重建语义转换；产物使用新路径/版本，旧 18 项保持。训练选择另行绑定，不能因新计数改变默默丢弃长样本。未来 SFT/DPO/原始模型比较和 P03 正式推理也要登记相同格式身份；语法改变后的 parse rate 不直接与旧格式混算。DPO frozen reference 仍须对应已验收 SFT checkpoint。

## 7. 原数据与人审证据的复用条件

原 data-build canonical manifest 为 `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`；两份实际构建各 18 项产物与 manifest 的物理 SHA-256 `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5` 均在本轮前后重验一致，数据代码/政策/参数及旧交接也未变。没有再次全量构建。

100 来源/114 决策的冻结 HTML、samples、manifest、review.csv、排除样例保持 hash；独立填写副本的不可变字段 hash 为 `b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`，整份副本 SHA-256 为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。本轮本地读回 verdict/reviewer 均 0 条已填；没有写入判定，也不据此声称 S0 是否已在别处收到回复。

若将来只新增可逆序列视图，逐例证明解码后的 ModelInput/Action 与旧值相同，并核对上述人审内容 hash，旧包仍可作为**同一语义数据集的来源/标签审查材料**。它不自动批准新 prompt 对角色/格式的解释，也不完成 P04 的 10 条真实 token/mask 人工核对。若改变消息、工具 schema、参数、标签、分组、split 或过滤后的训练覆盖范围，应登记新版本与受影响审查范围；S0 决定复用或补审，worker 不能签 kris PASS。本轮不再次发起人审请求。

## 8. 源码身份、命令与结果

全部 CPU；复用 Python `3.14.7`、tokenizers `0.22.2`、Jinja2 `3.1.6`、jsonschema `4.26.0`。无安装、联网下载或模型导入；探针确认 torch/mlx/mlx_lm/transformers 未导入。实际运行日志和完整 token 数组只保存在本 worktree 的忽略目录，S0 可按私有交接定位。

| 输入/制品 | SHA-256 或固定 revision |
|---|---|
| P03 原 parser commit | `79a15d990fc27a9a33d033983c94eb92cccfb268` |
| 原 parser `_json.py`（原字节导入） | `15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b` |
| 冻结 schema bundle | `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb` |
| 当前 data/lengths.py | `c661c975f2463d519f401fb302487edb2a293e5200c117f79656ba46f41b543a` |
| Qwen/Qwen3-0.6B revision | `c1899de289a04d12100db370d81485cdf75e47ca` |
| tokenizer.json | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` |
| tokenizer_config.json | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` |
| chat_template 文本 | `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8` |
| qwen-source.v1.json 文件 | `defcf9979e833671076313be199ef27f21e82b03e1e038a1d1eaffb0396bfea4` |
| 公开 example.json 文件 | `70e5b1aeba57245d9e997aa7d9e3296b1013e23119bff939164d705a60980bcd` |
| 12 例 `{name,example}` 数组 canonical hash | `81347cd9f79a4e00478b07046a48d95b12f4b37f23396c2fb480e8923b9f3852` |
| 最终原创探针源码 | `bb0b0009b076fadb47a6f6c1602f132a2cd0c281a4edd1be11d25c82c4feeac5` |
| 最终 probe-result-r3.json（447,820 bytes） | `9e291b4a336b0cb7f37ef974f5bbbe41215d716059af1280de08766b6a8d5327` |

可复现的最终核心命令如下；环境和 tokenizer 已在此前固定，本命令不下载依赖。先以 `git show 79a15d990fc27a9a33d033983c94eb92cccfb268:src/toolalign/tools/_json.py` 保存到独立私有文件 `p03_json.py`；探针导入前自行核对该文件 hash。

```bash
PYTHONPATH=src TOKENIZERS_PARALLELISM=false \
  .toolalign-local/tokenizer-venv/bin/python \
  reports/data/P02_OUTPUT_FORMAT_PROBE.py \
  --tokenizer-root .toolalign-local/verified-source/qwen \
  --parser-file .toolalign-local/output-format-proposal/p03_json.py \
  --output .toolalign-local/output-format-proposal/probe-result-r3.json
```

输出路径存在时拒绝覆盖；复现者须选新私有路径。实际命令经既有 `record_command.py` 捕获 stdout/stderr、argv、UTC、退出码、环境与完整 log hash。r1 在汇总 fixture hash 时把 Python tuple 传给拒绝强制类型转换的 canonical_hash，退出 1，没有产出结果 JSON；修正为显式 `{name,example}` JSON 对象数组后 r2 通过。r3 仅增加大字符串原 Action 先行校验，12 条序列 hash 与 r2 一致。

| 实际执行（公共路径或忽略目录内脚本） | 退出码 | 完整 log SHA-256 |
|---|---:|---|
| `verify-preservation.py` → preservation-before.json | 0 | `5b002d6c94427c06a6d27338c570215baf8a872af81e5fb005590378470ac53d` |
| `P02_OUTPUT_FORMAT_PROBE.py` r1，汇总 tuple 错误 | 1 | `83c68f3b50536a13b2164988feffe443bf95ce6e787fe807b5e4ed76a0547b68` |
| `P02_OUTPUT_FORMAT_PROBE.py` r2 | 0 | `239ad40e2fe0769086eff56982548245fcc0d469b92427c83458c9b8b6948c18` |
| `P02_OUTPUT_FORMAT_PROBE.py` r3（2026-09-06 04:27:06 UTC） | 0 | `13119afb3d87fd9c5e42df57d4d1e1d514193c69fdcb6a7041dcb7b16dd69265` |
| `.venv/bin/ruff check reports/data/P02_OUTPUT_FORMAT_PROBE.py` r1/r2/r3 | 0/0/0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `.venv/bin/python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| `verify-preservation.py` → preservation-after.json | 0 | `5b002d6c94427c06a6d27338c570215baf8a872af81e5fb005590378470ac53d` |

初版失败源码私有保留，SHA-256 `e390314a5e9e28251ef216b202d7edfdbb49f74eaa0fa4ca133703fcdb8725e8`；r2 源码 `dab8fab88b660c6ba08d4073391148b79cd80b5774347095fb1acb6c85d6fc50`，结果 `9ce0de3571337894116193a1b50c798d1387c8fe35da3f6fd068bcfc3b177d2a`。最终公开扫描、提交范围和新增私有制品占用登记于交接单。

本次没有运行旧 16 例跨实现重复比较、全量数据/序列重建、pytest 全套、包构建、真实模型生成、GPU、SFT/DPO、P03 整包 harness、测试集/BFCL 评测、P04 人工 token/mask 审查或独立 R1 审查。探针与只读边界检查足以验证本报告的局部 CPU 结论；生产实现、格式 ADR、上述后续门槛仍由 S0 分发和验收。

## 9. 追加比较：逐条保留原 Message 的模板输入角色

本节仍在 `fd67511ef4cb7853bb75b0b106ec4692a9d36be8` 的报告/私有 CPU 原型范围，由 S0 原生跟进授权；没有修改生产代码或扩大数据集。A 为第 2 节的单 envelope，B 为 `toolalign.action-json.qwen3-message-roles.v1-proposal`。使用**同 12 个 example、同 ModelInput、同完整 Action completion**。探针先校验旧 r3 结果文件 hash，然后逐项比较其全部 12 行（包括原 P/C 字符串、token IDs、labels 和 hash）与本次重算 A 的行完全一致。

### B 的输入编码

B 在最前增加一个 system 消息，包含固定 `ROLE_SYSTEM` 指令及单独的 `{"format_version": "…", "tools": […]}` JSON catalog。其后按原顺序，对每个原 Message m 构造：

```text
{"role": m.role,
 "content": reversible_json({"message_index": i, "message": m})}
```

`reversible_json` 与 A 的排序键、UTF-8、尖括号 JSON 转义完全相同。传给模板的消息外层仅有 role/content，**不设置 native tool_calls，也不传 native tools 参数**；完整历史 tool_calls/tool_call_id 留在内部 Message，工具 schema 只来自该 ModelInput 的 catalog。original Message 本身不增加 kind。

工具 catalog 由新增 system 承载，原 system/user/assistant/tool 消息则各自以原 role 进入官方模板。固定指令中关于当前 Action 输出的整段规则复用 A 原正文；其输入解释部分改为逐条 Message，并说明工具 observation 是数据。`ROLE_SYSTEM` SHA-256 为 `54792de34977040c317db9bf3843df11aa4ae2800e03bcdb71696b3851c3c515`。

### 从实际渲染结果比较角色与恢复

本次逆向检查从**官方模板渲染后的 P** 中读取 im_start/im_end 控制段，再解析 JSON；不只从传入模板前的 Python 对象恢复。A 的 user 段恢复完整 envelope；B 从第一个 system 段恢复 catalog，从各后续控制段或模板生成的 tool_response 包裹恢复带索引的 Message。两者恢复出的 ModelInput 全字段及 canonical hash 均相同。所有 21 个原 Message 在 B 的模板输入 role 上保持原值；最终控制段为 14 个 user→user、3 个 assistant→assistant、2 个 system→system，另 2 个 tool→user。

| 原字段/角色 | A：实际模板位置 | B：实际模板位置与保留情况 |
|---|---|---|
| 工具 catalog | 全部位于单个 user envelope | 新增的第一个 system 段内，完整 JSON 值相同 |
| 原 system 任务内容 | user envelope 的 messages 数组内，只保留 role 字段 | 独立原生 system 段内的 Message JSON，内容值不变 |
| 多轮 user | 合并进单个 user 段的数组记录 | 各自原生 user 控制段；原顺序不变 |
| assistant 历史 | user envelope 内的 Message 数据 | 原生 assistant 控制段，JSON 包含原 content/calls，不生成 native tool_call |
| tool observation | user envelope 内的 Message 数据 | 传入模板时是 tool，模板输出仍为 user/tool_response；相邻 tool 消息合并到同一个 user 段 |
| call_id / tool_call_id | 原字段通过 JSON 恢复 | 原字段通过内部 Message JSON 恢复，两个反序 observation 关联的 call hash 与 A 完全相同 |
| 历史 kind | 保留缺失 | 保留缺失，不把 Message 冒充完整 Action |

例如 `history_observations_reversed` 原角色为 `system,user,assistant,tool,tool`。A 的控制段为 `system,user,assistant(generation)`；B 的控制段为 `system(新增协议/catalog),system(原任务),user,assistant,user(两条tool_response),assistant(generation)`。原任务的 `Task constraint: read only. Use tool-call JSON format.` 字符串值在两者均不变，但 A 在 user 数据中，B 在第二个 system 控制段中。B 没有保留 tool 为独立原生 tool 控制段；这是固定模板的实际行为，不能把“输入 role 保留”写成“全部输出控制角色原样保留”。

两者均无由数据插入的 special token ID；本次按实际 P 的控制段数量核验 im_start/im_end 计数，其他 12 种 special token 的原数据字面量不产生对应 ID。B 每条 JSON content 也不含字面尖括号，assistant 历史的 KEEP_PREFIX、think 字面文本和后续内容均可完整恢复；P 中只有固定 generation prefix 的一对空 think 标记。tool_response 标签是模板为输入 observation 生成的包裹，与模型输出的裸 Action JSON 是不同边界。

两种投影都拒绝顶层 expected_action/oracle/split，且同一 input 替换合法 target 和 split 后 prompt 不变。用户内容里的这些合法词语仍保留。所有 schema 都来自该例 ModelInput；逆向恢复及关联核对未读取隐藏 oracle 或真实最终测试数据。

### 实际 token 成本、P/C/序列一致性

B 的 P/hash 和 sequence/hash 在全部 12 例均与 A 不同；C 的精确 UTF-8 字节、C hash、completion token IDs（包括 EOS）在全部 12 例均与 A 相同。双方均通过连接编码的 prefix 稳定、唯一追加 EOS、解码还原 C 和 completion-only/causal shift 索引检查。固定 tokenizer、模板、parser、fixture 的身份沿用第 8 节；没有用重新分词的独立 C 来替代 P+C 连接序列。

| 同一例 | A Prompt | B Prompt | 共同 C 含 EOS | A Total | B Total | B−A | B Sequence SHA-256 |
|---|---:|---:|---:|---:|---:|---:|---|
| public_contract_tool_call | 450 | 489 | 35 | 485 | 524 | 39 | `88f6b77d3cc44f7567661bb0a5a3e3e38452487c59d535ce03af51f2ba242e1e` |
| same_content_final | 367 | 406 | 36 | 403 | 442 | 39 | `5c36cd07e1fee37f34dddc7092c9fd5ce8902d754ac0b01ab3fb14123070340d` |
| same_content_clarify | 367 | 406 | 37 | 404 | 443 | 39 | `3ed51b117f56bb8e836243e190fcf55369d8ecf99eabf1d46399b7e21bbcfa78` |
| same_content_refuse | 367 | 406 | 37 | 404 | 443 | 39 | `12dac8e96d6a7b2652a94e799a7cfc099f9e14ca4d671f87505b5024b413b30c` |
| leading_newlines | 367 | 406 | 19 | 386 | 425 | 39 | `5dbf3b0518ff87af8095f517f9066df48a11bc8ab4d60c3c6809a6671f4095d5` |
| whitespace_content | 367 | 406 | 17 | 384 | 423 | 39 | `ab4d7fb52f8699a65d6a192cb4218a5fdadc9fab1293dde3fad571f18c0c34c3` |
| nested_two_tools | 761 | 800 | 207 | 968 | 1007 | 39 | `84ddab911753915812dc2495671f94395c0cba0102bca42f031c1ec1249f0318` |
| history_observations_reversed | 1050 | 1143 | 204 | 1254 | 1347 | 93 | `65769e261d7060ca4b769c1b48dd29c9a41b245101c4b8961d16a9a51fee69c0` |
| history_without_kind | 406 | 471 | 16 | 422 | 487 | 65 | `38ed0f19dccc9653cc363d55e37efdaf795ad1c5e6d776c3d7ee66a6123f05ff` |
| literal_think_history | 434 | 499 | 38 | 472 | 537 | 65 | `80f9e11d0ae131c9ea5143d65982f7d3807ec1ed7024cf66863311c727dd01b7` |
| literal_control_tokens | 904 | 956 | 277 | 1181 | 1233 | 52 | `87802888810aae68208a26358ae50c74929d986d554229dfe0529c1824332ec7` |
| legitimate_metadata_words | 376 | 415 | 20 | 396 | 435 | 39 | `c8df4a4823947cc07c7b2213e763fb7d41ba0fe7296d5feb17e8183daeccaaf5` |

完整每例 A/B 的 P hash、共同 C hash、A/B sequence hash、字符串及 token 数组均在新的比较结果 JSON 中；stdout 的比较 summary 也包含 B 的 P/C/sequence 完整 hash。另保存 12 行 `{name,a_prompt_sha256,b_prompt_sha256,shared_completion_sha256,a_sequence_sha256,b_sequence_sha256}` 的 canonical JSON 索引，SHA-256 为 `c88980abe55ff5951393f2f4bf77b64a8ee5420efe08cdba1b7c63d1922177c6`。B 增加的 39–93 token 同时来自格式指令正文、catalog 位置、记录索引/包裹和原生角色分段；这**不是只改变一个角色 token 的纯消融实验**，也不是全量数据的成本估计。

### 256-token 每响应上限是独立门槛

本次读取未修改的 `configs/protocol.v1.json`：`generation_defaults.max_new_tokens=256`，文件 SHA-256 为 `e1c38ac24c1faff3f631ca27b7dc9e8ab80ea951cd07f00c8d91b9fc61ebaa15`。该值按 P03 任务包定义是**每次响应上限**，不能由总上下文窗口是否容纳来替代。

11 个例的规范 C 加 EOS 都不超过 256。原创 `literal_control_tokens` 是边界例：两方案均为 **276 个非 EOS 内容 token + 1 个 EOS = 277**，即便后端不把停止 EOS 算入上限，也超过 256。它的全序列在 A/B 中只有 1,181/1,233 token，却不能在该响应上限内完整输出当前规范 target。离线取这条固定 target 的前 256 个 token 解码，精确 raw 被原 parser 拒绝为 `ContractError: Invalid JSON`，该 raw SHA-256 为 `32ec571a7a395b258dcd938cb62003b85421faf16321c59d8bf081d006f848a7`；这是 target 前缀的 CPU 边界检查，不是模型生成结果，也不证明所有可能 JSON 写法的最短长度。

后续 sequence 审计须分别列出 prompt/总上下文、completion 不含/含 EOS、`max_new_tokens`、EOS 计数约定、是否可在该响应预算内结束、raw 字节/复杂度/parser 状态。总长度合格的例仍可能无法在当前响应预算完整生成；保留这类原样例并单列约束，不能暗中删除、缩写标签或增加免费续写。真实后端的停止计数、length 终态及 mask 仍需实际验证，不能把本节的 12 例表示检查 PASS 写成 12 例均满足 256-token 可生成性。

### 残余解释规则与候选结论

完整 Action JSON 和可逆尖括号编码在两个投影中均有 CPU 证据。若结构目标要求保留原 system/assistant 的模板角色，**B 满足这组例的角色位置要求，A 不满足**；不能因为 A 的逆向解析更简单就缩小真实对话语义目标。B 可作为后续实现/真实模型验证的候选，当前两个格式均未切换生产默认。

B 仍有需 S0 明确的规则：原 system 内容虽然回到 native system 段，却是 Message JSON 中的字符串；新增格式协议与后续原 system 同属 system 段，原文本中的旧格式要求仍要按固定协议“只覆盖输出语法”来解释，这种优先关系没有模型验证。工具 catalog 从 A 的 user 数据移入新增 system，但工具描述仍是数据而不是额外指令。tool observation 在官方模板中仍由 user/tool_response 承载，内部 role/ID 可恢复，却不能只因外层 user 就把结果当用户授权。历史 assistant Message 与当前完整 Action 的字段不同，缺失 kind 不得补造。

CPU 证明不了上述规则会被小模型稳定遵守，也不能声称 B 模型质量更高。正式 ADR 应分别冻结 completion codec、prompt projection、指令/catalog 位置、角色解释和预算身份；在允许的开发/validation 证据上验证真实交互及训练/推理共用实现，不用隐藏测试得分挑格式。原数据及人审语义包不变不代表新 prompt 语义已验收。

### 追加命令、身份与结果

实际比较命令复用原 CPU 环境，在上述核心命令的基础上使用新输出路径并增加：

```bash
PYTHONPATH=src TOKENIZERS_PARALLELISM=false \
  .toolalign-local/tokenizer-venv/bin/python \
  reports/data/P02_OUTPUT_FORMAT_PROBE.py \
  --tokenizer-root .toolalign-local/verified-source/qwen \
  --parser-file .toolalign-local/output-format-proposal/p03_json.py \
  --output .toolalign-local/output-format-proposal/role-comparison-result-r1.json \
  --compare-roles-to .toolalign-local/output-format-proposal/probe-result-r3.json
```

实际 UTC 为 `2026-09-06T04:47:02.923087+00:00`，退出 0，完整 log SHA-256 `5e6e6bdd5a0938025b67dc59fda253dc17af4a9f4a414968288f327a093fe716`。本次探针源码 SHA-256 `31eb366ad7e222b6788b3c7d8684934d12ad71b2c171a44e2c989391f9dc94b8`；比较结果为 1,075,515 bytes，SHA-256 `a093e0dd16f6406597e3bf3fcb21149e0f6c07e7be3c5f086f9c93fc25c45d83`。既有旧 r3 结果 `9e291b4a336b0cb7f37ef974f5bbbe41215d716059af1280de08766b6a8d5327` 仅读取，未覆盖。原例集 hash 仍为 `81347cd9f79a4e00478b07046a48d95b12f4b37f23396c2fb480e8923b9f3852`。

追加探针首轮通过，没有新增意外失败；旧 r1 tuple 汇总失败记录仍保留。对修改后的探针运行 `.venv/bin/ruff check reports/data/P02_OUTPUT_FORMAT_PROBE.py`，退出 0，log SHA-256 仍为 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`。后续范围/原证据保留/公开扫描及精确追加提交登记在同一交接单的追加节。没有运行模型、训练、测试集评测、数据重建或新的人工判定；这仍是有界结构/长度比较。
