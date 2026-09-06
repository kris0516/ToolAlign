# P02-format-proposal-r1｜完整 Action JSON CPU 提案交接

2026-09-06，D1；`gpt-6-astra / max`。**提案已形成；worker CPU 探针通过，等待 S0 正式 ADR/实现授权。** 此结论不替代独立审查，不改变 P02 的 G-DATA 状态，也不授权 P04 训练。

## 身份与提交

- 工作分支：`work/p02-data`；本轮起点 `b0d8d83750c48cd951c16b50cfa28a7898976e72`。
- 授权：`fd67511ef4cb7853bb75b0b106ec4692a9d36be8`；已按原 SHA 读取 AGENTS、P02 任务包、PROTOCOL、PROJECT_STATUS、S0_P04_READINESS。
- 精确提案/探针提交：`429ff90d3c806398389f575d937dde7af2d845e0`，直接以本轮起点为父，仅新增两个报告目录文件。本交接为随后独立证据提交；最终候选 SHA 由原生回报给 S0。
- 契约：`toolalign.contracts.v1`；协议：`coordination.v1`；P03 受测原 parser 来自 `79a15d990fc27a9a33d033983c94eb92cccfb268`。
- 允许的三个新增文件：[提案](../../reports/data/P02_OUTPUT_FORMAT_PROPOSAL.md)、[原创 CPU 探针](../../reports/data/P02_OUTPUT_FORMAT_PROBE.py)、本交接单。没有接入新 main、修改生产默认、依赖、契约、src/tests、manifest 或协调状态。没有推送远端；S0 可从共享本机 Git 按精确 SHA 读取。

## 建议及实际结果

建议评估 `toolalign.action-json.qwen3-envelope.v1-proposal`：完整 Action JSON 保留四种 kind、content 和每个调用的 call_id/name/arguments；动态输入只接受 ModelInput。固定 system 指令加一个包含全部原消息和工具的 user JSON envelope；JSON 尖括号转义可逆，官方 Qwen 模板字节、non-thinking 开关不变，native tools 参数不传。

该方案避免模板重新声明 tool_call 输出、截取历史 think 内容和丢失 observation ID。完整 JSON 直接通过原 P03 raw parser，不采用生成后修复。原历史 Message 缺失 kind 的事实继续保留。它会改变模型看到的 role 结构和格式指令优先解释；数据值可逆不等于模型行为等价，后续必须验证。

| 实际检查 | 结果 |
|---|---|
| 12 个公开/原创 CPU 样例 | 全部 raw 往返、输入可逆、稳定 prefix、一个追加 EOS、completion-only/causal shift 索引检查通过；完整 token IDs/序列 hash 私有保留 |
| 四类输出与相同 content 的三类非工具输出 | 四类均保留；三类非工具的 prompt 相同、completion 和 sequence 不同 |
| 复杂输入 | 非 ASCII、引号、换行、空白、嵌套参数/JSON 类型、两工具、多轮历史、反序 observation 关联、无历史 kind、字面 think/14 种 special token 通过 |
| 旧表示反例 | 原 completion raw 解析失败；三 kind 合并；native tools 指令、历史 think 截取、ID 丢失与控制 token 注入均复现 |
| 五个负向 raw | 缺 kind、重复 key、Markdown 包裹、重复 call_id、转义后字节超限均被原 parser 按预期拒绝 |
| 数据/人审保留 | 本轮前后检查相同；两份实际构建各 18 项 hash/manifest，源码/政策/参数，100 来源/114 决策材料保持；未填写判定 |
| lint / 契约冻结 | 最终 ruff 与四文件冻结检查通过 |

一项明确限制：含 22,000 个 `<` 的 Action 先通过原结构校验，转义为 132,045 bytes 后触发 P03 131,072-byte raw 上限。新序列 manifest 必须同时记录 token 长度、raw 字节和 parser 接收状态，不能静默删掉这种样本。

后续建议由公共纯函数模块统一训练/推理投影，tokenizer 适配层保持各自锁定环境；不能将现有 0.22.2 的 `LocalTokenizer` 门禁直接用于 P01 0.23.2。需新格式跨实现/正式 1.7B 身份对照、独立 R1 审查、新长度/序列 manifest 和实际 mask 验证。旧语义人审材料可在内容 hash 与逐例 decoded projection 不变时供 S0 评估复用，但不能替代 P04 的 10 条 token/mask 人工核对。

## 证据与失败记录

完整来源身份、命令、退出码、日志和 12 个 sequence hash 在[提案第 8 节](../../reports/data/P02_OUTPUT_FORMAT_PROPOSAL.md)。实际最终探针运行于 `2026-09-06T04:27:06.161843+00:00`，Python 3.14.7 / tokenizers 0.22.2 / Jinja2 3.1.6 / jsonschema 4.26.0，退出 0。

- 最终探针源码 SHA-256：`bb0b0009b076fadb47a6f6c1602f132a2cd0c281a4edd1be11d25c82c4feeac5`。
- 最终结果 JSON SHA-256：`9e291b4a336b0cb7f37ef974f5bbbe41215d716059af1280de08766b6a8d5327`；完整 log：`13119afb3d87fd9c5e42df57d4d1e1d514193c69fdcb6a7041dcb7b16dd69265`。
- 原 parser SHA-256：`15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b`；模板：`a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`。
- r1 探针汇总 fixture hash 时错误传入 Python tuple，退出 1，未生成结果 JSON。保留原失败源码/log，修正为 JSON 对象数组后 r2/r3 通过；不能将 r1 改写成 PASS。
- r3 的 12 个 sequence hash 与 r2 相同；本轮未重复旧格式 16 例跨实现比较。

最终范围检查实际执行 `.toolalign-local/tokenizer-venv/bin/python .toolalign-local/output-format-proposal/verify-final-scope.py`，退出 0：167 个原有追踪文件逐字节未变，所有差异仅为三个允许新增文件；授权快照/原 parser/S0 证据 hash、报告来源 hash、12 行 token/sequence 表及此前日志均匹配。检查源码 SHA-256 `c8806be3a8630b96c953c7749329fb29ff37c75eb2b0ad7310345ce74c7e472f`，结果 JSON `7a5aef536f57efa0da7d39fbc1bb0def29d30ce34cd7731560a4fb4e2638dd14`，完整 log `01bfb4897a477b3532d939a743ac13f2c3eabc1c36ed8e77531bcc3323caf334`。受测提案 Markdown 文件 SHA-256 为 `dce15a0c5e4cd71323d9115d52f49395f518369fc92ae161be98e60f9aeb75a1`。

实际 `.venv/bin/python scripts/check_public_content.py` 对新增两个报告时扫描 169 路径、加入交接时扫描 170 路径，均退出 0；完整 log 分别为 `ee160a5bb882bd5bb47c9a33089d64b7059e69a92651dcbef5ac816c2bea6115`、`61186a06bf2a85c528548b80b369e98b6d78abf8aa755be6cc3e882ce1621c0c`。这是 index/working tree 启发式扫描，不代替人工公开内容审查。

范围检查时，本轮私有工作目录及本轮日志测得 1,019,968 bytes；该读数不含检查自己随后写入的结果和后续封存日志。没有新建环境或安装依赖，远低于授权新增 2GiB 预算。前后保留检查 JSON 同为 `a5d819465d6ac5f4162c5040d15b0f8c89db3e09457a8b4fdf0afe14ca846a80`。

## 不变证据与未运行项目

原 data-build canonical manifest：`87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。两份原 manifest 文件 SHA-256 均为 `c728dfe385e340fadf1e5949976c012709fc10a1dbca9010548edf74785259e5`。100 来源/114 决策的填写副本 hash 为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`；不可变身份字段 hash 为 `b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c`。本轮本地副本仍未填 verdict/reviewer；没有替 kris 判定或再次发送人审请求。

NOT_RUN：生产格式切换、standalone ModelInput 生产 validator、新格式跨 tokenizer/1.7B 对照、全量新序列统计、模型生成、真实 MLX mask/padding/packing、SFT/DPO、GPU、P03 整包 harness、测试集/BFCL 评测、P04 token/mask 人审、独立 R1 审查。本轮未运行整套 pytest/包构建，因为只新增报告与独立小探针，生产文件字节未变。

无模型/GPU/安装/下载/费用；未筛选或截断样本、重建/覆盖原产物或上传数据/模型。提交本交接后结束本轮，等待 S0 决定正式 ADR 和允许的实现范围。

## 同轮追加交接：Message 角色与每响应预算比较

S0 在原交接后追加了同一 `fd67511ef4cb7853bb75b0b106ec4692a9d36be8` 范围内的 CPU 比较。原提案 `429ff90d3c806398389f575d937dde7af2d845e0`、原交接 `c23b5136e596379000fcf4a9c2d1ce4bc9e27aec` 及全部原结果保留，未重写历史。**当前精确比较提交为 `ac3c99b10e46deef745b624be14acfacff2cb369`，直接以 c23b513 为父，仅修改原报告和原创探针；本节是其后的交接追加。** 最终完整候选 SHA 由原生回报给 S0。

新报告[第 9 节](../../reports/data/P02_OUTPUT_FORMAT_PROPOSAL.md)明确比较 A 单 envelope 与 B `toolalign.action-json.qwen3-message-roles.v1-proposal`：B 使用新增 system 协议/catalog，每条原 Message 保持传入官方模板时的 role，完整 Message JSON 放在 content；不传 native tools/tool_calls。双方仍使用完全相同的 Action completion。两候选都未切换生产默认，不再以单 envelope 易于往返作为定稿理由。

| 同 12 例的实际比较 | 结果 |
|---|---|
| 原证据复现 | 新计算 A 的全部 12 行 P/C/IDs/labels/hash 与原 r3 逐项相同，原结果文件仅读取 |
| 实际 rendered prompt 逆向恢复 | A/B 均恢复全部 ModelInput 字段与相同 canonical hash；历史 kind 缺失保留，expected/oracle 不进入 prompt |
| 角色位置 | B 的全部 21 个原 Message 在模板输入保留 role；输出控制段为 user→user 14、assistant→assistant 3、system→system 2、tool→user 2 |
| 原 system 约束 | A 在 user envelope 的记录中；B 回到独立 native system 段中的 Message JSON。格式优先规则及 JSON 引用方式仍需模型验证 |
| 工具 observation | 两个相邻 tool 消息被官方模板并入一个 user/tool_response 段；内部 ID 及反序关联完整保留，不声称 native tool 控制段原样保留 |
| think/特殊 token | 两者均消除数据字面量的模板/特殊 ID 冲突；B 从实际控制段逐项核验，历史文本可逆、仅 generation prefix 留一对空 think 标记 |
| P/C/token/sequence | 12 例 C 字节/hash/包括 EOS 的 completion IDs 完全相同；P/sequence hash 均不同；双方 prefix/EOS/监督边界通过 |
| 成本 | B 每例多 39–93 个 prompt/total token；包含指令正文/catalog/包装/角色分段差异，不是纯 role 消融或全量成本估计 |
| 每响应 256 上限 | 11 例规范 C+EOS 在预算内；原创控制例为 276 内容 token+1 EOS，两种计数口径都超限。其 target 前 256 token 的 raw 实际被 parser 拒绝为 Invalid JSON |

控制例的全序列 A/B 为 1,181/1,233 token，说明可放入总上下文不等于可在当前响应上限完整生成。它仅用于边界检查；本次没有真实模型生成，也没有宣称所有 JSON 写法的最短长度。后续序列审计需单列响应预算/EOS计数、上下文、raw字节及parser边界；不能静默删样本、缩写标签或免费续写。

结构结论是：B 满足本组例保留原 system/assistant 控制角色的目标，A 不满足；B 可作为后续候选，CPU 不能证明模型质量更高。B 的工具 catalog 移到 system、原 system 仍为 JSON 字符串、旧格式要求与协议优先关系、tool 被模板放到 user 中的解释规则均在报告中保留，待 S0 ADR 和真实模型/训练适配器验证。

追加实际命令及日志（均复用原 CPU 环境）：

| 命令/范围 | 退出码 | 完整 log SHA-256 |
|---|---:|---|
| `P02_OUTPUT_FORMAT_PROBE.py` 加 `--compare-roles-to` 原 r3，完整 argv 见报告 | 0 | `5e6e6bdd5a0938025b67dc59fda253dc17af4a9f4a414968288f327a093fe716` |
| `.venv/bin/ruff check reports/data/P02_OUTPUT_FORMAT_PROBE.py` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| 原 `verify-preservation.py` 的本次只读检查 | 0 | `f1f684d4cd715fabe0ab988aac8c327657090c5cf075da9a922640604d59b2df` |
| 私有 `verify-role-comparison.py` | 0 | `18b4d4ed924f14b2fd6d6fdcf52355c1f3f22e5808f7f53adabbebc626d1db88` |
| `.venv/bin/python scripts/check_public_content.py`，170 路径 | 0 | `61186a06bf2a85c528548b80b369e98b6d78abf8aa755be6cc3e882ce1621c0c` |

比较实际运行于 `2026-09-06T04:47:02.923087+00:00`；追加首轮通过，没有新增意外失败，原 r1 tuple 失败仍保留。精确制品：

- 新探针：`31eb366ad7e222b6788b3c7d8684934d12ad71b2c171a44e2c989391f9dc94b8`；当前完整提案 Markdown：`02907e03825878b0ac3d91512d18be25c938794db5783ced495ab2b8991b5023`。
- 比较结果 JSON：`a093e0dd16f6406597e3bf3fcb21149e0f6c07e7be3c5f086f9c93fc25c45d83`（1,075,515 bytes）；12 行 A/B P/C/sequence hash 索引：`c88980abe55ff5951393f2f4bf77b64a8ee5420efe08cdba1b7c63d1922177c6`。
- 比较范围检查源码：`aa2aca35ea70b211ee4011529e36b7114afd38514d90f3a4ab8c662c6b40ce1c`；结果：`cd272f4bad702f0fa493c60e5a3628f278de21f51c7b3ea24ed71f053cbd1759`；本次人审/数据保留检查结果：`00768aeb0bf9851e1ee9c72fa9557e3552872ffd11da21ffe3e45bd3805fb4c7`。

范围检查确认 167 个非允许路径的原追踪文件逐字节未变，原交接索引中的 16 个私有证据文件和 13 份命令记录/log 未变，原三个公开文件的私有快照与原 Git SHA 一致。两份原构建各 18 项、人审 100 来源/114 决策、填写副本 hash 与原结果一致；未写任何 verdict。检查时本轮累计私有目录/日志 2,221,523 bytes，不含本检查随后写入的结果和封存日志，仍远低于累计 2GiB；没有新增环境或安装。

追加仍只改这三个允许文件，未接入 main 或推送远端；没有修改 src/tests/data/manifest/锁/契约/训练选择/协调状态。原 G-DATA、P04、独立审查及全部模型实验门槛未变。完成追加交接后结束本轮，等待 S0 正式 ADR/实现授权。
