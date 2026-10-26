# P04-COLAB-ENVIRONMENT｜E1 交接 r4

2026-10-26。**READY_FOR_REVIEW**，供 R1 独立增量复审。

- 基点：`920c41551f0f7f2be8a5a8dcced23cc080ac1f27`。
- 授权：`b1a1af1c059f1d0fd6e8db36b42cfe2d4c55dd1d`。
- 实现：**`2ecb7a8b1ca73386f68d79d34896a3aedeb2658e`**，已先行推送；最终候选仅再增加本交接及 r4 报告，精确 SHA 随最终回执提供。
- 分支：`codex/p04-colab-environment-r4`。
- 新 Linux 锁 SHA-256：**`6a793bfd46af168b2df581f19ce8f23f97af239a12ac95b436e99baff080b2ea`**。

Linux 锁内同时声明 PyPI 与 CUDA 源，修正 pip 24.0 读取锁时覆盖 CLI extra index 的问题。原 48 个包和 894 条 hash 声明逐字保持，Mac 锁不变；没有重跑 uv。文档补入生成后处理及 Ubuntu `python3.12-venv` 前置条件。S1 后续配置需要绑定新锁哈希。

[验证报告](../../reports/experiments/P04_COLAB_ENVIRONMENT_R4.md)保留了旧锁 **2 failed**、中间测试空格比较失败及最终 **4 passed / 0 skipped / ruff PASS**。最终真实 pip 24.0 解析在两种入口下均保留两个源。本轮只下载 2.1 MB 的纯 Python pip wheel，通过私有 `PYTHONPATH` 加载，没有安装或升级 pip。

私有 `p04-colab-environment-r4/` 提供授权、S1 原诊断副本、旧锁、wheel 来源、原始命令/JUnit 及实现绑定核对；旧候选、报告、失败现场保持。GPU、SSH、CUDA wheel/模型下载、真实数据和训练均为 0。R1 verdict、正式问题计数及新 Colab 实例的真实安装验收由 R1/S1 完成。
