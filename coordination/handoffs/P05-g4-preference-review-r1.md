# R1｜G4 偏好 CPU 审查交接

**PASS（CPU 实现）**，新增 P0/P1/P2 均为 0。实现候选 `147d0450447a7ad543a7a913f2a9084b039b849d`；授权及实际受检源码 `f72bb5fc7343989efcfc01b305e690d0cddeb661`。补充交接 `938c47166786c1ad3b45314ee16d04aa35b4eeac` 只改文档。分支 `codex/r1-p05-g4-cpu-r1` 只新增双包各自报告和交接，共 4 个公开文件。[完整报告](../../reports/reviews/P05_G4_PREFERENCE_R1.md)。

实际输入身份、首分歧当前语义、prior observation 依赖、固定选对顺序、全计划分母、双方原始 completion/采样参数及 Q1 gate 均符合冻结协议。双包共 **4 项独立 CPU 检查通过**；本包新增的实际生成器反例确认合法未知及后续基础设施失败不产生偏好，另一项确认未使用的 advertised 工具也能触发整组传递隔离。独立命令与环境见[同轮生成交接](P05-g4-generation-review-r1.md)，不重复累计共享检查。

补充只回读 S1 已保存的 2→4 恢复产物并重新提取，得到 1 对 synthetic 偏好且保留 seed 42/43；未重跑 S1 原集成测试或生成额外候选。复用 D1 的 42 passed 与 52 条原作者 CPU 验证记录，已核对最终源码及产物身份。补充回读的实际入口为：

```sh
"$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/run_check.py" supplement-readback \
  "$R1_CPU_PYTHON" -B "$R1_REVIEW_ROOT/audit_supplement.py"
```

路径变量表示本轮指定环境与私有证据目录；复验使用新目录并保留原回执。私有索引 SHA-256 为 `cd9e52b0291d5ffa414216e8fe7fc53cc7a3d85f0b54336c3262fbadcf48ec55`，同时绑定两个独立测试脚本、补充脚本和各命令实际结果。

**未关闭数据问题**：Q1 r1 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 为 REQUEST_CHANGES；`Q1-G4-CORPUS-001 / P2` 涉及原第 10、13 项未明确版本值的 JSON 字符串类型。D1 定点修订、Q1 复核后由 S1 接纳新身份；沿用原问题，不新增重复失败计数。

S1 可接纳 CPU 实现；本结论不验收原语料或正式偏好质量。G4 真实候选、正式偏好和 DPO 仍 NOT_RUN，后续真实偏好池须另行实际完成 Q1 分层审核。本轮未改生产、数据、依赖或共享状态，未加载模型或使用 GPU，检查进程均已回收。
