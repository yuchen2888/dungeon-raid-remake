# T040-G 原生会话库计划（Claude，2026-10-20）

目标：把整合测试 F1–F4 中由 Python 测试宿主完成的"共享对象 + 钩子接线"固化为一个 C++ 会话（建议新模块 `recovered_session`），对 iOS 层只暴露少量接口；用 F4 的方式（原版 InitNewGame + 每帧真实 Game::Process）与会话逐帧比较。会话不执行任何原版指令。

## 接口草案

```
dr_session* dr_session_create(const dr_session_config*);      // 职业档案、难度、记录模式/模式
void dr_session_new_game(dr_session*, uint32_t seed);           // dr_init_new_game
FrameRoute dr_session_frame(dr_session*, float dt, int32_t touch_phase, float x, float y);   // dr_process_frame
const dr_session_view* dr_session_view(const dr_session*);      // 棋盘、选择、资源、标签飞行、代币、攻击动画等只读视图
size_t dr_session_drain_events(dr_session*, dr_render_event* out, size_t max);   // 表现事件队列（音效、标签、粒子、闪光、帮助、界面值……）
void dr_session_set_screen(dr_session*, int screen, bool open); // 界面层回报：菜单/帮助/结算等是否打开（FrameScreens）
```

## 必须共享的单一对象（F1–F4 实测）

| Game 字段 | 原生对象 | 说明 |
| --- | --- | --- |
| 攻击阶段 Game+0xb8a8 | AttackDamageState | 门槛与 ProcessAttack 共用 |
| RuneState（0x16491、高亮计数、分配数） | RuneState | 门槛、EndOfTurn、ProcessRune 共用 |
| Game+0xbfba | AttackAnimation.counterattack | EndOfTurnState.counterattack 指向它 |
| 代币待处理数 Game+0xb52c | TokenQueue 计数 | AddToken 与 Process 代币循环同一个数 |
| TurnFlags / TurnFinishFlags / EndGameState | 各一个 | 松手、EndOfTurn、结算、新局共用 |
| 闪光数 Game+0xbd8c | AttackAnimation.flare_count | 门槛读取、闪光淡出写 |
| 盾牌碎裂 Game+0xbf88/0xbf8c | ShieldShatterState | 生成事件启动、Process 推进、新局清零 |
| SimpleLabel 活动字节 | NewGameExtra.label_active | 伤害标签段读取；吸血 / 火焰 / 尖刺标签由会话的标签模型维护（damage_labels，T040-K6），当前伤害标签（Game+0xb550）仍由渲染层维护 |
| 当前触摸 Game+0x10/0x14 | TouchState | 整帧调度与 SelectionState.touch 同步 |

## 钩子接线（参考：各单元测试 Native 类中的回调）

| 钩子 | 事件 | 会话动作 |
| --- | --- | --- |
| SelectionHooks | ProcessRune | dr_process_rune（commit 参数） |
| SelectionHooks | ResourceShadows | dr_preview_resources |
| SelectionHooks | RuneMatchTile | dr_match_tile |
| SelectionHooks | ProcessPretzels | dr_process_pretzels（G1） |
| MatchHooks | Token | dr_enqueue_token → TokenHooks Initialise → dr_initialise_token（新代币运动） |
| MatchHooks | SetSpecialType / Shapeshift | dr_set_special_type / dr_shapeshift（G0） |
| ReleaseHooks | MatchTiles | dr_commit_path |
| PathHooks | MoveMatchedTiles | dr_move_matched_tiles |
| RefillHooks | Swap / AppendMoving / Randomise / Stab | 交换 GeneratedTile 附加数据并跟随 activated[]；加入下落列表；dr_randomise_tile；dr_stab |
| GenerationHooks | JumpDown / ShieldShatter | dr_jump_down；dr_initialise_shield_shatter |
| ResourceHooks | Healing / CheckEndGame / Menu | dr_healing（G0）；dr_check_end_game；界面层打开菜单 |
| ScheduleHooks | EndOfTurn | dr_end_of_turn |
| TurnHooks | match_tile / attack_skull / check_end_game / move_matched_tiles / ability(28) / swap / push_token / token_target / token_start | 对应原生函数（见 verify_end_of_turn / verify_abilities） |
| 攻击 ProcessHooks | counterattack / AttackSkull / MoveMatchedTiles / 吸血 | dr_do_counterattack、dr_path_attack_skull、dr_move_matched_tiles、dr_process_vampires |
| GameFrameHooks | input / effects / falling / tokens / pools / flare_fade / damage_label / damage_labels / attack | 见 T040-F3 |
| 其余事件 | 音效、标签、粒子、闪光、帮助、界面值、文字、UV、颜色、成就 | 进入表现事件队列 |

## G3：无界面整局演示（session_demo，Claude，2026-10-20）

`recovered/session_demo.cpp`（`sh recovered/run_session_demo.sh` 编译并运行）：只用原生会话库，不执行任何原版指令、也不经过测试宿主，自己打完整局。嵌入方做渲染层该做的事：职业表（0 号职业 1 级，其余未解锁）、棋盘布局（pitch 1/6）、触摸（按游戏自己的连线规则 dr_can_match 从所有起点随机走出的最长路径，或在技能就绪时按技能按钮）、菜单按钮（动画结束后选项、再确认）、代币飞行目标（演示用常量）。三局各打到结束画面（或 400 回合上限），打印每局回合数、等级、金币、技能数与菜单、技能使用次数；新局、连线、敌人回合、升级 / 商店 / 装备升级菜单、技能都要出现，否则返回非零。纳入 `verify` 的构建步骤（与 stroke_demo、rewards_demo 并列）。这证明规则核心可以脱离原版程序与 Python 测试独立运行，也是 Godot 接入（T050-A）的参考：Godot 侧做的就是这里 main 里的事，再加上画面。

## 仍需恢复或决定的部分（会话之外）

1. 物品模型：Item::Initialise / GenerateStats（1920 字节）/ GenerateName / MakeStats（文字，3028 字节）/ AddUpgrade，ItemUpgrade::GetRandomStat / IsUpgradeAllowed / Initialise。起始物品属性与升级都依赖它（当前测试用零属性）。
2. FoldoutMenu：Initialise(MenuType)（4140 字节，生成升级/商店/技能选项）与 ProcessInput（选择后应用到物品/属性/技能）——含游戏规则，不只是界面。
3. Interface 目标位置（GetTarget / GetSpecialTarget）：代币飞行目标是界面布局常量；当前测试由宿主给出。（后经核实 GetSpecialTarget(Token*) 决定法力药水给哪个技能充能并抽流 5，是规则，已由 T040-L1 恢复。）
4. ProcessPretzels 已恢复（T040-G1，dr_process_pretzels），会话中接 SelectionHooks 的 ProcessPretzels 事件。UpdateDimming（116 字节）待判定；UpdateCrossVisibility 为表现层。
5. SerialiseState / SerialiseClasses：存档（用户暂缓）。
6. 技能系统（2026-10-20 发现，未恢复）：Skill::Activate 0x2ad40（按 40 种技能类型分派，调用约 25 个 Game 技能函数：Earthquake、Teleport、Upgrade、CreateArrows、CreateChain、CreateMagicSword、CreateManaPotions、CreateExplosivePotions、ConvertTiles、ConvertColumnToSwords、GrabTiles、CollectBoard / CollectRandomRow / CollectRandomBlock / CollectEdgeTiles、KillSpecialEnemy、KillSkullsNextToCoins、PromoteNormalEnemy、DemoteSpecialEnemy、FreezeSkulls、ShatterDefence、ExplodeArmour、RemoveSkill 等）、Skill::CanActivate、技能冷却与输入目标（Game+0x58ac）。RuneState.enabled_16491 只由技能启用（已恢复代码中没有置 1 的路径），所以符文玩法在新局对局中走不到。是游戏规则，需单独任务（建议 T040-H）。

## 进度

- T040-G2a 完成：recovered_session（实际接口见 recovered_session.hpp：dr_session_create / destroy / objects / link / set_falling / set_motions / new_game / frame / input_route），verify_session 从新局逐帧对照原版。表现事件目前以"来源 + 原事件结构"转交宿主，尚未做成统一的 dr_render_event 队列；界面开关通过 dr_session_objects 返回的 FrameScreens 直接写。
- T040-G2b 完成：G0 / G1 与资源、遭遇单元内 CheckEndGame、ShieldShatter 已接（T040_SCHEDULE.md）。会话仍转交宿主的规则边界：物品构造 / UpdateStats / IncreaseStat / DestroyUpgrade（物品模型）、ShowMenu（FoldoutMenu）、技能（T040-H）。

## 实施顺序建议

1. 会话骨架：分配并互相连接全部状态，接线上表钩子，表现事件入队；先跑"空帧"（无触摸）与 F1 等价的敌人半回合。
2. 接入触摸：用 dr_process_input 走笔画/松手；对照 F2。
3. 新局：dr_init_new_game；对照 F4（物品仍零属性）。
4. 测试：ctypes 调用会话接口，`dr_session_view` 返回各状态指针，复用现有状态读取函数，与原版 F4 宿主逐帧比较；每一步保持 verify --full 通过并提交。
5. 之后：物品模型、FoldoutMenu、界面目标，再进入 T050 iOS 界面。
