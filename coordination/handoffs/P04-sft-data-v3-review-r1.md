# P04-SFT-DATA-V3-R1 技术交接

- 独立 Codex-AI(R1)，gpt-6-astra/max；完整授权 `4ea69e1339c6b0efb14d0149b77b2442601ddd9c`，plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0026。
- 精确 candidate `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa`，tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`；base `48be4352bbad53ced5af84186edac036dd0ff2ca`、实现 `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`。
- **FAIL；P0=0、P1=0、P2=1。** F1：`data_v3._read` 在 `fstat` 前阻塞打开无 writer 的 FIFO；原创空 FIFO 与信号栈已复现，空 writer 释放后才拒绝，child 全部回收。最小证据已先交 S0。
- R1 验证：135 项既有 CPU 测试、27 项独立原创测试通过；F1 独立探针 exit=1，另计。一次离线 target 安装、一次固定 prepare 和一次完整 13 例 rebind/export/readback 成功，7,928 条 view 成员及双引擎完整数组逐项核对；ruff/契约通过，最终公开扫描见终态记录。
- 原运行：40 条 T1 命令、12 个源码时点、两个失败与两个成功的实际固定尝试、两组实际归档均核对；原 source 失败的终态 counter 保持缺失，没有补造。所有 T1/R1 原始失败保留。
- 保全：seal 核对 64,500 文件/1,628 链接/1 个 lstat-only FIFO，1,189 项历史公开 Git 绑定；旧 989 scope 和 571 公开 Git/快照保持。继承原 30 文件路径/1 链接缺失例外及等价留存内容，未恢复原路径。
- 证据 seal `cdd2a826a40066d2c570d83dfb862dc0e21b09392ef09fccb5e13bfc1ec006be`，20,426,676 bytes；公开 [报告](../../reports/review/P04-sft-data-v3-r1/REVIEW.md)与[索引](../../reports/review/P04-sft-data-v3-r1/EVIDENCE.json)。审查 commit 直接以 candidate 为 parent，精确提交、tree/parent、普通推送与终态封存由原生交接给出。
- 新增范围仅本 review 目录及本 handoff；被审文件和 S0 台账未改。实际消费与安装额度均已用完；新框架/模型/GPU/优化/生成/API/真实编码/构建/下载/依赖均 0，新制品含独占测试目录受 1 GiB 上限约束。实际 trainer、浏览器、baseline/SFT、正式评测与服务均未验收。
- S0 按正式规则登记 F1 并接续修订；本轮不修改台账、不复审新候选、不将正常固定消费成功写成原候选整包通过。
