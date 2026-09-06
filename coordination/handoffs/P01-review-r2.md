# P01 — Independent review R1-r2

**FAIL；P0=0、P1=1、P2=0**。原 F2、F3 关闭；F1 的运行期错误路径通过，初始化生命周期仍有阻断残留 R2-F1。日期：2026-09-06。review 分支 `review/p01-r2`；精确独立 review commit 在提交后通过原生消息交给 S0。

| 身份 | 精确 SHA |
|---|---|
| 完整 candidate | `ac8095faa58a98e143a8dc4d63042093e426feb0` |
| authorization_commit | `fd67511ef4cb7853bb75b0b106ec4692a9d36be8` |
| production base | `37c00de9abe92e6fb24a0c0e0b7361aa4bb90385` |
| 已测修复 / 接入原审查 merge | `5c32e8a72e957df100691e0096d1413eed8ce8f9` / `f020046055717f4fc5a821a61fb2664d989e6875` |
| 原 candidate / 原 FAIL | `59b3802c81aa6eceaf3609af88f288756bcb1581` / `ac6bdf78d57c6753865a24a1d216b90dc4478646` |

已读授权 AGENTS/P01/PROTOCOL/STATUS/GOAL、原审查和 fix-r3 交付，契约 `plan-v0.1` / `coordination.v1` / `toolalign.contracts.v1`。完整复核相对 ac6 的 11 文件、1548 新增/24 删除行；最后 ac8095f 只增四份证据文件。当前 170 份 tracked 文件逐字节未改，只新增 `reports/review/P01-r2/` 五份文件及本交接，原八份 R1 文件和所有旧审查分支保留。

**R2-F1/P1，阻断：** `src/toolalign/training/compatibility/execution.py:317–318` 先写 running manifest，330 行初始 swap 读取、337–349 行 Popen 仍在 350 行保护 try 之前。R1 原创 prepared-config CPU 反例证明：初始 swap EIO 时 Popen 调用0次；Popen EAGAIN 时调用1次；两例实际创建 child 都是0。原异常传播，run 仍 running/ended_at=null/exit_code=null，无 resources，当前报告生成器的 summary runs=0。没有已执行微步、真实 child 退出或进程泄漏可声称。

最小修复：将已登记尝试的资源初始化和进程创建纳入终态收尾，保留原异常、failed/ended_at 及可被汇总的资源记录，明确未启动 child 和不可用测量；仅回收实际持有的 Process。不新增“磁盘全面不可写仍保证写出证据”的要求。initial_swap 由 R1 独立发现；S0 请求相邻 Popen 复现后，R1独立补测并确认。

原 F1 两个运行期反例已通过，新增 pressure TimeoutExpired、swap/RSS错误、真正 child wait timeout 对照均通过，保留真实 child -9/0、合成进度29 token/2更新和独立进程存活。F2 原回调通过，16组独立连续回调保留全部已完成微步/更新/token/loss，NaN/±Inf 与辅助指标按标准 JSON 保存真实类别；2e-6、mask/reference/数学/累积逻辑未改，固定上游 update→eval→callback 顺序核验。F3 全8份历史source hash绑定47c03404bab043e85b417cd8a6d0432dc2f85479，原aaab HEAD与raw未改写。

实际检查：原七项未修改 R1 **7 passed**；完整适用回归加三个报告测试 **238 passed**，共245个不同现有pytest检查。新增22项 **20 passed / 2 failed**，两失败均为 R2-F1，无xfail；17组独立 PyTorch CPU 数学通过。最终新增探针原日志 SHA-256：`7429dceb1bfc3d88635365d1db543e4160d2bdc8cf5f5e1c7358c7f30681f805`。全部 argv、退出码、时间、原始日志hash、失败分类和复现方法见[完整报告](../../reports/review/P01-r2/README.md)及[evidence.json](../../reports/review/P01-r2/evidence.json)。

独立重核10次旧run/185项manifest制品、27条旧日志、14条修复日志及相关proof/结果；当前报告生成器重建摘要与原 P01_RESULTS 完全一致。原始失败和此前审计保留，历史模型受限结论没有写成本轮GPU通过。新sdist及三个wheel逐成员绑定当前Git bytes，默认CPU隔离安装13条命令、8模块hash/schema/现有接口通过，0未知载荷。最终lint、冻结、公开扫描与staged范围检查通过。

G1-SFT/G1-DPO仍受R2-F1阻断；本轮没有新增算法失败，F2/F3关闭也不代表正式训练或人审完成。仅CPU/Python3.14.7，复用34项已锁CPU环境；记录时本轮约5MiB，连同复用环境及旧cache约1.31GiB，低于2GiB。NOT_RUN：MLX/模型/tokenizer、GPU/权重、P04/P05/accepted_sft、完整真后端256-token、kris人审、BFCL/最终测试、本机3.11/3.12/3.13、长期模型性能、付费/上传/部署。PyTorch仅17组小张量CPU数学实测。

R1提交后交回S0并结束本轮转空闲，等待正式修订授权；不修候选、不修改协调看板/共享契约、不自行合并。
