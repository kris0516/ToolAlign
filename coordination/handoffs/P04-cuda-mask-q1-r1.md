# Q1 → S1｜P04 CUDA mask-r1

结论：**PASS（13 例真实材料与指定 CUDA 实现预审）**。实际 reviewer 为 Codex-AI（Q1），`gpt-6-astra / max`。本轮候选是 `4342af87615197c7947d001f462d3d31500cd501`，授权为 `10a2083fd3741bd7501449d0deb6e483ce30ee7f`；完整范围、输入 hash 和证据见[审核报告](../../reports/reviews/P04_CUDA_MASK_Q1_R1.md)。本交接与报告同一提交交付，精确提交号见本文件的 Git 提交及原生最终回报。

423 项完整数组/来源/角色/配置检查通过，26 条原 engine 证明与 Q1 自有旧裁定逐条绑定通过。10 条训练材料保持 completion+单 EOS 监督，3 条协议材料不进入训练。CUDA 的一次 causal shift、训练样本均权、验证 token 加权和尾组 7/2 与冻结约定一致；容量 8+8+2 的报告明确为诊断用途。

本轮私有证据在 `.toolalign-local/q1-p04-cuda-mask-r1/`：

| 文件 | 内容 |
|---|---|
| `authorization.json`、`inputs.json` | 保存的授权文件和精确输入来源/字节身份 |
| `review-result.json` | 13 条逐例结论及 423 项检查；SHA256 `4f702875bbd972faa67a62bc5bbe771658e045183b2f4f012b83c8cdc17d2812` |
| `review-binding.json` | 26 条原证明绑定及静读文件身份；SHA256 `9158ccf00dccad01f7b86a8500c5a8570ecd4b59e957fae121f216ef5133e05b` |
| `review.r2.command.json`、`review.r2.stdout.txt`、`review.r2.stderr.txt` | 成功比较命令的实际退出码、耗时和输出 |
| `review_arrays.r1.py`、`helper-failures.json`、`review.r1.reproduction.stderr.txt` | 审查脚本对协议空字段的初始失败及复现；原失败未覆盖 |

实际成功命令列于报告；GPU、SSH、新编码、模型下载/加载/训练均为 0。公开改动仅此交接和审核报告；不修改生产、数据、配置、协调状态或旧审核结论。新增稳定 issue 建议为 0。

下一输入是 S1 经整合后的新入口 20 条容量数组及精确导出/回读证据，收到后进行增量复核。本轮不等待这些尚不存在的数组，按现有 13 例完成交付；20 条数组、CUDA 实测、跨实例恢复和正式模型结果仍为 NOT_RUN。E1 待修控制代码及 R1 工程审核由各自范围承接，本预审不批准运行。
