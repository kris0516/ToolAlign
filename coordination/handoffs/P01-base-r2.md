# P01-base-r2｜T1 共享基线同步交接

2026-09-06。T1 / P01，独立App任务，`gpt-6-astra / max`；分支 `work/p01-compatibility`。本轮CPU自测交付，待P01独立R1/S0验收，不把已验收共享包当作P01或P04放行。

## 精确基线与保留关系

- 旧完整候选：`f97bb0de346c220871962a5689014a379fe19c83`；旧[P01-r1](P01-r1.md)保留原字节。
- S0新生产code_base：`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；本轮authorization_commit：`f2a271be616cdb53c01e8d671029f31ae140c037`。
- 在原任务分支非强制merge该授权提交，merge SHA：`17a003f2678682fd3c6a072eba2b105fafc87102`；无冲突、无reset/rebase、旧SHA仍为祖先。
- 本轮仅CPU审计脚本提交：`e6825f657a359a812b44b8db96d7929efd9f77ff`；新增报告/本单在其后提交。**最终完整候选SHA由T1原生交接消息明确给出**，R1应审核含本单的新完整候选，而不是单独审merge提交。
- 已读新授权的AGENTS/GOAL/PROTOCOL、任务包第二基线段、STATUS及S0-SHARED-02 main验证/环境说明；契约仍为plan-v0.1、coordination.v1、toolalign.contracts.v1。

T1新改动限 `reports/hardware/P01_BASE_R2_*` 与本单；公共pyproject/lock/config/Protocol/看板只通过S0 merge取得，没有本地擅改。报告路径经S0确认沿用原`reports/hardware/`。真实task ID/绝对cwd仅保存在私有映射，给S0消息省略model/thinking；未创建其他任务或sub-agent。

## 证据入口与结果

- [本轮报告](../../reports/hardware/P01_BASE_R2_REPORT.md)：范围、命令口径、依赖差异、CPU数学和NOT_RUN。
- [命令证据](../../reports/hardware/P01_BASE_R2_VALIDATION.json)：命令/UTC/退出码/完整log SHA-256。
- [元数据/包/字节审计](../../reports/hardware/P01_BASE_R2_METADATA.json)：实际runtime/dev-only版本、候选源码hash、21个旧文件不变、真实归档逐项核对。

适用CPU回归 **217通过**：58基础+41 P01+46 P00首轮+72 P00-r2。日志SHA `dba7a71c4670da709d3b2b2368eee4d475ff205e4a440b12177694c459f8872f`。旧274包含的57个shared01结构快照绑定“一个extra”旧候选；未修改旧断言、未将其计作当前通过。lint/冻结/公开扫描通过。

公共归档回归排除241私有canary并保留18公开对照；原R1-r3补充45私有/21公开边界通过。这些范围有重叠，不相加成覆盖率。新公共修复合入后才运行正常`uv build`，真实sdist和由它构建的wheel成功；隔离安装/无ML后端导入/五类契约CLI通过。

实际sdist 110,865bytes，SHA `f74cd964bec2af10f673ac5104a88b9162a7cd27fb4a5e6398a9be621424c508`；47文件中46项与追踪文件字节相同，另PKG-INFO。wheel 44,037bytes，SHA `043e5d4508704d5637f7a9fef20dcb236c5223649def73b832750fa94dabd69b`；27文件中22项追踪源码/资源相同，另5项dist-info。两包未跟踪payload均0。与S0基础包大小不同是P01实现进入包，非私有文件进入包。没有归档发布/上传。

## 环境与 GPU 路径是否改变

**P01实现/GPU路径字节未变**：8个实现、2个测试、10个旧硬件证据文件与旧handoff共21项逐文件对照f97bb0d完全一致。旧10次运行manifest制品hash重新核对，重建汇总与P01_RESULTS字节相同，SHA `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`；所有旧失败、配置、32-token生成、0.6/1.7实测口径保留。

新私有锁环境：compatibility+dpo为69个distributions（64 runtime+4 dev-only+项目）；加p01-replay为90（85 runtime+4 dev-only+项目）。完整replay包含旧88包全部同版本，增加ruff0.15.0和toolalign0.0.1。dev-only为iniconfig2.3.0、pluggy1.6.0、pytest9.0.2、ruff0.15.0；前三项原探索环境已有。dpo子集少21个replay依赖，已有runtime版本同实测；不存在隐瞒升级。对shared01公共compatibility的真实fsspec变化2026.7.0→2025.3.0保留，对T1实际模型环境没有runtime版本变化。三个候选库11个记录源码文件hash相同。锁93记录不等于实际默认安装93包。

原独立metadata审查脚本在本worktree新环境原样通过，日志SHA `2e30405043c6f316242eb27cde1c641390e766878d8cf01fd418c7d500222745`；完整各包与closed graph见JSON。许可差异沿用公共说明：mlx-lm-lora metadata MIT但wheel LICENSE Apache-2.0，不重标许可。

仅PyTorch CPU小张量参考在新replay环境运行，禁止MLX/模型库导入；调用原有Torch参考函数并对照独立stdlib loss/解析梯度，误差均<2e-6、初始ln2误差1.9047e-9、reference无梯度。日志SHA `596d33ee397ff90ee0a32090fb127c1627e411a7904184df0d9105187582ad3a`。这不是重新执行历史完整MLX/Torch数学检查。

## 失败、NOT_RUN 与下一步

本轮适用检查未出现失败；历史首选DPO失败、备选r2假PASS降级、r3参考score失败和1536首轮pressure停止均保留，不能用本轮CPU同步覆盖。旧sdist失败证据也保留，新公共修复与实际新归档分开登记。

本轮不导入MLX、不加载模型、不申请GPU租约、不重跑104可测微步或其他GPU实验；完整math replay、P03集成推理、256token/30秒完整harness、正式P04/P05、最终测试/BFCL、服务部署均NOT_RUN。已有最多32token小生成没有扩大为完整harness结论。R1/S0对P01正式验收、kris人工语义确认仍待处理。

原始日志在本worktree私有 `.toolalign-local/checks/base-r2-*`；新venv/旧wheel保留/汇总在 `.toolalign-local/base-r2/`；历史run仍在 `.toolalign-local/runs/*/`。R1可只读按run_id和公开hash核对，不修改旧原始证据。新脚本在reports内，不进入模型路径。

T1提交/非强制push最终候选并给S0精确SHA后停止，等待S0分配独立R1；不自行合并main、修改正式状态或创建其他任务。
