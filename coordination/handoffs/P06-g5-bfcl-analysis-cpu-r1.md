# E1 → S1 / R1：P06 G5 BFCL 与分析 CPU r1

基于 `e580eb663b5658e611ce30a1bf7d1232ccba3917`；候选分支 `codex/e1-p06-g5-bfcl-analysis-r1`。精确交付提交随最终回报给出，完整文件身份在私有 evidence-index.json。详见[实现及证据报告](../../reports/P06_G5_BFCL_ANALYSIS_CPU_R1.md)。

**实际 BFCL 筛选为 0/150：simple_python、multiple、irrelevance 各 0/50。** 150 题均缺少冻结契约要求的对象闭合声明，28 题另有既有分组重叠。保留所有 ID、原因与 111 个连通 component；P02 仅读 policy-a 分组 metadata。长度全部为不适用、token 数 null，没有官方答案读取、inputs.json 或空执行计划。selection SHA256：`4014d0c8d3ca46dc2def17f32b38cc1bbb3b67f0889f0fd48820fa7e93b24b69`。

可交付接口：

- `python -m toolalign.evaluation.bfcl fetch/select/answers/score`：固定上游提交、无损 schema/name 映射、答前冻结、真实官方 scorer 和严格门控；外部工具不执行。
- `python -m toolalign.evaluation.analysis --inputs ... --run-root ... [--bfcl-scores ...] --output ... [--plot]`：完整分母、L1/L2 配对效应、真实 group 的 bootstrap/LOOG、A1/A2、失败索引、成本与 JSON/CSV/图表。
- 专用 CPU 环境用 `requirements/bfcl-scorer-py312.lock.txt`；默认项目和共享训练锁不变。19 项原创案例实际调用固定官方评分函数，socket 连接尝试为 0；原 import 缺 soundfile 的失败记录保留。
- 原创 T1→官方 scorer→分析 CLI：6 行计划保留 1 行未启动，5 个 child 全部回收；4 个 fixture 失败全部入索引。真实模型结果均为 NOT_RUN。

私有根 `.toolalign-local/p06-g5-bfcl-analysis-r1/`：`selection/` 为真实答前筛选；`commands/` 为命令回执；`original-demo/` 及其 `analysis-release/` 明确为原创 CPU 验算，不能用于模型效果。evidence-index.json 包含环境、精确提交、文件 hash、全部失败历史及审核入口，不应公开原始问题、答案或本机路径。

新增32项CPU测试全部通过；默认全库为1,396 passed/4 failed/78 skipped，4项失败来自本次错误设置pytest临时根，改用默认临时根后4项原测试全部通过。原日志保留，不改写为一次全绿。另有46项P00独立检查通过；全库Ruff、冻结契约、公开内容和离线分发检查均PASS。

R1 重点复核零题排除是否遵守无损语义、严格门控是否独立于 backend 声明、T1 缺失/中断结果是否保留分母，以及不等大小 group 的整组重采样。Q1 可审阅来源/分组/零题解释；当前 L2 应记为 NO_ELIGIBLE_INPUTS，不消耗 L2 GPU 推理额度。共享 BOARD/PROJECT_STATUS/DECISIONS 留给 S1 维护。
