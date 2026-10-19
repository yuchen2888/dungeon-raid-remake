# T030：回合结束 Game::EndOfTurn

开始：2026-10-19（America/Los_Angeles），Claude，起始提交 ad116bd（T020 已完成待复核）。

## T030-A：调用登记（只读）

`scripts/t030_eot_audit.py` 从原 ARMv7 切片和反汇编只读提取，生成 `docs/T030_EOT_CALLS.json`；检查命令：

```sh
cd scripts && python3 t030_eot_audit.py --check --out ../docs/T030_EOT_CALLS.json
```

EndOfTurn 0x13574 共 2292 字节，有 41 个直接调用点、24 个目标。分类依据 46 流程、T010、T020 的已恢复登记，以及表现层命名规则：

| 分类 | 目标 |
| --- | --- |
| 已恢复 | AttackSkull、GetEnemyCount、MatchTile、SetFreezeVisibility、GetPoison（46 流程）；MoveMatchedTiles（T010） |
| 表现边界 | QueueSound、QueueAchievement、AddSimpleLabel、AddParticles、AddFlare、UpdateText、Arrow::SetColour、HelpMenu、Interface::UpdateSkills / UpdateHealthBar / GetPoisonPosition / GetTarget |
| **未恢复的玩法** | CheckEndGame 0x10b18（780 字节，调用点 4 处）、Skill::Deactivate 0x2ab60（8）、Tile::SetFlameVisibility 0x3d89c（152；设置燃烧、累加火焰伤害、解除冰冻，不是纯显示）、ProcessCripples 0xcae0（228）、Tile::ActivateAbility 0x3f09c（452）、SerialiseState 0x91c4（896，存档） |

Tile::ActivateAbility 按敌人能力分派，展开一层后共有 21 个未恢复的能力函数（按大小）：MimicDefence 72、Resurrect 116、RunAwayEnemy 164、ExplodeEnemy 192、TeleportEnemy 240、LowerSkulls 256、FleeUp 272、IgniteTiles 292、DestroyUpgrade 308、StabAttack 332、MakeAcidPotion 340、ConvertSwordToSkull 356、ConvertRandomTiles 520、BreakRandomShieldSword 524、FreezeTiles 536、ThrowSkull 620、HealOrBless 636、JumpEnemy 684、AttractSkulls 1012、AttractShieldsSwords 1020、StealGold 1204。它还调用已恢复的 GenerateStats / UpdateValues（T010），以及显示用的 UpdateCountdown / UpdateEnemyUV。

静态调用点不是控制流图，也不证明分支会执行；"表现边界"是命名规则，具体到某个函数时仍需核对（例如 SetFlameVisibility 就因为写玩法字段而保留为未恢复）。

## 已读到的开头结构（待逐段核实）

- 0x1357e：回合数 Game+0xc 加 1，调用 CheckEndGame；非 0 跳到 0x13e04 结束。
- 0x1359a 起：遍历技能（数量 Game+0xbfa0，指针表 Game+0xbf90）。条件允许时（依据 GetEnemyCount(15)）把技能冷却 +0x90 加 1，上限 +0x8c，满时音效 10；然后 Skill::Deactivate。随后 Interface::UpdateSkills。
- 0x135fe 起：清一组本回合标志字节（含 Game+0xbe78..0xbe7b 的移位、Game+0xbfba 反击标志、0xbfbc），清 matched_counts（0xbfa4..）、计时器 Game+0xbd90=0、+0xbd94=1.0，然后进入逐格循环（0x13716 起，处理冰冻 Tile+0x255 等）。

## 建议顺序

1. 小而独立的整函数：Skill::Deactivate、MimicDefence、Resurrect、ProcessCripples、SetFlameVisibility。
2. CheckEndGame：游戏结束判断与计分；需区分玩法结果和计分界面。
3. EndOfTurn 主体按段恢复（技能冷却、标志重置、逐格冰冻/毒/燃烧、能力触发、补位、存档边界），沿用 T020 的段差分方法和全链测试类。
4. ActivateAbility 与各能力函数，可每次恢复一组。
5. 最后与 T020 一样做整函数逐回合差分。

## T030-B：MimicDefence、Resurrect、ProcessCripples（Claude，2026-10-19）

起始提交 caed5c5。新增模块 `recovered_turn.cpp/.hpp`（build.sh 增加 turn 模块并加入 iPhone 静态库），恢复三个**完整原函数**：

| 原函数 | 地址 | 原生函数 | 行为 |
| --- | --- | --- | --- |
| Game::MimicDefence | 0xbd20 | dr_mimic_defence | 格子防御 = 玩家当前护甲；UpdateText(0,1,0)、标签 20（颜色 28）、音效 23 |
| Game::Resurrect | 0xaf68 | dr_resurrect | 音效 22、14；黄色光效（RGBA 255,255,0,255，类型 1）；标签 38（颜色 46）；计时器 bd94=1.0、bd90=0。复活本身由调用方（ActivateAbility）完成 |
| Game::ProcessCripples | 0xcae0 | dr_process_cripples | 仅职业种族为 7 时生效：行优先遍历未匹配的普通骷髅（类型 1、敌人 0），生命 < 防御的格子 MatchTile(奖励 5)，标签 36（颜色 44）、成就 53（2.0） |

MatchTile 以同步回调 `match_tile` 接入已恢复的 dr_match_tile。Skill::Deactivate（只把技能 +0x80 清 0）会并入之后的 EndOfTurn 技能段，不单独建函数。

验证 `recovered/verify_turn_small.py`（建立在 T020 的全链测试类上）：三个原函数都从入口完整执行；ProcessCripples 的 MatchTile 及其奖励、代币是原函数，原生侧用同一组 match 钩子调用 dr_match_tile。
- MimicDefence 240 次（护甲 −3/0/7/99）、Resurrect 60 次、ProcessCripples 120 次（10 个种族 × 12 块棋盘），共 420 次比较；种族 7 时有 64 个骷髅被消灭。
- 错误副本：去掉种族判断、`>=` 改 `>`、改为列优先，均 exit 1。

## T030-C：SetFlameVisibility 与冰冻/燃烧结算循环（Claude，2026-10-19）

起始提交 1825640。turn 模块新增两项（build.sh 给 turn 的链接依赖加入 battle、combat，以复用 dr_set_freeze）：

| 原代码 | 原生函数 | 行为 |
| --- | --- | --- |
| Tile::SetFlameVisibility 0x3d89c（整函数，128 字节有效代码） | dr_set_flame_visibility | 开：已在燃烧则伤害 += 原火焰伤害；写自燃标志 +0x257、解冻（+0x255=0）、火焰伤害 +0x258、覆盖层 +0x1b0=1、燃烧 +0x256=1，覆盖层 Quad（UV、尺寸、alpha 200）为表现。关：覆盖层与燃烧清 0，写自燃标志 |
| EndOfTurn [0x13710,0x13910) + 循环头 [0x13d64,0x13d88) | dr_end_turn_burn_freeze | 列优先遍历。冰冻格：静止位置光效（100,230,255,255）、SetFreezeVisibility(false)（复用已恢复的 dr_set_freeze）、本回合首次播音效 22。燃烧格（未冰冻）：静止位置光效（240,150,10,255）；若是敌人，在静止位置显示标签 9（火焰伤害、颜色 18），生命 −= 火焰伤害，>0 则 UpdateText(0,0,1) 和粒子 2，否则生命 0、UpdateText、AttackSkull(0, false)，种族 8 时成就 54（2.0）；最后 SetFlameVisibility(false) 熄火 |

由此可见火焰每回合结算一次后熄灭；冰冻一回合后解除。

验证 `recovered/verify_turn_burn.py`：
- SetFlameVisibility 整函数 240 次直接调用（开/关、伤害含 −5 与 INT_MAX、已燃烧与否、自燃标志）。
- 循环 160 次（随机冰冻/燃烧/两者皆有，种族侧重 8）。其中 SetFreezeVisibility、SetFlameVisibility 与 AttackSkull 全链为原函数；108 个敌人被烧死。
- 共 400 次比较，额外比较每格自燃标志与火焰伤害（这两项原先不在 path 状态里）。
- 错误副本：火焰伤害不累加、解冻音效每格都播、`>0` 改 `>=0`，均 exit 1。
- 测试替身说明：选择层测试钩子会全局拦截 Quad::SetSize，并假定调用者是格子；覆盖层 Quad 位于格子 +0x140，因此来自这两个函数的 Quad 调用在最外层直接放行，以原函数执行。

## T030-D：生命回复与毒伤玩家段（Claude，2026-10-19）

恢复 EndOfTurn `[0x13910,0x13a1c)` 为 `dr_end_turn_regen_poison(ResourceState*, regen, TurnHooks*)`，返回值表示游戏是否已结束（原版跳到 0x13e04）：

| 步骤 | 行为 |
| --- | --- |
| 回复 | 回复量 Game+0xbe70（写入者在 EndOfTurn 之外，由调用者传入）>0，且 上限 = health_max + health_bonus > 当前生命时：音效 4；生命 = min(生命 + 回复, 上限)；UI 生命不同则同步并更新血条；在 Interface::GetTarget(0) 位置显示标签 3（数值为回复量、颜色 13） |
| 毒 | 毒（Game+0x15540）>0 时：音效 29；生命 −= 毒；**小于 0** 时生命归 0 并发成就 36（正好 0 不发）；同步血条；在毒图标位置显示标签 7（颜色 15）；随后调用 CheckEndGame，非 0 即结束 |

TurnHooks 末尾追加 `check_end_game` 回调。**CheckEndGame 尚未恢复**：本单元测试中两侧都记录一个有序的 check_end 事件，并返回用例指定的值；它的恢复是后续单元，届时把回调换成真实实现并重跑。

验证 `recovered/verify_turn_regen.py`：
- 350 组边界（生命 −3..40 × 回复 −1..100 × 毒 −1..45 × CheckEndGame 结果）+ 300 组随机 + 10 局 × 25 回合携带状态。共 900 次比较，其中 122 次在毒伤后结束。
- 错误副本：去掉"未满血才回复"、成就条件 `<0` 改 `<=0`、无毒时也调用 CheckEndGame，均 exit 1。

## 测试稳健性：去掉墙钟超时（2026-10-19）

一次全套验证在系统负载平均值约 74 时失败（主要是 Spotlight 索引进程占满 CPU）。verify_counterattack 与 verify_encounters 中的原版模拟撞上了 `emu_start` 的墙钟超时（5 秒和 1 秒），结果本身并没有不一致；该次运行已终止并作废。我写的测试（verify_attack_*、verify_turn_*）已改为 `timeout=0`，只保留指令数上限来防止死循环，这样结果不再受机器负载影响。继承的测试（verify_refill/path/match/motion 等）仍有墙钟超时；它们在正常负载下一直通过，是否统一修改留给下一位工具决定。
