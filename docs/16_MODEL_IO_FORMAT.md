# 16｜Action JSON、消息投影与序列身份

2026-09-06，ADR-0017。状态：**实现已在36b6988通过独立R1、最终CI及main技术验收；正式训练尚未授权**，见[S0主干证据](../reports/S0_P02_FORMAT_MAIN_VERIFICATION.md)。规范描述为 [model_io.action-json.v1.json](../configs/model_io.action-json.v1.json)；`format_id=toolalign.action-json.qwen3-message-roles.v1`。本规范不修改冻结 `toolalign.contracts.v1`，也不替代 G-DATA、G1 或 P04 的模型与人工检查。

## 选择依据

当前 P02 的原生 Qwen tool-call completion 与 P03 的完整 Action JSON raw parser 不同；相同 content 的 final/clarify/refuse 也会得到相同旧序列。直接训练旧 completion 再让 P03 补 kind 或修复 raw 不符合本项目目标。原始问题与命令见 [S0 衔接证据](../reports/S0_P04_READINESS.md)。

D1 用同 12 条公开/原创 fixture 比较了 A 单 user envelope 和 B 按 Message 保留模板输入角色的投影，完整候选为 `6c3d330e4b28be0fbc93c273bb2576f7317c69a8`，比较实现 `ac3c99b10e46deef745b624be14acfacff2cb369`。原 A 结果和提交保持。S0 读取报告、探针及实际结果，独立核对 68 项公开文件/命令/私有证据 hash 和 167 个不变原文件。两方案恢复同一 ModelInput，completion 的原始字节与 token IDs 相同；B 在这组例中保留原 system/assistant 控制段，A 将它们放入 user 数据。B 的工具观察仍由官方模板放入 user/tool_response，不能声称所有原生角色不变。B 比 A 多 39–93 个 prompt token，该差异也包括指令和 catalog 包装，不是纯角色消融或全量估计。

选择 B 是为了保留对话角色结构。CPU 证据不证明模型质量更高、输出语法指令必然被遵守，或引用在 JSON 内的原 system 内容与原纯文本具有同样影响。后续在原创开发/validation 证据验证，不用隐藏测试分数选格式。原完整提案/比较：[报告](https://github.com/kris0516/ToolAlign/blob/6c3d330e4b28be0fbc93c273bb2576f7317c69a8/reports/data/P02_OUTPUT_FORMAT_PROPOSAL.md)、[交接](https://github.com/kris0516/ToolAlign/blob/6c3d330e4b28be0fbc93c273bb2576f7317c69a8/coordination/handoffs/P02-format-proposal-r1.md)。

## 输入：仅由 ModelInput 构造 prompt

共用入口只接收 `ModelInput={messages,tools}`，独立验证后使用隔离副本。严格拒绝额外顶层字段、非原生或非有限 JSON、非法 ToolSpec/参数 schema、重复工具名、非法 Message、重复历史 call_id、缺失或重复观察关联、未完成 pending calls 和不允许的最后角色。遵循冻结契约已有语义，不通过伪造 example_id/split/expected_action 来代替 standalone ModelInput 验证，不修改冻结 validator。可使用 `schema_for` 提供的可信定义与已有 ToolSpec 公共验证函数；新关联检查必须与冻结规则一致。

prompt 不能接收 expected_action、oracle 或 split。它们作为用户合法文本内容出现时仍应保留，不能用词语黑名单删除数据。模板与可执行逻辑也不能来自数据样本。

先构造一个 system 消息：规范 JSON 中的固定 `instruction`、一个 `\n`、随后一个可逆 JSON catalog：

```json
{"format_version":"toolalign.action-json.qwen3-message-roles.v1","tools":[]}
```

此处 `tools` 逐值来自本次 ModelInput。之后按原顺序，对每个原 Message `m` 及从 0 开始的索引 `i` 构造：

```text
{"role": m.role,
 "content": encode_json({"message_index": i, "message": m})}
```

所有传入模板的消息只有外层 role/content；不设置 native tool_calls，不传 native tools 参数。完整历史 tool_calls、call_id、tool_call_id、content 留在内部 Message，不补造历史 kind。原 system 内容仍是任务约束；固定格式协议只规定当前输出语法，旧语法要求按该规则解释。工具描述、参数、观察是数据，其位置不赋予业务执行权限；P03 的注册验证仍独立。

保留官方模板字节，`enable_thinking=False`、`add_generation_prompt=True`。原 system/user/assistant 各自进入对应控制段；tool 输入由该官方模板转换为相邻观察共用的 user/tool_response 段，必须保留其内部 tool 角色、索引和关联 ID。该解释规则须在真实模型阶段验证，CPU 不能代签。

## 输出：完整 Action JSON

只序列化完整 `Action={kind,tool_calls,content}`。四类 kind 都显式保留；工具调用保留每个 call_id/name/arguments 和伴随 content，非工具输出保留原内容，包括合法空白、换行和非 ASCII。验证冻结 Action 结构与唯一调用 ID；训练 example 还需通过既有目标工具/参数/历史冲突检查。Action 编码和 prompt 入口分开，标签不能成为 prompt 的隐藏输入。

输入 catalog、每条 Message record 及 Action 输出使用相同 JSON 编码：UTF-8、排序键、紧凑分隔符、`ensure_ascii=False`、`allow_nan=False`；序列化后将所有字面 `<`、`>` 分别替换为 JSON 字符串转义 `\u003c`、`\u003e`。键和值均适用，JSON 解码后的值不变。不把 Python tuple、非字符串键或自定义对象强制转换为合法 JSON。

该转义避免数据字面 think/control 标记被固定模板或 tokenizer 当作控制。模型生成原始文本直接交给现有 P03 parser，不在生成后补字段、猜 kind、删标签、unwrap 或修复。一个终止 EOS 属于生成边界，不能把 JSON 内部文字当作终止标记丢弃。raw 的既有字节/节点/深度限制仍生效。

## tokenizer、序列和 loss

纯投影/编码模块不得依赖 tokenizers、Transformers、MLX 或 PyTorch；可选 renderer/encoder 适配层保留各自锁定版本。不要将当前 0.22.2 LocalTokenizer 的版本门禁强加给 P01/P04 的 0.23.2 环境。

S0 于 2026-09-06 只读核对 D1 的 0.6B 与 T1 的固定 0.6B/1.7B 来源：tokenizer.json SHA-256 `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`、tokenizer_config.json `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101`、LICENSE `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` 全部相同。原模板 UTF-8 SHA-256 为 `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`，与包含渲染参数的复合 model identity hash 是不同定义。没有读取权重或运行模型。

设 P 为上述消息经固定模板渲染的 prompt，C 为完整 Action 文本。必须编码 `P+C` 并核对其前缀与单独编码 P 相同，随后只追加一个 EOS；不能分别编码 P/C 再拼接冒充连接编码。监督 mask 覆盖 C 和该 EOS，prompt 及 padding 不参与 loss；next-token shift、首末监督位置、EOS 计数和解码后的精确 raw 都要有证据。真实训练器的 padding/packing/梯度与至少 10 条人工 token/mask 检查仍属于 P04，不能由离线数组测试替代。

本 v1 将提案版本标记和指令首句的 `v1-proposal` 改为 `v1`；其他 B 编码和角色规则保持。固定 instruction UTF-8 SHA-256 为 `294d8540bd3ff8de84293d5d8b0f7e8f2537ee9cf1c81b95e81b6415f1039cee`，完整规范文件 SHA-256 为 `e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207`。因此提案 prompt/sequence hash 和 token 数是历史证据，正式 v1 必须重新计算，不能沿用旧表。

## 新序列审计与保留规则

新的序列产物与原 data-build/18 项产物分开版本化，保留原 8,228 个 example、source/group/split/目标值、原数据模块与政策参数和 100 来源/114 决策人审包的 hash。只增加派生产物，不覆盖旧数据、原长度表或填写副本，不重新分组、截断、改写标签或自动代签人审。

逐例记录 example/ModelInput/Action 身份、format/描述符/指令/源码、模型来源/tokenizer/模板/渲染参数、P/C/连接序列/mask hash、prompt 与 completion 含/不含 EOS 和总 token、raw 字节/复杂度/parser 接收状态、上下文及响应预算判断和错误原因。固定审计 1024/1536/2048 上下文以及当前 protocol 的 256 响应上限；两者分别计数。不能因总长度合格就认为回答可完整生成。候选 cap 是历史校准边界及未改的 protocol 参数，不代表 P04 训练许可或真实吞吐保证。

提案的一个原创边界例是 276 内容 token+1 EOS，在 A/B 中均超出每响应 256，虽然总长低于 2048；其前 256 个 target token 实际不能解析成完整 JSON。这不代表最短 JSON 写法或模型生成分数。新审计必须保留超限与失败样本在完整分母，单列原因；不能免费续写或只统计成功行。训练选取策略待 S0 依据新的完整统计及阶段门另行登记。

新 manifest 绑定原 data-build canonical hash、实际输入文件 hash、新格式/代码/模板/依赖/参数/记录数与派生产物 hashes。全量只进行新格式所需的一次 CPU 测量；确定性用同一原创/允许的开发样例小集重新运行和逐项独立校核，原两遍数据构建及旧 16 例跨库比较不无理由重跑。任何字节/身份不一致需显式报错，不静默回退旧格式。

## 验收与回退

D1 仅在新的明确任务授权内实现共用模块、新序列审计和 CPU 证据；模型训练与真实推理适配器尚未授权。R1 独立审查精确候选，S0 合并并重验主干后，才可把新格式代码作为后续依赖。G-DATA 与 P04 的人工/真实模型检查仍独立。

原 P02 技术 PASS 只对应原格式及原实现，不被改写成新格式 PASS；语义人审可在逐例恢复值及原材料 hash 保持时继续使用，但不能覆盖新 prompt/mask 的人工检查。若新实现或真实模型不满足目标，停止新格式的后续实验，保留所有原始证据，登记新 ADR/版本再改；不回写旧格式身份或隐藏失败。
