# P02-format-review-r1｜独立审查

**FAIL — P0: 0 / P1: 0 / P2: 1。** R1，2026-09-06，gpt-6-astra / max，分支 `review/p02-format-r1`。被审候选为 `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`，parent `9f4e7a3f699a9d6cd9e444da2dc18f35f2cc9207`，tree `fdf0c10eef3f5ea5d37506a0f8973edd4854ee98`。审查授权 `1de90781e42a3693b112aafcf585a905bc052d63`；读取其 AGENTS、任务包、coordination.v1、状态/GOAL、ADR-0017、docs16 和完整 descriptor。后续修复不纳入本轮判断。

**去敏公开映射。** 原本地审查 commit 为 `f7086413a9fedd9e2a473ac6d2869efff74ddad5`。S0 在发布前发现派生 evidence.json 的一条安装命令仍带实际系统临时路径；这是 R1 发布附件遗漏，不增加候选缺陷数。依据同轮授权 `085a61c2d0d12d3bde05658259e566aac6ec27ed`，新分支 `review/p02-format-r1-public` 以原 candidate 为唯一父提交创建去敏公开 review，最终新 SHA 通过原生交接给 S0，**不等于原本地 SHA**。原分支和全部私有原命令/log/result 字节保留，本地原 commit 不进入新公开祖先。新 tree 仅调整公开路径角色映射、发布说明及相关公开文件 hash；235个候选文件、8个探针与 Ruff 配置逐字节保持，原 FAIL/P2=1 和测量数字不变，未重跑测量。公开命令中的角色占位符不是原始 argv，所列原始 hash 仍绑定未修改私有记录。新分支由 S0 独立核验后决定推送，本轮 R1 不 push。

原有 **664 pytest 项通过**，新增 **60 独立 pytest 项通过**；同 12 个原始公开/原创 fixture 的真实 native/reference 结果一致。独立参考路径对 **8,228 行进行一次全量重算，全部逐行字节及分层统计一致**。新 sdist、默认 wheel、显式从该 sdist 重建的 wheel 及默认安装接口通过。然而 optional HF adapter 在加载过程的同长度文件替换场景中报告错误的来源身份，故本候选不能取得完整格式技术 PASS。

**F1 / P2：HF 加载使用可变路径，前后文件核验不能证明实际加载了已验证的快照。** 位置：[offline.py](../../../src/toolalign/model_io/offline.py)，107–110 行；该文件 SHA `6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30`。构造器先读取三文件至 `data`，随后 `AutoTokenizer.from_pretrained(str(root), ...)` 再读目录，最后比较模板与重新读取的三文件。若读取期间目录被更新，并在最后检查前恢复，两个 hash 检查可以都通过，而 tokenizer 已装入中间内容。这破坏了 identity 对实际 token ID 的绑定，不能由模板相等或 EOS 一致补足。

[review_snapshot.py](review_snapshot.py) 在新建的私有来源副本上，用 Python 文件打开审计事件安排确定的文件替换次序。先保持原序列化、总长度和全部 token 文本，仅对调 tokenizer vocabulary 中 `!` 与 `?` 的 ID；已验证 tokenizer JSON/config 缓冲读完、LICENSE 打开时换入文件；HF 再次读取 JSON 后，在第三次打开 JSON（最后来源核验）前恢复原文件。未 patch AutoTokenizer、tokenizers 方法、返回值、identity 或期望 hash，没有线程计时假设。受保护的原始来源始终只读。

| 实际路径/邻例 | 结果 | identity | `encode("!")` |
|---|---|---|---|
| 原三文件，HF 固定参考环境 | PASS | 固定原身份 | `[0]` |
| 同长度替换/恢复，HF 源码路径 | **FAIL** | 仍与原身份完全相等 | **`[30]`** |
| 同长度替换/恢复，native 源码路径 | PASS | 原验证快照 | `[0]` |
| 同长度替换/恢复，HF 默认 wheel + 既有参考环境 | **FAIL** | 仍与原身份完全相等 | **`[30]`** |
| 同长度替换/恢复，native 默认 wheel + 既有 native 环境 | PASS | 原验证快照 | `[0]` |
| 不同长度替换，HF 正常拒绝邻例 | PASS | `tokenizer_source_size_mismatch` | 未建立对象 |

HF 三个原文件在调用前后都恢复到固定 hash；模板和 EOS 仍正确，实际完整 backend JSON 状态 SHA 却从 `a373b7ff0c52176575a72ede185c306613ef1c01a2346f900f3b631ce1dc23f9` 变为 `748f7b64298cf6ec3e9a1641b1dd32dcbe82088f174c434987cbcd6b4b46a0fa`。替换文件 SHA 为 `5340fa498d7bf49141374d0e053184d08be2264116272b25a3ed4d2d80213da7`，长度仍为 11,422,654 bytes。安装复现使用 `python -I`、独立 target 和既有可选 CPU 依赖；逐模块确认七个 ToolAlign 导入均来自已验证默认 wheel，源码导入为 0。它与仅六个默认 distributions 的纯接口验收是分开的检查。

建议由 D1 使 HF loader 消费已验证的稳定来源快照，或对实际已加载状态建立等价验证，再用同一原探针做 before/after；不能只增加一次对原可变目录的读取。本轮没有修实现。该场景需要加载期间的文件变化；普通静态附加文件没有在本轮产生相同问题，已验证全量文件也没有发现污染。

| F1 精确证据 | SHA-256 |
|---|---|
| 原探针 review_snapshot.py | `5b3f55d7fdddb2399b5ca7a8d0558dbbc51ce45715a163ec49b806d1ef37f2fc` |
| 公用独立 helper review_support.py | `3e712ce8358bae5e1f489fc898af7d75f326e37e7d6bb792f7a23cd0e13903a9` |
| 实际状态观察 helper review_tokenizers.py | `cd16584169c42861ada99567a89a22f4a59d33a55fd8b20a94df4095320d7ee3` |
| 源码 HF 原始失败结果 JSON | `f9914dd049865afc3abe8ddc91a4f03897d0bdf2ccd4cc9918d5e4e5975dbaa1` |
| 源码 native 通过结果 JSON | `8c9805d1c8af0040052e6682f03f8979be6af66f1ee36b58936ea1788359d117` |
| 源码 HF 原始失败 log | `9b1e5469b55f6487f2c3180cd94f85b7c9edb6c775592d73dcf92aa86034e48b` |
| 安装 HF 原始失败 log | `0f4c1f480337bdc66db72784f2e1b770b4610bbb80fec3152ed3120b9484f6e7` |

**规范与纯接口。** [test_independent.py](test_independent.py) 的 56 项原创检查覆盖 standalone ModelInput 无伪造目标、合法历史工具无需符合当前 catalog、逆序关联和 pending/重复/复用 ID、原生有限 JSON、冻结数组边界及 ToolSpec schema、嵌套隔离副本、四种完整 Action、数据键/值控制标记和非 ASCII、额外标签拒绝而同名字词保留、异常公开字符串不包含输入 sentinel。错误 cause 链沿用冻结 validator，本轮不把公开错误字符串的证明扩大为整条 traceback 脱敏承诺。

序列检查核对实际 `encode(P+C)` 与独立 P 前缀、C 精确解码、唯一追加 EOS、completion-only mask、next-token shift 首末 target 和右侧 padding，拒绝空/非法 IDs、边界变化、错误 EOS、解码变化和截断。字符 callbacks 是纯接口 test double；声明的 template hash 不是已读取模板的证明。独立 Action 编码可保存未注册工具，真实 Example 仍校验当前目标 catalog；表示转换没有授予 P03 执行权限。原 parser SHA `15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b` 未改，原 raw 字节/节点/深度限制和错误类别仍通过既有真实测试。

**实际消息和 tokenizer。** [review_tokenizers.py](review_tokenizers.py) 与 [review_support.py](review_support.py) 按规范独立重建消息和控制段，再分别使用真实 native Jinja/tokenizers 与直接 AutoTokenizer 参考路径，比较候选的完整 P/C/IDs/sequence/EOS/mask/shift 和 padding。实际 system/assistant 控制段保留；连续 tool 观察共用 user/tool_response 段，内部原 role/index/关联仍可逆，历史没有猜造 kind。所有模板输入仅外层 role/content，`tools=None`，`add_generation_prompt=True`，`enable_thinking=False`。原 12 fixture 没有改写；两种 repo identity 使用相同三个来源文件，24 identity rows 不是 24 个独立场景。R1 两环境结果与 D1 两环境真实制品也逐项相等。

native 使用复用的 tokenizers 0.22.2 / Jinja2 3.1.6 环境。新参考环境 Python 3.14.7、Transformers 5.16.1 / tokenizers 0.23.2 / Jinja2 3.1.6；37 个安装版本与当前 uv.lock 核对，用本机 cache、离线和 requirements hashes 安装，`uv pip check` 通过。与 D1 参考记录唯一版本差别为 fsspec：D1 记录 2026.7.0，本轮选当前 lock 的 2025.3.0；没有改写旧 native 环境身份。所有实际 tokenizer 进程先禁用 Torch/TF/Flax、启用离线限制，并检查没有 MLX/Torch/TF/Flax/JAX 或具体模型模块被加载。

另测十种静态来源情形：三文件各一次同长度损坏、added_tokens.json、special_tokens_map.json、vocab/merges、相同/不同 chat_template.jinja、additional_chat_templates 命名模板和额外 config.json。两引擎均拒绝损坏固定文件。HF 拒绝改变/命名模板；其余被接受的邻例 actual backend state 与 IDs 保持不变；native 直接使用验证缓冲，额外文件不参与。固定配置的 added_tokens_decoder 与主 tokenizer.json 优先级已结合本机 Transformers loader 源码核对，没有把“存在附加文件”自动判为失败。不同长度替换和同长度替换是另外两个文件交错场景；源/安装重复不增加场景分母。

固定来源：0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca`；1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`；三文件及 S0 来源证明 SHA 见 [evidence.json](evidence.json)。完整 descriptor/安装资源 SHA `e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207`；instruction SHA `294d8540bd3ff8de84293d5d8b0f7e8f2537ee9cf1c81b95e81b6415f1039cee`；官方模板 UTF-8 SHA `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8`；冻结契约 SHA `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。本次是 tokenizer/表示检查，不是两套模型权重测试。

**独立全量复算。** [review_full_audit.py](review_full_audit.py) 先验证原 policy-a/policy-b 各 18 制品、8,228 Example 与全部 split 行的逐例身份，再逐行绑定 source/revision/source-record/group/split/目标及共同格式/源码/协议/parser 来源。仅执行一次直接 AutoTokenizer 参考渲染/连接编码，期望计算不调用候选投影、序列或 AUDIT/CHECKS helper。对照行沿用被审 manifest 的 binding 字段作为比较键；本轮真实 reference 环境单独记录，未把它冒记为原 native 环境。

8,228 个完整比较行均无缺测/失败，字节 SHA 同为 `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff`；所有全量及分 split 的八个字段分位、raw 限制、上下文/响应/预留预算均独立复算相等。[test_audit_denominators.py](test_audit_denominators.py) 再用四个原创场景验证精确 cap、EOS 边界、缺测与 parser 失败保留，以及 nearest-rank 分位算法。

| 原 split | 分母 | 总长 >2048 | C 含 EOS >256 | 两项同时合格 |
|---|---:|---:|---:|---:|
| train | 7515 | 1344 | 230 | 6013 |
| validation | 234 | 3 | 17 | 217 |
| test | 215 | 3 | 13 | 201 |
| ood_test | 264 | 1 | 9 | 254 |
| 全量 | **8228** | **1351** | **269** | **6685** |

总长 P50/P90/P95/P99/max 为 1505/2239/2503/2939/4615；C 含 EOS 为 77/194/232/319/1001。1024/1536/2048 总长合格数为 1220/4308/6877；与响应预算的交集为 1220/4215/6685；P+预留256 合格数为 342/3310/6229。C 不含 EOS 超256 为261。全部保留原完整分母；没有生成训练子集。原 raw 的 str 前置字符长度、解码后 canonical bytes 与额外统计的 escaped UTF-8 bytes 是不同检查，本轮没有修改其定义。

**新包。** [review_package.py](review_package.py) 以精确 candidate Git blobs 独立核对成员集合、每个有效载荷字节、metadata、重复/逃逸/链接边界。sdist 为 86 tracked payload + PKG-INFO；两个 wheel 各为39源码/资源+5metadata。默认 wheel 确实由本次 sdist 构建，显式重建相同。源码直接 wheel 路线 **NOT_RUN**。

| 新制品 | bytes / members | SHA-256 |
|---|---:|---|
| sdist | 180780 / 87 | `e75cc4c86f9268215776d742676e1017d0a8d820f7aa47f2d6749c0a0ad42c84` |
| 默认 wheel | 80146 / 44 | `a0aac74f1667ff860c850f96fd210acef02818187e7a80fbed869640d88b13ea` |
| 显式重建 wheel | 80146 / 44 | `a0aac74f1667ff860c850f96fd210acef02818187e7a80fbed869640d88b13ea` |

新私有 target 安装的是**默认 wheel**。10 条实际子命令通过；`python -I -S`、外部临时 cwd，仅该 target 与标准库参与纯包验证，六个默认 distributions、39安装文件逐字节确认。descriptor、投影、Action/parser、字符序列接口对同12例通过，另有契约 digest 和五类 fixture CLI。纯/default 验证未导入 tokenizer/模型，也没有把字符接口测量称为真实 Qwen token 结果。可选 HF/native 的安装来源复现另用既有允许环境，见 F1。

**原证据保全。** [review_evidence.py](review_evidence.py) 核对235个被审文件全部保持，214个同期 P03 授权基线文件与3个旧提案文件均未变；最终候选相对parent只增4份证据。新18公开文件、D1 seal 内620项真实私有制品及37条完整命令元数据/log hash 全匹配。测量用 b33a55f 的实现、正式格式、协议与原 parser 均与本候选一致；旧 P02 技术 PASS 仍对应旧格式。十二个已有 review 分支 SHA 保持。

原 Example manifest canonical SHA `87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756`，examples 文件 `d45c815e9b775249c642cd3c9f624c28e7ab6505425cd6c009bfb06402c8f21f`；原100来源/114决策人审材料与填写副本保留，worksheet SHA `eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`，仍0 reviewer/0 verdict。身份核对不代签 kris 语义判断。

**失败、命令与边界。** [evidence.json](evidence.json) 登记精确 argv（私有路径以角色占位符显示）、退出码、时间、完整 log hash、脚本和结果身份。F1 在源/安装路径的两个 exit 1 是同一缺陷；不是两个独立问题。D1原三个失败命令（lint、首包检查、raw边界）均保留并核对，没有改写原错误。

R1 原失败也保留：首次 requirements 准备假设 fsspec 在当前锁中，写文件/安装前 KeyError；两次过宽导入保护分别误拦可用性查询及无模型加载的配置 utility；一次附加模板探针误用目录名；第一次全量旧回归启动器缺少 `__main__` 保护，spawn 子进程重复运行pytest，138 failed/526 passed。仅改R1启动器后，原664项40.77s全通过，没有改候选。新增56项后追加4个统计场景，最终60项通过。首次本轮 lint 的15项均为R1附件的导入格式、lambda样式或未用导入；为保持已执行/交给S0的探针精确字节，[本目录 Ruff 配置](.ruff.toml) 对四个具名证据附件保留窄样式例外，其他文件按仓库规则检查；最后 `ruff check .` 通过。源文件和测试内容没有为了掩盖候选失败而修改。

本轮仅 CPU；复用既有 native 环境并离线创建必要 reference 环境。新增私有环境、源码副本、证据的可枚举容量与 hashes 在 evidence.json 中；临时测试写入流量不是该容量数字，未声称精确 I/O 累计或峰值。未读取权重、加载 MLX/Torch 模型、申请 GPU、下载新依赖、产生费用或修改其他 worktree。原数据转换/分组/policy 两遍构建 **NOT_RERUN**；训练、模型生成、质量/隐藏 oracle/BFCL评分、P04人工 token-mask、trainer packing/梯度、G-DATA与人工语义验收、正式选集、S0主干验收 **NOT_RUN/PENDING**。完整格式技术结论为 FAIL，后续修复和集成由 S0 组织。

最小复现使用允许的固定 reference CPU 环境和已绑定的三文件，只在新的私有输出目录运行；预期本候选 exit 1，native 对照 exit 0：

```bash
PYTHONPATH=src "$REFERENCE_PYTHON" reports/review/P02-format/review_snapshot.py \
  --source "$VERIFIED_SOURCE" --out "$NEW_PRIVATE_OUTPUT" --engine transformers
```

全量已独立测量一次；后续读实际行/结果和小集即可，不应无理由重复全量。提交与交接见 [P02-format-review-r1](../../../coordination/handoffs/P02-format-review-r1.md)。
