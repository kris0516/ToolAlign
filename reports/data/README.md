# P02 ToolACE 数据转换与审计

本目录交付可复现的 CPU 数据流程与自动证据。S0 已正式发布 `toolalign.source_toolace.v1`；实现使用精确政策字节并保持冻结 `toolalign.contracts.v1`。最新结果见 [政策转换报告](P02_POLICY_BUILD.md) 与 [机器证据](P02_POLICY_BUILD.json)。**人工质量审查与独立 R1 验收尚待完成，P02/G-DATA 未 VERIFIED。** 历史的零样本严格检查点与 tokenizer 对照证据继续保留。

## 来源、授权与许可

主来源为 [Team-ACE/ToolACE](https://huggingface.co/datasets/Team-ACE/ToolACE/tree/6bda777c88d21e5a204703c1ee45597a8fa4f734)，固定 revision `6bda777c88d21e5a204703c1ee45597a8fa4f734`。官方 API 记录为公开、非 gated，README 声明 Apache-2.0，原树没有单独 LICENSE。署名 Team-ACE，*ToolACE: Winning the Points of LLM Function Calling*（2024，[论文](https://arxiv.org/abs/2409.00920)）。源文件为37,154,735 bytes、11,300条记录；原始字节/hash见 [source manifest](../../data/manifests/toolace-source.v1.json)。第三方数据保持其来源许可；公开仓库仅含原创实现/小 fixtures、元数据与统计，原始数据和转换产物均存私有目录。xLAM 未访问。

来源政策经 PR #3 独立 R1 PASS、S0 合并和 main 验证后授权；本 worker 合入精确 main `a6c8dd3c78b3674a242b4faacbb175f7b7c98303`，整合提交 `95d4c4f174c4e607de87765269dbcf25ac95cff3`。详见 [S0 政策说明](../../docs/13_TOOLACE_SOURCE_POLICY.md)。政策文件原始 UTF-8 SHA-256 为 `b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7`；更改政策字节或来源身份会拒绝构建。

Tokenizer 为官方 [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)，只下载 tokenizer.json、tokenizer_config.json、LICENSE。固定 revision、template hash、non-thinking 与包版本见 [tokenizer manifest](../../data/manifests/qwen-source.v1.json)。本包没有加载模型、Torch/MLX、执行 GPU 作业或产生模型服务。

## 数据规则与限制

1. 下载器仅接受固定官方来源和必要文件，复核 gated/private/license/revision、byte cap 和 SHA-256，不覆盖已存在的不一致文件。访问时间保存在私有 access.json，不参与样本 ID。
2. 仅导入经过实审的 JSON-list system 格式；其它格式隔离。调用解析为有界 `[exact_name(parameter=JSON, ...), ...]` 字面语法，拒绝单引号/Python 表达式、重复键、无穷值、过深值、歧义名称与未知格式。解析器不执行来源字符串。
3. 显式政策允许 `dict→object`、`int→integer`、`float→number`；缺少的对象闭合、字符串16384/数组1000上限属于项目收窄。既有有效更严边界保留；显式开放对象、更宽边界、缺失 items、未知类型/关键词继续隔离。原参数值不强转；任一历史或目标调用不满足收窄后的 schema，排除整条来源记录。
4. default 须符合该节点类型/约束，仅保存为带路径、类型、原值/hash 的 annotation，并进入对应参数 description；不填参、不改 required。未知约束不能借 annotation 删除。描述合并后超限时整工具拒收。外层 required 仅允许缺省或 null，不能覆盖 parameters.required。
5. 工具名确定性映射为 `ta_<ASCII slug 47>_<完整原工具 hash 前12位>`，检查完整 hash 冲突。声明、历史/目标调用与 observation 同时重建关联。所有工具原副作用事实为 unknown；wire sandbox_only/1000ms 是项目上限，manifest 写明 `historical_supervision_only`、`execution_binding=none`。这些工具没有真实执行实现，不能从数据导入 registry；历史 observation 不是本机执行成功证据。
6. System 仅替换已审计的源 boilerplate、函数列表和输出格式；保留确切日期/时间上下文与已知声明语法说明。未识别额外文本隔离。记录原文/转换后 hash、JSON span、版本化规则与保留上下文，避免保留矛盾输出格式或删除关键用户内容。
7. 每个可解析的 assistant 工具调用产生一个目标前缀；输入只包含目标 turn 之前的消息。自然语言没有明确 action-kind 真值，记 `action_kind_unlabelled`，不猜 final/clarify/refuse。源调用 parse 错误、不可可靠匹配的 observation 和超政策参数均完整保留排除理由。
8. 原始分组保持：source/tool/schema/词法任务模板及 MinHash64、16×4 LSH 候选、词三元组 Jaccard≥0.85连通。来源分组为3,517个，最大组6,716个不同来源；不拆组追求80/10/10条数比例。种子17，另以 group hash 留10% OOD 候选；LSH不保证所有语义近重复都被发现。
9. 另检查规范化 schema 语义键，忽略 annotation、排序 required/enum 等集合，但保留真实参数名。规范化语义跨多个旧组时隔离所有相关来源，原 group/split 不变；最终集再次验证原始键和规范化键的交集。此检查是结构语义规则，不是完整逻辑等价求解器。
10. 转换后的完全重复保留一例。全部候选测实际训练长度，bucket=2048/4096/8192；越界、无法测量或不稳定 token 前缀完整排除，无截断。长度参数属于 P02 数据探索；后续训练须绑定具体 manifest 与其模型窗口。

`source-index.jsonl` 包含每个来源/assistant决策的排除理由、policy hash、工具原 hash、系统变更、调用参数 hash 与历史 observation 关联。`tool-lineage.jsonl` 保存去重的完整原工具、转换工具、字段变化/理由、typed defaults 和可逆名称映射。`assignments.jsonl` 保存来源→旧组→split。候选 `lineage.jsonl` 连接来源/原工具/政策/规范化 hash、目标 turn、group/split、长度/序列 hash、exclusion reason、augmentation_parent 与 training_run=null。`normalized-group-conflicts.jsonl` 与 `tool-quarantine.jsonl` 分别保留分组冲突与工具拒收。

工具原 schema 的严格诊断与当前政策拒收分开报告；字段变化同时给去重工具、工具出现次数、来源记录、assistant决策四种分母。转换成功的工具可能出现在因其它原因隔离的来源记录中，不能将其数量当作最终工具数。

## 复现入口

所有构建输出、原始日志及探索环境使用 Git 忽略的 `.toolalign-local/`，预算总计5GiB。核心环境不安装 ML 后端；私有 tokenizer 环境使用公开的精确依赖版本：

```bash
uv sync --locked --python 3.14
uv run --locked python -m toolalign.data --help
uv run --locked python -m toolalign.data fetch --manifest data/manifests/toolace-source.v1.json --destination .toolalign-local/source/toolace --ca-file /etc/ssl/cert.pem
uv run --locked python -m toolalign.data fetch --manifest data/manifests/qwen-source.v1.json --destination .toolalign-local/source/qwen --ca-file /etc/ssl/cert.pem
uv venv .toolalign-local/tokenizer-venv --python 3.14
uv pip install --python .toolalign-local/tokenizer-venv/bin/python -r reports/data/tokenizer-environment.txt
uv pip install --python .toolalign-local/tokenizer-venv/bin/python -r reports/data/tokenizer-audit-environment.txt
```

`--ca-file` 使用本机系统 CA，保持 TLS 验证；默认信任链正常时可省略。首次实际下载的默认 Python 根链失败和之后的成功记录保存在严格检查点证据中。

保存下面配置为 `.toolalign-local/config-policy-a.json`。第二份配置仅更改 output_dir 为 `.toolalign-local/policy-b`，存为 config-policy-b.json。两次运行必须各自指向空目录；省略 source_policy 可复现旧严格模式，但不会导入本次已批准的适配。

```json
{
  "source_manifest": "data/manifests/toolace-source.v1.json",
  "source_dir": ".toolalign-local/source/toolace",
  "source_policy": "configs/source_toolace.v1.json",
  "output_dir": ".toolalign-local/policy-a",
  "seed": 17,
  "ood_fraction": 0.1,
  "length_buckets": [2048, 4096, 8192],
  "max_tokens": 8192,
  "review_sample_records": 100,
  "tokenizer_manifest": "data/manifests/qwen-source.v1.json",
  "tokenizer_dir": ".toolalign-local/source/qwen"
}
```

```bash
PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m toolalign.data build --config .toolalign-local/config-policy-a.json
PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m toolalign.data build --config .toolalign-local/config-policy-b.json
uv run --locked python -m toolalign.data compare .toolalign-local/policy-a/manifest.json .toolalign-local/policy-b/manifest.json
uv run --locked pytest -q
TOOLALIGN_TOKENIZER_DIR=.toolalign-local/source/qwen PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m pytest -q tests/data/
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
uv build --wheel
```

运行精确命令/退出码/log hash 见本次机器证据。不同 Git SHA 会影响 build manifest 的 code_revision；每个模块与产物的 hash 均另列。compare 会重新读取两边真实文件，不只比较 manifest 自述。未升级公共打包修复前，本 worktree 的默认 sdist 构建已发现会包含私有路径；失败 archive 已私有隔离，S0负责公共修复，本包使用显式 wheel 构建。

## 长度口径与人工审阅

规范化训练长度使用 `qwen3_non_thinking_concat_one_eos_v1`：固定 JSONL 对象键序，官方 non-thinking 模板渲染，整体 tokenize(prompt+completion)，检查 prompt IDs 保持前缀，再额外追加一个 EOS ID、不加尾换行。长度记录含 basis、sequence hash、EOS 与稳定前缀标识。原始 `raw_decision()` 的隔离表示长度单独统计；不能把它当作训练长度。Schema 为带/不带声明模板的 prompt token 边际差。

此前16个原创 fixture 对照本地 tokenizers 与 HF AutoTokenizer 的模板字符串和 token IDs，包括两个不稳定 BPE 前缀拒收；详见 [对照报告](P02_TOKENIZER_ALIGNMENT.md)。仅证明实际覆盖案例，不声称所有文本普遍等价。完整对照复现命令在 [机器记录](P02_TOKENIZER_ALIGNMENT.json)。核心环境缺少真实 tokenizer 依赖/路径时的17项 skip不能当作执行通过；本次真实CPU回归单独登记。

本次 `human-review/index.html` 与 samples.jsonl **仅抽取最终有效 examples**，按 split、语言、工具数、并行调用、多决策、历史 observation、默认值、日期上下文、转换规则和长度桶分层，再稳定 hash 补足100个不同来源。每条展示原始记录、完整有效 example、工具逐字段变化、政策新增限制、原始/规范化关联。源文本经过 HTML 转义，页面禁用脚本和外部资源。另有 exclusion-samples.jsonl，排除代表不混入有效样本池。

请将空白 review.csv 复制到单独的私有提交目录再填写 reviewer、真实UTC时间、pass/fail/unknown、问题类别与备注；一个 verdict 覆盖该来源展示的所有有效决策。原始构建包作为冻结证据保留。提交时附原始 build manifest hash 与 review样本hash，便于 S0 对照。模型抽查不替代 kris；没有实际人工记录时 mislabel_rate=null、accepted_examples_reviewed=0、G-DATA仍待审。本包没有执行P05偏好审计、训练、BFCL、正式评测或服务部署。
