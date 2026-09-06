# P04-SFT-NATIVE-TOY-R1｜原生 toy 独立审查

**PASS；新增 P0=0 / P1=0 / P2=0。** 精确候选的默认 CPU 准备、新 `TOY_NATIVE_GPU` 固定数值与状态绑定、受限资源终态通过独立核验。此次证据仅覆盖原创小表模型；正式模型训练、人工门槛、G-DATA、最终 CI/main 验收仍由 S0 后续处理。

R1，gpt-6-astra / max；2026-09-07（Asia/Kuala_Lumpur，原始日志为 UTC）。契约 plan-v0.1 / coordination.v1 / toolalign.contracts.v1 / ADR-0021。切换前读取并保存13份授权文件，随后审阅候选9条改动、T1原始交接、报告、索引及私有原件。仅新增本目录及[本轮交接](../../../coordination/handoffs/P04-sft-native-toy-review-r1.md)，候选408文件保持，399份原基线不变。

| 对象 | 精确身份 |
|---|---|
| candidate / 本 review 唯一父提交 | `f7326d1823c4cf132ae44525f4755c96c88ec159` |
| candidate tree | `247eba004d714def81f0bef65375ddbf0fee95cf` |
| candidate parent | `c06782a61857259097932078c661189b4fda781d` |
| R1 authorization | `482f8991c97c33678583aa6c853a75c41fda0f0f` |
| 实现基线 / T1 原授权 | `50867c0be43d110df6c3620c94022fcfdaf779b5` / `de86568d73ee77bbf92b6f749a39a9ab38955836` |
| 固定配置 SHA-256 | `fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb` |
| 原 cases SHA-256 | `df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47` |

分支为 `review/p04-sft-native-toy-r1`。review commit/tree 在最终 Git 对象与原生交接中登记，避免文件自引用。没有合入新 main、修改候选实现或原测试、变更锁/CI/配置/看板，也没有给自己的实现签通过。

## 独立 CPU 与默认安装结果

实际五组原回归为 `931 passed / 2 skipped`、`60 passed`、`2 passed`、`13 passed`、`44 passed`；[新增34项 CPU 探针](probe_cpu.py)通过，合计 **1084 passed / 2 skipped**。生产新增36项已含在931中；110个 subtests、安装版44项重复及数值逐例核对另记。两项 skip 均为 `tests/model_io/test_snapshot.py:178` 的 HF reference 专用 snapshot cleanup。使用已有 Python3.14.7、固定 tokenizer 来源与新系统 basetemp，未新建环境或下载依赖。

默认入口仍只做准备。新 target 的完整 prepare 得到 smoke train/validation 为1600/197，formal为6013/217；优化更新实际为0、`training_authorized=false`、完整选择 tokenization 为0。R1新 `preparation.json` 与 T1本轮原安装结果逐字节相同，SHA-256 `6d7829d4f049e1a7a4727357a857a07d5834c654194286c913d78e32bca1dcb0`；其中 CPU consumer 的 canonical hash 为 `4df0d2da491de0dd0abf4fdf7cc64ce733f475fce38617d07f4e7d3c72baf491`。上一轮 CPU prepare 的历史身份与原文件保持。

[安装检查](exercise_installed.py)在非源码 cwd、`-B -I -S` 下执行7条真实子命令：来源核验、原44项重复、help、完整 prepare，以及输出已存在/配置篡改/训练开关的预期拒绝。另有[安装版 native 边界](installed_guards.py)：help、FORMAL模式拒绝、输出范围拒绝、配置 hash 拒绝，以及无租约时在框架导入前拒绝。28个默认 ToolAlign模块均来自新 target，其中9个 SFT模块；58份包载荷匹配 wheel，可选框架未导入，也无源码回退。

## 原13例、完整梯度和两步状态

[标准库参考](numeric_reference.py)不导入 ToolAlign、MLX、Torch或NumPy。由原定义重新生成13个 rank 的 prompt/completion/EOS、右 padding、shift、监督位置与64个初始 float32参数，逐值等于固定 cases。rank1和13数值相同，保留全部13个 rank；有效数值载荷为12种，每次完整 validation 为44个监督 token。

参考使用稳定 log-sum-exp、完整8×8解析梯度，再独立计算 SGD0.07 的8例与5例平均更新。832个中心差分分量复核解析梯度，最大误差 `4.3414327688395815e-11`。训练按每例 completion-token mean 后对8/5例求均值；validation 按总 CE / 总监督 token 计量。

R1直接核对原三次运行及本轮两次运行的全部逐例数组。安装版新运行相对独立参考的 CE 最大误差 `1.904749411529849e-07`、完整梯度最大误差 `2.3736388549133736e-08`，均低于固定 `2e-6`。去 padding 的 CE/梯度及仅改 ignored logits 的 CE不变。原生 default_loss 负例实际把监督数由2变3，CE由正确的 `2.074565887451172` 变为 `2.0883114337921143`。

[独立进程包装器](native_probe.py)从新安装 target 调用冻结 `_numerics`；训练使用原 `trainer.train/evaluate/TrainingArgs`、completion loss、OrderedBatches及保持启用的 compile。没有复制训练循环、替换数值或修改 vendor。真实8+5运行中 model/optimizer/RNG对象保持，只 seed 一次，rank1–13各访问一次，实际 optimizer step 为1、2，分母分别为8、5。

| 安装版实际 checkpoint | 已处理微步 | validation CE | token数 | 文件 SHA-256 |
|---|---:|---:|---:|---|
| step1 | 8 | 2.066978758031672 | 44 | `06f9f5dcc8dbc6e399313eaac83b4506d90521f24793644b29c0c15fe43df58b` |
| step2 | 13 | 2.0616965131326155 | 44 | `17906c78b9689f4e75768eb2bbe23ce5853db2a66833e295b10b2fa9436eb132` |

R1使用标准库直接解析实际 safetensors header、F32 shape8×8及256字节参数，逐元素比较独立更新参考，最大误差 `1.862645149230957e-09`。各 checkpoint 重新按完整13例计算 token加权 CE，最大误差 `1.54053288348166e-07`。文件 hash、参数内容、selection、validation身份、step与microsteps均绑定；step2参数内容 hash 为 `0c4907f87df8c5d58efd31e3ba40a14fa6a5a28d3342c4394905ae6ad091a2dd`。

真实保存重载后 score与step2完全相同，使用step1文件给step2模型评分被 `checkpoint_parameter_content_mismatch` 拒绝。确定性选择得到step2。原创CPU边界验证了CPU/GPU不可混选、FORMAL/未知scope/profile、错误身份、计数、NaN/Inf、无效分母及不完整validation拒绝。验证重用相同toy训练例，仅证明状态记账；泛化和模型质量均 NOT_RUN。

## 两次框架额度与资源终态

R1新 ledger 实际启动 **2/2** 个框架子进程。第1次为上述安装版 segmented；第2次提前登记用途，直接观测不同的单段 accumulation=8 分支。第二次同样使用安装版源码，沿用冻结内部 mode 名称 `source_unsegmented_negative`。

单段分支实际访问13个 rank、仅更新一次，最终参数等于step1参考，距离完整两步参考最大误差 `0.013687163591384888`，丢失5个尾微步。结果是 **EXPECTED_NEGATIVE / process exit0**，用于确认反例，不计为正确完成训练。没有第三次框架启动。

| R1本轮运行 | 真实更新 | 墙钟秒 | 采样峰值 RSS bytes | 实际 MLX peak bytes |
|---|---:|---:|---:|---:|
| 新安装 segmented | 2 | 4.496296458877623 | 400310272 | 5864 |
| 新安装单段反例 | 1 | 3.140921541955322 | 400392192 | 5864 |

[资源与来源审计](audit_runtime.py)复核真实R1 owner、当前PID/启动时间、同一物理 `gpu0` 的fd/inode及持有状态。框架导入前租约已持有，并持续至 `os._exit`；MLX default/stream均为GPU，Torch实际CPU、intra/inter各2线程。两次退出均已wait/reap，记录PID现不存在，共享锁释放。2412/2411个有文件的实际模块 origins逐文件核验，30个已加载ToolAlign模块均来自新target。

只读复用 MLX0.32.2 / MLX-LM0.31.3 / Torch2.14.0 / NumPy2.5.2 / psutil7.2.2。trainer/datasets源码分别绑定 `ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe` / `fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17`。P01 wired-limit保护器保持原样，仅抑制OS setter，事件保留，setter和compile原API均恢复/保持。上述数字是固定小例的资源记录，不作容量或吞吐结论。

旧 `534445b` 控制器在磁盘故障后已回收CPU子进程，却因最终 `_disk_bytes` 再次报错而缺少 supervision，导致失败模式无法重登记；R1独立重现该反例。当前CPU探针用9000字节实文件及8192字节测试阈值，并明确注入identity、monitor、stdout hash及RSS报告故障，另检查不存在的可执行文件。实际共5个新增自有CPU子进程（含历史反例）均回收；当前失败记录保留终态并能重登记。无法取得的诊断值为null，未伪装成成功测量。生产资源限额与T1/R1真实框架ledger不受这些fixture影响。

T1原两次和R1新一次 semaphore shutdown warning 均保留。按真实SDK的 `SEM_FAILED` 定义，只对日志中三个确切名称执行 `sem_open(flags=0)`，均为ENOENT；没有create/unlink，也没有全局泄漏审计声明。原T1的sentinel误分类与SDK wrapper读取失败材料保持。

## 原始来源、归档和失败保留

[原件审计](audit_original.py)核对T1 FINAL_FILES的3038文件/197链接、测量3016文件、原1559文件，以及31份完整父命令的argv/环境/UTC/exit/源码与日志。27份测量子集对应7份源码快照、409份源码blob；提交前guard各自绑定原hash，重构的native源码blob为 `d839acaa1b16bb6e6264810ad1c7ba3461570ed68eea8c19a8caca34d83e2339`，并明确保留重构性质。

原数值源码为 `534445b`，资源修复为 `fae3d60`，安装probe为 `c06782a`，最终 `f7326d1`仅增加报告/索引/交接。六个数值/边界函数的AST与adapter/validation字节跨数值epoch到最终保持；guard与资源监督修改分别检查，没有把较晚提交冒充原执行源码。原三个非零父命令（启动前symlink-stat、第一轮CPU harness、第一轮安装origin probe）及S0原磁盘反例保留。

[归档检查](check_package.py)解析实际三归档，逐成员核对普通文件、安全路径、Git/包字节、metadata、entry point、license及完整RECORD。

| 原实际归档，R1本轮解析 | Bytes | 成员 | SHA-256 |
|---|---:|---:|---|
| sdist | 257973 | 122（121 Git + PKG-INFO） | `b8c29ecad579ec43a06b31b9d6106d669dc74c0c50c13d785c861cff46062a17` |
| 默认wheel | 140688 | 63（58包载荷 + 5 metadata） | `0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b` |
| 显式sdist重建wheel | 140688 | 63 | `0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b` |

原默认 `uv build` argv与raw stderr明确由新sdist构建wheel；显式sdist重建相同。原15份嵌套默认命令的实际字段和日志均核对，其中4份基础归档命令沿用旧timestamp字段、未单录cwd，该缺省字段原样保留，执行上下文由完整父命令和冻结helper绑定。R1通过离线 `--no-deps --no-python-downloads --target` 实际安装新target；R1额外构建及源码直接wheel均 NOT_RUN。

R1本轮三份辅助检查初稿非零退出均保留：把重构native blob错认成test文件；过严拒绝合法safetensors null metadata；混用三代嵌套命令的timestamp schema。只修正R1审计器，旧源码版本、raw失败与修订结果保持，候选未改变。没有用这些辅助失败掩盖候选缺陷。

末次保全确认旧51009私有文件（2453772768 bytes，排除于本轮新增预算）、284旧链接、上轮1673封存文件/156链接与9份旧审查文件保持；18个旧review refs和73个原ref对象在，旧私有历史不在公开祖先。保全快照时，本轮新材料及7个系统测试目录共165857374 bytes；最终清单与占用由后续completion封存，低于2GiB限额。

## 决议与交接边界

精确候选 `f7326d1823c4cf132ae44525f4755c96c88ec159` 可交S0继续集成。原CPU trainer的设备元数据KeyError证据继续有效；本次PASS覆盖新增GPU toy scope，不改变CPU trainer支持记录。人工表仅kris可填写，本轮填写0、实际页面观察0；未绕过原页面导航拒绝。

无预训练权重、真实P02优化、真实10+3或8228行新编码、选择重新物化、最终测试/BFCL训练、baseline/容量/SFT/DPO、费用、公网服务或模型/数据上传。G-DATA、人审与正式P04保持未放行。

Ruff全库/本目录及四份契约冻结已通过。[去敏机器索引](VALIDATION.json)固定29份测量命令、精确源码与证据hash。公开内容扫描、最终Git对象、普通推送/远端读回及完整私有封存随后执行并单独绑定，以避免自引用。R1交付后结束本轮；独立PASS不自动关闭最终CI/main或P00–P09目标。
