# P02-format-fix-r3｜真实 HF 加载状态与已核验字节绑定

2026-09-06，D1，`work/p02-data`，gpt-6-astra / max。状态：**IN_PROGRESS — 原审查同步前的阶段证据**。代码候选为 `b4dc1cf5c7d8c551506a7015bca2400573e16857`，父提交为原完整候选 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`。本报告、[证据索引](P02_FORMAT_FIX_R3_EVIDENCE.json)和[交接单](../../coordination/handoffs/P02-format-fix-r3.md)只增加证据；最终提交 SHA 由原生交接给 S0。

真实 HF 路径已改为从已核验内存字节建立私有快照，再实际调用 `AutoTokenizer.from_pretrained`。同一个文件时序反例在原候选出现声明身份相同而 `encode("!")` 从 `[0]` 变成 `[30]`；修复后为 `[0]`，完整 backend 状态与正常基线相同。原始失败、native 对照及全部开发失败均保留。最终适用组合检查 **675 passed / 2 skipped**；另外真实 HF 的本轮新测试 **13 passed**。同 12 个 fixture 的两套真实 engine 输出与修复前逐项一致，当前三个归档和 10 条默认 CPU 安装命令通过。这是 D1 修复自测，尚待独立 R1 复审和 S0 验收。

**授权和范围。** 本轮完整授权 `c6c02a5af084afe92c6e9f05d9d1c51392e805d0`；契约为 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`，格式仍按 ADR-0017 和 [docs16](../../docs/16_MODEL_IO_FORMAT.md)。从干净 7bada2e 继续，只改 [offline.py](../../src/toolalign/model_io/offline.py)并新增 [test_snapshot.py](../../tests/model_io/test_snapshot.py)。既有 `test_offline.py` 未改，其他格式/序列/资源/fixtures、数据、P03、旧审查、规范、依赖与状态只读。本轮没有接入随后 main/P01；现已收到 S0 同轮授权 `6272ad512b947b9cf14c5f7201b7807f7f188e13`，准备普通 merge 唯一公开 review `2942e568eae91d0292ad9691af133bbd8c33dd02`；合并后验证尚待本轮补充。原候选和全部父提交保留。

**缺陷与修复。** 原 reference loader 在 `_source_bytes` 返回后仍从调用方原目录读取，而结束时重查原路径不能证明 HF 实际加载的是先前核验字节。受控文件时序在读取 LICENSE 时交换已经读过的 tokenizer vocab ID，再在末次校验前恢复，因此两次来源 hash 相同而实际 tokenizer 不同。

新 `_reference_from_snapshot` 只把本次已核验的 `tokenizer.json`、`tokenizer_config.json`、`LICENSE` buffers 写入新建临时目录；独占创建文件，加载时文件权限 `0400`、目录 `0500`。真实 HF 使用 `local_files_only=True` / `trust_remote_code=False`，核对加载后的模板；成功和异常均释放私有目录。HF 已在返回前完成本适配器需要的加载，目录清理后实际渲染、编码和解码仍通过。I/O 或 JSON 加载异常转为 `tokenizer_reference_snapshot_load_failed`。native 仍从已核验的 tokenizer buffer 构造，未伪装成 reference。

原目录的附加 token、special token map、vocab/merges、额外模板或 model config 均不进入快照，也不会作为 override 被 HF 读取。加载状态不再取决于原目录在核验后的更新；既有文件在核验前遭篡改仍按原 size/hash 检查拒绝。这是来源加载绑定，不是同一 OS 用户任意篡改私有目录的安全隔离承诺。错误清理测试故意操作自己新建的私有快照来触发真实文件/JSON 异常，不以此宣称 OS 攻击防护。

**固定来源与代码映射。** 三份来源 SHA-256 依次为：

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| tokenizer.json | 11422654 | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` |
| tokenizer_config.json | 9732 | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` |
| LICENSE | 11343 | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` |

官方模板 SHA `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`、描述 SHA `e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207`、instruction SHA `294d8540bd3ff8de84293d5d8b0f7e8f2537ee9cf1c81b95e81b6415f1039cee` 均未变。模型身份仍为 Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca` 和 Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`；两者对应的三份小来源文件相同，沿用原来源绑定证据，不是模型权重测试。

`offline.py` 从 SHA `6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30` 变为 `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`。格式投影、Action 编码、连接序列、EOS 和 mask 算法全部保持；`tools=None`、non-thinking、generation prompt、`add_special_tokens=False`、EOS 151645 及真实版本身份未改。

**反例与相关场景。** S0 封存 proof SHA 为 `d33051b56aea3fc8588c47aa26e713b20b0783aca0d4f74f0e631f1a1d836510`。封存的 `review_snapshot.py` / `review_support.py` / `review_tokenizers.py` 分别为 `5b3f55d7fdddb2399b5ca7a8d0558dbbc51ce45715a163ec49b806d1ef37f2fc`、`3e712ce8358bae5e1f489fc898af7d75f326e37e7d6bb792f7a23cd0e13903a9`、`cd16584169c42861ada99567a89a22f4a59d33a55fd8b20a94df4095320d7ee3`。这是 S0 核验的未提交 R1 源码快照，不能称为正式独立审查交接。D1 校验并复制到本轮新私有目录，探针仅修改其新建来源副本，未修改 R1、S0 或旧来源目录。

| 实际执行 | 退出码 | 关键结果 | 完整日志 SHA-256 |
|---|---:|---|---|
| 原 7bada2e / reference | 1 | identity 相同；`!` 为 `[30]`，基线 `[0]` | `9b1e5469b55f6487f2c3180cd94f85b7c9edb6c775592d73dcf92aa86034e48b` |
| 原 7bada2e / native | 0 | identity 和实际状态相同 | `c84cfa0a9947f27f4df4a9f1cd2fe794aefac16be529f4d019d5f133fdc388c3` |
| 修复后 / reference | 0 | `!` 为 `[0]`；实际 backend 与原正常基线相同 | `781d781b496a06f646968a72c524164f02119b59e5cef47ec4f44f2a0c102e93` |
| 修复后 / native | 0 | 原状态保持 | `c84cfa0a9947f27f4df4a9f1cd2fe794aefac16be529f4d019d5f133fdc388c3` |

主回归只控制文件打开时序，真实 loader、返回值、identity 和期望 hash 均未 mock。reference 原正常 backend SHA `a373b7ff0c52176575a72ede185c306613ef1c01a2346f900f3b631ce1dc23f9`，受影响时为 `748f7b64298cf6ec3e9a1641b1dd32dcbe82088f174c434987cbcd6b4b46a0fa`；修复后恢复前者。来源三个文件在 before/after 探针结束时都恢复原 hash。

新增 pytest 包含 13 个参数化场景：正常来源、校验后同尺寸 vocab 替换、不同尺寸替换、config 更新、额外模板；真实私有文件写入失败和 HF JSON 读取失败；三个来源文件各自核验前的同尺寸和不同尺寸篡改。前五项核对真实加载状态和声明身份，reference 同时检查实际快照的 buffer hashes/权限及清理；两个异常场景核对稳定错误与目录清理；六项预存篡改按原检查拒绝。实际 HF 13/13 通过。另以封存探针在两 engine 各跑同 10 个来源邻例：七种额外文件均被忽略且状态相同，三个预存同尺寸篡改拒绝。这里是 10 种场景的两次 engine 执行，和 pytest 有重叠，不合并成 33 个独立场景。

开发首轮新 pytest 为 **7 failed / 6 passed**，日志 SHA `4864b20f51d1df4c1dc3411a36a27f8fc0044e5538a5a7a4ea4e2a4e39912063`：测试审计钩子未归一化临时路径别名，且 vocab 正则没有绑定原数字 ID。仅修正测试路径解析和匹配条件后，13/13 通过，日志 SHA `61553e5efa7043117cebd74c468ccf6a6d8b51acc17548e2e9a952c297c7dade`。失败测试源 SHA `7f21b15633516c4b4fb515811e516e90713d497e388924727b5acd563a0f7ae8` 与原日志保留；生产修复字节未因此变化。before 在干净 7bada2e 执行；初次 after/来源探针/新 pytest 执行时 HEAD 仍为 7bada2e，但工作树 loader 已是上述 f1354c3。源码快照明确绑定这一点，不把当时运行伪写为已提交 b4dc1cf。之后 b4dc1cf 的 fixtures、组合 CPU 和包验证使用同一最终源码。

**同 12 例与旧测量保持。** 复用既有 Python 3.14.7 环境；native 为 tokenizers 0.22.2 / Jinja2 3.1.6，reference 为真实 Transformers 5.16.1 / tokenizers 0.23.2 / Jinja2 3.1.6。reference 导入前禁用 Torch/TF/Flax 并设离线标记，探针断言无模型框架/模型模块。两个固定模型身份分别执行同 12 个原 fixture，逐项核对 P、C、完整 prompt/连接/sequence IDs、追加 EOS、completion-only/causal mask 和监督位置，再与原 v1 对应记录及角色绑定比较。每 engine 24 个身份行，独立 fixture 仍为 12。封存检查器另按规范构造期望表示并以真实库路径核对；它在本轮由 D1 运行，不代替 R1 独立结论。

新普通记录的所有实际字段、角色绑定、声明身份与旧记录相同；两 engine 的实际记录逐项相同，实际 backend 状态也与本轮 before 的旧代码正常基线相同。新 native/reference result SHA 为 `680986e8c0858d8838596f31dbb18683aef281668771c7180a6f750804db3a43`、`9e9a2ada92cea6a6445fa430927bcde78e2d8fa21f56453037c73ee917caa3fd`。比较结果 SHA `f21b256452d062a427b2ec6119f3558bc74173d371542a943c399a7f28e2686f`。

原 native 8,228 行审计继续绑定 `b33a55fba61d39f9da3c224ae6743c7cf6328cf6`、原 loader 6d1a447、输入/hash/运行时间；原私有 manifest SHA `07daedb35169d6fa4d6eae1c7663387380035971c15c88ae5461ff4e7f617d23`，rows SHA `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`。原公开序列 manifest SHA `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47` 未改。新全量测量次数为 0；S0 已送达正式原 R1 review 及其证明，后续在本轮读取对应历史结果并登记；此前 D1 未读取或改写 R1 全量测量，不将其重标为修复后执行。

**组合 CPU 与当前包。** 在 b4dc1cf 上使用既有组合命令运行全部 tests 以及未修改的 P00、P00-r2、P02、P03 lifecycle/semantics 独立测试：675 passed / 2 skipped，45.17 秒，日志 SHA `f5f4d626956e4e55ca0edf8c692616dd6546b6e55c70a83f4fff81fe5777f287`。其中既有 664 项加新增 native 11 项，两个 skip 仅为 HF 专属异常清理，已在单列 reference 13 项中实际执行。没有把另行安装重复或上述重叠场景累加进 675。完整 ruff、四份冻结契约和公开扫描均通过。

| b4dc1cf 实际归档 | 成员 | 字节 | SHA-256 |
|---|---:|---:|---|
| sdist | 88 | 183443 | `2c6d911e5b185e36a82bcc7b9f854be7b0cac40bea61c57e38003272f37508af` |
| 默认 wheel | 44 | 80633 | `239bfd4ab678ac3cbe2baba935f3cc5b642aa15c3378995b671ec329d036aac9` |
| 显式从该 sdist 重建 wheel | 44 | 80633 | `239bfd4ab678ac3cbe2baba935f3cc5b642aa15c3378995b671ec329d036aac9` |

默认 `uv build --offline --no-python-downloads` 实际从同一 sdist 构建 wheel；另显式重建。源码直接 wheel 为 **NOT_RUN**。沿用未修改的原包检查器，在本轮新 target 只安装默认 CPU 依赖，使用既有 Python 的 `-I -S` 从系统临时 cwd 检查；39 个包源码/资源与当前 Git 字节相符，12 个 fixture 的投影/编码/序列/parser 接口及五类契约验证通过。10 条安装/接口命令均 exit 0，实际安装仅六个默认包，可选 tokenizer/模型包不可导入。序列回调在此是透明字符测试替身；真实 Qwen 检查已在上述两个 CPU 环境单列。package summary SHA `e542e0195407bdf85540cb8b38ff8dfeebb97fc286b00e94c20507a3569e8f12`。最终证据文件不属于归档载荷，交接前再校验其余当前成员仍与已测 b4dc1cf 一致。

**保全和复现。** 范围检查逐字节核对原候选除唯一被修 loader 外的 **234 个公共文件**，以及原 v1 的 **620 个私有制品、37 组原命令元数据与日志**；原失败均未覆盖。原两次构建各 18 个制品实际通过原 manifest 校验，canonical hash 仍为 `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。100 来源/114 决策人审包和填写副本 SHA 保持；CSV 仍为 `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`，没有填写判断。首个最终范围结果 SHA `f6ed0297268d475dd70154b8f97dffa4c8368038d641c582add6b3e3679e8660`。

证据索引列出全部本轮实际 argv、环境设置、时间、退出码、完整 log hash、私有命令元数据 hash 和源/结果文件 hash；本机路径用别名，原文只在私有材料中。复现需已授权的三文件来源和既有两个固定 CPU 环境，参考命令为 `PYTHONPATH=src TOOLALIGN_TOKENIZER_DIR=SOURCE TOOLALIGN_SNAPSHOT_ENGINE=transformers USE_TORCH=0 USE_TF=0 USE_FLAX=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 REFERENCE_PYTHON -m pytest -q tests/model_io/test_snapshot.py`；SOURCE / REFERENCE_PYTHON 是明确占位符，不是额外下载请求。主反例按封存 SHA 对应脚本和证据中的真实参数复现。

本轮新私有目录与命令日志在范围检查时共 278972044 字节，低于 2 GiB；这是已保留文件的实测量。临时来源副本/快照由小型场景限定并由各自运行者清理，未把未仪表化的累计临时写入报告为精确测量。新 tokenizer 环境、下载、权重、模型/GPU、云费用、公开上传、来源重建、8,228 行重跑均为 0。正式格式验收、G-DATA、训练选择、P04/P05/P06、模型质量和部署均未完成；后续由 S0 独立分发，不由本修复自行推进。
