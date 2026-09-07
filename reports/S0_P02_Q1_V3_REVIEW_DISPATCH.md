# S0｜v3实际质量与材料审核冻结

2026-09-08（本地时间；证据UTC为09-07），Q1-P02-v3-r5 **CLAIMED／待原生派发**。固定输入在15:59:52 UTC冻结；R1已按完整`7a731c5f08a561f5941fcba5996004706f373392`原生派发，独立技术审查继续。尚无本轮Q1质量结论或R1技术结论，P02-Q-081计数1、G-DATA和P04门槛保持。

## 固定审核对象

候选`5825d789ee89afedbfff31e828223608c6f435e2`，实际新编码代码`6054b349c344cbbad30c12ce8fe8820c59e8bc10`；S0[完整接收](S0_P02_QUALITY_V3_HANDOFF.md)已经绑定候选、实际数据、原命令和归档。Q1使用S0协调基线`7a731c5f08a561f5941fcba5996004706f373392`，其生产基线仍为已验证`d3e56f68ebd67cc576d912b6f06636682b4170ab`。

输入manifest `b2ae91538823c2e64af68deb871736134e488df00937df34e2cfd207470e4a8c`，共294项：223份精确副本／29,269,007 bytes和71项既有制品只读引用。[Q1精确配置](../coordination/tasks/Q1_P02_V3_REVIEW_CONFIG.v1.json) SHA `e6a1c4ac922662992f5afeba338d88e522015367f5753c8c0ebc0743994ce51e`；[任务范围](../coordination/tasks/Q1_P02_V3_REVIEW.md)。

- v3实际输出30项和v2父输出30项，含有效集合、两profile、处置、排除、恢复、lineage、原rank和版本绑定；大型数据仅作身份及原行字节核验，不重新语义抽样。
- 当前66份固定材料覆盖13个唯一Example、两engine完整数组和静态HTML；旧66份材料和13份原测量依据保持。
- 36份新旧源码epoch元数据／consumer源码，两次新编码的原命令、事件、预算与S0精确放行保持。路径仅表示出处，不扩大递归读取范围，不运行这些生产器。
- 原8a和9c的判定／seal、固定issue台账和3份S0正式接收证明逐项绑定；旧83来源处置及新两来源语义仅作继承绑定，不重复计算正式修订轮次。

当前v3共84来源／103决策处置，81来源／100决策排除，3来源／3决策原字节恢复；有效train/validation为7,419/230，formal为5,938/213，smoke为1,583/194。Q1独立核验P02-Q-081两条决策是否全部实际隔离，并对两例新增sequence逐项判断token/mask；旧11例须通过完整记录相等后才继承原判定。

## 独立任务与保全

R1新分支`codex/review-p02-quality-exclusion-r1`、候选564文件和新身份均已核验。原intake `23c605822c626432475913f3113adc10ed7c034ae8f6b9622815bd22bbcc126f`的33,422路径／644链接、19份本轮授权及347份D1输入通过；无语义最终集读取。S0同时复核Q1原9c的556份公共Git／快照、767份旧scope文件，原生completed/idle和干净旧分支已确认。16:02:35 UTC这次检查共35,304实际路径，无新增生产测试或模型运行。

冻结辅助程序曾错误要求不同历史checkout的同名公共文件使用相同hash，首次检查在复制前停止；原脚本和原生失败退出保留。修正为逐个实际选定的不可变输入绑定既有证据后通过，没有修改原审核或候选。

## 候选CI

[PR15候选CI 34139426339](https://github.com/kris0516/ToolAlign/actions/runs/34139426339)的两个Python作业各14步骤全部成功。原日志均记录839 passed／48 skipped和另46项P00独立测试；实际checkout为`417fcf9f17ab0a421abdb9a8ffd779e3be98311e`，父提交为当时main `fac2a5c0a7cd7593e56ca89adc68dd5ab5630d4b`与候选5825。

S0通过Git对象、两份完整日志和job/step回执核对全部590个实际合并文件，候选仅11个新增文件叠加于当时main；证明SHA `ed61ef7273a4488d872b5f03b51e66bf049d431c8933ae5a1c48dadc02324ca1`。此为候选CI，不代替独立结论、最终集成CI或main验证；PR15保持Draft。

两独立审核均为gpt-6-astra/max，不使用sub-agent。Q1新增制品≤1GiB，生产测试／数据构建／编码／框架／模型／GPU／下载／业务API均0。浏览器实显和真实trainer消费仍NOT_RUN；同一问题连续第五次正式修订未通过才暂停整个目标，当前未达阈值。

S0输入冻结证明SHA `adb6cab413a39fbf44fd8dbdf87df28f04bf500dce63349a96ee77e0c4268b2a`；reviewer就绪／intake检查证明SHA `d089d9129af937d0717ca55909749a697dd018dbd73bde731c2e49fe264f8f52`。原生回执和完整私有路径仅留本机。
