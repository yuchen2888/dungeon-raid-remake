# T040 回合调度：Game::Process / ProcessInput / InitNewGame

## 调度结构（已核实，静态 + 差分）

- `main` 每帧调用 `Game::Process`（0x1717c，3168 字节）。它依次处理时间/FPS、各界面（GameOverScreen、ScoreScreen、HelpMenu、UnlockMenu、MainMenu、NameScreen、IntroScreen，属表现层）、ShieldShatter、Tile::ProcessEffects、下落列表（0x173c8..0x173ff，已恢复于 refill）、代币（0x1744c..0x174da 与 0x17d56..62，已恢复于 motion）、粒子与标签动画、两处 `ProcessInput` 调用（0x176f8、0x17d10），并在 0x17cdc 调用 `ProcessAttack`（T020 已恢复）。
- **Game::Process 不直接调用 EndOfTurn**：EndOfTurn 唯一调用点在 `ProcessInput` 0x1671e。MatchTiles 在 ProcessInput 0x1692a（松手），MoveMatchedTiles 在 0x16d6c。
- `InitNewGame`（0x15c50，2160 字节）由 StartTutorial / StartChallenge / NewGame / ContinueGame / NameScreen::ProcessInput 调用。

调用登记：`scripts/t040_process_audit.py` → `docs/T040_PROCESS_CALLS.json`（三个函数的全部直接调用点、类别、未恢复目标按大小排序、已恢复段落及字节哈希）。

## T040-B：ProcessInput 门槛 [0x16638,0x16748) 与 CountAttackers（Claude，2026-10-19）

新模块 `recovered_schedule`：

| 原版 | 原生 | 行为 |
| --- | --- | --- |
| Game::CountAttackers 0x8fb0 | dr_count_attackers | 行优先统计 type==1、无 attack_flag、未冰冻且 Tile::GetAttack>0 的格子 |
| ProcessInput 门槛 | dr_input_gate | 见下 |

门槛顺序：
1. 下落列表（Game+0xb3f8 std::list）非空、待发代币数（Game+0xb52c）>0、攻击闪光数（Game+0xbd8c）>0：直接返回（Blocked）。
2. 输入未就绪（PathState.input_ready，Game+0x5e14）且攻击阶段（AttackDamageState.phase，Game+0xb8a8）为 0：若"回合 ≤4 且有特长 0"则跳过敌人攻击；否则 CountAttackers>0 时阶段设为 1 并返回（AttackStarted）。跳过或无攻击者：阶段设为 8，进入 4。
3. 否则（已就绪或阶段非 0）：阶段 1..7 返回（Blocked，敌人攻击进行中）；阶段 8 进入 4；其他值不调用 EndOfTurn。
4. 阶段 8 时调用 Game::EndOfTurn（ScheduleHooks.end_of_turn，嵌入方接 dr_end_of_turn）。
5. 阶段归 0、输入就绪。没有触摸（Game+0x10 为 0）或存在活动的技能/菜单输入目标（Game+0x58ac ≥0）：返回（Idle）。否则清零 Rune 高亮计数（RuneState.highlight_count_164a0，即 dr_reset_rune_preview）并返回 Dispatch——之后按触摸阶段分派（2/3 → 0x17082 撤销暗化等，其他 → 0x16e10），由已恢复的 stroke/selection 分支与后续单元处理。

由此回合循环为：玩家松手 → MatchTiles/奖励/补位（期间下落列表、代币使门槛阻塞）→ 输入未就绪 → 门槛开始敌人攻击（阶段 1）→ Game::Process 每帧推进 ProcessAttack（阶段 1..7 时门槛阻塞）→ ProcessAttack 结束置阶段 8 → 门槛调用 EndOfTurn → 阶段 0、输入就绪 → 下一回合。

验证 `recovered/verify_input_gate.py`：原版从 ProcessInput 入口执行到分派点 0x1674e 或尾声；HavePerk、CountAttackers、GetAttack、std::list::size 为原代码，EndOfTurn 记录并跳过。每组同时比较 CountAttackers 整函数。600 组：阻塞 407、空闲 101、分派 70、开始攻击 22，其中 73 次调用 EndOfTurn；特长跳过、开始攻击、阶段 1..7 阻塞、EndOfTurn、分派等分支均到达。错误副本：回合阈值 `<4`、阶段 8 也阻塞、CountAttackers 不排除冰冻、代币条件 `!=0`、忽略输入目标，均 exit 1。

## T040-C：松手 MatchPath 分支、短路径与公共尾段（Claude，2026-10-19）

`recovered_schedule` 新增：

| 原版 | 原生 | 行为 |
| --- | --- | --- |
| Game::AddRevengeHealth 0xce7c | dr_add_revenge_health | 列优先：未匹配、type 1、enemy_type 21 的敌人 attack += kill_count_15548；UpdateText(1,0,0)、标签 27（格子中心，数字=kill_count，颜色 35，缩放 1）、音效 14 |
| ProcessInput [0x16890,0x16c1c) | dr_release_path | 松手路由之后的 MatchPath 与短路径（见下） |
| ProcessInput [0x16d88,0x16e10) | dr_release_clear | 公共尾段：清空路径与 fake 集合、current_damage=0，标签不在飞行时清 flame/spike 伤害，UpdateCrossVisibility（边界） |

调用顺序：dr_input_gate 返回 Dispatch 且触摸阶段为 2（松手）→ 已恢复的 dr_prepare_release（撤销暗化、ProcessRune(true)、恢复尺寸）→ dr_release_path。

MatchPath（路径长度减 fake 数 > 2）：
1. TurnFinishFlags.flag_1554c = 1（EndOfTurn 结尾清零）。路径含敌人（type 1）→ 音效 27；否则含剑（type 4）→ 音效 26，且帮助标志 0x102d0 & 0x10 时 HelpMenu::Initialise(首格中心, 0.0828125, 0.0828125, 类型 4)。
2. kill_count_15548、generated_enemies、killed_attack_164ac、generated_count 清零 → Game::MatchTiles（ReleaseEvent MatchTiles，嵌入方接 dr_commit_path；其中 MoveMatchedTiles 更新补位计数）。
3. generated_count > 9 且全部为敌人 → 成就 74（100）。
4. current_flame_damage > 0：火焰标签起飞（LabelFlight：arc=Rand(0.4,0.8,流 0)，起点=标签位置 Game+0x14e30，progress 0，speed 1），flame_label_moving=1；spike 同理（0x151d0 / 位置 0x151a4 / spike_label_moving）。
5. kill_count_15548 > 0 → AddRevengeHealth；若 > 14 且职业种族 6：Item::IncreaseStat(11)（Game+0xbe90 的物品，边界事件）、UpdateStats（边界事件，接 dr_update_stats）、标签 34（0.5, 1.290625，颜色 42）、成就 52（10）；TurnFlags.b165b8[0] 时再成就 57（100）。
6. TurnFlags.prev_164a7 且 killed_attack > 0：生命 = min(生命 + killed_attack, 上限 + 加成)，音效 4，与界面生命不同时更新血条，标签 29（Interface::GetTarget(0)，数字 killed_attack，颜色 37）。
7. 未计骷髅（skull_counted=0）：current_leech=0；否则吸血标签起飞（0xc31c / 位置 0xc2f4，无飞行标志）。→ 公共尾段。

短路径：current_leech=0；单格且为职业卷轴（type 6、special 1）时返回 ClassScroll，不做其余改动（[0x16c1c,0x16d88) 为后续单元）；否则公共尾段。

LabelFlight 字段含义由 Game::Process 0x177a4 起的读取确认：speed += 10·dt，progress += speed·dt（上限 1），位置在起点与目标间插值并按 arc 抬高；到达后吸血标签把数值加到生命（属 T040-D）。

验证 `recovered/verify_release.py`：原版从 ProcessInput 入口执行（门槛打开、触摸阶段 2）到尾声 0x170e6，职业卷轴停在 0x16c1c；Rand、std::list::size、AddRevengeHealth 为原代码，ProcessRune 跳过（dr_process_rune 已另验），其余调用记录并跳过，MatchTiles 两侧把用例给出的计数增量加到当前计数上（与原 MatchTiles 累加一致，故能检出调用前未清零）。原生先 dr_prepare_release 再 dr_release_path。500 组：MatchPath 276、短路径清除 203、卷轴 21；18 个分支（敌人/剑音效、帮助、成就 74、火焰/spike 起飞、复仇及其格子、种族 6 升级、成就 57、治疗、血条、吸血清零/起飞、短路径、卷轴、尾段两种清除）全部到达，且有治疗后血条不变的用例。比较事件序列（含标签位置）、选择状态、三个 LabelFlight、计数、flag_1554c、生命/界面生命、36 格 attack、路径与 fake、随机种子。

错误副本（18 个，全部 exit 1）：帮助位改 0x20、成就 74 用 ≥9、去掉全敌人条件、火焰 ≥0、复仇阈值 >15、去掉种族 6 条件、治疗不封顶、血条总更新、吸血条件反转、尾段总清火焰伤害、复仇不排除已匹配、复仇改行优先、起飞 speed 0、MatchTiles 前不清 kill_count / killed_attack、敌人与剑音效优先级、短路径卷轴先返回不清吸血、成就 57 无条件。其中"不清 kill_count"最初存活（测试把 MatchTiles 结果写成覆盖值），改为累加后被拒。

## 后续

- T040-C2：职业卷轴分支 [0x16c1c,0x16d88)（升级 / UnlockMenu、MatchTile、MoveMatchedTiles、CheckEndGame、SerialiseState）；Item::IncreaseStat（stats 模块，对称于 ReduceStat）；UpdateCrossVisibility（1032 字节）、UpdateDimming、ProcessPretzels 等仍为边界，见登记 unrecovered_by_size。
- T040-D：Game::Process 中的游戏部分调度（ProcessEffects、ShieldShatter、标签动画对生命/音效/CheckEndGame 的作用、ProcessAttack 调用条件），界面部分为表现层边界。
- T040-E：InitNewGame（CalculateTilePositions、物品构造、特长判断）。
