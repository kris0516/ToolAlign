# S0｜数据 CPU 修订第二轮正式审查接收

状态：**CHANGES_REQUESTED**。2026-09-07 23:19:19 UTC，S0 完成精确候选 `1769046468eb2ebfdd9e982ba4938833760e3fe0` 的 R1 正式交接核验；原 review `58212d26bdb1c6a681a1ac34ccae854daefca8d3`、tree `0e3a60db9865d82b8a15f35727769975d3b1be2b`、唯一 parent 1769046 均保持。原生任务已于 23:09:12 UTC completed/idle，gpt-6-astra/max。原 [正式审查](https://github.com/kris0516/ToolAlign/blob/58212d26bdb1c6a681a1ac34ccae854daefca8d3/coordination/handoffs/P04-sft-data-v3-review-r2.md) 为 FAIL，P0=0、P1=0、P2=1；该失败候选继续不合并。

| 稳定问题 | 本次正式处理 |
|---|---|
| P04-SFT-DATA-V3-F1：特殊输入无 writer 阻塞 | 原未修改 f44 反例在 source/新 target 各一次通过，及时拒绝、无需 writer、child exit0/reaped。分项 PASS 被 S0 接受，问题关闭，连续失败计数 1→0；原 b99 FAIL 事件保留。 |
| P04-SFT-DATA-V3-F2：fdopen 构造失败后的裸 FD | P2，首次正式失败计 1；一次目录替换残留一个 FD 为实测，长期重复累积/EMFILE 为源码推论。T1 已在同一已派范围修订；原中间消息、辅助失败和源/安装自测均不另计正式次数。 |

本次实际 147 项相关单元全部通过；六项附加 I/O 检查为 **5 PASS / 1 FAIL**，目录 FD 关闭断言原失败保持。最小无 stream 包装的观察再次确认 FD 留存，并主动关闭自有 FD；所有自有 child 均回收。拒绝及时和本次进程生命周期不能替代生产 API 的 FD 清理。R1 原拟 P3 判断及依据实际生命周期修正为 P2 的过程保留。详见 [S0 原发现](S0_P04_DATA_V3_R2_INTAKE_AND_FD_FINDING.md)。

唯一新默认 target 的固定消费通过：prepare/verify 各一次，13 例 rebind/export/readback 各一次，真实编码/数据 build 为 0。S0 核对四 view 的 7,928 成员、原行/rank/完整记录，13 唯一例/两 engine 26 份完整序列、padding、loss/causal masks、EOS 和 token 文本保持；10 个 train 材料与 3 个协议材料边界保持。

新导出 2,030,656B，SHA `4c261560f3e27842d1cad0fce16220c8073df8a35a9592c4526c61f64a5a738c`，与运行前冻结的完整预期字节一致。相对原 `9b711be1ba6b301e6efb8c9853c0c6b98fdaa2db9db2e2cd2fa348739ca6ba0b`，仅 `consumer.package_files.training/sft/data_v3.py` 从原 f3 hash 变为当前 `212c688c1a38e4c2ce7863e34efc7635d75878729e4e141333caeb08a6fd16a4`；数据及其类型未变。原 T1 的 NOT_RUN、原消费时点及旧导出均保留，不把本次结果套到尚未验收的 FD 新修订。

三份原实际归档、65 个安装包文件、75 条安装 RECORD、五个既有默认依赖/145 文件与 32 个实际模块来源通过。固定消费使用外部 cwd 与 `-B -I -S`，当时 package/consumer、614 输入和 helper pins、预先预约、原始 stdout/stderr、argv/UTC/exit 均与原生命令绑定。R1 所有安装/原反例/固定消费额度余额 0。

S0 接收证明 `b5332709432e9361bc7339ab870398c64c6a623a0164bf505f54ddf4bebad92a`：94,238 路径、1,707 个不跟随链接、13 个仅 lstat 的 FIFO、4,956 Git 绑定、23 条原生命令和终态关闭。621 候选文件不变，review 只新增 5 份材料，共 626 公开文件。T1 已进入授权的新修订，其旧 621 公开路径按原 1769046 Git/既有快照绑定；原私有证据仍按原字节核对。

原 terminal seal 为 29,244,725B / `677bdb9d35f45b2f1cb545f34930ae437c27ec8972a225ee7570bf2ed6544bbe`；envelope 为 2,600B / `473140397bd9a26c4438a488251c949c915fd9af5c3d1de57e04596c157bf38c`，完整关闭 exit0/reaped。R1 本轮含全部尾记录的制品 214,263,209B；旧模型 review、原 b99、所有旧失败、root identity 及 30 文件/1 链接缺失例外保持。20 模型文件只 stat，没有新增打开/API；未公开 f708 不在公共祖先。

S0 原生命令匹配器首次未正确追踪多次轮询的原 session，及本次接收脚本对 inventory/module-origins 的两次字段形状假设错误均保留；修正后完整绑定通过，未重跑 R1 的任何实际测试或数据 API。R1 自身辅助失败、预消费前 wire 草稿修正和原 5/1 失败也保持。

全台账现有 84 个问题，83 个关闭，唯一 F2 当前连续失败 1；无人达到 5 次阈值，整个目标继续，无需 kris 介入。[T1 FD 修订](../coordination/tasks/P04_SFT_DATA_V3_FD_CLOSE_FIX.md) 继续，完整候选/独立复审/最终 CI/main 待完成。模型 CPU 的 PR17 主干验收与冻结 v3 的 G-DATA PASS 保持；正式模型/容量/训练仍未授权。本次 S0 新增 build/install/数据 API/编码/模型文件读取/框架/GPU 均 0。
