# 14｜P01 可选兼容性环境

依赖候选只用于 P01 的本机功能/数值/资源核验，不代表 SFT/DPO 或 Metal 已通过。S0 从公开 PyPI 固定版元数据独立核对以下四个直接依赖，并由 uv 锁定传递依赖与制品 hash。CPU 基础安装不选择任何 extra。

| 直接依赖 | 固定版本 | 平台与用途 | 来源许可 |
|---|---|---|---|
| mlx | 0.32.2 | 仅 Darwin arm64；MLX 数组/候选训练 | MIT |
| mlx-lm | 0.31.3 | 仅 Darwin arm64；原始模型与 LoRA 候选接口 | MIT |
| torch | 2.14.0 | 仅 Darwin arm64；P01 强制 CPU 小张量参考 | PyPI 声明复合 SPDX，见下文 |
| psutil | 7.2.2 | 仅在选择 compatibility extra 时安装；进程资源监测 | BSD-3-Clause |

元数据来源：[MLX](https://pypi.org/pypi/mlx/0.32.2/json)、[MLX-LM](https://pypi.org/pypi/mlx-lm/0.31.3/json)、[PyTorch](https://pypi.org/pypi/torch/2.14.0/json)、[psutil](https://pypi.org/pypi/psutil/7.2.2/json)。PyTorch 此版本声明为 `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`，不能把整个分发包简化成单一 BSD 声明。

```bash
# 现有 CPU 基础：不安装或导入 MLX/PyTorch
uv sync --locked --python 3.14

# 仅在受支持的本机兼容性任务选择该 extra
uv sync --locked --extra compatibility --python 3.14
```

Darwin arm64 markers 避免 Linux CI 因 PyTorch 的 Linux 依赖引入 CUDA。选择 extra 不授予模型加载/GPU 权限；实际入口仍须检查平台、获得 GPULease、固定模型来源并实施预算。PyTorch 小张量参考显式使用 CPU，不能默认切到 MPS。未支持的平台选择 extra 只会得到适用依赖，不能据此宣称 MLX 可用；P01 CLI 应明确拒绝不支持的模型执行环境。

`mlx-tune` 暂不加入正式依赖；T1 报告的自动 set_wired_limit、reference 与 accumulation/mask 风险仍待最小复现。私有探索环境与公共 compatibility extra 必须分别登记，不能将成功安装解释为正式 DPO backend 通过。P01 若确需其他直接库或不同版本，向 S0 提交实证后再更新锁文件。

P01 后续可选备选/完整重放与源码包边界的候选更新见 [环境与打包说明](15_P01_ENVIRONMENT_AND_SOURCE_PACKAGES.md)。原 compatibility 四个直接 pin 保持；可选传递依赖变化须以该候选独立审查与新 lock 为准。
