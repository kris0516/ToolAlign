# E1｜G6 Mac客户端、开发示例与交付说明 CPU r1

2026-10-27，S1派发。起点为派发消息中的精确S1协议提交，父主干为PR34 `98d642a116da94f2ab2b2aaeb6e931f79fd5cabc`。在自己的既有worktree新建`codex/e1-p07-g6-mac-client-r1`，不覆盖旧证据。先实际读avoid-overkill、[G6协议](P07_G6_PROTOCOL.md)与[HTTP字段](../../docs/18_RESTRICTED_CUDA_SERVICE.md)。本轮只做CPU开发/说明，不加载固定模型或分配GPU。

目标：Mac经用户准备的loopback SSH转发调用固定CUDA服务，独立校验原始Action并执行现有只读工具；提供可运行的有限轨迹与五类原创scripted开发示例、复现/模型说明。T1并行实现服务，严格使用共享HTTP字段，不各自发明契约。

## 允许改动

新`src/toolalign/client/`、`tests/client/`、`examples/service/`；`README.md`、`docs/06_DEPLOYMENT_ROADMAP.md`、`docs/08_ACCEPTANCE.md`、`docs/10_LEARNING_DEFENSE.md`及新`docs/19_REPRODUCTION_AND_DELIVERY.md`中与本次实际交付直接相关内容。模型卡可以整合到19号文档，不必新增重复文档。公开交付报告`reports/P07_G6_MAC_CLIENT_CPU_R1.md`与交接`coordination/handoffs/P07-g6-mac-client-cpu-r1.md`；私有证据`.toolalign-local/p07-g6-mac-client-r1/`。

不修改service/inference、model_io、harness、registry/executor、Colab控制器、共享18号HTTP字段、已有冻结契约、依赖、训练/题集/oracle、BOARD/PROJECT_STATUS/DECISIONS。使用标准库HTTP及既有工具执行器，依赖不变。源码位置不依赖T1未交付模块，先对共享HTTP进行CPU契约检查，S1随后做两包真实组合。

## 客户端与示例

提供`python -m toolalign.client`的清楚CLI；URL仅Mac loopback，核对S1固定service_run_id和ModelIdentity。token从私有文件读入header，不进入argv或日志。重发丢失POST响应只用原key/同payload，所有轮询/重试共用单调截止。保存request_id；超时/中断时显式cancel并等待回收状态，网络不可达时写unknown，不能把本地退出写成远端已回收。不得自动换key、换run或启动Colab实例。

原文独立parse后与返回字段交叉核对，只允许本次advertised原样schema子集、合法参数、未重复call_id，通过原registry取得一次性ValidatedCall再交LocalToolExecutor。不接受服务返回的路径、模块、可执行代码或自称ValidatedCall。Action建议和本地工具观察构成下一步ModelInput，保持完整schema/history，不静默截断。

演示运行器最多3次模型决策、2工具轮、30秒决策预算；清理尾段单列。正常调用、无需工具、错误参数、故障恢复、预算终止五类均提供原创CPU scripted示例和命令，使用固定工具，不含隐藏测试或原训练数据。语义答案判定与API completed分开。真实模型尚未运行的示例标NOT_RUN，不能用脚本成功替代；不后处理修补或强迫模型final。

## 复现与最终说明

19号文档覆盖CPU用户入口、Colab固定私有配置/SSH转发前置、模型身份与许可、启动/停止/回滚、结果/失败边界、证据入口。SSH只连接已存在命名会话，避免官方CLI缺省创建实例；实际端口/完整命令待S1真实验证补齐。不编造执行成功。保留G5 M0/M1均0/28、A1均0/8、A2局部收益、G4无偏好/DPO未运行、L2无合格输入和无官方分数。

使用现有真实v3/13例材料之一解释token/mask，绑定已有公开报告与私有行身份/范围；不把原始数据复制公开。可只公开角色、长度/监督区间和hash。DPO解释给已验证原创数值例子、SUM/mask、固定SFT reference，明确它不是实际chosen/rejected训练对。用一条真实G5失败解释能力边界，不公开隐藏题面/答案。S1根目录现有私有证据可只读，按相关报告定位，不动原文件。

更新旧MLX/FastAPI/服务端工具执行设想、docs/10本人必须审核要求与docs/08 Gate编号和App goal编号混用；依据现行REVIEW_POLICY，实际审阅者为独立Q1 AI，不声称kris本人已掌握。README入口简明，指向实际结果和复现，不抹去失败或声称生产就绪。模型卡许可引用现有来源，新增事实按官方固定revision核对。

## 验证与交付

至少通过用户CLI/真实loopback响应、同key丢失响应恢复、超时远端取消、非法/未advertised工具不执行、五类scripted轨迹及真实本地child回收。关注公开行为，不复制实现逻辑造测试。真实Colab及模型推理仍NOT_RUN；后续与T1组合、R1干净环境复现和Q1最终说明审核由S1组织。

交付精确提交、命令/退出码/原始失败、示例结果、私有索引以及相关链接/公开内容检查。保留旧源码/证据；不修改协调状态，不自行合并或发布模型/数据。
