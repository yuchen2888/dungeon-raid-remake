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

## T030-E：CheckEndGame 判断与免死段（Claude，2026-10-19）

起始提交 f576964。恢复 Game::CheckEndGame 0x10b18 的判断部分 `[0x10b18,0x10c04)` 为 `dr_check_end_game(ResourceState*, EndGameState*, EndGameHooks*)`（turn 模块，链接依赖加入 rules 以复用 dr_mortal_enemy / dr_enemy_count）。

| 顺序 | 条件 | 行为 |
| --- | --- | --- |
| 1 | Game+0xcac4 非 0（游戏结束界面 GameOverScreen 位于 +0xcac0，这是它的显示中标志） | 返回 1 |
| 2 | Game+0x16611 胜利标志 且 record 模式 且 mode_14ae8==0 | 成就 76（100），进入结束结算（胜） |
| 3 | 生命 > 0 | 返回 0 |
| 4 | 种族≠0 且棋盘上有该职业的宿敌 | 成就 40 |
| 5 | 免死标志 guard_164a4（ResourceState 已有，Game+0x164a4） | 清它与 Game+0x164a5；生命 = 上限 + 加成；同步血条；音效 19；毒图标位置标签 28（颜色 36）；成就 61；返回 0 |
| 6 | 否则 | 进入结束结算（负） |

结束结算 `[0x10c04, 返回)` 暂由 `game_over(win)` 回调承接，是下一单元。已读到的内容：职业档案 games_played += 1、enemies_killed += 本局击杀 Game+0x165b4；非 record 模式按难度（Game+0x14ae0，即 MatchState 中旧名 spawn_enabled_14ae0 的字段，实为难度）更新 normal/hard/harder 最高分（无符号比较）；ScoreScreen::AddScore（计分表）；SetSkills；SerialiseClasses；GameOverScreen::Initialise(win)；然后写 Game+0x146d0=0、+0x146d4=1、+0x15546=1，成就 67，返回 1。需要先恢复 GetScore、GetTotalGold、GetTotalUP（小函数）。

验证 `recovered/verify_check_end_game.py`：原版从入口执行到返回或到达 0x10c04；后一种情况读出栈上 [sp,#0x14] 作为胜负标志，与原生 game_over 回调比较。
- 288 组边界（界面标志 × 胜利标志 × record × mode × 生命 −5/0/1 × 免死 × 种族 0/3/7 × 宿敌有无）+ 300 组随机，共 588 次比较。
- 结果分布：继续 266、已结束 175、负 111、胜 36；免死路径已覆盖。
- 错误副本：胜利条件改 mode==1、`>0` 改 `>=0`、免死不清 0x164a5，均 exit 1。

## T030-F：CheckEndGame 结束结算与计分函数（Claude，2026-10-19）

起始提交 7b9c85a。turn 模块新增：

| 原函数 / 段 | 原生函数 | 行为 |
| --- | --- | --- |
| Game::GetTotalGold 0x18a2c、GetTotalUP 0x18a5c（整函数） | dr_total_gold / dr_total_up | 当前值 + 累计值；record 模式且 mode 0 时除以 4（向零截断） |
| Game::GetTotalXP 0x189fc | dr_total_xp | 与 T010 的 dr_generation_total_xp 是同一原函数，这里提供 ResourceState 形式（同一公式，两处实现） |
| Game::GetScore 0x8c18（整函数） | dr_get_score | record mode 1：PathState.total；record mode 0：金币+XP+UP，胜利（Game+0x16611）时翻倍；其他：金币+XP+UP+回合数+Σ 技能等级（技能对象 +0x88）×100 |
| CheckEndGame 结算段 [0x10c04,0x10dd6) | dr_game_over | 职业档案 games_played+1、enemies_killed += 本局击杀；非 record：计分表条目（回合、XP、金币、UP、分数、难度），难度 1/2/3 时以无符号比较更新 normal/hard/harder 最高分；record mode 1：计分表条目用 crossing 平均/最佳/样本数；record mode 0：用 XP/金币/UP；其他 mode 不记；SetSkills（技能对象 +0x84，不足 4 个补 −1）；SerialiseClasses；GameOverScreen(win)；Game+0x146d0=0、+0x146d4=1、+0x15546=1；成就 67 |

**CheckEndGame 至此作为完整函数恢复**：`dr_check_end_game` 的 game_over 回调接 `dr_game_over`。EndGameState 末尾追加三个结束标志，新增 SkillSlots（技能对象 +0x84 编号、+0x88 等级）和 ScoreEntry。计分表（ScoreScreen::AddScore）、SetSkills、职业档案序列化（SerialiseClasses，存档边界）与结束界面以事件输出。

验证 `recovered/verify_game_over.py`：原版 CheckEndGame 从入口完整执行到返回，其中 GetTotalXP/Gold/UP、GetScore、GetMortalEnemyType、GetEnemyCount 为原函数；原生侧 dr_check_end_game → dr_game_over。
- 300 组边界（record × mode 0/1/2 × 胜利 × 难度 0..4 × 技能数 0..4）+ 300 组随机，共 600 次比较。路径：按难度记分 260、按模式记分 186、record mode 2 不记分 86、未结束 68。
- 测试域说明：技能数只取 0..4。原版只有 4 个技能槽，技能数为 5 会读到越界的野指针，测试第一次就因此报出未映射内存读取。
- 错误副本：最高分改有符号比较、胜利不翻倍、技能等级系数改 10，均 exit 1。

## T030-G：EndOfTurn 开头段（Claude，2026-10-19）

起始提交 178a77e。恢复 `[0x13574,0x13710)` 为 `dr_end_turn_begin(ResourceState*, PathState*, SkillSlots*, TurnFlags*, counterattack*, TurnHooks*)`，返回 true 表示 CheckEndGame 已结束游戏（原版直接返回）。

| 步骤 | 行为 |
| --- | --- |
| 回合 | PathState.turn（Game+0xc）+1 |
| 结束判断 | CheckEndGame；真则返回（check_end_game 回调接已完整恢复的 dr_check_end_game） |
| 技能 | 对每个技能（数量 Game+0xbfa0）：棋盘上没有 15 号敌人时，若当前值（+0x90）== 上限（+0x8c）−1 则音效 10，当前值 = min(当前+1, 上限)；无论如何 Skill::Deactivate（+0x80 清 0，原生为 SkillSlots.active）。随后 Interface::UpdateSkills |
| 清零 | Game+0x15561/2、Game+0x165b8..0x165bc |
| 箭头 | Game+0x16491 非 0 且 Game+0x16492 为 0 时 Arrow::SetColour(50,255,50) 并清 0x16491；之后清 0x16492 |
| 轮换 | 0x164a8 → 0x164a7；Game+0xbe78..7b → 0xbe74..77；0xbfbc → 0xbfbb（PathBattle.grant_coin_on_attack）；"下一回合"位均清 0 |
| 其他 | 反击标志 Game+0xbfba 清 0；matched_counts[0..4] 清 0；攻击计时器 bd90=0、bd94=1.0 |

新增 `TurnFlags` 保存这些按偏移命名的回合标志（含义待确认）；SkillSlots 末尾追加 active[4]。

验证 `recovered/verify_turn_begin.py`（建立在 CheckEndGame 全链测试类上）：原版从 EndOfTurn 入口执行到 0x13710，或因结束而提前返回；其中的 CheckEndGame 是完整原函数（含 GetScore 与结束结算），原生侧调用 dr_check_end_game → dr_game_over。
- 120 组边界（生命 5/0 × 15 号敌人有无 × 技能数 0..4 × 6）+ 200 组随机 + 8 局 × 10 回合携带状态。共 400 次比较；160 次由 CheckEndGame 结束，39 次技能就绪音效。
- 错误副本：冷却忽略 15 号敌人、不轮换金币标志、箭头条件忽略 0x16492，均 exit 1。

## T030-H：EndOfTurn 循环 B——中毒敌人（Claude，2026-10-19）

起始提交 a4371b9。恢复 `[0x13a1c,0x13af2)` + 循环头 `[0x13d88,0x13daa)` 为 `dr_end_turn_poison_enemies(PathState*, TurnHooks*)`。

- 列优先遍历（外层 x=[sp,#0x24]，内层 y；格子 = y*6+x）。只处理 type==1（敌人）。
- Tile::GetPoison 推进毒队列（current←next←following←0，归零时清效果），返回值为本回合毒伤；0 则跳过。
- 毒伤 >0：在静止位置（Game+0xb400）加标签 7（数值=毒伤，颜色 15，缩放 1.0）。剩余生命 = 生命−毒伤（32 位回绕）：>0 时写回生命、UpdateText(0,0,type)、粒子 2；否则 MatchTile(奖励 5)，种族（Game+0x1556C）为 1 时成就 47（2.0）。死亡分支不写回生命（MatchTile 自行处理）。
- 原版结束后跳 0x13cda（清 Tile+0x254，属下一单元）。

验证 `recovered/verify_turn_poison.py`：原版从 0x13a1c 执行到 0x13cda（循环自己清列计数器），GetPoison 与 MatchTile（含令牌/奖励）为原代码。240 组随机局面（60% 格子带随机毒队列与生命，含负毒、2^31−1 生命）：存活粒子 1337 次，种族 1 成就 449 次。
错误副本：行优先遍历、不写回毒队列、`>=0` 判存活，均 exit 1。

## T030-I：EndOfTurn 尾段（Claude，2026-10-19）

恢复 `[0x13b3c,0x13cda)` + `[0x13d12,0x13d64)` + `[0x13dc8,0x13e04)` 为 `dr_end_turn_finish(ResourceState*, PathState*, GenerationState*, EndGameState*, TurnFinishFlags*, TurnHooks*)`，返回 true 表示某次 CheckEndGame 结束了游戏（未到 SerialiseState）。TurnHooks 末尾追加 `move_matched_tiles`。

| 步骤 | 行为 |
| --- | --- |
| 免死轮换 | Game+0x164a6 ← 0x164a4 ← 0x164a5（revive_second）← 0 |
| 结束判断 | CheckEndGame；真则返回 |
| 补位 | MoveMatchedTiles（原生 dr_move_matched_tiles） |
| 清零 | 每格 Tile+0x86（attack_flag） |
| 生成标志 | 0x14af7 → one_health(0x14af5)、0x14af8 → force_coins(0x14af6)，来源清 0；filter_enabled/filter_swords（0xbfb8/9）清 0；time_to_promotion(0x14af0) −1，结果为负时取 0（INT_MIN−1 回绕为 INT_MAX，保留） |
| 帮助 | Game+0x102d0 的 0x8000 位：每列第一个敌人（自上而下）调用 HelpMenu::Initialise(格子中心, 0x3da9999a, 0x3da9999a, 15)；0x200000 位：每列第一个 enemy_type≠0 的敌人，类型 21。注意是每列一次，不是全盘一次（编译后的 break 只跳出内层循环） |
| 胜利 | Game+0x1554c 清 0；victory(0x16611) = record(0x14aed) && mode(0x14ae8)==0 && turn==100 |
| 收尾 | CheckEndGame；为假则 Game::SerialiseState（存档，边界事件） |

新增 `TurnFinishFlags`（按偏移命名，含义待确认）；TurnEventKind 追加 Help、SerialiseState。

验证 `recovered/verify_turn_finish.py`（建立在 CheckEndGame 全链测试类上）：原版从 0x13b3c 执行到尾声 0x13e04，两次 CheckEndGame 都是完整原函数，MoveMatchedTiles 为原函数（RandomiseTile/生成/遭遇）。64 组边界（帮助位 × record × mode × 回合 99/100 × 生命）+ 150 组随机 + 6 局 × 8 回合，共 262 次比较；164 次有生成事件；结局：保存 / 第一次结束 / 第二次结束（补位中遭遇扣血）/ 第 100 回合胜利均出现。
错误副本：帮助循环不 break、计时器按旧值判断下限、胜利条件漏 mode，均 exit 1。

剩余：0x13cda 清 Tile+0x254 与 ProcessCripples 之后的能力循环（Tile::ActivateAbility 及 21 个能力函数），然后 EndOfTurn 整函数差分。SerialiseState（存档格式）仍为边界。

## T030-G 修正：开头段标志归属（Claude，2026-10-19）

EndOfTurn 整函数差分（开发中）在代币累计（Game+0x165d0）上发现差异，追查到 AddToken 读取 Game+0xbe75..0xbe77。这三个字节以及 0xbe74、0x16491 早已属于其他已恢复状态，T030-G 却在 TurnFlags 中复制了一份：

| 偏移 | 所属原生字段 |
| --- | --- |
| Game+0xbe74 | SelectionState.double_damage（verify_selection） |
| Game+0xbe75..0xbe77 | ResourcePreviewState.double_upgrade / double_healing / double_gold（verify_preview） |
| Game+0x16491 | RuneState.enabled_16491（verify_rune） |

修正：TurnFlags 去掉 prev_be74[4] 与 arrow_pending_16491；dr_end_turn_begin 增加 RuneState* 参数，把 next_be78[0..3] 写入 SelectionState / 预览状态，箭头判断读写 RuneState。verify_turn_begin 改为从这些所属状态读回比较（原版侧仍读同一内存），400 次比较通过；错误副本"不写预览 double_*"exit 1。
教训：按偏移新建字段前，先在 verify_*.py 中搜索该偏移是否已有所属状态。
