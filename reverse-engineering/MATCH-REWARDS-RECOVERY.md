# 消除与奖励流程源码恢复

更新：2026-10-17。原版 Dungeon Raid 1.3.4。

后续同轮接入已完成整条路径：最新示例为 9 格消除、25 帧后金币 0 → 18，见 `PATH-INTEGRATION.md`。下文保留先恢复单格奖励阶段的证据；当前 rewards_demo 已升级，不再是仅圈内一格的旧示例。

本轮将符文圈内消除从“发出请求”接成了实际的消除状态、奖励生成、移动到达及资源入账。新代码可独立编译运行，不需要旧游戏二进制。它是依据原指令重建的可编辑源码，不是作者原工程，也不是已经可玩的完整游戏。

## 可直接复现的结果

在包根目录运行 `sh recovered/run_rewards_demo.sh`。

示例圈选 8 个周边金币格，识别圈内第 7 格；松手后将该格标为已消除并生成一个奖励。以每帧 1/60 秒推进，奖励在 22 帧后自行到达，金币 0 → 2，再推进一帧仍为 2。预览显示 18，因为它包含周边 8 格加圈内 1 格；当前示例只提交了符文圈内这一格，周边路径并没有冒充已结算。演示退出码为 0，日志见 `rewards-demo.log`。

目标位置由无界面示例提供，尚未接入手机 UI。全屏、HD、美术替换、中文显示和教程均尚未实现。

## 新源码与原版证据

| 源文件 | 原版入口 | 已重建行为 | 明确边界 |
|---|---|---|---|
| recovered_match.cpp | Game::MatchTile 0xbe60 | 重复消除保护、破损/特殊状态、连锁爆炸、敌人掉落、额外奖励概率、职业卷轴请求、成就请求 | SetSpecialType、Shapeshift、粒子/音效/提示仍为接口 |
| recovered_tokens.cpp | Game::AddToken 0x9890 | 奖励槽分配与复用、初始化调用、普通/额外奖励计数、特殊模式分数计算 | 通过 Initialise 回调接入 motion；计数不是玩家资源 |
| recovered_resources.cpp | Game::AddResource 0x12ee8 | 治疗、酸伤、技能充能、伤害奖励、金币/经验/升级进度、小数加成累计、升级阈值、护甲补充 | Healing、CheckEndGame、菜单与 UI 事件由调用者承接 |
| recovered_motion.cpp | Token::InitialiseFromTile 0x21448、Token::Process 0x21644 | 奖励类型、随机初始方向/速度、目标解析、逐帧运动、缩放、到达判定 | Interface 目标坐标与特殊目标选择、绘图接口 |
| recovered_random.cpp 新增入口 | Rand(float,float,RandType) 0x1b7a8 | 浮点范围随机，保留原种子推进和 float32 运算顺序 | 本批主要验证奖励使用的随机流 0；不是全输入证明 |
| recovered_motion.cpp 部分主循环 | Game::Process 0x1744c–0x174db、0x17d56–0x17d63 | 活跃奖励逐项推进、到达时入账、目标为棋子的特殊分支、菜单/死亡中断、裁掉尾部失活槽 | 只恢复该子段，不计为完整 Game::Process |

目前共 15 个 C++ 模块、46 个具名恢复流程，另列 ProcessInput 和 Game::Process 的部分代码。数量不是游戏完成百分比，具名流程也可能保留上述外部接口。

MatchState 直接引用 StrokeState 的棋盘和 ResourcePreviewState 的参数；ResourceState 引用同一个 MatchState；奖励初始化推进同一份随机种子。因此这条演示没有为每个模块另造一份互不关联的棋盘。较早的 Round/Battle 模块仍有重复状态字段，尚待统一接入。

## 实跑验证

| 脚本 | 本轮通过范围 | 验证方式 |
|---|---|---|
| verify_match.py | 1,311 场景 / 3,277 次单格调用；100 个手势 / 1,300 步 | 原 MatchTile 递归、GetRewards、真实 RNG 与 C++ 比较状态及有序事件；本阶段 AddToken 仍为边界 |
| verify_tokens.py | 442 场景 / 1,634 次入队；再接 1,311 消除场景与 100 手势 | 实际执行原 AddToken；本阶段 Token 初始化为请求适配 |
| verify_resources.py | 1,584 场景 / 5,904 次入账；100 手势及 400 次显式注入普通金币到达 | 实际执行原 AddResource；注入时刻明确不是动画完成证明 |
| verify_motion.py | 923 次初始化、20,627 个独立逐帧比较、54 个运动边界、593 次队列子段推进 | 原初始化、运动、浮点 RNG、归一化、Clamp 和主循环奖励子段真实执行 |
| 同上，联动 | 20 个围合手势，60 个金币奖励自行到达并入账；16 组菜单/死亡/棋子目标分支 | 到达时刻来自实际 Token::Process；额外推进一帧检查不会重复入账 |
| build.sh | 15 个模块通过 macOS ARM64/x86_64 与 iPhone ARM64 编译 | 生成静态库，不能当作 IPA 或真机验收 |
| audit.py | 46 项原字节哈希一致；部分函数片段另验哈希 | 证据审计，不冒充额外 gameplay 测试 |

上述案例相互复用，不可相加成独立测试总量。比较包括资源数值、float32 位模式、随机种子、棋盘标志、有序请求与提前退出。没有证明所有输入等价，也没有进行真实触摸、渲染或完整回合验收。

图形复制适配器只提供此阶段所需的位置和缩放；颜色、UV、尺寸请求的参数/顺序有记录，未实现整个 Quad 渲染器。特殊药水的目标选择仍由同样的显式输入适配器供两侧使用，不声称该选择算法已经恢复。Healing 和 CheckEndGame 回调不执行真实子系统。

## 接入方式与约束

1. SelectionEvent::RuneMatchTile → dr_match_tile。
2. MatchEventKind::Token → dr_enqueue_token。
3. TokenEventKind::Initialise → dr_initialise_token；保存逐槽 TokenMotion。
4. 每帧 dr_process_reward_tokens 推进运动，实际到达后内部调用 dr_add_resource；传入会由 UI/菜单回调更新的三个阻塞标志。
5. 将处理后的 pending 数回写队列；不要用预览总值直接给玩家加钱，也不要再次手动调用入账函数。

示例源码 `recovered/rewards_demo.cpp` 展示上述接法。它不是通用游戏控制器：只使用普通金币，预设输入门槛已满足；特殊模式、真实技能目标选择、完整菜单生命周期和存档仍待实现。索引必须有效，药水标志为布尔值，技能槽数量为 0–4，浮点输入限定正常游戏范围。

## 下一步

先把已有 MatchTiles 路径结算与这套共享棋盘/奖励状态接通，再处理 MoveMatchedTiles、RandomiseTile、SetType/GenerateStats 的下落和生成依赖。随后接敌人阶段、回合收尾和输入门槛，验收能连续玩下一回合。显示层还需要独立的现代 iOS 全屏布局、高清资源映射、Unicode 中文字体、多语言资源和教程入口。

## 复现命令

```sh
sh recovered/build.sh
python3 recovered/verify_match.py
python3 recovered/verify_tokens.py
python3 recovered/verify_resources.py
python3 recovered/verify_motion.py
sh recovered/run_rewards_demo.sh
python3 reverse-engineering/audit.py --reference reference
```

构建需要 Xcode。原版对照依赖检查点中的 ARM64 TCI 工具及原始 Mach-O，它们只用于验证；源码演示不链接模拟器、不读取旧程序。各批边界保留在对应 verification JSON 中，较早报告的“未恢复”描述属于该报告当时的隔离验证范围。
