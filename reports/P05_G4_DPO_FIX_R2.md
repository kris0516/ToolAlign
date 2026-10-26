# P05 G4 DPO 终态输出预算修订 r2

2026-10-26；E1。**本地定点验证通过，待 R1 复审**。修订 `P05-DPO-OUTPUT-001`：最终 summary 的完整编码字节现已计入输出预算；写入会超限时返回并保存有限大小的 FAIL 回执，已有产物保持原样。

起点为 S1 授权 `3890349baeb7f262230873bd0f52b4d05deeca4e`，分支 `codex/e1-p05-g4-dpo-r2`，执行[本轮任务](../coordination/tasks/P05_G4_DPO_FIX_R2.md)。起点已包含原候选和 R1 报告，没有重新 cherry-pick 原提交。[R1 首次 REQUEST_CHANGES](reviews/P05_G4_DPO_R1.md)及正式未通过计1保留，是否关闭问题由 R1/S1 定点复审决定。

## 原反例与修订

原实现检查目录大小后，才附加退出信息、编码并写入 `summary.json`，因此漏计最后一份文件。R1 的65,536字节反例为：summary前61,185字节，summary 8,357字节，最终69,542字节，返回值及文件均为PASS。

本轮先逐字节复制 R1 原反例并在未改的授权起点执行，**1 failed / 0.23秒**，复现最终69,525字节仍PASS；与R1的17字节差来自请求中的路径长度。R1原脚本、观察值和失败回执均保留。新增正式回归在修订前也实际得到 **2 failed / 0.15秒**，分别覆盖原ASCII回执和UTF-8多字节回执。

改动限于 `cuda_dpo/runtime.py` 的监督与终态写入：

- 在同一个 `max_output_bytes` 内为失败回执预留4096字节；连请求快照与该预留都放不下时，在创建输出目录、启动子进程前拒绝。运行中和子进程退出后的目录检查保留该空间。
- 子进程回收、退出信息补齐后，计算 `encoded(result) + b"\n"` 的实际字节数，与已有完整目录字节数相加，再决定终态。没有按字符数估算，也没有扩大冻结预算。
- 若拟写回执超限，改为FAIL，记录原状态、预算、写入前目录字节数、拟写summary的字节数及SHA256、原错误的有限摘录和退出信息；该失败回执本身验证不超过4096字节。返回对象与落盘summary一致。
- 已有输出不删除、不截断。若worker在父进程两次观察之间单次写入已超限，仍保留原文件并明确FAIL；不会把该目录报告为符合预算。

没有修改 DPO loss、data/models/trainer/checkpoint、协议、依赖、Colab脚本、共享状态或R1原报告。

## 定点结果

专用环境沿用 r1：Python3.12.14、pytest9.0.2，Torch2.8.0 / TRL0.26.2 / Transformers4.57.6等安装版本未改。测试只启动原创CPU文件/回执worker，没有模型加载或优化器更新。

| 场景 | 修订前 | 修订后 |
|---|---|---|
| 原反例对应回归，60,000字节产物 + 8,192字符元数据，预算65,536 | 目录69,517，summary8,358，PASS | 目录61,560，summary401，**FAIL**；60,000字节产物逐字节保留 |
| UTF-8回执，2,048个中文字符，预算65,536 | 目录67,470，summary6,311，PASS | 目录61,560，summary401，**FAIL**；按实际编码字节判定 |
| 普通成功大回执，预算1MiB | 既有路径 | 目录321,295，summary320,134，PASS；完整目录在预算内 |
| 运行中进入回执预留空间，预算65,536 | 新增边界检查 | 目录63,742，FAIL；62,400字节原文件保留，worker回收 |
| 运行中单次写出32,768字节，预算8,192 | 既有超限路径 | FAIL；原32,768字节文件完整保留，worker回收 |
| 墙钟超时、原始worker失败、预算不足以启动 | 受影响边界 | 超时及原始失败原因保留；不足预算启动前拒绝；所有已启动worker均回收 |

最终 **8 passed、1 deselected / 1.46秒，exit 0**。取消选择的是未修改的checkpoint检查；原生数值、reference和10对恢复按R1已支持的证据复用，没有重跑训练。相应3个Python文件Ruff检查 exit 0。

实际定点命令如下，`DPO_PY` 指既有专用CPU环境：

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "$DPO_PY" -m pytest -q tests/training/test_cuda_dpo_process.py -k 'not resume' --basetemp .toolalign-local/p05-g4-dpo-r2/pytest-004
.venv/bin/ruff check src/toolalign/training/cuda_dpo/runtime.py tests/training/dpo_process_cases.py tests/training/test_cuda_dpo_process.py
```

私有 `.toolalign-local/p05-g4-dpo-r2/evidence-index.json` 绑定精确提交、差异、环境、各条argv/退出码、修改前后的观察值、公开内容检查及原始R1证据引用。R1原索引SHA256为 `97aeb1e34e246a8f9006b99bc429a6a387263046815eea6e8fd2de5d96129519`，S1接纳文件SHA256为 `1e864c2c32f3d10e1f013c35794d608a900a11e7480e6a1fd9ff6422c4ad992f`，本轮读取均匹配。

本轮没有安装/环境变更、模型下载、真实偏好编码、GPU或Colab操作。真实80条候选的0成功/0偏好状态不由本工程修订改变；正式DPO未获运行许可。交付后由R1只复审输出预算边界。
