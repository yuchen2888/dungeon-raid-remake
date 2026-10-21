# 当前状态

更新：2026-10-21（America/Los_Angeles）。维护者：Claude（T040-K6）。当前阶段：规则核心（后端）的计划项——战斗、敌人回合、整帧调度、技能系统、装备、升级 / 商店 / 装备升级菜单——均已原生恢复并接入整局会话，与原版逐帧一致，待复核；存档 / 读档也已恢复（T030-N5）；剩少量已知差异；无界面整局演示（T040-G3）证明规则核心可独立打完整局；用户 2026-10-21 决定先做存档：对局存档、读档、继续游戏、职业进度与最高分已完成（T030-N5）；随后用户选择先补商店卷轴的已知差异，T040-K6 已完成（伤害标签的显示数据按原版恢复）；接着按用户同意的推荐做后端收尾盘点（T040_BACKEND_INVENTORY.md）：一局之外的规则分 7 项（T040-M1..M7）补做；之后进入 Godot 试玩原型（T050-A，计划见 T050_GODOT_PLAN.md，需用户先安装 Godot）；Gemini 尚未接入。

## 已核实

- 实际工作区为本 docs/ 的上级目录；创建前无 Git，无已有分支、提交、暂存修改或远端。源码基线提交 `bd9bbd3` 保存了原有 78 个源码/文档/脚本路径（含新增忽略规则）。
- 原有 7,282 个文件、1,207,443,199 字节已记录在本地 `.relay/bootstrap-before.json`，并在验证后重新逐项核对哈希。
- recovered/ 当前存在 30 个 `recovered_*.cpp` 模块、25 个头文件、82 个 verify 脚本、三个独立源码示例（含整局演示 session_demo）。attack_shield 模块现包含 ProcessAttack 的全部片段及整函数编排 dr_process_attack（T020-O）；turn 模块为 T030 新增；补位、生成、JumpDown/Stab 等既有逻辑继续复用。
- 根外同级 ZIP（2026-10-16）缺少 refill/generation/encounters 三组新源码和四个新验证脚本，rewards_demo.cpp 也较旧；不从 ZIP 覆盖当前代码。
- `/Users/yuchen/Documents/Codex/2026-10-14/new-chat/dungeon-raid-investigation` 是较早研究副本：7 个恢复模块与当前同名源码一致，另有旧版头文件/脚本；未改动或合并覆盖。
- Codex CLI 0.135.0 可执行；Claude Code 以桌面应用会话运行（`claude` 仍不在 PATH，check 如实显示），Gemini CLI 未发现。2026-10-18 Claude 完成 T010 并提交，属于首次实际跨模型接力；Gemini 尚未参与。
- T010：refill/generation/encounters 的 17 个原函数 + Game::Process 下落片段 0x173c8 已登记原地址、字节哈希、状态偏移、hook 与测试（docs/T010_REGISTRY.json）；与 46 流程零重叠且不并入计数。Codex 独立核对全部 18 段字节与反汇编一致。未恢复的玩法回调为 Game::CheckEndGame（测试强制返回 0）；Tile::UpdateCountdown 为未恢复的倒计时 UI 显示，不是推进玩法倒计时。
- T020-A：ProcessAttack 的 55 个直接调用点 / 32 个目标已登记，护甲损耗片段 `[0x147e4,0x1487e)` 已成为独立原生源码并接入统一构建/验证；复用共享棋盘、护甲和六个随机流。前一阶段计算出的已吸收伤害由调用者提供；完整调度和后续生命扣减仍未恢复。
- T020-B：上游护甲吸收片段 `[0x14790,0x147e4)` 恢复为 `dr_process_attack_armour_absorb`（同一 attack_shield 模块），R10 不再由调用者假设；与 T020-A 连成 `[0x14790,0x1487e)` 对原版连续差分通过。新增状态 AttackDamageState：阶段 Game+0xb8a8、来袭伤害 +0xbe84、9 号敌人伤害 +0x1553c。仍缺阶段调度、扣血、反击、吸血。
- T020-C：阶段 6 扣血片段 `[0x14a14,0x14ae4)` 恢复为 `dr_process_attack_health_damage`：剩余伤害扣生命（负数归 0）、毒＝max(9 号敌人伤害,毒)、阶段 7。阶段 5→6→7 的切换位置已核实（0x146ce/0x146d8）。Game::ProcessVampires 未恢复，作为有序回调。
- T020-D：完整原函数 Game::ProcessVampires 0xdaf8、Tile::AddHealth 0x3dc6c 恢复为 dr_process_vampires / dr_tile_add_health（encounters 模块），原版完整执行对照通过。扣血段通过 Vampires 事件交给调用方执行。
- T020-E：扣血段与真实 ProcessVampires 已在同一共享状态上链式差分（原版侧不再存根，原生 Vampires 事件调用 dr_process_vampires），空回调会被测试拒绝。
- T020-F：护甲损耗之后的敌人削弱片段 `[0x1487e,0x14938)`（含两段循环块）恢复为 `dr_process_attack_weaken`：Game+0xbe6c>0 时未出手敌人攻击减该值、最低 1。接下来的 Game+0xbe68 全体伤害仍未恢复。
- T020-G：阶段 7 遮罩淡出 `[0x14ae4,0x14b56)` 恢复为 `dr_process_attack_fade`：遮罩 alpha 兼作计时器，每帧 dt×(−900)，<0 时置阶段 8。
- T020-H：完整原函数 InitialiseFlares 0xd9b0（来袭伤害与 9 号伤害的来源）和阶段 1 淡入 `[0x14126,0x141c6)` 已恢复；调用登记中把 InitialiseFlares 当作表现边界的误分类已更正。AddFlare 的光效列表/计数仍由调用方负责。
- T020-I：全体伤害片段恢复为 `dr_process_attack_damage_all`，AttackSkull 经新增集成适配器 `dr_path_attack_skull`、MoveMatchedTiles 经 `dr_move_matched_tiles`，在完整共享状态上与原版全链差分（含击杀、奖励代币、补位、生成、下落）。顺带修正测试框架 verify_motion.py 的位置覆盖近似。
- T020-J：完整原函数 DoCounterattack 0x11214 恢复为 `dr_do_counterattack`，在共享状态上全链差分。ProcessAttack 直接调用的玩法函数已全部有恢复实现。
- T020-K：阶段 2..4 共享部分 `[0x141c6,0x143ca)` 恢复为 `dr_process_attack_flares`（新增 AttackAnimation 结构），含阶段 2→3/4、光效动画和阶段 3→7 触发反击，在完整共享状态上差分。
- T020-L：阶段 4 `[0x143ca,0x1457c)` 恢复为 `dr_process_attack_phase4`：按护甲进入阶段 5/6、运动参数、Rand(float) 流 0；原版栈上的“光效结束”标志改由 dr_process_attack_flares 返回。
- T020-M：阶段 5/6 标签运动 `[0x1457c,0x146ce)` 恢复为 `dr_process_attack_label_motion`（返回是否完成，对应原版两个出口）。
- T020-N：阶段 5 完成准备块 `[0x146ce,0x14790)` 恢复为 `dr_process_attack_phase5_done`。ProcessAttack 的每一段指令都已有恢复实现，尚未串成完整函数。
- T020-O：`dr_process_attack` 按原控制流组合全部片段；verify_process_attack.py 每帧从原版入口 0x14118 调整函数比较完整共享状态与事件：48 次完整攻击（阶段 1→8）、1985 帧通过。测试替身仅平台 powf 与 AddFlare 追加计数模型。
- T030-A：EndOfTurn 0x13574 调用登记（docs/T030_EOT_CALLS.json、T030_EOT.md）：41 调用点 / 24 目标；未恢复玩法 CheckEndGame、Skill::Deactivate、SetFlameVisibility、ProcessCripples、ActivateAbility（下有 21 个能力函数）、SerialiseState。
- T030-B：新增 turn 模块，完整原函数 MimicDefence、Resurrect、ProcessCripples 恢复并在全链共享状态上差分（ProcessCripples 的 MatchTile 为原函数）。
- T030-C：完整原函数 SetFlameVisibility 与 EndOfTurn 冰冻/燃烧结算循环恢复（dr_set_flame_visibility、dr_end_turn_burn_freeze），在全链共享状态上差分。
- T030-D：EndOfTurn 生命回复与毒伤段恢复（dr_end_turn_regen_poison），CheckEndGame 暂为有序回调。另将自写测试的 emu_start 墙钟超时改为 0（系统过载时曾导致假失败）；继承测试仍有墙钟超时，见 T030_EOT.md。
- T030-E：CheckEndGame 判断与免死段恢复为 dr_check_end_game；结束结算（计分、职业统计、最高分、界面、SerialiseClasses）暂为 game_over 回调。
- T030-F：CheckEndGame 结束结算与 GetScore/GetTotalGold/GetTotalUP 恢复，CheckEndGame 成为完整恢复（dr_check_end_game + dr_game_over），整函数差分通过；计分表/界面/职业档案序列化为事件边界。
- T030-G：EndOfTurn 开头段恢复（dr_end_turn_begin：回合数、CheckEndGame、技能冷却、回合标志轮换），测试中 CheckEndGame 为完整原函数全链。
- T030-H：EndOfTurn 中毒敌人循环恢复（dr_end_turn_poison_enemies），GetPoison/MatchTile 为原代码全链。
- T030-I：EndOfTurn 尾段恢复（dr_end_turn_finish：免死轮换、两次 CheckEndGame、MoveMatchedTiles、生成标志、帮助弹窗、第 100 回合胜利）；SerialiseState 为存档边界事件。
- T030-G 修正：开头段把 Game+0xbe74..77、0x16491 写回其所属状态（SelectionState、预览、RuneState），由整函数差分发现。
- T030-J/K/L：Tile::ActivateAbility 分派、EndOfTurn 能力段恢复；Game::EndOfTurn 整函数组合 dr_end_of_turn 与原版整函数差分通过（未恢复的能力函数与 SerialiseState 为边界）。
- T030-M：第一批 8 个敌人能力恢复并接入（RunAway/Explode/Teleport/LowerSkulls/FleeUp/IgniteTiles/StabAttack/ConvertSwordToSkull），在整函数差分中以原代码执行。
- T030-N1：MakeAcidPotion、FreezeTiles、BreakRandomShieldSword 恢复并接入（测试中模拟 std::set<Tile*>）。
- T030-N2：ConvertRandomTiles、JumpEnemy、AttractSkulls、AttractShieldsSwords 恢复并接入。
- T030-N3a：HealOrBless（含 std::set 重载）恢复并接入。
- T030-N3b：ThrowSkull 恢复并接入（代币模块新增 dr_token_queue_push；TurnHooks.push_token）。
- T030-N3c：StealGold 恢复并接入（动作模块新增 dr_token_set_target_tile；TurnHooks.token_target/token_start）。
- T030-N4a：新模块 stats 恢复 Game::UpdateStats，补上 ProcessAttack 输入（攻击几率/削弱/全体伤害）与回复量的生产者。
- T030-N4b：DestroyUpgrade 与 GetStatUpgrade/Downgrade 恢复（stats 模块，经 TurnHooks.ability(28) 接线）。EndOfTurn 可触发的逻辑全部恢复，只剩 SerialiseState。
- T040-A/B：调度调用登记（T040_PROCESS_CALLS.json）；新模块 schedule 恢复 ProcessInput 门槛（dr_input_gate：阻塞条件、开始敌人攻击、阶段 8 调用 EndOfTurn）与 CountAttackers。回合循环结构见 T040_SCHEDULE.md。
- T040-C：schedule 模块恢复松手后的 MatchPath 分支（音效/帮助、计数清零后 MatchTiles、成就 74、火焰/spike/吸血标签起飞、AddRevengeHealth、种族 6 护甲升级、击杀攻击回血）、短路径与公共尾段（dr_release_path / dr_release_clear）。职业卷轴分支、Item::IncreaseStat、UpdateCrossVisibility 等列为 T040-C2。
- T040-C2a：stats 模块恢复 Item::IncreaseStat（dr_item_increase_stat），松手的种族 6 升级事件接此函数。
- T040-M（盘点）：从 iOS 层调用的入口出发列出原版尚未恢复的函数。一局之内已全部恢复；一局之外待补 7 项——主菜单的三种开局（普通 / 教程 / 挑战）、开机初始状态（职业名单）、开局设置（名字、职业、模式、难度）、职业编辑、游戏中菜单、帮助提示队列、局后流程（T040-M1..M7，约 3～4 天）。纯显示、文字内容、平台功能、旧版兼容归前端或不做。详见 T040_BACKEND_INVENTORY.md。
- T040-K6：伤害数字标签（SimpleLabel）按原版恢复为新模块 recovered_labels（字形、数字、顶点、上升与淡出）。会话持有吸血、火焰、尖刺三个标签，商店抽卷轴时读到的吸血标签数据与原版一致，K5 留下的已知差异消除；标签位置（松手时伤害数字飞向生命条的起点）也改由会话提供。详见 T040_MENU.md 怪行为一节。
- T030-N5：存档 / 读档按原版恢复——每回合结束自动存档（与原版逐字节相同）、“继续游戏”从存档接着打（整局对照逐帧一致）、职业进度与最高分的存取。详见 T030_SAVE.md。
- T040-G3：无界面整局演示 session_demo——原生规则核心不靠原版程序、不靠测试工具，自己连续打完三整局（升级、商店、装备升级、技能都会出现）；`sh recovered/run_session_demo.sh` 可直接运行。
- T040-L1：法力药水给哪个技能充能的规则（原版藏在界面函数 Interface::GetSpecialTarget 里，会抽随机数）恢复为 dr_special_target，会话自己计算，不再由界面层回答。
- T040-K5：装备与三种菜单接入整局会话：新局按原版造出 5 件装备、属性随装备更新；28 号敌人“摧毁装备升级”与种族 6 的击杀奖励不再是缺口；经验 / 金币 / 升级点满 100（及技能 Upgrade）时打开升级 / 商店 / 装备升级菜单，选择后生效（K5b）；连线时不能接上的格子变暗（UpdateDimming，C3）。当时的已知差异（商店卷轴读到的吸血标签顶点暂取 0）已由 T040-K6 补上。
- T040-K3b/K4：商店（换装备、卷轴）与装备升级菜单恢复，与原版逐帧一致；三种菜单的规则都已恢复，剩会话接线（K5）。
- T040-K3a：物品（装备）生成规则恢复：新物品与商店里基于现有物品生成的新物品（名字、属性升降）。
- T040-K1/K2：升级菜单完整恢复——4 个选项的生成、点选与确认、关闭后技能 / 属性生效，与原版逐帧一致；商店、装备升级与会话接线是 K3..K5。
- T040-H6：技能接入整局会话（按技能按钮、39 种技能的效果、火焰吐息），与原版逐帧一致；技能系统完成（Upgrade 的升级菜单待物品模型）。按住技能按钮时棋盘输入暂停，这一点原先会话没有，测试发现后已改正。
- T040-J3：Game::Start 的抽取到不了游戏（每局重设种子），无需代码。
- T040-J2：恢复 UpdateCrossVisibility（路径上“会被打死”的十字标记及其标签抽取），会话在路径变化与松手时调用。
- T040-J1：恢复粒子与标签的流 0 随机抽取，会话所有相关事件接上。
- T040-H5：恢复技能按钮规则（按下 / 松开 / 冷却重置）、FireBreath 与动作分派；技能系统的规则部分完整，剩会话接线（H6）。
- T040-H4：恢复最后 10 个技能相关函数（四个收集技能与 CollectBoard、CheckShockAwe、变剑列、Teleport、Earthquake、KillSkullsNextToCoins、CreateChain）；技能用到的棋盘函数全部恢复。
- T040-H3：恢复第二批 6 个棋盘技能（Demote / Promote / Kill 特殊敌人、GrabTiles、ShatterDefence、ExplodeArmour）。
- T040-H2：恢复第一批 7 个棋盘技能（Upgrade、FreezeSkulls、ConvertTiles、Create* 四个）。
- T040-I：发现并恢复 Game::AddFlare 的游戏状态（流 0 随机抽取与闪光数），会话中所有闪光事件接上。
- T040-H1：新模块 skills 恢复 Skill::Activate / CanActivate / Game::RemoveSkill（技能分派、标志类技能、符文启用；棋盘技能函数为边界）。
- T040-G2b：会话接上 G0 / G1、资源与遭遇单元内的 CheckEndGame 和 ShieldShatter，测试中原版执行这些原函数（13375 帧一致）。
- T040-G2a：新模块 session（recovered_session）：一个 C++ 会话持有一局的全部状态并自行接线各单元，从新局与携带中局状态逐帧与原版一致（verify_session，11909 帧），含游戏结束。
- T040-G1：恢复 Game::ProcessPretzels（dr_process_pretzels，路径打结奖励等级与预览总数）。
- T040-G0：补齐 Tile::SetSpecialType、Game::Shapeshift、Game::Healing（原先为匹配/资源单元的适配器回调）。
- T040-F4：从新局开始（InitNewGame / dr_init_new_game）逐帧对局 60 回合与原版一致（verify_new_game_play）。
- T040-F3：原版真实 Game::Process 与原生 dr_process_frame（全部单元接线）逐帧一致地跑多回合直到游戏结束（verify_game_frames）。
- T040-F2：完整回合（玩家笔画与松手消除、补位、奖励、敌人攻击、EndOfTurn）携带状态逐帧与原版一致（verify_full_turn，32 回合）。
- T040-F1：回合循环敌人半段的携带状态整合测试（verify_turn_loop），与原版逐帧一致；记录了原生会话必须统一的共享状态。
- T040-C3a：schedule 模块组合 ProcessInput 整函数（dr_process_input），与原版整函数差分通过。
- T040-D3：schedule 模块恢复 Game::Process 整帧调度（dr_process_frame，各已验证步骤经 GameFrameHooks 接线）。
- T040-D2b：schedule 模块恢复 Process 回合计数清零、攻击闪光淡出（结束闪光使输入门槛放行）、当前伤害标签与帮助 8 取消笔画。
- T040-D2a：schedule 模块恢复 Process 棋盘效果段（首局帮助随机、盾牌碎裂进度、Tile::ProcessEffects 毒效果）与 InialiseShieldShatter；0xbf88 归 ShieldShatterState。
- T040-D1：schedule 模块恢复 Game::Process 伤害标签段（dr_process_damage_labels：吸血/火焰/尖刺标签显示与飞行，到达时回血或扣血并 CheckEndGame）。
- T040-E：schedule 模块恢复 Game::InitNewGame 整函数与 CalculateTilePositions（dr_init_new_game：种子、坐标、职业成就、全部状态清零、晋升计时、逐行生成棋盘、起始属性）；物品构造与 UpdateStats 为事件边界。
- T040-C2b：schedule 模块恢复职业卷轴分支（dr_release_class_scroll：升级当前职业或解锁随机未解锁职业、UnlockMenu、MatchTile 7、MoveMatchedTiles、CheckEndGame、存档边界）。

## 验证

2026-10-17 Codex 全套隔离构建通过：19 模块 macOS 双架构库与 iPhone ARM64 静态库、两个无界面源码示例、20 个既有 verify 脚本全部通过。2026-10-18 Claude 默认验证重新执行构建、两个示例及四组验证，通过 522 补位棋盘、3164 生成场景、1992 特殊动作场景，以及 20 个连续手势/1550 步联合链条，没有重跑另 16 个脚本。同日 T010 复核重跑登记检查、独立字节核对及损坏副本拒绝检查；两轮游戏验证的输入指纹与当时源码一致，T010 复核没有重复运行游戏测试。详细历史命令、边界和日志路径见 VALIDATION.md 与 T010_REVIEW.md。

2026-10-18 T020-A 实跑 `./scripts/relay.sh verify --full`：20 模块 macOS 双架构/iPhone ARM64 构建、两个示例、21 个 verify 脚本共 24 步通过。新分支 1510 组场景加 100 连续步骤一致，严格阈值错误副本被拒绝；4 项接力安全测试通过。运行目录 `.relay/runs/20261018T072018.132343Z`，新输入指纹及详细结果见 T020_VALIDATION.json；不再把旧输入指纹当当前验证。

## 本轮修改与继承修改

整理前没有 Git，全部现有文件视为继承成果，已原样建立源码基线；没有清理、stash 或覆盖。新增 AGENTS.md / CLAUDE.md / GEMINI.md、README、docs/、scripts/ 与接力安全测试，单独原子提交；以 `git log` 查看设施提交。忽略的本地材料不在提交内。当前无待转交的继承源码修改；完成后释放 T001 活动锁。

2026-10-18 Claude 接手时工作树干净（HEAD 557cf44），无继承未提交修改。本轮只新增 scripts/t010_registry.py、docs/T010_REGISTRY.json 并更新 docs/ 四个文档，单独提交；recovered/ 源码与原始材料未改动。验证路径见 VALIDATION.md 末节。

2026-10-18 Codex 从干净的 8d9604a 接手复核，仅修正登记/文档中 UpdateCountdown 的 UI 分类、整文件哈希及运行日期描述，并记录复核结论。原有 7282 文件重新逐项核对无内容变化；recovered/ 不改动。完成后 handoff 释放 T010 写入权。

2026-10-18 Codex 从干净的 7652bea 认领 T020，新增护甲损耗源码/测试、调用登记与用户操作说明，扩展 build.sh 和 verify.py；没有继承未提交修改。旧的 19 个模块源码未改动，原有文件仅 build.sh 因增加模块而有必要修改，原程序/素材/证据及其他原文件保持。完成一个可验证单元后提交并保存交接断点，完整 T020 仍保留为未完成。

2026-10-18 Claude 从干净的 1b1ad9f（Codex 已 handoff、无活动锁）认领 T020-B：在 recovered_attack_shield.cpp/.hpp 追加吸收函数（T020-A 原函数未改），新增 verify_attack_absorb.py，默认 verify 列表加入该脚本，调用登记脚本加 additional_recovered_partials；build.sh 未改。

2026-10-18 Claude 继续认领 T020-C（起始 929526b，工作树干净）：attack_shield 模块追加扣血函数，新增 verify_attack_health.py，默认 verify 与调用登记各加一项；build.sh 未改。

2026-10-18 Claude 继续认领 T020-D（起始 496d9aa）：encounters 模块追加两函数并在事件枚举末尾加 Text；build.sh 仅给 encounters 加 rules 依赖；attack_shield.hpp 只改注释；新增 verify_vampires.py。

2026-10-18 Claude 继续认领 T020-E（起始 77307b3）：只新增 verify_attack_vampires.py 并加入默认 verify，无源码改动。

2026-10-18 Claude 继续认领 T020-F（起始 98a112a）：attack_shield 模块追加削弱函数（头文件新增 include recovered_path.hpp），新增 verify_attack_weaken.py，默认 verify 与调用登记各加一项。

2026-10-19 Claude 从干净的 43a2c7f（无活动锁，Codex 尚未接手）继续认领 T020-G：attack_shield 模块追加淡出函数，新增 verify_attack_fade.py，默认 verify 与调用登记各加一项。

2026-10-19 Claude 继续认领 T020-H（起始 4fa6eba）：attack_shield 模块追加 InitialiseFlares 与阶段 1，build.sh 给 attack_shield 加 combat 依赖，新增 verify_attack_flares.py，调用登记更正分类。

2026-10-19 Claude 继续认领 T020-I（起始 536b68a）：attack_shield 追加全体伤害函数；recovered_path.* 新增集成适配器 dr_path_attack_skull；新增 verify_attack_all.py；修正 verify_motion.py 一行（位置覆盖取当前格子中心）。

2026-10-19 Claude 继续认领 T020-J（起始 72bf218）：attack_shield 追加 DoCounterattack，新增 verify_counterattack.py，verify_attack_all.py 测试类参数化（结果不变）。

2026-10-19 Claude 继续认领 T020-K（起始 3b0ce5f）：attack_shield 追加 AttackAnimation 与阶段 2..4 共享部分，新增 verify_attack_flare_phases.py。

2026-10-19 Claude 继续认领 T020-L（起始 b9d8ec3）：attack_shield 追加阶段 4 与 AttackAnimation 运动参数，flares 函数改返回 bool，新增 verify_attack_phase4.py，verify_attack_flare_phases.py 段尾改为可覆盖。

2026-10-19 Claude 继续认领 T020-M（起始 6b049e7）：attack_shield 追加标签运动，新增 verify_attack_label_motion.py，verify_attack_all.py 增加可选多停止点。

2026-10-19 Claude 继续认领 T020-N（起始 b7c08b0）：attack_shield 追加阶段 5 完成准备块，新增 verify_attack_phase5_done.py。

2026-10-19 Claude 继续认领 T020-O（起始 d7a24e3）：attack_shield 追加 dr_process_attack 编排与输入/钩子汇总结构，新增 verify_process_attack.py。

2026-10-19 Claude 认领 T030（起始 ad116bd）：T030-A 新增 scripts/t030_eot_audit.py 与登记；T030-B 新增 recovered_turn.* 模块（build.sh 加入）与 verify_turn_small.py。

2026-10-20～21 Claude 继续 T040-K（起始 ab10ae3，继承 K5a 未提交修改为本人前一会话所做）：提交 2a2c86d（K5 / C3：装备、三种菜单、变暗接入会话）、24f7993（L1：法力药水充能规则）、df0214b（G3：无界面整局演示）及其后的文档提交（T050_GODOT_PLAN.md）；每个代码提交前 verify --full 通过（见 VALIDATION.md）。交接时无未提交修改。

2026-10-21 Claude 认领 T030-N5（起始 0b9186b，用户决定先做存档）：提交 d32c7f9（存档 / 读档 / 继续 / 职业进度 / 最高分）及其后的保护与演示补充；每个代码提交前 verify --full 通过。

2026-10-21 Claude 继续 T040-K6（起始 a82c57c，继承的未提交修改是本人前一会话的 DECISIONS / 用户沟通记录条目与 recovered_labels 初稿）：新模块 recovered_labels、verify_labels，会话接入三个伤害标签；verify --full 通过（`.relay/runs/20261021T161657.995942Z`）后提交。

活动任务与未提交现场实时以 `./scripts/relay.sh check`、`git diff` 和 `.relay/active/owner.json` 为准；文档中的提交号只作里程碑，不用手工维护“永远等于 HEAD”的循环字段。

## 尚未完成及下一步

ProcessAttack（T020）、EndOfTurn（T030，含 CheckEndGame、全部敌人能力、UpdateStats）、回合调度（T040：ProcessInput 门槛/松手/卷轴、InitNewGame、Game::Process 各段与整帧调度 dr_process_frame）已有原生恢复并经原版差分，并已由原生会话库 recovered_session（T040-G2a）接成整局、从新局起与原版逐帧一致；技能系统（T040-H）、物品模型（T040-K3a）、升级 / 商店 / 装备升级菜单（T040-K）也已恢复并接入会话（K5）；存档（SerialiseState）仍为边界，主菜单、选职业等画面属前端，因此仍不能声称完整可玩；现代 iOS UI、高清、多语言和教程未验收。现有 IPA/宿主为兼容路线，不能当作新源码游戏。

T020 已完成（待复核）。T030 进行中：已完成 T030-A..N4b：CheckEndGame 完整恢复；Game::EndOfTurn 整函数已组合恢复并与原版整函数差分通过；ActivateAbility 的 20 个能力全部恢复（DestroyUpgrade 经 TurnHooks.ability(28) 接 dr_destroy_upgrade）；新 stats 模块恢复 UpdateStats。剩余边界只有 SerialiseState（存档格式，0x91c4，896 字节，另需 Tile/Item/Skill/HelpMenu/CharacterClass 的 Serialise 与更完整的物品模型）。存档（T030-N5）按用户指示暂缓。T040 进行中：A/B/C/C2a/C2b 已完成（门槛、松手 MatchPath、职业卷轴与尾段、IncreaseStat）；剩余 ProcessInput 边界见 T040-C3；T040-E（InitNewGame）与 T040-D1（Process 伤害标签段）已完成；Process 整帧调度（T040-D3）、ProcessInput 整函数（C3a）与回合敌人半段整合（F1）已完成；整帧与新局整合（F3、F4）已完成；G0/G1（小函数、ProcessPretzels）与 G2a（原生会话库 recovered_session + verify_session）已完成；G2b（会话接上 G0/G1 等）已完成。产品方向与前端选型（2026-10-20 用户确认，见 DECISIONS.md、用户沟通记录.md）：全平台、iOS 优先；先完善原版（高清、多语言、教程）且玩法原汁原味；新内容最后；界面用 Godot。其后用户决定先完成后端：T040-H 技能系统（H1..H6）、物品模型与 FoldoutMenu（T040-K1..K5）现已完成。下一步 T040-M1..M7（一局之外的规则，见 T040_BACKEND_INVENTORY.md），之后 T050-A Godot 试玩原型（计划见 T050_GODOT_PLAN.md；本机尚未安装 Godot，需用户安装，工具不自动安装）；存档（T030-N5）与 T040-K6 已于 2026-10-21 完成。沿用 T020 的段差分方法与全链测试类。建议下一位工具先复核 T020-B..O 与 T030-A..N4b。额度耗尽后由用户停止当前工具，再用同一目录让下一 AI 接手。简明操作见 用户操作.md。
