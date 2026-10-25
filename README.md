GRAPH WAR 求胜辅助器

从真实游戏窗口读取画面，识别坐标区、士兵和障碍，用校准过的仿真器预测弹道，用威胁模型和决策层选择动作，把函数推荐给人类确认。它不是协议 bot，不修改游戏文件，不读取游戏内存。

当前状态

版本 0.1，2026-10-25。

已完成：开源 bot 调研和源码归档；Java 游戏本体提取和启动脚本；屏幕感知模块；感知探针；合成感知测试；真实游戏截图回归；企划书和工程蓝图重写；目录整理，代码统一收进 botmain。

已完成的本体验证：Java 客户端窗口被 PrintWindow 离屏捕获成功；主菜单、创建房间、添加电脑玩家、进入实战画面都能走通；在实战画面上探针稳定识别出 6 个士兵和 12 个障碍，没有误检。

未完成：本体坐标标定（十字原点和像素比例，以及函数原点口径的试射确认）；感知基准集；仿真器；求解器；决策层；评估实验。

规划状态：企划已更新到 2.2 版。威胁不再按“敌人有没有解”计算，而是按“对手发现并打出来的概率”计算，由最简解的复杂度、解集体量和容差合成易发现度，再乘技能后验；函数图像以开火士兵为原点，求解器在射手坐标系里工作。

这个项目要回答的问题

在只能看到屏幕、状态存在误差的条件下，同一个感知和求解器，换一个决策策略，胜率能差多少；感知误差又会吃掉多少胜率。

计划用求解器强度 S0 到 S2 乘决策策略 D0 到 D5 的因子实验回答第一个问题，用 P0、P1、P2 三档感知消融回答第二个问题。

不是什么

不是自动瞄准外挂，默认不自动开火。

不是协议 bot，不依赖非官方服务器协议。

不是端到端神经网络直接输出函数。

不用于公开服务器、真人排位或未经授权的环境。

快速开始

启动游戏本体（需要 Java 8 以上）：

    bash game/run.sh

等价命令是进入 game 目录执行 java -jar graphwar.jar。jar 只保存在本地，不提交、不分发。

新机器上先安装依赖（在 botmain 目录里）：

    cd botmain
    py -3 -m pip install -r requirements-perception.txt

注意本机默认的 python 是 Python 2.7，所有命令都要用 py -3。

跑合成测试和真实样本回归：

    py -3 -m pytest -q

分析一张已有截图：

    py -3 scripts/perception_probe.py --image shot.png --shooter-index 0 --allies 1,2 --save-debug debug/probe --json debug/probe/state.json

分析真实游戏窗口：

    py -3 scripts/perception_probe.py --window Graphwar --save-debug debug/probe

探针会打印坐标区矩形、每个士兵的世界坐标和像素坐标、队伍标签、不确定度，以及每个障碍的圆心和半径。它不会求解，也不会输入任何内容。

游戏本体

game/graphwar.jar 是真正的 Java 客户端，是整个项目唯一的本体。它不是任何人复刻的仿真软件。之前本地拉取的 Rust 项目 graphwar 是别人逆向复刻的还原版，现在只作为阅读参考。

本体来源是 references/oss/zielmicha-graphwar-bot，源仓库没有许可证文件，jar 按上游 GPL 客户端理解。它只保存在本地，已加入 .gitignore，不随项目发布。

文件大小 607525 字节，SHA-256 为 b44c5f9bc0a6885f6ff8eb7f315fe3913fa9e3482f3fb5ee9a4f2471c70a5111。

实测画面几何：窗口标题恰好是 Graphwar，游戏画布 800x600，绘图区白底黑框，左上角约在 14,14，可见大小约 755x451。绘图区里的黑色十字竖线约在 x=400，横线约在 y=240，二者并不等于白色矩形的几何中心；这个十字是固定的世界原点还是跟着当前射手移动的坐标轴，还要用两张不同射手的截图判定。所以坐标标定要以十字或试射为准。详细说明见 game/README.txt 和 PROJECT_PLAN_V2.md 第十四节。

函数语义：对局中观察到发射时函数图像以开火士兵为原点绘制，表达式里的 x 是相对射手的水平距离。求解器因此在射手坐标系里工作，候选表达式换算到世界坐标时再加上射手位置。细节（入参口径、常数是否被抵消、起点取中心还是边缘）还要用试射确认，见企划 1.2 和 4.1。

目录

game                    Java 游戏本体、启动脚本和工作说明，jar 只保存在本地，不进版本库
botmain                 辅助器工程：感知、状态、仿真、求解、决策、评估
botmain/src/gwbot/perception    屏幕捕获、检测、状态适配、不确定度
botmain/scripts         感知探针和一次性工具
botmain/tools           测试用窗口驱动，点击和输入，不属于辅助器功能
botmain/tests           合成感知测试和真实样本回归
botmain/data            截图、校准语料、会话日志，默认不进版本库
references/oss          开源 bot 参考源码，只读，不进版本库（只保留 README 和清单）

文档

PROJECT_PLAN_V2.md      企划书：研究问题、算法、评估、路线图
PROJECT_BLUEPRINT.md    工程蓝图：分层、骨架、流程图、甘特图
OPEN_SOURCE_BOTS.md     开源 bot 调研和许可证边界
botmain/README.txt      工程目录说明和第一阶段任务清单
botmain/src/gwbot/perception/README.txt    感知层说明
THIRD_PARTY_NOTICES.txt 第三方许可证声明

数据与隐私

截图和会话日志可能包含玩家名字，默认不提交。提交示例图之前要脱敏。

许可证

本项目计划使用 MIT 或 Apache-2.0。当前直接复用的 graphwar-aim 和 GraphBot 代码都是 MIT，声明见 THIRD_PARTY_NOTICES.txt。GPL 和无许可证项目只作阅读参考，不复制进核心代码。

使用范围

只在自己创建的房间、离线模式或与内置机器人对战中运行。不使用公开服务器，不参与排位，不影响其他玩家。
