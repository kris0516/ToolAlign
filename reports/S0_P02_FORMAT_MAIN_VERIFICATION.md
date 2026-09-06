# P02 共用格式与P03截止时间修订｜S0主干验收

2026-09-06，S0。**P02-FORMAT-v1与P03-CI-DEADLINE技术范围VERIFIED。** [PR8](https://github.com/kris0516/ToolAlign/pull/8)已实际合并；P02整包/G-DATA仍待kris语义审查与训练配置绑定，P04正式训练尚未授权。

## 提交与独立审查

- 实际main合并为`36b6988af6b4e0125b59fb81b1cea142233e14a2`；GitHub已读回closed/merged，11:22:35 UTC合并。本地main已快进到同一提交。
- 最终PR head为`b3d07dd7c0db90085efb647ff7e740fdfbec240b`，实际main、该head与CI检出的`66a41123d942056e64e0726ef94540c99b5bb115`具有相同tree：`76fd03e8f86e9892c1ab51c8e8bdd15ea2d28be4`。两个merge的父提交均为main6a53a07与最终head，337份文件逐字节核对一致。
- 格式候选8c439f6获原R1审查`b9f7567d7c1066eeb0bff7c47033bb2771eb9594` PASS；截止时间候选947144f获原R1审查`1531892a9e49b69283ef07f3142b221693483628` PASS，均P0/P1/P2为0。普通merge保留两份原审查及原格式FAIL2942e568；原未去敏审查未进入公开祖先。独立证据与S0接收证明见[CI跟进](S0_P02_FORMAT_CI_FOLLOWUP.md)及[最终组合](S0_P02_FORMAT_FINAL_INTEGRATION.md)。

格式实现提供角色保留的Action JSON v1投影与完整序列边界；HF来源修复让真实loader消费已核验字节的独立快照。截止时间改动仅为测试与局部helper，区分启动前到期和真实工具阻塞后到期，生产executor/harness/isolation字节不变。测试时钟的700/1100ms不作为运行性能。

## 最终CI与实际main检查

[CI34029892077](https://github.com/kris0516/ToolAlign/actions/runs/34029892077)的Python3.14 job101477377185与Python3.11 job101477377737均全部步骤成功。每个默认CI job为487 passed / 48可选tokenizer skipped，另46项P00独立检查通过；lint、4契约、337路径公开扫描及归档边界检查也通过。归档边界探针保留241私有canary和18公开对照的实际范围，不等同于正常产物的成员数。

两份连接器实际decoded原日志按完整UTF-8字节保存，SHA-256分别为`4fc5b060b2380e2dfba4eac7a28ff84da226c7f11fceb473e1ddcc9c871bcf04`与`720772edff4657a989b422ecd04a44c27b4661850a30747ab94471b8926d24bc`。CI提交/父关系/全部步骤证明为`42cafb3e24fd4fae5fecf96a1617b7bf6faf4af6f2d5a6d3c0fa31acca56af77`。原CI34024093376的真实失败仍保留。

11:23–11:25 UTC在实际main复用既有CPU环境和固定本地tokenizer运行。各命令有本轮实际argv、环境、Git/tree、UTC、退出码与日志hash；三个pytest调用互不重叠：

| 实际main范围 | 结果 | 日志SHA-256 |
|---|---|---|
| 全部tests及既有P00/P02/P03/P01独立回归与P01-r3/r4报告检查 | 781 passed / 2 skipped，52.14s | `a145e4115ec57c8f7dbf700c790bdcae5e53c27b8a4f588db00dc8b88c57a7b8` |
| 原R1格式结构及统计检查 | 60 passed / 0 skipped，0.13s | `b40f7074b5c83beb3dfff0891b029118d9fc58ace31af2619271fdc35cab43e3` |
| 新R1截止时间边界探针 | 2 passed / 0 skipped，11.55s | `6f8c24f6ae2e6797a0ce5479e071fd93b94737d09c7cbd318423fcde91cd4d8e` |

合计**843 passed / 2 skipped**。两项跳过是native环境的HF专属清理测试；R1另组真实HF覆盖保留其原运行身份。目标三例已包含在781内，不额外相加。具体路径集合沿用[最终组合报告](S0_P02_FORMAT_FINAL_INTEGRATION.md)，本轮分别使用新的main临时目录。Ruff、4份冻结契约及337路径公开扫描通过。本轮7条验证命令均exit0。

## main与实际归档/安装证据的绑定

本轮直接重新解析最终组合6108c08实际生成的三份归档，检查成员、当前main Git载荷、metadata和RECORD：sdist214091B/101成员、默认及显式重建wheel各107033B/52成员。sdist100份Git文件全部匹配main，wheel47份生产源码/资源匹配main；归档完整SHA见最终组合报告。实际main与CI/head的tree完全相同，没有以旧包推定新代码行为。

这次main验证没有新增构建或安装。两个实际wheel与[08:42–08:55组合预检](S0_P02_FORMAT_PREFLIGHT_R2.md)实际安装的默认wheel完整字节相同，因此保留该次10条默认接口命令与安装版两engine原F1验证的真实时间、环境与结果。归档/main绑定证明为`6a5cc819f818dab176806e570e904d06bcef25f222d2077afbe2b2e0ae830c76`；本轮解析日志为`7c2e15f6bf50784b33205f54587091739bbafa18c69905c0cb99087af5d1dfe2`。源码直接正常wheel、完整8,228行新重跑及新模型/GPU运行均NOT_RUN。

本轮主干摘要SHA-256为`b1c14a83774efa975f489a89ff71b4e98411e5ae06902b817d0abf7eea747602`，记录337文件身份和全部7条实际命令。原S0环境前置失败、归档脚本遗漏及全部D1/E1/R1失败保持原记录，未改写为成功。

## 剩余门槛

11:26 UTC实际检查共享GPU租约为空闲；原100行人审填写副本仍0 reviewer/0 verdict、SHA-256保持`eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb`。旧数据、split、目标、8,228行表示审计及其测量代码/环境/时间继续保留。

技术验收解除共同格式的main前提，但不代替kris语义判断、训练选择/配置/manifest绑定或P04至少10条token/mask人工核对。后续CPU准备须有独立限域任务；正式训练、偏好、评测和服务仍按P04–P09阶段门推进，完整目标尚未完成。
