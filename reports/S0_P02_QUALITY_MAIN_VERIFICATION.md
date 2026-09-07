# P02质量修订：main技术验收

**VERIFIED，仅CPU技术范围。** [PR12](https://github.com/kris0516/ToolAlign/pull/12)以最终head `b1a9483e0cb7967a33a4ef922f2ca546e84c86d5` 普通合并为 `6c81dfcc855fca188181d1bb08870f47d8edacc9`。原候选 `9b7cf019b1d55501a7e656dbfb79b13bc7369fa0` 与独立R1 PASS `1e45cf2c2ea07b703be548a112ef16e1ef134ee9` 保持原SHA；P0/P1/P2为0。

S0已在实际main运行七组CPU检查及lint、冻结契约、公开扫描、diff和共享GPU锁读取。13条命令全部exit 0，执行前后main和480个源码文件一致；最终证明于2026-09-07 04:22:11 UTC完成，SHA-256为 `940f17eadfca53dd498ebc4e518b001da2bc36703f96288b31a063f2f3a857ef`，核对2,846个文件路径。

| 验收 | 结果 |
|---|---|
| 实际main CPU | **1,186 passed / 2 HF-only skipped**；110 subtests另记 |
| 分组 | 1,007基础CPU + 60格式 + 2截止时间 + 13训练绑定 + 44 SFT CPU + 34 native CPU + 26质量边界 |
| 最终CI | Python 3.11/3.14各14步骤成功；各713 passed/48可选环境skip，另46 P00 passed |
| 实际CI检出 | `5e813e0924f5f5aec4055d2a2d1426ea75a02239`，parents=`769f9ff` + `b1a9483`；480文件与实际main完全一致 |
| 现存归档及安装绑定 | 三归档、127个sdist源码、60个包载荷与main一致；原11条安装执行及实际module origins保持 |
| 主干新增构建/安装/API/框架 | 均0；复用并绑定此前隔离集成的真实产物与执行记录 |

最终[CI34082309397](https://github.com/kris0516/ToolAlign/actions/runs/34082309397)的两个原始job日志hash分别为：3.11 `03610c0f04b12418b2755ee9799d9b488f84b6fc860d192c9bd964289c503af4`，3.14 `2b4ede1d64c104a3a57ba46e232dd0eb51024d0645beee948dfb699898ab2bc2`。CI归档检查实际排除241个私有canary并保留18个公开fixture。CI绑定证明为 `58247729948f825586f54ef49f2793b82eed1b791081ec8059cf898cce8f42e5`；connector曾返回旧base字段，实际检出日志与Git父提交已核定真实基线，未用缓存字段推断合并结果。

三份归档和新默认安装发生在[隔离集成f90be60](S0_P02_QUALITY_INTEGRATION.md)，main仅验证这些现存字节与原记录，没有把旧执行时间改成main重跑。sdist hash为 `65623012f5046bbc46160c99d384d94532e8d30a5a08e684ca67652d5177b629`，两个wheel均为 `7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b`。默认环境下三正向入口、八次输入替换拒绝、无optional模块导入的原证据仍成立。

本次main没有失败命令；D1、R1和S0集成辅助脚本的历史失败按[接收](S0_P02_QUALITY_REVIEW_ACCEPTANCE.md)及[集成报告](S0_P02_QUALITY_INTEGRATION.md)保留，不增减正式质量失败轮次。当前main新私有制品时点统计为2,267文件、154,053,628 bytes；共享GPU锁实际未持有，S0新增模型/框架/全量数据或16例材料编码为0。

可验收能力是固定输入的32来源/40决策暂挂、原选择有序过滤、带lineage的staging和可核验的完整序列材料。尚未合入Q1后续恢复/隔离决定，未通过G-DATA，`training_authorized=false`，没有正式模型训练、评测或推理部署结果。

R1当前精确E1 `5270d1e` 的审计技术轮继续ACTIVE；S0于04:15:26–04:15:30 UTC核验8,658个intake路径、438候选/428基线、10授权副本及旧封存，证明 `3ce86d8246db1e18d7dfcdb0ae2f1bf6b1021fdeefee225f4581dafb20e9d215`。Q1固定50来源/60决策独立裁定继续，待完整封存接收后冻结数据新版范围；无需kris填写或签字。
