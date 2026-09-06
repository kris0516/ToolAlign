# P03-base-r2｜共享基线同步交接

owner E1；2026-09-06；gpt-6-astra / max；原独立 App 任务与 `work/p03-execution-harness` 分支。状态：CPU 同步候选，仍等待 S0 安排独立 R1，尚未验收 P03。

## 精确提交与范围

- 原 P03 候选：`85e0905fc82da4504d73bf7eb489c1f1a0d227a7`；原实现：`8afb114bd14e69d3a2138212ab423147809fed63`。
- S0 生产 code_base：`37c00de9abe92e6fb24a0c0e0b7361aa4bb90385`；本轮 authorization/merge 目标：`f2a271be616cdb53c01e8d671029f31ae140c037`。
- 非强制 merge SHA：`86c5e8abaf0a6518fda0d33dba1b68eb6815737a`；tree：`969724e49233c44bd282694f973095a4cec0d3b0`；父提交恰为原候选和指定目标。
- 含本文的最终完整候选是 merge 后仅新增本文与本轮证据报告的文档提交；精确 SHA 及非强制 push/远端核对结果由 S0 最终交接消息给出。不要把 merge SHA 与完整交接 SHA 混淆。

没有 reset/rebase、修改其他 worker worktree、创建新任务或 sub-agent。合入的公共文件均来自 S0 指定提交；E1 没有手改公共代码/配置/依赖/CI/AGENTS/看板/ADR。本轮本地新增仅 `coordination/handoffs/P03-base-r2.md` 与 `reports/harness/P03_BASE_R2_VERIFICATION.md`。

## 原实现与证据保留

逐文件 SHA-256 比较确认：原 P03 的 17 个公开交付文件和 63 个本任务私有证据文件字节未变，包括原 P03-r1、实现、测试、fixtures 与原报告。P01/P02 源码相对同步目标差异为 0。保留原候选和全部历史记录；旧报告中禁止旧基线 sdist 的表述不覆盖新基线的本轮实际结果。

已读取并私存指定授权提交的 AGENTS/GOAL/PROTOCOL/PROJECT_STATUS、P03 同步段和共享 main 验证报告。原始身份、路径、授权副本、命令记录与安装制品留在本机私有目录，不提交公开仓库。

## 当前验证证据

详细真实命令、退出码、log hash、归档字节和限制见 [P03-base-r2 验证报告](../../reports/harness/P03_BASE_R2_VERIFICATION.md)。

- 当前 CPU 回归：**309 passed**，退出 0，日志 `cfa7ec544f2552516dcaf8a812b049c693e8461e141d84175c0b1b70457472c1`。组成是 P03 133 + 默认基础 58 + P00 独立 46 + P00-r2 72；不计旧 shared01 单 extra 的 57 项历史快照，也不混入 P01/P02。
- lint、冻结检查、公开扫描通过；原共享 canary 原样重跑通过，未扩大私有路径扫描。241 私有/18 公开与补充 45 私有/21 公开是两组有重叠的边界检查，不相加成覆盖率。
- 新基线实际 `uv build` 与 sdist 重建 wheel 均退出 0。sdist **112,760 bytes**，SHA-256 `a095ab30fbd3ffc35689253164be79b70dc0061d80078f80bb47c88d9a54178f`；默认与重建 wheel 各 **37,042 bytes**，SHA-256 均为 `e9d559cd0cfd17dc66b24f88455b1a138599a59faa476a34d3fb9d76c19a891c`。
- sdist 的 49 个追踪文件、wheel 的 24 个源码/资源文件逐项匹配 Git 字节；其余分别仅 PKG-INFO 和五个已知 dist-info metadata。未跟踪载荷、缺失文件、字节差异均 0。归档核对日志 `7109107e593c049a0d6d065a180dbff465aef461c85df79204f54543d2a1162c`。
- 从源码包重建的 wheel 在独立 CPU venv 中通过 **15 条子命令**：哈希依赖闭包、安装、pip check、冻结 schema、五类 fixture CLI、tools help/registry/demo、进程回收探针；总日志 `15948e3c943ffa303a4a77e090b5c69948d047ce45ee44e54797af1e663e5346`。
- 安装后的 scripted demo **10/10**，90 条合法 trace、20 个已启动自有进程全部回收。另四项真实阻塞检查分别验证工具/模型 timeout/cancel，4 个进程都确认 started/stopped/reaped 与实际 exitcode；无残留自有 PID/操作目录。

初版私有归档核对器漏列 Git 已追踪的 `.gitignore`，发生一次退出 1；初版程序与失败日志保留。修正只对该已知追踪文件补做精确字节比较，不放宽未跟踪载荷规则；未修改任何公共实现。详见报告的失败记录。

## 隔离构造限制与 NOT_RUN

独立安装运行在本任务私有隔离子目录，使用清除 PYTHONPATH/PYTHONHOME 后的 `python -I`。核对实际模块来自独立 venv、冻结资源 hash 与 registry hash 未变，未从源码包路径导入项目模块。

父进程 backend 必须轻量、可导入、可 pickle；generate 实际在持续的自有模型子进程中运行。registry 含锁/一次性签发记录，留在父进程；工具子进程按固定名称/hash/原生调用快照重建 registry。oracle/标签不进入 ModelInput。超时/取消只回收亲自创建并保存的 Process，经 join/必要 terminate/kill/join 确认不再运行及 exitcode 后才记 reaped。

真实已加载 MLX/Qwen 对象的跨进程兼容性、模型包导入、权重下载、GPU/训练/费用、真实 tokenizer/吞吐、正式隐藏测试、BFCL、P04/P06 扩展均 **NOT_RUN**。保留 3 决策/2 工具轮次/每次 256 token/候选统一 30 秒及预算不重置的原有条件。scripted 或 wheel 成功不是模型实验。

## 请求独立复核

请 R1 审 S0 消息中的最终完整候选，复核非强制合并来源、P03 原字节保留、当前 309 项口径、实际归档与安装后的 spawn/资源条件。E1 不给 P03 自签 PASS，不合并 main，不修改状态看板；非强制推送本任务分支后停止，等待独立 R1。无需 kris 重答既定硬件与协作约束。
