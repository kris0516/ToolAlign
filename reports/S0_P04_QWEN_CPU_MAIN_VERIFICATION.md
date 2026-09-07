# S0｜固定 Qwen 模型接口 CPU 主干验收

状态：**VERIFIED_CPU**。2026-09-07 22:46:12 UTC，S0 完成 [PR17](https://github.com/kris0516/ToolAlign/pull/17) 合并后的实际主干验证。固定文件/header/代码来源校验、租约守卫、参数原始字节身份及受限加载/装配/重载接口已进入 main；真实模型加载、LoRA 装配、容量和训练仍为 NOT_RUN。

| 证据层级 | 精确对象与结果 |
|---|---|
| E1 完整候选 | `01eeb74d1bce3c3a3c41d84575d4d706e246e818` |
| 独立 R1 | 原 `bdebe4c2bddf927995a6c15124fab75ad04ba5de`，PASS，P0/P1/P2 均 0；[接收](S0_P04_QWEN_REVIEW_HANDOFF.md) |
| 普通隔离集成 | `170be4295b2557953fa0349a8c5746a4fc098926`，973 CPU / 48 optional-tokenizer skipped；[证据](S0_P04_QWEN_CPU_INTEGRATION.md) |
| 最终 PR head | `1e8d76fdbf5c9e10b33676a8b54dbc596192acf3` |
| 最终 CI | [run 34167222348](https://github.com/kris0516/ToolAlign/actions/runs/34167222348)，Python 3.11/3.14 各 14 步成功；各 959 passed / 48 skipped，另 46 项 P00 通过 |
| 实际 CI checkout | `84bf065dfbf4371813e76c6a6488061437ac331a`；parents 为 `5f44f0be5a8d6ab7721de6a0ae4e4595e6effd93` 与最终 head |
| 普通合并 main | `f27951aea573d3e220b053563078d5e428564419`，22:43:37 UTC；原候选与原 review SHA 保持 |
| 主干验证 | 134 passed，包含本包 120 项与 R1 独立 14 项；未重复运行已通过的全部历史组 |

实际 main、最终 head 和 CI checkout 的 tree 均为 `ecaffcc7a76c983ea0269e26539fa3e12eb64b6b`，647 份公开文件逐字绑定。GitHub PR 返回的历史 base SHA 与当前 base 不同；S0 使用实际 CI 原日志、Git parents 和 fetch 后的 main 核对，并保留原 API 响应。

主干执行 `pytest -q -p no:cacheprovider tests/model_io/test_qwen_model.py reports/review/P04-qwen-model-r1/test_independent.py`，使用既有默认 CPU 环境、独占新 basetemp、原始日志和 JUnit。实际 134 项均通过，无跳过，未加载可选模型/框架模块。另五条记录命令完成显式公开 Python 文件 ruff、四份冻结契约、647 路径公开扫描、`git diff --check` 和现存归档/安装绑定，均 exit 0；每条命令的 argv、UTC、输出、源码时点和 child 回收均封存。

三份现存归档再次核对成员和 RECORD；143 个打包源码输入、65 个安装包文件与实际 main 字节一致。R1 原安装目录的 75 条 RECORD 和 9 个模块来源继续匹配，原安装 smoke 的执行时间保持原值；main 未重新构建、安装或调用实物模型文件 API。

主干证明 SHA-256：`aabb8d3f5363aeb7d792e7e38197c41e4f91579f107c0864e1005b084beb3861`，542 条证据路径、36 个不跟随链接、3 个仅 lstat 的 FIFO。最终 CI 证明 `68e88cc92f4f6a244fc4a31f199b70a43610d52f4c868cbaa6e8808ae700f3b0`；原隔离集成证明 `3eb8b4ea97b86655381ae159697c8c11ef3e2be57ec90e5d370f774bf6517ea3`。

保留原 S0 集成启动器预加载 psutil 引起的失败，以及默认环境中相同 1,021 用例 ID 的成功复验。本次只读 CI 核验脚本的两次错误假设（遗漏可执行文件 mode、写错协调文档名称）及修正记录也保留；候选、CI 和测试未为这两次核验错误而改动或重跑。原 R1/E1 失败与限制均未改写。

本次 S0 新增 build/install/实物模型 API/框架/GPU 运行均 0；无新环境、费用、模型/数据上传或公网服务。冻结 v3 的 G-DATA PASS 保持；数据 CPU 修订 R1-r2 继续独立审查。模型 CPU 主干验收不授权正式 P04 训练。
