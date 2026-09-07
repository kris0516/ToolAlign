# S0｜固定 Qwen CPU 接口隔离集成

**隔离集成通过，最终 CI/main 待完成。** 原 R1 对完整 `01eeb74d1bce3c3a3c41d84575d4d706e246e818` 的 PASS `bdebe4c2bddf927995a6c15124fab75ad04ba5de` 已由 S0 完整接收；范围为固定模型文件、加载前来源门和参数身份接口的 CPU 技术验证。真实模型加载、LoRA 装配/重载、容量、优化和生成均 NOT_RUN。

从 S0 main `5f44f0be5a8d6ab7721de6a0ae4e4595e6effd93` 建立隔离分支 `codex/s0-p04-qwen-model-r1`，普通合并原 review 为 `170be4295b2557953fa0349a8c5746a4fc098926`。原 636 份 main 文件保持，新增五份模型实现/交付文件和五份独立审查文件，共 646 份；固定模型配置原已在 main 同字节。原 candidate 与 review SHA 均保持，S0 未修改被审生产实现或测试。

2026-09-07 22:27:24–22:32:11 UTC，S0 在精确集成提交运行七条命令，保留一次原环境干扰失败，六项最终检查通过：

| 检查 | 实际结果 |
|---|---|
| 默认 CPU 组合测试 | **973 passed / 48 optional-tokenizer skipped**；包含原相关 120 项和 R1 独立 14 项，不重复累加为新覆盖 |
| Git 跟踪 Python 的显式 ruff 列表 | PASS；无缓存，包含新模块、测试和独立审查代码 |
| 契约冻结 | PASS，4 份冻结契约不变 |
| 公开扫描与 diff | PASS；646 路径；公开扫描是启发式检查 |
| 三份现存归档 | PASS；sdist 144 成员、两 wheel 各 70 成员，143 个打包源码输入逐字对应集成提交 |
| 现存安装字节 | PASS；65 个包文件、75 条安装 RECORD、原 9 个模块来源与集成源码一致 |

首次 CPU 启动器复用了早前兼容检查的 `psutil` 缓存，并在 pytest 前加载了该模块。`test_original_runtime_sources_detect_change_after_preflight` 使用独立模拟来源目录，生产 `_loaded_origins` 因已加载的外部 `psutil` 正确返回 `shadow_loaded_module`；原结果为 **1 failed / 972 passed / 48 skipped**。原脚本、日志、环境、退出码和测试目录完整保留。

S0 改用现有项目默认 CPU 环境启动新进程，未添加或加载旧缓存，未修改生产守卫或候选测试。复验通过；两份 JUnit 的 **1,021 个完整用例 ID 集合相同**，原失败用例保留且通过，48 个跳过项仍因缺少固定私有 tokenizer 前提。最终进程未加载可选模型/框架模块，未安装依赖或创建环境。这个 S0 启动器修正不构成新的候选修订或正式问题计数。

三份归档仍是 E1 原实际产物：sdist `73ee4795ca39d81021b3eed1eb1ed4b8a9e9d3caf5899469e91cfd75f5f7e1cf`，两 wheel 均 `117f74f92aad166aceb16336771ec4d4bf9f98e7ac6142fb0592d2c1246373d6`。原安装检查发生于 R1 的 21:46:00 UTC；本次只核对其成员、RECORD、来源及对应源码，不把该时间改写为 S0 新执行。

2026-09-07 22:33:51 UTC 封存证明 `3eb8b4ea97b86655381ae159697c8c11ef3e2be57ec90e5d370f774bf6517ea3`：6,167 个文件路径、370 个不跟随链接、6 个仅 lstat 的 FIFO。两次独占测试目录与本轮私有证据在 proof 前合计 191,410,034 bytes；全部测试源码首尾 hash 相同，自有命令 child 已回收。完整 argv/UTC/exit/原输出与包绑定存于本机，原失败未覆盖。

复核入口为默认环境的 `pytest -q tests reports/review/P04-qwen-model-r1/test_independent.py`，以及显式 tracked Python lint、契约/公开/diff 和原归档/安装字节绑定；实际命令另含各次独占 basetemp、JUnit 和禁用可选 tokenizer 的环境参数。S0 本次新 build/install、真实模型文件 API、编码、框架/模型/GPU 均 0。仍需 [PR17](https://github.com/kris0516/ToolAlign/pull/17) 最终双 Python CI、普通合并和实际 main 验证。

R1 当前接续精确 1769046 的数据特殊文件修订复审；原 b99 F1 连续失败保持 1。该数据包与后续原生 runtime CPU 尚未达到主干验收，当前模型 CPU 集成不放行容量或正式训练。
