# P04-SFT-NATIVE-TOY-R1｜独立审查交接

owner：R1；gpt-6-astra / max；日期2026-09-07；分支 `review/p04-sft-native-toy-r1`。**PASS；P0=0 / P1=0 / P2=0。** [完整审查](../../reports/review/P04-sft-native-toy-r1/README.md)与[机器索引](../../reports/review/P04-sft-native-toy-r1/VALIDATION.json)记录范围、实证与限制。

| 绑定 | 精确值 |
|---|---|
| candidate / review唯一父提交 | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| candidate tree | `247eba004d714def81f0bef65375ddbf0fee95cf` |
| candidate parent | `c06782a61857259097932078c661189b4fda781d` |
| R1 authorization | `482f8991c97c33678583aa6c853a75c41fda0f0f` |
| 实现基线 | `50867c0be43d110df6c3620c94022fcfdaf779b5` |
| T1原授权 | `de86568d73ee77bbf92b6f749a39a9ab38955836` |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0021 |

本交接所在review commit/tree由最终Git对象确定，随原生回报及私有completion给S0。只新增本轮审查目录与本交接；被审408文件只读、399原基线保持，未合入新main或修候选。

## 通过的范围

- 五组原CPU检查1050 passed / 2 HF-only skips；新增原创34项通过，合计1084。110 subtests及安装版44项重复另记，生产新增36项已包含。Ruff全库/新审查目录、四份冻结契约通过。
- 标准库由原定义核对13 rank/12数值载荷、64个float32参数、EOS/shift/padding及44个监督token；解析CE/完整梯度经832个中心差分分量复核。逐例CE/梯度及真实checkpoint对独立两步参考均在固定2e-6内。
- 本轮R1框架额度实际2/2，失败亦计数，未增加额度。新安装版segmented真实8+5两次更新、同一model/optimizer/RNG、完整native evaluate、保存重载和错误checkpoint拒绝均通过。第二次提前登记用于不同的单段分支，真实仅一次更新/丢5尾微步，EXPECTED_NEGATIVE / exit0。
- 两次使用真实R1 owner、同一物理gpu0租约，框架导入前持有直至进程退出；GPU default/stream、Torch CPU 2+2线程及来源核验通过。原P01保护器和compile保持；实际子进程已回收，PID不存在，共享锁释放，均低于300秒/RSS4GiB/MLX1GiB限制。
- 原磁盘收尾丢终态已独立CPU复现；当前磁盘、monitor、最终诊断、启动与注入RSS故障保留终态并允许失败重登记。实际5个新增小型CPU子进程全部回收，未修改生产限额或T1/R1真实框架ledger。
- T1原31命令、27测量子集、7快照/409源码blob、3038文件/197链接、1559原文件与15嵌套默认命令已核对；三个源码epoch分别绑定。三归档122/63/63成员、58包载荷、Git/metadata/RECORD及默认sdist来源通过；R1新增离线安装target的准备/帮助/拒绝及native纯导入/guard通过，无可选框架或源码回退。

## 主要原件 SHA-256

完整argv、环境、UTC、原始日志、完整数组/checkpoint、模块来源与全部路径仅在本机新私有目录，路径随原生交接提供；未放入公开仓库。

| 证据 | SHA-256 |
|---|---|
| R1原件/epoch核验 | `878bed4d7888f744f4d1d77b8f421375f8ab44273992015fa92ea23a53cb7368` |
| R1原三运行独立解析参考 | `b108a72a9e676660922b6658d3d558c9012d59b68029652e19f2c32c5c82af43` |
| R1新安装segmented独立参考 | `4e689f0826e2a0224527283e03c0f0a6bc6709378dd92fed4aff0e7d418f302f` |
| R1新单段反例独立参考 | `2ab6e2653d5c04a5324e221a684fbac5ccf0cdce38b6306b795112c0a5f73ae7` |
| R1两次真实运行资源/所有模块来源/只读名称审计 | `84d4029fd418e8f29557520d4f539c64dcb63583709237b805f855e5ca0f6053` |
| R1实际三归档核验 | `65f4e7a51f1622916c923bc09022f7b0f6669160bcd85e9dedc56453af021e75` |
| R1末次旧材料保全快照 | `8837ce081ea387ec8452a17809030a43d9ac5147516cc820c46c473662127cda` |

旧51009文件、284链接、上轮1673封存文件/156链接与9份review文件保持；18旧review refs及73个原ref对象保留，旧私有历史不在公开祖先。本轮预算包括7个新系统测试目录；保全快照165857374 bytes，最终清单与占用随后单独封存。

## 保留失败与剩余边界

T1原启动前symlink-stat、第一轮CPU harness、第一轮安装origin、原磁盘反例和旧CPU KeyError均保留；原两次及R1一次semaphore warning保留，只读检查三个具体名称均ENOENT，不宣称全局泄漏审计。R1三份辅助审计初稿的schema/字段假设失败及修订原件也保留，仅修R1审计器。

此次PASS限固定原创toy与默认CPU准备。原CPU trainer仍保留 BLOCKED_UPSTREAM_CPU_ENTRY 历史；正式模型训练、真实P02优化、10+3/8228新编码、BFCL、泛化/容量指标均NOT_RUN。人工字段与页面观察均未执行，G-DATA及正式P04仍未放行。

公开扫描、最终commit/tree/parent、普通push/远端读回与最终私有completion在机器索引写定后绑定，避免循环hash。S0接到完整原生交接后决定集成、最终CI/main验收及下一任务；本轮不自行合并main，R1正式交付后结束。
