# 11｜仓库启动记录与后续接手

## 当前状态

`kris0516/ToolAlign`已是公开仓库，后续代码和实验采用branch/PR/独立审查流程；本仓库**不再需要运行首次建仓脚本**。当前受检版本、运行和验收见[PROJECT_STATUS](../coordination/PROJECT_STATUS.md)。首次发布脚本保留在`scripts/publish_plan_repo.sh`，仅用于记录原规划包的发布设计，不应对当前仓库再次执行`--publish`。

## Supervisor 接手

1. 克隆或在 Codex 中打开 `https://github.com/kris0516/ToolAlign`。
2. 实际读取本机avoid-overkill技能，再读[AGENTS](../AGENTS.md)、[toolalign.md](../toolalign.md)和[当前状态](../coordination/PROJECT_STATUS.md)。
3. 用GitHub/Git读回当前`main`精确SHA，对照已验收提交、未提交改动与实际活动作业。
4. 从当前范围接续，不重做已完成P00–P03；旧任务包和原规划不自动授权新运行。
5. 如需新实现，按[协作协议](../coordination/PROTOCOL.md)使用**独立Codex对话**及隔离worktree，禁止sub-agent；已有实现与证据按当前状态复用。

## 远端验收要求

Supervisor 每次接手都应确认：仓库仍为 public、默认分支为 main、README 与核心文档可读、目标 commit 存在。不要用聊天中的旧 SHA 代替 read-back。

规划包的 `MANIFEST.sha256` 用于验证规划文件快照；后续功能开发进入正常 branch/PR/审查流程后，不把 manifest 当永久全仓文件清单。

## 历史首次发布脚本

`scripts/publish_plan_repo.sh` 原本用于“本地规划包 → 新建公开仓库”的一次性流程，包含账号、manifest、意外文件和非强制 push 检查。由于仓库现已存在，当前环境下再次运行 `--publish` 应被视为错误操作；仅可阅读或在独立副本中运行 `--dry-run` 做历史包验证。

## 失败恢复

若后续 push/PR 失败，保留远端和本地已有提交，核对 branch、base/head 与权限后使用正常非强制 Git/PR 流程恢复。不得删除仓库、强推 main 或重新创建同名仓库来“修复”。
