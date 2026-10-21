# 任务列表

每个任务一次只由一位 AI 认领。填写状态、工具、涉及文件、验收和证据后再写代码。任务顺序对三个工具相同。

| 编号 | 状态 | 目标及验收 | 范围 / 证据 |
| --- | --- | --- | --- |
| T001 | 完成 / Codex | 接力规则、隔离验证、Git 基线；全套现有测试通过，交接安全测试及只读检查；原文件逐项核对 | AGENTS.md、docs/、scripts/、tests/test_relay.py；VALIDATION.md |
| T010 | 完成 / Claude；Codex 复核通过 | 更新恢复函数登记，给 refill/generation/encounters 标明原地址、状态字段、回调和测试；对照现有 46 流程旧清单，不重复计数。结果：17 函数 + 1 片段，零重叠，未建模直接具名调用 0；修正 UpdateCountdown 为 UI 边界 | docs/T010_REGISTRY.json、scripts/t010_registry.py、T010_REVIEW.md；登记检查及 18 段独立字节对照通过，Claude 默认游戏验证已通过且输入指纹未变 |
| T020 | 完成 / Codex、Claude，待复核 | ProcessAttack 每帧逻辑全部恢复（T020-A..O），整函数与原版逐帧差分通过。剩余边界：Game+0xbdc8/+0xbe6c/+0xbe68 的来源、AddFlare 表现实现、阶段 8 之后的调度（转入 T030/T040） | 0x14118 的 55 直接调用点 / 32 目标已登记；见 T020_ATTACK.md |
| T020-A | 完成 / Codex | 护甲损耗片段 0x147e4..0x1487d：特殊敌人 29、真实随机流 5、护甲/UI 状态及有序事件；1510 场景 + 100 连续步骤通过 | recovered/recovered_attack_shield.*、verify_attack_shield.py；20 模块构建 + 2 示例 + 21 verify 全部通过，错误阈值副本被拒绝；T020_ATTACK.md / T020_VALIDATION.json |
| T020-B | 完成 / Claude，待复核 | 护甲吸收片段 0x14790..0x147e3：min(来袭伤害,护甲) 作为 T020-A 的 R10，写回剩余伤害，全吸收时阶段 7 与 9 号敌人标签；单段与连续 [0x14790,0x1487e) 差分 1776 次比较 + 80 连续步骤 | recovered_attack_shield.* 新增 dr_process_attack_armour_absorb、verify_attack_absorb.py；两个错误副本被拒；T020_ATTACK.md T020-B 节 |
| T020-C | 完成 / Claude，待复核 | 阶段 6 扣血片段 0x14a14..0x14ae3：剩余伤害扣生命并归 0、毒＝max(9 号伤害,毒)、阶段 7；ProcessVampires 作有序回调；单段 2080 + 连续回合 240 次比较 | dr_process_attack_health_damage、verify_attack_health.py；两个错误副本被拒；T020_ATTACK.md T020-C 节 |
| T020-D | 完成 / Claude，待复核 | 完整原函数 Game::ProcessVampires 0xdaf8 + Tile::AddHealth 0x3dc6c：吸血鬼回血、封顶与宿敌不封顶路径、列优先遍历；1100 次比较 | recovered_encounters.* 新增 dr_process_vampires / dr_tile_add_health、verify_vampires.py；build.sh 给 encounters 加 rules 依赖；两个错误副本被拒 |
| T020-E | 完成 / Claude，待复核 | 扣血段与真实 ProcessVampires 在同一共享状态上链式差分（原版不再存根）；600 次比较，空回调反向检查失败 | verify_attack_vampires.py；无源码改动 |
| T020-F | 完成 / Claude，待复核 | 敌人削弱片段 0x1487e..0x14937＋循环块：Game+0xbe6c>0 时未出手敌人攻击减该值（最低 1），首个播音效；1011 次比较 | dr_process_attack_weaken、verify_attack_weaken.py；两个错误副本被拒 |
| T020-G | 完成 / Claude，待复核 | 阶段 7 遮罩淡出 0x14ae4..0x14b55：alpha+=dt×(−900) 截断，<0 置阶段 8，两个 SetAlpha；2577 次比较 | dr_process_attack_fade、verify_attack_fade.py；错误常量与 `<=0` 副本均被拒 |
| T020-H | 完成 / Claude，待复核 | 完整原函数 InitialiseFlares 0xd9b0（来袭伤害与 9 号伤害来源）+ 阶段 1 淡入 0x14126..0x141c5（>200 进入阶段 2）；2428 次比较；修正调用登记中的误分类 | dr_initialise_flares / dr_process_attack_fade_in、verify_attack_flares.py；build.sh 给 attack_shield 加 combat 依赖；三个错误副本被拒 |
| T020-I | 完成 / Claude，待复核 | 全体伤害 0x14938..0x14a13＋块：清计数、列优先 AttackSkull、成就 43、MoveMatchedTiles、清 attack_flag；新增集成适配器 dr_path_attack_skull；共享状态全链 430 次比较；修正 verify_motion.py 位置覆盖 | dr_process_attack_damage_all、verify_attack_all.py；三个错误副本（含空回调）被拒 |
| T020-J | 完成 / Claude，待复核 | 完整原函数 DoCounterattack 0x11214：敌人以自身 GetAttack 自伤（列优先）、MoveMatchedTiles、清 attack_flag；共享状态全链 586 次比较 | dr_do_counterattack、verify_counterattack.py；verify_attack_all.py 参数化；两个错误副本被拒 |
| T020-K | 完成 / Claude，待复核 | 阶段 2..4 共享部分 0x141c6..0x143c9：两个计时器、阶段 2→3/4、光效动画、阶段 3→7 并反击；989 次比较（65 次完整反击链） | dr_process_attack_flares、AttackAnimation、verify_attack_flare_phases.py；三个错误副本被拒 |
| T020-L | 完成 / Claude，待复核 | 阶段 4 0x143ca..0x1457b：进度、按护甲进入阶段 5/6、运动参数、Rand(float) 流 0、HelpMenu、三个 alpha；856 次比较 | dr_process_attack_phase4、verify_attack_phase4.py；flares 函数改为返回光效结束标志；三个错误副本被拒 |
| T020-M | 完成 / Claude，待复核 | 阶段 5/6 标签运动 0x1457c..0x146cd：速度/进度、弧线位置、powf alpha、两个出口；1001 次比较 | dr_process_attack_label_motion、verify_attack_label_motion.py；三个错误副本被拒 |
| T020-N | 完成 / Claude，待复核 | 阶段 5 完成准备块 0x146ce..0x1478f：阶段 5→6、下一段运动参数、Rand(float)、−min(伤害,护甲) 标签、HelpMenu；三个出口；653 次比较 | dr_process_attack_phase5_done、verify_attack_phase5_done.py；三个错误副本被拒 |
| T020-O | 完成 / Claude，待复核 | 完整 dr_process_attack 编排；每帧从入口 0x14118 与原版整函数差分：48 次完整攻击、1985 帧、阶段 1..8 全覆盖、所有玩法被调函数为原函数 | verify_process_attack.py；三个编排错误副本被拒 |
| T030 | 进行中 / Claude | 分段恢复 EndOfTurn，验证毒/冻结/能力、再次补位与存档边界。T030-A 调用登记已完成：41 调用点 / 24 目标，未恢复玩法 6 个 + ActivateAbility 下 21 个能力函数 | 原入口 0x13574；docs/T030_EOT.md、T030_EOT_CALLS.json；建议先做小的整函数（Skill::Deactivate、MimicDefence、Resurrect、ProcessCripples、SetFlameVisibility） |
| T030-A | 完成 / Claude，待复核 | EndOfTurn 与 ActivateAbility 一层的调用登记、分类与大小排序 | scripts/t030_eot_audit.py、docs/T030_EOT_CALLS.json；--check 通过 |
| T030-B | 完成 / Claude，待复核 | 完整原函数 MimicDefence 0xbd20、Resurrect 0xaf68、ProcessCripples 0xcae0；新 turn 模块；420 次比较 | recovered_turn.*、verify_turn_small.py；build.sh 加 turn；三个错误副本被拒 |
| T030-C | 完成 / Claude，待复核 | 完整原函数 SetFlameVisibility 0x3d89c + EndOfTurn 冰冻/燃烧结算循环 [0x13710,0x13910)＋循环头；400 次比较、108 次烧死 | dr_set_flame_visibility、dr_end_turn_burn_freeze、verify_turn_burn.py；三个错误副本被拒 |
| T030-D | 完成 / Claude，待复核 | EndOfTurn 生命回复与毒伤玩家段 [0x13910,0x13a1c)；CheckEndGame 暂为有序回调（未恢复）；900 次比较 | dr_end_turn_regen_poison、verify_turn_regen.py；三个错误副本被拒 |
| T030-E | 完成 / Claude，待复核 | CheckEndGame 判断与免死段 [0x10b18,0x10c04)；结束结算暂为 game_over 回调；588 次比较 | dr_check_end_game、verify_check_end_game.py；三个错误副本被拒 |
| T030-F | 完成 / Claude，待复核 | CheckEndGame 结束结算段 + 整函数 GetScore/GetTotalGold/GetTotalUP；CheckEndGame 成为完整恢复；600 次比较 | dr_game_over 等、verify_game_over.py；三个错误副本被拒 |
| T030-G | 完成 / Claude，待复核 | EndOfTurn 开头段 [0x13574,0x13710)：回合数、CheckEndGame（完整原函数全链）、技能冷却与 Deactivate、回合标志轮换；400 次比较 | dr_end_turn_begin、TurnFlags、verify_turn_begin.py；三个错误副本被拒 |
| T030-G 修正 | 完成 / Claude，待复核 | TurnFlags 中重复的 Game+0xbe74..77、0x16491 改写入 SelectionState / 预览 / RuneState（整函数差分发现） | dr_end_turn_begin 增加 RuneState*；verify_turn_begin.py 读回所属状态；错误副本被拒 |
| T030-H | 完成 / Claude，待复核 | EndOfTurn 循环 B 中毒敌人 [0x13a1c,0x13af2)+[0x13d88,0x13daa)，GetPoison/MatchTile 为原代码；240 次比较 | dr_end_turn_poison_enemies、verify_turn_poison.py；三个错误副本被拒 |
| T030-I | 完成 / Claude，待复核 | EndOfTurn 尾段 [0x13b3c,0x13cda)+[0x13d12,0x13d64)+[0x13dc8,0x13e04)：免死轮换、两次 CheckEndGame、MoveMatchedTiles、生成标志、帮助、第 100 回合胜利、SerialiseState 边界；262 次比较 | dr_end_turn_finish、TurnFinishFlags、verify_turn_finish.py；三个错误副本被拒 |
| T030-J | 完成 / Claude，待复核 | Tile::ActivateAbility 0x3f09c 整函数（一次性守卫、跳转表、倒计时、复活）；未恢复能力经 TurnHooks.ability；995 次比较 | dr_activate_ability、verify_activate_ability.py；三个错误副本被拒 |
| T030-K | 完成 / Claude，待复核 | EndOfTurn 能力段：清 Tile+0x254、ProcessCripples、列优先 ActivateAbility；200 次比较 | dr_end_turn_abilities、verify_turn_abilities.py；三个错误副本被拒 |
| T030-L | 完成 / Claude，待复核 | Game::EndOfTurn 整函数组合与整函数差分（原版从入口到返回）；230 次比较，四个结束出口与存档出口全覆盖 | dr_end_of_turn、EndOfTurnState、verify_end_of_turn.py；两个错误副本被拒 |
| T030-M | 完成 / Claude，待复核 | 第一批 8 个能力（RunAway/Explode/Teleport/LowerSkulls/FleeUp/IgniteTiles/StabAttack/ConvertSwordToSkull）恢复并接入 dr_activate_ability；640 次比较，activate/能力段/整函数测试改为让它们以原代码执行 | verify_abilities.py；六个错误副本被拒 |
| T030-N1 | 完成 / Claude，待复核 | MakeAcidPotion、FreezeTiles、BreakRandomShieldSword 恢复并接入（std::set 在测试中模拟）；verify_abilities 共 880 次 | 五个错误副本被拒 |
| T030-N2 | 完成 / Claude，待复核 | ConvertRandomTiles、JumpEnemy、AttractSkulls、AttractShieldsSwords 恢复并接入；verify_abilities 共 1200 次 | 六个错误副本被拒 |
| T030-N3a | 完成 / Claude，待复核 | HealOrBless（含 std::set 重载）恢复并接入；verify_abilities 共 1280 次 | 三个错误副本被拒 |
| T030-N3b | 完成 / Claude，待复核 | ThrowSkull 恢复并接入；代币模块新增 dr_token_queue_push，TurnHooks 追加 push_token；测试框架修正 RandomiseTile 的 JumpDown；1360 次比较 | 三个错误副本被拒 |
| T030-N3c | 完成 / Claude，待复核 | StealGold（含 set 重载）恢复并接入；动作模块新增 dr_token_set_target_tile，TurnHooks 新增 token_target/token_start；1440 次比较 | 四个错误副本被拒 |
| T030-N4a | 完成 / Claude，待复核 | 新模块 stats：Game::UpdateStats 0x14c04（dr_update_stats），ProcessAttack 输入与回复量的生产者；400 次比较 | verify_stats.py；五个错误副本被拒 |
| T030-N4b | 完成 / Claude，待复核 | DestroyUpgrade、GetStatUpgrade/Downgrade 恢复（stats 模块）；经 TurnHooks.ability(28) 接线；verify_stats 共 700 次 | 四个错误副本被拒（另一个为等价变异） |
| T030-N5 | 待做 | Game::SerialiseState 0x91c4（896 字节，存档格式）；之后 T040 回合调度 | 存档格式需与 progression 编解码一并考虑 |
| T040 | 进行中 / Claude | 恢复输入阻塞门槛、新局初始化与完整回合调度 | ProcessInput 0x16638、InitNewGame 0x15c50、Game::Process；同一棋盘可进入下一回合且不执行旧程序；见 T040_SCHEDULE.md |
| T040-A | 完成 / Claude，待复核 | 调用登记：Process 76 / ProcessInput 74 / InitNewGame 51 个直接调用点，已恢复段落与哈希 | scripts/t040_process_audit.py → docs/T040_PROCESS_CALLS.json（--check） |
| T040-B | 完成 / Claude，待复核 | 新模块 schedule：ProcessInput 门槛 [0x16638,0x16748)（dr_input_gate，含 EndOfTurn 调度）与 CountAttackers；600 次比较 | verify_input_gate.py；五个错误副本被拒 |
| T040-C | 完成 / Claude，待复核 | 松手 MatchPath 分支、短路径与公共尾段 [0x16890,0x16c1c)+[0x16d88,0x16e10)（dr_release_path / dr_release_clear）与 AddRevengeHealth；500 次比较 | verify_release.py；错误副本被拒；见 T040_SCHEDULE.md |
| T040-C2a | 完成 / Claude，待复核 | Item::IncreaseStat（dr_item_increase_stat，stats 模块）；verify_stats 增 300 组 | 三个错误副本被拒 |
| T040-C2b | 完成 / Claude，待复核 | 职业卷轴分支 [0x16c1c,0x16d88)（dr_release_class_scroll，接 dr_class_level_up）；verify_release 增至 800 组 | 十个错误副本被拒 |
| T040-E | 完成 / Claude，待复核 | InitNewGame 整函数（dr_init_new_game）与 CalculateTilePositions；字段表来自写入追踪；200 次比较 | verify_new_game.py；错误副本被拒；物品构造仍为边界 |
| T040-D1 | 完成 / Claude，待复核 | Game::Process 伤害标签段 [0x176fc,0x17cda)（dr_process_damage_labels：显示、飞行、到达回血/扣血、CheckEndGame）；300 组 1081 帧 | verify_damage_labels.py；错误副本被拒 |
| T040-D2a | 完成 / Claude，待复核 | Process 棋盘效果段（dr_process_board_effects：首局帮助随机、盾牌碎裂、毒效果淡出）与 InialiseShieldShatter；250 组 620 帧 | verify_board_effects.py；错误副本被拒 |
| T040-D2b | 完成 / Claude，待复核 | Process 回合计数清零、攻击闪光淡出、当前伤害标签与帮助 8 取消笔画（三个原生函数）；300 组 726 帧 | verify_frame_parts.py；错误副本被拒 |
| T040-D3 | 完成 / Claude，待复核 | Game::Process 整帧调度 dr_process_frame（界面门槛、触摸消耗、菜单、步骤顺序与离开/结束）；1500 帧、12 种去向 | verify_frame.py；错误副本被拒 |
| T040-C3a | 完成 / Claude，待复核 | ProcessInput 整函数组合 dr_process_input（门槛 + 分派到笔画/取消/松手/卷轴）；1500 组、9 种去向 | verify_process_input.py；六个错误副本被拒 |
| T040-F1 | 完成 / Claude，待复核 | 回合循环敌人半段携带状态整合：门槛→攻击→闪光→EndOfTurn→输入就绪；8 局 32 回合 1699 帧 | verify_turn_loop.py |
| T040-F2 | 完成 / Claude，待复核 | 完整回合携带状态整合：笔画、松手（MatchTiles / MoveMatchedTiles 原位置）、补位、奖励、攻击、EndOfTurn；8 局 32 回合 2160 帧 | verify_full_turn.py |
| T040-F3 | 完成 / Claude，待复核 | 原版真实 Game::Process 对原生 dr_process_frame（各单元接线）逐帧整合：6 局 22 回合 1603 帧，含 2 次游戏结束 | verify_game_frames.py |
| T040-F4 | 完成 / Claude，待复核 | 从新局（InitNewGame / dr_init_new_game）开始逐帧对局：6 局 60 回合 3574 帧 | verify_new_game_play.py |
| T040-G0 | 完成 / Claude，待复核 | 会话前补齐 SetSpecialType / Shapeshift / Healing（dr_set_special_type / dr_shapeshift / dr_healing）；400 组 | verify_small_units.py；8 个错误副本被拒 |
| T040-G1 | 完成 / Claude，待复核 | ProcessPretzels（dr_process_pretzels：路径斜步交叉计数→奖励等级与预览总数）；1500 组，四个等级都覆盖 | verify_pretzels.py；10 个错误副本被拒，4 个等价变异存活（见 T040_SCHEDULE） |
| T040-G2a | 完成 / Claude，待复核 | 原生会话库 recovered_session：全部状态对象 + C++ 接线（等价 F4 的测试宿主接线）+ GameOverScreen::Initialise 的状态写入；新局 9 局 + 携带中局 10 局，181 回合 11909 帧，11 局以游戏结束收场 | verify_session.py；错误副本见 VALIDATION |
| T040-G2b | 完成 / Claude，待复核 | 会话接上 F 系列仍为适配器的部分：G0（SetSpecialType / Shapeshift / Healing）、G1（ProcessPretzels）、单元内 CheckEndGame（资源、遭遇、松手）、ShieldShatter 事件 → dr_initialise_shield_shatter；测试中原版同时执行这些函数 | verify_session.py 扩展 |
| T040-H1 | 完成 / Claude，待复核 | 新模块 skills：Skill::Activate（40 类型分派、标志类技能、符文启用）、Skill::CanActivate(int)、Game::RemoveSkill；棋盘技能函数暂为 SkillHooks.action 边界 | verify_skills.py；21 个错误副本被拒；T040_SKILLS.md |
| T040-I | 完成 / Claude，待复核 | Game::AddFlare 的游戏状态（Rand(0,360,流 0) + 闪光数）：dr_add_flare，会话所有 Flare 事件接上 | verify_add_flare.py；verify_session.py；见 T040_SCHEDULE |
| T040-H2 | 完成 / Claude，待复核 | 棋盘技能第一批：Upgrade、FreezeSkulls、ConvertTiles、CreateManaPotions、CreateExplosivePotions、CreateArrows、CreateMagicSword | verify_skill_board.py；16 个错误副本被拒；T040_SKILLS.md |
| T040-H3 | 完成 / Claude，待复核 | 棋盘技能第二批：DemoteSpecialEnemy、PromoteNormalEnemy、KillSpecialEnemy、GrabTiles、ShatterDefence、ExplodeArmour | verify_skill_board2.py；17 个错误副本被拒；T040_SKILLS.md |
| T040-H4 | 完成 / Claude，待复核 | 棋盘技能第三批：CheckShockAwe、CollectBoard、CollectRandomRow / Block、CollectEdgeTiles、ConvertColumnToSwords、Teleport、Earthquake、KillSkullsNextToCoins、CreateChain；22 个技能函数全部恢复 | verify_skill_board3.py；20 个错误副本被拒、1 个等价 |
| T040-H5 | 完成 / Claude，待复核 | 技能按钮规则（Interface::ProcessInput 技能部分：按下 / 松开、冷却重置）、FireBreath、动作分派 dr_skill_action | verify_skill_input.py；12 个错误副本被拒 |
| T040-J1 | 完成 / Claude，待复核 | AddParticles（33 / 81 次）与 SimpleLabel::Initialise（经 AddSimpleLabel 两个重载，1 次，类型 1/3/8/9/10 除外）的流 0 抽取：dr_add_particles / dr_add_simple_label，会话所有粒子 / 标签事件接上 | verify_effect_draws.py；verify_session.py |
| T040-J2 | 完成 / Claude，待复核 | Game::UpdateCrossVisibility：dr_update_cross_visibility（路径格子按 Tile::GetDamageType 设置十字可见性、十字标签 30 / 35 各抽 1 次、未选中的敌人 30），会话在 SelectionEvent / ReleaseEvent CrossVisibility 调用 | verify_cross.py；verify_session.py |
| T040-J | 完成（J1..J3） / Claude，待复核 | J3：Game::Start 只在 App 启动时调用，每局 InitNewGame 用 time() 重设六路种子，其抽取到不了游戏，无需代码（REVERSE_ENGINEERING.md T040-J3）。 表现层代码里的流 0 随机抽取（同 T040-I 的 AddFlare）：AddParticles（类型 0 抽 33 次，类型 1–3 抽 81 次）、SimpleLabel::Initialise（除类型 1/3/8/9/10 外抽 1 次；经 AddSimpleLabel 两个重载）、UpdateCrossVisibility（路径每次变化时为路径格子重建十字标签，类型 30 / 35 各抽 1 次，需恢复 Tile::GetDamageType）、Game::Start。流 0 也决定职业卷轴出现的倒计数、代币飞行速度等，所以这些抽取改变后续游戏结果 | 计数已用原版实测（40 个随机棋盘不变）；见 REVERSE_ENGINEERING.md T040-J |
| T040-H6 | 完成 / Claude，待复核 | 技能接入会话：SkillState / SkillInput / skill_button，InterfaceProcess 处 dr_skill_input，技能事件与动作接到各单元；门槛输入目标改为按下的技能槽 | verify_session.py 技能阶段；12 个错误副本被拒 |
| T040-H | 完成（H1..H6） / Claude，待复核 | 技能系统：Skill::Activate（40 种类型）/ CanActivate 与 22 个 Game 技能函数、技能按钮、会话接线；Upgrade 的升级菜单属物品模型任务 | verify_skills / skill_board / skill_board2 / skill_board3 / skill_input / session |
| T040-G | 完成（G0..G2b） / Claude，待复核 | 原生会话库：把测试宿主中的共享对象与钩子接线固化为 C++ 会话（新局、每帧 dr_process_frame、触摸输入、状态查询），供 iOS 层调用；用 F4 方式与原版逐帧比较 | 新 recovered_session 模块 + 测试 |
| T040-F | 完成（F1..F4） | 原生整局示例：用 dr_init_new_game + dr_process_frame 与各步骤接线跑若干回合，与原版逐帧比较（不执行旧程序的整局验收） | 新的整合测试 |
| T040-C3 | 完成 / Claude，待复核 | ProcessInput 剩余：UpdateDimming（dr_update_dimming，会话经 SessionObjects.dimmed 交给渲染层，随 K5 提交）；ProcessPretzels 已由 T040-G1、UpdateCrossVisibility 已由 T040-J2 完成 | verify_dimming.py；3 个错误副本被拒 |
| T040-K1 | 完成 / Claude，待复核 | 升级菜单（FoldoutMenu 类型 0）的选项生成：recovered_menu 新模块（dr_menu_open_level、Skill::Initialise 两种、GetSkillPool、IsSkillUnlocked、基础冷却表与职业基础技能表） | verify_menu_level.py；19 个错误副本被拒、1 个等价 |
| T040-K2 | 完成 / Claude，待复核 | 升级菜单的选择、确认、开关动画与生效：dr_menu_input、dr_menu_process、dr_set_skill（Game::SetSkill） | verify_menu_flow.py；23 个错误副本被拒 |
| T040-K3a | 完成 / Claude，待复核 | 物品生成：recovered_items 新模块（新物品与商店物品的图标、名字、属性生成，IsUpgradeAllowed、GetRandomStat） | verify_items.py；20 个错误副本被拒、4 个等价 |
| T040-K3b/K4 | 完成 / Claude，待复核 | 商店（dr_menu_open_shop：3 件物品、卷轴、SetItem、UpdateStats）与装备升级（dr_menu_open_upgrade：4 个升级方案、AddUpgrade） | verify_menu_shop.py、verify_menu_upgrade.py；24 个错误副本被拒、1 个等价 |
| T040-K5a | 完成 / Claude，待复核 | 装备与属性接入会话：新局造装备、UpdateStats、种族 6 IncreaseStat、敌人 28 DestroyUpgrade（不再是边界），两份几率副本同步 | verify_session.py 装备阶段 |
| T040-K5b | 完成 / Claude，待复核 | 菜单接入会话：经验 / 金币 / 升级点满 100 与技能 Upgrade 打开三种菜单，菜单打开时每帧 dr_menu_process（menu_button 由渲染层写入），买下的卷轴 dr_skill_activate | verify_session.py（菜单按原代码执行）；32065 帧一致；14 个错误副本被拒、1 个等价、2 个不可达 |
| T040-K6 | 待做（低优先） | 商店卷轴读到的吸血标签（Game+0xbfc0）类型与顶点：需 SimpleLabel::RegenerateLabel 的模型；会话目前取 0，只在吸血标签从未显示时与原版一致 | T040_MENU.md 怪行为一节 |
| T040-K | 完成（K1..K5） / Claude，待复核 | 升级 / 商店 / 装备升级菜单（FoldoutMenu）：资源单元在经验、金币、升级点满 100 时发出 Menu 0 / 1 / 2，原版 Interface::ShowMenu → FoldoutMenu::Initialise(MenuType)（4140 字节）生成选项（RandI 6 处、Rand 2 处；职业技能池 CharacterClass::GetSkillPool、Game::IsSkillUnlocked、Skill::CanActivate；商店 Game::GetItem + Item::Initialise(Item*)；装备升级 ItemUpgrade::Initialise / GetRandomStat 等），菜单打开期间 Game::Process 只处理菜单；FoldoutMenu::ProcessInput（636 字节）应用选择（Game::SetSkill 688 字节、物品购买、ItemUpgrade 应用、Item::GenerateStats / MakeStats）。K5 已把装备与三种菜单接入会话，选择升级这一核心玩法在原生整局中可用。分步：K1 选项生成（三种菜单），K2 选择的应用（SetSkill、物品、装备升级），K3 物品模型（Item 构造 / GenerateStats / MakeStats、ItemUpgrade），K4 会话接线（菜单打开 / 选择接口）与整局测试 | 新单元测试 + verify_session 菜单阶段 |
| T050-A | 后端完成后（用户 2026-10-20 决定先做后端） | Godot 4 试玩原型：recovered_session 经 GDExtension 装入 Godot；简单图形显示棋盘、鼠标 / 触摸连线、打怪、敌人回合、直到游戏结束；Mac 上可试玩 | 新目录（如 frontend/godot/）；用户试玩确认手感；原型明确标注，非正式画面 |
| T050 | 待 T040-H 等规则完成 | iOS 正式版（优先）：高清画面、多语言、新手教程，玩法与原版一致；高清美术来源与原版素材授权待用户决定 | 实机 / 模拟器交互验收 |
| T060 | 往后，但一定要做 | 安卓、PC（Windows / Mac）版本，用同一 Godot 项目导出 | 各平台实机验收 |
| T070 | 最后 | 新技能、新职业等新内容 | 用户确认设计后再做 |

首次接力已验收：Claude Code 桌面会话于 2026-10-18 完成 T010 并提交 8d9604a，Codex 从干净工作区接手，重跑 `--check`、独立核对全部 18 段字节、确认 HavePerk/GetSpecialEnemyCount 和容器替代边界，修正一处 UI 误分类。详细结果见 T010_REVIEW.md。Gemini CLI 接力尚未发生。

认领记录：`T010 / claude / 起始 557cf44 / 继承差异：无（工作树干净） / 目标：三模块地址-状态-回调-测试登记 / 文件：scripts/t010_registry.py、docs/T010_REGISTRY.json、docs/*.md / 验收：--check exit 0 + verify 四组 passed / 结果：.relay/runs/20261018T070600.453747Z / 下一步：T020 前用同法给 ProcessAttack 0x14118 列静态调用分类`

认领记录：`T020-B / claude / 起始 1b1ad9f / 继承差异：无 / 目标：护甲吸收片段 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_absorb.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-B 节 / 下一步：0x14a14 起扣血代码`

认领记录：`T020-C / claude / 起始 929526b / 继承差异：无 / 目标：阶段 6 扣血片段 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_health.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-C 节 / 下一步：ProcessVampires 0xdaf8`

认领记录：`T020-D / claude / 起始 496d9aa / 继承差异：无 / 目标：ProcessVampires + Tile::AddHealth / 文件：recovered/recovered_encounters.*、recovered/build.sh、recovered/recovered_attack_shield.hpp（注释）、recovered/verify_vampires.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-D 节 / 下一步：扣血段接真实 ProcessVampires 的连续回合测试`

认领记录：`T020-E / claude / 起始 77307b3 / 继承差异：无 / 目标：扣血段接真实吸血的链式验证 / 文件：recovered/verify_attack_vampires.py、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 空回调反向检查失败 / 结果：见 VALIDATION.md T020-E 节 / 下一步：阶段 7 收尾或 0xbe6c/0xbe68 分支`

认领记录：`T020-F / claude / 起始 98a112a / 继承差异：无 / 目标：敌人削弱片段 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_weaken.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-F 节 / 下一步：Game+0xbe68 全体伤害`

认领记录：`T020-G / claude / 起始 43a2c7f / 继承差异：无 / 目标：阶段 7 遮罩淡出 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_fade.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-G 节 / 下一步：阶段 1 或全体伤害`

认领记录：`T020-H / claude / 起始 4fa6eba / 继承差异：无 / 目标：InitialiseFlares + 阶段 1 / 文件：recovered/recovered_attack_shield.*、recovered/build.sh、recovered/verify_attack_flares.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-H 节 / 下一步：阶段 2..4 或全体伤害`

认领记录：`T020-I / claude / 起始 536b68a / 继承差异：无 / 目标：全体伤害与共享状态全链测试 / 文件：recovered/recovered_attack_shield.*、recovered/recovered_path.*、recovered/verify_attack_all.py、recovered/verify_motion.py（测试替身修正）、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-I 节 / 下一步：DoCounterattack`

认领记录：`T020-J / claude / 起始 72bf218 / 继承差异：无 / 目标：DoCounterattack / 文件：recovered/recovered_attack_shield.*、recovered/verify_counterattack.py、recovered/verify_attack_all.py（参数化）、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-J 节 / 下一步：阶段 2..4`

认领记录：`T020-K / claude / 起始 3b0ce5f / 继承差异：无 / 目标：阶段 2..4 共享部分 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_flare_phases.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-K 节 / 下一步：阶段 4`

认领记录：`T020-L / claude / 起始 b9d8ec3 / 继承差异：无 / 目标：阶段 4 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_phase4.py、recovered/verify_attack_flare_phases.py（结尾可覆盖）、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-L 节 / 下一步：阶段 5/6 动画`

认领记录：`T020-M / claude / 起始 6b049e7 / 继承差异：无 / 目标：阶段 5/6 标签运动 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_label_motion.py、recovered/verify_attack_all.py（多出口）、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-M 节 / 下一步：0x146ce 完成准备块`

认领记录：`T020-N / claude / 起始 b7c08b0 / 继承差异：无 / 目标：阶段 5 完成准备块 / 文件：recovered/recovered_attack_shield.*、recovered/verify_attack_phase5_done.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 结果：见 VALIDATION.md T020-N 节 / 下一步：完整 ProcessAttack 串联`

认领记录：`T020-O / claude / 起始 d7a24e3 / 继承差异：无 / 目标：完整 ProcessAttack 编排与整函数差分 / 文件：recovered/recovered_attack_shield.*、recovered/verify_process_attack.py、scripts/verify.py、scripts/t020_attack_audit.py、docs/ / 验收：verify --full 全部通过 + 编排错误副本 exit 1 / 结果：见 VALIDATION.md T020-O 节 / 下一步：Codex 复核 T020-B..O，然后 T030 EndOfTurn`

认领记录：`T030-A / claude / 起始 ad116bd / 继承差异：无 / 目标：EndOfTurn 调用登记 / 文件：scripts/t030_eot_audit.py、docs/T030_EOT_CALLS.json、docs/T030_EOT.md、docs/TASKS.md、docs/PROJECT_STATE.md / 验收：t030_eot_audit.py --check / 下一步：小整函数恢复`

认领记录：`T030-B / claude / 起始 caed5c5 / 继承差异：无 / 目标：三个小整函数 / 文件：recovered/recovered_turn.*、recovered/build.sh、recovered/verify_turn_small.py、scripts/verify.py、scripts/t030_eot_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：SetFlameVisibility 与 EndOfTurn 开头段`

认领记录：`T030-C / claude / 起始 1825640 / 继承差异：无 / 目标：SetFlameVisibility 与冰冻/燃烧循环 / 文件：recovered/recovered_turn.*、recovered/build.sh、recovered/verify_turn_burn.py、scripts/verify.py、scripts/t030_eot_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：生命回复与毒伤玩家段 0x13910..0x13a1c`

认领记录：`T030-D / claude / 起始 1825640（与 T030-C 同轮）/ 继承差异：无 / 目标：回复与毒伤段 + 测试去墙钟超时 / 文件：recovered/recovered_turn.*、recovered/verify_turn_regen.py、recovered/verify_attack_*.py、verify_turn_*.py（timeout=0）、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：CheckEndGame`

认领记录：`T030-E / claude / 起始 f576964 / 继承差异：无 / 目标：CheckEndGame 判断段 / 文件：recovered/recovered_turn.*、recovered/build.sh、recovered/verify_check_end_game.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：GetScore/GetTotalGold/GetTotalUP 与结束结算段`

认领记录：`T030-F / claude / 起始 7b9c85a / 继承差异：无 / 目标：结束结算与计分函数 / 文件：recovered/recovered_turn.*、recovered/verify_game_over.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：EndOfTurn 开头段与循环 B`

认领记录：`T030-G / claude / 起始 178a77e / 继承差异：无 / 目标：EndOfTurn 开头段 / 文件：recovered/recovered_turn.*、recovered/verify_turn_begin.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：循环 B（中毒敌人）`

认领记录：`T030-H/I / claude / 起始 a4371b9 / 继承差异：无 / 目标：EndOfTurn 循环 B 与尾段 / 文件：recovered/recovered_turn.*、recovered/verify_turn_poison.py、recovered/verify_turn_finish.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：T030-J 能力循环`

认领记录：`T030-J/K/L / claude / 起始 16470b2 / 继承差异：无 / 目标：ActivateAbility、能力段、EndOfTurn 整函数 / 文件：recovered/recovered_turn.*、recovered/build.sh、recovered/verify_activate_ability.py、recovered/verify_turn_abilities.py、recovered/verify_end_of_turn.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本 exit 1 / 下一步：T030-M 能力函数`

认领记录：`T030-M / claude / 起始 92ecb2e / 继承差异：无 / 目标：第一批 8 个能力函数 / 文件：recovered/recovered_turn.*、recovered/verify_abilities.py 及 activate/能力段/整函数测试、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T030-N 剩余 11 个能力`

认领记录：`T030-N1 / claude / 起始 294f14a / 继承差异：无 / 目标：MakeAcidPotion、FreezeTiles、BreakRandomShieldSword / 文件：recovered/recovered_turn.*、recovered/verify_abilities.py、recovered/verify_activate_ability.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T030-N2`

认领记录：`T030-N2 / claude / 起始 ab4b93b / 继承差异：无 / 目标：ConvertRandomTiles、JumpEnemy、AttractSkulls、AttractShieldsSwords / 文件：recovered/recovered_turn.*、recovered/verify_abilities.py、recovered/verify_activate_ability.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T030-N3`

认领记录：`T030-N3a / claude / 起始 d8c3007 / 继承差异：无 / 目标：HealOrBless / 文件：recovered/recovered_turn.*、recovered/verify_abilities.py、recovered/verify_activate_ability.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：代币接口与 ThrowSkull`

认领记录：`T030-N3b / claude / 起始 0ad60e6 / 继承差异：无 / 目标：ThrowSkull 与代币直接入队 / 文件：recovered/recovered_tokens.*、recovered/recovered_turn.*、recovered/verify_abilities.py、recovered/verify_activate_ability.py、recovered/verify_end_of_turn.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：StealGold、DestroyUpgrade`

认领记录：`T030-N3c / claude / 起始 5755260 / 继承差异：无 / 目标：StealGold / 文件：recovered/recovered_motion.*、recovered/recovered_turn.*、recovered/verify_abilities.py、recovered/verify_activate_ability.py、recovered/verify_end_of_turn.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：物品模型与 DestroyUpgrade`

认领记录：`T030-N4a / claude / 起始 ded977a / 继承差异：无 / 目标：Game::UpdateStats / 文件：recovered/recovered_stats.*、recovered/verify_stats.py、recovered/build.sh、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：Item::MakeStats 与 DestroyUpgrade`

认领记录：`T030-N4b / claude / 起始 80e0e2e / 继承差异：无 / 目标：DestroyUpgrade / 文件：recovered/recovered_stats.*、recovered/recovered_turn.hpp、recovered/verify_stats.py、recovered/build.sh、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：SerialiseState 或 T040`

认领记录：`T040-G / claude / 起始 51927de / 继承差异：无 / 目标：先补 G0 三个小函数，再设计/实现原生会话库 / 文件：recovered/recovered_schedule.*、recovered/verify_small_units.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：会话库设计`

认领记录：`T040-F（先做 C3a）/ claude / 起始 219c41d / 继承差异：无 / 目标：ProcessInput 整函数组合，然后原生整局 / 文件：recovered/recovered_schedule.*、recovered/verify_process_input.py、recovered/verify_release.py（空路径保护）、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-F 原生整局`

认领记录：`T040-D3 / claude / 起始 cfae180 / 继承差异：无 / 目标：Game::Process 整帧调度 / 文件：recovered/recovered_schedule.*、recovered/verify_frame.py、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-F`

认领记录：`T040-D2b / claude / 起始 6877c6f / 继承差异：无 / 目标：Process 回合计数、闪光淡出、伤害标签 / 文件：recovered/recovered_schedule.*、recovered/verify_frame_parts.py、recovered/verify_new_game.py（字段改名）、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-D3`

认领记录：`T040-K / claude / 起始 3097f03 / 继承差异：无 / 目标：FoldoutMenu 三种菜单（升级技能、商店、装备升级）的选项生成与选择应用、物品模型、会话接线 / 文件：recovered/recovered_menu.*（新）、recovered/recovered_stats.*、recovered/recovered_session.*、recovered/verify_*.py、recovered/build.sh、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：K1 选项生成`

认领记录：`T040-D2a / claude / 起始 a866a5e / 继承差异：无 / 目标：Process 棋盘效果段 / 文件：recovered/recovered_schedule.*、recovered/verify_board_effects.py、recovered/verify_new_game.py（0xbf88 改归属）、scripts/、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-D2b`

认领记录：`T040-D1 / claude / 起始 6088b38 / 继承差异：无 / 目标：Game::Process 伤害标签段 / 文件：recovered/recovered_schedule.*、recovered/verify_damage_labels.py、scripts/t040_process_audit.py、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-D2`

认领记录：`T040-E / claude / 起始 9140da5 / 继承差异：无 / 目标：InitNewGame 与 CalculateTilePositions / 文件：recovered/recovered_schedule.*、recovered/verify_new_game.py、recovered/build.sh、scripts/t040_process_audit.py、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-D`

认领记录：`T040-C2a/C2b / claude / 起始 94e35ca / 继承差异：无 / 目标：Item::IncreaseStat、职业卷轴分支 / 文件：recovered/recovered_stats.*、recovered/recovered_schedule.*、recovered/verify_stats.py、recovered/verify_release.py、recovered/build.sh、scripts/t040_process_audit.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-E 或 T040-D`

认领记录：`T040-C / claude / 起始 88a0d7b / 继承差异：无 / 目标：松手 MatchPath 分支与公共尾段、AddRevengeHealth / 文件：recovered/recovered_schedule.*、recovered/verify_release.py、recovered/build.sh、scripts/t040_process_audit.py、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-C2`

认领记录：`T040-A/B / claude / 起始 1ee4beb / 继承差异：无 / 目标：调度调用登记、ProcessInput 门槛 / 文件：recovered/recovered_schedule.*、recovered/verify_input_gate.py、recovered/build.sh、scripts/t040_process_audit.py、scripts/t030_eot_audit.py（排序确定化）、scripts/verify.py、docs/ / 验收：verify --full 全部通过 + 错误副本被拒 / 下一步：T040-C`

认领记录模板：`Txxx / 工具 / 起始 HEAD / 继承差异 / 目标 / 文件 / 验收命令 / 结果路径 / 下一步`。详细活动现场存于 `.relay/active/owner.json`，持久事实随原子提交更新这里和 PROJECT_STATE.md。
