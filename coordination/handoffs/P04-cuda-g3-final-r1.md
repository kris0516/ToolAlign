# R1｜G3 实际 SFT 技术终验交接

**PASS，P0/P1/P2 均为 0。** 授权材料 `c658541bbf966c324353404ed3d964329e7c1670`；真实执行源码 `2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。分支 `codex/review-p04-cuda-g3-final-r1` 从精确授权提交建立，只新增本交接及[独立报告](../../reports/reviews/P04_CUDA_G3_FINAL_R1.md)，未维护共享状态。

独立重建 10 段、941 次更新和 12 个验证点；实际消费 1,583/5,938 条、完成 198/743 次更新，尾批 7/2，未重复 epoch。训练逐例均值、完整验证 CE 商与公开 CSV 一致，原始点不参与 SFT 选模。所选 CE 为 0.0414936900 / 0.0244376391，原始 CE 为 0.7398840323 / 1.1452295558，分母 21,226 / 23,841。

已在 CPU 读取 10 份唯一完整状态，核对 18 份保留副本和 8 次接续；LoRA、Adam、恒定学习率、step/cursor、RNG 结构与摘要、历史 best 及恢复文件身份通过。可接纳的完整状态如下：

- smoke step 198：`e29e650615be4dbb71ff4cb50d02ecca008ddde5901c496845bdc5a4da3eb51f`。
- formal step 743：`cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14`。

10 份实际归档与 196 个索引产物完成回读核对；外部回收先于下一段启动，唯一实例已停止。累计占用 9,124.538896 秒、余额观测差 3.85 CU，满足冻结资源边界。Torch 峰值与设备采样分别登记，完整 SFT 底座全量内容 hash 仍为 NOT_RUN。

复用 R1 `fd4ad07`、G2 实测 R1 `be756a1` 和 Q1 全数组 `98cf0e1`，未重跑旧矩阵。158 条原始命令中保留首次安装 SSH Broken pipe 失败及同一安装进程随后成功的证据。R1 自身首次源码范围断言失败也完整保留，纠正依据及其后通过记录见报告；没有候选缺陷。

私有 `audit-result.json` 摘要为 `cbd3ab9b377f81e781f1f6cee9663f2f654b562cc94f8af76bc812bf7a9fc570`，绑定各核对结果和命令回执；最终文件清单为本轮私有 `handoff-index.json`。输入总索引摘要为 `be10313e0c200dde1a8c2c4660842a3d2474d9210ab7d01bda2cc506cecef544`。

本轮主要核对命令如下；`R1_REVIEW_ROOT` 指本轮私有证据目录，`R1_CPU_PYTHON` 指指定既有 Torch 环境。记录器为每条命令设置 2 线程、300 秒上限并回收进程；完整 argv、源码提交、时间与退出码已保存。

```sh
python3 -B "$R1_REVIEW_ROOT/run.py" records python3 -B "$R1_REVIEW_ROOT/audit_records.py"
python3 -B "$R1_REVIEW_ROOT/run.py" states "$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/audit_states.py"
```

本轮新增模型加载、训练、编码、SSH、GPU 和安装均为 0，私有材料不足 1 MiB。支持 S1 接纳技术终验并保留上述 SFT 状态；Q1 最终说明审核、主干集成及 G3 正式状态由 S1 维护。
