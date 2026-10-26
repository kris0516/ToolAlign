# P07 G6｜T1 服务 CPU r1 交接

2026-10-27，T1。分支 `codex/t1-p07-g6-cuda-service-r1`，基于精确授权头 `ef885c035f2b08a5ad781f040d4ee8867f2c79ba`；实现与测试精确版本为本交接所在 Git 提交，私有索引绑定源码哈希。实现范围和配置见[报告](../../reports/P07_G6_CUDA_SERVICE_CPU_R1.md)，HTTP 沿用 S1 [冻结契约](../../docs/18_RESTRICTED_CUDA_SERVICE.md)。

交付 fixed M1 prepare、service child 循环、单调截止/串行生命周期、loopback HTTP、principal/cache 隔离、只读 key 查回、幂等、取消、有限 journal 和 SIGINT/SIGTERM 清理。Colab 只修改 `scripts/colab/support.py` 固定入口及预算分支，无额外 controller 接缝。未改 client、共享 HTTP、contracts、依赖、registry、oracle、训练数学或共享协调状态。

149 项不同 CPU 检查通过，3 项既有 pip parser 检查因缺 pip 跳过。最终服务矩阵 25 passed，24 个运行的 35 个真实 child 全部回收；完整父进程两种信号退出均释放 lease 并保存 summary。独立原创 tiny CPU cache 子检查另有 1 个 child 回收，同 principal 命中 11 tokens，principal 切换清除复用，输出相同。三次含失败的命令及修正依据均保留，不能把其中两次退出码 1 写成整次检查通过。

私有证据入口：`.toolalign-local/p07-g6-cuda-service-r1/evidence-index.json`。最终服务输出绑定在 `final-process-evidence.json`；原始 HTTP 输入、accepted/started/terminal、worker ready/closed 和完整父服务进程 stdout/stderr 均保留。清理确认失败测试是明确标记的 MOCK_ONLY 分支，真实 child 已回收，服务仍保留 stopping/cleanup_unconfirmed。

S1 接入该精确提交后，与 E1 客户端组合交 R1 独立审核。生产入口为 `python -m toolalign.service serve --run-config <private-run.json>`，CPU 配置预检为同模块 `validate`；S1 冻结 auth 映射、端口、run 身份和最多 12 次实际尝试的 smoke 输入，实际 GPU 仍须另行授权。当前 **CUDA 服务、Mac→SSH→Colab 全链路和模型效果 NOT_RUN**；本包不自行合并 main、启动 GPU 或改写 G5 结论。
