BOTMAIN：Graphwar 求胜辅助器的工程目录

这里是真正要写代码的地方。决策、求解、感知、评估全部在本目录内完成。游戏本体不在这里，它在上一级的 game 目录；参考资料在上一级的 references 目录；企划书和工程蓝图也在上一级。

第一阶段的目标只有一个：把真实 Java 客户端的画面读准。

当前进度

已完成：窗口捕获（PrintWindow 离屏）、坐标区检测、士兵检测、障碍检测、队伍人工标注、不确定度字段、合成测试、真实截图回归、实机四人局验证。

未完成：坐标标定。现在是从白色矩形线性换算世界坐标，实机实测有偏差，详见 src/gwbot/perception/README.txt 第八到第十一条。标定完成之前，探针输出的世界坐标只能当近似值。

第一阶段任务清单

第一步，启动本体，进入一场自己和电脑的对局。

    bash ../game/run.sh

第二步，用窗口工具确认窗口和截图正常。

    py -3 tools/game_window.py info
    py -3 tools/game_window.py shot debug/menu

第三步，跑感知探针，肉眼核对调试图。

    py -3 scripts/perception_probe.py --window Graphwar --save-debug debug/probe

第四步，做坐标标定。先截两张不同射手的画面，比较黑色十字有没有移动；十字固定才能拿它锚定世界原点，会移动就只能靠试射或固定参考物。然后用试射标定像素到世界单位的比例，把结果写成配置文件，替换当前按矩形线性换算的做法。同时确认函数图像的原点：对局观察显示发射时函数以开火士兵为原点绘制，要用同一表达式在两个不同士兵位置各打一次来定案，并检查加常数会不会把曲线整体抬高。这一步完成之前不要开始求解器。

第五步，采集校准语料。每次截图存原图、检测结果和人工修正，放进 data/calibration 和 data/perception_benchmark。

常用命令

安装依赖：

    py -3 -m pip install -r requirements-perception.txt

跑测试：

    py -3 -m pytest -q

注意本机默认的 python 是 Python 2.7，所有命令都要用 py -3。

目录说明

src/gwbot/perception    屏幕捕获、检测、坐标区、状态适配、不确定度（已有代码）
src/gwbot/state         状态对象、信念状态、回放格式（第二阶段）
src/gwbot/sim           表达式解析、弹道、碰撞、爆炸、地形、校准参数（第二阶段）
src/gwbot/solver        函数族、代数种子、无梯度优化、多目标、地形改造候选（第三阶段）
src/gwbot/threat        敌方易发现度、发现概率、士兵价值、暴露增量、技能后验（第四阶段）
src/gwbot/decision      行动评分、一步安全、推荐生成（第四阶段）
src/gwbot/search        一步 expectimax、beam search、MCTS 接口（第五阶段）
src/gwbot/opponent      技能后验、风格统计、变化点检测（第八阶段）
src/gwbot/learning      候选先验、排序剪枝、价值网络、感知置信度（第十阶段）
src/gwbot/output        剪贴板、粘贴、热键、候选面板、人工确认记录
src/gwbot/ui            覆盖层、人工修正界面、设置
src/gwbot/eval          对局跑批、指标、消融、因子实验
src/gwbot/cli           命令行入口
scripts                 探针和一次性工具
tools                   测试用窗口驱动（点击、输入、截图），不是辅助器功能
tests                   合成感知测试、真实样本回归
data                    截图和校准语料，默认不进版本库
debug                   调试图和探针输出，默认不进版本库

边界

不修改游戏文件，不注入进程，不读游戏内存，不使用公开服务器和排位。默认由人确认开火。辅助器只截屏和粘贴文本。
