# P04-QWEN-MODEL-R1｜固定模型接口独立CPU审查

状态：PLANNED，尚未派发。等待 E1 的完整候选、原始证据及原生终态；精确 candidate/code_base、完整授权和交接 seal 均待 S0 接收后填入。不审变化中的候选，不提前运行下述独立消费。

沿用原独立 R1 App 任务和隔离 worktree，gpt-6-astra/max；拟用 `codex/review-p04-qwen-model-r1` 和新私有 scope `review-p04-qwen-model-r1`，禁止 sub-agent。先保存届时完整授权中的 AGENTS/GOAL/PROTOCOL、REVIEW_POLICY/REVIEW_FAILURES、RESOURCE_LOCK、ADR-0027、本任务、[E1任务](P04_QWEN_MODEL_CPU.md)、[固定metadata](../../configs/qwen-models.v1.json)和S0完整交接报告，再切换到精确候选。原审查SHA、全部旧FAIL/PASS、私有封存、根identity和未公开f708保持；不合入新main或把f708加入公开祖先。

仅新增 `reports/review/P04-qwen-model-r1/` 和 `coordination/handoffs/P04-qwen-model-review-r1.md`。完整候选只读，不改被审生产/测试/配置、依赖/CI或S0协调文件，不替E1修复后给原候选签通过。发现阻断先交最小证据，仍对精确原候选给出整包结论。

独立核验以下边界：

1. 完整diff只在E1授权路径，原公共代码/配置保持。新配置必须精确为 `b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145`，42成员输入manifest为 `41aadaa79eac7467c7ef2b7c39a0524ec894d1b0e9c616d7a6ab303d05e33cc5`。model ID/revision/文件集合与S0固定来源一致，不出现任意模型/配置/源码/参数的跳过选项。
2. 模型根、固定文件、header/index/offset/shape/dtype、重复tensor和全文件hash的顺序正确，错误在框架导入/loader之前拒绝。原20文件、9库metadata及固定源码的实物独立核对；原字节与header核对无需tensor解码。symlink/路径逃逸、额外model文件、重复JSON键、非有限数、bool/float整数替代、自定义模型/架构/量化和shadow import有有效反例。
3. 311序列化BF16 tensor和sanitize后的预期310底座叶明确区分，只有`lm_head.weight`按固定源码移除。56个LoRA目标的底座名称映射、112个A/B的shape/FP32/scale2/rank8/dropout0逐一核对；不能用原文件数量或示例keys代替完整集合。S0的原字节hash和计数是输入，R1按实际header及源码自行核对。
4. 默认import/文件验证为纯CPU，不构造tokenizer。真实loader实现只在当前真实共享物理gpu0租约、文件/版本/源码/来源确认后导入MLX，使用固定本地BF16与strict eager加载，无远端回退/模型配置覆盖。原租约属于调用方并覆盖模型驻留；本包不新增进程/训练循环或释放调用方锁。实际模型路径本轮NOT_RUN，模拟路径必须清楚标记。
5. 参数身份使用实际dtype原字节，正确区分BF16原字节和FP32转换结果，按完整name/shape/dtype/内容绑定；宿主复制有界。装配/重载只允许固定A/B，严格检查缺失/额外/错shape/dtype/hash，复核实际A/B和全部冻结底座。仅上游`strict=False`成功返回不足以证明严格重载；错误文件、底座更改、未知scale/targets/adapter配置均拒绝。
6. metadata的`is_run_authorization=false`与后续S0运行任务/配置/物理租约职责明确。CPU技术接口存在不等于模型已加载、容量通过或具备正式训练结果。原model sampling默认值与后续greedy配置不混淆，双EOS和pad来自固定文件；新模块不编码、生成、评分或选择checkpoint。

仅现有CPU环境、原创小fixture/模拟对象和必要少量自有CPU进程；独立实际文件验证最多一轮两模型，优先用新安装target。0框架/模型/tensor值解码/LoRA实际装配/adapter实际重载/forward/优化/生成/GPU/真实tokenizer/数据build/下载/新环境。新增制品≤1GiB、不复制大权重，proof出处不扩大私有读取权限。默认环境缺少MLX时拒绝为预期边界，不能为获得真实加载结果追加安装或GPU运行。

核对E1实际三归档的成员、源载荷、metadata/entry points/LICENSE/RECORD及构建源码时点；可直接使用绑定的默认wheel，一次离线`--no-deps`安装到R1新target，外部cwd核对纯导入/拒绝及固定文件验证来自安装目录。新归档构建0，除非独立发现具体归档缺陷后由S0调整范围。只跑本次相关CPU和独立反例、ruff、契约、公开扫描；无关历史HF/数据/toy组不重复跑，重复用例不累加成独立计数。

保留实际argv/UTC/exit/原始stdout/stderr、源码/consumer时点、所有失败和最终seal。给出精确candidate的PASS/FAIL/BLOCKED与P0/P1/P2；只提交本轮审查目录和handoff，review直接以该candidate为parent。普通推送、原生回报完整candidate/review/tree/parents/封存后结束；普通回报省略model/thinking。PASS仍需S0整合/最终CI/main，真实模型与容量另审；同问题第五次规则由S0按正式台账执行。
