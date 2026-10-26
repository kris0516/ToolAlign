# R1｜G6 真实服务与最终交付技术终验 r1

实际smoke、停止和全部71份远端产物回收已完成。S1随正式派发给出精确候选提交和私有索引。本任务不授权GPU、模型重跑或修改实现。沿用已接受的 CPU 独立审查与未改变的数值结果，不重复完整检查矩阵。

只读复核真实 Mac→SSH loopback→Colab 固定 CUDA child 的证据链；不能以作者总结或 scripted 案例代替真实请求。检查最终 README/复现说明实际命令可对应已审核代码，并核对公开最终差异及 GitHub 版本。

- 冻结源码、依赖、M1/G3 step743、模板、输入、seed、请求顺序与配置在首个输出前绑定；实际尝试数及所有失败/缺失保留，没有输出后换题或补跑。固定模型与工具 schema、principal 来源及原文 gate 一致。
- 实际 SSH 转发和 HTTP 回包可绑定同一 service_run_id/来源/ModelIdentity；服务仅监听 loopback，非公网。token 不出现在 argv、返回或日志，原始证据留私有。启动 prepare 的 ready/epoch 来自真实当前 child，无隐藏生成预热。
- 冷加载、请求队列、child generation、TTFT/prefill/decode、cleanup和完整wall定义一致。真实 cache_hit_tokens与prefill_tokens支持命中，跨principal与重载后的miss符合单entry契约；相同原文不独自证明命中。不得把有限smoke外推为P95或稳定吞吐。
- active取消以实际running、取消回应、child回收和锁释放为证；重载必须为新child/epoch且固定身份相同。请求先完成或未确认回收不能写成取消成功。正常退出、SIGTERM及controller硬限的实际使用范围区分，不把未运行分支写成CUDA已验证。
- Mac客户端独立parse实际raw，核对本次advertised schema/参数/call_id后通过既有registry执行；所有本地tool child计数与回收对应实际记录。接口completed、工具completed、轨迹完成及语义正确分别说明。实际错误不被scripted动作覆盖。
- 逐项核对服务started/terminal、summary、controller manifest/recovery、实例身份与停止后不存在；未知保留unknown。总G6分配从创建开始包含安装、失败连接、空闲、传输和回收，符合7200秒/观测4CU与首单3600秒上限；attempt不超过冻结计划及12次总限。
- 干净CPU环境复现证据和五类原创示例来自本轮精确源码；公开包不含私有数据、隐藏题、权重、token或本机任务身份。两个已验证SFT完整checkpoint的位置/身份可读，DPO无checkpoint不补造。回滚为停服并恢复上一稳定代码/配置/训练制品，不虚构前版已部署服务。

交付 PASS/REQUEST_CHANGES、精确依据、必要问题ID与失败轮次建议、独立审核报告/handoff/commit及私有索引。只对所核范围下结论，不修改共享台账，不修实现后自签；无需再分配GPU重复已有smoke。

实际运行源码为PR35 main `aaab0171246feaf307ad2c626108e94383e438d9`；结论候选见[实测报告](../../reports/S1_P07_G6_SERVICE_R1.md)。重点区分：生成次数上限已回收epoch2 child，后续SIGTERM只结束HTTP父进程；取消只观察到调度running，内核执行进度未知；原SSH安装中断和同实例并发SSH的HTTP429保留。审查[复现说明](../../docs/19_REPRODUCTION_AND_DELIVERY.md)的新启动顺序、账户资源账目和全部未完成边界。

仅提交 `reports/reviews/P07_G6_FINAL_R1.md` 与 `coordination/handoffs/P07-g6-final-r1.md`；审计脚本、逐项计算和原始证据索引留私有。复用已接受CPU数值、五类案例及干净环境证明，除发现具体证据缺口不重复运行全量测试。
