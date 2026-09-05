# 11｜创建新公开仓库与推送计划

## 当前边界

本交付会话已通过 GitHub 连接确认账户 `kris0516`，但当前可用操作仅提供读取，未提供新建仓库/提交文件；本机执行环境也未配置 GitHub CLI 登录。**因此没有实际创建 `kris0516/ToolAlign`。**

用户已经要求建立新开源项目。本手册让具有用户本机权限的 Supervisor 完成这一步，不再要求用户手工逐份上传文档。不要把这个计划中的目标地址当成已存在的链接。

## 首次启动

把文档包解压到一个独立目录 `ToolAlign/`，不要放入 LiDARFoodAgent 或其他现有 Git 仓库内部。在 Codex 中打开这个文件夹，以 `SUPERVISOR_START_HERE.md` 的启动提示词开始独立 Supervisor 对话。

Supervisor 首先执行：

```bash
bash scripts/publish_plan_repo.sh --dry-run
```

该命令检查发布 manifest、文件 hash 和意外多余文件，不联网、不新建仓库、不提交。初次发布前不要先修改规划文件，否则 hash 检查会拒绝，防止把非预期内容公开。

在用户本机已装好 Git、Python 3、GitHub CLI，并已用 `gh auth login` 登录 `kris0516`、配置真实 Git 作者身份后执行：

```bash
bash scripts/publish_plan_repo.sh --publish
```

这是**显式公开发布动作**。脚本只创建指定的新公开仓库，不改已有仓库可见性，不覆盖远端，不上传模型/数据，不使用 force push，不修改全局 Git 配置。GitHub CLI 创建仓库方式见 [S18](09_SOURCES.md)。

## 脚本安全行为

脚本验证账号、待发布文件和干净初始目录；本地有 `.git` 或目录位于其他仓库内会停止。新建仓库使用 `gh repo create --public`；同名仓库存在则由 GitHub 拒绝，而不是复用或覆盖。

推送后读回 `private=false` 与 `main` commit SHA，必须与本地一致才能输出成功；生成忽略的本机 receipt。真实成功后 S0 更新 `coordination/PROJECT_STATUS.md`，记录初始提交和领取信息并提交新的状态 commit。

此脚本只用于首次导入。后续代码与文档更新按普通 branch/PR/审查流程，不反复运行它。`MANIFEST.sha256` 是本次规划交付快照，不是未来所有代码版本的永久文件清单。

## 失败时如何处理

- 缺少 `gh`/Git/Python：在本机安装所缺工具；不要求用户向聊天粘贴 token。
- 登录账号不是 `kris0516`：停止；不要替用户创建到另一个账号。
- 同名仓库已存在：先确认它是不是本次此前创建的一部分；没有确认不得修改。
- 仓库创建成功但 push 失败：保留本地 commit 和远端，不自动删除。S0 核对新建仓库 URL、是否空仓库、origin 和本地 SHA，再按正常非强制 push 恢复；已存在其他提交时先检查，不能强推。
- hash 不匹配或多余文件：检查为什么变化，恢复初始包或独立审查新增内容。不要用关闭校验绕过隐私/许可检查。

## GitHub 创建完成后的验收

使用 GitHub read-back 验证仓库确实公开、默认/工作分支为 main、README 能读取、核心文档路径存在、提交与本地一致。不要把“CLI 打印了 URL”当作完整内容验证。

随后才进入 P00 的项目实现工作。独立子对话尚未创建，创建与分发必须有真实记录；禁止把模板当实际任务领取。
