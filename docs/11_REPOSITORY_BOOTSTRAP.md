# 11｜仓库启动记录与后续接手

## 当前状态

`kris0516/ToolAlign` 已由用户创建为公开仓库。当前会话已通过 GitHub 写入规划基线；因此本仓库**不再需要运行首次建仓脚本**。首次发布脚本保留在 `scripts/publish_plan_repo.sh`，仅用于记录原规划包的安全发布设计，不应对当前仓库再次执行 `--publish`。

## Supervisor 接手

1. 克隆或在 Codex 中打开 `https://github.com/kris0516/ToolAlign`。
2. 读取 `AGENTS.md`、`SUPERVISOR_START_HERE.md`、`docs/00_MASTER_PLAN.md`、`coordination/PROTOCOL.md`。
3. 用 GitHub/Git 读回当前 `main` 的精确 SHA，并登记为 P00 的 base commit。
4. 领取 P00，冻结 contracts、最小项目结构、测试入口与共享 GPU 锁实现。
5. P00 合并后再按依赖分发 P01/P02/P03 到**独立 Codex 对话**；禁止 sub-agent。

## 远端验收要求

Supervisor 每次接手都应确认：仓库仍为 public、默认分支为 main、README 与核心文档可读、目标 commit 存在。不要用聊天中的旧 SHA 代替 read-back。

规划包的 `MANIFEST.sha256` 用于验证规划文件快照；后续功能开发进入正常 branch/PR/审查流程后，不把 manifest 当永久全仓文件清单。

## 历史首次发布脚本

`scripts/publish_plan_repo.sh` 原本用于“本地规划包 → 新建公开仓库”的一次性流程，包含账号、manifest、意外文件和非强制 push 检查。由于仓库现已存在，当前环境下再次运行 `--publish` 应被视为错误操作；仅可阅读或在独立副本中运行 `--dry-run` 做历史包验证。

## 失败恢复

若后续 push/PR 失败，保留远端和本地已有提交，核对 branch、base/head 与权限后使用正常非强制 Git/PR 流程恢复。不得删除仓库、强推 main 或重新创建同名仓库来“修复”。
