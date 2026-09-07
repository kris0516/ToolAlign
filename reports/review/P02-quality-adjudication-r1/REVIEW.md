# P02 新版数据与材料 — R1 技术独立审查

结论：**PASS；P0=0、P1=0、P2=0**。本结论只对应精确候选 `1c47e6af6af3e3419db97bdbb1296e6f56e04c2b` 的 CPU 技术范围，Q1 语义/处置验收与 G-DATA、P04 仍需分别完成。

R1 使用现有独立 Codex 任务、gpt-6-astra / max；授权 `d9e5622c4148896803f92c53caf615975ef5254c`，生产基线 `6c81dfcc855fca188181d1bb08870f47d8edacc9`。逐项审查全部 12 个新增文件，492 个候选文件中的 480 个基线文件未变。原 v1、Action JSON、契约与依赖保持。配置逐字匹配 S0，217 项冻结输入没有替换为更新的台账。

## 数据与选择

在已有 wheel 的隔离安装中实际构建一次新版，并完成 verify。R1 复查并运行不导入 producer 的 stdlib 交叉检查，将这次构建与 D1 原构建比较：29 个稳定文件逐字节一致，manifest SHA 为 `0b0fdb79f728256dac42ddba75e0f3fc43aebb9502f2e9097398a482d5774251`。

80 来源的全部 98 条决策排除，3 来源/3 决策恢复原字节；7,651 条有效 Example 的原始 JSONL 行、lineage、group/split 与顺序保持。受影响 group 内其他 5,182 来源/5,553 决策保留。profile 沿原名单过滤，保留父 rank、不补选；仅一个恢复例原本具备两个 train profile 的选择资格，其他两个没有获得新资格。旧三份 staging 不晋升。

| 集合 | train | validation |
|---|---:|---:|
| 有效全集 | 7,421 | 230 |
| formal | 5,940 | 213 |
| smoke | 1,583 | 194 |

formal 比原 6,000 下限少 60，按 ADR-0024 如实登记。训练绑定为 false；安装后的旧 SFT prepare 实际拒绝新版 selection，错误为 `private_selection_manifest_mismatch`，后续需要单独适配及配置授权。

## 材料与原始执行身份

本轮只执行一次固定 13 例静态核验。安装版 compare 和 R1 完整数组/HTML 检查覆盖两路径的 26 份记录、39,936 行 token 表及 1,340 个观测 token ID 的文字一致性；完整 P/C、IDs、loss/causal mask、唯一追加 EOS、右 padding、原长度审计与新 revision/freeze 绑定通过。两路径各 28 份材料 payload 与原件字节相同，语义判定列仍为空，浏览器实显 NOT_RUN。

原编码实际发生在 11:09–11:11 UTC，当时 HEAD 为 `6c81dfc`，新模块尚未提交；真实源码由原 dirty epoch 绑定。`d64531c` 是后来保存相同源码字节的提交，不是原执行 HEAD。后续 `f7acd93` 仅静态重封装；本轮真实分词、模型/框架/GPU运行均为 0。原 `349e9540` manifest 的来源/决策分母误标及两份旧构建保留，修订只更正该元数据，28 份数据 payload 不变。

## 回归、归档与保全

默认纯 CPU 回归 **766 passed / 48 skipped**，其中包含 D1 新增 53 项；[R1 原创边界反例](probe_boundaries.py)另 **9 passed**。48 项额外真实 tokenizer fixture 和不受修改影响的旧 427 项报告分组没有补跑；没有把 D1 的 1,193 或 110 subtests 算成本轮执行。Ruff 和四文件契约冻结通过。

现存 sdist 134 成员、两份 wheel 各 67 成员，RECORD、metadata 与 62 个包文件绑定候选；两 wheel 字节相同，没有重建归档。只进行一次已有 wheel 临时 target 安装，`-B -I -S` 下 help/build/verify、材料核验及配置/旧 SFT 拒绝检查通过，源码 cwd 导入为 0，未添加环境或依赖。复核工具见 [归档检查](check_archives.py)、[材料检查](check_materials.py)。

复核 D1 57 条原 wrapper 命令、1 条封存命令、6 条安装命令及 15 个源码 epoch。结束检查覆盖 26,308 条输入路径、533 个链接，原 R1 的 504 个公共文件明确映射原 Git/快照；候选、旧私有封存与根身份均保持。原五项 D1 失败及三项 wrapper 启动事件继续留存。

R1 自身的辅助错误也全部保留：首次默认测试启动缺少 multiprocessing 入口保护，且私有 basetemp 破坏三项公共输出反例的环境假设，已中止并保留原 `18 failed / 341 passed / 17 skipped` 及嵌套输出；更正启动脚本和普通临时目录后得到上述有效 766/48。归档检查的等价版本约束顺序误判、保全脚本提前读取自身终态回执、两次只读枚举错误亦有原始记录。被审实现没有因此改动；这些辅助尝试不构成候选正式修订失败。结束时未发现本轮遗留 Python 进程。

全部 argv、UTC、退出码、stdout/stderr、原始失败和源码映射由私有封存提供；公开摘要见 [EVIDENCE.json](EVIDENCE.json)。最终公开扫描、精确范围、提交/普通推送及远端回读回执由终态封存和原生交接绑定。R1 不修改协调台账、不合并 main、不代替 Q1 签语义通过。
