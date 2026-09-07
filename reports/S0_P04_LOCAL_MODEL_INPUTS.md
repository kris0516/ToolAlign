# S0｜既有本地模型文件绑定

2026-09-08，完成后续P04配置准备所需的**只读文件核验**。以main `6c573be0d1af4249a41ba33799dfe8faa5d72bf9`的P01公开记录为起点，核对原真实run manifest和prepared config，再流式核对当前已有20个公开模型文件及20份原下载metadata；没有下载、复制权重、导入框架、反序列化tensor或运行模型。

| 原检查点 | revision | 当前文件数 | 权重文件数／bytes | 原P01模型聚合身份 |
|---|---|---:|---:|---|
| Qwen/Qwen3-0.6B | `c1899de289a04d12100db370d81485cdf75e47ca` | 9 | 1／1,503,300,328 | `c8277aece81bbdb466c899ad37afaf8587a6cba7119f9cdc52dd49b37252eb82` |
| Qwen/Qwen3-1.7B | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | 11 | 2／4,063,515,592 | `c3cc19430177bf7bfd9dcbdd4bd1ef53dbe4deb4463e223a46dac02fd6557aed` |

20份现存文件的全部字节、大小和原下载revision均与原P01记录相符；三份safetensors的hash也匹配原LFS metadata。0.6B原run manifest/config为`fde4390b4641bf2d5e8cbdebfb18265afc584927b7ae9a97c849f5643ae720a9`／`7bc42965803c9dcea7b80c802e8fc5f589180a9e7df9dac732f97637c8bbb7fc`；1.7B为`8444892edb41716b9ad619f757fa6aef4580b50b5a5cd8d079d35b7488e94be2`／`25726f3ea1e781a39b02523a2bd332dec4f8e027308d2bcca75420ad07681e49`。这是与既有来源记录的本机对应检查，未请求当前Hub。

两配置均为Qwen3ForCausalLM、28层、BF16、共享输入输出embedding，hidden size分别1024/2048；没有model_file或量化覆盖。1.7B分片index的全部目标均对应现存两个分片。两模型的原tokenizer聚合身份相同：`54bb02c1a606dc0e7a5137a38837788d17dbeb61948a71be6b32d475070c7985`；原template配置聚合身份`6089820b86a50260ec00285b2c36717c955c82e7a2cfd2b696b1f5913ce548f2`保持。后续运行须绑定完整文件清单，包含generation_config与分片index，并另核对实际loader、模型参数和共用Action JSON格式。

仅读取T1现有环境的9份distribution METADATA：MLX/Metal 0.32.2、MLX-LM 0.31.3、NumPy 2.5.2、psutil 7.2.2、safetensors 0.8.0、transformers 5.16.1、tokenizers 0.23.2、Jinja2 3.1.6。没有导入这些包。T1的tokenizers 0.23.2与D1既有native编码的0.22.2分别保留身份；本次没有新增编码或将两环境写成同一版本。

本机证明SHA `c44fdf1761fcd4fffdd78532c627fa7cbdf2f6a6abd9ac8d59339c9307f85a8e`；完整路径、每份文件hash、原下载metadata和实际检查回执仅存本机。所有权重保持原位，新增模型／框架／GPU／优化／生成均0。本报告供后续精确配置冻结使用；v3独立审核和main验证、CPU消费实现、真实原生容量与正式P04仍按各自门槛推进。
