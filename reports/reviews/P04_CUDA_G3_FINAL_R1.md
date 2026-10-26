# R1｜G3 实际 SFT 技术终验

2026-10-26。**PASS，P0=0、P1=0、P2=0。** 独立核对支持两模型完成冻结的一轮 SFT，并按完整 validation CE 选中 step 198/743 的完整状态。支持 S1 接纳 G3 技术结果；Q1 最终结论和主干集成由 S1 接续。

审查授权及材料提交：`c658541bbf966c324353404ed3d964329e7c1670`；真实执行源码：`2abbe7ac913661df1d5e430f285604b4ceb8ff4b`。范围见[任务包](../../coordination/tasks/P04_CUDA_G3_FINAL_R1.md)，对照材料为 [S1 实测报告](../S1_P04_CUDA_G3_SFT.md)。生产代码和依赖与已审候选 `c633bd70f4446bc8ea3ee80440944e6e6da7ff87` 一致。

## 实测数值与选模

| 模型 | 原始 validation CE | 所选 SFT CE | SFT − 原始 CE | 所选 step |
|---|---:|---:|---:|---:|
| Qwen3-0.6B | 0.7398840323 | 0.0414936900 | −0.6983903422 | 198 |
| Qwen3-1.7B | 1.1452295558 | 0.0244376391 | −1.1207919166 | 743 |

从 10 段实际 events 独立重建 **941 次连续更新**：smoke 消费 1,583 条，198 次更新、尾批 7 条；formal 消费 5,938 条，743 次更新、尾批 2 条。step、cursor、有效 batch、25 步 checkpoint 节奏及每 100 步/final 验证点均对应冻结计划，没有重复 epoch。

941 个训练 loss 均与其实际 batch 内逐例 loss 的算术均值一致。10 个 SFT 验证点与 2 个原始模型点，均满足已保存 `CE_sum / supervised_tokens`；完整 validation 的分母为 **21,226 / 23,841**，样本数为 194/213。上述重算残差均为 0。训练指标是 mean-example completion CE，验证指标是 completion+EOS token-weighted CE。

逐段按最低有限 CE、较早 step、checkpoint 摘要重新选模，结果与实际 summary、checkpoint index 和保存状态一致。两个原始模型点在 fresh 段首次更新前关闭 adapter 计算；续训段明确跳过，step 0 未进入 SFT 候选。两个 profile 的最后验证点均为最低 CE。

公开 941 行训练 CSV、12 行验证 CSV 与日志逐行一致；LF 换行及 SVG 行末空格规范化未改变数值和绘图内容。公共脚本、发布 CSV 与实际重画回执绑定，重画 PNG 与原分析 PNG 字节一致；已检查图像中的模型标签、原始点、所选点及右侧对数坐标。

## 完整状态与恢复链

R1 使用既有 CPU Torch 环境，以 `map_location="cpu", weights_only=True` 读取 **10 份唯一完整状态**；18 份保留副本与外部回收清单对应。每份包含 112 个 FP32 LoRA 张量和对应的完整 Adam 状态，形状、参数顺序、有限值、二阶矩非负、各 Adam step、恒定学习率、data cursor 及身份均通过。两模型的可训练参数分别为 1,146,880 / 1,605,632。

Python、NumPy、Torch CPU RNG 可在独立 CPU generator 中读取；单设备 CUDA RNG 为保存的 16 字节状态，本轮未调用 CUDA。每段终点的 adapter 与 RNG 摘要均由实际张量重算并匹配 events。**8 次续训**所指定的上一完整 state 摘要、保留副本及启动 adapter 摘要全部相符；同一 state 的字节绑定覆盖 optimizer、恒定学习率和 RNG。各段历史最佳及最近有分数的回滚状态得到保留，最后与最佳索引均指向实际选定状态。

| G4 可引用的 SFT 完整状态 | SHA-256 |
|---|---|
| smoke step 198，cursor 1583 | `e29e650615be4dbb71ff4cb50d02ecca008ddde5901c496845bdc5a4da3eb51f` |
| formal step 743，cursor 5938 | `cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14` |

各段绑定同一实际源码、各自完整数组、冻结模型 revision、Linux 依赖锁和 CUDA v2 配置；实际环境为 Torch 2.8.0+cu128 / CUDA 12.8 / L4，strict deterministic、warn_only=false、workspace `:4096:8` 均对应。完整 SFT 的底座内容全量 hash 保持 `NOT_RUN`。

复用 R1 `fd4ad07cb4a6a083c5fc178ba30a5705cc2a9684` 的原始 CE 实现审查、R1 `be756a152b13eb01d7586d961aee39a8298f1608` 的 G2 严格恢复实测，以及 Q1 `98cf0e1370ff68ca3306e157be1f7c95ac37a2e9` 的 7,928 行全数组审核。原报告与完成记录保持，当前数组文件摘要和 Q1 材料已核对；没有重跑旧矩阵或重新编码。

## 外部回收、资源与原始失败

10 份实际 tar 的成员与字节均匹配 **196 个索引产物文件和各自 MANIFEST**。10 个训练进程正常退出且时间不重叠，每段均在下一段启动前回收到 Mac；停止前 inventory 与这 10 份回收记录一致。该外部证据独立于 summary 内的 remote-copy 标记。

trainer 总时长为 smoke **876.210 秒**、formal **5,834.922 秒**。Torch peak allocated/reserved 分别为 **2.150/3.787 GiB**、**4.691/5.553 GiB**；1 秒设备采样峰值为 **4,174 / 5,982 MiB**，最小采样空闲比例为 **79.84% / 71.99%**。事件内存记录和采样均满足 20% 余量。

唯一实例累计占用 **9,124.538896 / 14,400 秒**，涵盖安装、下载、训练、验证、空闲及回收；账户余额观测差为 **3.85 / 8 CU**。原停止命令成功，07:50:27 UTC 的停止回执确认实例不存在，后续账户查询为 0 active assignments、0.00 CU/hr。回读时 S1 私有证据约 1.080 GB，低于 4 GiB；余额差不作为精确账单归因。

158 条原始命令回执及其 stdout/stderr 均完成绑定。其中首次 setup 包装命令 exit 1，对应 SSH exit 255 / Broken pipe；同一远端原安装进程随后 exit 0、pip check 通过。原失败保留，10 段训练全部正常退出。另有 1 条训练前只读分母统计在 `7eb0ac97e394528d82533c6cc92c298aa5d305b0` 执行，其余 157 条命令绑定实际源码 `2abbe7ac`；G3 计划仅补入四个监督 token 总数字段。

R1 首轮核对脚本曾把上述早期统计和计划元数据扩充误要求为同一源码版本，产生 5 项断言失败、命令 exit 1。根据原始 receipt 与 Git 差异纠正核对范围后全部解除；原脚本、失败输出及修正回执保留，未更改生产实现或训练证据，没有形成候选缺陷。

| R1 私有证据 | SHA-256 |
|---|---|
| 最终独立结论及命令索引 | `cbd3ab9b377f81e781f1f6cee9663f2f654b562cc94f8af76bc812bf7a9fc570` |
| 原源码范围假设的证据纠正 | `2f0be6c5ab9fdf5fda7e4f0ca3dc52879cbf847e035ddfc66702b1bee391e26b` |
| 独立事件、CE、选模与资源重算 | `b1fa8ae4a4b259fe30e0dd3be9ebf54578529b312abbe17e40b81d77a937906a` |
| CPU 完整状态与续训核对 | `293770ab973e6687be3b2dced3e79f25165f6a3ee3fe49c64093bcb5932201a7` |
| 公开绘图、原安装失败及既有审查绑定 | `425a1e386338a1a2f53ed2c6a9750d789aabb25aad25ed8dd5ded3cddfa7c5e1` |

输入总索引 SHA-256 为 `be10313e0c200dde1a8c2c4660842a3d2474d9210ab7d01bda2cc506cecef544`。本轮仅在 Mac 只读分析保存张量、日志与归档，使用 2 线程和单命令 300 秒上限，新增私有材料不足 1 MiB；没有新增真实模型加载、训练、编码、SSH、GPU 或安装。结论为各模型在自身冻结 validation 上的 CE 降低和完整 SFT 状态验收；工具语义效果、DPO 和服务属于后续范围。
