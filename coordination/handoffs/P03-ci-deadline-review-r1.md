# P03-ci-deadline-review-r1｜R1 独立审查交接

2026-09-06。**PASS；P0=0、P1=0、P2=0。** owner=R1，gpt-6-astra / max。本轮审查旧截止时间测试修订；原测试的启动速度假设已通过实际反例定位，新控制正确拒绝仅靠tool_timeout收尾的运行。

| 字段 | 精确值 |
|---|---|
| 授权 | `c91ea4f79e59e667fd008fab28aaca2e3efdbfe4` |
| 被审candidate / parent | `947144fa2dd248113f6db412f120cdae5483c9b8` / `f69c6a309ff45980c21c2119016f4c5cf8acf8b7` |
| candidate tree | `198606c59676c2fd5e92056d7217dc22c0ee2d8e` |
| 输入基线 | `4a1fa84d2d367ed037a1e39b1d4033f54a385e6a` |
| 审查分支 / parent | `review/p03-ci-deadline-r1` / 上述candidate |
| 契约 | plan-v0.1 / coordination.v1 / toolalign.contracts.v1 |

实际审查commit/tree在提交后按Git对象回报S0并写私有completion；可从本交接单的提交历史读回，不能把候选SHA当作review SHA。[完整审查报告](../../reports/review/P03-ci-deadline-r1/README.md)与[机器证据](../../reports/review/P03-ci-deadline-r1/evidence.json)包含命令、原始日志hash、完整归档成员、失败与NOT_RUN。

- 精确947完整CPU **657 passed / 0 skipped**，47.97秒；已含三个目标控制和17项真实CPU tokenizer。另两个独立探针通过，不重复累计目标三例。完整日志 `25d1ddbc82bb151a118c2f69d2e0a835f93bed5cb8c727594e239292931303ba`。
- 原测试/未追踪helper/launcher按原字节重放：真实请求约693.63ms到期，工具尚未执行仍被停止并回收，原709行断言exit1。原日志 `c00c6a211a33097079dcdfe49289b223dfd8f8f40dedf324bd52bd0f70ed1e54`。
- 原负向launcher调用候选同一正向断言：绕过请求单调约束后靠原tool_timeout收尾，共用断言明确exit1，日志 `1d3653bae64c5c2bc4909d937b9d6243aded91821e95b8ed2f7e80c7648db7ae`；不计新增成功场景。
- 独立探针覆盖0.3秒真实清理延迟，以及阶段标记缺失/请求绕过时10秒真实watchdog退出。7次相关运行的14个自有真实子进程全部reaped、目录清理；全部局部patch与Timer恢复。测试时钟700/1100ms不属于性能数字。
- 282份候选及277份原文件保持；f69至947只三份交付文档；生产42份包载荷不变。4767路径按S0清单独立重算hash/bytes，19条原始命令与15条公开命令绑定，五份tokenizer来源和15条旧review refs保持。不同清单有交集，不相加。
- 实际新sdist SHA `eed6c038c31170a0fb4957b8286e01f20b0ecf96c64514f05f9b97a1040a76fc`（194485B，89成员）；默认/显式sdist重建/精确4a1基线直接wheel SHA均 `e2c5d06beff3c8b7bc0098c0c58a45413de2dbd505ad5378acb05f689a7657b5`（96713B，47成员）。45份确切基线包输入与当前生产输入相同；所有成员、Git载荷、metadata与RECORD核对通过。
- 原E1缺psutil/临时目录错误、预期失败及无独立inline stdout的限制保持；R1两次辅助核对设置错误及原脚本/log也保留，修正后全量核对通过。没有改被审实现或旧测试签PASS。

复用既有纯CPU解释器，禁写bytecode；未安装新项目环境、联网下载、导入模型框架或占GPU。本轮新增制品与四个pytest目录公开前为7030151逻辑bytes，低于2GiB。原始绝对路径、PID/owner ID与日志只在本机；公开材料使用角色占位符。

未合main、未合新格式、未推动旧分支或重跑PR8。新候选CI/最终组合main、未变wheel的重装、Linux/Python3.11、模型/训练/BFCL/正式评测/P04、全量数据重测、人审/G-DATA及服务部署均NOT_RUN。R1审查提交后结束，普通回报S0并等待其集成验收。
