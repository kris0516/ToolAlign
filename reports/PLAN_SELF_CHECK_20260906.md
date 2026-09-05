# plan-v0.1 交付自检

日期：2026-09-06。检查对象：当前 Markdown 规划包及首次公开发布辅助脚本。

这是编写方自检，**不是 R1 独立实现验收**；所有模型训练/服务验收仍为 NOT_RUN。

## 实际执行的本地检查

| 检查 | 结果 | 范围 |
|---|---|---|
| Shell 语法 | PASS | `bash -n scripts/publish_plan_repo.sh` |
| Manifest/dry-run | PASS | 完整文件 hash 验证，不执行网络写入 |
| dry-run 无 Git 初始化 | PASS | 未创建 `.git` |
| 篡改 README 被拒绝 | PASS | 临时副本，hash mismatch |
| 篡改后无 Git 初始化 | PASS | 临时副本 |
| 意外额外文件被拒绝 | PASS | 临时 private-notes 测试文件 |
| 额外文件后无 Git 初始化 | PASS | 临时副本 |
| 错误账号被拒绝 | PASS | mock GitHub CLI，未调用写入动作 |
| 错误账号后无 Git 初始化 | PASS | 临时副本 |
| 已存在本地 Git 仓库被拒绝 | PASS | 临时 `.git` 目录 |
| Markdown 相对链接 | PASS | 所有当前相对文件链接存在 |
| 任务包数量/结构 | PASS | P00–P09 共 10 包 |
| 独立对话分发模板 | PASS | S0/D1/T1/E1/I1/R1 共 6 类 |
| 无模型/原始数据大制品 | PASS | 文件类型/清单检查 |
| 有限凭据模式扫描 | PASS | 未匹配常见 GitHub/AWS/Google/private-key 值；不宣称完整安全审计 |

## 内容自检

确认十天核心与长期扩展分开；DPO reference、模板、mask、数据隔离与语义 oracle 有验收；真实BFCL与本地任务指标不混用；Mac实测前不填训练时间/峰值；独立对话不替换成sub-agent；worktree与GPU锁不同；开源代码与公网服务不同。

## 未完成与未运行

GitHub 仓库由用户创建后，本次会话已通过 GitHub 写入规划基线并完成提交级文件核对。首次发布脚本的 `--publish` 路径仍未在本机 CLI 环境执行，也不需要对现有仓库再次执行；远端状态以 GitHub read-back 为准。

Mac MLX 兼容测试、SFT/DPO、数据下载、BFCL、推理服务、GPU互斥实现、独立Codex对话分发：**均未开始**。文档中的路径/接口/验收是下一阶段任务，不是现成功能。

## 交付内容

44 份 Markdown，MIT LICENSE、Git 忽略/文本配置、首次发布脚本和规划快照校验清单。不含用户私有项目源码、模型权重、健康资料或凭据。
