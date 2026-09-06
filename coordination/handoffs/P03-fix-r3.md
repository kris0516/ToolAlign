# P03-fix-r3 — 最终修复交接

日期：2026-09-06；owner E1；状态：**READY_FOR_REVIEW，自测通过，等待 S0 安排新精确候选独立 R1 复审**。不自行签验收或合并 main。完整命令/退出码/log hash、开发失败与归档证据见 [最终自测报告](../../reports/harness/P03_FIX_R3_VERIFICATION.md)。

## 版本与原 SHA 保留

| 项目 | 记录 |
|---|---|
| branch | `work/p03-execution-harness` |
| 当前工作契约 | `toolalign.contracts.v1` / `toolalign.protocol.v1` / `coordination.v1`；冻结文件未修改 |
| 原候选 | `79a15d990fc27a9a33d033983c94eb92cccfb268`，原始 `85e0905fc82da4504d73bf7eb489c1f1a0d227a7` 仍保留 |
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 修复授权 | `243821a988a12a6ff9f20b5fbb5ba1ae374d63c9`；最终授权 `fd67511ef4cb7853bb75b0b106ec4692a9d36be8` |
| F1/F2 实现与 checkpoint | `fde181d3319f36179298a4bec2a928a8354ee6b3` / `2195b2e4ea3219884c3a8c1eed26d413141daa65` |
| 原独立 R1 审查 | `f34f7c5a4eac54b18a2b092495f4ce8eaa334f98`，父严格为 `79a15d9`；原结论 FAIL，P1=2/P2=1 |
| 普通 merge | `5fe4e905cf43af04e744d3801b19472bd839c67a`，父依次为 `2195b2e4ea3219884c3a8c1eed26d413141daa65`、`f34f7c5a4eac54b18a2b092495f4ce8eaa334f98` |
| 最终生产代码及测试 | `8d11225861214141de3da77c2b5eaf1752fc43b2`，tree `90fc20c5d3d3c3e847e2b4b5fc6b8750ee588461` |

完整 candidate 为包含本交接与最终报告的文档提交；其精确 SHA、tree、非强制推送和远端读回在原生交接中提供给 S0。文档提交相对 `8d11225` 仅新增这两份文档，不修改已测试源码/测试或打包输入。未 reset/rebase/cherry-pick 原 R1 SHA，未 merge 无关 P01/P02/main 状态。

## 问题对应

| ID | E1 当前修复及证据 |
|---|---|
| F1/P1 | stop 信号失败仍执行一次自有进程 close，并返回含 cleanup 失败事实的合法 HarnessResult/trace；raw、原 parse failure、已知 13/9 token 与失败分母保留。原 R1 两例通过，真实回收退出 -15，无抛出 OSError。 |
| F2/P1 | 句柄关闭与目录 cleanup 分阶段记录；目录失败后重试不访问关闭句柄。`reaped`/exitcode 不替代 `directory_cleaned`，目录未清理如实返回 false。原 R1 两例通过，真实退出 0，目录最后由探针清场；未冒充候选目录 cleanup 成功。 |
| F3/P2 | 按顺序维护 pending call；观察必须属于已有未完成调用，并核对完整 call 的 canonical hash 和 result.call_id。不可靠顺序/绑定给 unknown；多解、多步/恢复/无工具及 terminal 追加前评分保持，真正失败和未完成执行仍 failure。原 R1 倒序反例变为 unknown。 |

这些是 E1 修复与复跑结果，**不改写原 R1 FAIL，也不等同新 R1 PASS**。原 R1 的七个文件逐字节不变。首次接入后复跑全部原 54 项为 53 passed/1 failed（F3），日志 `6805b15d2cd01a1a1fbad4c669bda07062a6e75e59cd2fc08aa53a4be00d4614`；本次最终 54 项已包含在全部通过的完整回归内。

## 实际验证与失败记录

- 精确 `8d11225` 完整 CPU：**389 passed，无 skip/xfail**，由原适用 309 + E1 新增 26 + 原 R1 54 组成；日志 `5acb2ab177e0e0da54846b9ec70d08fcf6fbafcbc3fae8db4a64e6c8b2af01fa`。包含真实阻塞、SIGTERM 无效升级 SIGKILL、无关进程保持存活、parse/后端崩溃、预算和原 R1 全部探针。
- lint、四个冻结文件、实现提交 156 路径公开扫描均通过；最终文档公开扫描和干净工作树状态随原生交接提供。所有源代码及测试检查绑定实现 SHA，未因仅新增文档无理由重复运行。
- 新 sdist **116137 字节**，SHA256 `622ed5b412d5275656880d364256ba255d868851aba86ab88e0e8effda87187c`；52 文件，51 tracked + 1 metadata。默认及显式 sdist 重建 wheel 均 **37495 字节**，SHA256 `c6f0a491bb92c516f5ba13ffc1ec00a40529935a46309f1df1ad4659d760faa1`；29 文件，24 源码/资源 + 5 metadata。三份归档逐成员匹配当前 Git 字节，未知/遗漏/路径逃逸均 0。
- 新 CPU 隔离安装 **17 条子命令退出 0**，日志 `c2b838e5f0efc2748306c2d992b2a573ef2c824f7e88e98d7f0a9f5e2c432947`；`python -I` 来源位于新 venv，三个修改模块字节一致。scripted demo 10/10；四项实际阻塞与四项收尾故障检查通过；相同 demo 的 20 次 terminal 前后 oracle 检查 success、8 种不可靠 trace unknown。
- 原 F1/F2 修改前的 4 failed/3 passed 与 checkpoint 全部证据保留。本次 E1 顺序探针初版 8 failed/8 passed 含 1 个测试准备错误：观察 call/result ID 单条不一致；初版修复后 16 passed/1 failed。只修正这条测试使观察内两个 ID 同步变化、与原执行不同；最终 16 项新检查及原 F3 为 17 passed。原稿、失败源码版本和日志保留，未改 R1 测试或冻结校验绕过问题。

## 允许文件与保留证据

相对原 `79a15d9`，本轮 E1 自己只修改/新增以下八个允许文件：

- `src/toolalign/evaluation/harness.py`
- `src/toolalign/tools/isolation.py`
- `src/toolalign/evaluation/oracles/semantic.py`
- `tests/evaluation/harness/test_finish_cleanup.py`
- `tests/evaluation/harness/test_oracle_order.py`
- `reports/harness/P03_FIX_R3_CHECKPOINT.md`
- `reports/harness/P03_FIX_R3_VERIFICATION.md`
- `coordination/handoffs/P03-fix-r3.md`

另七个文件仅通过原 R1 SHA 原样 merge 接入，未由 E1 编辑：

- `coordination/handoffs/P03-review-r1.md`
- `reports/review/P03/README.md`
- `reports/review/P03/audit_p03_evidence.py`
- `reports/review/P03/evidence.json`
- `reports/review/P03/test_p03_lifecycle.py`
- `reports/review/P03/test_p03_semantics.py`
- `reports/review/P03/verify_p03_package.py`

原 148 个 checkpoint tracked 文件中仅新授权 semantic.py 变化，其余 147 个相同；全部 741 个既有私有/归档文件（包含原 400 个）与原 R1 七文件保持 hash 相同。旧 P03-r1/P03-base-r2、checkpoint 报告、before 日志及旧包均未覆盖。旧源码仍由原候选和审查 commit 保留。新私有 final 子目录与完整运行 manifest 的绝对路径仅给 S0，不写入公开仓库。

## 资源、NOT_RUN 与后续

仅 CPU，独立原任务/worktree，gpt-6-astra/max。本修复轮私有目录累计快照 15480 KiB（其中 final 11388 KiB，不重复相加）；复用 `.venv` 35068 KiB，低于累计新增 2 GiB。没有运行中的自有测试/模型进程。

NOT_RUN：新精确候选 R1 独立复审、S0 合并/main 验证；ML/模型/tokenizer 导入、权重/GPU/P04/P06/BFCL/最终隐藏集、真实吞吐/质量/长期稳定性、已加载 MLX 对象的 spawn 兼容、训练输出格式改造及服务部署。无业务写入、费用、模型/数据上传、公网推理或共享配置/依赖改动。

按授权非强制推送本原分支并读回精确远端 SHA 后，E1 结束本轮，等待 S0 安排 R1 对新完整 candidate 独立复审；不自行推进 main 或正式模型实验。
