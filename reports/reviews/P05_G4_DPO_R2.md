# R1｜DPO 输出预算 r2 定点复审

2026-10-26。**PASS**。`P05-DPO-OUTPUT-001 / P2` 的终态预算缺口已通过定点验证，建议 S1 登记关闭；新增 P0/P1/P2 均为0。[r1 正式 REQUEST_CHANGES](P05_G4_DPO_R1.md)、首次未通过计1及全部失败证据保留。

精确候选 `61f84f536d0181760aba23bc8e4637765e67cae1`，父提交及授权 `3890349baeb7f262230873bd0f52b4d05deeca4e`。本轮直接从候选建立 `codex/r1-p05-g4-dpo-r2`，按[修订任务](../../coordination/tasks/P05_G4_DPO_FIX_R2.md)仅复审输出预算。5个候选文件与 Git blob、交付索引一致；相对 r1 受检版本，生产/配置/依赖/脚本/测试范围只有 runtime 和两个进程测试文件变化。

## 根因修订

[runtime.supervise](../../src/toolalign/training/cuda_dpo/runtime.py) 在子进程回收并加入退出信息后，计算完整 `encoded(result) + b"\n"`，与输出目录实际字节数相加，再决定终态。普通 PASS 必须容纳这份完整 summary。

同一冻结上限内预留4096字节用于失败回执；请求快照和预留放不下时，在创建输出目录和启动 worker 前拒绝。拟写 summary 超限时改为 FAIL，记录原状态、预算、已有字节数、拟写字节数/hash、有限错误摘录及退出信息，并检查该回执不超过预留。已有文件保持原样。worker 若单次写入已经超限，原超限文件继续留证并记 FAIL。

## 独立复验

R1 逐字节复用原 worker，读取 r1 原请求，仅替换本轮输出目录；原65,536字节预算、60,000字节产物及8,192字符回执字段保持。使用现有专用CPU环境，生产 spawn/Pipe、监督、编码、文件写入与回收均实际执行，**1 passed / 0.28秒，exit 0**。

| 本轮原反例 | 实测 |
|---|---:|
| 写 summary 前 | 61,186 bytes |
| 拟写完整原 PASS summary | 8,358 bytes |
| 若直接写入的总量 | 69,544 bytes，超过65,536 |
| 实际有限 FAIL summary | 409 bytes |
| 实际完整输出 | **61,595 bytes ≤65,536** |

返回值与落盘 summary 均为 FAIL，拟写回执长度及 SHA256 与独立重建的实际编码一致。原60,000字节文件逐字节保留，worker退出码0且已回收。原 r1 的69,542字节/PASS现场没有覆盖或重跑。

另外回读并绑定 E1 的69份材料、8条命令回执和最终受检源码，复用 **8 passed / 1 deselected / 1.46秒**：ASCII及UTF-8超限回执均改为FAIL；普通大回执成功目录321,295字节≤1MiB；进入预留空间时FAIL；墙钟、原始失败及worker回收保持。中途单次写出的32,768字节原文件在8,192字节预算失败后完整保留。未选择的是未修改的checkpoint检查；没有重跑这组回归。

data/models/trainer/checkpoint、配置、依赖与Colab脚本未变，r1已支持的SUM/mask/EOS/梯度、启用同一SFT adapter的独立reference和10对CPU恢复证据继续有效，本轮未重跑训练。

私有 `evidence-index.json` SHA256：`b54bca032bc3250725ef3b08653706c8f2243f286b3912941d48a4fa65898f64`；绑定10份本轮材料、精确源码、原反例、执行回执与回读记录。[交接](../../coordination/handoffs/P05-g4-dpo-review-r2.md)给出复验入口。共享台账由S1维护。本轮未加载模型、编码真实偏好、安装/修改环境或操作GPU/Colab；当前真实80条仍为0对偏好，DPO继续未放行。
