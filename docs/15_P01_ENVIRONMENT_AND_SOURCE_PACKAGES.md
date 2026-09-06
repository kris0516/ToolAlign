# P01 可选环境与源码包边界

状态：S0-SHARED-02 候选，待独立 R1、CI、合并与 main 验证；不代表 P01 或正式 SFT/DPO 已验收。

## 环境职责

默认安装继续只提供 CPU 契约与开发检查。`compatibility` 的四个直接版本保持不变；下列组均为显式选择，ML 依赖根同时限制在 Darwin arm64。

| 选择 | 用途与直接约束 |
|---|---|
| `compatibility` | MLX 0.32.2、MLX-LM 0.31.3、Torch 2.14.0、psutil 7.2.2；已有兼容性基础环境 |
| `compatibility` + `dpo` | 增加 mlx-lm-lora 3.1.2 与 datasets 3.6.0；为唯一备选路径提供依赖，仍需 P01/P05 独立数值与功能验收 |
| 上述组 + `p01-replay` | 增加 mlx-tune 0.6.0 及其必需依赖，仅用于重放首选失败和跨库审计；不能把安装成功解释为该首选通过 |

P01 当前完整 `math`/`smoke`/`calibrate` 探针包含首选检查，必须选择 `p01-replay`。备选依赖组本身不保证整个 P01 重放入口可执行。后续 P04/P05 的正式训练入口另行实现和审查。

```bash
uv sync --locked --python 3.14
uv sync --locked --python 3.14 --extra compatibility --extra dpo
uv sync --locked --python 3.14 --extra compatibility --extra dpo --extra p01-replay
```

第三条命令会安装首选包必需的 VLM/audio 等传递依赖；这不是项目新增多模态训练范围。S0 只做安装和 metadata 验证，不导入这些包、加载模型或开放服务。T1 的实际 ML 测试环境为 Python 3.14.7/macOS 26.5.1；其他平台的依赖解析不能写成实机训练验证。

`datasets` 显式固定 3.6.0，是为了复现 T1 已测闭包。初次只固定备选包会解析到 datasets 5.0.1；该未测升级已放弃。现锁定 dill 0.3.8、fsspec 2025.3.0、multiprocess 0.70.16，与实测一致。fsspec 会从前一兼容环境的 2026.7.0 改为 2025.3.0；这是真实依赖变化，不能声称所有可选环境完全不变。默认 CPU 依赖不漂移。

来源：固定版 [mlx-lm-lora metadata](https://pypi.org/pypi/mlx-lm-lora/3.1.2/json)、[datasets metadata](https://pypi.org/pypi/datasets/3.6.0/json)、[mlx-tune metadata](https://pypi.org/pypi/mlx-tune/0.6.0/json)。版本、制品哈希与实际安装记录见本包报告。

## 许可来源事实

mlx-tune 0.6.0 与 datasets 3.6.0 的 metadata 和随包 LICENSE 均为 Apache-2.0。mlx-lm-lora 3.1.2 的 metadata 写 MIT，但 wheel 中 LICENSE 为 Apache License 2.0；两处声明不一致。本项目保留这项差异及各自字节摘要，不替上游推定统一许可。依赖不作为本项目 MIT 源码重新许可，也不在源码包内复制这些第三方实现。未来若分发依赖制品，须保留上游许可文件并复核该差异。

## 源码包的显式选择

T1 在 App worktree 中枚举到私有环境、模型和日志进入默认 sdist 文件选择，并停止了耗时构建。S0 用固定 Hatchling 1.27.0 只读复核该选择。T1 与 S0 当时未完成含真实私有内容的源码包；随后 D1 在旧基线的一次构建生成了含私有文件的失败归档，已移入私有证据目录并标记禁止发行，没有上传。不能把 T1 的停止记录扩展为所有任务从未生成过归档。

原因已由固定源码和合成构建定位：Hatchling 的 `load_vcs_exclusion_patterns` 在绝对项目根匹配自身忽略规则时返回空规则。App worktree 位于 `.codex` 目录之下，项目 `.gitignore` 又排除 `.codex/`，因此触发了这一行为。普通 worktree 中 `.git` 是文件本身不足以解释问题。参见 [Hatch 显式选择配置](https://hatch.pypa.io/1.13/config/build/#explicit-selection)；实际版本仍锁定 1.27.0。

本项目为 sdist 设置 `only-include`，仅选择项目代码、配置、测试、三个验证脚本及所需公开根文件。首轮独立审查发现：目录选择仍会纳入目录内部的被忽略文件，例如 configs 中的密钥和 src 中的权重。因此修订增加 `[tool.hatch.build].exclude`，将环境、密钥、模型、日志、运行制品和私有目录的显式排除同时应用于 sdist 与直接构建的 wheel，不依赖 Hatchling 是否保留 VCS 规则。新增私有路径类别时须同步检查打包排除和真实归档回归。

研究报告、原始数据、权重、运行目录、环境与任务私有映射不属于源码包内容；完整研究证据仍通过 Git 仓库与受控私有原始记录交接。公开内容扫描负责索引/待提交内容，并不扫描被 Git 忽略的文件；它不能替代实际发行包内容检查。

```bash
uv run --locked python scripts/check_source_distribution.py
uv build
uv run --locked python reports/review/P00/verify_wheel.py
```

新检查在临时 `.codex/worktrees` 下创建真正的 Git worktree，植入 85 个合成私有文件，覆盖根目录及 configs/tests/src 内部的密钥、权重、环境、日志和私有子目录。检查实际 tar、从该源码包重建的 wheel 以及直接由工作区构建的 wheel，核对泄漏探针和冻结 schema。检查已加入 CPU CI。测试不读取或打包用户真实权重，不上传任何制品。

历史审查目录中的包结构/extra 精确断言绑定它们报告写明的旧候选。例如 S0-SHARED-01 的“只有一个 extra”是当时的快照，不是禁止后续合法新增 extra 的长期契约；保留原探针和旧结果，当前候选使用新的独立审查证据，不修改旧断言来制造当前全绿。
