GRAPH WAR 屏幕感知层

用途

从真实游戏窗口读取画面，识别坐标区、士兵和障碍，输出带队伍标签和不确定度的世界状态。这个目录只做感知，不做决策，不做函数求解，不修改游戏文件。

来源与许可证

vendor/graphwar_aim 来自 graphwar-aim，MIT，Copyright (c) 2026 RE22GDV。保留了 capture.py、vision.py、geometry.py 和裁剪后的 config.py，去掉了求解器、GUI 和应用逻辑。

window_capture.py 的 PrintWindow 逻辑来自 GraphBot，MIT，Copyright (c) 2024 KroSheChKa。只保留窗口客户区离屏截图，去掉了浏览器界面、规划器和配置文件。

完整声明见项目根目录 THIRD_PARTY_NOTICES.txt 和 vendor/graphwar_aim/LICENSE。

安装

需要 Python 3.10 以上，以及 numpy、opencv-python、scipy、Pillow。Windows 上建议安装 pywin32，用于离屏截图；没有 pywin32 时会退回桌面截图。

    py -3 -m pip install -r requirements-perception.txt

在 botmain 目录跑感知探针和测试：

    py -3 scripts/perception_probe.py --window Graphwar --save-debug debug/probe
    py -3 scripts/perception_probe.py --image shot.png --shooter-index 0 --allies 1,2 --json debug/state.json
    py -3 -m pytest -q

合成测试只验证坐标换算和标注逻辑，不验证真实游戏。真实游戏截图必须人工看一遍调试图。

目录

vendor/graphwar_aim/capture.py    窗口枚举、DPI 感知、桌面截图
vendor/graphwar_aim/vision.py     坐标区、障碍、士兵检测
vendor/graphwar_aim/geometry.py   像素坐标与世界坐标互转
vendor/graphwar_aim/config.py     世界边界和视觉阈值
window_capture.py                 Windows PrintWindow 客户区离屏截图
state.py                          队伍标注、不确定度、状态对象、截图入口

最小用法

    from gwbot.perception.state import capture_state

    state, frame = capture_state(
        title_substring="Graphwar",
        shooter_index=0,
        ally_indices=(1, 2),
    )
    print(state.describe())

返回的 state 包含：

    shooter       当前开火的士兵
    soldiers      所有士兵，带 team 和 uncertainty
    obstacles     所有障碍圆，世界坐标和半径
    plot_rect     画面里坐标区的像素矩形
    source        printwindow 或 screengrab
    notes         感知备注

分析已有截图

    from gwbot.perception.state import analyze_image

    state, frame = analyze_image("shot.png", shooter_index=0)
    print(state.describe())

保存调试图

    from gwbot.perception.vendor.graphwar_aim import vision

    scene = vision.analyze(frame)
    vision.save_debug(frame, scene, "debug")

队伍标注

第一版采用人工标注，因为自动识别队伍会把感知错误带进决策。调用时传 shooter_index 和 ally_indices。索引就是 state.describe 里打印的编号。

如果不知道索引，可以先不传 shooter_index，再传 shooter_xy 给出大致的己方世界坐标，模块会选最近的士兵。

后续可以接入 GraphBot 的黄色身体加红色圆环检测，自动找当前行动的士兵；队伍仍建议人工确认一次。

已知限制

第一，坐标区检测假设画面是白底黑障碍。换主题、换分辨率、窗口被遮挡或缩放比例变化时，需要重新校准阈值。

第二，士兵检测依赖鲜艳颜色和固定尺寸范围。名字牌、弹道轨迹、重叠士兵、死亡动画都可能造成漏检或误检。检测结果应当允许人工增删。

第三，障碍检测只输出圆。真实地形被爆炸削掉后，下一回合重新截图即可得到新地形；但同一回合内自己这一发的爆炸效果要用本地仿真预测。

第四，屏幕坐标有误差。state 里的 uncertainty 目前按一个像素折算，实际误差要用真实游戏截图标定。决策层应当把它当作概率或安全边距，而不是精确值。

第五，这个模块不识别回合、倒计时、游戏模式和比分。第一版建议用快捷键触发分析，人确认当前是自己的回合；后续再加状态栏识别。

第六，PrintWindow 在 Chromium 系窗口上可能返回全黑，例如本地 Rust 端口跑在 Edge 里时就是这样。capture_frame 会检测空白帧并退回桌面截图，但桌面截图带浏览器边框，坐标区和检测都会偏。真实目标是 Java 客户端窗口，这个回退只用于诊断，不用于生产。

第七，本地 Rust 端口的主题是米色底、深绿障碍，和真实 Java 客户端的白底黑障碍不同。默认阈值在本地端口上会漏掉全部障碍，还会把爆炸粒子当成士兵。不要用本地端口做感知验收；它只用于跑通捕获链路和决策仿真。

第八，Java 客户端的绘图区和经典布局不完全一样。本机实测：黑框在左上角约 14,14，可见区域约 755x451，右侧紧贴一条滚动条样式的控件，会遮掉少量像素。检测出的坐标区矩形大约是 15,15 到 775,475，比真实黑框大几像素。按矩形做线性换算时，边缘处的世界坐标会有约半个单位的偏差，底部和右侧最明显。

第九，Java 客户端的黑色十字不等于白色矩形的几何中心。实测竖线在 x 约 400，横线在 y 约 240，而矩形中心是 391。所以坐标标定必须用十字或试射锚定原点，不要用矩形居中。还有一个待验证的问题：游戏里函数图像以当前射手为原点绘制，如果画面上这条十字也是跟着射手移动的坐标轴，那它就不是世界原点，感知拿它当全局锚点会在换人时整体偏移。判定方法是截两张不同射手的画面比较十字位置。在这两条都做完之前，探针给出的世界坐标只能当作近似值，不能直接拿去开火。

第十，Java 窗口是 DPI 非感知的，而感知进程开启 DPI 感知，所以 PrintWindow 截出的位图可能大于真实客户区，多出来的部分是黑边。绘图区检测不受影响，但任何屏幕坐标换算都要小心。给窗口发鼠标事件时，建议直接用客户端坐标 PostMessage，不要走屏幕坐标。

第十一，实测通过。在这个 Java 本体的一场四人实战中，探针用 PrintWindow 抓到一帧，识别出 6 个士兵（与画面一致）和 12 个障碍（含相邻小圆各自成圆），没有把名字牌或爆炸标记误认成士兵。这证明捕获、坐标区检测、颜色分割到世界坐标输出的整条链路在真实本体上是通的，剩下的主要是标定精度问题。

和游戏本体的关系

这个方案不读取游戏内存，不修改游戏文件，不依赖私服协议。它只截取真实游戏窗口，所以对游戏版本相对独立。代价是状态是近似的，必须用不确定度和安全边距来吸收误差。

游戏本体是 game 目录下的 Java 客户端，启动命令是 bash game/run.sh。所有几何常量、函数语义、爆炸半径和地形移除规则，都要用它的截图和试射校准。

本地 Rust 项目只是逆向复刻的阅读材料，不参与感知，也不是真值。

下一步

第一，做 Java 本体的坐标标定：用黑色十字锚定世界原点，用试射标定像素比例，把结果写成标定文件，替换现在按矩形线性换算的近似做法。

第二，标定像素误差，把 uncertainty 从固定值改成按检测置信度估计。

第三，接入 GraphBot 的当前行动士兵检测，减少人工点击。

第四，在感知层之上接入威胁图、候选生成器和决策评分。

第五，加入试射校准模式，记录函数、预测轨迹、真实落点和地形变化，建立真值回放集。
