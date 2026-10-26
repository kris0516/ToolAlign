# R1｜DPO 输出预算 r2 复审交接

**PASS**，`P05-DPO-OUTPUT-001 / P2` 可由 S1 登记关闭，新增实质问题0。候选 `61f84f536d0181760aba23bc8e4637765e67cae1`，父提交/授权 `3890349baeb7f262230873bd0f52b4d05deeca4e`；分支 `codex/r1-p05-g4-dpo-r2` 直接从候选建立。[完整报告](../../reports/reviews/P05_G4_DPO_R2.md)。本复审提交仅新增报告和本交接。

原worker及请求复用，仅更换输出目录；原反例现返回/落盘均FAIL，实际完整目录61,595≤65,536字节，409字节终态回执包含原状态、拟写长度/hash和退出信息。60,000字节原文件完整保留，worker已回收。独立 **1 passed / 0.28秒，exit 0**。

已核对5个候选文件、69份E1证据与8条命令回执；复用其8 passed/1 deselected定点回归，覆盖普通PASS完整目录、UTF-8字节、预留空间、中途超限、墙钟、原始失败及回收。训练与恢复相关文件未变，r1的SUM/mask/reference/10对恢复证据继续复用，未重跑训练或整组回归。

实际独立命令如下。`R1_DPO_PY` 为派发的既有专用CPU解释器，`R1_REVIEW_ROOT` 为本轮私有证据目录。recorder固定本worktree源码、离线、2线程、300秒上限，保存完整argv、源码/脚本hash、退出码与输出；复验使用新目录并保留原记录。

```sh
"$R1_DPO_PY" -B "$R1_REVIEW_ROOT/run_check.py" original-counterexample-r2 \
  "$R1_DPO_PY" -B -m pytest -q -p no:cacheprovider \
  "$R1_REVIEW_ROOT/test_original_counterexample_r2.py" \
  --basetemp "$R1_REVIEW_ROOT/pytest-counterexample"
```

本轮证据索引SHA256：`b54bca032bc3250725ef3b08653706c8f2243f286b3912941d48a4fa65898f64`。原R1提交 `32a031b76a68a57945c6decce796ba6a9dd1836d`、首次正式REQUEST_CHANGES计1、原始失败现场均保留。建议S1按策略登记本轮通过及原问题关闭；未修改共享状态或旧报告。

本轮无模型加载、优化器更新、真实偏好编码、安装/环境变更或GPU/Colab操作。真实80条仍0对，复审PASS不放行DPO。
