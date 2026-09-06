# P02-format-review-r2｜独立复审

**PASS；P0=0 / P1=0 / P2=0。原 F1/P2 已关闭。** R1，2026-09-06，gpt-6-astra / max，分支 `review/p02-format-r2`。唯一被审 candidate 为 `8c439f683b9d6b04919ff1f7184d8924ccf82f9f`，parent `6c82d29ddaade349d3e2a15f50d35214dbc7bf8d`，tree `0695bd9605148be3304ba8824506098bdfa9bc46`。原 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57` 的正式审查 `2942e568eae91d0292ad9691af133bbd8c33dd02` 仍是 **FAIL / P2=1**，没有回写。

授权为 `41233633ac9aeaf72e66b280908bc0156149c0f2` 及 S0 对该精确候选的原生派发。已读取并私有保存 AGENTS、任务包 r2 与最后核验段、coordination.v1、状态/GOAL、ADR-0017、docs16 和 descriptor。契约继续为 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`。只新增本目录与[本轮交接单](../../../coordination/handoffs/P02-format-review-r2.md)，候选实现、测试、原审查和旧私有材料均未修改。

**范围与历史。** 独立 Git 核验确认生产修复 `b4dc1cf5c7d8c551506a7015bca2400573e16857` 直接以原 7bada 为父，只改 `offline.py` 并新增 `test_snapshot.py`。证据 checkpoint `7b8ef310db214845ef5ac1fabfef1e37e9e05ab0` 以 b4dc1cf 为父；普通 merge 6c82d29 的两个父为 7b8ef31 与公开原 review 2942e568；最终 8c 只更新三份 D1 修复证据。原 234 个未修文件和 12 份原 review 逐字节保持；本轮全部 251 个候选文件保持。未合入随后 main/P01。原本地 `f7086413a9fedd9e2a473ac6d2869efff74ddad5` 及原分支保留，且不是 8c 的祖先；本轮不推送它或其后代。

**F1 的独立关闭证据。** 首先核验 D1 在原 7bada 的实际 before 元数据、退出码与原始日志，再与原 R1 源码及默认 wheel 的结果逐项比较：真实 reference 均为相同 FAIL，声明身份不变而 `!` 从 `[0]` 变成 `[30]`；native 均 PASS。原 reference 失败结果 SHA 为 `f9914dd049865afc3abe8ddc91a4f03897d0bdf2ccd4cc9918d5e4e5975dbaa1`，原 source log SHA 为 `9b1e5469b55f6487f2c3180cd94f85b7c9edb6c775592d73dcf92aa86034e48b`。

随后在精确 8c 源码及本轮实际构建、安装的默认 wheel 上复跑**未改的原 [review_snapshot.py](../P02-format/review_snapshot.py)**。该脚本及两个 helper 与原公开 review 的 SHA 分别仍为 `5b3f55d7fdddb2399b5ca7a8d0558dbbc51ce45715a163ec49b806d1ef37f2fc`、`3e712ce8358bae5e1f489fc898af7d75f326e37e7d6bb792f7a23cd0e13903a9`、`cd16584169c42861ada99567a89a22f4a59d33a55fd8b20a94df4095320d7ee3`。

| 本轮实际路径 | 退出码 | 声明与基线相同 | 实际 backend 与基线相同 | `!` |
|---|---:|---|---|---|
| 源码 / reference | 0 | 是 | 是 | `[0]` |
| 源码 / native | 0 | 是 | 是 | `[0]` |
| 默认 wheel / reference | 0 | 是 | 是 | `[0]` |
| 默认 wheel / native | 0 | 是 | 是 | `[0]` |

新 reference 的 source/installed 结果完全相同，SHA 为 `a5672aeb79df254d9bb91651cff88824a2700a07d22c262687d4b8d08814663c`；native 两者均为原正常结果 SHA `8c9805d1c8af0040052e6682f03f8979be6af66f1ee36b58936ea1788359d117`。reference backend SHA 保持 `a373b7ff0c52176575a72ede185c306613ef1c01a2346f900f3b631ce1dc23f9`，未出现原错误状态 `748f7b64298cf6ec3e9a1641b1dd32dcbe82088f174c434987cbcd6b4b46a0fa`。四次执行是同一 F1 场景的引擎/安装重复，不是四项发现。

修复后的 [offline.py](../../../src/toolalign/model_io/offline.py) SHA 为 `f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3`，原为 `6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30`。真实 `AutoTokenizer.from_pretrained` 只接收从已核验三份 buffer 写出的新临时目录，使用 `local_files_only=True`、`trust_remote_code=False`。原目录不再交给 HF 重读；没有新增原路径重查、放宽身份、替换库返回值或用 native 伪装 reference。实际所读快照只有 tokenizer JSON、config 与 LICENSE，首读 hash 等于固定来源，文件权限 0400、目录 0500；返回或异常后目录已删除。

**来源邻例与清理。** 原来源探针在两 engine 各跑同 10 个场景：三份必需文件各自的同尺寸篡改均拒绝；七种静态附加文件均不影响实际状态。旧 HF 会拒绝不同/命名模板，本修复将这些未绑定附加模板与其他 extras 一并忽略；这是明确的附加文件处理变化，固定三文件上的正常表示保持不变。

新增 [review_neighbors.py](review_neighbors.py) 独立核对 7 种情形：来源与快照清理后的继续使用、已核验 JSON 随后改变尺寸、已核验 config 随后更新、七种附加文件同时存在、真实排他文件写入失败、真实 HF JSON 加载失败、真实加载模板不匹配。前四种在 native/reference 各执行；后三种仅适用于 reference。共 4 次 native 与 7 次 reference 场景执行，与既有测试重叠，不相加为独立问题数。

四种成功情形都在删除本次来源副本及 HF 快照后，重复运行原 12 例的 render/encode/decode/sequence/parser；实际状态、完整输出均等于正常基线，未重新打开已删来源或读取附加文件。三种错误均产生对应稳定 `ModelIOError` 且清理临时目录。错误检查只故意损坏本次私有快照以走真实异常分支，**不是同用户 OS 任意攻击隔离证明**。主 F1 和这些邻例都未 mock loader 方法、返回值、identity 或期望 hash。

**规范与回归。** 原 [56 项结构/序列检查](../P02-format/test_independent.py) 和 [4 项统计边界检查](../P02-format/test_audit_denominators.py) 按未改字节重新执行。standalone ModelInput、原生有限 JSON、历史关联、合法历史工具、隔离副本、四类完整 Action、call_id/参数/content、控制字符和非 ASCII 往返、合法同名词保留与额外标签拒绝、公开错误字符串边界均通过。序列重新核对 `encode(P+C)` 的稳定 P 前缀、精确 C 解码、唯一追加 EOS、completion-only/causal shift 和右侧 padding；错误身份、边界变化与截断仍拒绝。字符 callbacks 是纯接口替身；其 template hash 是可信调用方声明，不能当作实际读模板的证明。

| 实际 pytest 组 | 通过 | 跳过 | 说明 |
|---|---:|---:|---|
| 全部适用旧 CPU/真实 native、P00/P02/P03 独立检查及候选新增测试 | 675 | 2 | 含原 664 项与新增 native 11 项；44.78 秒 |
| 原 R1 结构/统计独立检查，另组调用 | 60 | 0 | 保留原同名测试与全局收集规则；0.12 秒 |
| 真实 reference 的候选 snapshot 测试，单列 | 13 | 0 | 包括上组跳过的两个 HF 专属清理场景；8.93 秒 |

前两组无重叠，为 **735 passed / 2 skipped**；reference 13 与其中 11 项场景重叠，单独登记，不相加成一次无 skip 的总回归。私有 pytest 启动器有 multiprocessing 主入口保护。全仓 Ruff、四份冻结契约检查通过；本轮公开扫描与历史载荷检查见证据/交接封存。

**真实固定 tokenizer 与同 12 例。** 复用 Python 3.14.7 的两个原 CPU 环境，没有新建 tokenizer 环境或联网下载。native 为 tokenizers 0.22.2 / Jinja2 3.1.6；reference 为 Transformers 5.16.1 / tokenizers 0.23.2 / Jinja2 3.1.6。两个环境各自 `uv pip check --offline` 通过。导入前禁用 Torch/TF/Flax、设置离线及禁用遥测，并实际检查无模型框架或具体模型模块。reference 的五份库 loader 源码 hash 与原 R1 完全相同。

使用未改的原独立 tokenizer/控制段探针，在两条真实库路径与生产适配器之间重新比较每例完整 P/C、prompt/连接/sequence IDs、EOS、loss/causal masks、shift 首尾和 padding。原 system/assistant 控制段、tool_response 分组、内部 role/index/call_id、无历史 kind 猜造、键值转义和原 P03 raw parser 均保持。两个模型身份共用相同来源：Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca`；Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。每 engine 24 个身份行，**独立 fixture 仍为 12**。

本轮 native/reference 完整 result SHA 分别为 `680986e8c0858d8838596f31dbb18683aef281668771c7180a6f750804db3a43` / `79fd96ef8f6d8d1d4fe454807218f3166fd54f2704becff1ef93056b2ae13e88`，与原 R1 逐字节相同，也逐项符合 D1 原 v1 和修复后记录。R1 reference 的 fsspec 保持 2025.3.0；D1 既有 reference 的 2026.7.0 单独保留，未混标。

**新归档与实际安装。** 本轮对精确 8c 新执行默认 sdist→wheel 构建及显式 sdist 重建，并以当前 Git blobs 核对完整成员集合、每个载荷字节、重复项、链接/逃逸边界和 metadata。结果与 D1 较早归档恰好同 hash；这里有本轮独立运行时间和日志，不把旧制品冒充新执行。

| 本轮归档 | 成员 | 字节 | SHA-256 |
|---|---:|---:|---|
| sdist | 88 | 183443 | `2c6d911e5b185e36a82bcc7b9f854be7b0cac40bea61c57e38003272f37508af` |
| 默认 wheel | 44 | 80633 | `239bfd4ab678ac3cbe2baba935f3cc5b642aa15c3378995b671ec329d036aac9` |
| 显式从该 sdist 重建的 wheel | 44 | 80633 | `239bfd4ab678ac3cbe2baba935f3cc5b642aa15c3378995b671ec329d036aac9` |

sdist 含 87 个 Git 载荷与 PKG-INFO；每个 wheel 含 39 份源码/资源及 5 份 metadata。新 target 安装的是**默认 wheel**。10 条实际默认安装/接口命令通过：外部临时 cwd、`python -I -S`、仅六个默认 distributions，39 份源码/资源匹配；descriptor/投影/Action/字符序列/P03 parser 的同 12 例接口、契约 digest 与五类 CLI 验证通过，无可选 tokenizer/模型依赖。

真实可选 engine 的安装检查另用既有允许环境和 `python -I -B`；[run_installed.py](run_installed.py) 只选择实际安装 target 与未改原探针，逐模块验证文件路径和 wheel hash。原 F1 每 engine 七个 ToolAlign 模块全部来自 target，源码导入为 0。另在安装 reference 上实际删除来源/快照后复核同 12 例所有适配器操作；14 个实际 ToolAlign 模块仍全来自 target。该安装重复不增加独立 fixture 数。**源码直接 wheel 路线为 NOT_RUN。**

**旧全量审计与数据保持。** [review_history.py](review_history.py) 只读核验旧两套各 18 制品及原输入/manifest/行文件，并对已测行重核八个指标分位和所有全量/分 split 的上下文、响应、预留预算与 raw/parser 统计，没有调用 tokenizer 或重建来源。两套原数据 canonical SHA 仍为 `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`。原人审材料、100 来源/114 决策填写副本保持；CSV SHA `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`，仍为 0 reviewer / 0 verdict。

旧 native 全量仍绑定 `b33a55fba61d39f9da3c224ae6743c7cf6328cf6` 与原 loader；原 R1 唯一 reference 全量仍绑定 7bada、原环境及 2026-09-06 07:10:35–07:10:57 UTC。两者 rows SHA 均为 `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`；旧公开 manifest SHA 保持 `69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47`。原 R1 全量 log SHA 仍为 `63c2fc41b766e4ae939d0062a1b9c65634e9a492694a7a111d13891fb1fdfe18`。

| 原分层 | 完整分母 | 总长含 EOS > 2048 | C 含 EOS > 256 | 两项均合格 |
|---|---:|---:|---:|---:|
| train | 7515 | 1344 | 230 | 6013 |
| validation | 234 | 3 | 17 | 217 |
| test | 215 | 3 | 13 | 201 |
| ood_test | 264 | 1 | 9 | 254 |
| 全量 | 8228 | 1351 | 269 | 6685 |

源映射明确承认 `offline.py` 变化；其余绑定格式/序列/指令/描述符/parser 字节保持，新正常小集完全相同。因此按授权**本轮 8,228 行重测次数为 0**，没有修改旧 manifest、重标旧测量 commit 或将 6,685 交集用作训练选集。新代码的全量重新编码属于 NOT_RERUN，不是本轮运行结果。

**证据保全、失败与边界。** [review_bindings.py](review_bindings.py) 核对 D1 原 v1 的 620 个私有制品/37 组命令、新修复的 542 个私有制品/39 组命令，以及原 R1 的 37 个登记私有材料/42 条验证与发布日志。集合按各自身份分别登记，不与 S0 其他核验计数相加。原真实 F1 失败、R1 旧 guard/启动器/发布错误、D1 旧测试与收集失败均原样保持。

本轮登记验证无非零退出。复制包检查器后、首次执行前仅规范化新附件的一处导入排序，未改原附件或候选；没有新增全局 Ruff 例外。所有实际 argv、退出码、时间、log hash 和脚本/结果身份见 [evidence.json](evidence.json)。公开 argv 使用角色占位符；原 argv/log 与系统路径只保留私有。索引封存后的最终公开扫描/提交核验由私有 completion 及原生交接绑定，避免自引用 hash。

新增私有材料和明确列出的本轮临时测试目录均计入容量封存，低于 2 GiB；复用环境不算新环境。记录的保留容量不是未仪表化的累计临时 I/O 或精确峰值。模型/权重/GPU、训练、正式评分/BFCL、费用与上传均未执行；不代签 kris 人审。原 P03 parser 的字节/节点/深度与 registry 边界保持，格式转换不授予工具执行权。

本结论仅为该候选的格式与 CPU 技术复审。S0 最终 CI、普通合并和 main 验证仍待进行；**G-DATA、真实模型质量、训练选择、P04 token/mask 人审与训练授权仍未通过或未运行**。提交本轮独立 review 后结束该轮，由 S0 接续。
