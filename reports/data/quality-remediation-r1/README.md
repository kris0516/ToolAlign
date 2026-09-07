# P02 quality remediation r1

状态：D1 CPU 候选，待 R1 独立审查和 S0 集成。任务 `P02-QUALITY-REMEDIATION`；基线 `86b80bada50ac7c8f4b3910e3831a397ed65a853`，授权 `2aa0cf4a756e78d32cf10130edbe6d0e3925bf3a`，分支 `work/p02-quality-remediation`。契约为 plan-v0.1 / coordination.v1 / toolalign.contracts.v1。

按已封存的委托 AI 审阅，实际生成了两次独立的新修订视图。32 个来源的全部 40 条规范化决策被暂挂；保留记录的原 JSONL 字节、身份、group、split 不变。同受影响 group 中其他来源的 5,586 条记录保留。审阅标签仍是审阅者判断；本轮没有执行外部 API 来证实其语义结论。

| 集合 | 原分母 | fail 来源暂挂 | unknown 来源暂挂 | 有效数量 |
|---|---:|---:|---:|---:|
| train | 7,515 | 26 | 14 | 7,475 |
| validation | 234 | 0 | 0 | 234 |
| formal / train | 6,013 | 22 | 11 | 5,980 |
| smoke / train | 1,600 | 3 | 4 | 1,593 |
| formal / validation | 217 | 0 | 0 | 217 |
| smoke / validation | 197 | 0 | 0 | 197 |

训练选择只过滤原已选集合，保留相对顺序和 `parent_selection_rank`，没有回填或重新划分。新 manifest 绑定固定质量配置、原数据和审阅 hash、原训练配置、旧序列依据和新有效集合，保持 `training_authorized=false`。冻结的旧 v1 选择、序列常量、原材料及失败证据保持。

两次构建各有 24 份稳定文件，逐字一致；独立运行的 `run.json` 保留不同创建时间。修订标识为 `6656f5cbf74634f55dde31a0d68cc19a206a2130e1e27b8d214b147708078708`，manifest 文件 hash 为 `d97c5d542a0890e1b05d84fcd703895bbd041ad07887fcc370497cfa60d17d3b`。[标准库交叉核验](check_revision.py)重新检查原字节、来源家族、选择排名和候选派生；这是 worker 自查，不能代替 R1。

## 重标候选和新材料

只应用封存草案的两处精确 Action 参数变更，重新计算 Example ID。新 annotation sidecar 绑定原 Action、原用户依据、schema 和 annotation parent，保留上游 `source_record_hash`、`source_revision`、group、split、许可身份。另重建了一份后续历史前缀候选；其中旧工具观察逐项标记 `UNVERIFIED_AFTER_ACTION_CHANGE`，后续条件未验证。三份候选都留在 staging，未进入有效 train 或任何训练选择。

从有效选择按原规则重选 10 例，其中 6 例沿用旧代表例身份、4 例是新的代表例；旧被暂挂代表例没有混入。加上 3 类原创协议例、2 份直接重标和 1 份后继，共 16 个不同案例。各例按其 smoke/formal 模型身份，用现有 Transformers 与原生 tokenizers CPU 路径分别测量，共 32 次案例测量。两引擎的完整 P/C、IDs、loss mask、shift、EOS、padding、token 文字和来源记录相等，记录集合 hash 为 `0908dbf24fe43acb89ccb063427b2f5fa2f4803baace5ec1d57aafc2907bf6dc`。没有重跑全量序列测量。

| 候选 | P tokens | C tokens，不含 EOS | 总长，含 EOS | 展示 padding |
|---|---:|---:|---:|---:|
| staged-direct-01 | 1,263 | 67 | 1,331 | 1,536 |
| staged-dependent-01 | 1,421 | 65 | 1,487 | 1,536 |
| staged-direct-02 | 2,822 | 246 | 3,069 | 3,072 |

第三行超过既有 1,024 / 1,536 / 2,048 上下文限制，展示 padding 不改变训练上限。全部候选的含 EOS response 长度均不超过 256，但这不构成候选晋升或语义通过。

材料包含完整 JSON、静态 HTML 和身份绑定 CSV。所有 reviewer、semantic verdict、token/mask verdict、时间和备注栏为空，供后续委托 AI / 独立复核使用。静态 HTML 与记录可精确重建；浏览器实显仍为 `NOT_RUN`，本轮未重试旧被拒绝的浏览器访问。

## 验证证据

生产及新增测试字节冻结于 `1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e`；之前的质量视图实现提交为 `53bf6bd617a454c022fdd03c09276b162df1f1fa`。构建 A 的对应源文件尚未提交时运行，B 在 53bf6bd 运行；两者消费文件完全相同。每条命令保存实际开始/结束时间、前后 HEAD、完整源文件快照、退出码和日志 hash，见 [evidence.v1.json](evidence.v1.json)。最后的文档和核验脚本不改变上述生产和归档载荷。

| 实际 CPU 检查组 | passed | skipped |
|---|---:|---:|
| tests 与原 P00/P01/P02/P03 回归 | 1,007 | 2 |
| 原格式独立审查用例 | 60 | 0 |
| 截止时间审查用例 | 2 | 0 |
| 训练绑定独立审查用例 | 13 | 0 |
| SFT CPU 审查用例 | 44 | 0 |
| native 路径的 CPU 审查用例 | 34 | 0 |
| 合计 | 1,160 | 2 |

两项跳过仅适用于参考引擎的 snapshot 清理；运行上述套件使用原生 tokenizer 环境。13 项训练绑定用例另含 110 个 subtests，没有重复计入总数。新增 76 项已包含在 1,007 中。未运行模型数值探针或实际 trainer。各组记录的模型模块加载数为 0。

[输入替换检查](check_rejections.py)实际调用固定公共 build 边界 12 次，分别替换配置、原 manifest、选择 manifest、训练配置、序列依据、原始源、来源政策、审查 seal、语义 CSV、整改提案、重标草案和原 token 审查 CSV，均以 `input_hash_mismatch` 拒绝，没有产生输出目录或成功 manifest；没有 monkeypatch 生产校验。新增单元用例另覆盖错误 source/Example/CSV/final split、整来源前后决策隔离、同组其他来源保留、选择顺序、无回填、候选新 ID 和 parent、未验证观察、staging 泄入和写入失败的 manifest 行为。

[实际包检查](check_package.py)核对 sdist 128 个成员、两个 wheel 各 65 个成员的精确集合、全部载荷字节、METADATA 和 RECORD；默认 wheel 与从实际 sdist 重建的 wheel 相同，hash 为 `7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b`。复用已有默认依赖目录，离线无依赖安装新 wheel；4 条实际命令验证安装、隔离 API/材料比较、CLI help 和完整修订 verify。`-B -I -S` 下加载的 ToolAlign 模块全部来自新 wheel，60 份包文件匹配；tokenizers/transformers 和模型框架均不可导入。默认安装没有进行 Qwen 编码。

Ruff、4 份冻结契约和公开内容扫描通过。未创建新的持久环境，未下载依赖/数据/模型，未运行 GPU、训练、生成或外部 API，未接入变化中的 E1 审阅。全部新制品与保留测试临时目录的实际字节预算、原输入最终不变核对和最终候选完整 SHA 随私有封存交接。

## 保留的失败与限制

- 首次 build 被原 CSV 对提案理由的归属说明包装挡住，返回 `proposal_verdict_binding`，无输出；修正为在分别精确 hash 固定的两份完整文件间校验非空原理由包含关系，并补充回归。
- 首次材料单元测试为 17 fail / 2 pass，原因是新增原创测试 fixture 缺 audit identity；第二次为 1 fail / 18 pass，暴露 JSON 落盘排序后 HTML 文本不稳定。修正 fixture 和 HTML 序列化排序后 19 项通过，并纳入完整回归。原失败日志保持。
- 首次 Ruff 记录器在并行创建相同源快照目录时退出，Ruff 尚未启动；保留包装器失败说明后顺序重试通过。没有把该次写成成功测试。
- 32 个来源当前是暂挂，并非都已修成可训练正例。新代表例、两份重标和后继均未获新语义裁决。扩大 train/validation 审计、R1 独立审查、S0 main 验证、G-DATA 质量验收和 P04 显式授权仍是后续依赖。

## 复现入口

私有交接提供 `input-paths.json` 九个显式路径参数和封存制品位置。`build`/`verify` 使用同一组 `--config-path`、`--data-manifest-path`、`--selection-manifest-path`、`--training-config-path`、`--audit-path`、`--review-root`、`--token-review-root`、`--raw-source-path`、`--source-policy-path` 以及 `--output`。所有生成目录必须是新的私有目录。

```sh
python -m toolalign.data.quality_revision --help
python -m toolalign.data.quality_revision build --help
python -m toolalign.data.quality_revision verify --help
python -m toolalign.data.quality_materials measure --help
python -m toolalign.data.quality_materials compare --help
```

实际 token 测量须使用已验证的离线 CPU 环境和固定 Qwen tokenizer 来源，设置 `USE_TORCH=0 USE_TF=0 USE_FLAX=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`。`compare` 核对已测材料，不重新编码。精确实跑 argv 和完整日志保留于私有封存，公开证据仅给出去敏命令与 hash。
