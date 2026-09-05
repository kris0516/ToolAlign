# P02 CPU tokenizer / 训练序列衔接

状态：**此项 CPU 衔接已实测；P02 整包及人工 G-DATA 仍待前提。** 主修正提交 `7be53fae63013aa5485321b92da9087da34bda66`；随后 `85ebcd23762068ec24d2c08a3f45f677c024d1ca` 保留合法 tool-call action 伴随正文并加入回归。本轮不采用未获明确 main 验证通知的 ToolACE 新政策，不改公共依赖/契约，不重写旧14项来源产物。

T1 的 `samples.py` / `execution.py` 只读参考提交为 `47c03404bab043e85b417cd8a6d0432dc2f85479`，文件字节 hash 已登记。没有从该实现导入或复制编码实现；独立参考直接调用 HF `AutoTokenizer.apply_chat_template`（字符串与 tokenizing 两个入口）及 tokenizer 编码接口，基于 D1 自建的16个合法原创v1 fixtures。[完整机器证据](P02_TOKENIZER_ALIGNMENT.json) 保存精确命令/退出码/原始日志 hash 与结果。

## 固定环境与输入

| 项目 | D1 被测路径 | HF 独立参考 |
|---|---|---|
| Python | 3.14.7 | 3.14.7 |
| tokenizers | 0.22.2 | 0.23.2 |
| Jinja2 | 3.1.6 | 3.1.6 |
| transformers | 不导入 | 5.16.1 |
| 模型/权重 | 不加载 | 不加载 |

共同 tokenizer 为 Qwen/Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca` 的既有本地必要文件；逐文件 hash / template hash 保持原 lock。HF 以 `local_files_only=True`、`trust_remote_code=False` 加载，设置离线/禁用隐式凭据/遥测，实际 `torch` / `mlx` 均未导入。EOS 为 `<|im_end|>`，ID `151645`。

语料覆盖：单/并行工具调用、单/并行 observation、多轮历史、无工具、clarify/refuse、中文、组合 Unicode/emoji/XML/引号/反斜线、空 system/user、TAB/CRLF、leading LF、字面 EOS、历史 thinking 标签。它们是原创 CPU fixtures，不是 ToolACE/BFCL/最终测试集。

## 发现与修正

- 相同序列化视图上，D1 Jinja+tokenizers0.22.2 与 HF5.16.1+tokenizers0.23.2 的 **prompt字符串、completion字符串、prompt IDs、concat IDs、追加EOS后的全部IDs 16/16一致**。版本相同语义不作普遍等价承诺，只报告这些输入的实测。
- 原 `normalized()` 把 prompt 与 `completion + EOS + newline` 分别计数。14个稳定前缀样本全部多计1 token；两个 leading-LF 样本还存在跨边界BPE合并，分段求和无法识别。
- `leading_newline`：原 prompt 最后 token `271` 在拼接后变成 `1406`，第一处改变位于零起始索引19；`leading_two_newlines` 变成 `1022`，索引20。二者 prompt 末尾原为 `[271,151668,271]`，concat 对应片段分别为 `[271,151668,1406,2307,13]` 与 `[271,151668,1022,2307,13]`。现与 T1 一样拒收 `prompt_completion_boundary_changed`，不会据不稳定边界创建训练 mask 或窗口结论。
- 规范化计数现定义为 `qwen3_non_thinking_concat_one_eos_v1`：整体encode(prompt+completion)，核对prompt token前缀，额外追加恰好一个EOS ID，无额外换行。字面EOS fixture已有EOS被保留，末尾出现两个EOS，其中只有一个为编码器追加；没有暗中去重标签。
- 固定内存与 JSONL 持久化后的对象键序，保证相同例子的实际字符串/IDs可复现。工具调用的伴随正文也被保留。规范化长度返回明确basis及完整训练sequence hash；用于接入训练时仍须绑定同一prompt/completion序列化。

## 实际长度

下表旧值是旧D1分段计数；新值为整体编码+追加EOS的诊断长度。两个拒收行不能当合法训练长度。其余14行 prompt/总长/completion长度均与HF参考完全一致。

| Fixture | 旧总数 | 新总数 | 处理 |
|---|---:|---:|---|
| single_tool | 212 | 211 | 前缀稳定 |
| parallel_tools | 240 | 239 | 前缀稳定 |
| observation | 236 | 235 | 前缀稳定 |
| parallel_observations | 269 | 268 | 前缀稳定 |
| conversation_after_final | 228 | 227 | 前缀稳定 |
| no_tools | 21 | 20 | 前缀稳定 |
| clarification | 202 | 201 | 前缀稳定 |
| refusal | 27 | 26 | 前缀稳定 |
| chinese_specials | 246 | 245 | 前缀稳定 |
| empty_system_and_user | 21 | 20 | 前缀稳定 |
| leading_tab | 28 | 27 | 前缀稳定 |
| leading_newline | 25 | 23 | 拒收 |
| leading_two_newlines | 26 | 24 | 拒收 |
| leading_crlf | 24 | 23 | 前缀稳定 |
| literal_eos | 25 | 24 | 前缀稳定，保留字面EOS |
| history_reasoning_tag | 36 | 35 | 前缀稳定 |

## 验证与保留

最终实现 `85ebcd2` 在私有真实 tokenizer 环境的全仓测试 **143 passed**、退出0，包含16个HF参考fixtures及伴随正文回归；原始日志hash `2fce1a9f4ba0a41fa33316b4a7f9d6a30c782465fc66069a34ca6b11f742d2d2`。相同代码不含tokenizer可选环境时会明确skip这些可选检查，不能把skip当真实tokenizer通过。

逐字段独立比较16/16通过，日志hash `b5fda279bd43624869df38b3db8c19800181698e799e387627fc3f18383b2ed7`；完整参考字符串和所有 token IDs 在私有 `tokenizer-final-hf.json` / `tokenizer-final-local.json`，公开golden只保存原创fixture的精确hash。初始HF收集器将新版BatchEncoding当普通dict处理导致一次断言失败，已改为Mapping；这是收集器接口形状问题，不是分词差异。

两份旧checkpoint再次逐项重读并验证14个artifact hash，共同原 manifest hash仍为 `c3f283fd26598acf7dd7716fb6351a164f7891f12ad3ed9b1a60f2f5c0b2c562`，没有把旧 raw 来源长度换成新训练口径。`raw_decision()` 数值定义不变。无新真实ToolACE转换、模型训练/推理、GPU、BFCL、kris审阅或公网动作。

本机 `.toolalign-local` 389,916 KiB + `.venv` 35,068 KiB，总约415.0MiB，在5GiB内。包版本表与复现命令见 [README衔接段](README.md)。下一个步骤仍是等待 S0 明确的已验证公共基线，再继续有效数据规范化和人工门材料。
