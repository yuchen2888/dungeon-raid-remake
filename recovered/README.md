# Dungeon Raid 逆向恢复：规则、连线、攻击与职业进度

## 当前进度（2026-10-17 更新）

当前共 16 个 C++ 模块、46 个具名恢复流程，另有 ProcessInput 和 Game::Process 的部分分支。新 path 模块是接入适配器，不额外计作原版函数；数量不是完整游戏的完成比例。

已将整条路径的攻击、消除、奖励生成、移动与入账接通，并统一持久棋盘字段的归属。新增联合验证通过 517 个路径场景，以及 26 个从真实输入开始的手势（含 6 个敌人路径）、973 个操作/帧步骤、412 个实际完成的奖励。完整缺口和边界见 `../reverse-engineering/PATH-INTEGRATION.md`。

`sh run_rewards_demo.sh` 是完全由恢复源码编译的无界面示例，无需原游戏二进制或模拟器：周边八格加圈内一格全部消除，9 个奖励在 25 帧内到达，金币 0 → 18；再推进一帧不重复入账。

下落补位、生成、敌人阶段、回合收尾与完整主循环仍未接通；真实全屏、HD、中文、多语言、教程和新的可玩 iOS App 均未完成。消除与奖励各模块的隔离证据见 `MATCH-REWARDS-RECOVERY.md`，较早 stroke_demo 及以下报告保留其历史范围。

## 早期阶段记录

这是一份部分逆向成果，不是完整游戏或可安装 IPA。目标是恢复原程序行为，不改画面与规则。

当前包含 33 个原版算法、状态与编解码流程。前 15 个完成直接指令对照；攻击、连线结算、职业进度与路径选择分别标明外部接口。接口尚未实现的部分不计为已经恢复的游戏功能。

## 已恢复并验证的函数

- Tile::GetAttack：实际攻击值，在特定种族条件和中毒状态下减半；整数向下取整，例如 11 → 5。
- Tile::AddPoison：毒伤向三个回合槽叠加，并保留图形状态标志的变化。
- Tile::GetPoison：返回本回合毒伤、推进剩余回合，并更新毒伤消退标志。
- Tile::CanMatchType：连线类型判断，包含特殊剑块和巫妖命匣例外；不包含相邻性、回退和最短路径处理。
- Tile::GetDamageType：根据路径方向、种族、缺陷和敌人组合返回原伤害分类值；不是完整伤害结算。
- Game::GetNearestUnmatchedTile：在指定列向上查找未匹配方块。
- Game::GetEnemyCount：统计棋盘上指定类型敌人的数量。
- CharacterClass::HaveFlaw / GetMortalEnemyType：缺陷判断与种族对应敌人表。
- Game::TouchStart / TouchDrag / TouchEnd / TouchInterrupted：触摸状态与原坐标换算。
- Game::GetTileAtPosition：将归一化触摸坐标映射为棋盘方块，保留原截断和边界行为。
- Tile::IsBeingSelected：使用原 f32 运算顺序计算选中范围，保留原 0.8 倍半径。
- Game::AttackSkull：完整单体攻击分支，连接护甲挡伤、逐点破甲、毒伤、冻结、击杀统计及巫妖转化。
- Tile::MakePhylactery：恢复巫妖转化后的攻击、防御、生命、毒伤槽及状态位。
- Tile::SetFreezeVisibility：恢复冻结状态位；具体贴图 UV、尺寸和透明度由渲染接口承接，未在此批次恢复。
- Tile::GetRewards：恢复敌人对应的掉落种类、数量分配及随机调用顺序；奖励入账尚未实现。
- Game::MatchTiles：恢复按路径依次调用伤害和攻击结算、特殊剑块、守护敌人、交叉评分、边缘/全金币判定及清理标志；`MatchTile` 和 `MoveMatchedTiles` 仍是待恢复的接口。

- 职业进度新增 11 个流程：替换技能计数、职业校验、单局与完整职业档案编解码、十职业档案编解码、升级、职业成就判定与全职业满级判定。
- `Game::ProcessTileSelection` / `Tile::Select`：恢复已有划线的连续延伸、回退清理、类型判断、冻结限制、特殊剑块桥接、移出范围取消，以及伤害、火焰、反伤、吸血预览重算。起始选中与松手后的回合调度仍待接入。

依据来自旧 IPA 内的真实 ARMv7 指令。C++ 是依据汇编恢复出来的新源码，不是找到了作者原始工程。种族枚举的具体名字和图形字段的具体名字尚未完整还原，使用的判断值和状态字节已经对照。

## 验证方式与结果

1. 从旧程序提取原始机器指令及常量，不重新汇编，不替换原始算法。
2. 使用 Unicorn 执行原始 ARMv7 指令，覆盖边界值、随机输入、不同职业索引、毒伤叠加及连续回合变化。
3. 先与 x86_64 编译版本对照，并导出原始指令的返回值和状态变化。
4. 在 Apple silicon 上原生运行 ARM64 编译版本，重放 57,055 项函数级输入和 497 个路径场景的原版结果，对照通过。
5. 使用 iPhone SDK 编译全部恢复代码，生成 ARM64 静态库 `libDungeonRaidRecovered-ios-arm64.a`。静态库不能直接安装到手机。

原生 ARM 版本的 Unicorn 依赖在当前环境的初始化阶段退出。因此原始指令执行器使用已安装的 Rosetta 和系统 x86_64 Python；恢复代码的 ARM64 验证使用原生 Python 与 ARM64 动态库。这个调整没有修改系统安全设置。

测试覆盖：攻击值计算 5,160 组；毒伤叠加 10,296 组；毒伤推进 1,716 组；连续回合序列 4,500 步。测试通过说明这些函数在测试输入下行为一致，不构成整个游戏或所有输入的形式化等价证明。

第二批共 14,595 项：种族对应表 16，缺陷判断 405，掉落查找 2,688，敌人计数 250，连线类型 5,916，伤害分类 5,320。原始程序的 std::list 遍历和相关辅助函数均执行真实指令，没有以自编算法替换。

第三批共 13,628 项：触摸开始、移动、结束、中断各 256；棋盘坐标换算 9,468；选中范围 3,136。覆盖格子边界及相邻浮点值、选中半径内外、不同偏移和间距。范围限定为正常有限浮点坐标；不宣称所有 NaN、无穷大或非正常参数的等价性。

第四批共 7,160 项：攻击 5,812，冻结状态 8，命匣转化 60，掉落分配 1,280。攻击项中包括 1,200 步连续攻击，持续携带护甲、毒伤、冻结、音效标志和计数。随机数由同一输入序列提供，**未验证原随机数发生器**。音效、渲染、`MatchTile` 和奖励输出存储使用接口适配，验证返回值、核心状态和有序调用事件。

第五批为 497 个棋盘/路径场景：原始 `MatchTiles` 实际调用原始 `GetDamageType`、`AttackSkull`、`AddPoison` 等代码，与 64 位实现的联动结果一致。覆盖普通多敌人、方向加成、守护敌人的列优先顺序、特殊剑块远程击杀、满盘金币、棋盘边缘，以及交叉评分 5/6、9/10、14/15 的阈值。部分路径为隔离分支而构造，仅保证索引有效；相邻性和回退属于尚待恢复的 `ProcessTileSelection`，不能据此宣称真实划线操作已经验证。

第五批中的 `MatchTile`、`MoveMatchedTiles`、随机、渲染/音频、标准集合存储和异常登记是明确接口。测试不包含奖励实际入账、掉落动画、补位或完整可玩回合。标准集合接口用于适配旧 C++ 库的存储，不替换游戏分支算法。

一个已与原指令对照的例子：攻击 5、防御 2、生命 20，应用毒伤 3，给定本次随机输入，结果为生命 17、防御 1、三个毒伤槽各 3、冻结标志为 1。该结果包含一次破甲和一次冻结触发，并不表示它们每次必定发生。

## 新增职业进度与路径验证

职业进度先执行原始十职业初始化与所有相关原指令，生成 800 份档案往返结果。原生 64 位实现各在 ARM64 与 x86_64 上通过 4,000 项对照、524 个无效/截断输入防护检查，以及 210 个升级/成就事件场景。真实的旧存档格式保持为 26 字节单局职业、47 字节完整职业和 472 字节十职业档案；C++ 内部使用 8 字节指针和新的类型布局。职业校验对重复天赋/缺陷的清理顺序、基础职业固定等级、技能槽位以及容易难度的成就门槛均保留原行为。Game 存档脏标记、缓冲区所有权与成就队列时序是明确接口，尚未集成完整存档系统。

路径选择对照 2,485 个场景，实际运行原 `GetTileAtPosition`、`IsBeingSelected`、`CanMatchType`、种族对应、敌人数、向量归一化及 `Tile::Select`。验证包含 1,365 次路径改变，并对照有序视觉/音频事件及中间箭头路径数据。全套结果已在原生 ARM64 重放。旧 list/set 的分配存储以及视觉、提示框、箭头、音频是接口；这些接口不替换选路分支。结果不证明 UIKit 触控或视觉效果已经正常。原函数的递归延伸改为保持事件顺序的循环；输入限定为有限坐标、正常棋盘几何和有效路径。

新增文件是 `recovered_progression.cpp`、`verify_progression.py`、`progression_*`、`recovered_selection.cpp/.hpp`、`verify_selection.py`、`selection_*` 与 `original_selection.bin`。

```sh
sh build.sh
/usr/bin/arch -x86_64 /usr/bin/python3 ../runtime/liveexec32/verify-original-progression.py
python3 verify_progression.py
/usr/bin/arch -x86_64 /usr/bin/python3 verify_progression.py
/usr/bin/arch -x86_64 /usr/bin/python3 verify_selection.py
python3 verify_selection.py --replay
```

这两份原生模块尚未接入兼容 IPA。当前安装包采用的仍是原 ARM32 程序加现代 ARM64 宿主及 LiveExec32 运行库，不是用这 33 个流程拼成完整游戏。

## 文件

- recovered_combat.cpp：恢复的 C++ 代码，采用原生 64 位指针及新数据布局。
- original_functions.bin / .asm：原始 168 字节指令与汇编证据。
- provenance.json：来源和哈希。
- verification.json：原始指令对照结果。
- original_results.json：从原始指令捕获的输入、输出和状态。
- verification_arm64.json：原生 ARM64 的重放结果。
- recovered_combat_native.dylib：包含 ARM64 与 x86_64 两个切片的 macOS 编译产物。
- recovered_combat_ios_arm64.o：面向 iPhone 的 ARM64 目标文件。
- verify_original.py：原始指令对照验证。依赖 Unicorn 2.1.4。
- replay_arm64.py：原生 ARM64 重放验证。
- recovered_core.hpp：供后续 iOS 工程接入的统一类型与函数声明。
- recovered_rules.cpp / recovered_input.cpp：新增连线、伤害分类及触摸规则。
- rules_* / input_*：对应的原始结果、证据、对照报告和 ARM64 复验报告。
- verify_rules.py / verify_input.py：新增批次的对照执行器；加 `--replay` 可在 ARM64 上复验。
- build.sh：统一构建 macOS 双架构验证库与 iPhone ARM64 静态库。
- recovered_battle.cpp / recovered_round.cpp：新增单体攻击与多目标路径调度。
- verify_battle.py / verify_round.py：新增对照执行器；加 `--replay` 可在 ARM64 上复验。
- battle_* / round_*：对应原始结果、哈希证据及两种架构验证报告。
- crossing_boundary_paths.json：交叉评分阈值用的固定测试路径。

## 构建与复现

在本次工作环境中，依赖安装在项目的 tools（ARM64）和 tools-x86（x86_64）目录。独立使用时可在对应 Python 环境安装 Unicorn 2.1.4。

```sh
xcrun --sdk macosx clang++ -std=c++17 -Wall -Wextra -Werror -O2 -arch arm64 -arch x86_64 -dynamiclib recovered_combat.cpp -o recovered_combat_native.dylib
xcrun --sdk iphoneos clang++ -std=c++17 -Wall -Wextra -Werror -O2 -arch arm64 -miphoneos-version-min=18.0 -c recovered_combat.cpp -o recovered_combat_ios_arm64.o
/usr/bin/arch -x86_64 /usr/bin/python3 verify_original.py
python3 replay_arm64.py
```

新增批次按以下步骤构建、验证：

```sh
sh build.sh
/usr/bin/arch -x86_64 /usr/bin/python3 verify_rules.py
/usr/bin/arch -x86_64 /usr/bin/python3 verify_input.py
/usr/bin/arch -x86_64 /usr/bin/python3 verify_battle.py
/usr/bin/arch -x86_64 /usr/bin/python3 verify_round.py
python3 verify_rules.py --replay
python3 verify_input.py --replay
python3 verify_battle.py --replay
python3 verify_round.py --replay
```

完整原始指令验证需要上一级的 `DungeonRaid-original` Mach-O 和 `armv7-disassembly.txt`，检查点均已包含。当前重放脚本共用原始执行器的数据类型定义，因此仍需要 Unicorn 包可以导入，但重放不会启动它的模拟执行引擎。

## 原游戏运行尝试

已取得官方 touchHLE 0.3.0，验证发行包哈希并解包。运行器确实能识别 Dungeon Raid 1.3.4、载入其 ARMv7 主程序及 C++ 等依赖，并开始执行 CPU 指令。

- 图形模式：当前执行环境无法取得显示器，报 `The video driver did not add any displays`；没有显示出游戏画面。
- 无画面模式：原程序在旧广告组件 `+[PHWebView load]` 内调用运行器尚未实现的 `_class_getInstanceMethod` 后停止。
- 独立研究副本：将该广告初始化入口改为立即返回，之后执行推进到了主 NIB/UI 初始化。无画面模式在访问图形环境时停止；不能据此判断有画面模式已经可玩。

`../runtime/prepare_research_copy.py` 可重现这一处补丁，`research-patches.json` 记录准确地址、字节和前后哈希。原 IPA 和用于规则对照的原始 Mach-O 均未修改。研究补丁仅用于兼容性定位，不能代替真正的 64 位原生移植。

当前兼容运行工程见 `../runtime/liveexec32/README.md`，已编译 iOS/Catalyst ARM64 宿主并保留全部原资源，尚未完成手机签名、JIT 与实际游玩验证。

原生恢复下一步是将已有路径结算接入当前共享状态与奖励流程，恢复 `MoveMatchedTiles` 及生成依赖，再将敌人阶段、回合收尾、渲染、音频和完整存档接成完整循环。当前结果不能用于推算完整移植总工时，也不是可安装/可玩的游戏。
