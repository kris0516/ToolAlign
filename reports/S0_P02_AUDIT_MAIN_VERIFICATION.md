# P02审计类型修复：main验收

**VERIFIED，仅CPU审计技术范围。** [PR13](https://github.com/kris0516/ToolAlign/pull/13)以最终head`c5afd89e5c4952be75b4b1b724a07220a77444d7`普通合并为`1887feb060dce5b92270050f825991964c829b5a`。精确修复`da22baf46248c2fc0a36e04105bb8df9b48d62fb`、原R1 FAIL`964505512b56af927e4022aab260ab5a91ca5b86`、新R1 PASS`0cefe771c8d867d9e253b6603105ad31dc3a7787`均保持原SHA与完整历史。

S0在实际main执行9条检查，全部exit0、子进程已回收，执行前后525个追踪文件与main一致。main证明`b0f572ff612b1a49aa7ae83595146b241e5b25fb78e74ed85d34219f06325cc1`核验658条文件路径，独立接收与此前组合证据见[集成报告](S0_P02_AUDIT_INTEGRATION.md)。

| 验收 | 实际结果 |
|---|---|
| main类型/引用/固定采样原创夹具 | **55 passed** |
| main材料与显示数组检查 | 9+6项通过：12个错误变体拒绝，3个正常或合法重排检查通过 |
| Ruff/显式全部Python文件Ruff、契约、公开扫描、diff | 全部通过；4份冻结契约、525公开路径 |
| 最终CI | Python 3.11/3.14各14步骤成功；各713 passed/48可选环境skip，另46 P00 passed |
| CI实际检出 | `b91afd8fb7799e04b87d5b637b566c7b0355cfd7`，父提交93e088f与最终c5afd89；525文件/整棵tree与实际main一致 |
| 归档与安装绑定 | 三份现存归档、127份sdist源码、60份已安装包文件与main一致；原11条安装入口执行时间保持 |
| 新增构建/安装/API/分词/模型/框架/GPU | 均0；共享GPU锁实际空闲 |

最终[CI34114614433](https://github.com/kris0516/ToolAlign/actions/runs/34114614433)的两个原job日志hash分别为3.11 `33c4101ee561dd6d4144b71e9b7da8824d5f5961769d5823faf73a283cd2a384`、3.14 `3e47b786756ee2390279a6100af21ebc556def183601e381c92c404c84a054a7`。CI归档实际排除241个私有canary并保留18个公开fixture；精确提交/日志绑定证明`5f267ad67eb9fe92771ff6f9c9d78abf9a35dc6b07a0fdd8ea509db8b4540584`。connector缓存的旧base字段没有被当成实际基线，真实检出日志与Git父提交已核验。

生产包源码、旧测试、配置、锁与构建脚本没有变化；旧[PR12 main的1,186CPU/2跳过](S0_P02_QUALITY_MAIN_VERIFICATION.md)继续作为原时点证据，本次main只实际运行上述55项pytest，不作累计或冒称全套重跑。sdist hash`65623012f5046bbc46160c99d384d94532e8d30a5a08e684ca67652d5177b629`，两个wheel均为`7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b`，原安装发生于f90be60，main仅复核现存字节与执行记录。

本次main检查无失败。S0组合证明的状态名辅助断言失败、原R1/E1失败及工具事件保持。更新PR元数据时，GitHub对同仓库的maintainer协作标志返回422，但标题/正文已应用；S0读回确认后未重试更改权限。CI的既有Node运行时弃用提示保留于原日志，不影响本次成功步骤。

`P02-AUDIT-TYPE-001`按新正式PASS关闭、连续失败归零；原首次FAIL事件与四类反例均在主干。其他数据问题及D1的217项冻结输入保持，不将新台账追溯写入旧审阅输入。Q1原判断仍绑定原packet，浏览器实际显示NOT_RUN。D1新版数据、R1技术与Q1材料核验仍待完成，G-DATA和正式P04尚未授权；无模型/数据上传、费用或公网推理。
