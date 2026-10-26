# R1｜P04 真实 pip 索引覆盖增量复核

状态：READY。owner R1，协调者 S1。已合并基线 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`，E1范围见 [r4任务](P04_COLAB_ENVIRONMENT_R4.md)。精确候选由 S1 后续原生提供；未收到前只读实际失败材料和独立复现解析行为，不对未交付代码出结论。

在既有R1 worktree从该基线建立 `codex/review-p04-colab-environment-r4`，保留旧分支/证据。只新增 `reports/reviews/P04_COLAB_ENVIRONMENT_R4.md`、`coordination/handoffs/P04-colab-environment-review-r4.md` 与必要私有比较；不修生产、锁、共享状态。

核对S1实测：初次setup缺系统venv包、补齐后ensurepip通过；第二次pip24找不到CUDA版Torch，但直接CUDA源存在版本，实际parser在锁内主索引处重置命令行附加源。两次都未加载模型或训练；完整run文件已回收到Mac，实例已停止并验证不存在。

收到候选后，独立核对修复使真实pip解析保留两个批准源，48个包版本及全部wheel hashes不变，锁生成/后处理说明真实，系统venv前置条件清楚。用必要CPU最小检查区分原缺陷与修复；不重复未变的清理/数值/数组检查。共享CPU环境保持不动；如需pip24.0，只允许其小型纯Python wheel用于私有解析测试。每命令≤300秒、2线程、新增≤200MiB；GPU、SSH、模型、真实数据、新编码均0。

最终提交一次精确候选的PASS/FAIL及证据；真实Linux完整安装与CUDA结果由S1另验。新问题稳定ID `P04-COLAB-INDEX-001`，当前是S1实测发现、尚无独立正式失败次数；r4任务名不用于计数。原两项已关闭控制问题沿用独立证据。
