# Q1 → S1｜P04 CUDA G2 实际结果终验-r1

**PASS（数据与报告范围）。** 实际 reviewer 为 Codex-AI（Q1），`gpt-6-astra / max`。授权 `873b88858da13c993ebeeee4c17546772752413f`；reviewed source `eb73fbcdb5f053509a396c59092e28d7c317cdd9`；被审报告 SHA256 `5421c2a410e79b723a921ce206afb4c65c16e2344e8b532b48efbaae5e0240d5`。本交接与[审核报告](../../reports/reviews/P04_CUDA_G2_FINAL_Q1_R1.md)同一提交交付，精确提交号见 Git 记录及最终回报。

20 条数组和 13 例材料逐字节对应 Q1 `ed022da` 留存实物，沿用 `ed022da` / `82f1e88` 的语义与 mask 结论。新旧 manifest 仅五处 v2 配置/源码绑定变化；完整 profile 保持 5,938/213。实际组长为 8+8+2、2、2，更新数 3+1+1，最终游标 18，验证分母 335。98 项核对全部通过；原 531 项矩阵未重跑。

同实例新进程和新实例均有实际记录；新 v2 第 2 步经外部回收、第一实例停止后，才在新实例恢复。65 个回收文件、三份完整 state 的相同摘要和 33 份命令回执对应；S1 的 1,883 项/672 张量比较已核对结果与绑定，Q1 未加载张量，技术验收交 R1。两实例停止回执及末次账户记录支持 G2 累计 3,640.213026/5,400 秒、0 active assignments；1.27 CU 为余额观测差。

原 v1 FAIL、零更新诊断、两次 SSH 断线和一次 HTTP 429 均保留；reviewer helper 的时间读钟等值假设错误及一次字段探查错误也留档。最终核对 exit 0、约 0.090 秒，无候选新增 issue 建议。正式 SFT、DPO、模型效果和服务仍 NOT_RUN；S1 结合本结论与 R1 技术终验裁定 G2，不由 Q1 提前关闭问题或整体目标。

私有证据入口：`.toolalign-local/q1-p04-cuda-g2-final-r1/`。

| 文件 | 用途 / SHA256 |
|---|---|
| `authorization.json`、`inputs.json`、`additional-inputs.json` | 授权与 206 个输入路径的实际字节绑定；197 份非二进制副本、9 份二进制流式核对记录 |
| `review-result.json` | 98 项核对及指标；`43faa51cd1d8f4817137edf5228272f458509a6e44a7aa9895711cf5690886e6` |
| `review-command-r2.json`、`review-r2.stdout.txt`、`review-r2.stderr.txt` | 完整 argv/限制/退出与原输出；回执 `6bb915399585f6fadd19d0ccaaeb17235fd988630a0c55b4623d64378a27d1be` |
| `prior-review-binding.json` | 直接绑定原 Q1 manifest/结论与本次五处差异；`f4395eb165d5de6455a14291d2f7aa6ea84e7f93b8245eb025d0bed2c355b9cd` |
| `review_results-r1.py`、`review-result-r1.json`、`review-command-r1.json`、`review-r1.*.txt` | 首次 helper 失败保留，纠正原因见正式报告 |

本次公开改动仅审核报告与交接；新增私有产物约 10 MiB。生产、配置、原数组和共享状态未改，新增 GPU/SSH、模型、训练、编码、安装均为 0。
