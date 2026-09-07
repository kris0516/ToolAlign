# P02-QUALITY-REVIEW-r1

结论：**PASS（冻结的 CPU 技术范围）**。精确候选为 `9b7cf019b1d55501a7e656dbfb79b13bc7369fa0`；本轮新增技术问题 P0/P1/P2 均为 0。此结论不关闭已有质量问题 `P02-Q-001`，不构成 G-DATA 验收或 P04 训练授权。

R1 按授权 `6e9d29b2d408f9e3a2f319406b05eb1a97b16153`，在独立任务、自己的 `review/p02-quality-r1` worktree 复核。模型/推理等级为 gpt-6-astra / max；契约为 plan-v0.1、coordination.v1、toolalign.contracts.v1。实现基线 `86b80bada50ac7c8f4b3910e3831a397ed65a853` 的 428 文件不变，完整候选共有 440 文件，本轮审查全部 12 个新增文件。

生产代码和新增测试载荷位于 `1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e`。最终候选随后新增交接单、公开报告/证据和三个审计辅助脚本，共六个文件；生产代码及测试字节保持。R1 只新增本目录和自己的交接单，没有修改被审实现、旧配置、训练选择或旧序列。

## 独立结果

| 集合 | 原分母 | 暂挂 fail | 暂挂 unknown | 有效分母 |
|---|---:|---:|---:|---:|
| train | 7,515 | 26 | 14 | 7,475 |
| validation | 234 | 0 | 0 | 234 |
| formal train | 6,013 | 22 | 11 | 5,980 |
| smoke train | 1,600 | 3 | 4 | 1,593 |
| formal validation | 217 | 0 | 0 | 217 |
| smoke validation | 197 | 0 | 0 | 197 |

- 20 个 fail 来源和 12 个 unknown 来源的全部 40 条决策被暂挂。来源内前序/目标/后继身份逐条核对；同 group 的 5,586 条其他来源决策保留。JSONL 原字节、顺序、source revision、group 和 split 保持。
- 原选择集合有序过滤、保留 parent rank 和原测量侧记；没有回填，smoke 仍为 formal 子集。全部 proposal membership、移除身份及分母独立计算。最终划分只使用既有七行审阅元数据，未消费其语义或训练内容。
- R1 两次新 build 与 D1 两次旧 build 的每套 24 个稳定文件完全相同；四次运行时间各异。稳定 manifest 为 `d97c5d542a0890e1b05d84fcd703895bbd041ad07887fcc370497cfa60d17d3b`，质量修订身份为 `6656f5cbf74634f55dde31a0d68cc19a206a2130e1e27b8d214b147708078708`。
- 两份直接 Action 修订与一份后继前缀均绑定原草稿、原 source hash、annotation parent、新身份及原 group/split。变化限定于获授权的参数和依赖前缀。旧观察保留 `UNVERIFIED_AFTER_ACTION_CHANGE`，后续条件未验证，三例均只在 staging。

上述复算由 [audit_view.py](audit_view.py) 完成，不调用生产修订函数。原始交接由 [audit_original.py](audit_original.py) 复核：9,683 个当前路径、180 个符号链接、11 个源码 epoch、32 条原命令与 26 条公开回执均绑定；原执行失败与发布前 recorder 失败保留。最后再次核验原路径、440 候选文件和十份授权文件；旧 native review 的 2,281 文件、173 个链接及原 `67976fdcb33cba15caac8130213997bd330a7233` 分支保持。

## 序列、材料与安装边界

R1 独立按原规则选出相同的 16 个唯一例：10 个有效 train、3 个原创协议、2 个直接 staging、1 个后继 staging。在两种现有离线 CPU 引擎上各测一次这 16 例：reference 为 Transformers 5.16.1 / tokenizers 0.23.2，native 为 tokenizers 0.22.2；两者 Jinja2 均为 3.1.6。实际导入来源、发行包 RECORD、模板和本地词表字节均已核对，未导入模型框架。

[audit_materials.py](audit_materials.py) 另以标准库独立重建角色保留 JSON 投影及固定模板分支，并根据词表执行 ByteLevel 解码。它没有新增 token 编码或导入生产模块。四套材料的完整记录一致，records hash 为 `0908dbf24fe43acb89ccb063427b2f5fa2f4803baace5ec1d57aafc2907bf6dc`。检查涵盖完整 P/C、所有 token ID、唯一追加 EOS、loss mask、next-token shift、右 padding、attention、源身份和空白审阅 CSV；每套 26,112 行 HTML 表与 JSON 逐格一致，HTML 内容均按文本解析。浏览器实际观察仍为 NOT_RUN。

`staged-direct-02` 的序列为 3,069 tokens、展示 bucket 为 3,072，超出原 2,048 context cap。材料明确记录预算未通过及不晋升；其余 staging 为 1,331/1,487 tokens。结构和展示检查均不赋予语义通过、工具执行效果或训练容量结论。

[check_archives.py](check_archives.py) 复核现存 sdist、default wheel、由 sdist 重建的 wheel：127 个 sdist Git 文件和两个 wheel 的全部 60 个包载荷对应精确候选，全部成员、RECORD 与元数据一致。default/rebuilt wheel 同为 `7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b`。本轮没有重新构建归档。

从该 default wheel 离线、无依赖安装到新私有 target 后，以 `-B -I -S` 和非源码工作目录运行。60 个包载荷和实际 module origins 均来自新 target，八项 optional 包不可见，default 入口未导入 tokenizer 或模型模块。帮助入口、完整 revision verify、两引擎 compare 三条正向命令通过；实际替换配置、来源、审阅或旧选择文件后，build/verify 共八条负向命令均以 `input_hash_mismatch` / exit 1 拒绝，未发布新输出，原成功稳定文件不变。

## 回归与失败保留

| 检查 | 结果 |
|---|---|
| 基础 CPU 回归及既有 P00/P01/P02/P03 审查探针 | 1,007 passed / 2 HF-only skipped |
| 旧格式独立审查探针 | 60 passed |
| 截止时间独立探针 | 2 passed |
| 训练绑定独立探针 | 13 passed；110 subtests 单列 |
| SFT CPU 独立探针 | 44 passed |
| native CPU 原创探针 | 34 passed；没有执行 native 框架运行 |
| 本轮 [probe_boundaries.py](probe_boundaries.py) | 26 passed |
| 合计 | **1,186 passed / 2 skipped**；subtests 不加进分母 |
| Ruff | 默认命令及显式 112 个 Python 文件均 PASS |
| 冻结契约 | PASS，4 文件 |

新增探针覆盖四决策来源的中间重标与两个后继、观察保留、同组其他来源、零有效 smoke 不回填、关系缺失/错配、选择分母、发布各阶段 I/O 失败、重算拒绝自洽伪造 manifest 及 CPU 前置守卫。生产输入替换使用原 pins，原创 fixture 仅注入小型测试输入。

本轮五次审查辅助失败的原始回执和当时源码均保留：两次原交接审计辅助脚本分别误读链接结构、误认 intake 前源码 epoch；首个 reference 启动的审查钩子误拦 `find_spec` 可用性查询，尚未编码任何例；归档辅助脚本误将等价 Requires-Python 顺序当作差异；新增探针首轮 fixture 漏写字符串 maxLength，19 failed / 7 passed。只修正 R1 辅助代码后继续，未修改候选；这些失败不是五次候选修订，也不增加项目正式失败轮次。后续通过结果见 [evidence.v1.json](evidence.v1.json)。

## 限制与交付

既有 `P02-Q-001` 仍为 CHANGES_REQUESTED、正式失败轮次 1；本轮不增、不清零。冻结候选仍含该完整来源问题，须由 Q1/S0 和后续质量修订处理。没有读取动态 Q1/E1 标签作为本候选输入，没有重做 180 来源语义审计；G-DATA、真实模型容量、正式 P04 训练及语义/token-mask 签字仍未由本轮放行。

本轮新环境、依赖下载、框架/模型/GPU 运行、浏览器、付费 API、公网服务和模型/数据上传均为 0。归档安装复用已有 default 依赖。新私有制品及八个保留测试目录在最终检查时共 385,890,304 bytes，低于 2 GiB；发布后的最终字节数与文件清单另行封存。

精确命令参数、UTC、退出码、stdout/stderr hash、执行源码快照和复算结果 hash 位于 [evidence.v1.json](evidence.v1.json)；路径均以角色占位符公开，实际命令和输入只在私有证据中。当前 review 提交的公开扫描、完整 SHA、远端一致性与最终文件封存见本轮私有 completion/publication。R1 不合并 main、不改协调状态或训练授权；正式交接见 [P02-quality-review-r1](../../../coordination/handoffs/P02-quality-review-r1.md)。
