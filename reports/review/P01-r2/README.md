# P01 / R1-r2 修复候选独立复审

结论：**FAIL；P0=0、P1=1、P2=0**。原 F2、F3 已关闭；原 F1 的运行期异常已修复，初始化阶段仍有一个阻断问题。日期：2026-09-06。完整命令与证据见 [evidence.json](evidence.json)，交接见 [P01-review-r2.md](../../../coordination/handoffs/P01-review-r2.md)。

| 身份 | 精确提交 |
|---|---|
| 被审完整候选 | `ac8095faa58a98e143a8dc4d63042093e426feb0` |
| R1-r2 authorization_commit | `fd67511ef4cb7853bb75b0b106ec4692a9d36be8` |
| 共享生产 base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 已测修复实现 | `5c32e8a72e957df100691e0096d1413eed8ce8f9` |
| 接入原审查的 merge | `f020046055717f4fc5a821a61fb2664d989e6875` |
| T1 修复授权 | `a0a800b2a544cb25e7eccad2dce12173acc77ea1` |
| 原候选 / 原 FAIL | `59b3802c81aa6eceaf3609af88f288756bcb1581` / `ac6bdf78d57c6753865a24a1d216b90dc4478646` |
| 本轮分支 | `review/p01-r2`，直接从完整候选建立 |

已读取精确授权提交的 AGENTS、P01 任务包、PROTOCOL、PROJECT_STATUS/GOAL，及 P01-fix-r3、FIX_R3_REPORT/VALIDATION/SOURCES 与完整差异；沿用并逐字节确认不变的 docs/03、05、12、RESOURCE_LOCK 和冻结 lock。契约仍为 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`。相对原 R1 的本轮候选差异是 11 文件、1548 新增/24 删除行；相对原候选另包含八份原 R1 文件。最后的 `ac8095f` 只新增四份证据/包脚本/交接文件，八个生产模块均绑定 `5c32e8a`。

## 原问题的关闭情况

| 原问题 | 本轮证据 | 决定 |
|---|---|---|
| F1/P1，监控异常遗漏终态 | 原两个反例通过；新增运行期 pressure timeout、swap/RSS 读取异常均保留原异常、已知用量、实际 child 退出及失败汇总；普通 child wait timeout 正常继续。初始化 swap 与 Popen 失败仍遗漏终态。 | **部分修复，保留 R2-F1/P1** |
| F2/P1，ln(2) 失败漏记已执行工作 | 原回调对照通过；新增 16 组连续回调覆盖累积边界内外、有限门槛、NaN/±Inf、非有限辅助指标。每个已执行微步、实际 optimizer step、监督/处理 token、loss 与失败分类均先保存。 | **CLOSED** |
| F3/P2，历史工作树误称记录 HEAD | 原 math-r2 配置、八份实际源码 hash、记录 HEAD 的两个差异及后续可恢复提交逐项核验；公开说明已纠正，历史 raw 保留。 | **CLOSED** |

G1-SFT 与 G1-DPO 的本轮工程验收仍因 R2-F1 为 FAIL。历史受限 SFT 和唯一备选 DPO 的功能证据继续保留；这不是新增的算法或模型训练失败。首选 mlx-tune DPO 的历史失败保持原判，不能由本轮 CPU 记账修复改成通过。

## R2-F1 / P1：已登记的尝试在初始化失败后仍永久 running

位置：[execution.py](../../../src/toolalign/training/compatibility/execution.py) 的 317–318、330、337–350 行。`run.json` 已写入 `running`，随后初始 swap 读取和 `Popen` 都在保护 `try` 之前。任一步抛异常，运行期新增的错误终结逻辑不会执行；[P01_BUILD_REPORT.py](../../../reports/hardware/P01_BUILD_REPORT.py) 的 23–24 行又跳过没有 `resources.json` 的目录。

R1 对合法的原创 prepared-config fixture 注入两个有界 CPU 故障，候选生产代码保持不变：

| 触发 | Popen 调用次数 | 实际创建 child | 实际终态与汇总 |
|---|---:|---:|---|
| 初始 `psutil.swap_memory()` 抛 EIO | 0 | 0 | 原异常传播；run 为 running，ended_at/exit_code 都为 null；无 resources；summary 的 runs 为 0 |
| `Popen` 本身抛 EAGAIN | 1 | 0 | 同上；没有创建 child，也没有任何已执行训练微步 |

两例都验证捕获对象就是原异常。第一次检查由 R1 独立发现；S0 随后要求补测同一初始化范围内的 Popen 路径，R1 自写探针复现。最终两例仍是普通失败断言，没有 xfail。问题不是进程泄漏，也没有可报告的真实 child 退出码；遗漏的是已经登记的失败尝试及终态证据。该路径在修复前也存在，本轮没有把它描述成修复引入的新回归。

最小修复方向：从已登记尝试开始统一覆盖资源初始化和进程创建的异常收尾；只有确实创建了 Process 才进行回收。保存 failed/ended_at、原始错误和可被汇总的 resources，并明确表示 child 未启动、测量尚不可用。不能把缺测写成健康读数或虚构 child 退出码。本要求不扩大到磁盘全面不可写时仍保证写出证据。

## 本轮独立验证

首先运行了原封不动的七项 R1 反例/对照，**7 passed**；八份原 R1 文件与原提交 hash 全部一致。随后运行完整适用回归及三个 worker 报告测试，**238 passed**：core 58 + P01 59 + P00 review 46 + P00-r2 review 72 + 报告 3。两组共 **245 个不同的现有 pytest 检查通过**，不计入旧 shared01 的 57 项快照调查。

本轮新增 **22 项：20 passed / 2 failed**。四项运行期监控/正常对照与 16 项连续回调检查通过；两个初始化反例失败。早期 20/1、单独两项失败及最终 20/2 的日志分别保留，计数不重复相加。

监控探针启动真实原创 CPU child，写明 PID/PPID 和已知 progress；在实际 child wait 超时后，再触发压力读取 `TimeoutExpired`、第二次 swap 读取错误或第二次 RSS `AccessDenied`。三例均保留同一个原异常、真实 RSS 样本、29 个合成监督 token/2 个合成更新、有效 failed manifest、制品 hash 与 `FAILED_MONITOR` 汇总。child 忽略 SIGTERM，实测经 SIGKILL 退出 -9，`waitpid` 证明已回收；另外持有的独立睡眠进程仍存活。正常对照经历真正的 wait 超时后退出 0，未发送终止信号。这里只缩短测试内等待宽限期，不启动模型，也不修改生产预算。

回调检查逐字提取当前 Callback，只提供 CPU closure；没有导入 MLX。连续喂入两组不同长度的原创 pair，独立累计每步 7/9 个处理 token 和 5/7 个监督 token，验证每条旧记录保留、微步数累加和第八步实际更新入账。有限 loss 在 ln(2)±1e-6 内通过、偏差 3e-6 在首周期失败；第九步的有限不同 loss 不再套初始门槛。NaN/±Inf 保留为数值 null 与准确的 `nan`/`inf`/`-inf` 类别，非有限辅助指标也记录失败；严格 JSON 解码通过。

11 份原上游源码重新计算 hash 后均不变。固定 `dpo_trainer.py` 的 357 行实际 `optimizer.update(model, grad)`、614 行求值、665 行 callback 的调用顺序再次核对；当前 fallback 在 Callback 以外的源码逐字节未变。core/numerical/model_probe/samples、mask/reference、累积除法、冻结接口及 **2e-6** 门槛均未改变。上述回调是 CPU 单元与固定上游源码证据，GPU 故障注入仍为 NOT_RUN。

原 R1 独立 PyTorch CPU 数学脚本本轮重新运行 **17 组通过**，最大误差分别为 CE loss `4.011570280404442e-7`、CE 梯度 `1.905478064223587e-8`、DPO loss `8.22313996895474e-8`、DPO 梯度 `3.629568690738383e-9`，均小于 2e-6。只使用 float32 小张量和两个 CPU 线程；未执行 MLX 数学入口。

## 历史绑定与新包

`audit_p01_r2_evidence.py` 独立核验 159 份未变原文件、八份原 R1 文件、27 条旧命令日志、13 条修复公开日志及一条 release 扫描日志、七份 proof 文件、两份私有结果及七份失败观察文件。原 R1 私有审计结果的 hash 绑定原已提交 evidence；10 次历史 run 的公开证据 hash 和全部 **185 项 manifest 制品**重新读取核验。未变的 token/mask、参数字节及数学解释沿用此前 R1 审计；没有重新导入 tokenizer、模型或重跑长校准。

math-r2 原记录 HEAD 仍是 `aaab75ed5d993f9354f11f74b58edb67d0af45c3`，source hash 仍是 `17479619a5ef1fb0e2d9747211a67a7d1d71acfd266b48ee1514b267ceca6241`。全部八份源码匹配 `47c03404bab043e85b417cd8a6d0432dc2f85479`，其中 model_probe/numerical 两份与记录 HEAD 不同。当前报告已正确说明工作树与 HEAD 的区别，未将旧 run 改写为当前修复代码实测。

R1 又从自己的候选运行当前报告生成器，只读历史目录，写入自己的私有目录；结果与旧 P01_RESULTS 逐字节一致，SHA-256 `d0fb9deb067b1e3f6f8b85855a0d1509b3bc15569065bbfed22a5c95928f42bd`。原首选 BF16 失败、smoke06-r2 raw PASS 的后续降级、smoke06-r3 失败和 1536-r1 pressure 停止均保持原样。

实际构建本轮 sdist、默认 wheel、从该 sdist 重建的 wheel 和直接 wheel。检查完整成员集合、路径/链接、当前 Git blob 字节、八个模块及冻结 schema，未追踪载荷均为零；没有套用原候选的旧包 hash。

| 本轮归档 | 大小与完整成员 | SHA-256 |
|---|---|---|
| sdist | 114450 字节；48 文件，47 tracked + 1 metadata | `024126435a5065ddae8e12c86272cc530ed4a8ae09eddd1fa2b0b0916d6ccf2e` |
| 默认 / 重建 / 直接 wheel | 均 44605 字节；27 文件，22 tracked + 5 metadata | `941a1efb88b48cb8479ec9b5869c4db90984fd266e209933ef128b0792fa34e1` |

新建默认 CPU 环境，实际执行 **13 条子命令**：锁定依赖导出、带 hash 安装、重建 wheel 安装、pip check、八模块 hash/来源检查、现有小接口、P01 CLI help、schema digest 和五种 fixture CLI。从源码目录之外以 `python -I` 运行，清除 PYTHONPATH/PYTHONHOME；全部模块来自安装 prefix，六个 runtime distributions，不含 Torch/MLX/模型/tokenizer 包。每条实际 argv、cwd、起止时间、原始 stdout/stderr 及 hash 均保留。T1 的旧临时安装单独 stdout/stderr 已未保留，本轮只核验其生产者元数据，未假装重算这些缺失流；本轮自己的新安装提供独立证据。

资源记录：macOS 26.5.1 arm64、Python 3.14.7；基础环境 12 项、复用 CPU 环境 34 项版本均匹配原 lock。记录时本轮私有目录分配 5246976 字节（约 5 MiB）；连同复用环境和旧 cache 的保守合计为 1401593856 字节，低于 2 GiB。本数是磁盘分配快照，不是模型内存或运行峰值。

## 重现与日志

在精确候选加本审查文件的独立 worktree 中运行下列命令。`<CPU_PYTHON>` 表示已锁且含 psutil/pytest 的 CPU 环境 Python；本轮复用原 R1 私有环境，没有新装模型依赖。

```bash
PYTHONPATH=src <CPU_PYTHON> -m pytest -q reports/review/P01/test_p01_processes.py reports/review/P01/test_p01_failure_counters.py
uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py reports/hardware/P01_FIX_R3_REPORT_TESTS.py
PYTHONPATH=src <CPU_PYTHON> -m pytest -q reports/review/P01-r2/test_p01_r2_regressions.py
PYTHONPATH=src <CPU_PYTHON> reports/review/P01/check_p01_cpu_math.py
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
```

第三条在本候选上的预期实测为退出 1、20 passed / 2 failed；只看初始化反例可添加 `-k initialization_failure`。默认 pytest 不自动发现本目录。历史审计需要保留的 T1 私有证据与原 R1 私有审计结果；完整真实参数在 evidence 中，缺失制品不能当作通过。

以下为本轮原始 stdout+stderr 的 SHA-256。原始日志仅存 `.toolalign-local/review-p01-r2/logs/`，真实任务 ID、本机路径与进程身份均留私有目录；公开 argv 使用 `<R1_WORKTREE>` / `<T1_WORKTREE>` 占位符。首个七项检查的旧 wrapper 只记录 argv/时间/退出/hash，其候选身份由此前工作树检查及只读范围绑定；后续 wrapper 同时记录 HEAD/tree。

<!-- COMMAND_TABLE_BEGIN -->

| 检查 ID | 退出码 | 完整日志 SHA-256 |
|---|---:|---|
| original-seven-unchanged | 0 | `42e694012b7e27bb5c20c10b875ab87f9e2ff07c01903380ab24bab29de80308` |
| cpu-regression | 0 | `86f3e7adf34ca42380715d96d37e7f4bbe777a7cc7d7df092a117dcf1c7724af` |
| adjacent-failure-probes | 1 | `c45ad08bcb2708e3eee9fe83a7639b9bd76daec663a32d40abecde6f80872040` |
| independent-cpu-math | 0 | `17307b5921a3e9089effd2d824e287b872ce23ea8e2a0b0fe6522f3cea8cc26e` |
| initialization-adjacent-probes | 1 | `08a23fdf0d33a57d7ae05934cb4ad1cd08b51d3d2237fdc447f18fe2ac9630c7` |
| preserved-evidence-and-source-mapping | 1 | `aa7802e7e1a7e7c5704018a8e2c349620c50ff368c283f208e6a4b0786947d16` |
| current-package-build | 0 | `135920dc9011a3d9ec9b1e1312041099fa254db63560fe183f951b58b91868fc` |
| wheel-from-current-sdist | 0 | `5c8cdf6b737d532bcd7445349c2e95f0bc0c69d090e52dd70c5d36c505e8cd25` |
| direct-wheel | 0 | `a4d4b15463d8f7214dd741d6e9c884a88525d3308341afe05b6cc009f07a7f44` |
| isolated-current-package | 0 | `e91ebcc329a293c0d7d9105683e66a53ca1829372e3f4b3dc048a520976daf96` |
| preserved-evidence-corrected | 0 | `4e69ca8dbe397d942322bf3e8f45aee47af881d79b317fe01da66ad1924cb945` |
| final-lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| contract-freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| current-historical-summary | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| final-independent-probes | 1 | `7429dceb1bfc3d88635365d1db543e4160d2bdc8cf5f5e1c7358c7f30681f805` |
| environment-and-summary-binding | 0 | `0ccd3865a97d1eb08490a1c9d7a33816af88d5601740c3de906f61854dcb0932` |
| public-content | 0 | `6572dda14a1d50532e50d374e714cbe0de3f0bca704c5217ae6c84c91070537a` |
| final-scope | 0 | `7ce3d1ecf264662d402483ceb3a3b29c5bf0300696e606d1b7fa0d947f1ba746` |

<!-- COMMAND_TABLE_END -->

历史审计第一次因 R1 源码匹配字符串误用了 `grad_accum` 而失败；实际固定上游变量为 `grad`，文件 hash 本身一致。仅修正新增审计器后通过，原日志与原审计器副本保留；该失败不计为候选问题。最终 lint、冻结、公开扫描与提交范围检查通过；只新增本目录五份文件及新交接，170 份候选 tracked 文件和此前全部审查分支保持不变。

NOT_RUN：MLX/模型/tokenizer 导入、权重下载、GPU重放或故障注入；本机 Python 3.11/3.12/3.13；P04/P05 正式训练及 accepted_sft reference、完整真后端/256-token 协议、kris token/mask 人审与 P02 语义抽查、BFCL/最终测试、长时模型性能、费用、上传或服务部署。旧共享归档 canary 和未变依赖调查未重复运行。已知 PyTorch 小张量 CPU 数学实测单列于上文。本轮交回后等待 S0 修订授权，不自行修改实现或合并。
