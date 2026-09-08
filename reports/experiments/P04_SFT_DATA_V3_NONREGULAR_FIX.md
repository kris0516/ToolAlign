# P04 v3 非普通输入阻塞修订

**READY_FOR_REVIEW_CPU。** `data_v3._read` 已在打开前拒绝非普通路径，并以 `O_NONBLOCK` 覆盖预检查后被替换成 FIFO 的窗口；原同 FD 的类型、大小、预算与 hash 检查保留。相关模块 **147 passed**，其中 12 项为新增原创 I/O 检查；原 R1 probe 保持原字节，源码与默认安装版各唯一一次执行均在没有 writer 的情况下拒绝 FIFO，子进程正常回收。本结果为 T1 自测，尚无该修订的独立 R1 结论。[结构化结果](P04_SFT_DATA_V3_NONREGULAR_FIX.json) SHA `fec0c946efd2cdfed47b2a8d92d63d7607b1a0d833bbde6847fa5cbbc4ef13c6`。

任务 `P04-SFT-DATA-V3-NONREGULAR-FIX`，branch `codex/p04-sft-data-v3-nonregular-fix-r1`；base `f3b7f1a1abb23cce3bdccb74ddc6d2e0477bb2aa` / tree `1cd40f093c17da1c5a1f1399117c29eb3c1d9547`，完整授权 `90ded89286d130b2e36dd7e18d334ed603ced9f6`。base 是原待审候选，并非已通过 R1 的生产版本。契约 `plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0026` 保持。实现与实测归档固定在 `53d86109f18e4131cff1ddcb905086892580d136`，之后只新增本报告、JSON 与交接单。

**原发现与最小修订。** 原 `f3b7f1a1` 先阻塞 `open(O_RDONLY | O_NOFOLLOW)`，再 `fstat`。R1 原空 FIFO 无 writer 时栈停在 open；外层即时拒绝断言 exit 1，空 writer 释放后 child 才返回 `v3_regular_file_budget` 并 exit 0/reaped。原 probe SHA `f44cc02cc066ad9f2befe1b11c27c92981ff77ae87cf83672c422e3118ff1c7d`，结果 SHA `fa03a9689cbda1117aac63766dc55eaea49184a6473101f2322291a727bf7744`，S0 原接收证明 `cf6826fa347277151d01886acb97ad8b25bab5dc5bf88ddfe0ef92e5c66c1603`。

本任务接收的是中间 `P04-SFT-DATA-V3-F1 / P2` 发现；成文时尚未收到 S0 追加的原整包正式 review SHA，不自行增加正式失败次数或关闭正式问题。13 份精确授权与 7 份原反例副本已保存，输入 manifest `cd401df1e59e791db5ef0bb9e13989ca23a664d2fa7b84ce32372d80dd2a190c`；没有重跑旧失败或递归读取 R1 其它工作区。

新入口在原 `try` 内先以 `lstat` 要求普通文件，随后使用 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 打开。同 FD 的 `fstat` 再确认真实对象，随后才进入原大小/hash/byte-budget 读取循环。即使预检查后被换成 FIFO，也会非阻塞取得 FD 并在读取内容前拒绝。已有 symlink 拒绝、正常二进制/空文件、hash-only 返回值及普通文件的大小/hash/预算错误代码均已检查。没有延长原 probe 超时，也未修改其它 I/O 模块、配置、CLI、依赖或原报告。

生产模块 SHA `212c688c1a38e4c2ce7863e34efc7635d75878729e4e141333caeb08a6fd16a4`；测试 SHA `2706c6ab860a5fe5621a3d6d5fc62d902d662c407086476d87a6c44a22acc4a1`；S0 精确配置保持 `e27a7d4bcdd378944af56559833c3bcd10f601b689a75f1daec96b884bd780c1`。

| 已执行验证 | 实际结果 |
|---|---|
| 相关模块，新独占公开 pytest 根 | 147 passed，0 failed；包含原 135 与新 12 项，不叠加为 282 |
| 新普通/特殊路径反例 | FIFO、目录、symlink 在打开前拒绝；空/二进制普通文件、hash-only 及大小/hash/预算负例通过 |
| 原创替换竞态 | 在预检查后、真实 open 前将普通路径换成 FIFO 或 symlink；两条 child 均及时拒绝、exit 0/reaped，无超时；FIFO 没有 writer |
| 源码原 R1 probe | `rejected_before_writer=true`、`empty_writer_needed_to_release_open=false`、child exit 0/reaped；proof `2e6664742bfe563be096e179b6d89ccaba53819939772d9a4286e072c3630b53` |
| 安装原 R1 probe | 同样三项通过，实际 child `_read` 来自新 target；proof `f5d56f829b042131e95980d40018d297ff816cd2f80ade3a9190d560ca3c629a` |
| 安装版普通 I/O | 外部 cwd、`-I -S`，5 次原创局部读取核对内容/hash-only 和 3 项错误代码；proof `255ec54e03f02ead24f3bb12349b89acce53062d6b45b914268a80f2f4311515` |
| Ruff | PASS；本包未重跑无关旧数据、HF、模型或 toy 套件 |

原 probe 文件未经修改。私有启动包装保留它的完整执行逻辑，以独立观察 hook 记录实际 child 的模块路径/hash 和局部 `_read` 次数，并拒绝真实数据/编码接口和框架导入。两 child 分别实际调用原创 FIFO `_read` 一次，模块 hash 均为当前修订；两个进程的观察记录、原 argv/UTC、stdout/stderr 与原 result 全部封存。时间是本次 I/O probe 的观察结果，不是模型性能数据。

**实际归档与安装。** 在现有离线构建支持上只执行一组三归档和一次新 target 安装。`uv pip install --offline --no-deps` 仅安装 toolalign 0.0.1，默认 CPU 依赖从原有环境复用；未新建环境或安装/下载依赖。安装版普通 I/O 使用隔离解释器显式加入新 target 与现有默认依赖路径，实际包来源已经核对。

| 归档 | bytes | 普通成员 | SHA-256 |
|---|---:|---:|---|
| direct | 204,680 | 70 | `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf` |
| rebuilt | 204,680 | 70 | `101eccd619e16805230cfdb8b440d4f19858020ae5d6c1d3d4068b0d31fa1ecf` |
| sdist | 355,610 | 143 | `cabbc8a37151f767925d9f83fd05b9adab93c88798db11fb298135b84b55d3de` |

源码、sdist、直接 wheel、重建 wheel 与 target 的 65 份包文件逐字节一致；METADATA、console script、LICENSE 及完整 RECORD 通过。两 wheel 各验证 70 行，安装 RECORD 验证 75 行；uv 的空 `.lock` 不属于 distribution RECORD，已单独 hash 并封存，未冒称为 RECORD 成员。包证明 `4531b68295b239c86c4614342a49391234a793eb96712c36787d3f9efd02faaa`。两份新报告和交接单不在 sdist allowlist，成文不触发再次构建。

**保全与额度。** intake `2516ea64a0df97c263ddbd29bebc5d6b2c41b7ee0965567473b1718371a13465` 核对原 10,935 路径/370 链接、618 原公开 Git/冻结副本、609 旧输入、5 旧 refs 和根 identity。修订后重新核对 10,933 旧私有及其它当前路径，两个获准修改的公开路径按原 f3 Git/冻结副本保存旧字节，并另绑当前新字节；其余 616 基线文件及原 scope、旧归档/target、失败、报告/交接均保持。完整交付核对 `c44809b0140a5a21d54cc160fad8fc69562100dcf2953bda3b9fc4b7f3914588`。

四个新 FIFO 节点保留原设备/inode/0600 权限和 lstat 类型记录，未纳入普通文件 hash 清单，封存不读取 FIFO 内容。替换竞态 fixture 本身实际执行过一次非阻塞 open 后同 FD 拒绝；清单函数的 `opened_or_hashed=false` 仅描述封存行为，不能解释为整个测试未打开 FIFO。其它 symlink 以原链接文本单列；未删除特殊节点后伪称原件仍在。

本轮唯一辅助失败发生在 recorder 启动前：新 `commands` 父目录缺失，创建 label 时 exit 1，intake/probe 尚未启动。原观察保留 `9f9a7bfa3656ff0528aecbaa7e530d645645258c12c3e3d8ad62678eb7160d60`，精确开始 UTC 没有记录；仅创建新父目录并换独立 r2 intake 标签后通过，未伪造 inner receipt。新单测、probe、构建和安装命令均无失败。原 R1 FIFO 失败及上一轮所有真实消费失败照常保留。

源/安装原 probe 额度各 **1/1**，归档组与 target 各 **1/1**，余额全部 **0**。真实 609 数据 prepare/verify、固定 13 例转换/导出/回读、全数据 build、新编码、框架/模型/GPU、优化、生成、业务 API、浏览器、费用与上传均 **0**。上轮完整 13 例消费属于 `bfdf2a256065d5396e6f7a4860fd7c7506f5c278`，当前修订真实数据消费为 **NOT_RUN**，不冒称新源码已重跑旧成功。

新制品在成文前为 29,025,009 bytes，预算 1GiB；最终 seal 继续计入文档、所有后续命令和自有外部 pytest 文件。最终公开扫描、五路径 scope、完整 candidate/tree/parents、普通 push/远端一致性与特殊文件终态随[交接单](../../coordination/handoffs/P04-sft-data-v3-nonregular-fix-r1.md)原生提交。独立 R1、最终 CI/main 与真实 trainer/容量/训练/评测/服务均待后续范围，不由本包自签通过。
