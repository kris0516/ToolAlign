# P04 CUDA：实际容量输入

2026-10-26。**新入口的prepare、20条编码及portable reader回读均PASS，待Q1增量复核。** 来源为[PR21](https://github.com/kris0516/ToolAlign/pull/21)合并提交 `920c41551f0f7f2be8a5a8dcced23cc080ac1f27`，其整棵树与已审head `0e52598c12db82960727b868a2b2adf3914b989d` 一致。[最终Linux CI](https://github.com/kris0516/ToolAlign/actions/runs/40246480269)的Python 3.11与3.14全部步骤通过；T1/E1/Q1前置证据见[CPU集成记录](S1_P04_CUDA_INTEGRATION.md)。

## 范围与实际结果

| 项目 | 结果 |
|---|---|
| prepare | 独立无框架进程，exit 0，80.87秒；再次验证冻结v3与13例，暂存20条，新增编码0 |
| encode / reader | 新进程使用tokenizers 0.22.2、Jinja2 3.1.6；exit 0，2.13秒；新增编码恰好20条，完整数组回读通过 |
| train | 固定18条，长度2044–2048，bucket2048，按原selection rank消费，组为8+8+2 |
| validation | 固定2条，长度1851与1882，bucket2048 |
| 13例预审沿用 | 新prepare导出的review数组与已通过Q1预审逐字相同；10条train材料、3条protocol-only材料 |
| 模型/tokenizer身份 | Qwen3-1.7B，revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`，固定模板与文件身份 |

两条实际命令均使用同一源码提交，命令记录器确认执行前后文件不变。prepare内限240秒、外限300秒；encode内限120秒、外限180秒；各最多20条、输出至多128MiB。Mac只做数据准备与tokenizer编码，GPU分配和真实模型加载均0。

## 输入与回执身份

| 实物 | SHA256 |
|---|---|
| CUDA配置 | `3d4785e1e130dd04990abb3767c23d92cdb7b18dad1d30cc6991f976cd44c9c4` |
| 固定cohort | `48d66f48010dc0d0ce6db5bc64ac5e7223aa79fe7824f7ca623e6449f4adedeb` |
| prepare命令回执 | `1ad4692fac91716011d3bd3b886ba29170bb8556843b4ef540dc79841a8762b5` |
| encode命令回执 | `94808db570e6e1f89a31118f797c9113476a586d18934ba91dbdaaf428234d32` |
| stage manifest | `4ae93d53a8490c0c21c307b75213344408afe9a42a9aafbf87838ccae61e0f0a` |
| 13例review数组 | `cc82ba3cc030ac990e741bd5fa0a735009f6cb2498ec0b1b30523daa1c3649d3` |
| array manifest（10,984 bytes） | `fb429fe3767a5571f0c08369cf1c6705a0584ec11e83e0913a73dcfaa57a4536` |
| train数组（790,488 bytes） | `017d9ed1dfad71daf2be2192b59b1dffbe165df159bc8d384d992d69537eaa7e` |
| validation数组（91,945 bytes） | `7852256b10d27f9f48d02010ca43c5f064eb180b27c601460955a357967cd387` |

原命令为 `python -m toolalign.training.cuda_sft prepare --request PREPARE_REQUEST` 与新进程中的 `encode --request ENCODE_REQUEST`；实际绝对argv、请求、原始stdout/stderr及全部材料保存在本任务私有证据目录。两次执行均成功，没有覆盖先前消费或CPU集成的失败记录。

这是容量诊断输入，完整formal profile仍为5,938 train / 213 validation。实际CUDA三步、完整checkpoint的新进程及新实例恢复、正式epoch和模型效果均尚未运行；下一步是Q1核对本批实际数组后，S1签发有限GPU配置。
