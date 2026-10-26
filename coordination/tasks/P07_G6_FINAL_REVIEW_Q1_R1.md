# Q1｜G6最终案例、模型说明与交接审核 r1

真实服务11次冻结尝试已完成，71份产物回收、唯一实例停止；S1随正式派发提供精确文档候选与私有索引。实际审核者Q1 AI，替代旧本人填表/答辩要求；不声称kris本人已掌握。只读检查原始证据与说明，不写生产实现，不重新推理/训练，不改变原指标或私有测试。

核对精确代码/模型/adapter/模板/数据身份、服务run配置、真实request/terminal与回收账目。五类原创CPU scripted案例（正常、无需工具、错误参数、恢复、预算）逐一说明为何符合既有契约，实际GPU模型案例单列；API completed、工具执行completed与完整任务成功不得混写。取消、超时、未回收/缺失用真实状态，不能把scripted动作补到模型输出。

复查模型卡/README/复现与回滚说明，保留已独立验收的G3 CE、G4 0偏好无DPO checkpoint、G5 M0/M1 0/28、恢复0/8、A2局部prefill收益、L2零合格无官方成绩。监督目标全tool_calls与结果一致，但不能单独归因为唯一原因；后续训练须独立train/development材料，本轮没有新训练授权。小样本延迟不写P95 SLO或稳定吞吐提升。

用既有真实v3/13例之一核对角色、token范围、completion/EOS监督及mask；不用公开原数据。DPO数学说明应使用已验证原创例子，chosen/rejected的相对policy/reference SUM差与sigmoid loss方向正确，reference是固定SFT，初始policy=reference时约ln2；它不冒充实际可训练偏好。用一条真实G5失败解释终止/澄清/无需工具边界，保留隐藏题隐私。

实际服务只在loopback，经SSH本地转发；固定registry、auth、幂等与取消的说明对应CPU与真实路径证据。启动冷加载、排队、生成、cleanup、完整wall分别对应定义；真实命中必须有cache_hit_tokens和身份，输出相同不单独证明命中。预算覆盖全部安装/失败连接/空闲/回收，最终停止缺席有据。

公开内容只含代码/原创开发材料/聚合结果/身份与许可。私有checkpoint和原始证据用本机索引定位，GitHub不含原始训练/隐藏测试/权重/凭据。首次服务版本没有此前部署服务版本：回滚应表述为停服并恢复已验收代码/配置/训练制品，不能虚构旧服务可用。

给出逐项判定、精确文档位置与必要修改，按现行五次规则提建议事件但不维护共享台账。交付实际AI报告、handoff、精确commit、私有证据索引；与独立R1技术终验一起由S1接纳。

实际运行源码为PR35 main `aaab0171246feaf307ad2c626108e94383e438d9`；审阅[实测报告](../../reports/S1_P07_G6_SERVICE_R1.md)、[复现说明](../../docs/19_REPRODUCTION_AND_DELIVERY.md)、README与最终材料入口。独立推导实际单位转换/无需工具/三决策轨迹的结论，保留API完成与任务完成的区别；本轮语义观察不改写G5正式分母。

仅提交 `reports/reviews/P07_G6_FINAL_Q1_R1.md` 与 `coordination/handoffs/P07-g6-final-q1-r1.md`；私有索引绑定实际审计证据，不复制原始训练或隐藏测试内容。
