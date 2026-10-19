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
