# Q1｜P04 CUDA 数据、mask 与说明复核

状态：READY。独立 reviewer Q1，协调者 S1。待审 T1 精确候选 `4342af87615197c7947d001f462d3d31500cd501`；当前真实消费报告源提交 `e5f023cd1cd50b60184d44576203070726e9dddf`。authorization_commit 与私有材料路径由原生派发提供。按 [REVIEW_POLICY](../REVIEW_POLICY.md)记录实际 AI reviewer，不代签用户。

本轮先完成有实物的预审：S1 当前接口真实 prepare/rebind/export/readback 所得13例、26条原engine记录（10条train材料、3条protocol-only），以及 T1 CUDA数组/损失/验证/报告的对应。审查13例当前 Batch 与原 sequence、token文本、原Q1判定、原行绑定；核对completion+单EOS监督、角色边界、右padding、一次causal shift，protocol-only不进入训练。旧质量批准与无关来源处置沿用；不重新抽样，不重做全数据质量审查。

核对 T1 对训练样本均权、验证token加权、尾组7/2的解释是否与冻结约定和实际消费者相符；核对固定最长18train+2validation容量cohort的用途边界。容量probe的验证/epoch字段必须明确仅为诊断，不能声称完整正式SFT或模型提升。R1负责数学/工程复核；本轮Q1不批准尚待修订的E1控制代码，也不以语义审阅代替GPU实测。

使用 Q1 自己的干净 worktree，从 T1 候选建立 `codex/q1-p04-cuda-mask-r1`，先保存当前授权文件，保留历史分支与私有证据。只新增 `reports/reviews/P04_CUDA_MASK_Q1_R1.md`、`coordination/handoffs/P04-cuda-mask-q1-r1.md` 和必要私有逐例判断；不改生产、配置、数据或共享状态。公开报告仅放必要计数、身份hash、结论和方法，不复制原始聊天/样本/本机任务身份。

本轮输出明确限定为13例真实材料及指定CUDA实现的预审 PASS/FAIL/BLOCKED。20条容量数组尚未由新入口生成，记 NOT_RUN；S1集成并执行有限编码后会提供精确数组与回读证据作增量复核，不需要为等待它挂起本轮已有材料审查。最终CUDA运行与结果解释另有实际证据后再审。

GPU、SSH、真实模型加载/下载/生成/训练、新token编码均为0。可读现有材料并作纯CPU小型JSON/数组比较；若需要解码，只使用已有token文本或固定tokenizer解码，不编码新序列、不导入模型框架。每次命令至多300秒、2线程，新增私有证据至多200MiB；共享CPU环境由S1提供，不新建或安装依赖。

交精确reviewed commit与材料hash、逐例结论/不可判项、实际命令和保留的失败、报告/交接提交。发现影响训练语义的具体问题给稳定issue ID建议和原材料定位；Q1只审阅不代修。旧失败保持原身份和历史，计数由S1维护。
