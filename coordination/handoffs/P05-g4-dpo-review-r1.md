# R1｜G4 DPO CPU 审查交接

**REQUEST_CHANGES**，P0=0、P1=0、P2=1。候选 `982cc1917d23b4004dbf9f683c685515eb390ea7`；授权 `0b470325f0aff277285026f2d6c2e691ee7dd975`。分支 `codex/r1-p05-g4-dpo-r1` 从授权建立并 cherry-pick 候选为 `8261d2a92ce2a09d3ba0b18a471ee5de92847861`，24个交付文件一致。[独立报告](../../reports/reviews/P05_G4_DPO_R1.md)。R1 后续提交仅新增报告及本交接。

**P05-DPO-OUTPUT-001 / P2**：`runtime.supervise` 在写入最终 summary 前检查目录大小，之后仍返回 PASS。原创 CPU 反例的预算65,536字节、写终态前61,185字节，加入8,357字节 summary 后达到69,542字节；返回与文件状态均为PASS，worker已回收。需要 E1 将终态写入纳入完整预算、超限记FAIL并留存失败回执，补该边界回归。建议 S1 登记一个新实质问题；原失败及修订记录保留。

原生数值与CPU恢复获得支持：独立3对、4,720参数 fixture 的 SUM/mask/EOS/梯度和两条 logits_to_keep 路径在预定容差内通过；原生尾组3对的梯度相对独立均值参考最大误差2.2352e-8，仅policy adapter变化。原10对checkpoint和81份证据已直接回读，连续/恢复的adapter、Adam和尾梯度差为0，scheduler/RNG一致，新进程只消费末2对。未重跑10对训练或全部70项控制测试。

实际命令以变量表示如下。`R1_DPO_PY` 是派发的既有专用CPU解释器，`R1_REVIEW_ROOT` 是本轮独占私有目录；`run_check.py` 固定自身受检src、离线和2线程设置、每命令300秒上限，并保存完整argv、源码、脚本hash、退出码与输出。复验必须用新证据目录，保留已有回执。

```sh
"$R1_DPO_PY" -B "$R1_REVIEW_ROOT/run_check.py" output-budget-regression \
  "$R1_DPO_PY" -B -m pytest -q "$R1_REVIEW_ROOT/test_output_budget.py" \
  --basetemp "$R1_REVIEW_ROOT/pytest-output-budget"
"$R1_DPO_PY" -B "$R1_REVIEW_ROOT/run_check.py" independent-native \
  "$R1_DPO_PY" -B -m pytest -q "$R1_REVIEW_ROOT/test_native_review.py" \
  --basetemp "$R1_REVIEW_ROOT/pytest-native"
"$R1_DPO_PY" -B "$R1_REVIEW_ROOT/run_check.py" independent-numerics-corrected \
  "$R1_DPO_PY" -B -m pytest -q \
  "$R1_REVIEW_ROOT/test_native_review.py::test_independent_native_sum_mask_reference_and_three_pair_tail" \
  --basetemp "$R1_REVIEW_ROOT/pytest-numerics-corrected"
```

第一条实际1 failed，构成本轮问题；第二条使用保留的 initial 脚本版本，恢复回读通过，数值探针因负对照修改reference梯度标志而失败；第三条将负对照移到独立副本后1 passed，冻结断言及候选实现未改。完整差异、两个版本、原回执均在私有证据中，不能将第二条的辅助代码失败登记为候选缺陷。

本轮索引 SHA-256：`97aeb1e34e246a8f9006b99bc429a6a387263046815eea6e8fd2de5d96129519`。E1 原索引 SHA-256：`5b41c51428b5b63ae1382c7f2081d7d7b508e715ed1df0e62f09f3de4d7e449b`。独立测试、原始数值/失败、24文件绑定及依赖回读均已归档。

下一步由 S1 交 E1 定点修订并安排 R1 复核；未受影响的数值/恢复证据继续复用。本轮不改生产、共享状态或专用环境。真实Qwen、正式偏好编码、DPO CUDA安装/容量/恢复和正式DPO均NOT_RUN，未发生GPU/Colab操作，也不产生真实运行授权。
