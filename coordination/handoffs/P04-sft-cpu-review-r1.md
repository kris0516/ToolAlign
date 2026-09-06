# P04-SFT-CPU-R1｜独立审查交接

R1，gpt-6-astra / max；2026-09-07。**CPU准备部分 PASS，P0=0 / P1=0 / P2=0；完整原生trainer仍 BLOCKED_UPSTREAM_CPU_ENTRY。**

- 精确candidate / review唯一父提交：`33d6248e2c518ea777618224382bd30a3cc3433d`。
- candidate tree / parent：`1d2d5474ef87034e0184f8ebfa359345182e3356` / `0c7c2671a64d49fe48c722375481b4cf7a5c82c8`。
- 原生授权：`d65592e5529f573f061355775fec071737233d12`；T1实现基线 `42eaa50a9519efe96d60b49f07cfbd106b36778c`。
- 新分支：`review/p04-sft-cpu-r1`；完整review commit/tree与发布证明由Git对象、最终completion和原生回报登记。
- 已读授权AGENTS/PROTOCOL/PROJECT_STATUS、本任务/原准备任务/精确配置、ADR-0017至0020、docs03/16、S0原中间/交接证明与候选20项新增。契约plan-v0.1 / coordination.v1 / toolalign.contracts.v1不变。

仅新增[审查目录](../../reports/review/P04-sft-cpu-r1/README.md)和本交接；没有修改候选384文件、364份原基线或其他worktree，没有合入后来main、创建任务/sub-agent、变更协调状态或长期goal。

四组原CPU回归895/2 skipped +60+2+13=970/2，再加44项原创独立探针，合计 **1014 passed / 2 skipped**。原51项、110 subtests和安装版44项重复不额外计数。两项skip为HF reference专用snapshot cleanup。Ruff全库/显式报告及4份冻结契约通过；最终公开扫描和推送在机器索引写定后由completion封存。

完整原verifier和四视图实测通过：smoke1600/197、formal6013/217；原Example/sidecar、排名/身份/split/profile、最小桶及隔离副本均核对，8个固定输入/输出负例拒绝。原13例完整IDs重建的共用Sequence/新collator与冻结reference/native及T1数组一致；真实新增编码0、8228重编码0、原selection新增物化0。最终test/ood_test/BFCL未用于训练、统计筛选或调参。

一次持共享租约的R1自有CPU子进程，以13条原创小例、词表4/参数16/最大桶8验证completion CE和梯度。loss最大误差 `2.384185791015625e-07`、gradient `8.940696716308594e-08`，均在float32 `2e-6`内；padding与ignored-logits不变量通过。默认loss负例实际错误增加一个监督位置。

有效模型/SGD/dataset调用真实MLX-LM train一次，在原 `trainer.py:229` 缺失CPU字段 `max_recommended_working_set_size` 处KeyError，未进入循环；optimizer step0、访问0、checkpoint0，参数前后hash一致。预期异常保存后子进程exit0，结论为PASS_NUMERICS_WITH_EXPECTED_ENTRY_BLOCK，不是训练成功。MLX0.32.2 / MLX-LM0.31.3 / Torch2.14.0保持锁定；原P01保护器与vendor未改。子进程3.547687166秒、采样峰值RSS389185536 bytes，实际wait/reap且共享锁释放，无第二次数值尝试。

因此可用入口是固定输入的 `python -m toolalign.training.sft` CPU prepare，以及只读视图/collator/计划/validation结构。完整原生 `train_toy_segments`、`post_update_score` 仍不可依赖；8+5实际更新、尾周期数值、native evaluate、checkpoint保存重载/post-tail绑定全部NOT_RUN。200/752是计划，Score结构与参数hash测试不是实际checkpoint验收；最终接收与兼容修订交S0决定。

独立核对原2418路径、T1248份封存/18条命令及实际Git源码epoch、108份核心从eefc142到33d不变。T1原两次非零失败和S0三份证明均保持。解析原新sdist119成员（118 Git+PKG-INFO）和两个wheel62成员（57包文件+5metadata），全Git/metadata/RECORD通过。sdist SHA `54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655`，两wheel SHA `936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33`。

R1实际将该默认wheel离线无依赖安装到新target，非源码cwd的7条子命令核对origin/44项原创重复/help/完整prepare/3项拒绝（exit1/1/2）。27个ToolAlign模块含8个新增模块均来自target；11种可选库不可导入。源码与安装版prepare报告逐字节一致。R1新build和源码直接wheel均NOT_RUN，没有新环境/依赖/权重下载。

旧50685私有文件、283链接、上轮1562封存条目/7份审查文件保持；旧审查分支与66个原ref对象保留，两个App临时diff ref名称已消失但原对象仍在。R1保留初稿ruff I001及保全检查器临时ref假设错误的失败回执和源码，没有修候选后签原候选。原未去敏审查仍只在本机且不在公开祖先。

两份人工表仍PENDING，R1页面观察0、未代签。G-DATA、正式P04、真实模型容量/训练/评测均未关闭。无费用、公网接口或模型/数据上传。精确命令、全部失败/跳过/NOT_RUN、证据hash见[机器索引](../../reports/review/P04-sft-cpu-r1/VALIDATION.json)，最终completion经原生消息交S0。普通推送本新review分支后结束本轮，等待S0。
