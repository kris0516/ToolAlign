# P02-QUALITY-REVIEW-r1｜质量修订技术独立审查

状态：READY；D1完整候选与原生终态已核验，S0交接证明通过，待原生派发。语义裁定由独立Q1承接，E1继续原固定审计；本包技术PASS不等于G-DATA或P04通过。

- owner：R1；复用原独立 App 任务及自己的隔离 worktree，gpt-6-astra / max。
- 精确候选/code_base：`9b7cf019b1d55501a7e656dbfb79b13bc7369fa0`；原实现已验证基线 `86b80bada50ac7c8f4b3910e3831a397ed65a853`；原 D1 授权 `2aa0cf4a756e78d32cf10130edbe6d0e3925bf3a`。
- 新 branch：`review/p02-quality-r1`。保存旧 `review/p04-sft-native-toy-r1`、原67976fd审查及全部旧制品，不reset/rebase。先从S0实际授权提交保存本任务/规则及D1原任务/配置，之后切至候选。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1；审查整个相对86b80ba新增的12文件，不能修改被审实现。
- [S0交接证据](../../reports/S0_P02_QUALITY_HANDOFF.md)：440候选/428不变基线、9,685当前路径、32原命令、12负向入口、实际三归档与4安装命令已绑定。worker 1,160/2是自测，仍须本轮独立复核。

审查32来源40决策整来源暂挂、原JSONL字节/顺序/group/split、同group其他来源保留；原已选集合有序过滤、旧rank追溯、无回填及精确分母。独立计算与至少两次新私有build对应稳定产物，逐条核对来源/全部决策/选择；不读取heldout语义或重新全量编码。

核对固定配置与所有真实输入字节，原v1生产/配置/选择/序列保持，不能靠放松原pins接纳新输入。实际生产build/verify入口检查替换配置、来源、审阅、选择等拒绝；原创小fixture检查关系错配、缺决策、来源边界、后继、暂存晋升、写入错误和假成功manifest。保留每次原始失败，不修实现后冒称旧候选通过。

两份直接重标与一份后继必须有正确new ID/annotation parent、原source revision/group/split与原草稿，仅限已授权Action变化；旧观察与后续条件未验证、staging从不进入有效训练。检查16例为10有效train+3原创协议+3staging、选择身份与完整P/C/IDs/mask/shift/EOS/padding和来源绑定。可在两种现有离线CPU引擎上各独立测一次相同16例（每engine最多20个不同例），核对实际引擎/模板/词表/消费者身份；禁止无差异全量tokenization与框架/模型。

已知质量未决项：E1在有效代表材料发现完整源内的截断PDF编码，S0已验证并列P02-Q-001；该来源仍在首版effective/formal，后续独立Q1和新修订处理。此为原32范围之外的新增发现，原输入和候选保持冻结；技术审查不得因代码结构正确就宣布所有有效数据语义PASS。Q1/动态E1标签不作为本候选的生产输入，R1不重做180来源语义审计。

实际跑适用CPU回归一次（原1160/2覆盖范围加本轮有意义的新探针），Ruff/契约/公开扫描。复核D1提供的三份现存归档字节与精确candidate，从已验证default wheel离线无依赖安装到R1新私有target，确认实际module origins并测试安装版边界；默认环境不得导入tokenizers/transformers/model modules。现存归档已完整绑定，本轮不要求无理由重建归档。生产与新增测试载荷1c90ce0和最终9b7文档差异须记录清楚。

资源：复用现有允许CPU环境，USE_TORCH/TF/FLAX=0且HF/Transformers离线，实际检查无模型模块；新增持久环境/依赖下载/费用/GPU/浏览器为0，私有新制品≤2GiB。可只读复用D1现有分词环境/源缓存，代码必须实际来自R1当前候选；不要写其他worktree/旧缓存。R1旧native框架2/2已结束，本轮不续用旧框架额度。

允许只新增 `reports/review/P02-quality-r1/` 与 `coordination/handoffs/P02-quality-review-r1.md`。交精确原候选和review SHA、PASS/FAIL/BLOCKED及P0/P1/P2、命令/退出码/UTC/日志hash、输入/新产物/归档/安装来源、失败与NOT_RUN；原候选与旧审查SHA保留。问题按[五次规则](../REVIEW_POLICY.md)附稳定ID/当前正式轮次建议，S0裁定台账；不得把单条测试或重复执行凑成五轮。交付后结束本轮，不自行合并main、改状态或放行训练。
