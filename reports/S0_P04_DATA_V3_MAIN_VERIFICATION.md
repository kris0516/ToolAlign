# S0｜P04 v3 数据接口主干收尾

2026-10-26（Asia/Shanghai）。结论：**VERIFIED（CPU 接口）**。

[PR19](https://github.com/kris0516/ToolAlign/pull/19) 以普通 merge 合入 `abdc53d468a270cc1bfecbe56980dd34918480e1`，head 为 `af72c48e5faf04ffc6ca3cc2076b5eb9c5771d3d`。原 R1-r3 PASS `f2f11e04a94cebb0ad658851d4e22a8452180556` 与两轮 FAIL 原 SHA 保持。最终 CI run `34174834740` 的 Python 3.11 / 3.14 全部步骤通过，每个 job 记录主检查 1,116 passed / 48 skipped，另有 P00 46 passed。

已有[隔离集成](S0_P04_DATA_V3_INTEGRATION.md)覆盖 CPU 组合、三归档和一次安装；初始路径相关失败及一次定点补验保持原状，不改写成一次全绿。

main 收尾核对生产路径 `src/`、`tests/`、`configs/`、`pyproject.toml`、`uv.lock` 与 PR19 head 无差异。2026-10-25 20:21 UTC，在 main 用已有默认 CPU Python 运行：

```text
python -B -m pytest -q -p no:cacheprovider \
  tests/training/test_sft_data_v3.py \
  reports/review/P04-sft-data-v3-r3/test_independent_io.py \
  --basetemp=NEW_EXCLUSIVE_TEMP
```

结果 **163 passed in 3.72s，exit 0**。禁用插件自动加载，临时根不位于私有目录祖先中。原 argv、输出和 Git 绑定保存在本机交接目录。生产代码未再改动，因此没有重复构建或重跑既有成功的全部 CPU 检查。

本次新增 GPU/模型/编码/训练为 0。修复后的真实冻结数据消费、CUDA runtime 与正式训练仍不能据此登记通过。
