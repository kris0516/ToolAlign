# P00｜仓库启动与契约冻结

规划状态：P00 为 READY，其余待依赖通过。尚未分发或领取。

| 字段 | 初始值 |
|---|---|
| owner 角色 | S0 |
| 依赖 | 无；先确认本地/远端真实状态 |
| base commit | UNASSIGNED — S0 分发前填实际完整 SHA |
| branch/worktree | UNASSIGNED — 每包独立，不共用 checkout |
| 契约 | toolalign.*.v1，P00 冻结后填写精确版本 |
| 交接 | `coordination/handoffs/P00-r1.md` |

## 目标

创建或验证用户授权的新公开仓库；建立可安装最小 Python 项目、shared contracts、测试入口、资源锁接口、目录与分支规则。

## 允许修改范围

公共 contracts、pyproject/依赖分组、最小 fixtures、coordination 文件。

除此之外文件默认只读；公共契约、依赖锁和main合并权归S0。路径尚未创建时，先核对P00结构，不能各自发明一套。

## 非目标

不训练正式模型，不自动创建付费资源，不在未冻结接口时并行展开全部模块。

## 验收

新仓库 URL/public/commit 读回；contracts 正反样例；CPU 测试可在无 MLX 环境启动；锁位置跨 worktree 一致；公开内容扫描。

S0/worker在实际实现前把上述验收转换成可运行命令与预期，完成后附命令/退出码/日志。当前没有声称这些测试已执行。

## 资源

任何模型加载/训练/大批生成都先申请全局GPU锁。默认零外部付费；具体token/内存/时间预算使用P01实测。不要把其他worktree的空闲误认为GPU空闲。

## 阻塞处理

现有同名仓库、错误 GitHub 身份、无写权限时停止远端写入，保留本地状态；不要重建或覆盖。

## 交接要求

使用../templates/HANDOFF.md；附关键输入输出、个人应理解的技术点、真实commit、未完成项和独立审查请求。自测通过不自动变成MERGED/VERIFIED。
