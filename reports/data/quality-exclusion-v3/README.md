# P02 v3 整来源排除与材料复用

本轮已交付 CPU 候选：新增一处完整来源排除，保留原 83 来源的处置和局部判断；按 Example 身份复用 11 个旧材料，仅对两个固定新例各运行两条 CPU tokenizer 路径。独立 R1 技术复核、Q1 实际处置与完整材料验收及 S0 主干验证待完成，`training_authorized=false`。

生产基线为 `d3e56f68ebd67cc576d912b6f06636682b4170ab`，原授权为 `3e18145b66baa7bce498926869b2d52bd0503453`。实现与全部实际新编码绑定 `6054b349c344cbbad30c12ce8fe8820c59e8bc10`；两次实际编码命令执行时该提交干净，源码 epoch 为 `6a78def4887e6e41aa3f3e8a02a99f091acbcc42a187d3f30de90027ff707598`。后续报告提交不改变已测生产源码。契约保持 plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / Action JSON v1。

S0 配置逐字复制，SHA `784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261`；原 347 项输入 manifest SHA `ebbaf56bbb5730b5d31eca195d5ac7772d148ff876fc96be1c1c5dbbadf51e06`。新增执行放行独立保存，未改写配置、输入、issue 台账或原判断。Q1 的来源审阅提交为 `9c12c47fd815f86992078313bac88dcec253f37f`，两完整来源及三 Action/前缀、六调用 PASS；S0 放行文件 SHA `1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd`。该审阅范围为来源语义，完整 v3 交付仍待后续独立验收。

| 集合 | 已验收 v2 | 实际 v3 | 本轮移除 |
|---|---:|---:|---:|
| 有效 train | 7421 | 7419 | 2 |
| 有效 validation | 230 | 230 | 0 |
| formal train | 5940 | 5938 | 2 |
| formal validation | 213 | 213 | 0 |
| smoke train | 1583 | 1583 | 0 |
| smoke validation | 194 | 194 | 0 |

两份新目录各含 29 个稳定制品，逐字一致；共同 manifest SHA `f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437`，quality revision `919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8`。两次构建额度已用尽，后续验证和安装未产生第三份数据目录。构建时的原 HEAD、dirty 状态与源码快照保留在各自运行记录中，不冒称构建发生于后来的实现提交。

实际核对 84 个处置来源、103 个局部决策，排除 81 来源/100 决策，原字节恢复的 3 来源/3 决策保持。新增来源的两个局部 Action PASS 保留，整来源历史不适合训练的结论独立决定排除。其同组此前有效的另 5532 个决策均保留。共核对 7928 个选择 sidecar 和 15577 条原始 JSONL 行；`selection_rank` 为连续 v3 排名，`parent_selection_rank` 为原 v1 排名，`previous_selection_rank` 为已验收 v2 排名。无补选、重标、跨 split 或 staging 晋升。formal train 较原 6000 下限少 62 条，训练绑定明确记录该偏差，实际 trainer 消费仍为 `NOT_RUN_PENDING_SEPARATE_ADAPTATION`。

固定代表规则仍选择 10 个有效 train 原例和 3 个原创协议例。11 个旧例包含三协议例，完整 sequence、padding、token_texts 按 Example 身份绑定原两 engine 记录；保留原编码命令、实际时间、源码、原 run 与静态再发布出处。另一退出代表材料的旧 PASS 例仍保留训练资格。静态冻结的三个版本只更新发布者代码身份，cases/coverage/manifest 字节不变；所有旧目录和失败保留。

两条实际新编码命令均在 S0 放行后运行：tokenizers 于 15:02:22–15:02:55 UTC，transformers 于 15:03:52–15:04:26 UTC。每条恰好生成两个新 sequence，总计四次。独占预算文件及逐次开始/完成事件防止同一 engine 自动重试。来源中第三个仅供完整语义覆盖的目标未编码，旧 11 例未重新测量。

两条路径的完整 13 例记录 SHA 均为 `a41f5c24a55eb5e4fed434b9352b655fbf78e5aa68276de5de183671c81412de`。native manifest 为 `d37aa9d34e0fd90e99391f2411324bb8a9163bf12a4b1953d67ffd8973e6c585`，reference manifest 为 `affb910add686885b8bc8410c086be4797be11dcb6fca2bae5b8329839b69469`。26 是两条路径的材料记录数，其中 22 个复用、4 个新测；独立例数为 13。语义与 token/mask 判定栏空白，HTML 字节核对通过，浏览器实显仍为 NOT_RUN。

最终适用默认 CPU 回归为 **839 passed / 48 optional skipped**，其中本轮新增 73 项：数据与 issue 绑定 29 项、材料与编码边界 44 项。跳过项需要额外真实 tokenizer 范围；本轮未重跑已验收且无关的 427 项历史报告测试。每次 pytest 使用独立 basetemp，原旧测试目录不被清理。Ruff、四文件契约冻结、公开内容扫描和 diff 检查通过。最初两次新测试失败分别是夹具未制造实际排名变化、断言未沿用精确 trainer 状态；修正后通过，原日志/源码 epoch 保留。另有四次只读路径查找失败，均保存原退出信息和纠正记录。

实际 sdist 含 140 个成员；默认 wheel 和从该 sdist 重建的 wheel 各含 69 个成员且字节一致。sdist SHA `50881d9f05a35a15825ab55d9b3bd03eb99783f4fc99b56153d706f7446fe642`，两 wheel SHA `681428cbe1e9638aeab8eb6ed1f123d518021c17279084e7191b6ae52e829f95`。成员、RECORD、元数据及 64 个安装包文件已绑定源码。默认隔离安装使用既存纯 CPU 依赖目标和 `-B -I -S`，6 条命令验证安装包 API、完整材料比较、新入口、已有输出拒绝及原 v3 输出验证；其中一次退出 1 是预期的重复目录构建拒绝。无源码 cwd 导入、可选框架导入、新编码或第三次数据构建。

原始数据、数组、HTML、日志、运行源码快照、执行放行及最终封存仅留本机。公开复现入口为 [verify_outputs.py](verify_outputs.py) 与 [check_package.py](check_package.py)，汇总见 [evidence.v3.json](evidence.v3.json)。本轮没有新持久环境、依赖或下载，没有全库重分词、模型/GPU/训练、外部业务调用、费用、上传或浏览器重试。P02-Q-081 的正式失败计数仍为 1，由 S0 和独立审阅者接续处理。
