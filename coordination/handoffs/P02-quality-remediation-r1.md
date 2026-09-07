# P02-QUALITY-REMEDIATION r1 — D1 handoff

状态：READY_FOR_REVIEW；本轮 CPU 候选交付，不代表 R1 PASS、G-DATA 或 P04 验收。

- code_base：`86b80bada50ac7c8f4b3910e3831a397ed65a853`。
- authorization：`2aa0cf4a756e78d32cf10130edbe6d0e3925bf3a`。
- branch：`work/p02-quality-remediation`；保留旧训练绑定分支和全部旧制品。
- model / thinking：gpt-6-astra / max；沿用原独立 Codex 任务，没有子代理。
- 契约：plan-v0.1 / coordination.v1 / toolalign.contracts.v1。
- production/test payload：`1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e`；最终文档/交接 commit 的完整 SHA 和普通推送核验由原生 S0 消息及私有完成封存给出，避免提交内容自引用。

交付两个限域数据模块、76 项原创测试、逐字复制的授权质量配置、3 个证据核验脚本及本交接。[报告](../../reports/data/quality-remediation-r1/README.md)给出实际分母、构建、token 材料、失败项和限制；[公开证据](../../reports/data/quality-remediation-r1/evidence.v1.json)绑定原始日志和源字节快照。其他基线生产/测试/配置、协调状态及 ADR 未修改。

实际两次构建相同：32 个来源 / 40 条决策暂挂，train 7,475，validation 234；formal 5,980 / 217、smoke 1,593 / 197。原 Example 字节、group、split 保持，其他来源同 group 的 5,586 条记录保留。选择只过滤原集合，保留原 rank，无回填。两份直接重标和一份依赖历史候选保留新 ID / annotation parent / 上游身份，全部 staging；变更调用之后的旧观察与条件未重新验证。

新有效代表例 10 个、原创协议例 3 个、staging 3 个，共 16 个不同案例，两 CPU 引擎各测一次，完整记录相等，审阅判定空白。其中一份直接候选 3,069 tokens 超出既有上下文上限，仍未晋升。浏览器实显、实际 trainer、真实模型和外部工具重执行均 NOT_RUN。

验证：1,160 passed / 2 个 HF-only skipped；110 个 subtests 另列不累加。12 次固定入口输入替换均拒绝且无成功目录；两次实际构建稳定；sdist/default wheel/实际 sdist 重建 wheel及 4 条默认安装命令通过；Ruff/冻结/公开扫描通过。原三条失败命令和一次未启动 Ruff 的记录器目录竞争均保留，修正后的对应验证已通过。

私有交接包含九参数输入映射、两次修订目录、两引擎全部 JSON/HTML/CSV、原始命令和退出码、源快照、归档安装材料、最终原输入不变及字节预算核对、完成 seal。原委托 AI 两份 CSV 与旧个人审查占位材料未覆盖，不代签 kris 或 AI，不请求重填。S0 精确授权以外的后续审阅未接入。

请 R1 对原生交接的精确候选 SHA 独立检查来源家族隔离、旧 rank 和分母绑定、输入替换拒绝、候选身份和旧观察状态、有效选择与 staging 分离及材料完整性。E1 扩展审计、S0 main 验证、G-DATA 质量验收和 P04 授权仍待后续处理。D1 本轮交接后空闲，不合并 main，不启动模型/训练。
