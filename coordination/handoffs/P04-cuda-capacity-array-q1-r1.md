# Q1 → S1｜P04 实际容量数组-r1

**PASS：20 条实际容量数组通过增量复核，可作为既定预算容量配置的输入。** 独立 reviewer 为 Codex-AI（Q1），`gpt-6-astra / max`。reviewed source：`920c41551f0f7f2be8a5a8dcced23cc080ac1f27`；authorization：`594894d4dc8050f301eb8f419ee674ef43786b7c`。本交接与[审核报告](../../reports/reviews/P04_CUDA_CAPACITY_ARRAY_Q1_R1.md)同一提交交付，精确提交号见 Git 记录和最终回报。

531 项比较全部通过：18 train / 2 validation 的原行、sidecar、固定 cohort/rank、完整数组、单 EOS、右 padding、一次 causal shift 及解码文本均对应。满桶训练例保留 EOS；历史 assistant/tool 消息不进入监督。容量验证总分母为 335，训练组保持 8+8+2。旧 13 例与 `82f1e88` 预审实物逐字相同，沿用结论。

私有证据位于 `.toolalign-local/q1-p04-capacity-arrays-r1/`：

| 文件 | 内容与身份 |
|---|---|
| `authorization.json`、`inputs.json` | 授权副本及 21 份实际输入的来源、字节数和 hash |
| `review-result.json` | 20 条逐例结论与 531 项检查；SHA256 `ba31264fb2433e09591246d67a527495110b53effa565ff6377fc69ca64d7bb9` |
| `review-command.json`、`review.stdout.txt`、`review.stderr.txt` | 实际命令、约 0.452 秒/exit 0、原始输出；命令记录 SHA256 `5c9ed52231671190a17dfb9b5e51264b1fdfc029c95127e51e996509140c5c37` |
| `decoded-records.json` | 20 例已有 token 的实际解码文本，仅私有保存；SHA256 `0bf686c936b6fadad98bb05853aa366ba31e064bd27cccf2d499b6f7796f87d7` |

本轮无新增失败或 issue 建议，旧记录保持；问题正式次数由 S1 维护。公开修改仅本报告与交接，生产、配置、原数组和共享状态未改。新增编码、GPU、SSH、模型加载/下载/训练、环境安装均为 0。

CUDA 容量实测、外部持久化、新实例恢复、正式 epoch 和模型效果仍为 NOT_RUN；后续真实运行保持数组绑定的 `920c415` 源码，实际结果交付后再审。
