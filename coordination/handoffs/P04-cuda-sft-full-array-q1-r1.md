# Q1 → S1｜G3 完整 SFT 数组-r1

**PASS：完整 smoke/formal 数组通过独立增量审核，可供 S1 冻结既定 G3 运行配置。** 实际 reviewer：Codex-AI（Q1），`gpt-6-astra / max`。授权及 reviewed source 为 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。本交接与[审核报告](../../reports/reviews/P04_CUDA_SFT_FULL_ARRAY_Q1_R1.md)同一提交交付，精确提交号见 Git 记录与最终回报。

| Profile | train 行 / 监督 token | validation 行 / 监督 token | 一轮更新数 / 尾组 |
|---|---:|---:|---:|
| smoke | 1,583 / 141,211 | 194 / 21,226 | 198 / 7 |
| formal | 5,938 / 536,238 | 213 / 23,841 | 743 / 2 |

两套合计 7,928/7,928 行逐一对应冻结 example/sidecar、实际 stage 和 arrays，ID/rank/顺序、token 摘要、P/C/N、单 EOS、padding、一次 causal shift 与完整监督 mask 均通过。137 项文件/来源/汇总核对无失败；未读测试集 payload。两套 13 例材料内容身份不变，沿用 `82f1e88`、`ed022da`、`847e0be` 结论，未重跑旧 531 项矩阵。

smoke arrays manifest：`9a504ffd00b571eb5f5294d174d4285c92a695dee0d3171988d572185a860b5b`；formal：`58b59c6a47be9c768835dadf020a303c801909f8ad07b1875918ee2168170d58`。S1 原索引为 `533752d2223111f3476cd9b04f4ab8d5632d03ff8954f76a9dbb373931edb5ab`。四个生成回执退出 0、源码未变，新编码严格为 1,777/6,151 次；Q1 本轮新增编码为 0。

私有入口 `.toolalign-local/q1-p04-cuda-sft-full-array-r1/`，新增产物约 4.7 MiB：

| 文件 | 内容 / SHA256 |
|---|---|
| `authorization.json`、`inputs.json` | 授权和 46 份小型元数据副本；大型文件只读流式核对 |
| `review-r1/result.json` | 完整统计、71 个输入路径身份与全部核对项；`76b84c1405235ca6176bb89d13d5c74b0589bc5d15040a1aa3fc8e24ce47f025` |
| `review-r1/row-verdicts.jsonl` | 7,928 行 ID/rank/摘要/边界/判定；`c6fdf943ef4f053e0deb54832c93b6546749d381c5e40f3a319406ca411a9133` |
| `review-command-r1.json`、`review-r1.stdout.txt`、`review-r1.stderr.txt` | 原始 argv、限制、退出与输出；回执 `6be4bfa82514a1c515fb23bed4d17ec31899f84f7d45a35b17c3eee72f5ba40e` |

首次核对 exit 0、14.164 秒，未新增 issue。真实模型/GPU/SSH/编码/安装均为 0；完整 SFT 与模型效果仍 NOT_RUN。后续运行按上述源码与实际数组 manifest 绑定，执行和结果验收由 S1 继续组织；Q1 未改共享状态。
