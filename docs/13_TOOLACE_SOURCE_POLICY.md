# 13｜ToolACE 历史监督数据适配规则

政策：`toolalign.source_toolace.v1`；配置为 `configs/source_toolace.v1.json`。本规则须经独立 R1 审查、S0 合并与 main 验证后由 D1 使用；草案分支不构成提前执行授权。冻结 `toolalign.contracts.v1` 的 schema、validator、Protocol 和运行协议字节保持不变。

## 证据与范围

来源为 [官方 ToolACE 仓库](https://huggingface.co/datasets/Team-ACE/ToolACE)，固定 revision `6bda777c88d21e5a204703c1ee45597a8fa4f734`。D1 已下载并哈希 `data.json`：37,154,735 bytes、11,300 条原记录；SHA-256 见配置。来源卡标记 Apache-2.0，API 未 gated；仍保留原始声明、署名与转换记录，不能将其改标原创 MIT。

转换器实现前，D1 检查了前 32 条真实记录、142 个工具：全部缺少项目副作用字段，全部以 `dict` 表示参数根对象；还存在缺少闭合/长度约束、`int`/`float`、默认值、空格或大写工具名。S0 阅读了代表原记录并核对官方来源卡。上述小批数不是全量兼容率；全量统计由 P02 输出。

本导入器产出**历史监督记录**。ToolACE 的工具描述和历史 observation 不提供真实外部 API 的执行实现，也不能证明那些 API 是只读的。原始副作用信息保持 `unknown`；潜在写入描述不能变成 `read_only` 事实声明。

## 项目执行政策与来源事实分开

Wire tool 的 `side_effect_class=sandbox_only` 是本项目给这些历史工具设定的**最宽许可范围**：未来只有另外实现并审查过的本地隔离 fixture 才可能执行；它不是“原始 API 已沙箱化”或“有真实执行器”的声明。当前 dataset manifest 必须写 `record_scope=historical_supervision_only`、`execution_binding=none`、原始副作用 `unknown`，并绑定本政策 hash。

所有导入工具使用 `ta_` 名称空间。P02 不创建注册表/执行实现，不请求历史工具 URL，不重放实际业务操作。P03/P07 的 registry 必须只接受显式登记的原创本地实现和精确 schema/version/hash；不能从数据工具描述或 `sandbox_only` 字段自动授予执行权。未绑定的 ToolACE 工具调用必须作为 unknown/unregistered 拒绝。P03 的独立验收必须加入该边界测试。

`timeout_ms=1000` 同样是未绑定 fixture 的项目上限字段，不是来源 API 的实测延迟。未来若确实引入某个可执行 fixture，必须另登记身份与预算，不能继承历史 observation 为真实成功证据。

## 允许的确定性转换

1. 只将明确观察到的类型别名 `dict → object`、`int → integer`、`float → number` 规范化。实际参数值不做字符串转数值、布尔转整数等强制转换。缺类型、冲突类型、union、refs/组合/正则及其他未知 schema 关键词继续隔离。
2. 参数名和 required 集合保持不变；只读外层冗余 `required=null` 可移出 wire 并保留源信息。不能用它覆盖 `parameters.required`；非空外层 required 的含义不明确时隔离。
3. 缺少的 `additionalProperties` 明确补为 false，string 的 maxLength 补为 16384，array 的 maxItems 补为 1000。这是**项目主动收窄**，不是无损恢复来源约束。已有更严格有效边界保留；来源明确允许开放对象、更宽边界或未提供 array items 时隔离并计数，不静默截小。所有历史/目标调用必须通过收窄后的验证；出现额外参数、越界值或不一致时隔离整条来源记录。
4. `default` 只当来源 annotation：保留原始路径、有限 JSON 值及 hash，并把默认值信息保留在对应参数 description 中；不得自动补入调用、改变 required 或把省略参数改成显式值。默认值须符合该节点类型与项目边界；冲突、超限或不可解释值隔离。除 default 与上文明确列出的冗余外层字段，不允许通过“移入 metadata”删除未知 schema 约束。
5. 工具名称为 `ta_<slug>_<hash12>`：slug 由原始名称按 ASCII 小写字母/数字保留、其他连续字符替换为下划线并去除两端下划线，截至 47 字符，空 slug 用 `tool`；hash12 为完整原始工具对象 canonical_hash 的前 12 位。必须保存原始名称、完整原始工具 hash、规范化名称的可逆映射，并检查完整 hash 冲突；冲突时失败，不能覆盖。描述保留原名以便解释。历史与目标调用、tool observation 身份一同重建关联，不能只改工具声明。
6. description、默认值说明和原名注记合并后仍须满足 wire 长度边界；不能截断后伪装为完整工具。原始 system 中的函数列表与输出格式要求转换为统一 ToolAlign 输入模板时，保存原文 hash 和精确变更规则，不能留下互相矛盾的旧输出格式要求，也不能删除用户任务关键内容。

每次转换保存 `source_record_hash → raw_tool_hash → policy_hash → normalized_hash`、字段级修改理由和计数；保留所有原始记录/工具的私有副本。policy_hash 是配置文件原始 UTF-8 字节的 SHA-256，工具对象 hash 使用冻结 canonical_hash。分组必须同时参考来源身份和规范化语义，不能利用改名或默认值文本绕过去重。改写留原组；相同原始输入与政策必须可真实重建相同输出。

## 继续拒绝与验收

不是所有数据都必须变成有效 example。消息前缀无法可靠关联、输出无法安全解析、目标真值不明、缺少 required 参数、未知调用名、未知约束、超范围类型/值和原始 parse 错误均按理由隔离。禁止 eval/exec 或执行源字符串；安全解析也必须限制深度、大小、重复键和有限值。不用模型补答案或推断外部调用成功。

P02 测试必须覆盖：别名正负例；主动收窄导致的整记录排除；默认值保留但未填参；工具/调用一致改名；hash 冲突拒绝；恶意 schema 无法经 annotation 绕过；历史 observation 不被当作当前执行；私有源记录可追溯；两次真实重建一致。人工审阅材料明确显示转换前后、项目新增约束和未绑定执行状态。没有 kris 真实质量抽查，G-DATA 仍不能通过。

本政策通过只允许 D1 实现并验证适配器，不等于 P02 数据已合格，也不解除 P03/P04 等后续阶段的独立验收。
