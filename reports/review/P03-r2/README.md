# P03 修复候选独立复审 r2

日期：2026-09-06；R1；**PASS，剩余 P0=0 / P1=0 / P2=0**。本结论仅适用于精确候选 `3598cef2efb99e2990e384812a028902964cf494` 的授权 CPU 范围。原 F1/F2/F3 均关闭，未发现新的阻断项；原候选的 FAIL 和原始失败日志保留。

## 身份与范围

| 项目 | 精确记录 |
|---|---|
| task / branch | P03-R1-r2 / `review/p03-r2` |
| 被审完整候选 | `3598cef2efb99e2990e384812a028902964cf494` |
| 被审 tree | `c818ddfd06eb0bf09dd6e17e4a1365ba8888aa1e` |
| 本轮 S0 授权 | `cbb6d4614c3b8e8f584315ac3bdad434544c3984` |
| 生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 原候选 / 原审查 | `79a15d990fc27a9a33d033983c94eb92cccfb268` / `f34f7c5a4eac54b18a2b092495f4ce8eaa334f98` |
| F1/F2 实现 / checkpoint | `fde181d3319f36179298a4bec2a928a8354ee6b3` / `2195b2e4ea3219884c3a8c1eed26d413141daa65` |
| 保留原审查的 merge | `5fe4e905cf43af04e744d3801b19472bd839c67a`；父依次为上述 checkpoint、原 review |
| F3 实现 | `8d11225861214141de3da77c2b5eaf1752fc43b2` |
| 契约 | `toolalign.contracts.v1` / `toolalign.protocol.v1` / `coordination.v1` |

在 S0 确认前轮终态并原生授权后，从 3598 新建自己的复审分支；切换前已读取并私存授权版本的 AGENTS、P03 任务包、PROTOCOL、PROJECT_STATUS、GOAL。沿用原完整审查已读的 docs/01、04、12、13、冻结接口和配置，其候选字节未变。独立 App 任务，gpt-6-astra / max，无 sub-agent 或新任务。

完整复核三处生产修改、两个新增测试、checkpoint 和最终交接证据。相对 79a15d9 的 15 个差异路径中，8 个为 E1 授权修改/新增，7 个为原 R1 文件原样接入；3598 相对 8d11225 只新增最终交接与报告。原 146 个候选文件中 143 个未变，三处生产修改均逐段审阅；原全包审查继续提供未变范围的证据。本轮确认全部 **158 个被审文件**与 3598 的 Git blob 相同，仅新增本目录五份文件及 [本轮交接](../../../coordination/handoffs/P03-review-r2.md)。未改实现、原探针、公共契约/配置/锁、协调状态或其他 worktree。

## 三项关闭结论

| 原问题 | 独立复核及结论 |
|---|---|
| F1 / P1：停止通知 EIO 后结果消失 | **CLOSED**。[harness.py](../../../src/toolalign/evaluation/harness.py) 224–273 将一次收尾尝试、实际进程回收和失败记账分开。原正常/raw 解析失败两例均返回合法 HarnessResult，stop 写入由原两次变为一次，真实进程退出并关闭句柄。原 raw、13/9 已知合成 token 和原 parse failure 保留，失败仍在分母。新增同时 stop+目录 EIO 的 final、parse、响应 token 超限、后端崩溃、实际阻塞后 cancel/timeout 六例通过。 |
| F2 / P1：目录 EIO 后重复访问关闭句柄 | **CLOSED**。[isolation.py](../../../src/toolalign/tools/isolation.py) 109–133 分开维护进程句柄关闭与目录清理状态。原两例实际退出 0、句柄已关闭、目录仍存在，返回结果如实记录 `directory_cleaned=false`。新增直接 close 连续失败一/两次均保留同一个 OSError，没有 ValueError 覆盖，实际 Process.close 只执行一次；恢复本探针的 cleanup 后仅重试目录，后续 close 幂等。返回时的记录快照不会被探针重试改写为成功。 |
| F3 / P2：观察先于执行仍 success | **CLOSED**。[semantic.py](../../../src/toolalign/evaluation/oracles/semantic.py) 99–135 按顺序维护未完成调用，观察须匹配完整 call 和 result.call_id，再消费该调用。原倒序反例返回 unknown。新增真实双工具同轮执行、同工具有限重试两组，交换/重放观察、改变参数、跨轮旧 ID、漏执行及重叠执行 12 个损坏对照全部 unknown。合法多解与正常恢复在 finalized 前后均 success；错误答案仍 failure。没有给合法评分增加 finalized 先决条件。 |

关闭结论以原反例、新反例和源代码共同支撑。原 [R1 FAIL 报告](../P03/README.md) 的 49 passed / 5 failed 不改写；修复者 checkpoint 的 53 passed / 1 failed 也保持原始日志。

## 实际 CPU 与进程证据

| 本轮检查 | 实际结果与计数口径 |
|---|---|
| 原 R1 两个文件，逐字节未改 | **54 passed**，退出 0；含六类工具语义、策略、调用重验、预算、raw、解析/崩溃、四个真实阻塞 timeout/cancel、三个原问题 |
| 其余适用测试 | **335 passed**，退出 0；`tests` + P00 46 项 + P00-r2 72 项 |
| 不重复的 pytest 总数 | **389 = 原 309 + E1 新增 26 + 原 R1 54**，无 skip/xfail；不是 389 再加 54 |
| R1 新增脚本探针 | **31/31**：11 个清理/正常对照 + 两次真实执行产生 trace 上的 20 个评分检查；不是 31 次模型评测 |
| 安装包重复验证 | 同一 31 项 **31/31**；用于绑定安装结果，不再加进独立检查数 |
| lint / 冻结 | 全部通过，四个冻结文件不变 |

原四项阻塞探针在实际执行标记出现后才允许取消；timeout 同样观察到真实阻塞。模型忽略 SIGTERM 后以 SIGKILL（-9）回收，工具以 SIGTERM（-15）回收；在真实 Process.close 前观察 is_alive=false、非空 exitcode、该 Process 不在 active_children 中，同时另一个由探针持有的无关进程保持存活。

新增组合故障的第二次 generate 也真正进入阻塞并忽略 SIGTERM；回收后保留已完成首轮的 **31/17 合成 token、2 次模型决策、1 次工具轮次**，尚未完成响应的 token 记账明确不完整。正常/解析失败、257 输出 token 超限及退出 23 的后端崩溃分别保留其原始终止含义。检查 trace 的连续索引、唯一 task_outcome、raw/repaired 分离、实际回收及 `total=1, excluded=0`，未用终态字段代替活进程观察。

目录清理故障后的残留目录由探针恢复自己注入的失败后清理。这个安全清场不计为候选在故障时已成功清理；`reaped` 与 `directory_cleaned` 分别核验。没有扫描 PID 后批量杀进程。

## 历史来源与当前安装包

[证据核对脚本](audit_revision_evidence.py)只读核对原 17 份公开来源、63 份初版私有文件，以及 checkpoint 保全清单的 **741 条私有/归档路径**；其中 735 个普通文件、6 个 venv 解释器软链接。六个链接均解析到本轮同一受验证解释器，只核对字节，不执行 E1 环境。148 个 checkpoint 追踪文件绑定原提交，除新授权 semantic.py 外的 147 个与最终候选相同。

原 R1 七文件、22 份命令日志、9 份原反例观察、3 份私有结果和 15 条隔离子命令日志均保持 hash。初版/同步 demo 的 22 个已审制品只重核 hash；未无理由重跑旧共享 canary。修复阶段共核对 29 份主命令日志（checkpoint 13 + final 16）、33 条安装子命令日志（16 + 17）及六份实际归档。原 53/1、顺序探针初稿 8/8、初版修复 16/1 均保留，并核对工作树源码 hash 与后来提交的映射。

本轮证据核对脚本开发时有三次失败：先把 `{sha256, bytes}` 行当作 hash 字符串；随后沿用小文件读取器，拒绝了清单中的解释器软链接；再误把未追踪 `dist/` 归档当作 checkpoint Git 文件。三次失败的脚本版本、原日志和 hash 均保存。修正只涉及新增 R1 核对脚本；最终完整绑定通过。这些不是候选行为失败，也没有修改被审文件以通过检查。

R1 在自己的 worktree 实际构建新 sdist/default wheel，再由该 sdist 显式重建 wheel。默认构建原日志明确为 **wheel from source distribution**；本轮没有执行另一次源码直接 wheel 构建。

| 本轮归档 | 字节数 | 文件成员 / 当前 Git 字节 | SHA256 |
|---|---:|---|---|
| sdist | 116137 | 52 = 51 tracked + 1 metadata | `622ed5b412d5275656880d364256ba255d868851aba86ab88e0e8effda87187c` |
| default wheel | 37495 | 29 = 24 源码/资源 + 5 metadata | `c6f0a491bb92c516f5ba13ffc1ec00a40529935a46309f1df1ad4659d760faa1` |
| 显式 sdist 重建 wheel | 37495 | 同上，字节完全相同 | `c6f0a491bb92c516f5ba13ffc1ec00a40529935a46309f1df1ad4659d760faa1` |

三份新归档逐成员与当前 Git blob 相同，未知、遗漏、符号链接或逃逸载荷均为 0，且与 E1 最终归档字节相同。[安装验证脚本](verify_revision_package.py)在新默认 CPU venv、非项目根 cwd、清除 PYTHONPATH/PYTHONHOME 并使用 `python -I`，实际完成 **16 条子命令**，包括 hash 锁依赖安装、pip check、冻结 digest、五类 fixture、CLI/registry、scripted demo、11 个 P03 模块的安装来源/字节和新增修复探针。

安装后 scripted demo **10/10**，90 条 trace、20 个自有进程记录；同一公开 fixture 的调用、观察、前缀 hash、策略和预算另经 R1 读取器重建。其 220/140 token 是脚本预算值，不能解释成模型吞吐或正式质量。旧演示、新安装演示及修复者的演示是重复实现检查，不是额外独立任务样本。

## 命令与日志

下表由本轮实际命令索引生成；完整 argv、时间、退出码、精确 HEAD/tree、日志及制品 hash 见 [evidence.json](evidence.json)。原始日志和进程身份保存在私有审查目录。三个核对脚本开发失败单独标明，其余验证均退出 0。

<!-- COMMAND_TABLE_START -->

| 检查 | 实际命令 | 退出码 | 日志 SHA256 |
|---|---|---:|---|
| original-r1-54 | `uv run --locked pytest -q reports/review/P03/test_p03_lifecycle.py reports/review/P03/test_p03_semantics.py --basetemp=.toolalign-local/review-p03-r2/original-r1-54` | 0 | `7aa02d11d99fb5482ca4294eb793da9b845ff1c1478e4cd2bb36cdbd691b5a09` |
| applicable-cpu-335 | `uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py --basetemp=.toolalign-local/review-p03-r2/applicable-cpu` | 0 | `8277c6646ca23d53a9b0602bfa75a7ec4742d24ce74c3bf81ac744da705135f4` |
| revision-edges | `uv run --locked python reports/review/P03-r2/revision_probe.py --output .toolalign-local/review-p03-r2/revision-edges` | 0 | `7f7c9f2693a654e03dd2cea2e2a551b6605f73f3d9e8083d61c0113c110e3f9e` |
| historical-binding（R1 核对脚本开发失败） | `uv run --locked python reports/review/P03-r2/audit_revision_evidence.py --e1-root <E1_WORKTREE> --output .toolalign-local/review-p03-r2/historical-binding.json` | 1 | `90ef827fcd2f444fd2ebc8d251afd88e5e4af0eb447de4a6ef1d516de85a1fae` |
| build-current | `uv build --out-dir .toolalign-local/review-p03-r2/build` | 0 | `4e1eb09f152333e4e8548009ad2835f9fbedf900c641ebbb0b3cffce71c46a05` |
| rebuild-from-sdist | `uv build --wheel --out-dir .toolalign-local/review-p03-r2/rebuilt .toolalign-local/review-p03-r2/build/toolalign-0.0.1.tar.gz` | 0 | `da774a8da0d835dad50454078e64f1b7a2437cd9303cc086b56748dc6c779e39` |
| historical-binding-final（R1 核对脚本开发失败） | `uv run --locked python reports/review/P03-r2/audit_revision_evidence.py --e1-root <E1_WORKTREE> --output .toolalign-local/review-p03-r2/historical-binding.json` | 1 | `75dba0232eb7d9b7eb020ba6beaade18615d6e7ec2b281d593340e7d2def4f01` |
| historical-binding-verified（R1 核对脚本开发失败） | `uv run --locked python reports/review/P03-r2/audit_revision_evidence.py --e1-root <E1_WORKTREE> --output .toolalign-local/review-p03-r2/historical-binding.json` | 1 | `30fdc9a077d36dd515212cfb9a789d5d4884c7f281ffa5a30816615a999b3c19` |
| historical-binding-complete | `uv run --locked python reports/review/P03-r2/audit_revision_evidence.py --e1-root <E1_WORKTREE> --output .toolalign-local/review-p03-r2/historical-binding.json` | 0 | `a8049213c4ca6cdc45331d8e0f752104410abaeaea0e81d36fa629c07ea57dc4` |
| installed-current-package | `uv run --locked python reports/review/P03-r2/verify_revision_package.py` | 0 | `b4cc4526e6ed00c5517ebb0076b29c28a0962f103a1b71f67e93c353426e4ad4` |
| contract-freeze | `uv run --locked python scripts/check_contract_freeze.py` | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| lint | `uv run --locked ruff check .` | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| environment-resources | `.venv/bin/python .toolalign-local/review-p03-r2/environment_check.py` | 0 | `6603df309ec6876bbe97fd2809b55c03656a1827fac93bfaa02c05b72a93f782` |
| public-content | `uv run --locked python scripts/check_public_content.py` | 0 | `412f4d55583602d36ae2c83d19d9a4124e41ba79063273eb572b45a5a5433f28` |
| review-scope | `.venv/bin/python .toolalign-local/review-p03-r2/verify_scope.py` | 0 | `1819d4d449ed7b00395e7c01d4a124462b5a75c67b0f8f2a4b4aaf2cf3b01a06` |

<!-- COMMAND_TABLE_END -->

## 资源、边界与交接

本机独立实测 Python **3.14.7 / arm64 / macOS 26.5.1**，复用的默认开发环境 12 个发行包全部匹配冻结锁；隔离安装只有项目及五个默认运行依赖。未导入 ML/模型/tokenizer。磁盘快照：本轮私有环境/制品 **11,923,456 字节**，复用核心环境 **36,245,504 字节**；合计约 45.9 MiB，低于新增 2 GiB 预算，非模型内存或性能测量。

NOT_RUN：独立 Python 3.11、真实 MLX/Qwen/模型或 tokenizer、权重下载、GPU、P04/P06/BFCL/最终隐藏集、真实吞吐/模型质量/长期稳定性、已加载 MLX 对象的 spawn 兼容、生产输出格式变更、S0 合并及主干组合验证、推理服务部署。父进程轻量可序列化后端的构造前提没有被 scripted 成功消除。

无费用、业务写入、模型/数据公开上传或公网推理。R1 只提交独立复审文件，由 S0 处理后续集成与阶段门；本轮交接后结束，等待新的精确授权。
