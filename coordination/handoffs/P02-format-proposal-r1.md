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
