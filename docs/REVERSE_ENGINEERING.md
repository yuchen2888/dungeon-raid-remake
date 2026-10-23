# 逆向证据登记

本文件区分磁盘事实、历史报告和本轮验证。初始文件哈希及 ZIP 差异见 INITIAL_AUDIT.json；新实跑以 VALIDATION.md 和对应 `.relay/runs/` 为准。不要从聊天数字推断完成度。

| 领域 | 静态源码/证据 | 历史报告声称 | 当前边界 |
| --- | --- | --- | --- |
| 基础/输入/职业 | combat/rules/input/progression/selection；原有 provenance 与原结果 fixture | 原函数和重放多组通过 | 职业 fixture 是旧输入；非完整 UI 或局面存档 |
| 随机 | random，原 RNG 地址/字节及 random_provenance.json | 5 个函数、6 流逐步对照 | 原始溢出域、启动取种等以原测试边界为限 |
| 输入/围合 | stroke/preview/rune | 629 手势、1192 预览、594 符文等，集合互有重叠 | 输入门槛预先满足，不能相加为独立游戏覆盖 |
| 消除/奖励/路径 | match/tokens/resources/motion/path | 517 路径、26 联合手势、973 步、412 奖励 | 特殊目标/表现、完整主循环仍是接口 |
| 补位 | refill；PositionTile/MoveMatchedTiles/Tile::Process/SwapTiles 及 Game::Process 下落片段，见 T010 登记 | 522 棋盘、108 定位、2705 下落步 | 独立测试对生成/Stab 用确定性回调；SwapTiles 直接差分在 verify_encounters（1296 swap） |
| 生成 | generation；11 个原函数，地址/字节哈希见下节 T010 登记 | 3164 场景 | 独立于 46 流程登记，不累加为完成度 |
| 特殊动作 | encounters；Stab/JumpDown（SwapTiles 源码在 refill），见 T010 登记 | 1992 场景（1296 swap/36 jump/360 stab/300 move） | 与补位/生成接通，非完整敌人 ProcessAttack；CheckEndGame 被测试强制返回 0 |
| 连续链条 | verify_refill_integration.py、rewards_demo.cpp | 20 手势、1550 步、280 奖励/新格 | 明确没有重开输入或完整回合 |

未核实的聊天说法不能升级为已完成项。本轮已实际复现表中各组现有验证，包括 522、3164、1992 和联合链条，详情见 VALIDATION.md；表中历史数字仍保留其原范围，不与其他组累加。职业档案以原 fixture 重放通过，未重新采集原版档案。旧 generation_failure.json 等失败现场虽与后续 passed 报告并存，也原样保留，不据文件名推断历史失败的修复原因。

原 `reverse-engineering/inventory.json` 的 46 流程只覆盖较早阶段；当前 19 模块不意味着 19 个原函数，也没有恢复百分比。较早 README/REVERSE-ENGINEERING-STATUS 的“16 模块、补位未恢复”已经落后于磁盘。

待恢复：ProcessAttack 0x14118、EndOfTurn 0x13574、ProcessInput 0x16638 门槛、InitNewGame 0x15c50、Game::Process 的完整阶段转换、Healing/CheckEndGame 及存档系统。首先查原指令和现有模块接口，再写差分复现，不用等概率随机或空敌人回调拼成假完整循环。

新增条目必须记录：原符号/地址/字节哈希 → 源码函数与文件 → 状态字段 → 明确回调 → 原版执行或 fixture 重放 → 场景与边界 → 本轮验证来源哈希/退出码。未经逐个核对不要补猜地址或函数数量。

## T010：补位 / 生成 / 特殊动作登记（Claude，2026-10-18）

机器可读真源 `docs/T010_REGISTRY.json`，由 `scripts/t010_registry.py` 从原可执行文件中的 ARMv7 切片和 armv7-disassembly.txt 只读提取；整份可执行文件的 SHA-256 为 `5ab6e004…9356`（与 inventory.json 一致，不是单独切片哈希）。`python3 -I scripts/t010_registry.py --check` 重新提取登记内容并与已存 JSON 比较，`problems` 必须为空。字节长度取反汇编符号起点到最后一条指令（含文字池），17 个均与下一符号相接。

计数：17 个完整原函数 + 1 个 Game::Process 片段，与 46 流程旧清单地址/原生函数零重叠；这是独立清单，不并入 46，也不换算完成度。

| 模块 | 原函数 | 地址 | 字节 | 原生函数 | 直接差分 |
| --- | --- | --- | --- | --- | --- |
| refill | Game::PositionTile | 0xb3c8 | 204 | dr_position_tile | verify_refill |
| refill | Game::MoveMatchedTiles | 0x10ed8 | 664 | dr_move_matched_tiles | verify_refill |
| refill | Tile::Process | 0x3d1d0 | 76 | dr_process_falling_tile | verify_refill |
| refill | Game::SwapTiles | 0xb494 | 304 | dr_swap_tiles | verify_encounters |
| refill（片段） | Game::Process 下落列表 | 0x173c8 | 56 | dr_process_falling_list | verify_refill_integration |
| generation | Tile::GenerateStats | 0x3e740 | 2084 | dr_generate_stats | verify_generation |
| generation | Tile::SetType | 0x3f32c | 272 | dr_set_tile_type | verify_generation |
| generation | Tile::Promote | 0x3f260 | 204 | dr_promote_tile | verify_generation |
| generation | Game::RandomiseTile | 0xf5b8 | 516 | dr_randomise_tile | verify_generation |
| generation | Tile::MakeArrow / MakeManaPotion / MakeBroken | 0x3d870 / 0x3d814 / 0x3d714 | 44 / 92 / 72 | dr_make_arrow / dr_make_mana_potion / dr_make_broken | verify_generation |
| generation | Tile::UpdateValues | 0x3db9c | 96 | dr_update_generated_values | verify_generation |
| generation | Game::IsTimeToPromote / SetTimeToPromotion / GetTotalXP | 0xcbc4 / 0x90d8 / 0x189fc | 168 / 60 / 48 | dr_time_to_promote / dr_set_time_to_promotion / dr_generation_total_xp | verify_generation |
| encounters | Game::Stab | 0x10e24 | 180 | dr_stab | verify_encounters |
| encounters | Game::JumpDown | 0xb5c4 | 132 | dr_jump_down | verify_encounters |

状态字段（原偏移均在对应 verify 脚本中有字面量，脚本逐条断言）：GenerationState 的 time_to_promotion +0x14af0、generated_count/enemies +0x165c0/+0x165c4、promotion_enabled/one_health/force_coins +0x14af4..6、inhibit_force_coins +0x15563、filter +0xbfb8/9；GeneratedTile 的 Tile+0x22c/+0xb0/+0xb4/+0x224；补位的 resting_position 表 Game+0xb400、移动列表 Game+0xb3f8、608 字节 Tile 交换；特殊动作的 health +0xbd98、ui_health +0x5994、shake +0xbd90/4。

回调边界：目标名以 `__Z` 开头的直接 C++ 调用（bl/blx/b.w）逐个分类为 T010 内、46 流程内、hook 事件或原生内联，未建模 0 个。提取器不统计数值地址的平台 stub 或间接调用，不能据此声称所有调用均已恢复。
- 需由调用方接回已恢复逻辑的 hook：Refill.Randomise→dr_randomise_tile、Refill.Stab→dr_stab、Generation.JumpDown→dr_jump_down（rewards_demo / 联合测试已接）。
- 原生内联替代：CharacterClass::HavePerk、Game::GetSpecialEnemyCount、std::set<Tile*>（索引序布尔数组，因 Tile 连续存放与指针序一致）、std::list::push_back（AppendMoving）。
- 未恢复且影响玩法：**Game::CheckEndGame**（Stab 后调用，测试强制返回 0，死亡/结束路径未验证）。**Tile::UpdateCountdown** 属未恢复的 UI：读取 Tile+0x250 的已有数值，用 sprintf / Label::SetText 更新倒计时文字并调整 Label 位置，没有推进或写回玩法倒计时；事件目前仅记录。其余为渲染/音频/UI/成就。

边界：静态调用不是 CFG，也不证明分支已执行；没有 ProcessAttack 0x14118 / EndOfTurn 0x13574 / 完整 Game::Process。报告计数为历史文件与前次完整运行 `20261018T065100.380122Z`（洛杉矶时间 2026-10-17）对照一致；2026-10-18 默认 verify `20261018T070600.453747Z` 再次实跑四组通过，输入指纹相同。Codex 复核已独立逐字节对照全部 17 函数及 1 片段，见 T010_REVIEW.md。

## T020-A：攻击护甲损耗片段（Codex，2026-10-18）

已登记 ProcessAttack 0x14118 的 55 个直接调用点、32 个目标（含平台 stub，间接调用不在此表）。新增 `recovered_attack_shield.cpp/.hpp` 只覆盖 `[0x147e4,0x1487e)` 的 154 字节子段：指定敌人 29 / 真实 RNG 流 5 的护甲损耗、UI 同步和有序表现事件。1510 场景及 100 连续步骤与真实原指令一致，错误阈值副本被拒绝；本轮全套 21 个 verify 与构建/示例通过。

原地址、字节哈希、共享字段、调用者提供的 R10 输入及未恢复边界见 T020_ATTACK.md / T020_ATTACK_CALLS.json。它不是完整 ProcessAttack，不新增完整函数数量，也未接完整敌人回合；DoCounterattack、ProcessVampires、前置伤害/阶段与后续生命扣减仍待恢复。

## T020-B：攻击护甲吸收片段（Claude，2026-10-18）

`[0x14790,0x147e4)` → `dr_process_attack_armour_absorb`（recovered_attack_shield.cpp）。读 Game+0xbe84 来袭伤害与护甲，算出 R10＝min(伤害,护甲) 交给 T020-A，写回剩余伤害，全吸收时置阶段 Game+0xb8a8＝7 并结算 Game+0x1553c 标签。原版差分 verify_attack_absorb.py 同时比较单段和连续 `[0x14790,0x1487e)`。字段来源、测试数和边界见 T020_ATTACK.md 的 T020-B 节；登记在 T020_ATTACK_CALLS.json 的 additional_recovered_partials。仍是局部片段，不计入完整函数数。

## T020-C：阶段 6 扣血片段（Claude，2026-10-18）

`[0x14a14,0x14ae4)` → `dr_process_attack_health_damage`。剩余伤害扣生命（负数归 0）、毒取 max(9 号敌人伤害, 现毒)、阶段置 7。Game::ProcessVampires 0xdaf8 未恢复，作为有序回调保留（已核对只写吸血敌人格生命）。verify_attack_health.py 含单段差分和吸收→扣血连续回合。细节见 T020_ATTACK.md 的 T020-C 节。局部片段，不计入完整函数数。

## T020-D：ProcessVampires 0xdaf8 / Tile::AddHealth 0x3dc6c（Claude，2026-10-18）

两个完整原函数 → `dr_process_vampires` / `dr_tile_add_health`（recovered_encounters.cpp）。吸血鬼（敌人 20）按攻击力回血，平时封顶于 max_health，玩家宿敌为吸血鬼时走 AddHealth 不封顶并抬高上限；遍历为列优先。verify_vampires.py 原版完整执行，1100 次比较。这是 T020 期间新增的两个完整函数，单独计数，不并入 46 流程或 T010；ProcessAttack 调用登记里 ProcessVampires 的分类已改为 T020-D。

## T020-E / T020-F（Claude，2026-10-18）

T020-E：verify_attack_vampires.py 让扣血段中的 ProcessVampires 在原版侧真实执行，原生侧事件调用 dr_process_vampires，共享同一状态，无源码改动。T020-F：`[0x1487e,0x14938)`＋循环块 `[0x14b56,0x14b5e)`、`[0x14b9c,0x14bbe)` → `dr_process_attack_weaken`，按 Game+0xbe6c 削弱未出手敌人攻击（最低 1）。细节见 T020_ATTACK.md。均为局部片段，不计入完整函数数。

## T020-G：阶段 7 遮罩淡出（Claude，2026-10-19）

`[0x14ae4,0x14b56)` → `dr_process_attack_fade`。遮罩 Quad 顶点 0 的 alpha（Game+0xb92b）兼作计时器，每帧加 dt×(−900) 并向零截断，<0 时置阶段 8。常量为 0xc4610000（−900）；初版误读为 −160，被差分测试发现。原版 Quad::SetAlpha 在测试中真实执行。细节见 T020_ATTACK.md。

## T020-H：InitialiseFlares 0xd9b0 与阶段 1（Claude，2026-10-19）

完整原函数 InitialiseFlares → `dr_initialise_flares`：行优先累加可出手敌人的攻击，得到来袭伤害与 9 号敌人伤害，并为它们加眼睛光效。阶段 1 `[0x14126,0x141c6)` → `dr_process_attack_fade_in`：alpha 每帧 +dt×800，>200 时进入阶段 2 并调用 InitialiseFlares。原调用登记把 InitialiseFlares 误归为表现边界，已更正。AddFlare 维护的光效列表/计数仍是调用方边界。细节见 T020_ATTACK.md。

## T020-I：全体伤害（Claude，2026-10-19）

`[0x14938,0x14a14)`＋块 `[0x14b5e,0x14b9c)`、`[0x14bbe,0x14be0)` → `dr_process_attack_damage_all`。AttackSkull 经新增集成适配器 `dr_path_attack_skull`（不计入恢复函数），MoveMatchedTiles 经 `dr_move_matched_tiles`，在共享状态上与原版全链差分。测试框架 `verify_motion.py` 的代币位置覆盖原取用例初始中心，已改为当前中心，以对应原版的 `&tile->center`。细节见 T020_ATTACK.md。

## T020-J：DoCounterattack 0x11214（Claude，2026-10-19）

完整原函数 → `dr_do_counterattack`：每个未出手的敌人用自己的 GetAttack 对自己 AttackSkull（列优先），标签显示在静止位置表 Game+0xb400，随后 MoveMatchedTiles 并清 attack_flag。verify_counterattack.py 在完整共享状态上全链差分。ProcessAttack 的直接玩法调用已全部有恢复实现；剩余工作是阶段 2..4 及阶段 5/6 动画片段本身和整体调度。

## T020-K：阶段 2..4 共享部分（Claude，2026-10-19）

`[0x141c6,0x143ca)` → `dr_process_attack_flares`。Game+0xbd90 / +0xbd94（MatchState 的 shake 字段）在攻击中是两个计时器：A 每帧加 dt，B 每帧减 4.5dt。B<0.5 时阶段 2 转 3（反击标志 Game+0xbfba）或 4（伤害/毒标签）；B<0 时光效数清零。阶段 3 进度满 1 且光效结束时置阶段 7 并调用 DoCounterattack。新增 AttackAnimation 结构承载 Game+0xbd58/+0xbd54/+0xbd38/+0x15520/+0xbd8c/+0xbfba。细节见 T020_ATTACK.md。

## T020-L：阶段 4（Claude，2026-10-19）

`[0x143ca,0x1457c)` → `dr_process_attack_phase4`。标签进度满 1 且本帧光效刚结束（原版栈标志 [sp,#0x2c]，现由 dr_process_attack_flares 返回）时，按护甲 Game+0xbda4>0 进入阶段 5，否则进入阶段 6，并写入运动参数，调用 Rand(float) 流 0 和 HelpMenu。细节见 T020_ATTACK.md。

## T020-M：阶段 5/6 标签运动（Claude，2026-10-19）

`[0x1457c,0x146ce)` → `dr_process_attack_label_motion`：带加速度的进度、弧线轨迹（阶段 5 横向、阶段 6 纵向）、powf(t,5) 控制的 alpha。Interpolate 标量版为 a·t+(1−t)·b，二维版为 (1−t)·a+t·b，两者方向相反。平台 powf 是边界，测试两侧都用本机 C 库 powf。细节见 T020_ATTACK.md。

## T020-N：阶段 5 完成准备块（Claude，2026-10-19）

`[0x146ce,0x14790)` → `dr_process_attack_phase5_done`：阶段 6 完成则转扣血；阶段 5 完成则置阶段 6，写入下一段运动参数，调用 Rand(0.4,0.8,流 0)，显示 −min(伤害,护甲) 标签与帮助菜单，同一帧接护甲吸收。ProcessAttack 全部指令段至此都有恢复实现。细节见 T020_ATTACK.md。

## T020-O：完整 ProcessAttack（Claude，2026-10-19）

`dr_process_attack` 按原控制流组合 T020-A..N。verify_process_attack.py 每帧从原版入口 0x14118 调用整函数，与原生在完整共享状态上逐帧比较：48 次完整攻击（阶段 1→8）、1985 帧，所有玩法被调函数均为原函数。测试替身只有平台 powf 与 AddFlare 的追加计数模型（两侧一致）。ProcessAttack 每帧逻辑的恢复至此完成（待复核）；阶段 8 后的调度、EndOfTurn、输入重开属于 T030/T040。

## T040-I：AddFlare 不是纯表现（Claude，2026-10-20，更正）

此前各测试把 Game::AddFlare 0x9f94 当作表现边界（T020-O 只模拟"追加并计数"）。实际 0xa0c8..0xa0d0 调用 Rand(0.0, 360.0, 流 0)（闪光旋转，写 quad+0x6c），0xa0fa..0xa0fe 计数 Game+0xbd8c + 1。流 0 与棋盘生成共用，所以每个闪光都改变后续随机结果；计数阻塞输入直到淡出。原生 dr_add_flare 与 verify_add_flare.py 见 T040_SCHEDULE.md T040-I；会话已在全部闪光事件上调用。各单元测试仍按原样跳过 AddFlare（两侧一致），整局对照由 verify_session 覆盖。

## T040-J：表现层代码的流 0 随机抽取（Claude，2026-10-20，发现与计划）

继 AddFlare（T040-I）之后又发现三处表现代码抽取流 0：
- Game::AddParticles 0xa914 → Particles::InitialiseFromTile(Tile*, type)：类型 0 走 InitialiseFromTile(Tile*)，类型 1/2/3 走 InitialiseAtPosition（防御 / 生命 / 攻击标签位置）。原版实测（40 个随机棋盘、随机格子）每次调用的 Rand 次数固定：类型 0 为 33 次，类型 1–3 为 81 次；随机数只影响粒子外观，但推进流 0。调用方：AttackSkull（2）、ProcessAttack（1）、ShatterDefence（2）、EndOfTurn（2）、MatchTile（1）。
- SimpleLabel::Initialise 0x23078：标签类型 1、8、9、10 速度固定 0.1，类型 3 固定 0.08，其余类型 Rand(0.1, 0.2, 流 0) 一次。调用方：Game::AddSimpleLabel 两个重载（32 处调用）、UpdateCrossVisibility、Game::Start、Game::Process（伤害标签类型 8/9/10 与当前伤害标签类型 1，不抽取）。
- Game::UpdateCrossVisibility 0xaa24（路径每次变化与松手时调用）：按路径格子的 Tile::GetDamageType 重建十字标签（类型 30、35 等），每个标签抽取一次。T040-J2 已恢复（dr_update_cross_visibility）：标签取自 Game+0x164c8 的标签池，位置为池首 + 游标 Game+0x164d4 × 0x358（SimpleLabel 大小），游标在池满时回绕；池与游标属表现层，会话不建模。
流 0 也被游戏规则使用（职业卷轴出现倒计数 RandI(20,30,0)、代币飞行速度、攻击标签运动），所以这些抽取改变后续游戏结果。各单元测试的原版宿主一直跳过这些函数（两侧一致）。计划：J1 AddParticles 与 AddSimpleLabel 的抽取模型并在会话所有相关事件上接上；J2 UpdateCrossVisibility 与 Tile::GetDamageType；J3 Game::Start 随开局流程。
T040-H6：ProcessInput 门槛的输入目标 Game+0x58ac 即 Interface+0xbd0（Interface 在 Game+0x4cdc），就是按下的技能槽；Interface::Process 0x20c64 在 FoldoutMenu（Interface+0xd18 = Game+0x59f4）、GameMenu（+0xe30 = 0x5b0c）、StatsMenu（+0xec0 = 0x5b9c）都未打开且第二参数（输入就绪 Game+0x5e14）为真时调用 Interface::ProcessInput，其后的 Heartbeat、Tooltip、按钮动画属表现层。
T040-K（商店卷轴）：FoldoutMenu::Initialise(1) 0x25526 的卷轴候选循环在 Rand ≥ 0.1 时读 *(Game+0xbf90+4t)（t = 0..39）判断是否排除该技能，越出 4 个技能指针，读到 skill_count、matched_counts、0xbfb8.. 字节与吸血标签 SimpleLabel（Game+0xbfc0）的类型与顶点数据；详见 T040_MENU.md；会话（K5b）中 t = 13..39 曾暂取 0，T040-K6 已用 SimpleLabel 模型补全。
T040-K6（SimpleLabel，recovered_labels）：对象 0x358 字节——+0 激活、+4 类型、+8 起 32 个顶点（每个 20 字节：x、y 为像素 / 320，RGBA，u、v 为像素 / 1024）、+0x288 八个字形的贴图矩形、+0x308 各字形缩放、+0x328 字形数、+0x334 位置、+0x33c 缩放、+0x340 数字大小（类型 3、4、5、7、8、9、10、26、27、29 为 0.5）、+0x344 上升速度、+0x348 / +0x34c 计时与持续时间、+0x350 数字、+0x354 淡出基准透明度。数字的十个字形表由静态初始化函数 0x313c 填入（0x1eac64 / 0x1eacb4）；数字从万位起、不写前导零，负数先加减号字形（并把首字形下移一个字形高）；类型 5 与 10 在数字大于 1 时换用复数字形 {425,143,465,156}；类型 8 末尾另加一个字形。100000 及以上的数字在原版会读出数字表之外（越界），本作把该位限为 9，记为边界（伤害标签不会出现这么大的数）。Game::Start 0xb880 给吸血 / 火焰 / 尖刺标签设颜色 17 / 18 / 19、当前伤害标签颜色 10，持续时间都写 0.2（0x3e4ccccd）。Game::Process 伤害标签段除 SimpleLabel 调用外还直接写两处标签字段：缩放 +0x33c（0x17874 / 0x17a76 / 0x17c7a）与吸血标签淡出基准 Game+0xc314（0x177a0，紧跟 SetAlpha(0xff / 0x80)）。松手 MatchPath 的标签起飞点（Game+0xc2f4 / 0x14e30 / 0x151a4）就是三个标签的位置字段，因此标签位置属于规则状态。
T040-J3 结论（无需代码）：Game::Start 0xb880 只有一个调用点 _main 0x8216（App 启动时一次），它先 SetRandSeed(time, 6) 再做两次标签初始化抽取。每局都经 InitNewGame 0x15c50 开始（StartTutorial / StartChallenge / NewGame / ContinueGame / NameScreen::ProcessInput 五个调用点），InitNewGame 在 0x15c98 调 SetRandSeed(time(), 6)——类型 6 把六路种子全部设为同一值（SetRandSeed 0x1b6c0：r1==6 时写满 6 个字），随后 FlushRandSeeds 把每路种子乘 16807。所以 Game::Start 的抽取到不了任何一局；读档时 DeserialiseState1 / DeserialiseState2 各用 5 次 SetRandSeed 恢复存档里的种子（存档任务需核对第 6 路）。

T040-M1 / M2（详见 T040_BACKEND_INVENTORY.md）：主菜单的 Game::NewGame / StartTutorial / StartChallenge 都是先写记录模式字节 Game+0x14aed（只有挑战为 1）、调用 InitNewGame，再打开开局设置画面（NameScreen::Show，挑战时第二个参数为真）。教程另把难度 Game+0x14ae0 写成 0（在 InitNewGame 之后）、帮助开关 Game+0x13ec8 打开并 HelpMenu::ResetHelp（HelpMenu+0x38 即 Game+0x102d0 的第 0..22 位置上，其余位保留）；普通与挑战关闭帮助并 ClearHelp（清零）。Game::UpdateHelpState（游戏菜单）：待显示的帮助不为空且帮助关闭时清空，为空且帮助打开时 ResetHelp。CharacterClass::Initialise 0x111e20：职业 0 为 1 级，其余 0 级（锁住）；种族 = 基础种族 = {0,1,6,4,5,9,3,8,2,7}[类型]；第一个天赋与缺陷 = {255,6,2,5,4,1,7,8,9,3}[类型]，其余 255；基础技能 20 个（+0x30）、其余 20 个技能按序（+0x3c）、替换技能 20 个 255（+0x48）；类型 10 以上没有基础技能。Game::SetCurrentClass：所选职业等级为 0 时当前职业改为 0。

T040-M3（开局设置）：NameScreen 在 Game+0x102dc。Show(名字, 挑战) 写挑战标志 +0x3bbc、打开 +0x292d（即 Game+0x12c09），名字为空时编辑框放 “Enter name” 且 +0x294c（已输入）= 0，否则 strncpy 16 个字符且 +0x294c = 1。ProcessInput 只在触摸由 0 变 1 时响应（+0x2960 存上一帧阶段）；键盘隐藏时依次检查名字框、随机名字、职业编辑、模式说明、返回、模式 / 难度、职业、开始。随机名字 GenerateRandomName：RandI(0,1,流 0) 为 0 时 “%s%s”（前半 50 个之一 + 后半 49 个之一），否则 “%s%s %s%s”；两张字表各 5 字节一项（0x18da29 / 0x18d934），最长 17 个字符（写进编辑框不越界，SetName 只存 16 个）。挑战局只有两个模式按钮（SetMode 0 / 1），其他局只有四个难度按钮；职业按钮只对已解锁（等级不为 0）的职业有效。开始按钮在 y > 1.33、x 在 0.25..0.75 之间，且只有在 NameScreen::Process 把它淡入到 255 之后才响应——Process 只在键盘隐藏、已输入名字且长度大于 0 时淡入。开始：SetName(编辑框) → IntroScreen::Initialise（Game+0xc330，打开 +0xc0；它的流 0 抽取在 InitNewGame 重新播种之前，不影响本局）→ InitNewGame → 关闭设置画面。IntroScreen::Process：淡入后在同一位置按下 “继续”，淡出结束时关闭并 SerialiseState（新局一开始就有存档）。Game::SetMode / SetDifficulty / SetScorePage 都是“夹到范围、与旧值不同则置已改变标志（0x14aec / 0x14ae4 / 0x16610）”；SetName 用 strcmp 判断已改变（Game+0xbe49）后 strncpy 16 个字符。原版各单元直接读当前职业记录（Game+0x1648c 指向的那条），所以换当前职业后种族、天赋、缺陷立即按新职业生效。UpdateName 按字体宽度截短名字，与字体有关，归前端。

T040-M4（职业编辑，ClassScreen 在 Game+0x12c78 = NameScreen+0x299c）：CanChooseRace = 非职业 0 且等级 ≥ 5；CharacterClass::IsPerkUnlocked(格) = 格 0 等级 ≥ 1、格 1 > 2、格 2 > 6、格 3 > 8；GetReplacementSkillsAllowed = 等级 ≤1 为 0、≤3 为 2、≤5 为 4、≤7 为 6、10 为 10、其余（8、9）为 8；SetPerk / SetFlaw 只对格 1..3、格已开放、且职业没有这个天赋（缺陷）时写入（HavePerk / HaveFlaw 对 255 返回否，所以写 255 = 取下）；SetReplacementSkill 只对格 1..19：已有替换的格可直接换，空格只在已替换数小于允许数时放入。Game::IsRaceUnlocked：第一个以该种族为基础种族的职业决定（职业 0 总是，其余等级 ≥ 5），没有就锁住；Game::IsPerkUnlocked：天赋 0 总是解锁，否则第一个以它为第一天赋的职业决定（该职业已解锁）。ClassScreen::UpdatePerks：天赋 / 缺陷 i 可拖 = 天赋 i 已解锁且当前职业不是职业 0 且格 1 已开放，再去掉已放进格子的；UpdateAbilities：其余技能 i 可拖 = 技能已解锁、允许替换数 > 0、不是职业 0、还没被用作替换。拖放：种族图标在 IsRaceUnlocked 且 CanChooseRace 时可拿起，放到种族格后直接写记录的种族（+8）；“完成”按钮 = Validate、SetCurrentClass(记录的类型)、SerialiseClasses；切换分页也 SerialiseClasses。
T040-M5（游戏中菜单与统计菜单）：Interface 在 Game+0x4cdc，GameMenu 在 Interface+0xe24（Game+0x5b00），StatsMenu 在 Interface+0xeb4（Game+0x5b90），两者字段相同：+0xc 打开（FrameScreens.menus[1] / [2]）、+0x10 上一帧触摸阶段、+0x14 按下的按钮（统计菜单为当前分页）、+0x18 正在关闭、+0x1c 计时（0.2 秒）。Interface::Process 0x20c64 依次：FoldoutMenu 打开 → 它的 Process；否则游戏菜单打开 → GameMenu::Process；否则统计菜单打开 → StatsMenu::Process；否则有输入时 Interface::ProcessInput；随后（FoldoutMenu 关着时）ProcessHeartbeat。两个菜单的 Process 都先走计时：计时 > 0 时减去 dt，减完不大于 0 则置 0，若正在关闭就关掉菜单，这一帧不收输入。GameMenu::Process 0x32580：阶段 1 且上一帧阶段 0 时，按顺序找 9..15 号按钮里被按住的那个（CursorInQuad），记下并响声音 0；阶段 2 或 3 且有按下的按钮时，若触摸仍在该按钮上：9 = 计时 0.2、正在关闭、Game::UpdateHelpState；10..14 = Game::SetSoundState / SetHelpState / SetClockState / SetAttackDimmingState / SetHighFramerate（参数是原字节异或 1；声音打开后再响声音 0）；15 = MainMenu::FadeIn（MainMenu+4 打开即 Game+0xc400、+0xc 淡入、+8 = 0.5）；无论是否生效都清掉按下的按钮；最后记下本帧阶段。退出到主菜单时游戏菜单本身不关闭，留到下一局 InitNewGame 的 Interface::Reset。Game 的设置字节：0x13ec6 声音（已改变 0x13ec7）、0x13ec8 帮助（无已改变标志）、0x13ec9 时钟（0x13ecc）、0x13eca 攻击变暗（0x13ecd，只有 Game::Render 读）、0x13ecb 高帧率（0x13ece，平台读）；各 Set 函数把“已改变”写成“新旧值是否不同”（覆盖而不是累加）。Game::QueueSound 在声音关闭时不入队。Game::UpdateHelpState 0x9edc：待显示的帮助（Game+0x102d0）不为 0 时，若帮助关闭则 ClearHelp；为 0 且帮助打开则 ResetHelp（置上 0..22 位）。StatsMenu::Process 0x33c0c：阶段 1 且上一帧阶段 0 时，若触摸在菜单外（CursorOutsideMenu）则响声音 0、计时 0.2、正在关闭，并直接返回（不记本帧阶段）；否则 10..15 号分页按钮中被按住且不是当前分页的，换成当前分页并响声音 0（分页内容、标签、菜单高度都是显示）。Interface::ProcessInput 0x209e4：阶段 1 且上一帧阶段 0 时，先看技能按钮（0..3，按钮号小于技能数的才算），都没有时看菜单按钮 Interface+0xbd4（+0xcb4 = 1，响声音 0）和统计按钮 +0xc44（+0xcb5 = 1）；阶段 2 或 3 时先处理技能按钮的松开，再在 +0xcb4 / +0xcb5 置位时打开游戏菜单 / 统计菜单并清标志——松开的位置不限，取消（阶段 3）也会打开。GameMenu::Show / StatsMenu::Show：按下 = -1、上一帧阶段 = 0、不在关闭、计时 0.2、打开（统计菜单回到首页）。Interface::Reset 0x204a4 的状态部分：+0xbd0（按下的技能按钮，Game+0x58ac）= -1，+0xcb4 / +0xcb5 = 0，两个菜单关闭；其余是心跳计时、颜色和数值阴影（显示）。
T040-M6（帮助提示）：HelpMenu 在 Game+0x10298：+0xc 打开（Game+0x102a4，即 FrameScreens.help_102a4）、+0xd 正在关闭、+0x10 计时、+0x14..+0x20 提示框（Show 按文字排版算出，显示）、+0x24 上一帧触摸阶段、+0x38 待显示的帮助位（Game+0x102d0）、+0x3c std::list<HelpItem>（屏幕说明的队列：文字、x、y、大小）。HelpMenu::Initialise(x, y, 宽, 高, 类型) 0x380b8：已打开则什么都不做；类型位不在待显示里也不做；否则清掉该位，全部清空时先 Game::SetHelpState(false)（帮助开关关掉），再 Show(第 类型 条文字, x, y, 宽, 高)。HelpMenu::Show 0x37f04：计时 0.2、不在关闭、打开、上一帧阶段 = 1（所以要先松手再按才算）、排版（显示）。HelpMenu::QueueHelp(文字, x, y, 大小) 0x38268：未打开时立即 Show(文字, x, y, 大小, 大小)，否则排到队尾。HelpMenu::Process 0x38128（Game::Process 的帮助路线：先把阶段 2/3 变 0，再调用；此时游戏其余部分都不跑）：计时 > 0 时减 dt，不大于 0 时置 0，若正在关闭则关掉，并在队列非空时 Show 队首、弹出队首；计时用完后，阶段 1 且上一帧阶段 0 且触摸在提示框内时开始关闭（计时 0.2）；最后记下阶段。23 种帮助的来源：Game::AddToken（代币 0..3 → 帮助 3、6、2、5，格子位置，0.0828 见方）、Game::MatchTile（22：0.0828 见方；1：宽 0.04）、Game::EndOfTurn（15 / 21：每列第一个符合的格子，0.0828 见方）、Game::ProcessAttack（16：攻击标签位置，0 x 0；17：同位置，高 0.1）、Game::ProcessInput 松手（4：路径第一格，0.0828 见方）、Game::Process（0：每帧随机一格的静止位置，帮助位 0 在时每帧抽两次随机数；8：伤害数字位置，宽 0.05）、Interface::ShowHelpBaseDmg 9 / WeaponDmg 10 / Armour 11 / UP 12 / XP 13 / Gold 7 / Health 18（固定位置：(0.33125, 1.265625)、(0.640625, 1.265625)、(0.496875, 1.265625)、(0.5, 1.390625)、(0.5, 1.446875)、(0.140625, 1.296875)、(0.8578125, 1.26875)，0 x 0）、Interface::UpdateSkills（每个技能：冷却满或为 0 时，未激活 19 / 激活 20，指向该技能按钮，0.0953125 见方；凡是刷新技能按钮的地方都会调用：变形、拿资源、回合结束、装备技能、UpdateStats、读档、按技能按钮）、Interface::ProcessHeartbeat（14：显示血量 / 显示上限 ≤ 0.35，位置同 18；Interface::Process 在没有 FoldoutMenu 打开时每帧调用，三种开局和继续游戏末尾的 Interface::Process(0, false) 也会调用）。屏幕说明：开局设置画面的“?”按钮（NameScreen+0x868，按下即响声音 0 并排 5 条：0x155f9c、0x156008、0x1560d8、0x156184、0x1561d4）；职业编辑画面的“?”按钮（ClassScreen+0x2b0，按下记 +0xa7d、在按钮上松开时按当前分页 +0x9d0 排：分页 0 五条 0x16e298..0x16e510、分页 1 四条 0x16e5b0..0x16e760、分页 2 四条 0x16e808..0x16e97c、分页 3 五条 0x16ea3c..0x16ec84）。会话里屏幕说明编号为 100..122（文字本身属于原版资源，只在本地取，不进 Git）。
T040-M7（局后流程与主菜单）：MainMenu 在 Game+0xc3fc：+4 打开（Game+0xc400）、+8 淡入淡出计时、+0xc 淡入（否则淡出：计时变负时关闭主菜单）、+0x80 标题图的透明度（+0x8f；开机 255，每秒减 500，不为 0 时不收输入）、+0x4e0 按下的按钮（-1 无）、+0x4e4 有存档（Game+0x146d0 > 0，显示“继续”）、+0x4e5 有最高分（ScoreScreen::GetScoreCount > 0）、+0x4e6 奖励按钮显示（平台）、+0x6a8 “覆盖存档？”确认框、+0x6ac 它要开的局（0 新局 / 1 挑战 / 2 教程）、+0x6b0 选了“是”、+0x6b1 正在关闭、+0x6b4 它的 0.3 秒计时、+0x6b8 上一帧阶段。MainMenu::Process 0x2e668：先更新两个“有”标志；计时 > 0 时只走淡入淡出；确认框打开时计时减 dt，变负则置 0，若正在关闭则关掉确认框并在选“是”时开对应的局，计时恰为 0 时才收输入（阶段 1 且上一帧 0：是 / 否按钮，响声音 0、开始 0.3 秒关闭）；标题图透明度不为 0 时按 -500 / 秒递减（截断为整数、不低于 0）；否则阶段 1 且上一帧 0：“更多游戏”（+0xf0，声音 10，Game::ShowMoreGames）、奖励按钮显示时的第 8 个按钮（+0x470 与按钮 7 是同一块，声音 10，ShowBonusRequest）、按钮 0..7（没有存档时跳过 0，没有最高分时跳过 4；声音 0、记下按下）；阶段 0（触摸已结束）且有按下的按钮时，若触摸仍在该按钮上：0 Game::ContinueGame，1..3 有存档则打开确认框（0.3 秒）否则 Game::NewGame / StartChallenge / StartTutorial，4 Game::ShowScores（ScoreScreen::Show(Game+0x1660c 页, false) 与主菜单关闭），5 声音开关（打开时响声音 0），6 Game+0x15545 = 1（平台随后调用 OpenFeint 的 launchDashboard），然后清掉按下；最后记下阶段。Game::ContinueGame 在读档后调用 MainMenu::FadeOut（0.3 秒淡出）与 Interface::Process(0, false)。GameOverScreen 在 Game+0xcac0：+4 打开（Game+0xcac4）、+0x158 是否获胜、+0x15c 状态（Game+0xcc1c）、+0x160 当前行、+0x164 进度、+0x168 等待、+0x16c / +0x170 计数值与增长率、+0x174..+0x184 已显示的图标数（职业 5 个、技能、天赋、缺陷、棋盘上剩余的敌人）、+0x188 图标间隔 0.2、+0x18c / +0x190 / +0x194 天赋 / 缺陷 / 敌人数（InitIcons 0x3013c：当前职业记录的天赋与缺陷不为 255 的个数，Game::GetEnemyCount 0..32 之和）、+0x24a4 上一帧阶段。Process 0x30c28：状态大于 1 时“阶段 1 且上一帧 0”的点击把等待清零并（状态 3 以外）把进度置 1；等待大于 0 时减 dt，减到不大于 0 且状态 2 时响声音 27 并换行（12 之后是 21），仍大于 0 则返回。状态 0：进度每秒 +0.5，满 1 进入状态 1 并等待 1 秒；状态 1：进度每秒 +1，满 1 进入状态 2（行 -1，等待 0.5，计数值与增长率 1，图标间隔 0.2，InitIcons）；状态 2 的各行：0..2 只等待；3 回合数、4 等级、5 总经验、6 总金币、7 总升级点（记录模式且模式 1 时为穿越平均 / 最佳 / 次数，Game+0x16604 / 0x16608 / 0x16600）、12 分数，增长率每秒 +0.1，计数值乘以增长率，达到目标或进度为 1 时取目标并响声音 10，否则整数部分变化时响声音 2，达到后进入下一行（进度 0、计数值与增长率 1、等待 0.5）；8 职业图标 5 个、9 技能数、10 天赋、11 缺陷、21 敌人，每 0.2 秒加一个并响声音 2（敌人 14），进度为 1 时直接满；21 完成后 Game::ShowNagScreen、状态 3、等待 10 秒；状态 3：进度每秒 +0.5，满 1 关闭画面。Game::Process 在游戏结束画面状态 3 时每帧调用 ScoreScreen::Show(挑战局的模式页或难度页, true)。ScoreScreen 在 Game+0xef68：+4 打开（Game+0xef6c）、+5 正在关闭、+8 0.3 秒淡入淡出、+0x15c 上一帧阶段、+0x160 拖动中、+0x164 / +0x168 上一帧与起点的 x、+0x16c 拖动速度、+0x170 页面位移、+0x178 正在滑动、+0x17c 方向（1 前一页 / -1 后一页 / 0 回原位）、+0x1cc / +0x1cd / +0x1ce 按下的返回 / 左 / 右、+0x1d0 页 0..5。Show(bool) 0x36720：SetScorePage、清各标志、上一帧阶段 = 1、打开，参数为假时淡入 0.3 秒。Process 0x367f8：计时走完时若正在关闭则关闭；滑动中：位移 = Interpolate(方向, 位移, 0.3)（即 方向×0.3 + 0.7×位移），与方向相差小于 0.00625 时到位并换页（钳到 0..5）、SetScorePage；阶段 1 且上一帧 0：在页面行区内则开始拖动（速度 0，起点 = 上一帧 = 触摸 x），再看返回 / 左（页 > 0）/ 右（页 ≤ 4），按下并响声音 0；上一帧 1 且阶段 0：拖动结束时开始滑动，方向由速度（±0.1）或位移（±0.5）与页数决定；返回松开在按钮上：关闭（0.3 秒）、MainMenu::Show、SetActive(true)；左右松开在按钮上：向前 / 向后滑；其余拖动中的帧：位移 = x - 起点（第 0 页右拖、第 5 页左拖时重置起点），速度 = Interpolate((x - 上一帧 x) / dt, 速度, 0.4)。Interpolate(a, b, t) = a×t + (1 - t)×b。Game::SetScorePage 0x83a4：钳到 0..5（Game+0x1660c），已改变标志 Game+0x16610。

T040-M7d（开局设置画面的淡入淡出与“返回”）：NameScreen（Game+0x102dc）+0x2930 淡入淡出计时（NameScreen::Show 设 0.3、+0x2934 正在关闭清 0）、+0x292d 打开（Game+0x12c09）、+0x292c 屏幕键盘显示、+0x2960 上一帧触摸阶段、+0x295c 按下按钮的高亮编号（显示用）。NameScreen::Process 0x3cac0：职业画面（+0x3408）或模式画面（+0x36f8）打开时转给它们；计时 > 0 时减 dt，变负时置 0、正在关闭则关画面（恰好减到 0 不关，下一帧照常收输入），本帧不调用 ProcessInput；否则调用 NameScreen::ProcessInput 及显示更新。ProcessInput 只在触摸开始（阶段 1、上一帧 0）时判断按钮；“返回”（+0x154 的按钮）仅在键盘隐藏时有效：音效 0、正在关闭 = 1、计时 0.3、MainMenu::Show、MainMenu::SetActive(true)（主菜单上一帧阶段 = 1）。原生 dr_session_setup_back；所有 dr_session_setup_* 在淡入淡出期间及淡出结束的那一帧不生效（会话记下“上一帧在淡入淡出”）。键盘显示与否归前端，前端在键盘打开时不应提供“返回”。

T030-N5（存档，详见 T030_SAVE.md）：Game::SerialiseState 在中毒与 time_to_promotion 之间跳过一个字节（保留缓冲上一次的内容，读档也跳过）；冰冻且燃烧的格子存了火焰伤害字节而读档不读（先冰冻清除燃烧），其后错位——正常对局两者互斥，不会出现；xp / up / gold 存“当前 + 累计”，读回按 100 拆分；Item::Serialise 在非零属性多于 7 个时触发成就 72；读档时记录模式 mode 被夹到 0..1、难度夹到 0..3；Game::SerialiseClasses 的 CharacterClass::Validate 会改动当前职业（5 级以下恢复基础种族等），对局中途（职业卷轴升级）也会发生。DeserialiseState1（无 0xff 标志的最老存档格式）未恢复，本作不需要。最高分（ScoreScreen::AddScore）：已有 10 条都不低于新分数时，新分数仍顶掉第 10 名（最新一局总会进榜）；DeserialiseLegacyState（更早的分数格式）未恢复。
