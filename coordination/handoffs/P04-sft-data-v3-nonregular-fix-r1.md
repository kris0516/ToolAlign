# P04-sft-data-v3-nonregular-fix-r1 交接

**READY_FOR_REVIEW_CPU。** T1 完成原 `P04-SFT-DATA-V3-F1` 的限定 I/O 修订及自测，未签本修订的独立技术 PASS。任务 `P04-SFT-DATA-V3-NONREGULAR-FIX`，branch `codex/p04-sft-data-v3-nonregular-fix-r1`，base `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` / tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`；完整授权 `90ded89286d130b2e36dd7e18d334ed603ced9f6`。契约 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0026`。

实现 checkpoint `53d86109f18e4131cff1ddcb905086892580d136`，直接父为原 f3b7f1a1；最终仅补三份本包文档，完整 candidate/tree/parents 和原生远端回执在提交后发送，不在文件内伪造自引用 commit。生产模块 SHA `212c688c1a38e4c2ce7863e34efc7635d75878729e4e141333caeb08a6fd16a4`，测试 SHA `2706c6ab860a5fe5621a3d6d5fc62d902d662c407086476d87a6c44a22acc4a1`；配置 e27a7d4b 原字节保持。

五条改动路径为 `src/toolalign/training/sft/data_v3.py`、`tests/training/test_sft_data_v3.py`、两份 `reports/experiments/P04_SFT_DATA_V3_NONREGULAR_FIX` 报告及本交接单。原 report/handoff、其它生产/测试、CLI、依赖/构建/CI、S0 协调文件和原 PR16 候选分支保持；没有更改其它 worktree。

具体行为与完整自测见[报告](../../reports/experiments/P04_SFT_DATA_V3_NONREGULAR_FIX.md)（SHA `cd82bb8099a2a54f279ddede016048c7c1f4c5d6ba7c4b4c142ce39b3bd57aab`）及[JSON](../../reports/experiments/P04_SFT_DATA_V3_NONREGULAR_FIX.json)（SHA `fec0c946efd2cdfed47b2a8d92d63d7607b1a0d833bbde6847fa5cbbc4ef13c6`）。只新增打开前 `lstat` 普通文件要求与 `O_NONBLOCK`，继续同 FD 的 fstat、no-follow、hash/size/byte budget；相关模块 147 passed（原 135 + 新 12），Ruff PASS，两条原创替换竞态 child 均回收。

原 probe SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d` 不变。源码与新安装 target 各唯一一次执行，均 `rejected_before_writer=true`、`empty_writer_needed_to_release_open=false`、child exit 0/reaped，实际 child `_read` 的模块路径/hash 已独立记录。source proof `2e6664742bfe563be096e179b6d89ccaba53819939772d9a4286e072c3630b53`；installed `f5d56f829b042131e95980d40018d297ff816cd2f80ade3a9190d560ca3c629a`。外部 cwd 的隔离安装普通/hash-only/错误语义5次原创读取通过，proof `255ec54e03f02ead24f3bb12349b89acce53062d6b45b914268a80f2f4311515`。这些均为原创 I/O fixture，真实语料接口0。

唯一一组三归档及新 target 65 包文件一致，完整 METADATA/entry points/LICENSE/RECORD 核对通过；sdist `cabbc8a37151f767925d9f83fd05b9adab93c88798db11fb298135b84b55d3de`，直接/重建 wheel `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf`，包证明 `4531b68295b239c86c4614342a49391234a793eb96712c36787d3f9efd02faaa`。使用 `--no-deps` 只装新 wheel，复用现有默认 CPU 依赖，无新环境/依赖安装/下载；原两组旧归档与 target 保持。原 probe/归档/安装余额全部0。

完整接收/保全证明 `c44809b0140a5a21d54cc160fad8fc69562100dcf2953bda3b9fc4b7f3914588`：原618公开字节用f3 Git/新冻结快照保存；当前616不变，两个获准修改路径分别绑定新旧字节；10,933其它旧当前路径、370旧链接/target状态、5旧refs、root identity与609原输入保持。四个本轮FIFO保留节点及lstat类型/权限/device/inode，不读内容、不放入普通hash清单；替换竞态测试自身的非阻塞open与仅lstat的封存动作分开记录。

唯一新辅助失败是 recorder 缺新父目录而在 intake/probe 前退出1；精确开始UTC未记录，观察 `9f9a7bfa3656ff0528aecbaa7e530d645645258c12c3e3d8ad62678eb7160d60` 保留。补新父目录后独立r2 intake通过；本轮测试/probe/build/install无失败。原R1中间发现及旧所有失败保留，成文时原候选正式review SHA 尚未由S0追加，不自行登记正式失败轮次或关闭问题。

最终 seal 包含全部实际 argv/UTC/exit、源码快照、归档/安装、原 probe 输入/完整输出、普通/链接/特殊节点清单、完整 candidate/tree/parents 和普通推送/远端回执；完整路径/hash 只在本机原生交接。T1交付后结束，由S0派精确候选独立R1及最终CI/main。当前真实609消费、13例转换/导出/回读、新编码/框架/模型/GPU/优化/生成/业务API/浏览器/费用/上传均0；旧完整13例成功仅绑定bfdf2a2，当前真实trainer/容量/正式训练/评测/服务仍 **NOT_RUN**。
