# Q1｜P04 20条实际容量数组增量复核

状态：READY。独立Q1，协调者S1。精确执行源码为已合并PR21的 **`920c41551f0f7f2be8a5a8dcced23cc080ac1f27`**。沿用13例预审 `82f1e88e168b80298c47455c26084cc9a4b54b92`；本轮审新CUDA入口实际生成的18 train与2 validation数组，资料hash见[输入报告](../../reports/S1_P04_CUDA_CAPACITY_INPUT.md)，authorization_commit与私有路径由原生派发提供。

在Q1既有worktree从执行源码建立 `codex/q1-p04-capacity-arrays-r1`，保留旧分支与证据，先保存授权。只新增 `reports/reviews/P04_CUDA_CAPACITY_ARRAY_Q1_R1.md`、`coordination/handoffs/P04-cuda-capacity-array-q1-r1.md` 与必要私有比较；不改生产、配置、原数组或共享状态。

核对实际命令的源码身份与退出码、stage/array manifest及全部文件身份；20条记录必须逐一对应stage中的批准原例、sidecar audit与原行hash，并与预先固定cohort、原rank顺序一致。核对完成部分加单EOS、prompt/历史角色不监督、右padding及一次causal shift、20个序列hash和监督分母。必要时只解码已有token，不能重新编码。13例review数组与已通过预审逐字相同，仅核对身份后沿用，不重复整套语义审阅。

输入为固定formal容量cohort：18个train长2044–2048，2个validation长1851/1882，全部bucket2048；组为8+8+2。核对报告明确其诊断用途、完整profile计数未变、没有正式SFT或模型效果结论。20条数组通过后可支持S1按已定预算签发容量配置；本轮不代替GPU实测或最终结果审核。

单命令≤300秒、2线程、私有新增≤200MiB；JSON/数组比较优先标准库，若需要解码复用既有共享CPU环境和固定tokenizer。GPU、SSH、模型加载/下载/训练、新编码、环境/依赖安装均0。交精确reviewed源码、材料hash、逐项PASS/FAIL/不可判范围、实际命令及保留失败；问题与正式次数由S1维护。
