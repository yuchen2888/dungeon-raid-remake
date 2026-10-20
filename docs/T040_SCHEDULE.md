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

## 后续

- T040-C：ProcessInput 触摸分派之后的未恢复部分（松手后 MatchTiles 之前/之后、AddRevengeHealth、Item::IncreaseStat、UnlockMenu、UpdateCrossVisibility、UpdateDimming、ProcessPretzels 等，见登记 unrecovered_by_size）。
- T040-D：Game::Process 中的游戏部分调度（ProcessEffects、ShieldShatter、标签动画对生命/音效/CheckEndGame 的作用、ProcessAttack 调用条件），界面部分为表现层边界。
- T040-E：InitNewGame（CalculateTilePositions、物品构造、特长判断）。
