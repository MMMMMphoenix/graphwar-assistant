GRAPH WAR 开源 BOT 参考源码

目录：references/oss
建立日期：2026-10-25
用途：把调研过的公开项目源码集中放在一个地方，方便以后查实现、跑基线、对照行为和核对许可证。

重要说明

这个目录是只读参考资料，不是本项目的一部分，不参与构建，不进入在线主链路。

目录里包含 GPLv3 项目和无许可证项目。除非逐个项目确认许可证，否则不要把这里的代码复制进 src，也不要把整个目录打包进公开发布物。我们的核心代码保持净室实现，只借鉴思路，不复制实现。

同目录下的 .gitignore 已把各仓库目录排除在版本控制之外，只允许提交 README.txt 和 MANIFEST.txt 这两份说明。如果确实要提交某个参考仓库，先单独确认许可证。

目录结构

GraphBot                  多表示弹道实验室，JavaScript 加 Python，MIT
GraphingSolver            人工点选折线编码器，Python，MIT
Graphwar-Bot              nico-fb 的人工航点加 S 形门工具，Java，无许可证
GraphwarBot               Scaleneee 的未完成项目，Python，无许可证
cheatclient               客户端修改项目，Java，GPLv3
copacaaa-graphwar-bot     简单直线和二次曲线加浏览器自动化，Python，无许可证
graphwar-aim              屏幕读取加网格动态规划瞄准器，Python，MIT
graphwar-aim-assist       进程内精确状态加分段动态规划，Java，GPLv3
graphwar-generator        人工点选加 DCT 余弦级数，Python，MIT
master-ferrari            AutoHotkey 覆盖层加人工折线，AHK，无许可证
zielmicha-graphwar-bot    人工点选加极限开关拼接，Python，无许可证

每个仓库保留原始目录结构和许可证文件，只删除了 .git 元数据。对应的提交哈希、远程地址和许可证见 MANIFEST.txt。

每个项目先读什么

GraphBot

先读 core/symbolic_ga_planner.py，看表达式树遗传算法的基因、交叉、变异和评分。
再读 core/polynomial_planner.py，看 16 系数多项式的闭式岭回归和目标点采样。
再读 core/pathfinding.py，看 100 乘 60 网格上的 A 星和拉绳简化。
再读 core/avoidance.py 和 core/detection.py，看屏幕读取和禁入区构造。
最后读 docs/MATH.md，看作者对多种表示的数学说明。

GraphingSolver

读 solver.py。重点是 sign 函数窗口、S 形函数窗口、折线拼接和末尾微小正弦。它展示的是人工点选工具怎样把任意折线编码成合法函数。

Graphwar-Bot

读 Graph.java。重点是人工点击的屏幕坐标换算、S 形门 y 除以 1 加 e 的负 100 乘以 x 加 x0 次方，以及多个门相加的写法。

GraphwarBot

读 solver.py 和 models.py。它只计算两点连线斜率，主程序为空。用来确认这是一个未完成项目，不要期待可运行基线。

cheatclient

读 README.md 和 functions.conf。functions.conf 里有台阶、尖峰、正弦台阶、定向正弦、斜坡等预设，是很好的函数形状词典。
不要读它的客户端修改实现来抄，GPL 和合规风险都不合适。

copacaaa-graphwar-bot

读 graphwar_bot.py 和 browser_bot.py。重点是直线和二次曲线的简单计算，以及浏览器自动化的雏形。没有障碍约束和搜索。

graphwar-aim

先读 graphwar_aim/solver.py。重点是按列推进的网格 DAG、精确线段与圆盘相交、平滑惩罚、粗网格到细网格、边距放松、RDP 简化、目标圆心重新锚定。
再读 graphwar_aim/formula.py。重点是把折线转成绝对值函数、系数精度升级和漂移检验。
再读 graphwar_aim/legit.py。重点是直线、抛物线、三次、正弦、正弦加斜率的闭式解和排序。
再读 graphwar_aim/vision.py、capture.py、simulate.py。看屏幕读取、坐标校准和自仿真。

graphwar-aim-assist

先读 source/src/Graphwar/AimAssist.java。重点是逐段竖直列动态规划、列间距 0.5、行间距 0.5、最大跳变 3.5、共线合并、贪心多目标、ReLU 斜坡输出。
再读 source/src/Graphwar/ComputerPlayer.java 和 Function.java。这是官方内置遗传算法的 Java 实现，可以看到完整的适应度和命中记录方式。
再读 GameData.java 和 Obstacle.java。看它怎样直接读精确状态、怎样调用游戏自己的碰撞和爆炸逻辑。

graphwar-generator

读 graphwar_fourier/main.py 和 lagrange.py。重点是 50 点采样、离散余弦变换、50 个余弦项输出。它适合当最后手段的基函数展开。

master-ferrari

读 master-ferrari.ahk 和 vision.ahk。重点是覆盖层交互、坐标换算、ReLU 折线拼接、剪贴板粘贴和自动回车。图像搜索只用来找自己的位置。

zielmicha-graphwar-bot

读 graphbot.py 和 graphloc.py。重点是 join_func 用 abs(x) 的 0.00001 次方做左右切换，以及递归拼接折线。func-join.fkt 是公式模板。

官方内置 ComputerPlayer 在哪里

本项目里的 Rust 版本在 graphwar/crates/server/src/bot.rs。它保留了种群 50、精英 5、变异 25、代数等于等级、敌方命中加 200 万、友军命中减 200 万、最近距离补齐到 100 万的设定，并增加了跨回合种群记忆。

Java 版本在 references/oss/graphwar-aim-assist/source/src/Graphwar/ComputerPlayer.java，配套阅读 Function.java。这个仓库是 GPLv3 的上游分支，只用于阅读行为，不复制进核心代码。

上游地址：https://github.com/catabriga/graphwar

为什么这些项目大多用屏幕读取，而不是协议

一句话回答：因为它们面对的是官方 Java 客户端或 Steam 客户端，这些客户端没有公开的 bot 协议；而屏幕是唯一个不修改客户端、又能跨版本工作的通用接口。只有 graphwar-aim-assist 走了另一条路，直接改游戏源码读内存对象，代价是 GPL、版本锁定和作弊争议。我们的 WebSocket 协议模式是这个本地 Rust 端口才有的东西，不是那些项目当时的可选方案。

展开说有五层原因。

第一，目标平台不同。

绝大多数项目写给官方客户端或 Steam 版。官方客户端的状态保存在 Java 进程里，画面只是渲染结果。外部程序想拿状态，只有两条路：读屏幕，或者注入进程读内存。官方没有提供外部 bot API，也没有文档化的房间和开火协议。graphwar-aim、GraphBot、Master-Ferrari 都选择读屏幕。

我们的项目跑在 Tiendepchai 的 Rust 端口上，这个端口自带版本化 JSON WebSocket 协议，协议版本 11，消息包括 hello、create_room、add_bot、set_ready、start_game、fire_function，服务端回 turn_started、shot_resolved、game_finished、state_sync。这是本地服务器的一部分，不是官方 Java 客户端的能力。拿它去解释 2020 年到 2024 年的屏幕工具，就像拿今天的 API 去问昨天的程序为什么不用。

这里有一个容易误解的点：上游 Java 版并不是完全没有网络协议。GraphServer/NetworkProtocol.java 里有一组数字消息，例如 FIRE_FUNC 24、NEXT_TURN 25、SEND_FUNC 26、SET_ANGLE 28。但它是客户端内部协议，没有公开文档，也没有为外部 bot 设计。要用它，得自己实现完整的客户端握手、房间状态、回合同步和版本适配，还要面对官方服务器是否允许无头客户端的问题。对一个只想做瞄准器的人来说，维护成本比屏幕读取高得多，所以多数作者不选它。我们的 WebSocket 协议不同，它有明确的版本号、JSON 结构和 add_bot、state_sync 这类为本地 bot 测试准备的消息，是服务端主动提供的接口。

第二，合规边界不同。

屏幕读取是外部观察。程序不注入、不读内存、不改客户端文件，很多作者因此在 README 里明确写“不做注入、不读内存、不自动开火”，把工具定位成辅助而不是外挂。它仍然可能违反服务条款，但至少不触碰客户端完整性。

进程内读取是修改客户端。graphwar-aim-assist 直接 fork 游戏源码，读 GameData、Soldier、Obstacle，调用游戏自己的碰撞函数，甚至替换 graphwar.jar。它拿到了精确状态，但付出了 GPL 传染、Java 8 版本锁定、每次上游更新都要重新适配的代价。

协议读取是服务端授权。客户端按协议登录、进房、等回合、提交函数，服务端负责结算。这是我们采用的路径。它既精确又不需要修改客户端，但前提是服务器本身提供这个协议。官方客户端不提供，所以老项目没有这个选项。

第三，需求层次不同。

这些项目是瞄准器。瞄准只需要知道“敌人在哪、障碍在哪、自己从哪出发”，像素级精度就够。士兵半径 7 像素，爆炸半径 12 像素，屏幕校准误差通常小于命中容差。它们不需要精确的地形图，不需要预测地形被削掉以后的样子，不需要知道对手的技能和偏好，也不需要跨回合价值。屏幕读取的近似性正好够用。

决策智能体不一样。要算暴露，就必须知道每一块地形被削掉以后会打开哪条火线；要算多杀，就必须知道爆炸半径内的所有士兵；要算对手回应，就必须知道回合顺序和剩余士兵。这些都需要精确状态。屏幕读取可以做，但会把误差带进决策，所以协议模式更合适。

第四，工程成本和路径依赖不同。

屏幕读取的难点在视觉，但 Graphwar 的画面恰好适合视觉：白底、黑色障碍、固定坐标映射、士兵是明显的圆。做一次校准和识别，就能跨地图复用。反过来，逆向官方客户端的网络协议要处理登录、房间、序列化、心跳、版本差异，工作量大且不稳定。对一个只想做瞄准器的人来说，屏幕是更短的路径。一旦视觉管线跑通，也没有动力再换。

graphwar-aim-assist 是例外，因为作者直接拿到了 GPL 源码，改客户端比写视觉更省事。但它也只能服务自己 fork 的版本。

第五，分发和用户体验不同。

屏幕工具可以打包成独立程序，用户打开游戏、打开工具、点几下就能用，不需要替换 jar，不需要装 Java 8，不需要管服务器地址。它还能加覆盖层、实时预览、剪贴板粘贴，交互很顺。协议客户端则要处理账号、房间、回合计时、断线重连，用户群体也完全不同。

所以正确的说法不是“屏幕读取比协议好”，而是：

在那个年代、那个客户端、那个需求下，屏幕读取是唯一低摩擦的通用方案。
在精确状态可用、又需要决策的情况下，协议读取是更好的方案。
graphwar-aim-assist 证明了精确状态的价值，但它用修改客户端的方式拿到，代价太高。
我们的本地 Rust 服务器把精确状态通过 WebSocket 暴露出来，所以我们可以既精确又干净。

这也是本项目的一个结构性优势：不是我们的视觉更强，而是我们不需要视觉。视觉只保留为离线标注、对照实验和可选适配器。

许可证与使用边界

MIT：GraphBot、GraphingSolver、graphwar-aim、graphwar-generator。可以在保留版权声明和许可证文本的前提下复用，但仍然建议净室重写，避免把第三方实现细节带进核心。

GPLv3：cheatclient、graphwar-aim-assist，以及上游 catabriga 的 graphwar 和 Tiendepchai 的端口。复制代码会让本项目变成衍生作品，必须整体按 GPLv3 发布。核心库不采用 GPL，因此不能复制这些代码。

无许可证：Graphwar-Bot、GraphwarBot、copacaaa-graphwar-bot、master-ferrari、zielmicha-graphwar-bot。没有许可证不等于公共领域，默认保留所有权利。只能读思路，不能复制代码、资源或大段结构。

无论哪种许可证，都不要把 references/oss 整个目录提交到公开仓库或打包进发布物。需要公开引用时，链接原仓库并说明借鉴的是哪一条思路。

如何更新

MANIFEST.txt 记录了每个仓库的远程地址和调研时的提交哈希。需要更新时，重新克隆对应仓库，核对提交差异，再替换目录内容。不要直接修改参考目录里的源码；自己的实验代码放在 benchmarks 或 analysis 下。

相关文档

OPEN_SOURCE_BOTS.md  逐项目方案、横向对比、基线建议、许可证分析
PROJECT_PLAN_V2.md   项目企划与核心命题
PROJECT_BLUEPRINT.md 工程蓝图、模块骨架、流程图、甘特图
