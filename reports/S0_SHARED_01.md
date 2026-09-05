# S0-SHARED-01｜公共支持自查

日期：2026-09-06；base `4cfbe1a5b8d93c20d7b11ec14b31757a574d0903`；分支 `work/shared-compat-source-policy`；结论：**自查通过，待独立 R1**。

## 改动与限制

- 四个直接 optional 依赖及 uv.lock，Darwin arm64 的真实私有环境安装成功；默认 CPU 环境 metadata 确认无 MLX/MLX-Metal/MLX-LM/Torch/psutil。
- Linux x86_64 与 Intel macOS 的 sync dry-run 仅规划基础包加 psutil；无 CUDA/MLX/Torch。这是解析计划，不是那些机器上的实际安装。
- uv 解析 52 个锁定项；本机 extra 环境实际安装 50 个 distributions。MLX/MLX-LM/PyTorch 未被本次 S0 检查导入，未下载/加载模型，未请求 GPU 租约。
- 冻结契约四文件 hash 检查通过；src/runtime/原 tests/协议配置均无变更。58 项现有 CPU 测试通过。
- ToolACE 仅提供待 D1 实现的数据政策；不将潜在写入工具标成只读，不将历史 observation 冒充实际执行。仍需 P02 自动/人工验证和 P03 registry 边界测试。

## 原始日志索引

原始 stdout/stderr 与安装环境保存在本机私有证据目录。下表的简短名称对应原始命令；完整的 uv 参数和 metadata 检查方式如下。

| 检查 | 退出码 | 原始日志 SHA-256 |
|---|---|---|
| cpu-sync | 0 | `bcef7a88bb46d63aa0da7cbaea573d6e1397f4ae0faa0724185ed446a85bdd7a` |
| cpu-test | 0 | `54c70c2d0f84df5cf558bf2a299803b2a520413c4b8dc53d227e197a62004a7c` |
| lint | 0 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| freeze | 0 | `cbd2ccd1c8bb7222da949ce7cca8ba74134a38f89a35b3295062c93c4e10d190` |
| public | 0 | `2ee07a8ad77465f844cb0ff483ef25c20472b27733d363be2a3f1cb66f7dc6da` |
| compat-sync | 0 | `d9b5723ade69f60b95e41adc0fc75436b7cd84b2ab0ad5911fe775886219e3db` |
| linux-plan | 0 | `402ab58adc42ef23ae4b4f6a6f3f50440490ee3571530d6381a259e30a2507d2` |
| intel-mac-plan | 0 | `1bb21464e9839834ad600363fd253c972eb572465a2c76570747a3331c1dba0b` |
| cpu-metadata | 0 | `0ac9c52b652dc1a21fd54258f8d98bd278c16be0845b3b3c65393a37c97a03a9` |
| compat-metadata | 0 | `9fd1acc0f26e78036b95fac65bfc7512ad2423d7d777ebe5b1868135e0efb83d` |

CPU 命令：`uv sync --locked --python 3.14`、`uv run --locked pytest -q`、`uv run --locked ruff check .`、冻结检查与公开扫描。可选安装命令：`uv sync --locked --extra compatibility --python 3.14`，用独立 UV_PROJECT_ENVIRONMENT 保存隔离环境。跨平台命令在该命令后追加 `--python-platform x86_64-unknown-linux-gnu --dry-run` 或 `--python-platform x86_64-apple-darwin --dry-run`，均不创建外部运行机。

metadata 检查只读取 importlib.metadata.distributions/version；验证默认环境不存在五个可选包，兼容环境版本与直接 pins 及 mlx-metal 0.32.2 一致、没有 mlx-tune。没有用 import/model 运行验证替代这些包清单证据。

## 来源核对

S0 重新读取 D1 已下载的固定 ToolACE data.json，独立计算 SHA-256、字节数、记录数并比对 revision API：`6bda777c88d21e5a204703c1ee45597a8fa4f734`，gated=false，37,154,735 bytes，11,300 records，`ba12c083fca7e8da48c67ad5b895e495447da7c66e39a2e19742c082e6cb537e`。源内容不进入公开仓库。

PyPI 固定版 JSON 元数据由 S0 独立 curl 获取并保留 hash（MLX/MLX-LM/Torch/psutil）；来源链接和许可见 docs/14_COMPATIBILITY_ENVIRONMENT.md。首次系统 Python urllib 请求因本机 CA 配置失败，改用验证 TLS 的系统 curl 成功；没有关闭证书验证或修改全局设置。

## 后续门槛

R1 对精确候选审查，CI 通过后 S0 合并并验证 main；只有届时 T1/D1 可采纳公共变更。SFT/DPO 算法正确性、真实模型资源、数据质量与人工检查仍归原 P01/P02，当前均不能据此宣称通过。
