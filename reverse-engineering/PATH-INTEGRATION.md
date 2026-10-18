# 整条路径与共享棋盘接通

2026-10-17。在本轮消除与奖励恢复的基础上，进一步将已有 MatchTiles、AttackSkull 接入实际 MatchTile、AddToken、Token 初始化/运动、奖励主循环子段和 AddResource。

现在纯源码示例能完成：圈选周边 8 个金币格并围住中间 1 格 → 松手 → 9 格实际消除 → 9 个奖励逐帧移动 → 金币 0 → 18。以每帧 1/60 秒推进，最后一个奖励在第 25 帧到达；额外一帧不重复入账。`rewards-demo.log` 是本轮真实运行输出。

这是无界面的路径结算与奖励演示。它停在需要下落补位的边界，没有敌人行动、完整回合、现代 iOS 界面、全屏、HD 或中文字体。不能据此宣称整个游戏可玩。

## 解决的接入问题

新增 `recovered_path.cpp/.hpp` 是接入适配代码，不冒充多恢复一个原函数。当前共有 16 个 C++ 模块、46 个具名恢复流程，以及 ProcessInput / Game::Process 的部分分支。

早期 Round、Battle 和 Selection 的数据类型存在重复字段。本次为实际接通明确了归属：

| 状态 | 唯一持久来源 |
|---|---|
| 棋子类型、特殊类型、敌人状态、位置、已消除、冻结、火焰标志 | StrokeState 的选择棋盘 |
| 当前攻击和方向加成 | SelectionState.current_damage / weapon_damage；与原 0xbe7c / 0xbdbc 相符 |
| 棋子攻击、防御、生命、毒伤、其余战斗显示标志 | PathState.combat |
| 击杀计数、破甲概率、施毒值、攻击送金币与毒音效状态 | PathState.battle |
| 随机种子、匹配计数、爆炸/巫妖过渡字段、额外奖励概率 | MatchState |
| 预览参数与特殊模式的 0x165d0 值 | ResourcePreviewState |
| 奖励槽和额外奖励总数 | TokenQueue |
| 玩家生命、金币、经验等实际资源 | ResourceState |

较早 Round API 仍保留，便于历史隔离测试。新适配器仅在调用期间构造临时 RoundState，并在每个外部调用前后同步；它不留下第二份持久棋盘。消除回调引发连锁爆炸、类型变化或种族变化后，后续路径判断会看到更新状态。此阶段没有直接重写已经单独验证的 MatchTiles 算法。

另核实：原 +0xbfa4 起真正的消除计数只有前 5 个整型；后续字节中 +0xbfbb 是“攻击送金币”标志。联合测试分别验证计数和该标志，没有把重叠内存误当第六个独立计数。MatchTile 单独验证模块保留的尾部原始槽只用于特殊参数的隔离对照；正常整条路径不将其当独立资源计数。

## 实际验证

`python3 recovered/verify_path.py` 已通过：

- 517 个路径场景：原 MatchTiles、AttackSkull、MatchTile、奖励初始化及真实 RNG 联动执行，与恢复源码比较棋盘、战斗状态、资源计数、全部种子、奖励运动初始状态及有序事件。
- 26 个从真实输入入口开始的手势，其中 20 个金币围合、6 个敌人路径；共 973 个操作/帧步骤，412 个奖励实际到达并入账。
- 敌人路径包含普通敌人、特殊敌人和巫妖命匣转化，核对从选路计算出的攻击值确实进入战斗结算。
- 检查连锁爆炸、守护敌人、破甲、毒伤、冻结，以及明确适配的职业卷轴/种族变化回调对后续路径状态的影响。
- 每个联合序列末尾追加一帧，验证已完成奖励不会再次入账。

旧存储容器、图形/声音和平台运行库通过适配器承接。MoveMatchedTiles、SetSpecialType、Shapeshift、特殊药水目标选择、Healing、CheckEndGame 仍是明确边界；其中类型/种族回调仅用两侧一致的指定状态变化检验接线，未恢复子系统算法。直接路径场景中部分路径为隔离分支而构造，不能当真实手势；26 个联合手势单独统计。

构建通过 macOS ARM64/x86_64 与 iPhone ARM64 静态库。静态库不是安装包，未进行 UIKit、真机或完整回合验收。此次新增模块不应改变既有恢复函数数量；`inventory.json` 将其列在 integration_modules。

## 复现

```sh
sh recovered/build.sh
python3 recovered/verify_path.py
sh recovered/run_rewards_demo.sh
```

源码示例无需原二进制或模拟器；原指令对照需检查点包含的原始 Mach-O、汇编和本机 TCI 工具。

下一项是 MoveMatchedTiles 及其 RandomiseTile、SetType、GenerateStats 依赖：保留原列顺序、棋子身份与数值、随机调用次序。完成补位后，再接敌人阶段与回合收尾，验收能够开始下一回合。全屏、高清、多语言和教程仍是后续必须交付的产品目标。
