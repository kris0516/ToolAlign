# P02 格式修复｜S0 组合预检

2026-09-06，S0。**修复与当前已验收 P01/P02/P03 的本地组合检查通过，最终独立审查交接、CI、合并与 main 验证仍待完成。** 本记录是新候选的实际预检；[原候选预检](S0_P02_FORMAT_PREFLIGHT.md)及其后来发现的 F1 失败保持。

## 精确组合

在 S0 的新隔离 worktree，从 main `758aa2cb87464bae46d192598806e03f69efe835` 普通 merge 完整修复 `8c439f683b9d6b04919ff1f7184d8924ccf82f9f`，产生本地 `50f7589e2d4bef486c682b8f96f0d63362adb3e9`，tree `88d44749bf3718daf3b8ab7f3024e8ddb93ef681`。277 份既有 main 文件和 37 份候选新增文件逐字节保持。集成分支未推送，main 实现未改。原未去敏 review 不在新组合祖先。

## 实际回归

08:42–08:55 UTC，离线 CPU，复用既有环境。第一组全部适用组合测试 **779 passed / 2 skipped，49.62s**，另组未改的原 R1 结构/统计检查 **60 passed / 0 skipped，0.11s**；两组不重叠，合计 **839 passed / 2 skipped**。两项跳过是 native 环境下的 HF 专属清理测试；本轮安装版 F1 复验不消除这两项 skip。候选的完整 reference 清理覆盖属于 D1/R1 的另组证据。Ruff、4 份冻结契约和 314 路径公开扫描均通过。

| 关键检查 | 原始日志 SHA-256 |
|---|---|
| 组合 pytest | `666c5d59b34e2b47f549ce078c480f0b2bf7c05a5c499be190d059e41d2ddb7e` |
| 原 R1 60 项 | `b746f5b04deb9a4a5ab9ad150ef96de12b7adc51f3b8f0c709ce03184f5e8501` |
| 新三归档与隔离接口 | `a83b240ad9877f9f9c5930a1bed3a1f4fb0a472e6cc6b2b5162ac8f4c533a25e` |
| 实际安装默认 wheel | `365ae21433f12056f6bb7558865a499a602e5deb4733c632ea7a53f1e908fa7f` |
| 安装版原 F1 / native | `34de549b057680752c4f3ba79e1b4cdedb4eb370559250ac0ff4448fa1489492` |
| 安装版原 F1 / reference，更正环境后 | `285e68d1f52cd7550ca2c864aac473be78b670a87f6ccc2dec358af7eb8d8e5b` |

复现命令与[原预检](S0_P02_FORMAT_PREFLIGHT.md)相同的全部组合测试路径保持，另组运行 `reports/review/P02-format/test_independent.py` 与 `reports/review/P02-format/test_audit_denominators.py`，分别使用新的独立 pytest 临时目录。完整实际 argv、UTC、精确 Git/tree、退出码与日志 hash 留在私有证据；没有更改全局收集规则或原测试。

## 新包与真实安装路径

| 实际归档 | Bytes / 成员数 | SHA-256 |
|---|---|---|
| sdist | 212228 / 100 | `068f03c74a6558f3f961ad76c6a93becb7b774ff05b34a09f98dc93f2f703956` |
| 默认 wheel，由同次 sdist 生成 | 107033 / 52 | `6c5674e403f27008b64e119b07def38e122856f958be4942358e23be336f1721` |
| 显式 sdist 重建 wheel | 107033 / 52 | `6c5674e403f27008b64e119b07def38e122856f958be4942358e23be336f1721` |

实际执行 `uv build --offline --no-python-downloads` 和对该 sdist 的显式 wheel 重建。未改的 D1 包探针核对归档实际成员、当前 Git 载荷及隔离安装；源码直接构建 wheel 为 NOT_RUN。47 个安装源码/资源匹配 Git 和 wheel，10 条纯默认安装/接口命令及 20 份输出流通过。`python -I -S` 从源码外执行的 12 例序列接口使用透明字符回调；实际 Qwen completion 输入来自原 native 结果的不变副本，不是本次新分词。

随后将本次**默认 wheel**另装入新 target，使用未改的原 `review_snapshot.py` 在 `-I -B` 下分别运行 native/reference。两者都实际触发原来源替换、恢复并完成真实 loader：声明身份与完整 backend 状态等于各自正常基线，`!` 保持 `[0]`。两个 result SHA 分别为 `8c9805d1c8af0040052e6682f03f8979be6af66f1ee36b58936ea1788359d117`、`a5672aeb79df254d9bb91651cff88824a2700a07d22c262687d4b8d08814663c`。每条路径的 7 个 ToolAlign 模块均来自新 target，逐文件匹配当前 wheel，checkout 生产模块导入为 0。

安装启动器以 D1 已交付版本为来源，仅选择本次实际 wheel hash 和 47 个实际载荷文件；没有改变原探针、tokenizer 或期望身份。native 复用 tokenizers0.22.2，reference 复用既有 Transformers5.16.1/tokenizers0.23.2/Jinja3.1.6、fsspec2025.3.0 的纯 tokenizer 环境。环境未修改、无新建环境或下载，实际检查无模型框架/模型模块。

## 保留的 S0 调用失败

reference 首次使用 P01 环境，该环境已安装模型框架，原探针在 `cpu_only()` 的“模型库不可用”前置断言停止，尚未构造 tokenizer。安装启动器随后要求已导入 ToolAlign，从而遮住原异常。保留首次 exit1 日志 `2800e885ae49fddcf4823501e960e835e63698f6d13fdc1cc7f018e8a9663f9f`；另存诊断启动器，仅增加原异常 traceback 输出，第二次同样 exit1，日志 `919f96c0579efc67e84d94af409cb4e54755ac99410acc9facce50fede05f0d1` 明确定位原前置检查。

成功调用使用原启动器和原探针，只更换 Python 为已有纯 tokenizer 环境，并使用新的输出目录。两个失败调用及诊断脚本均保留，没有补装或卸载依赖、弱化前置检查或改写生产实现。

初始八命令摘要 SHA-256 为 `a49ccddead2a56f9851d3c805d91dfe1ca9e972d9f38c137bccbb50b4a57bf19`；它先于安装真实路径扩展封存。后续五命令及失败/修正的附加证据 SHA-256 为 `e1b619a8642d4bcf35fef2e68a87e9cecc177a3ae82a9156c4a92aaed52b8fe6`。两阶段范围分开；包/默认接口摘要为 `c32ed0a8b7d1a1ce53c6cecdc241ace3f512bc3a3ebf7bc91cd2b842febc165b`。

本轮没有重新编码完整 8,228 行、建立训练选集、运行模型/GPU或代填人审。R1 正式精确候选结论与最终 S0 主干验收仍是下一门槛；G-DATA 和 P04 状态不变。
