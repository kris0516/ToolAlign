# P06 G5｜独立测试只读工具集 CPU 首包

owner E1；在既有独立worktree从S1派发的精确提交建立 `codex/e1-p06-g5-tools-r1`。先实际读取avoid-overkill。目标是为[固定评测协议](P06_G5_PROTOCOL.md)提供与P03/G4旧六工具分离的、真实可执行的新静态工具集。当前旧六工具在G4构成一个train连通组，不能直接当独立测试工具。

新增单个 `tools/heldout_catalog.py`，固定catalog ID `heldout-devops.v1`。四个工作域各两个read-only工具，共8个即可：发布清单与部署记录、事件窗口与处置规则、软件包构建与测试套件、存储池与配额。每域第一个工具的返回值可提供第二个工具需要的标识，从而支持两步依赖；两个工具有可说明的语义差异，保留错误对象/版本/日期的可构造反例。使用原创虚构静态资源、明确enum或有界数值参数，所有信息来自代码内固定数据，不读取caller路径、网络、环境或原始训练数据。不扩展通用插件系统。

LocalToolRegistry新增固定catalog选择参数，默认仍旧catalog；保持旧catalog.py字节、默认manifest/sourcehash/registry_hash及全部工具spec不变。只允许代码内枚举出的两个catalog模块与其固定IMPLEMENTATIONS，未知catalog明确拒绝。manifest准确绑定所选source内容和工具实现名称。LocalToolExecutor把固定catalog身份传给owned child，child重建同一subset registry并验证hash后执行其绑定实现；不能由caller导入任意模块或提供callable。保留一次性ValidatedCall、白名单、故障注入、取消、时限和进程回收边界。

四域设计为不同工作任务，参数语义本身应不同，不仅靠改工具名改变hash。后续D1将用真实P02/P03/G4 source/tool/schema/template键审计分组，不能在此承诺已完全隔离或把四域强行标成四个独立group。本包不创建48条最终题目、oracle或偏好，也不改旧数据；先交清晰schema、固定资源语义和可用两步示例，D1随后独立构造私有测试与反例。

允许改 `src/toolalign/tools/registry.py`、`executor.py`、`__init__.py`必要导出与新增heldout_catalog.py；对应tools CPU测试。T1独占评测后端/harness/runner/Colab，彼此不越界。不改contracts、旧catalog.py、已有任务/oracle、依赖锁、模型或共享状态。CPU验证覆盖8工具的真实执行、subset只允许advertised工具、错误catalog/source绑定、旧默认身份逐字节保持、错误参数、超时/取消和回收的受影响分支；复用未变边界证据，不重跑无关ML矩阵。

公开报告 `reports/P06_G5_TOOLS_CPU_R1.md` 与交接 `coordination/handoffs/P06-g5-tools-cpu-r1.md`，交付精确commit、实际命令/退出码和私有证据索引，列明固定catalog API、工具/资源和两步关系，供T1/D1集成。只授权CPU开发与现有环境，不安装新依赖、不下载模型、不访问GPU、不读取最终benchmark答案。R1独立技术检查后由S1接纳。
