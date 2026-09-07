# P04-SFT-RUNTIME-PROPOSAL｜真实Qwen运行接口只读方案

状态：IN_PROGRESS。14:15:28 UTC按完整8929cbbef0b24f9a4053adfe778bb4ef76147293原生派发T1并确认新轮ACTIVE，gpt-6-astra/max；14:28:40 UTC实际新branch/完整intake经S0核验5,617路径/197链接、553基线/408旧Git快照、18授权/10输入及2原回执通过。可与D1 v3实现及Q1来源审核并行，计入最多两个实现/准备任务；正式P04及新生产实现仍未授权。

code_base `d3e56f68ebd67cc576d912b6f06636682b4170ab`（PR14已验证main）；新branch `codex/p04-sft-runtime-proposal-r1`、新私有scope `p04-runtime-proposal-r1`，仅自己的隔离worktree。先从完整authorization_commit保存本任务、AGENTS/GOAL/PROTOCOL/PROJECT_STATUS/BOARD、REVIEW_POLICY、ADR-0025、P04规格、P02 v3任务/配置及PR14/PR11主干证据，再切换code_base。统一gpt-6-astra/max，不创建其他任务或sub-agent。

S0已再次核对T1原f7326d1823c4cf132ae44525f4755c96c88ec159的408公开Git/新只读快照、全部原seal/1559旧制品及197链接，共5,416文件路径通过。切换前仍保存自己的旧public映射、核对旧CPU/P01 refs和私有封存；新identity只写新scope，根identity不覆盖。旧分支落后远端的S0集成历史保持，不pull/reset/rebase。

固定input manifest SHA `eb5f25bd164c1394c0d82350a1f1d0ccc09ddb1306dac3977403b695d7f1ac02`，10份副本/166,598 bytes：v3长度与更新投影、D1固定政策、现有MLX-LM 0.31.3的8份源文件。原trainer SHA ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe、datasets SHA fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17保持。私有路径由S0分发；复制后按hash读取，出处路径不作读取D1/Q1新输出或语义数据的许可。必要补读限定已有本地MLX-LM/MLX源码并记录路径/hash，禁止框架导入/执行、联网或安装。

交付可由S0直接拆成后续精确实施范围的方案：明确复用点、最小新增/变更文件和API、缺少实物证据及最小验证。代码/配置建议均标PROPOSED_NOT_AUTHORIZED，缺少v3真实输出hash写PENDING，不伪造占位SHA。

1. 新数据消费：现有`training.sft.data.prepare`硬绑定旧v1/CPU配置。提出新入口验证实际quality/selection/training-binding、复用view/格式/collator的边界，类型/原字节/rank守卫，完整13例与已审数组的绑定方式。11旧材料可以静态复用；未来真实trainer消费编码须由S0另定精确范围并匹配原长度审计。CPU准备、模型容量与正式训练的权限分开记录。
2. 真实训练：固定0.6B smoke/1.7B formal及原revision、本地权重和原生公开接口；参考P01已验收LoRA rank8/scale2/q_proj+v_proj/全部28层、Adam lr1e-4、microbatch1、accumulation8、seed42、单遍/无shuffle/packing/截断，给出可追溯默认方案。必要变化写明依据供S0决定，不把toy ≤13例/16tokens/4096参数/2更新守卫直接放宽成已授权formal入口。
3. 更新/验证：v3投影formal5938=742组8加尾2，共743更新；smoke1583=197组8加尾7，共198更新。用原生train分段保持同一model/optimizer/RNG，明确更新边界、尾段真实分母、完整rank覆盖/模型模式/时间账。训练为逐例completion-token-mean等权，validation为总CE/总监督token。设计有限且有用的checkpoint/validation时点、保存后实际参数/文件hash/optimizer step绑定、重载及确定性score选择；不把末次上游内置validation当最终状态，不混用toy score。
4. 容量/预算：0.6B在1536新格式的容量仍NOT_RUN，P01旧1024或1.7B计时不能替代。提出一个固定且有限的真实容量/过拟合/保存重载试跑候选及选例依据、更新/启动/时间/内存/制品上限；具体ID及输出hash须等已验收v3后由S0冻结。沿用全局GPU租约、自有子进程监督/清理，不提高wired-memory限制。区分P01 compile_disabled历史与后续原生compile路径的新证据要求。
5. 原始/SFT基线：说明同一格式、greedy/预算、prompt/tokenizer/停止条件如何绑定两模型输出，并由P03 Action JSON/注册本地工具消费。仅规划允许的train/validation诊断，最终test/ood/BFCL不用于选样/调参/回答生成。列明后续P05所需已验收SFT checkpoint与reference身份材料。

允许新增`reports/experiments/P04_SFT_RUNTIME_PROPOSAL.md`、`reports/experiments/P04_SFT_RUNTIME_PROPOSAL.json`和`coordination/handoffs/P04-sft-runtime-proposal-r1.md`。生产代码/测试/配置/契约/依赖/构建及S0协调文件不改，不复制上游训练循环或构建通用平台。报告给出准确源码行号/hash、建议后续任务顺序/文件边界/最小反例、待测项与预算；不重做已冻结质量裁定。

本轮仅核对文档和结构化方案内部一致性、来源hash、更新算术、所有权、公开扫描/diff；Ruff仅适用于自有私有辅助脚本。无需新生产测试、完整pytest/build/install。新增私有≤128MiB，0新环境/依赖/下载/数据构建/分词/框架/模型/GPU/训练/生成/API/浏览器/费用。保存实际命令、源码时点、退出码/失败和最终seal，完整candidate普通推送并交接后结束；S0决定下一实施范围，不自行领取正式训练。
