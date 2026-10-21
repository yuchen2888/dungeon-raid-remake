# T040-K：升级 / 商店 / 装备升级菜单（FoldoutMenu）

状态：K1..K5 完成（Claude，2026-10-20，待复核）；剩一项低优先的已知差异（商店卷轴读到的吸血标签顶点，T040-K6）。本文件记录原版行为与恢复进度，供接手者继续。

## 触发

资源单元（recovered_resources）在经验、金币、升级点满 100 时发出 ResourceEvent Menu：经验 → 0（升级：选技能 / 属性），金币 → 1（商店：换装备），升级点 → 2（装备升级）。原版是 Interface::ShowMenu 0x1eb20，它直接调用 FoldoutMenu::Initialise(MenuType) 0x24a54（FoldoutMenu 在 Interface+0xd10，即 Game+0x59ec）。会话目前只转发这个事件，菜单从不打开。

## FoldoutMenu 字段（相对 FoldoutMenu）

| 偏移 | 含义 |
|---|---|
| +0x8 | 打开（= Game+0x59f4，FrameScreens.menus[0]） |
| +0xc | 菜单类型 0 / 1 / 2 |
| +0x10 / +0x14 | Game* / Interface* |
| +0x18 | 动画位置（表现） |
| +0x20 | 确认按钮可用 |
| +0x21 | 确认按钮已按下 |
| +0x24 | 动画计时（浮点；负数 = 打开中、可操作） |
| +0x28 | 1 打开动画 / 0 关闭动画 |
| +0x2c | 上一帧触摸阶段 |
| +0x30 / +0x34 | 第一 / 第二选择（按钮 14..17，−1 无） |
| +0x38.. | 商店的 3 个物品选项（Item*） |
| +0x48.. | 升级菜单的 4 个选项（Skill*） |
| +0x58.. / +0x68.. | 装备升级：物品与 ItemUpgrade 选项 |
| +0x78 | 升级菜单中技能选项的个数 n |
| +0x10c / +0x110 | 商店里卷轴所在的选项槽（−1 无）与卷轴技能（Skill*） |

## Initialise(type)：选项生成

公共：打开、类型、计时 0、+0x28=1、选择清空、Tooltip::Hide、界面四边形（表现）。记 f = Game+0x14aed（record）且 Game+0x14ae8 == 0（模式 0）。

类型 0（升级，音效 12）：
1. 技能池：已装备 4 个技能时 = 已装备技能的类型；否则 = 当前职业的技能池（CharacterClass::GetSkillPool，职业 = Game+0x15564 + 388 × Game+0x1648c）。
2. 对每个已装备技能：f 为假、等级 ≤ 9 且类型不是 33 → 保留（并记“并非全部已满”）；否则从池中去掉它的类型。f 为真时再去掉 22。
3. 属性池 = {0..6}，再加 7，除非四组 Game+0xbe18/1c、20/24、28/2c、30/34 的和都 > 99。
4. record 且模式 1：池去掉 24、7，属性池去掉 6。
5. 技能选项数 n = min(2, 池大小)；已装备 3 个且全部已满时 n = min(1, 池大小)。写 +0x78。
6. 第 i 个技能选项（i < n）：RandI(0, 池大小−1, 流 3) 取池中第 r 个（升序）；i = 0、Game+0xbe4c == 2、职业+4 ≠ 0 且（f 为假或职业首技能 ≠ 33）时改为职业首技能（职业+0x30 指向的第一个值）。找已装备的同类型技能（最后一个匹配）。i = 0、已装备 3 个且没有同类型技能时：池清空，f 为假则放回所有等级 ≤ 9 且类型 ≠ 33 的已装备技能；否则从池中去掉该类型。选项 = Skill::Initialise(类型, 同类型已装备技能或空)。
7. 其余选项（n..3）：RandI(0, 属性池大小−1, 流 3) 取属性池中第 r 个并去掉，选项 = Skill::Initialise(StatType)。

Skill::Initialise(SkillType, Skill* existing) 0x2b2a0：类型；冷却上限 = existing ? (existing 等级 == 10 ? existing 上限 : existing 上限 − 1) : 基础冷却表[类型]；f 时再 −4；当前冷却 = existing ? min(existing 当前, 上限) : 上限；等级 = existing ? existing 等级 + 1 : 1，f 时为 5，否则不超过 10。图标、名字、文字属表现。基础冷却表（0x1d7e18，与 Skill::GetBaseCooldown 同表）：13, 16, 15, 16, 18, 18, 15, 20, 18, 18, 35, 12, 18, 15, 25, 15, 14, 15, 15, 15, 18, 20, 18, 15, 25, 14, 12, 16, 14, 20, 24, 15, 15, −1, 14, 12, 25, 35, 18, 16。

CharacterClass::GetSkillPool 0x111ad4：职业+4 为 0 时 = 0..39 中 Game::IsSkillUnlocked 的类型；否则 20 项，每项取替换技能（职业+0x48 数组，255 表示无）否则基础技能（职业+0x30 数组）。

类型 1（商店，音效 11）：物品类型池 {0..4}；3 个选项各 RandI(0, 池大小−1, 流 2) 取一个类型并去掉，选项 = Item::Initialise(Game::GetItem(类型))。卷轴：概率 0.25（职业+8 == 3 时 0.5），Rand(0,1,流 2) < 概率时卷轴槽 = RandI(0,2,流 2)，再 Rand(0,1,流 2) = r；候选技能为 0..39 中除 33、（record 且模式 1 时）24 以外，r < 0.1 或该类型已装备……（待续读 0x25512 起），满足 Skill::CanActivate 的加入；RandI(0, 候选数−1, 流 2) 选一个，Skill::Initialise(类型, 空) 存入 +0x110。否则卷轴槽 = −1。

类型 2（装备升级）：待读（0x256f4..0x25a58，ItemUpgrade::Initialise / GetRandomStat 等）。

## ProcessInput 0x239c8：选择与确认

仅在新触摸（Game+0x10 == 1 且上一帧阶段 0）时：确认可用且触摸在确认按钮（四边形 7）上 → 记按下（音效 0）。否则依次检查按钮 14..17（商店只有 14..16），触摸在其上时：
- 再点已选的第一 / 第二选择 → 取消该选择；
- 没有第一选择 → 设为第一选择；
- 已有第一选择：商店 / 装备升级改选；升级菜单若还没有第二选择则设为第二选择，两个都选了则不变。
- 音效：商店 1（卷轴槽显示卷轴提示），升级 9，装备升级 8。
确认可用 = 升级菜单两个选择都有；其他菜单有第一选择。松开（阶段 2）时确认已按下且仍在确认按钮上 → 开始关闭动画（计时 0、+0x28=0，音效按类型 11 / 12 / 13），否则取消按下。

## Process(dt) 0x23c44：动画与生效

计时 < 0 时处理输入。否则计时 += dt，达到阈值后：打开动画结束 → 计时置负（可操作）；关闭动画结束 → 关闭菜单并按类型生效：
- 商店：Game::SetItem(选中物品)（返回的旧物品存回选项）、Game::UpdateStats；卷轴槽 == 选中槽时 Skill::Activate(卷轴技能)，职业+? == 3 时成就 0x31。
- 升级：Game::SetSkill(第一选择)、Game::SetSkill(第二选择)（返回值存回选项）。
- 装备升级：Item::AddUpgrade(物品, 升级)、Game::UpdateStats。

## K1：升级菜单的选项（完成）

新模块 recovered_menu：`dr_menu_open_level`（Initialise 类型 0）、`dr_skill_option`（Skill::Initialise(SkillType, Skill*)）、`dr_stat_option`（Skill::Initialise(StatType) 与 SetStatChance）、`dr_class_skill_pool`（GetSkillPool）、`dr_skill_unlocked`（IsSkillUnlocked）、`dr_skill_base_cooldown` 与职业基础技能表 `dr_class_base_skills`（用原版 CharacterClass::Initialise 实测取出）。SkillRecord 表示一个 Skill 对象的游戏字段（装备中的技能或菜单选项）；选项的 active 字节保留对象原有值（原版的选项对象会与装备中的对象互换、循环使用）。

验证 `recovered/verify_menu_level.py`：原 FoldoutMenu::Initialise(0) 从入口执行（GetSkillPool、IsSkillUnlocked、两个 Skill::Initialise、SetStatChance、RandI 为原代码；std::set<int> 由测试宿主模拟；四边形、标签、文字、提示、SjLj 桩跳过；音效记录），1500 组一致：技能选项 2 个 1364 组、1 个 84 组、0 个 52 组，40 种技能与 8 种属性选项都出现。错误副本 20 个，19 个 exit 1；1 个等价（record 模式 0 时第一次选到新技能后重建候选池去掉“f 为假”条件：此时已装备技能都已从池中去掉、“全部已满”为真，已装备 3 个时只有 1 个技能选项，重建的池不再被使用）。

注意：Game+0xbe1c / be24 / be2c / be34（属性的物品部分）在原生侧有两个镜像——MatchState.bonus_chance_extra（匹配时读取）与 PlayerStats.chance_*（UpdateStats 写入）；会话接入物品属性时需统一为一个所有者。

## K2：升级菜单的选择与生效（完成）

`dr_menu_input`（ProcessInput）、`dr_menu_process`（Process：动画计时与关闭后的生效）、`dr_set_skill`（Game::SetSkill 0x13e68）。MenuSources 增加 preview、selection、player、stat_counts（Game::SetSkill 写入的治疗 / 护盾值、基础伤害、界面生命上限与骷髅值、属性计数 Game+0xbde8..）。菜单按钮由渲染层给出（14..17 选项、7 确认、−1 无）。

Game::SetSkill：技能类型（< 40）时，已装备同类型技能则与选项对象互换（PositionSkill）；否则未满 4 个时与下一槽对象互换、技能数 + 1，冷却物品（Game+0xbe64）时上限 − 1，作为第 4 个技能且有特长 3 时再 − 1（当前值不超过上限）；最后 UpdateSkills。已满 4 个且无同类型：只 UpdateSkills。属性选项（40..47）：治疗、护盾增加；四个加成几率增加且不超过 100；非 record 模式 1 时生命上限与生命增加（上限或生命变化时刷新血条）；基础伤害增加（骷髅值变化时刷新）；属性 0..3 的计数 + 1。

验证 `recovered/verify_menu_flow.py`：先按 K1 打开菜单，再逐帧运行原 FoldoutMenu::Process（ProcessInput、Game::SetSkill、HavePerk 为原代码；CursorInButton / CursorInQuad 按本帧按钮回答；音效、高亮、确认按钮颜色、界面刷新记录；提示跳过）。每组先随机点按（选择、取消、点第三个、未可用时点确认、在别处松开确认），再选两个并确认、播放关闭动画直到生效。600 组、24095 帧逐帧一致（菜单状态与计时位、四个选项、按槽顺序的装备技能、各属性值、事件），新增技能 299 次。错误副本 24 个：23 个 exit 1；1 个（计数条件改为 ≤ 44）会写出 4 元素数组之外，不是有效变体，改用 ≤ 42、≥ 41 两个变体均 exit 1。

## K3a：物品生成（完成）

新模块 recovered_items：`ItemRecord`（Item 对象的游戏字段：类型 +0x80、图标 +0x84、名字前缀等级 / 前缀 +0x88 / +0x8c、名字 +0x90、属性 +0x94 共 20 项），`dr_item_make`（Item(Game*, ItemType) 与 Item::Initialise(Item*) 的规则部分）、`dr_item_initialise`、`dr_item_generate_name`、`dr_item_generate_stats`、`dr_upgrade_allowed`（ItemUpgrade::IsUpgradeAllowed）、`dr_random_item_stat`（ItemUpgrade::GetRandomStat）。图标与名字下标只决定画面与名称，但它们的随机抽取推进流 2。名字表大小用原版 Item::InitialiseNames 实测：前缀 148 个；13 组名字按图标区间 [0,20) 15、[20,40) 12、[40,50) 13、[50,60) 12、[60,80) 15、[80,160) 17、[160,240) 16、[240,320) 17、[320,340) 14、[340,360) 11、[360,370) 14、[370,380) 16、[380,400) 16。图标区间：类型 0 为 0..79，1 为 80..159，2 为 240..319，3 为 160..239，4 为 320..399。

Item::GenerateStats（有原物品时，原物品的正属性按升序逐个处理，Rand 均为流 2）：
- 类型 0：属性 0 = 原值 + 1；其他属性以 0.15 概率下降（降幅 GetStatDowngrade，最低 0）并使属性 0 再 + 1，否则保持。
- 类型 1：属性 11 = 原值 + 1；其他属性以 0.2 概率变化：允许升级、本次尚未升级过且再以 0.5 概率时上升（升幅 GetStatUpgrade），否则下降并使属性 11 + 1。
- 类型 2：先以 0.2 概率属性 11 = 原值 + 2 且其他属性全部保持，否则属性 11 = 原值 + 1，其他属性以 0.1 概率下降并使属性 11 + 1。
- 类型 3：属性 11 = 原值 + 1；属性 0 以 0.7 概率下降（属性 11 + 1）；其他属性以 0.2 概率下降，再以 0.2 概率使属性 0 + 1，否则属性 11 + 1。
- 类型 4：属性 10 = 原值 + GetStatUpgrade(10) / 2；其他属性以 0.1 概率下降并给 GetRandomStat(4) 选出的属性加一次升级；最后 record 模式 1 时必定、否则以 0.5 概率再给一个随机属性加一次升级（属性 5 为 0 时可选 5）。

验证 `recovered/verify_items.py`：先让原版 Item::InitialiseNames 真实建好名字表（std::vector 的存储用测试宿主的分配器），再从入口执行 Item::Initialise(Item*)（商店物品）或新物品的三步（Initialise(ItemType)、GenerateName(0)、GenerateStats(0)），IsUpgradeAllowed、GetRandomStat、GetStatUpgrade / Downgrade、HaveFlaw / HavePerk、RandI / Rand 为原代码，std::set 由宿主模拟，MakeStats 跳过。1500 组一致（5 种物品类型、商店物品 1117 组、新物品 383 组）。错误副本 24 个：20 个 exit 1；4 个等价或本测试不可达：IsUpgradeAllowed 14 的“不超过 100”截断（两种写法在 v > 100 时都为真）、GetRandomStat 类型 1 的属性池（GenerateStats 只用类型 4，K4 装备升级会用到）、类型 4 的 /2 与 >>1（升幅只会是 0 或 10）、属性 5 的 == 0 与 <= 0（新物品属性不会为负）。前缀等级边界变体在补充 135..147 用例后被拒。

## K3b：商店（完成）

`dr_menu_open_shop`（Initialise 类型 1）与 `dr_menu_process` 的商店生效。MenuState 增加商店的 3 个物品、卷轴所在选项（−1 无）与卷轴技能对象；MenuSources 增加装备中的 5 件物品（Game+0xbe88..0xbe98：类型 0..3 各一件，其余一件）、StatsTargets 与 StatsHooks（物品函数与 Game::UpdateStats）、SkillState（Skill::CanActivate）与 probe（Game+0xbf90 起的 40 个字，见下节怪行为）。

打开：音效 11；物品类型池 {0..4}，3 个选项各由 RandI(流 2) 取池中一种类型并去掉，选项物品 = Item::Initialise(Game::GetItem(类型))（K3a 的商店物品）。卷轴：概率 0.25（当前职业种族 3 时 0.5），Rand(流 2) 小于概率时卷轴位于选项 RandI(0,2,流 2)，再 Rand(流 2) = r；候选为 0..39 中除 33（与 record 模式 1 的 24）外、已解锁、Skill::CanActivate 为真、且 r ≥ 0.1 时 probe 字为 0 的类型，RandI(流 2) 选一个，Skill::Initialise(类型, 无)。原版候选为空时会读空向量（崩溃），原生侧不处理该情形（实际对局中 t ≥ 13 的类型通常可选）。

点选：选项 14..16（17 不可用），音效 1，点到卷轴所在选项时显示卷轴提示。确认后关闭：Game::SetItem 0x8b08 把所选物品与同类型装备互换（返回的旧物品存回选项），Game::UpdateStats；卷轴在该选项时 Skill::Activate（未装备的对象，ActivateScroll 事件，会话接 dr_skill_activate，槽 −1），种族 3 时成就 49。

验证 `recovered/verify_menu_shop.py`：原 Initialise(1) 从入口执行（GetItem、Item::Initialise(Item*) 及其生成函数、Rand / RandI、IsSkillUnlocked、Skill::CanActivate(int) 为原代码；std::set<ItemType> 与 std::vector<int> 由宿主模拟；吸血标签内存 Game+0xbfc4.. 写入随机字，原生侧拿到同样的 40 个字），再逐帧运行 Process（SetItem、UpdateStats 为原代码，界面刷新记录）。500 组、20489 帧一致：出现卷轴 210 次、买下卷轴 77 次。错误副本 18 个：17 个 exit 1；1 个等价（卷轴概率比较 < 与 ≤，只在随机数恰好等于 0.25 / 0.5 时不同）。

## K4：装备升级（完成）

`dr_menu_open_upgrade`（Initialise 类型 2）：音效 13；类型池 {0..4}，4 个选项各由 RandI(流 4) 取一种类型并去掉，选项为该类型的装备物品，配一个 ItemUpgrade::Initialise 0x2da74：属性 = GetRandomStat(物品类型, 属性 5 为 0 时允许 5)，幅度 = GetStatUpgrade(属性)。选项 14..17，音效 8。确认后关闭：Item::AddUpgrade 0x29de0 把幅度加到该物品的属性，Game::UpdateStats。

验证 `recovered/verify_menu_upgrade.py`：在商店测试的宿主上执行原 Initialise(2)（ItemUpgrade::Initialise、GetRandomStat、GetStatUpgrade 为原代码，升级文字跳过）与逐帧 Process（Item::AddUpgrade、UpdateStats 为原代码）。500 组、20510 帧一致，20 种属性都出现在升级方案中。错误副本 7 个全部 exit 1。

## K5a：装备与属性接入会话（完成）

会话新增 5 件装备（ItemRecord，Game+0xbe88..0xbe98；原版 Game 构造时把这 5 个槽的地址按 0..4 放进 Item** 向量 Game+0xbe9c，Game::UpdateStats 按此顺序遍历）、StatsTargets 与 StatsHooks。接线：InitNewGame 的 Item(Game, type) 事件 → dr_item_make（新物品），UpdateStats 事件 → dr_update_stats；松手的 IncreaseStat（种族 6、一次连线击杀 > 14）→ dr_item_increase_stat（Game+0xbe90 即槽 2），随后的 UpdateStats；敌人 28 的能力 → dr_destroy_upgrade（原先是边界）；属性事件中的标签施加流 0 抽取。属性的物品部分 Game+0xbe1c / be24 / be2c / be34 在原生侧有两份（PlayerStats.chance_* 由 UpdateStats 写入，MatchState.bonus_chance_extra 在匹配时读取），会话在每次 UpdateStats 后让后者等于前者。SessionObjects 增加 items。

验证：verify_session 每个用例带 5 件装备与 UpdateStats 写入的各字段并加以比较；原版侧 InitNewGame 的 Item 构造（Item::InitialiseNames 事先跑一次）、UpdateStats、IncreaseStat、DestroyUpgrade 都作为原代码执行（界面刷新、物品文字、图标、音效跳过，std::vector<int> 由宿主模拟，DestroyUpgrade 的标签施加流 0 抽取）。新增“装备”阶段 10 局：种族 6 走 15 格以上的血量 1 骷髅路径（IncreaseStat 4 次），或敌人 28 下回合发动能力（DestroyUpgrade 32 次）。四个阶段共 26876 帧一致。错误副本 7 个：新局物品类型、新局 UpdateStats、IncreaseStat 的槽、松手 UpdateStats、DestroyUpgrade、属性标签抽取 6 个 exit 1；两份几率同步的错误副本（对应关系换错）在 K5a 的测试中未被发现（那时对局中装备属性很少变化），K5b 加入商店与装备升级后被拒。

## K5b：菜单接入会话（完成）

会话新增 MenuState、menu_button（渲染层写入的菜单按钮：14..17 选项、7 确认、−1 无，SessionObjects.menu_button）与 probe（商店卷轴读取的 Game+0xbf90 起 40 个字）。接线：ResourceEvent Menu（经验 / 金币 / 升级点满 100）与技能 Upgrade 的 SkillEvent Menu 打开对应菜单（dr_menu_open_level / shop / upgrade）；每帧 InterfaceProcess 时若 FoldoutMenu 打开则 dr_menu_process（本帧 dt、触摸阶段、菜单按钮），否则（GameMenu / StatsMenu 打开时不处理）在输入就绪时处理技能按钮；买下的卷轴（ActivateScroll）→ dr_skill_activate（未装备对象，槽 −1）。商店 / 装备升级结束时的 UpdateStats 之后、卷轴激活之前同步两份几率副本。

probe 的组成：t=0..3 为非零（技能对象指针），4 为 skill_count，5..9 为 matched_counts[0..4]，10 为 Game+0xbfb8..bb 四个字节（filter_enabled、filter_swords、counterattack、coin），11 为 next_coin，12 为吸血标签的激活字节；13..39 落在吸血标签 SimpleLabel 的类型与顶点数据里，原生侧取 0（标签顶点属渲染层，尚无模型）——这与原版在显示过吸血标签之后的行为可能不同，记为已知差异（见下节怪行为）。

测试发现并改正两处：
- FoldoutMenu::Initialise 会把“上一帧触摸阶段”（+0x2c）清零，三个打开函数原先漏了这一步（单元测试里每次都是新菜单，所以没有暴露）。
- 商店的卷轴概率（种族 3 时 0.5）与成就 49 原先读 classes[class_index].race；原版读当前职业记录的种族（Game+0x15564 + 388 × Game+0x1648c + 8），原生各单元读的是 selection.character.race（同一字段的视图，Shapeshift 改的也是它），会话并不维护职业表里的种族。现改为读 selection.character.race，verify_menu_shop 相应把种族写到 selection（仍 500 组、20489 帧一致）。随机职业的整局测试暴露了这一处。

验证：verify_session 的原版侧不再跳过 Interface::ShowMenu：FoldoutMenu::Initialise 作为原代码执行（std::set<int> / std::set<ItemType> / std::vector<int> 由宿主模拟，十个职业的基础技能与替换技能数组写入职业对象，菜单的 Skill / Item / ItemUpgrade 对象指回 Game；界面、文字、提示跳过）；菜单打开时 Interface::Process 改为执行 FoldoutMenu::Process（FoldoutMenu::CursorInButton / CursorInQuad 按本帧菜单按钮回答），其中 Game::SetSkill、SetItem、Item::AddUpgrade、UpdateStats 为原代码，卷轴的 Skill::Activate 按技能按钮那套方式执行。对局中菜单打开后，测试等开场动画结束，随机点按几次，再选择（升级菜单两个）并确认，直到关闭动画结束。比较内容增加菜单状态（类型、选择、确认、计时位、动画方向、上一帧阶段、技能选项数、4 个选项、3 件商店物品、卷轴、4 个升级方案）。技能阶段现在也按技能 10（Upgrade，打开装备升级菜单）；装备与技能阶段的当前职业（Game+0x1648c）从 0..9 随机抽取（菜单的技能池按职业）：原版测试宿主的载入函数把当前职业的数据（种族、特性、缺陷）写在 0 号职业记录，测试把这条记录整条搬到抽中的位置、0 号换成另一个职业，并按当前职业读出 Game::MatchTile 用到的职业类型、等级与种族（原版指令 0xc33c 起按 Game+0x1648c 计算记录地址，确认原版读的是当前职业）。升级方案只在当前菜单是装备升级菜单时比较：商店的 SetItem 会搬动原版残留升级方案所指的物品对象，而 Initialise(2) 会重写全部四个方案，这些残留不会被读到。结果：四个阶段共 32065 帧一致（新局 9 局、残局 15 局、装备 10 局、技能 62 局；菜单打开：升级 62 次、商店 93 次、装备升级 5 次；40 种技能都被实际使用）。为让每种技能都落到不同槽位，技能阶段的槽位顺序每 10 局轮换一次（40 种技能每局 4 个时，否则同一种技能总在同一槽，第 4 槽只有装满时才有）。错误副本 17 个：14 个 exit 1（菜单事件打开菜单、技能 Upgrade 打开菜单、每帧处理的 dt、触摸阶段、卷轴激活、卷轴前同步几率、几率同步的对应关系、probe 的 skill_count / matched_counts / 第 10 / 11 个字、上一帧阶段清零、当前职业序号、商店读种族的位置）；1 个等价（probe 第 10 个字里 counterattack 的移位：只用到是否为 0）；2 个本测试不可达：GameMenu / StatsMenu 打开时不处理技能按钮（测试不打开这两个界面），probe 第 12 个字（吸血标签激活字节，商店打开时这些对局里吸血标签都未显示）。

## C3：UpdateDimming（完成，随 K5b 提交）

`dr_update_dimming`（recovered_selection）：原 Game::UpdateDimming 0x9c78 对每格调用 Tile::CanMatchType(路径, true)，能接上的 Undim、不能的 Dim（只改格子与标签的透明度）。原生结果为 36 格的 dimmed 表；会话在 SelectionEvent::UpdateDimming 时更新它，经 SessionObjects.dimmed 交给渲染层。验证 `recovered/verify_dimming.py`：原函数从入口执行（CanMatchType 为原代码，Dim / Undim 按格记录），1500 组（含无路径、各种类型 / 特殊类型 / 标志）一致；错误副本 3 个全部 exit 1。

## 原版怪行为：商店卷轴候选读到了 Game+0xbf90 之后的内存

FoldoutMenu::Initialise(1) 0x25526：卷轴候选循环 t = 0..39 中，Rand(0,1,流 2) ≥ 0.1 时检查 *(Game + 0xbf90 + 4t) 是否为 0，非 0 则不选该类型。Game+0xbf90 只有 4 个已装备技能指针，后面依次是 skill_count（t=4）、matched_counts[0..4]（t=5..9）、字节 0xbfb8..0xbfbb（t=10）、0xbfbc..0xbfbf（t=11），t=12..39 落在“吸血”伤害标签 SimpleLabel（Game+0xbfc0：+0 激活字节、+4 类型、+8 起为顶点数据）里。所以 t=0..3 永不入选；其余取决于这些字段与标签的顶点内容（标签显示过之后大多为非零浮点）。这像是原版的越界错误，但影响卷轴出现哪种技能。恢复时须按这些字段的实际值判断；标签顶点需要 SimpleLabel 的生成模型（RegenerateLabel），在 K3b 单元测试里作为单独输入；会话（K5b）里 t = 13..39 暂取 0，即只在吸血标签从未显示过时与原版一致，记为已知差异，待补 SimpleLabel 模型（T040-K6，低优先：只影响商店卷轴出现哪种技能的概率）。

## 计划

K1 升级菜单选项（Skill::Initialise 两种、GetSkillPool、Initialise 类型 0）；K2 选择 / 确认 / 动画 / SetSkill 生效；K3 商店（物品、卷轴、SetItem）；K4 装备升级（ItemUpgrade）；K5 会话接线（菜单事件打开菜单，帧路由 Menu 时处理菜单）与整局测试。
