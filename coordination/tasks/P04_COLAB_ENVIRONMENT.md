# P04-COLAB-ENVIRONMENT｜CUDA 锁与远程运行入口

状态：READY。owner E1；协调者 S1；code_base `61c2176d556fd0e4cfc2af00b16242dddcfadfd3`；authorization_commit 由原生派发提供。分支 `codex/p04-colab-environment-r1`，复用 E1 干净隔离 worktree并保留旧证据。先保存当前任务/AGENTS/GOAL与CUDA协议，再从 code_base 建分支。

目标：独立的Linux/Python3.12 CUDA环境锁、Colab setup/运行/恢复/回收入口与说明。允许 `requirements/cuda*`、`scripts/colab/`、`tests/colab/`、`docs/18_CUDA_RUNTIME.md`、`reports/experiments/P04_COLAB_ENVIRONMENT.md`、`coordination/handoffs/P04-colab-environment-r1.md`。共享依赖特许仅限新CUDA lock；不改pyproject/uv.lock、旧配置、生产训练或共享状态。与T1的接口通过S1协调。

独立锁定torch CUDA wheel、Transformers、PEFT、Accelerate及所需tokenizers/Jinja2/safetensors和传递依赖。Python3.12/torch2.8.0+cu128可作候选，不把另一项目通过当本项目通过。核对固定Qwen3和原生tokenizer接口：后者接受tokenizers0.22.2或0.23.2、Jinja2=3.1.6，不放宽旧守卫。TRL在G4锁定/验证，本包记录兼容候选即可。版本选择引用官方文档；尽快回报精确候选供T1的CPU数值测试使用。

安装与执行分离：setup仅安装/核对身份，不启动模型/训练、不重装本机CLI/认证。运行指定run ID、源码/配置/数据身份、任务输出与共享锁根，安装也计入时间。复用ADC/proxy包装；ToolAlign专有SSH配置先status确认实例存在，缺失不得裸ssh隐式创建。不得连接、停止或覆盖其他项目实例/目录。

tmux记录PID/日志/退出码；断连先查已有作业，不自动重复提交。同实例重连、新进程恢复、新实例重建分别记录。输出原子写实例盘再传ToolAlign专属持久目录并读回；Drive挂载不等于持久化。支持完整checkpoint取回Mac私有结果目录。回收成功后停止本任务实例并查会话。不keepalive绕限、不购买/充值、不开公网服务、不传无关资料。

本包资源：只读CLI help/sessions/status允许；GPU分配/SSH连接/真实模型下载或训练为0。允许解析Linux依赖锁，必要metadata/源码下载≤1GiB，不在Mac安装CUDA wheel。需要torch CPU测试时先回报精确依赖，由S1统一选择一个专用CPU环境；不各建训练环境。

验收（PLANNED）：锁在目标Python/Linux可解析；脚本语法和最小伪CLI/fixture验证setup不训练、缺session拒绝、已有作业不重复启动、失败退出保留、checkpoint回收/校验、只停止自有run；模拟不记作Colab实测。定点ruff/公开扫描。真实Linux安装/pip check、硬件、容量/跨实例恢复由S1签发GPU配置后执行。

交付精确提交、实际命令/退出码、锁与来源、setup/launch/status/recover/stop命令、私有路径占位说明、未验证项和handoff。R1复核、S1集成。首轮准备1.7B最重SFT探针：2–3完整step、验证、保存/重载和恢复一步；真实cohort/run ID/时限/输出上限由S1在代码就绪后固定，不自行分配GPU。
