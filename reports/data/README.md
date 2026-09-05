# P02 严格来源审计与数据流水线

本包为 D1 的 **pipeline/自动审计交付**。来源适配尚待 S0 发布独立审查后的规则；kris 的人工抽查未进行，P02/G-DATA 不得标记 VERIFIED。当前真实 ToolACE 在未适配的冻结 v1 下没有可训练样本。生产工具不会因数据转换获得执行注册或权限。

## 来源与许可

主来源为 [Team-ACE/ToolACE](https://huggingface.co/datasets/Team-ACE/ToolACE/tree/6bda777c88d21e5a204703c1ee45597a8fa4f734)，revision `6bda777c88d21e5a204703c1ee45597a8fa4f734`。官方 API 返回公开、非 gated；下载无需凭据或接受额外访问条款。数据卡 YAML 声明 Apache-2.0，仓库树没有单独 LICENSE；保留其声明而不把第三方数据改授 MIT。署名：Team-ACE，*ToolACE: Winning the Points of LLM Function Calling*（2024，[论文](https://arxiv.org/abs/2409.00920)）。公开目录只有原创代码/测试、文件 hash、下载方法和去敏统计；原始数据及转换结果均留私有目录。xLAM 未访问，为可选来源。

源文件精确大小/hash 见 [`toolace-source.v1.json`](../../data/manifests/toolace-source.v1.json)。Tokenizer 为官方 [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)，仅下载 tokenizer.json、tokenizer_config.json、LICENSE；revision、文件/hash、template hash 与 non-thinking 绑定在 [`qwen-source.v1.json`](../../data/manifests/qwen-source.v1.json)。没有模型权重、Torch、MLX、GPU 或模型运行。

## 实施边界与顺序

首次先检查真实前 32 条记录（142 个工具出现次数），后补查其他来源格式，再实现转换。原始文件共 11,300 条。源列表里的工具声明属于数据，不能运行其函数、链接或指令。

1. 下载器只允许上述官方仓库及必要文件，先查精确 revision 的官方 API：gated/private 必须明确为 false、许可必须匹配。文件流有 byte cap，下载后复核大小/SHA-256。发现已有文件不一致时失败；不覆盖它。访问时间放在私有 access.json，不参与样本 ID。
2. `extract_tools` 仅解析经实审确认的 JSON-list 标记；其他格式隔离。安全调用语法为 `[exact_name(parameter=JSON, ...), ...]`，保持调用顺序。无 eval/exec/AST 执行、类型强转、默认实参填充、函数名称映射。单引号/Python 表达式、重复键、无穷值、歧义名称和未支持调用格式均拒绝。
3. 用原始参数 schema 调用冻结 P00 验证器；探针的固定 metadata 只用于参数诊断，永不输出为工具或训练样本。正式工具必须已有明确、合法的 side_effect_class/tool_version/timeout_ms。`dict`/`int`/`float`、无界 string/array、未闭合 object、pattern/default 等不被静默改写。所有当前真实工具均隔离。
4. 有明确可解析工具调用的 assistant 决策才有候选标签。自然语言回复没有足够的原始 action-kind 真值，保留 `action_kind_unlabelled`，不猜 final/clarify/refuse。每个合法候选只包含目标 turn 之前的消息；历史工具结果按唯一名称匹配 pending call，歧义会污染后续前缀并拒收。原始多轮记录始终保持同组。
5. 全部来源记录先建立连通组：来源内容 hash、每个工具名称、剥离 description/default 注释后的参数 schema、业务请求的显式词法模板（NFKC、大小写、引号槽位、URL、数字）及可识别近重复。近重复为固定 SHA-256 MinHash 64 个值/16×4 分带候选检索，再精确检查词三元组 Jaccard ≥0.85。它不保证语义近重复的完整召回。工具/schema 的共享边采用保守连通，因此可能形成大组。
6. group ID 是排序去重来源 hash 的 hash。种子17；10% group hash 候选留作 ood_test，剩余以独立 hash 按80/10/10划分；不拆大组追求条数比例。工具/schema/template/source/group 交集校验独立执行。所有当前来源划分只是隔离数据的暂定分组，正式四个 split 文件均为空。
7. 转换后同 messages/tools/action 的完全重复只保留一例，所有拒收保留 lineage。增强 API 只接收已分组的父样本并继承 source/group/split；本包未生成增强。时间元数据不参与规范化 ID；对话中的日期仍作为有意义输入保留。
8. 长度策略为完整保留或完整拒收，bucket=2048/4096/8192，超过8192剔除；这是 P02 探索参数，不修改冻结生成配置。没有 tokenizer 证据的候选也不进入训练。没有截断 schema/答案。模型输入仅投影 messages/tools；这无法自动发现自然语言里的语义泄漏，必须由 kris/R1 核查。

每个 assistant 决策写入 `source-index.jsonl` 的 turn_index、全部拒收原因及 normalized_hash（未生成则 null）。`assignments.jsonl` 记录完整来源 hash→group→split；候选 `lineage.jsonl` 保留 normalized_hash、augmentation_parent、长度、排除原因和 training_run=null。相同原记录多次出现保留其索引，避免从原始分母消失。

## 本机复现

所有原始/处理产物放 `.toolalign-local/`（Git 忽略）。首轮数据、环境、tokenizer 预算5GiB；源文件上限512MiB，实际磁盘用量见审计报告。公开核心包不新增依赖；tokenizer 只在私有探索环境使用 [`tokenizer-environment.txt`](tokenizer-environment.txt) 固定版本。当前 Python 3.14.7。

```bash
uv sync --locked --python 3.14
uv run --locked python -m toolalign.data --help
uv run --locked python -m toolalign.data fetch --manifest data/manifests/toolace-source.v1.json --destination .toolalign-local/source/toolace --ca-file /etc/ssl/cert.pem
uv run --locked python -m toolalign.data fetch --manifest data/manifests/qwen-source.v1.json --destination .toolalign-local/source/qwen --ca-file /etc/ssl/cert.pem
uv venv .toolalign-local/tokenizer-venv --python 3.14
uv pip install --python .toolalign-local/tokenizer-venv/bin/python -r reports/data/tokenizer-environment.txt
```

`--ca-file` 仅为本机 Python 证书链路径选择，仍启用 TLS 验证；在默认信任链可用的机器可省略。本机首次默认 urllib 证书检查失败，改用系统 CA 后成功；未禁用证书检查。

保存如下配置为私有 `config-a.json`；实际执行参数中的相对路径均以仓库根目录为基准。第二次仅把 `output_dir` 改为 `.toolalign-local/build-b`，保存 `config-b.json`。输出目录必须为空，不能复制第一次产物冒充重建。

```json
{
  "source_manifest": "data/manifests/toolace-source.v1.json",
  "source_dir": ".toolalign-local/source/toolace",
  "output_dir": ".toolalign-local/build-a",
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
PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m toolalign.data build --config .toolalign-local/config-a.json
PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m toolalign.data build --config .toolalign-local/config-b.json
uv run --locked python -m toolalign.data compare .toolalign-local/build-a/manifest.json .toolalign-local/build-b/manifest.json
uv run --locked pytest -q tests/data/
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked python scripts/check_contract_freeze.py
uv run --locked python scripts/check_public_content.py
```

不同交付提交的 Git SHA 会影响数据集级 manifest（预期行为）；module hashes 和每项产物 hash 可用于比较同一实现。`compare` 同时重新读取并核验两边的实际产物，拒绝路径逃逸/内容改动；不仅比较 manifest 自述。

## Token 长度与人工门

官方 tokenizer 文件与 template 逐字节校验；仅用 tokenizers 0.22.2 和 Jinja2 3.1.6 的不可变沙箱渲染已核对的官方模板，enable_thinking=false。token count 不添加 tokenizer special tokens，模板本身包含控制符。原始表示保留原始 system、历史文本及 tool observations，目标 assistant 文本单独加结束标记计数；不把其混作规范化后的训练长度。

schema 占比为移除 system 中原始工具 JSON span 前后的 prompt token 数差值（边际贡献），避免把 BPE 分段 token 数误当可加和。只在能定位 span 的决策上计算 schema/prompt/completion 占比；完整长度分母仍覆盖全部可渲染 assistant 决策。自然语言类别/工具可执行性/正确性没有人工真值，均不以模型自评补出。

`human-review/index.html` 是离线、转义源文本并禁用脚本/外部资源的查看页；CSV 保持 review 结果空白。按语言书写体系、工具格式、多轮及拒收类型分层覆盖后，以固定 hash 补足100条。问题分类包括格式、schema、副作用、action kind、参数语义、缺真值、泄漏、分组、长度、许可。样本只供质量审查；不能用于模型选择或偏好挖掘。

G-DATA 仍缺 kris 实际抽查、S0 已批准的来源适配和正式可训练 manifest；P05 偏好人工阈值不用于本包验收。训练、BFCL、正式评测、推理部署和公网发布均 NOT_RUN。

## 后续 CPU 衔接检查：规范化训练长度

严格检查点的原始来源统计与14项产物保持原样。后续 `normalized()` 改用 `qwen3_non_thinking_concat_one_eos_v1`：先按本包 JSONL 的对象键序固定序列化、渲染官方 non-thinking prompt，再整体 tokenize(prompt + completion)，检查 prompt IDs 完整保留，最后追加一个 `eos_token_id`，不追加末尾换行。若前缀发生 BPE 合并则记 `prompt_completion_boundary_changed`，完整排除并保留计数。对 completion 中已有的文字/控制 token不做偷偷删除；包括用户要求字面 EOS 的原创边界 fixture，仍只额外追加一个 EOS。

长度结果带 `length_basis`、`sequence_hash`、EOS 和稳定前缀标识，供后续训练器绑定实际序列。工具调用 completion 的 JSON 使用本包固定序列化（非 ASCII 保留、稳定参数键序）；T1 的编码器接收给定 completion 字符串，比较须使用同一字符串，不能把不同 JSON 空白排版当同一序列。`training_sequence()` 可提供准确的 prompt/completion 字符串和 IDs；实际训练集仍待 S0 的来源政策和训练方绑定。原始 `raw_decision()` 仍是隔离表示的统计，不用作规范化训练窗口依据。

独立 CPU 证据使用16个原创合法v1 fixtures（工具调用、并行调用/observation、多轮、无工具、clarify/refuse、中文/Unicode/特殊字符、换行与 EOS 边界），参考环境仅从本地已 pin tokenizer 加载 `AutoTokenizer`，`local_files_only=True`、`trust_remote_code=False`，离线且不导入 Torch/MLX。未调用、复制或运行 T1 的 samples/execution 实现；其已提交编码政策仅作只读口径参考。

```bash
uv venv .toolalign-local/tokenizer-reference-venv --python 3.14
uv pip install --python .toolalign-local/tokenizer-reference-venv/bin/python -r reports/data/tokenizer-reference-environment.txt
uv pip install --python .toolalign-local/tokenizer-venv/bin/python -r reports/data/tokenizer-audit-environment.txt
PYTHONPATH=src .toolalign-local/tokenizer-reference-venv/bin/python tests/data/tokenizer_crosscheck.py --engine hf --output .toolalign-local/hf-tokenizer-check.json
PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python tests/data/tokenizer_crosscheck.py --engine local --output .toolalign-local/local-tokenizer-check.json
uv run --locked python tests/data/compare_tokenizers.py --local .toolalign-local/local-tokenizer-check.json --reference .toolalign-local/hf-tokenizer-check.json --output .toolalign-local/tokenizer-comparison.json
TOOLALIGN_TOKENIZER_DIR=.toolalign-local/verified-source/qwen PYTHONPATH=src .toolalign-local/tokenizer-venv/bin/python -m pytest -q tests/data/
```

对照记录含具体字符串/全部 token IDs；公开 golden 是原创 fixtures 的参考 hash，不包含上游数据。核心环境没有可选 tokenizer/本地路径时，16项真实 tokenizer 测试明确 skip；须另运行上面的私有 CPU 命令才能声称这些测试通过。版本间一致性只证明所列 fixtures，不声称所有文本上的普遍等价。详见后续 CPU 长度衔接报告与交接增补。
