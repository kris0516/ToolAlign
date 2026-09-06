# P02-format-review-r1｜R1 独立交接

**FAIL，P0=0 / P1=0 / P2=1。** 被审 candidate `7bada2e451d43dae4b3ed532d5efa310fc8e6a57`，parent `9f4e7a3f699a9d6cd9e444da2dc18f35f2cc9207`；授权 `1de90781e42a3693b112aafcf585a905bc052d63`；分支 `review/p02-format-r1`，gpt-6-astra/max。本交接所在的新增独立 review commit 通过同轮原生消息提供；没有把候选 SHA 当作 review SHA。

**去敏来源映射。** 原本地 review SHA `f7086413a9fedd9e2a473ac6d2869efff74ddad5` 保留。S0 在发布前发现 evidence.json 有一处实际系统临时路径，按新授权 `085a61c2d0d12d3bde05658259e566aac6ec27ed` 将其映射为公开角色占位符，并在 `review/p02-format-r1-public` 从原 candidate 单独建立新的公开 review commit。原本地 SHA 与新公开 SHA 不同；最终公开 SHA、唯一父提交、tree 和12公开文件 hash 由原生消息交接。原含路径提交不在新公开祖先，未 reset/rebase/amend/cherry-pick 或 push 原分支；私有原日志/结果/命令字节、8探针和 Ruff 配置均不改。只改三份发布材料中的路径/来源说明及相应公开hash，复查 lint/public/diff/scope；F1=P2=1、FAIL、实际测试数字保持。本轮 R1 不推送任何 review 分支，由 S0 独立核验后处理。

只新增 `reports/review/P02-format/` 与本交接单；235个候选文件、217个旧/提案受保护文件、12个已有review分支均保持。没有修候选、修改全局配置或状态/ADR、合并main或接入后续D1修复。

**F1/P2。** `src/toolalign/model_io/offline.py:107–110` 的 HF 分支从可变目录重新加载，再比较调用前后的三文件，未绑定实际加载快照。原JSON/config已验证后换入同长度tokenizer JSON，HF实际加载后、最后路径hash检查前恢复，构造器仍接受且identity完全不变，`!` ID却从0变成30。未patch真实loader/返回值。源路径和真实默认wheel安装路径均复现；native对应对照通过；不同长度替换及静态来源/模板损坏正常拒绝。建议D1固定所消费的验证快照或核验实际加载状态，并保留相同探针before/after。本轮不签修复通过。

原探针 [review_snapshot.py](../../reports/review/P02-format/review_snapshot.py) SHA `5b3f55d7fdddb2399b5ca7a8d0558dbbc51ce45715a163ec49b806d1ef37f2fc`；支持文件 SHA 与完整实际 backend 前后状态见[正式报告](../../reports/review/P02-format/README.md)。原源路径失败结果 SHA `f9914dd049865afc3abe8ddc91a4f03897d0bdf2ccd4cc9918d5e4e5975dbaa1`，失败log `9b1e5469b55f6487f2c3180cd94f85b7c9edb6c775592d73dcf92aa86034e48b`；安装失败log `0f4c1f480337bdc66db72784f2e1b770b4610bbb80fec3152ed3120b9484f6e7`。

**已取得的范围证据。** 原664 pytest全通过，新增60独立pytest全通过；同12原始fixture的两真实CPU路径/两相同来源模型身份与D1制品一致，重复安装/身份不增加独立场景数。十个静态来源场景和两个加载交错邻例分开登记。独立参考路径只跑一次8,228行完整新格式表示，全行比较字节SHA `36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff` 与D1一致，完整分母、八字段分位和全部分split统计相等，0测量错误。1351条总长>2048、269条C含EOS>256、6685条联合合格是统计，未成为训练选集。

新三归档逐成员/精确Git字节通过；sdist 180780B/87成员，默认及重建wheel各80146B/44成员。新默认wheel target六个默认distributions、39源码/资源、同12例纯格式/序列接口与5类契约CLI通过，10个安装检查子命令全exit0。源码直接wheel NOT_RUN；真实可选tokenizer安装复现与纯default验收分别记录。235候选文件、18新公开文件、620项D1私有制品及37条D1日志全部绑定；原两遍构建各18制品、人审100来源/114决策和填写副本未变，0 reviewer/0 verdict。

**原失败与限制。** R1原启动器未保护multiprocessing主入口导致138失败/526通过，原log保留；只修启动器后未修改的664项通过。requirements准备/两次过宽import guard/错误附加模板目录/首次review附件lint也如实登记。最终lint通过；仅四个已封存证据附件有具名窄样式例外，候选规则未放宽。D1三个历史失败也原样保留。完整命令、退出码、log/结果/代码hash及实际环境见 [evidence.json](../../reports/review/P02-format/evidence.json)。

仅CPU，没有MLX/Torch模型/权重/GPU/训练/模型生成/BFCL/最终模型评分/云费用；原来源转换、分组及两遍构建未重跑。G-DATA、kris语义审查、P04至少10条人工token-mask、trainer packing/梯度、真实模型质量、正式训练选集和S0主干验收仍NOT_RUN/PENDING。R1完成本精确候选的独立审查后等待S0下一次明确授权。
