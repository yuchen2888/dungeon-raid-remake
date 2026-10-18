# 符文围合与松手前置处理

后续更新（2026-10-17）：实际单格消除、奖励移动和到达入账已在新的联合场景接通，见 `MATCH-REWARDS-RECOVERY.md`。下文是较早阶段的验证记录，其未完成描述保留当时范围。
2026-10-16。此次恢复了 Game::ProcessRune 的圈内扫描、计数与调用顺序，并增加 ProcessInput 的高亮重置和松手前置处理。还没有完成实际单格消除和奖励入账。

## 游戏行为

符文开关启用、路径超过三格且首尾相邻时，原程序按行扫描圈内方块。它根据路径中每个选中方块的前后邻居改变“圈内/圈外”状态，并检查右侧仍有选中边界。扫描只处理中间四行，最后一列作为右边界。

拖动时，圈内方块计入资源预览，并获得高亮请求。松手时，它为符合条件的圈内方块调用 MatchTile，奖励类型参数为 5；类型为敌人且 enemy_type 不为 0 的方块不发消除请求，但仍计入圈内类型计数。实际请求数超过扣除桥接格的路径长度时，会请求成就 58、进度 100。代码保留这些判断，不自行猜测敌人名称或改成通用多边形库。

高亮计数重置位于 ProcessInput 0x16748..0x1674c，而不是长路径的 ProcessRune 内部。首轮独立函数验证通过后，连续手势对照发现了这个调用层差异；已增加 `dr_reset_rune_preview`，在通过输入门槛且触摸阶段非零时调用。不能在输入被阻塞时任意清零，也不能省略导致高亮数量累加。

## 源码入口与接法

- `recovered_rune.cpp/.hpp`：`dr_process_rune`，原地址 0xf7bc，字节范围 0x3b0 含常量；`dr_reset_rune_preview` 是额外恢复的输入分支，不计独立原函数。
- `recovered_stroke.cpp/.hpp`：新增 `dr_prepare_release`，按原顺序对棋盘发 Undim、执行 ProcessRune(true)、恢复选中尺寸并清 selected，再判断去向。返回后尚未执行路径 MatchTiles、卷轴效果、后续清理或回合调度。
- `SelectionEvent::ProcessRune` 应接到 `dr_process_rune`；资源预览接到已有 `dr_preview_resources`。
- 新事件 RuneAllocateHighlight、RuneHighlight 交给显示层；RuneMatchTile 交给后续实际消除实现；RuneAchievement 交给成就系统。
- 当前高亮事件携带格子索引和槽位，显示层从对应 tile.resting_position 定位。旧 QuadStrip 纹理构造和内存布局没有搬进新源码。

`stroke_demo.cpp` 展示完整接法，无旧二进制、Unicorn 或原生动态库依赖，直接编译恢复的 C++ 文件。它能走八格周边、得到一个内部高亮和金币预览 18，然后请求消除中间第 7 格；请求只打印，不假装已入账。

## 验证证据

`verify_rune.py` 实际执行原 ProcessRune 指令，原列表遍历保留。对照 native ARM64 的计数、匹配状态、分配/高亮槽位及有序消除/成就请求。

- 独立案例 594 个：不同大小和位置的矩形、正反方向、斜线、开口、短路径、禁用符文、不同格子和敌人、复用高亮槽、桥接格与选中标志异常组合。
- 连续手势 100 组，共 1,600 步：实际起笔、沿矩形延伸、停留、回退、松手前置处理、取消；输入、选择、符文和资源预览同时执行原指令。
- 其中 100 次松手前置处理使用有效金币围合路径，验证到原路线目的地为止。不是所有敌人/技能/卷轴组合的松手验收。
- 检查到 743 个 MatchTile 请求、55 个成就请求、849 个高亮分配、1,621 个高亮位置事件。数字来自上述测试中的事件量，不是新增独立测试数。
- 11 个模块通过 macOS ARM64/x86_64 与 iPhone ARM64 编译；独立源码示例退出码 0。

边界：旧集合存储、QuadStrip 绘图对象、声音、UI、平台 ceilf 是适配器；MatchTile 与成就效果只记录调用。部分独立案例在两端用相同适配器把被请求方块的 matched 标记置 1，用于验证状态共享，不能证明真实消除行为。ProcessPretzels 仍未恢复。输入门槛预先满足；有限坐标、0..5 棋盘坐标、0..6 格子类型和有效路径是接口约束。

复现：

```sh
sh recovered/build.sh
python3 recovered/verify_rune.py
sh recovered/run_stroke_demo.sh
python3 reverse-engineering/audit.py --reference reference
```

`rune_provenance.json` 保存原字节哈希；`release_prefix_provenance.json` 单列新输入分支；`rune_verification.json` 保存本轮结果和分支命中记录；`rune-native-build.log` 保存编译输出。

下一步是实际 MatchTile 的状态变化和奖励事件，再连接 AddResource 与补位。当前 App 的全屏、高清素材、中文、多语言和教程都尚未实现。
