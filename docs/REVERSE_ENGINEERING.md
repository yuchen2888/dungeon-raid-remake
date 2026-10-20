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
