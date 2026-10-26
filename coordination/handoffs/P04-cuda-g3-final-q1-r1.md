# Q1 → S1｜G3 实际 SFT 数据与说明终验-r1

**PASS：941 条训练事件、12 个完整验证点、实际输入身份、选模、回收/停止记录及报告解释均通过。** 实际 reviewer：Codex-AI（Q1），`gpt-6-astra / max`。授权 `c658541bbf966c324353404ed3d964329e7c1670`，实际训练源码 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。本交接与[完整审核报告](../../reports/reviews/P04_CUDA_G3_FINAL_Q1_R1.md)同一提交交付，精确提交见 Git 记录及最终回报。

| Profile | train / validation | 更新 / 尾批 | 原始 CE → 所选 SFT CE | 最佳 step |
|---|---:|---:|---:|---:|
| smoke | 1,583 / 194 | 198 / 7 | 0.739884032 → 0.041493690 | 198 |
| formal | 5,938 / 213 | 743 / 2 | 1.145229556 → 0.024437639 | 743 |

实际数组 manifest 与本人 `98cf0e1` 已审副本一致，验证分母为 21,226/23,841；13 例材料审核沿用，未重跑全数组或旧质量矩阵。每段 cursor 连续，尾批分母准确，恢复分段不作独立重复实验。训练 mean-example loss 与验证 token-weighted CE 分开标注，原始点不参与 SFT 选模，测试集未消费。既有公开脚本复画 PNG 与汇总 PNG 相同，CSV 全行数值与日志相同。

10 段 exit 0；196 个文件与 10 个归档完成字节校验，回收清单与停止 inventory 对应。设备 6,269 条采样支持报告中的观测峰值；唯一 L4 已停止且当时 CLI 确认不存在，最终账户记录为 0 active assignments。占用 9,124.538896/14,400 秒，余额观测差 3.85/8 CU，未写成精确账单归因。

保留安装 SSH 255/Broken pipe、本地包装 exit 1，以及原安装进程最终 exit 0 的真实历史。早期只读统计来自 `7eb0ac9`；后续 157 条记录、数组和训练来自 `2abbe7ac`，各回执与自身提交一致。Q1 首次 helper 的“一律同一 HEAD”假设失败已保留，仅来源补核后通过；其余已通过检查未重跑，无需登记生产修订失败。

私有入口 `.toolalign-local/q1-p04-cuda-g3-final-r1/`：

| 文件 | 内容 / SHA256 |
|---|---|
| `inputs.json` | 输入副本及流式字节核验记录；`dac9436b73f33b489bcd679cc7ff42eadb3a0aacce2ae606be995462e204940c` |
| `review-final-result.json` | 最终 PASS，关联原核对及来源补核；`1ae5741e29cd4816720ce7306f93d82faf6a532384d896868a2f2bbab1dacab3` |
| `manual-review.json` | 图像、指标口径、源码和结论范围；`135a2811d13eb4ebf2afad9de1dcf0d6bcfff6f27539ce01f6e0c9aa4af688e3` |
| `review-command-r1.json`、`review-source-command-r2.json` | 原始命令、退出与输出，0.178/0.193 秒，300 秒/2 线程限制 |

公共改动仅两份审核文档；私有新增小于 35 MiB。Q1 未加载模型/张量、调用 GPU/SSH、重新编码或安装。完整 SFT 底座内容全量摘要保持 `NOT_RUN`，R1 负责独立张量与恢复技术终验。S1 结合 R1 结论决定 G3 接纳和 G4；工具语义、无需工具判断、故障恢复行为和测试效果属于 G5，DPO 属于 G4。本交付不改共享状态或宣布全项目完成。
