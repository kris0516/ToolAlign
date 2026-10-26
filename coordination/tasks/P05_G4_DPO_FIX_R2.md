# P05 G4｜DPO 终态输出预算修订 r2

owner E1；复用既有独立worktree，从S1派发的精确授权commit建立 `codex/e1-p05-g4-dpo-r2`。该起点包含原候选 `982cc1917d23b4004dbf9f683c685515eb390ea7` 和R1审查 `32a031b76a68a57945c6decce796ba6a9dd1836d`；先实际读取avoid-overkill。只做CPU修订，不分配GPU或编码真实偏好。

唯一问题 `P05-DPO-OUTPUT-001`，P2，首次正式未通过计1。[R1原始反例](../../reports/reviews/P05_G4_DPO_R1.md)：预算65,536字节，写最终summary前61,185字节，加入8,357字节summary后69,542字节，返回值及summary仍为PASS。S1已回读31份独立材料、确认24个候选文件及原始失败；原失败保留。

修订 `src/toolalign/training/cuda_dpo/runtime.py` 的终态预算核算：最终编码后的summary及必要终态写入必须计入完整输出；返回PASS前确认满足上限。为失败回执预留有限空间，超限明确FAIL并保留证据，不能通过删除已有输出、扩大冻结阈值或减弱断言取得PASS。以原反例补一个实质回归，同时确认普通成功及既有中途超限/子进程回收路径。具体实现保持简单，不重写训练循环或建立通用存储层。

允许上述runtime、相应DPO进程测试/fixture、新增 `reports/P05_G4_DPO_FIX_R2.md` 和 `coordination/handoffs/P05-g4-dpo-r2.md`。不修改data/models/trainer/checkpoint、协议或依赖锁、Colab脚本、共享状态和R1原报告。继续使用已安装的专用CPU环境，不重装或下载模型。

R1已支持的SUM/mask/梯度/reference及10对新进程恢复在未受影响时继续复用；无需重跑一轮训练、全部依赖或全部旧测试。交付精确commit、diff、实际定点命令/退出码、原失败到修订结果的证据索引，再由R1定点复审。当前真实80条生成产生0对偏好，DPO运行仍未放行；本任务只修工程边界。
