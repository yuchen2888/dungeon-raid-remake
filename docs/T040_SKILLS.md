# T040-H 技能系统

玩家技能（Skill 对象）是游戏规则：装备的技能在棋盘上起作用或设置本回合标志。RuneState.enabled_16491（符文）只由技能 35 启用，此前已恢复的代码中没有置 1 的路径。

## 调用关系（原版）

- Interface::ProcessInput：点技能按钮 → Skill::CanActivate() → Skill::Activate()（冷却与输入目标在界面输入里，待 H6）。
- FoldoutMenu::Process：菜单里选择 → Game::SetSkill(Skill*)（装备）或 Skill::Activate()。
- FoldoutMenu::Initialise(MenuType)：用 Skill::CanActivate(int) 过滤选项。
- Game::EndOfTurn：Skill::Deactivate()。
- Skill::Activate 内：技能 33 用后 Game::RemoveSkill(this)。

## Skill 对象

+0x7c Game*，+0x80 active 字节，+0x84 类型（0..39），+0x88 等级，+0x8c 冷却上限，+0x90 当前冷却。装备的技能为 Game+0xbf90 起 4 个指针，个数 Game+0xbfa0（ResourceState.skill_count）。原生：每个槽的类型 / 等级 / active 在 SkillSlots，冷却在 ResourceState.skill_max / skill_current；对象在槽之间移动时这些一起移动。

## H1：Skill::Activate / Skill::CanActivate / Game::RemoveSkill（Claude，2026-10-20）

新模块 `recovered_skills`：`dr_skill_activate`、`dr_skill_can_activate`、`dr_remove_skill`，状态 SkillState（SkillSlots、ResourceState、PathState、GenerationState、TurnFlags、TurnFinishFlags、RuneState、AttackAnimation、EndGameState），钩子 SkillHooks（event：音效、成就、Arrow::SetColour、Interface::PositionSkill；action：棋盘技能函数，H2..H5 前为边界）。

Skill::Activate 0x2ad40（tbh 40 项，类型 > 39 无动作）：

| 类型 | 音效 | 动作 |
| --- | --- | --- |
| 0 | 0x13 | 标志：Game+0xbfbb（PathBattle.grant_coin_on_attack）= 1，Game+0xbfbc（TurnFlags.next_coin_bfbc）= Game+0x1554c |
| 1 | 0x14 | FreezeSkulls |
| 2 / 3 / 9 / 12 | 0x13 | GrabTiles(0,0) / (3,3) / (0,1) / (2,2) |
| 4 | 0x13 | Game+0xbfba（反击）= 1，active = 1 |
| 5 | 0x16 | ShatterDefence |
| 6 / 13 / 14 / 15 / 32 | 0x13（32：0xe） | ConvertTiles(4,2) / (4,3) / (1,4) / (2,4) / (2,1) |
| 7 | 0x15 | Teleport |
| 8 | 0x18 | CreateExplosivePotions |
| 10 | 0x13 | Upgrade |
| 11 | 0x19 | CollectRandomRow |
| 16 / 17 / 18 / 19 | 0x17 | 标志：双倍伤害 be74 / 金币 be77 / 回复 be76 / 升级 be75 = 1，下回合 be78 / be7b / be7a / be79 = Game+0x1554c |
| 20 / 21 / 23 | 0x13 / 0x1a / 0xe | DemoteSpecialEnemy / KillSpecialEnemy / PromoteNormalEnemy |
| 22 | 0x1b | 标志：one_health 0x14af5 = 1，next_one_health 0x14af7 = Game+0x1554c |
| 24 | 0x22 | 标志：force_coins 0x14af6 = 1，next_force_coins 0x14af8 = Game+0x1554c |
| 25 / 26 / 27 / 28 / 29 / 30 / 31 | 0x13 / 0x25 / 0x1c / 0x1c / 0x18 / 0x1b / 0x1a | CreateMagicSword / Earthquake / ExplodeArmour / CollectRandomBlock / CreateManaPotions / ConvertColumnToSwords / CreateArrows |
| 33 | 0x13 | 普通骷髅（骷髅 − 特殊敌人）> 19 时成就 64（100.0）；CollectBoard；RemoveSkill(this) |
| 34 | 0xe | 标志：0x164a7 = 1，0x164a8 = Game+0x1554c |
| 35 | 0x13 | 符文：0x16491 = 1，Arrow::SetColour(0x50,0x82,0xff)，0x16492 = Game+0x1554c，active = 1 |
| 36 | 2（三次） | KillSkullsNextToCoins |
| 37 | 0x13 | 标志：0x164a4（guard）= 1，0x164a5（revive_second）= Game+0x1554c |
| 38 / 39 | 0x1b / 0x17 | CollectEdgeTiles / CreateChain |

标志类技能都把 active 置 1；"下回合"标志取自 Game+0x1554c（TurnFinishFlags.flag_1554c）。

Skill::CanActivate(int) 0x2ac74（tbb 37 项，类型 > 36 为 true）：3 → 盾牌（类型 3）> 0；6、13 → 剑 > 0；20、21 → 特殊敌人 > 0；5、14、23 → 普通骷髅 > 0；27 → 有骷髅且护甲 > 0；2、8、9、29 → 普通药水 > 0（Tile::IsNormalPotion：三个药水标志都为 0）；25、31 → 普通剑（非魔剑、flag_231 为 0）> 0；0、1、4、34 → 骷髅 > 0；36 → 普通骷髅 > 0 且金币 > 0；12、15、32 → 金币 > 0；其余 true。

Game::RemoveSkill 0x9114：找到该技能的槽，其后的技能依次前移（每次 Interface::PositionSkill(槽)），被移除的放到最后一槽，skill_count − 1；不在列表中则不变。

验证 `recovered/verify_skills.py`：原函数从入口执行（GetTileCount、GetSpecialEnemyCount、GetNormalPotionCount + IsNormalPotion、GetNormalSwordCount、RemoveSkill 为原代码；音效、成就、箭头颜色、PositionSkill 与棋盘技能函数记录并跳过），1200 组随机棋盘（缺少某些格子类型的棋盘、19 / 20 个普通骷髅的棋盘）：每组 41 个类型的 CanActivate（49200 次）、900 次 Activate（含未装备技能、一次性技能 33）、300 次 RemoveSkill，事件、动作、全部标志、装备槽与 skill_count 一致。错误副本 21 个全部 exit 1。

## H2 第一批：Upgrade、FreezeSkulls、ConvertTiles、CreateManaPotions、CreateExplosivePotions、CreateArrows、CreateMagicSword（Claude，2026-10-20）

recovered_skills 新增（结束时都把闪光计时 MatchState shake_progress_bd90 = 0、shake_scale_bd94 = 1.0）：

| 原版 | 原生 | 行为 |
| --- | --- | --- |
| Game::Upgrade 0x9694 | dr_skill_upgrade | 只有 Interface::ShowMenu(2)（升级菜单，FoldoutMenu） |
| Game::FreezeSkulls 0xa470 | dr_freeze_skulls | 按列遍历，每个骷髅（类型 1，含特殊敌人）：闪光（类型 1，颜色 100,230,255,255），Tile::SetFreezeVisibility(true)（冻结、冻结遮罩显示、燃烧清除） |
| Game::ConvertTiles 0xa7f4 | dr_convert_tiles | **按行**遍历，类型 from 的格子（from 为 1 时跳过特殊敌人，from 为 4 时跳过箭）Tile::SetType(to, 回合, 难度) 后白色闪光；金币变骷髅（2→1）还置 Game+0x165b8（TurnFlags.b165b8[0]） |
| Game::CreateManaPotions 0xa548 | dr_create_mana_potions | 按列，每个普通药水：闪光（100,100,255,255），Tile::MakeManaPotion |
| Game::CreateExplosivePotions 0xa380 | dr_create_explosive_potions | 按列，每个普通药水：闪光（255,150,0,255），Tile::MakeExplosivePotion（flag_234，UV (variant×0.0517578125, 类型×0.0517578125+0.6044921875)） |
| Game::CreateArrows 0xcdac | dr_create_arrows | 按列，每把普通剑：Tile::MakeArrow，白色闪光 |
| Game::CreateMagicSword 0xccc0 | dr_create_magic_sword | RandI(0, 普通剑数−1, 流 5) 选一把，Tile::MakeMagicSword（magic_sword，颜色 150,150,255,255），闪光（100,100,255,255） |

闪光以 SkillEventKind::Flare 交出（会话接 dr_add_flare），格子外观（UV / 颜色）与随机数按生成单元的事件格式交出。验证 `recovered/verify_skill_board.py`：原函数从入口执行，生成宿主打开（SetType、RandI、IsNormalPotion、GetNormalSwordCount、Tile::Make*、SetFreezeVisibility 为原代码），AddFlare 与 ShowMenu 记录并跳过；700 组（每个函数 100 组）、2561 个闪光，事件、棋盘、战斗格、药水、生成附加数据与事件、随机种子、闪光计时、Game+0x165b8 一致。错误副本 16 个全部 exit 1（其中一个发现：ConvertTiles 是按行遍历，初稿按列被测试拒绝后改正）。

## 后续

- H3..H5：其余 14 个棋盘技能函数（GrabTiles、ShatterDefence、Teleport、CollectRandomRow、DemoteSpecialEnemy、KillSpecialEnemy、PromoteNormalEnemy、Earthquake、ExplodeArmour、CollectRandomBlock、ConvertColumnToSwords、KillSkullsNextToCoins、CollectEdgeTiles、CreateChain、CollectBoard），每个 200～450 字节。
- H6：Interface::ProcessInput 的技能按钮（CanActivate、冷却、输入目标 Game+0x58ac）、Skill::Deactivate、Game::SetSkill，以及会话接线。
