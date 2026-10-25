# S0 长期目标与当前接续约束

更新：2026-10-26。P00–P09 长期研究目标保持，当前进度见 [PROJECT_STATUS](PROJECT_STATUS.md)，新 Supervisor 入口为 [toolalign.md](../toolalign.md)。本次是整理与迁移交接，不表示长期目标已完成，也不创建新 Supervisor。

后续训练、偏好生成、容量检查和批量模型评测全部使用 Colab GPU，Mac 只做开发、CPU 检查、远程控制和分析。优先 L4 24GB，显存不足时 A100 80GB；先估算、后短验证。旧 Mac/MLX 未派发任务不自动恢复。CUDA 环境与正式实验按新任务和版本化配置执行。

每个新/接续对话先实际读取并应用 avoid-overkill。S0 和所有独立 worker/reviewer 保持 gpt-6-astra / max；仅独立 Codex 对话与隔离 worktree，禁止 sub-agent，最多两个实现任务与一个重 GPU 作业。R1 技术独立审查；Q1 承接后续原需人工的语义、偏好及最终说明审核。同问题连续第 5 次正式修订未通过才整体暂停，按 [REVIEW_POLICY](REVIEW_POLICY.md)登记，旧失败保留。

用户已指定既有 Colab 路线，不据此新增购买、充值或公开服务。数据和模型身份、原始失败与正式结果须可追溯；公开仓库不含凭据、私人聊天或原始数据。无需为消息更新反复重跑未改变的已验收检查。

本机现存 S0 自动跟进配置读取为 PAUSED，本次未修改或恢复；后续是否恢复由用户的新接续安排决定。本文件不宣称 App goal 当前 ACTIVE，也不改变其真实状态。实际任务/自动跟进身份仅保存在本机。
