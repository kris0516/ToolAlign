# P02-format-r2｜Action JSON v1 实现与 CPU 证据

2026-09-06，D1，`work/p02-data`，gpt-6-astra / max。状态：**READY_FOR_REVIEW**。完整被测代码候选 `9f4e7a3f699a9d6cd9e444da2dc18f35f2cc9207`；本文和新 manifest/交接单仅增加证据，正式最终候选完整 SHA 由同轮原生交接给 S0。

8,228 条固定 Example 的新表示全部可逆且原文 parser 接收精确，0 序列失败；其中 **1,351 条总长超过 2,048，269 条 completion 含 EOS 超过 256**。完整分母和全部超限行保留，没有生成训练子集。最终组合 **664 passed / 0 skipped**；三份实际归档与 10 条默认 CPU 隔离安装命令通过。以上是 D1 自测，不替代 R1、S0 主干验收、G-DATA 或 P04。

**授权和提交关系。** 最终格式授权 `0c94ad58a78d30cd88a9ad86ac8e8d8c83b2442c`，冻结契约 `toolalign.contracts.v1`，ADR-0017 / [docs16](../../docs/16_MODEL_IO_FORMAT.md)。从原提案 `6c3d330e4b28be0fbc93c273bb2576f7317c69a8` 普通 merge 得 `88733d1878390c3c00b995a506344f74e30a0570`；实现和唯一全量测量绑定 `b33a55fba61d39f9da3c224ae6743c7cf6328cf6`。S0 同轮授权 `5212b24c0ef2d5442e190ed791a9b7008d8e0724` 已含验收的 P03 合并 `29a5e4c6affa2b822717fd3184b25ccb756e1651`，普通 merge 形成 `e086e1d1ece65fe2516b3992e1195ec61b4e5732`，父为 b33a55f 和 5212b24。包/边界探针提交 `0e64d2d345fb5e9758dd0a9c5902cc2894a0cb23`，原失败保留；修正测试的原 parser 错误预期为 `9f4e7a3f699a9d6cd9e444da2dc18f35f2cc9207`。没有 reset/rebase/cherry-pick 或改写原父提交。

全量运行使用先前明确允许的私有 P03 精确副本；合并后另以 `toolalign.tools._json.parse_action` 对同 12 条原始 C 验证。两份源码都是 `15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b`。最终核对测量所用源码/格式/协议/数据均未改，因此保留原测量，没有重跑全量 tokenizer。

**交付接口。** [纯格式模块](../../src/toolalign/model_io/format.py) 的 `validate_model_input` / `prompt_messages` 只接收 `{messages,tools}`，从可信冻结 subschema 独立验证，使用副本；不伪造 Example、目标或 catalog。历史关联与冻结规则相同：历史调用无需匹配当前 catalog/参数；目标检查由真实 Example 的 `training_sequence` 完整验证负责。`encode_action` 保留四种 kind、call_id/name/arguments/content。UTF-8 排序紧凑 JSON 后对字面角括号作可逆转义，普通文本中的 expected_action/oracle/split 仍保留。

[序列模块](../../src/toolalign/model_io/sequence.py) 接收可信应用显式提供的 renderer/encoder/decoder/EOS；编码 P+C 并核对独立 P 的前缀，一个追加 EOS，C 精确解码；显式右 padding，prompt/pad loss 为 0，C/EOS 为 1。causal input=`sequence[:-1]`，target=`sequence[1:]`，loss=`mask[1:]`，首末监督位置 `len(P_ids)-1` / `len(sequence)-2`。这是离线序列接口，不是 P04 trainer 的 packing 或梯度验收。回调接口的 template hash 是调用方声明的绑定；[可选 CPU 适配器](../../src/toolalign/model_io/offline.py) 才核验本机实际三文件字节、原模板和依赖版本。纯入口和导入该 optional 模块均不导入 tokenizer/模型框架；原 `data.LocalTokenizer` 默认实现未改。

格式为 `toolalign.action-json.qwen3-message-roles.v1`；完整描述 SHA `e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207`，instruction SHA `294d8540bd3ff8de84293d5d8b0f7e8f2537ee9cf1c81b95e81b6415f1039cee`，原模板 UTF-8 SHA `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`。包资源与 S0 descriptor 逐字节一致，安装后从资源加载，不依赖源码 cwd。固定模板 non-thinking / add_generation_prompt=True，native tools=None、无外层 native tool_calls。工具观察在官方模板中合并至 user/tool_response 控制段，内部原 tool 角色/索引/关联仍精确保留；CPU 恢复不证明真实模型必然正确遵守。

**同 12 例的新跨实现证据。** Python 3.14.7，native tokenizers 0.22.2 / Jinja2 3.1.6，与真实 AutoTokenizer Transformers 5.16.1 / tokenizers 0.23.2 / Jinja2 3.1.6 对照。HF 导入前 USE_TORCH/TF/FLAX=0、HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE=1；`local_files_only=True`、`trust_remote_code=False`，实际 model modules 列表为空。

同一组原创/公开 fixture canonical SHA `81347cd9f79a4e00478b07046a48d95b12f4b37f23396c2fb480e8923b9f3852`。两环境分别为 0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca` 和 1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` 建立身份，使用 D1 已有三份小来源文件；S0 已只读核验 T1 两模型对应文件完全相同，证明 SHA `83bafd8cfeedf25ef82f558ddb23eb5a1a333a2617cbaf2a461b9aadb24b7d3f`。这是同字节来源的两个身份绑定，不是两模型推理或两套权重测试。

[对照实现](P02_FORMAT_V1_CHECKS.py) 独立按规范重构消息/JSON，经各自真实 tokenizer 路径渲染编码，逐项核对完整 P、C、prompt IDs、P+C IDs、sequence、EOS、未 shift/shift mask、首末 target、右 padding、实际 rendered prompt 反向恢复及原 parser。每例再跑同小集确定性核对。24 个身份行逐项相等，独立样例分母始终 12；四种 Action、空白/非 ASCII、双工具、逆序观察、无 kind 历史、think/control 字面串均覆盖，旧 16 例跨库比较未重跑。

| 原创/公开样例 | P | C 无 EOS | C 含 EOS | 总长 |
|---|---:|---:|---:|---:|
| public_contract_tool_call | 485 | 34 | 35 | 520 |
| same_content_final | 402 | 35 | 36 | 438 |
| same_content_clarify | 402 | 36 | 37 | 439 |
| same_content_refuse | 402 | 36 | 37 | 439 |
| leading_newlines | 402 | 18 | 19 | 421 |
| whitespace_content | 402 | 16 | 17 | 419 |
| nested_two_tools | 796 | 206 | 207 | 1003 |
| history_observations_reversed | 1139 | 203 | 204 | 1343 |
| history_without_kind | 467 | 15 | 16 | 483 |
| literal_think_history | 495 | 37 | 38 | 533 |
| literal_control_tokens | 952 | 276 | 277 | 1229 |
| legitimate_metadata_words | 411 | 19 | 20 | 431 |

`literal_control_tokens` 的完整 C 为 276 tokens，加 EOS 为 277，总长 1229；其前 256 个 target token 送原 parser 的结果仍为 `Invalid JSON`。这是固定目标的截断诊断，不是模型输出分数，也不据此自动改变 protocol。

**固定全量审计。** [审计实现](P02_FORMAT_V1_AUDIT.py) 先验证原 manifest canonical `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756` 及全部 18 项文件。原 examples 文件 SHA `d45c815e9b775249c642cd3c9f624c28e7ab6505425cd6c009bfb06402c8f21f`，逐例与原 split 文件身份完全一致，仍为 train 7515 / validation 234 / test 215 / ood_test 264；原 8228 全是 tool_calls。仅表示层测量一次，没有转换来源、重分组、筛选、截断、改标签或模型评分。

逐例私有行包含原 Example/ModelInput/Action、source/revision/source-record/group/split、共同代码/描述/tokenizer 绑定、P/C/连接序列/mask/causal hash、长度、raw 限制/parser 与预算原因。实际反向恢复和 parser 精确通过均 8228/8228，缺测和错误均 0。以下所有分位的 measured/denominator 均为 8228/8228，采用 nearest-rank `ceil(n*p)`；完整分 split 的全部字段分位、缺测原因和统计均在[新 manifest](../../data/manifests/model-io-sequences.v1.json)。

| 字段 | P50 | P90 | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|
| action_depth | 4 | 5 | 6 | 8 | 10 |
| action_native_utf8_bytes | 225 | 558 | 667 | 977 | 2707 |
| action_nodes | 12 | 28 | 34 | 53 | 217 |
| completion_tokens | 76 | 193 | 231 | 318 | 1000 |
| completion_tokens_including_eos | 77 | 194 | 232 | 319 | 1001 |
| completion_utf8_bytes | 225 | 558 | 667 | 991 | 2707 |
| prompt_tokens | 1404 | 2124 | 2366 | 2822 | 4561 |
| total_tokens | 1505 | 2239 | 2503 | 2939 | 4615 |

| context cap | 总长合格 | 总长超限 | 总长且 C 含 EOS ≤256 | P+预留256 合格 |
|---:|---:|---:|---:|---:|
| 1024 | 1220 | 7008 | 1220 | 342 |
| 1536 | 4308 | 3920 | 4215 | 3310 |
| 2048 | 6877 | 1351 | 6685 | 6229 |

各格分母均为 8228。响应单独统计：C 含 EOS 合格 7959 / 超限 269；不含 EOS 合格 7967 / 超限 261。总长≤2048 且响应合格的 6685 条只是统计交集，没有成为训练选择。上下文 cap 和 256 来自明确固定的校准/协议边界，后续策略由 S0 另行登记。

| 原 split | 分母 | 总长 P50/P90/P95/P99 | 总长>2048 | C 含 EOS>256 | 两项均合格 |
|---|---:|---|---:|---:|---:|
| train | 7515 | 1547 / 2269 / 2529 / 2961 | 1344 | 230 | 6013 |
| validation | 234 | 1152 / 1605 / 1778 / 2074 | 3 | 17 | 217 |
| test | 215 | 1145 / 1698 / 1817 / 2050 | 3 | 13 | 201 |
| ood_test | 264 | 1144 / 1548 / 1698 / 1908 | 1 | 9 | 254 |

raw UTF-8 131072 bytes、值节点 8192、root=0 深度24 的限制全部单列；最大实际 raw 2707 bytes / 217 nodes / depth10。本次传原文 str 给 P03，不补 kind、不 unwrap、不修复。P03 的 str 前置长度检查按字符，解码后的 canonical bytes 另受限；审计另外直接统计 escaped UTF-8 bytes，没有把这两个定义混同或修改 parser。新增原创反例证明：合法 Action 也可能因转义后 bytes、节点或深度被原 parser 拒绝；节点/深度的内层 `JSON complexity limit` 会按原代码包装为 `Invalid JSON`。

**原证据保全。** 217 个公共受保护文件按最近授权来源逐字节匹配；原 11 个 data 模块、旧 tests/data、所有旧 manifest/政策/参数、原三份提案文件保持。两遍原构建各 18 制品完整验证；人审仍 100 来源/114 决策，填写副本 SHA `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`、0 verdict / 0 reviewer，本轮填写 0。原角色比较结果及 16 条旧命令日志 hash 保持。最后仅从已存在审计行独立重算统计和原身份，没有再次 tokenizer 测量。该阶段可枚举新增私有文件、日志及新模块 pyc 共 33098412 bytes，预算 2147483648 bytes；短命测试/build 临时目录已清理，不声称该数字是所有临时文件的精确累计。没有新增 tokenizer 环境或下载依赖。

**实际组合验证和包。** 最终 664 = 原已验证组合551 + 本轮 model_io113；包含固定真实 tokenizer 旧回归及 P00/P02/P03 独立反例。新增 raw probe 后的最终组合重新运行，0 failed / 0 skipped。pytest basetemp 为独立系统临时目录，无私有父目录导致的负例语义变化。

| 最终产物 | bytes | members | SHA-256 |
|---|---:|---:|---|
| default_wheel | 80146 | 44 | `a0aac74f1667ff860c850f96fd210acef02818187e7a80fbed869640d88b13ea` |
| rebuilt_wheel | 80146 | 44 | `a0aac74f1667ff860c850f96fd210acef02818187e7a80fbed869640d88b13ea` |
| sdist | 180780 | 87 | `e75cc4c86f9268215776d742676e1017d0a8d820f7aa47f2d6749c0a0ad42c84` |

sdist 为86个当前追踪文件逐字节匹配加 PKG-INFO；默认 wheel 由该次 sdist 生成，显式从它重建的 wheel 完全相同。44成员=39源码/资源+5metadata，无未知/缺失/重复/链接/逃逸成员。源码直接 wheel 路线 NOT_RUN。新包[核验代码](P02_FORMAT_V1_PACKAGE.py) 复用已有解释器与 offline cache，按 uv.lock 默认依赖 hash 安装到新私有 target；不是新 tokenizer venv。清除 PYTHONPATH/PYTHONHOME，从系统临时 cwd 用 `python -I -S`，仅该 target 与标准库参与导入。10 条子命令全退出0；39安装源码/资源匹配，12样例 prompt/Action/原 parser/纯序列接口和5类契约CLI通过；模型/可选 tokenizer 包均不可导入。此处纯序列的字符回调只是接口 test double，真实 Qwen token 对照由前述两环境证据提供。

**失败保留。** 一次 ruff 的新测试 import 排序错误已修正。第一轮包探针漏列 Hatchling 实际包含的受跟踪 `.gitignore`，补充其精确字节校验后通过，原归档和失败日志保留。新增 raw 边界 probe 首轮1 passed / 2 failed，因测试误预期内层复杂度错误；仅把测试修正为核对原 parser 的外层及 cause，源码未改，原失败提交0e64d2d保留。各轮测试与打包失败记录均保留；全部本轮已记录命令 argv、退出码、时间和完整 log hash 在[去敏证据索引](P02_FORMAT_V1_EVIDENCE.json)，本机保存完整输出及路径。

| 关键实际命令标签 | exit | 原始完整 log SHA-256 |
|---|---:|---|
| format-v1-fixtures-native-r1 | 0 | `e7a14f7d96c7efffd1d203d5aeba835ab04262f4f6d7e1b32814ee07ee346b22` |
| format-v1-fixtures-reference-r1 | 0 | `db53eca88ca401d41f6887331acf262e8092ddb99b4e3922fbc338903c5b2aa3` |
| format-v1-fixtures-compare-r1 | 0 | `77d1f0c3d9c4011a98251521937cd20df728023c2f4d5e25ae42d4c70a64cfe9` |
| format-v1-full-audit-r1 | 0 | `8a3cee17dec439f606af4126d294a84e11255030ca1d4291572d52d4b98712ce` |
| format-v1-merged-parser-r1 | 0 | `323e68a7cae01acb8c010e58ce906e141353e533c898e4fee0385f8b0f73b243` |
| format-v1-combined-cpu-r2 | 0 | `ab8992181072396d51b1a8e356e6eae93d595871cb730c297697fb1fcd790bd1` |
| format-v1-freeze-final-r1 | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| format-v1-lint-final-r1 | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| format-v1-build-default-r2 | 0 | `82d31ffae052a75fff03146d6f638542ff3241fceb8d999d6165edc635665189` |
| format-v1-build-rebuilt-r2 | 0 | `5fd406bdb468e91cecd4224d6898a1737df16a7d83ebf066cce78e69fd4295b8` |
| format-v1-package-verification-r3 | 0 | `fd24d9d24e2a5d2679c2b086c88e8977817954525b3c9c7129b9ce40bc965a5c` |
| format-v1-preservation-r1 | 0 | `999f3e1a0d0a0798f2897f67d31a7690e89e1367713bcd8e1ca01beb4ab5a7ab` |
| format-v1-final-scope-r1 | 0 | `24086242808112407199da32a252b00256aef32409740be74baad82ad4669f7d` |

公开扫描最终退出0，235个追踪路径，日志 SHA `1a9b666545d97f29026afcdf72071d5301ed84f580992cb49a115737c04c546e`；扫描为启发式检查，另做人工元数据/路径检查。

关键制品：逐行文件 SHA `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`；私有测量 manifest `07daedb35169d6fa4d6eae1c7663387380035971c15c88ae5461ff4e7f617d23`；公开 manifest `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47`；两环境比较 `9fd24c389d54992051fde3c9a8584be12cddd6316088c166f206d8659f0ee222`；最终归档 inventory `e364bcc8b9448efc90b59994996a9f016d2be50e8a8f04a86317c4a412ab8ceb`；隔离摘要 `a87fb5ef6090b2bf4c8a5ee7dcec75ef4baf9b746146012887725b2129882827`。原始身份/模板/依赖/渲染参数和所有派生 hash 均有定义，未沿用提案 v1-proposal 的 prompt/sequence 数值。

**复核入口。** 使用已有固定环境，精确来源文件与 private P03 副本须先核验上述 hash。两环境对照/一次全量原命令由证据索引逐条绑定；私有可信驱动 SHA `6208bfdb8e17a1d2885bb00b181252b4223a0f207bb0ebfc54f821dd50e72f20`，调用公开 CHECKS/AUDIT helpers，数据从不提供代码路径。P03 已合并后的 reviewer 可直接导入同 hash parser。不要为了复核无理由重复全量，先验证制品及小集。

```bash
PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR="$D1_TOKENIZER_DIR" "$D1_CPU_PYTHON" -m pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/review/P02/test_p02_boundaries.py reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py --basetemp="$SYSTEM_PYTEST_TEMP"
uv build --offline --no-python-downloads --out-dir "$NEW_ARCHIVES/default"
uv build --offline --no-python-downloads --wheel --out-dir "$NEW_ARCHIVES/rebuilt" "$NEW_ARCHIVES/default/toolalign-0.0.1.tar.gz"
python reports/data/P02_FORMAT_V1_PACKAGE.py --root . --archives "$NEW_ARCHIVES" --out "$NEW_PRIVATE_PACKAGE_CHECK"
```

路径变量的实际值只在本机证据登记；输出必须新建，禁止覆盖。生产实现没有注册或执行业务工具，也未修改模型 backend。真实训练/生成/GPU、BFCL/隐藏测试评分、训练选集、kris 人审/P04至少10条token-mask人工检查、trainer padding/packing/梯度、独立R1与S0新格式主干验收全部 NOT_RUN/PENDING。
