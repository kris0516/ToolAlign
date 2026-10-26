# P05 G4｜train 任务与决策偏好 CPU 实现

状态：READY；owner D1；base `1267d1a33dfb08bfd9800b80ea97315730748952`。工作分支 `codex/d1-p05-g4-preference-r1`，复用D1现有隔离worktree。S1提交本任务后的精确授权commit由派发消息给出。

目标：实现[共享协议](P05_G4_PROTOCOL.md)中的原创train-only任务构建、来源/分组审计、保守首分歧偏好抽取和Q1审阅材料；本包不生成真实模型候选、不训练。

允许修改：新增 `src/toolalign/data/preferences/`、对应 `tests/data/preferences/` 和小型原创fixtures；`reports/P05_G4_PREFERENCE_CPU.md`、`coordination/handoffs/P05-g4-preference-r1.md`。新增P05内部manifest格式和CLI放在该包中。若catalog或oracle能力不足，先报告具体任务与缺口，不在本包静默改公共工具或真值规则。

禁止修改：contracts、model_io、P02 pipeline/原数据和split、P03公开开发fixture、工具registry/executor/oracle、CUDA/训练代码与依赖、共享状态和T1范围。不得建立sub-agent或新聊天；沿用gpt-6-astra/max。

任务构建要求：最多128个新原创train任务，覆盖工具混淆、参数对象/日期/版本、无需工具、信息缺失、多步依赖、有限故障恢复等实际可判类别。不要求凑满；同一模板实体变体显式标family及共同group。复用固定工具实现，不把原10个开发例换ID塞入train，不从ToolACE猜造可执行真值。独立编写答案/允许策略后用真实CPU executor验证正向和有区分力的反例，不能用同一被测函数充当唯一oracle。保存全部合法替代策略，且错误答案/错误对象即使tool正常返回也失败。

在生成任何模型候选前交付固定tasks.json/manifest、准确类别/来源/group数及与P02和P03开发资料的重叠审计。P03开发资料是公开诊断，身份不变；同工具/schema共享须明示，不能伪报schema隔离。若正式P02 split存在可识别同组冲突，隔离新任务并报告，不改P02。未来G5同组只能作为seen-group诊断，正式held-out必须另有隔离组。新任务原始材料在私有目录，公开仅生成方法/小型测试/统计。

偏好抽取：读取T1协议候选，验证task/model/prompt/trace身份及每个decision_inputs hash；只取成功/失败的共享完整前缀首次语义分歧。成功轨迹不足、两边合法/等价、未来才失败、unknown、纯格式/长度/超时/基础设施失败均有明确处置，不硬配。比较实际合法路径剩余动作，不能用JSON文本差异判负；如有限oracle不能证明某动作不合法，记unknown并排除。每任务按candidate ID固定顺序至多1对。

输出冻结preference.v1及lineage/dispositions/summary，保留chosen/rejected各自真实生成参数和决策位置；格式字段generation_parameters绑定chosen，sidecar保存双方。提供Q1预注册分层抽样和可读审阅材料，抽样数min(total,max(100,ceil(.1total)))，未知计误标，严格>5%阻断。不能把自动验证表填为Q1通过。

CPU验收使用显式标synthetic/scripted的少量正/反轨迹测试数据路径：合法替代tie、JSON/key/call_id差异、正确第一步后错误最终答案、同prefix恢复选择错误、无工具误调用、未来/混合trace、非train与泄漏拒绝、分母不删失败。真实模型候选和正式偏好质量仍NOT_RUN。交付精确commit与命令/退出码/证据索引，S1回读后安排R1和Q1独立审核。
