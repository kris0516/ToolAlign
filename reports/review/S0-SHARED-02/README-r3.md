# S0-SHARED-02：R1 复审 r3 证据

日期：2026-09-06；精确候选 `f8ec7ff040053f11e073b6858e1f849e888d4ac2`；分支 `review/shared-02-r3`；结论 **PASS（P0/P1/P2 均为 0）**。正式判断见 [r3 handoff](../../../coordination/handoffs/S0-SHARED-02-review-r3.md)。r1/r2 的 FAIL、探针与原始证据索引均保留原文。

## 关闭前后对照

同一未修改的 r2 `probe_case_boundaries_r2.py case-variants`，在相同本机自动检测条件下执行：

| 精确候选 | sdist 私有泄入 | 重建/直接 wheel 私有泄入 | 退出码 | 完整日志 SHA-256 |
|---|---:|---:|---:|---|
| r2 `8148929` | 21 | 7 / 7 | 1 | `2c0db872a93c150e42c38c8b1177c75992fa95a0162416d69aab85b34bbd3ac7` |
| r3 `f8ec7ff` | 0 | 0 / 0 | 0 | `8e3cd55571baa9c48335121bbe198ce9062a54a19461946ba27b6a3a7e151acd` |

r2 行为此前 R1 实际结果；r3 行为本轮独立重跑。Git 自动检测 `core.ignorecase=true`，Hatch VCS 规则均为 0，没有强制改变本机 Git 设置。源码包的 30 个公开文件对照、两种 wheel 的各 15 个对照字节保持一致。`lowercase` 也在本轮退出 0；未因大小写修订丢失原小写排除。

```bash
uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_case_boundaries_r2.py case-variants
uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_case_boundaries_r2.py lowercase
uv run --locked python scripts/check_source_distribution.py
```

本轮独立执行候选的 241 私有 / 18 公开归档回归通过。该脚本在它创建的微型临时仓库内设置 ignorecase，以支持 Linux CI；R1 的旧探针和新增探针则使用本机自然检测值。大小写变体使用独立父目录，未发生 Mac 同名覆盖。实际 tar、从 tar 重建的 wheel 和直接 wheel 均验证成员字节与冻结 schema。

## 新增边界探针

```bash
uv run --locked --with hatchling==1.27.0 python reports/review/S0-SHARED-02/probe_additional_boundaries_r3.py
```

此脚本复用 r2 未修改的少量命令/归档读取辅助函数，只创建小型真实 Git worktree，复制当前追踪的公开文件，并加入随机合成字节。要求本机 Git 自动检测 ignorecase=true，不设置该选项，也不复制真实私有输入。

额外 45 个 Git 忽略文件覆盖缓存/工作目录、`.coverage`、`.DS_Store`、三种 py[cod] 后缀、根级 data/raw/processed/private 的大小写变体，以及 `.ENV.EXAMPLES`、`.eNv.ExAmPlE.private` 两个不得因 `.env.example` 例外而放行的名称。21 个公开对照包括三种大小写 `.env.example`、`.PYI`、`weights.PT.example`、`credentials.KEY.example` 和普通 JSON。

| 构建路径 | 私有泄入 | 字节保持一致的公开文件 |
|---|---:|---:|
| sdist | 0 | 47（现有 26 + 新对照 21） |
| 从 sdist 重建 wheel | 0 | 21（现有 14 + 新对照 7） |
| 直接 wheel | 0 | 21（现有 14 + 新对照 7） |

脚本在 Git 忽略集合、Git 可见公开文件和实际归档三处交叉核对。schema 摘要保持 `ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb`。各脚本场景有重叠，不相加为独立覆盖率。

## CPU、正常安装及继承范围

本轮实际运行 176 项 CPU 回归、冻结摘要、最终 lint 和公开扫描；命令及结果在 [evidence-r3.json](evidence-r3.json)。旧“恰一个 extra”历史快照未修改，也未计入 176 项。

```bash
uv run --locked pytest -q tests reports/review/P00/test_independent.py reports/review/P00-r2/test_revision_boundaries.py
uv run --locked python reports/review/S0-SHARED-02/verify_public_install_r2.py
```

第二条在只含 Git 追踪公开文件的新合成 worktree 中实际 `uv build`，再运行原 P00 隔离安装脚本。默认依赖 hash/check、schema digest、五类 CLI fixture、无源码树依赖和 no-ML 均通过。正常 sdist 为 87,889 bytes、SHA-256 `7d1e53cd0a824846abd4b679526e53d80eaa22c849b843284cd89245c7723a1f`；wheel 为 18,422 bytes、SHA-256 `8eaf706a2d3f24bb7d902f8ccda453a28431bc0783a02c882588b38848033ec2`。后者与前两轮正常公开产物相同。

完整新候选与上一审查 commit 的受保护路径比较退出 0：src/configs/tests、uv.lock、第三方说明、.gitignore、CI、docs/14、冻结摘要、PROTOCOL/GOAL、r1/r2 handoff 与原审查目录字节未变。TOML 结构对照确认 exclude 之外的项目字段、直接依赖、extra 和构建工具相同。前轮 69/90 环境、平台解析、固定制品与许可证据据此沿用；本轮未再次读取这些完整 ML 环境或重新下载上游制品。既有 MIT metadata / Apache LICENSE 差异仍明确保留。

初次 lint 退出 1，原因仅为 R1 新增探针的导入分组多一空行。仅删除该空行后，最终 lint 和新探针均重跑通过；候选和旧探针未修改，最初日志及脚本摘要仍保留。这项审查文件格式错误不属于候选产品缺陷。

## 证据与未执行项

[evidence-r3.json](evidence-r3.json) 包含实际命令、退出码、完整私有日志 SHA-256、新脚本与初版脚本摘要。原始日志和本机身份/路径仅私有保存，不把输出裁剪后的文本作为完整日志 hash。

**NOT_RUN**：ML 导入、模型/张量/GPU/训练、完整 ML extras 重新安装及 69/90 环境再次审计、来源重新下载、跨平台实机安装、P01/P02/P03 全包验收、D1 私有归档/解包日志、最终 GitHub CI 和 main 集成。本 PASS 限于精确共享候选；S0 完成最终 CI、合并和 main 验证后再发布新基线。
