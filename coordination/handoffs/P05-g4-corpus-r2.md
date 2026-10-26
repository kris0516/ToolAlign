# P05-g4-corpus-r2 — D1 交接

状态：READY_FOR_REVIEW。起点 `6adfd14167288ce2e3c2e542b2b7ac196251d11c`，分支 `codex/d1-p05-g4-corpus-r2`。本轮公开改动仅本单及[修订报告](../../reports/P05_G4_CORPUS_R2.md)，精确交接提交见最终回复和私有证据索引。

针对 Q1 审阅 `fd0e8f34f3e7bf80d70914e5177d84cc8386a50e` 的 `Q1-G4-CORPUS-001`，原数组第 10、13 项已明确要求版本答案为 JSON 字符串，并同步约束证据。原答案、调用策略、工具/oracle/生产逻辑均未改；原 r1 全部材料及 REQUEST_CHANGES 保留，原 20 项审阅分母不变。

- 新包仍为 20 train / 12 family / 10 类 / 1 group，P02 隔离 0。其余 18 条完整 authoring 和全部 20 条答案/策略不变。
- 两项 task ID/source hash 改变；原第 10、13 项移至新第 5、11 项，共 9 个数组位置改变。全组 20 项 group 引用改变，完整 mapping 和原始差异留私有。经身份映射后分组拓扑、P02 绑定及 P03 共享 schema 审计一致。
- 新运行四条 CPU scripted 轨迹：字符串答案 2 success，数字答案 2 failure，当前决策 legal/illegal 与显式类型要求一致，自有进程全部回收。私有修订验证脚本 exit 0；原 52 条轨迹未重跑。
- 新 tasks 文件 SHA256：`b9c6f18995579d8af1a58d137cafe9cc1c9f2f40279d9434aa85e2c7769eb015`；规范 task list hash：`4c9e7edaef35352a294aa8d62130847264645059dd5ce529fb528f926c339bd8`。其它输入/manifest/mapping hash 见报告，精确位置及原始证据由私有索引提供。

交 S1/Q1 对新第 5、11 项作定点复审，原 18 项结论按身份 mapping 复用。现有 R1 代码审查继续；本交接不自签独立 PASS，也不登记该问题已关闭。未生成真实候选或正式偏好，未运行 DPO、tokenizer、GPU，未新增安装或修改 E1/共享状态。
