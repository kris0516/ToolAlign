# R1｜G4 生成 CPU 审查交接

**PASS（CPU 实现）**，新增 P0/P1/P2 均为 0。候选 `d1aa1c8e542898173455afbfa72d09fc3faaa9b7`；授权及实际受检源码 `f72bb5fc7343989efcfc01b305e690d0cddeb661`。分支 `codex/r1-p05-g4-cpu-r1` 同时交付生成与偏好两份独立结论，只新增各自报告和交接，共 4 个公开文件。[完整报告](../../reports/reviews/P05_G4_GENERATION_R1.md)。

实际检查支持：固定 CUDA/checkpoint/adapter 加载路径、完整输入与采样参数、2048 含生成预留边界、started/terminal 恢复和全计划分母，以及 Colab 外层进程组对真实 owned child 的回收。双包合计新增 **4 passed，0 failed，0 skipped**；生成器实际输出可被 D1 消费，未知语义与基础设施失败不会误作 rejected。S1 既有 2→4 恢复产物只回读并重做提取，得到 1 对 synthetic 偏好；没有重跑其原集成测试。

实际独立命令如下。`R1_CPU_PYTHON` 为指定既有环境，`R1_REVIEW_ROOT` 为本轮私有证据目录；两个 basetemp 均为本轮独占。命令由同目录 `run_check.py` 记录完整 argv、受检源码、退出码、时间和输出，设置离线、2 线程与单命令 300 秒上限。

```sh
"$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/run_check.py" independent-probes \
  "$R1_CPU_PYTHON" -B -m pytest -q "$R1_REVIEW_ROOT/test_independent_g4.py" \
  --basetemp "$R1_REVIEW_ROOT/pytest-independent"
"$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/run_check.py" controller-owned-child \
  "$R1_CPU_PYTHON" -B -m pytest -q "$R1_REVIEW_ROOT/test_colab_process_group.py" \
  --basetemp "$R1_REVIEW_ROOT/pytest-owned-group"
```

以上为已执行命令的路径变量化表示；复验时使用新证据目录，保留原回执。私有索引 SHA-256 为 `cd9e52b0291d5ffa414216e8fe7fc53cc7a3d85f0b54336c3262fbadcf48ec55`。复用 T1 的 170 passed / 2 skipped 及最后改动的 18 passed，未重复全套检查。

Q1 r1 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 的 `Q1-G4-CORPUS-001 / P2` 保持未关闭；D1 修订语料后须由 Q1 复核。S1 可接纳本 CPU 实现，完成语料验收后另行冻结 pilot。G4 真实生成、正式偏好和 DPO 仍 NOT_RUN；本轮无模型、安装、GPU 或共享状态写入，所有独立检查进程已回收。
