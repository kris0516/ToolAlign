# 决策记录

仅 S0 更新。每项后续变更应包含日期、基线 commit、备选、理由、影响、验证与回滚，不覆盖历史决定。

## ADR-0001｜Mac 原生优先

状态：规划已采纳。主训练为 MLX；PyTorch CPU 提供独立数学参考。CUDA 是未来可选，不默认产生云费用。

## ADR-0002｜独立对话，不使用子代理

状态：用户明确要求。S0 与 worker/reviewer 使用独立对话和独立 worktree。缺原生线程管理时由用户转交分发词，不用 sub-agent 替代。

## ADR-0003｜先有效实验，再复杂部署

状态：规划已采纳。SFT/DPO/数据隔离/oracle 是核心。首版不默认公网、复杂前端、多租户、GRPO 或投机解码。

## ADR-0004｜DPO 技术门

状态：规划已采纳，backend 尚未锁定。社区实现仅是候选；SFT reference、mask、数值、保存加载和适配兼容验收后才能正式使用。

## ADR-0005｜结果与许可诚实

状态：规划已采纳。负结果允许；无实测不填数字。原创内容 MIT，模型/数据/第三方代码分别核对许可，不复制私有毕设源码。

## ADR-0006｜GitHub 规划基线已远端发布

状态：已完成。用户创建公开仓库 `kris0516/ToolAlign` 后，规划内容通过 GitHub 连接写入 `planning/bootstrap-v0.1` 并进行提交级核对。首次建仓脚本保留为历史交付工具，不再用于当前仓库。

## ADR-0007｜S0 领取与持久独立对话协作

日期：2026-09-06；基线 `0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f`；状态：已执行。

本地 Codex 项目已 clone；S0 建立 P00–P09 长期 goal 和本对话每 30 分钟跟进。已发现原生独立对话 create/send/read/wait 能力，后续只通过这些真实能力派发，返回 ID 保存本机私有映射；不使用 sub-agent。遵从用户选择，所有 worker/reviewer 固定 gpt-6-astra / xhigh。备选为手动分发文本，仅在原生能力不可用时采用。

影响：最多两个活跃实现对话，R1 纯 CPU 审查独立；P00 冻结合并验证前不发 P01–P03。验证：本机 Git clone/push dry-run、GitHub 权限/public read-back、长期 goal/自动跟进工具返回成功。回退：停用跟进不删除提交或未合并 worktree，按 handoff 手动继续。

## ADR-0008｜CPU 契约、离线 schema 子集与冻结摘要

日期：2026-09-06；基线同 ADR-0007；状态：P00 候选，待 R1 和 main 集成。

选择 Python 3.11–3.14 + jsonschema Draft 2020-12，五类严格 wire record、六个独立 Protocol，额外检查字段关联。备选 Pydantic 或手写完整 validator 未采用；保持数据/接口可用 JSON 跨 backend 使用，并避免基础包导入 MLX/PyTorch。依赖用 uv.lock 固定。schema、validator、interfaces、protocol config 以 contracts.v1.lock.json 记录精确字节。

工具参数只允许闭合且有界的有限子集，拒绝 refs/正则/远程引用；支持范围外的来源记录隔离计数，后续如需扩展由 S0 通过 ADR 与新证据调整。GPU 使用 Git common dir 的 flock，锁文件不删除，元数据留私有目录。这保证同仓库 worktree 协作互斥，不声称阻止其他仓库或不合作进程使用 GPU。

验证：P00 正反样例、CPU 无 MLX 安装、跨进程/跨 worktree 竞争与异常退出、wheel 独立安装、公开扫描；具体退出码/日志由 handoff 记录。回退：S0 以非强制 revert 修复并重新冻结版本，不让已分发任务自行降级。

## ADR-0009｜偏好抽检阈值与运行预算候选

日期：2026-09-06；基线同 ADR-0007；状态：在采样/实验前预注册，随 P00 审查。

数据规范原有最少抽样规则保留；有效对抽检误标率严格大于 5% 时阻断正式 DPO，unknown 计入误标。选择 5% 是项目质量门的工程判断，非实测结论；更严格阈值会增加小样本返工，更宽松阈值会引入更多偏好噪声。实际误标率与原始分母都保留，不能看过结果后提高阈值。

首版最多 3 次模型决策、2 次工具轮次；256 输出 token / 30 秒仅是 P01 校准前的配置候选，未用于性能承诺。影响 P02/P05 抽检和 P03/P07 预算接口。验证/回退：配置与文档一致；如 P01 不可行，S0 预先登记新配置和理由再运行，保留原规则记录。
