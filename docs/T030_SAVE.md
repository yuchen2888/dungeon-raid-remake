# T030-N5 存档 / 读档 / 继续游戏（Claude，2026-10-21）

状态：对局存档、读档、继续游戏、职业进度与最高分的存取完成（N5a..N5d，待复核）。用户 2026-10-21 决定先做存档、Godot 往后（DECISIONS.md）。

## 原版怎么存

- 对局存档：Game::SerialiseState 0x91c4 把整局写进 Game 内的缓冲 Game+0x13ecf（0x800 字节），长度 Game+0x146d0，Game+0x146d4 置 1 表示“有变化”。调用处：每回合结束且游戏未结束（EndOfTurn 收尾）、ProcessInput 的尾段（职业卷轴等）、IntroScreen::Process。
- 写盘由外层（Objective-C）负责：每帧检查“有变化”标志，长度为 0 则删除、否则把缓冲作为 NSData 存进系统设置（NSUserDefaults）；启动时把存的数据（≤ 0x800 字节）拷回缓冲并恢复长度。游戏结束时 CheckEndGame 把长度置 0、标志置 1（删除存档）。
- 主菜单：长度不为 0 才显示“继续”（MainMenu::Show / Process）。Game::ContinueGame 0x165f4：Game::InitNewGame → Game::DeserialiseState → Game::CalculateTilePositions（之后主菜单淡出、Interface::Process(0, false) 为表现）。
- 职业进度：Game::SerialiseClasses 0x8ee8 写 Game+0x146d5（0、10、每个职业 47 字节，共 472），长度 Game+0x14ad8，变化标志 Game+0x14adc；调用处：游戏结束、职业卷轴升级、选职业界面。Game::Start 时 Game::DeserialiseClasses 0x8ea0 读回（第二字节为 10 才读）。
- 外层另把“职业卷轴倒计时”Game+0x15558 在 Game+0x15555 置位时单独存（MatchState.spawn_remaining_15558 / spawn_dirty_15555，由平台层处理）。

## 格式（版本 3）

0xff、3；记录模式（mode，非记录模式 0xff）；total、crossing_samples（各 4 字节）、crossing_average、crossing_best（各 1 字节）；当前职业序号；该职业 CharacterClass::SerialiseGameState（种族、特长 / 缺陷 1..3、替换技能 1..19，共 26 字节）；spawn_count_1555c；36 格的类型两格一字节（高 4 位在前）；每格 Tile::Serialise；turn、kill_count_165b4；奖励几率 Game+0xbe18 / be20 / be28 / be30、中毒、（一个不写的字节）、time_to_promotion；base_bde8[4]、base_damage、shield_value、healing_value、health_max、health、xp + total_xp、up + total_up、gold + total_gold、armour_current；五件装备 Item::Serialise；技能数与每个技能（类型、冷却上限、当前、等级）；玩家名（到结尾 0，最多 17 字节）；随机流 1..5（流 0 不存）；帮助标志；难度。

- Tile::Serialise：种类字节（药水：爆炸 1、法力 2、酸 3；剑：魔法 1、破损 2、箭 3；盾：破损 1；卷轴：特殊类型；其他类型无）；冰冻 1 / 燃烧 2（燃烧时再加火焰伤害一字节）；骷髅另有攻击、防御、生命、生命上限（各 4 字节）、敌人类型、状态、flag_25d、中毒值（到第一个 0，最多 3 个）。
- Item::Serialise：图标在本类型区间内的序号（区间起点 0 / 80 / 240 / 160 / 320 对应类型 0..4）、名字前缀等级、前缀、名字、非零属性的位掩码及其值；非零属性多于 7 个时顺带触发成就 72。
- 读档时 DeserialiseState 按版本：版本 > 2 才有记录模式与 total / crossing（记录模式 mode 被夹到 0..1）；版本 > 1 才有职业与 kill_count；版本 0（无标志）盾牌没有种类字节。xp / up / gold 按“和 % 100”拆回当前值，其余为累计，等级 = 累计 xp / 100 + 1。读档先对每格 Tile::SetType（回合 0、当前难度；此前把 time_to_promotion 置 1，使骷髅走生成而非晋升），再逐格恢复；装备读完后护甲、护甲上限、生命加成清零做 Game::UpdateStats，再放回生命与护甲；界面值随之更新；最后设随机流 1..5、帮助开关（帮助标志非 0）与难度（夹到 0..3，变化时置 Game+0x14ae4）。

## 原版怪行为（记入 REVERSE_ENGINEERING.md）

- 存档跳过一个字节（中毒与 time_to_promotion 之间），该位置保留缓冲里上一次的内容；读档也跳过它。
- 冰冻且燃烧的格子：存档写了火焰伤害字节，读档却先冰冻（清除燃烧）而不读它，后面全部错位。正常对局中冰冻与燃烧互相清除，不会同时出现。
- 存 “xp + 累计 xp”、读回时按 100 拆分：依赖“当前值 < 100、累计为 100 的倍数”。
- DeserialiseState1（无 0xff 标志的最老格式）未恢复：只可能来自很早期版本的原版存档，本作不需要；读档时返回 false、不读。
- 原生的两处保护（原版没有）：读档时职业序号大于 9（损坏的存档）即停止并返回 false；存档时技能数按最多 4 个处理。正常存档里不会出现这两种值。

## 原生实现

新模块 `recovered_save`：`dr_serialise_state`、`dr_deserialise_state`（SaveSources 指向各字段的唯一所有者；读档复用 dr_set_tile_type、dr_make_mana_potion / broken / arrow、dr_set_special_type、dr_set_flame_visibility、dr_update_generated_values、dr_class_read_game 与会话的 UpdateStats），`dr_serialise_classes` / `dr_deserialise_classes`（dr_classes_write / read）。原版的职业记录就是单位读取的数据；原生的单位读 SelectionState.character（种族、缺陷）、MatchState.perks 与 class_type / class_level 这些“视图”，所以存档时职业记录取视图的值，读档与职业存取后视图跟随记录（SerialiseFullState 的 Validate 可能改动当前职业，例如 5 级以下恢复基础种族，视图同步改变）。

会话：SessionObjects 增加 save（0x800 字节缓冲；长度与变化标志即 EndGameState.flag_146d0 / flag_146d4）、name（玩家名，渲染层写入）、settings（帮助开关、难度变化标志）、class_save；回合结束与 ProcessInput 尾段的 SerialiseState 事件 → dr_serialise_state，游戏结束与职业卷轴的 SerialiseClasses 事件 → dr_serialise_classes；接口 `dr_session_save`、`dr_session_deserialise`、`dr_session_continue_game(time)`（InitNewGame、DeserialiseState、CalculateTilePositions）、`dr_session_restore_save`、`dr_session_restore_classes`（启动时平台把存的字节交回，后者含 Game::Start 的 DeserialiseClasses）。平台层（将来的 Godot）：变化标志置位时把对应字节写盘并清标志，启动时交回。

## N5d：最高分（ScoreScreen）

原版 ScoreScreen（Game+0xef68）有 6 类最高分表（ScoreType：难度 0..3，游戏模式 0..1 记为 4、5），每类最多 10 条；一条 56 字节：玩家名、回合、三个值（按难度：经验、金币、升级点；按模式：该模式的三个值）、分数、4 个技能（−1 为无）。

- ScoreScreen::AddScore 0x347c0（另两个重载：GameMode 用类型“模式 + 4”，Difficulty 用类型“难度”）：上一次加分的类别与本类别标记为“已变化”；新分数排在所有“不低于它”的分数之后；若已有 10 条都不低于它，仍放在第 10 位、顶掉原第 10 名（原版怪行为：最新一局总会进榜）；较低的依次后移（最多保留 10 条）；复制名字、写入数值、技能置 −1；条数加 1（最多 10）。
- ScoreScreen::SetSkills 0x34418：写最新一条的 4 个技能（游戏结束时紧跟 AddScore）。
- 存取：SerialiseState(类别) 0x34524 把一类表写进 ScoreScreen+0xf20（条数；最新一条若在本类为其位置否则 0xff；每条回合、三个值、分数各 4 字节，4 个技能各 1 字节，名字到结尾 0 最多 17 字节），记录长度与类别、清该类“已变化”；SerialiseChangedState 写第一个已变化的类别；外层每帧在 HaveScoresChanged 时循环调用它并按类别存盘。启动时 DeserialiseState(类别) 0x34680 读回（条数夹到 0..10；最新位置不是 0xff 时成为最新一条；技能 0xff 为 −1，否则夹到 0..39）。构造函数：没有分数、没有最新一条、无变化（没有默认分数）。DeserialiseLegacyState（更早的旧格式）未恢复，本作不需要。

原生新模块 `recovered_scores`（ScoreBoard 的内存布局与原版 ScoreScreen+0x1e0..0x132e 相同）：dr_score_add / set_skills / count / changed / serialise / serialise_changed / deserialise。会话：游戏结束时的 AddScore 事件（会话里的玩家名）与 SetSkills 事件写入会话的最高分表；接口 `dr_session_restore_scores(类别, 字节)`（启动时）、`dr_session_save_changed_scores()`（返回下一个已变化的类别及其字节，平台存盘后再调用，直到 −1）。玩家名由 Game::SetName 限制在 16 个字符以内。

验证：`recovered/verify_scores.py`：原 ScoreScreen 各函数从入口执行（ClampI 为原代码，strcpy 由宿主模拟），300 组、每组 40 次随机操作（加分、技能、存、取（原样 / 改坏 / 随机字节）、计数与“是否变化”），每步比较原版整块最高分内存（0x114e 字节）逐字节一致；出现满表 201 次。错误副本 15 个全部 exit 1。verify_session：游戏结束时原版 AddScore / SetSkills 作为原代码执行，每帧比较整块最高分内存；会话接线的错误副本 2 个（模式 / 难度的类别对应、技能写入）exit 1（前者在完整测试中由记录模式下结束的对局覆盖）。

## 演示

`sh recovered/run_session_demo.sh`：第一局打到第 40 个操作时“退出”，dr_session_continue_game 从存档继续（经验、金币等原样恢复），接着打到结束。

## 验证

- `recovered/verify_save.py`：原 Game::SerialiseState 从入口执行（Tile / Item / Skill / HelpMenu / CharacterClass 的 Serialise、GetRandSeed 为原代码，QueueAchievement 记录），对 400 个覆盖所有分支的状态（各种格子种类、冰冻 / 燃烧、中毒长度、记录模式、当前职业、最多 20 项属性的装备、0..4 个技能（含无冷却）、各种长度的名字、缓冲原有内容）逐字节一致；成就 72 一致。错误副本 23 个全部 exit 1。
- `recovered/verify_load.py`：用原版存一个状态，把字节读进另一个状态，原 Game::DeserialiseState 从入口执行（SetType 等格子函数、Item::Deserialise2、UpdateStats、Skill::Deserialise、SetRandSeed、SetHelpState、SetDifficulty 为原代码；界面更新、图标、文字跳过），300 组（版本 3 与转换出的版本 0..2）比较整局状态、资源与几率、当前职业记录与视图、名字、帮助开关、难度标志，以及读档过程中的每一次随机抽取与格子颜色 / 贴图 / 文字事件；另把一个状态的职业存档读进另一个状态（原 DeserialiseClasses，含替换技能、等级、进度与“不是 10 个职业”的情形）比较十个职业记录。错误副本 35 个：30 个 exit 1；5 个等价（读档 SetType 用的难度：回合 0 且敌人类型尚未设定时不参与计算；燃烧伤害“加”与“赋值”：此前已清零；flag_25d 取字节与“等于 1”：存档里只有 0、1；UpdateStats 前不清护甲上限：UpdateStats 会重写它；难度不夹到 0..3：存档里只有 0..3）。职业存档另与原版 Game::SerialiseClasses 直接比较（含单位视图已与记录不同——如变形后的种族——的情形，以及 Validate 对当前职业的改动），错误副本 4 个全部 exit 1。
- `recovered/verify_session.py`：原版侧不再跳过 SerialiseState / SerialiseClasses，二者作为原代码执行，每帧比较存档缓冲（长度、标志、字节）与职业存档；新局阶段部分对局打到一半“退出”再继续（原版 InitNewGame + DeserialiseState + CalculateTilePositions，原生 dr_session_continue_game），然后接着打并逐帧比较；游戏结束时原版 ScoreScreen::AddScore / SetSkills 作为原代码执行，每帧比较整块最高分内存。整局 34561 帧一致，其中原版存档 340 次（逐字节一致）、退出再继续 4 次、职业存档 14 次、加分 14 次（按难度 13、按模式 1，残局阶段加了一局低血量的记录模式对局以覆盖后者）。技能阶段按技能时优先按至今用得最少的已装备技能（职业存档的 Validate 改变了后续对局，原先的轮流按法有两种技能没被用到）。
