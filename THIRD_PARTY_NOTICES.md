# Third-party sources and publication boundaries

原创 ToolAlign 文档和未来原创代码采用 MIT。MIT 不重新授权任何上游模型、数据集、库、商标或私有项目内容。

- ToolACE：数据卡当前标注 Apache-2.0。下载时保存许可、revision 和源链接。
- Salesforce xLAM 60K：数据卡当前标注 CC-BY-4.0，且要求确认访问条件。默认不自动接受或镜像发布。
- Qwen3 模型：使用下载时对应模型的准确许可与模型卡；独立保存原始来源、量化/adapter 转换记录。
- MLX/MLX-LM 与社区 DPO 依赖：按锁定版本读取其 LICENSE，生成实际依赖清单；不要把所有依赖概括成 MIT。
- BFCL：代码与数据分别核实对应文件许可；使用官方 evaluator 不代表可无限重分发全部样本。
- LiDARFoodAgent：本项目不引入其私有源码、AGPL 代码、用户资料、设备捕获或云配置。未来若复用须独立决定许可兼容与授权。

详见 [来源登记](docs/09_SOURCES.md) 和 [数据治理](docs/02_DATA_GOVERNANCE.md)。本文件是工程发布清单，不替代逐项许可审查。
# P00 CPU dependency note

P00 使用 jsonschema 4.26.0 及锁定的传递依赖；测试与打包使用 pytest、ruff、hatchling、uv。版本和来源解析记录于 `uv.lock`/`pyproject.toml`。这些包各自保留上游许可证，仓库 MIT 仅覆盖原创内容；没有复制它们的源码或重新许可。正式模型/数据的许可验收仍由 P01/P02 完成。

## P01 optional compatibility dependencies

可选 compatibility extra 只含固定版本的 MLX、MLX-LM、PyTorch 与 psutil，传递依赖由 uv.lock 记录。PyTorch 2.14.0 的分发许可为复合 SPDX，不能将所有内容概括为 BSD；准确元数据链接与限定见 [兼容性环境](docs/14_COMPATIBILITY_ENVIRONMENT.md)。mlx-tune 尚未作为正式 DPO 依赖纳入。

ToolACE 历史监督数据固定来源 revision 与 Apache-2.0 声明，适配与署名按 [来源政策](docs/13_TOOLACE_SOURCE_POLICY.md) 保存。数据描述不提供真实 API 的执行授权，也没有将来源工具宣称为只读。
