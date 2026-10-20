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

## T040-C2a：Item::IncreaseStat（Claude，2026-10-19）

stats 模块新增 `dr_item_increase_stat`（原版 Item::IncreaseStat 0x29d58）：属性 += GetStatUpgrade（dr_stat_upgrade；下限 0），再重做物品文字（ItemText 事件）。与已恢复的 ReduceStat（DestroyUpgrade 内）对称。松手 MatchPath 的种族 6 升级（ReleaseEventKind::IncreaseStat，Game+0xbe90 的物品，类型 11）接此函数。

验证：verify_stats 新增 300 组，原版 IncreaseStat 与 GetStatUpgrade 为原代码，MakeStats 记录；随机物品与类型（偏向 11、2、10、14、17）及负值触底。错误副本：不触底、改用 Downgrade、不发 ItemText，均 exit 1。

## T040-C2b：职业卷轴分支 [0x16c1c,0x16d88)（Claude，2026-10-19）

`recovered_schedule` 新增 `dr_release_class_scroll`（dr_release_path 返回 ClassScroll 之后调用）：

1. 当前职业（Game+0x15564 + 索引×388，索引 Game+0x1648c）等级 ≤9 且职业类型非 0：RandI(0,1,流 5) 为 0 时走"解锁"，否则升当前职业；其余情况直接走"解锁"。
2. 解锁：收集 10 个职业中等级为 0 的索引（std::vector<int>）；非空时 RandI(0,n−1,5) 选一个，CharacterClass::LevelUp（已恢复的 dr_class_level_up，含 UnlockAchievement 与 CheckIfAllClassesMaxed）并 UnlockMenu::Show(索引, 1)。为空则转去升当前职业。
3. 升当前职业：等级 ≤9 时 LevelUp 并 UnlockMenu::Show(类型, 新等级)；等级 10 跳过。
4. 卷轴格 MatchTile(格, 奖励 7)、MoveMatchedTiles、CheckEndGame：为真时原版直接离开 ProcessInput（不走尾段），原生返回 true；否则 SerialiseState、SerialiseClasses（存档边界）和 dr_release_clear。

ReleaseHooks 增加 `check_end_game` 回调（接 dr_check_end_game），ReleaseEventKind 增加 UnlockMenu、MatchTile（接 dr_match_tile）、MoveMatchedTiles、SerialiseState、SerialiseClasses。职业档案为 ClassProfile[10]（progression 模块）；MatchState.class_level / unlocked[] 是同一批职业记录的视图（当前职业等级、职业 1..9 等级），函数结束时同步。升级成就经 progression 的 achievement 回调转成 ReleaseEvent Achievement；其难度门槛（QueueAchievement 内部）由 ClassScrollState.difficulty 给出，测试取非 0。

验证：verify_release 增至 800 组（另 300 组强制卷轴），原版 CharacterClass::LevelUp / UnlockAchievement / CheckIfAllClassesMaxed / RandI 为原代码，std::vector<int> 在测试中模拟（无分配器），CharacterClass+0 写入 Game 指针。卷轴 329 组；分支：RandI 选择、解锁搜索、解锁升级、无可解锁、当前职业升级、等级 10 跳过、CheckEndGame 结束与继续、等级 >4 成就、全职业满级成就 28 均到达。错误副本 10 个（类型 0 也可选、等级阈值 ≤8、RandI 结果反转、可解锁条件 <10、从职业 1 开始搜索、UnlockMenu 传类型、等级 10 仍升级、忽略 CheckEndGame、奖励 5、不同步 MatchState 视图）全部 exit 1。

## T040-E：新局初始化 InitNewGame（Claude，2026-10-19）

`recovered_schedule` 新增 `dr_init_new_game`（原版 Game::InitNewGame 0x15c50，2160 字节，整函数）与 `dr_calculate_tile_positions`（Game::CalculateTilePositions 0xb264）。字段表由写入追踪得到：在测试宿主里执行原版 InitNewGame，记录其对 Game 内存的全部写入（约 190 个字段及 36 格的中心/坐标/尺寸），逐个归入现有原生状态（MatchState、StrokeState/SelectionState、ResourceState、ResourcePreviewState、PathState、GenerationState、TokenQueue 计数、TurnFlags、TurnFinishFlags、RuneState、EndGameState、AttackDamageState、PlayerStats）；没有归属的放入新结构 NewGameExtra（按偏移命名：5 宽代币计数两端、0x164d4、0xb53c/0xb54c、0xbde8 组、0xbf88、四个 SimpleLabel 活动字节、技能对象 4×4 字节）。

顺序：time() 种子设所有随机流并 Flush → CalculateTilePositions（记录模式时垂直偏移 0.015625；格 y*6+x 静止位置 ((x+0.5)·pitch+0.003125, (y+0.5)·pitch+0.246875+偏移)，中心=静止位置，尺寸 pitch、半尺寸 pitch/2，SetSize 与 InitialiseLabels 事件）→ 职业成就（职业 0，再 1..9；dr_class_unlock_achievements）→ 回合/路径/战斗/代币/标签/标志清零 → 晋升计时（记录模式且 mode 0 为 200，否则 50，缺陷 8 为 49）→ filter_enabled=1 时逐行生成棋盘（dr_position_tile + dr_randomise_tile；filter_swords 沿用旧值）→ filter 清零、起始属性（基础伤害 3，特长 4 +1；生命上限 40，记录模式 1 为 100，特长 9 +10，缺陷 1 −10；界面值不同才更新；经验/升级/金币清零；奖励几率 20，特长 7 使 Game+0xbe18 +10，缺陷 4 使 Game+0xbe30 −10；护甲 0）→ 五件新物品（类型 0..4，Item 事件）、技能对象字节置 0xff → health_bonus/冷却清零、UpdateStats 事件 → 阶段 0、输入就绪、技能数 0、下落列表清空、代币计数 0、等级 1、累计 0、标签活动字节 0 → Interface::Reset。

边界：物品构造（Item::Initialise / GenerateName / GenerateStats / MakeStats，物品模型未恢复）与 UpdateStats（嵌入方接 dr_update_stats）为事件；界面值/血条/Reset、格子标签、Quad::SetSize、Game+0x5e18 回合标签为表现层事件；QueueAchievement 的难度门槛由 NewGameState.difficulty 给出；当前职业取 classes[0]（与既有模块一致，MatchState.perks / SelectionState.character.flaws 为其特长与缺陷）。

验证 `recovered/verify_new_game.py`：原版从入口执行到返回，time() 返回用例种子；SetRandSeed、FlushRandSeeds、UnlockAchievement / CheckIfAllClassesMaxed、HavePerk / HaveFlaw、PositionTile、RandomiseTile 为原代码（生成宿主记录 RandomiseTile 的调用，原生用 GenerationHooks）。200 组：比较追踪到的全部字段（除表现层标签字段与物品指针）、36 格、生成/补位棋盘状态与事件、随机种子、事件序列。晋升 200/50/49、基础伤害 3/4、几率 ±10、生命上限 30..110、血条 0/1/2 次、各界面值更新与否、成就 1..28（含全职业满级 28）均出现。

错误副本 22 个全部 exit 1：垂直偏移条件反转、x 不加 0.003125、半尺寸改全尺寸、x/y 对调、种子只设流 0、不 Flush、跳过职业 0 成就、晋升条件 mode≠1、缺陷 8 改 7、生成前不置 filter、PositionTile 行列对调、不清 filter_swords、特长 4 改 5、生命 100 条件 mode 0、第一次血条传上限、经验条总更新、特长 7 加错几率、去掉缺陷 4、代币 pending 不清零、等级 0、不清 victory、不清标签活动字节。其中"pending 不清零"最初存活（用例初始 pending 恒为 0），改为随机代币计数后被拒。

## T040-D1：Game::Process 伤害标签段（Claude，2026-10-19）

`recovered_schedule` 新增 `dr_process_damage_labels`（Game::Process [0x176fc,0x17cda) 及分支块 [0x17d74,0x17da4)），每帧依次处理吸血、火焰、尖刺三个伤害标签（SimpleLabel：Game+0xbfc0 / 0x14afc / 0x14e70，活动字节为 NewGameExtra.label_active[0..2]）：

1. 标签活动且数值为 0：SimpleLabel::Process(dt)（淡出）。数值 >0 才继续，负值跳过。
2. 显示：吸血在路径有伤害（current_damage>0）时显示在触摸点上方 0.1 处（类型 8，未活动时 Initialise，否则 SetPosition + SetNumber），透明度按 skull_counted 为 255/128；火焰在未飞行时显示（类型 9，有吸血时偏移改为 0x3d75c290≈0.06，比 0.06f 大一个 ulp）；尖刺类似（类型 10，有火焰时再上移 0.04）。
3. 飞行（吸血松手后、火焰/尖刺标签 moving 时）：speed += 10·dt，progress += speed·dt（上限 1），位置 = Interpolate(起点, (0.8625, 1.29375), progress) 再按 arc·(0.25 − (progress−0.5)²) 抬高，缩放 = Interpolate(0.1, 1, progress⁵)（float 版 Interpolate 为 a·t + b·(1−t)，与 GLfloat2 版方向相反）。
4. 到达（progress ≥ 1）：吸血回血（上限 health_max + health_bonus）、清零、音效 4；火焰/尖刺扣玩家生命（不足 0 取 0 并成就 35 / 34），清零与 moving 标志，音效 17 / 25，CheckEndGame：为真时原版直接离开 Game::Process（不调用 ProcessAttack），原生返回 true。

验证 `recovered/verify_damage_labels.py`：段差分，原版从 0x176fc（R4=Game）执行到 ProcessAttack 调用 0x17cda 或尾声 0x17da4；Interpolate、Sqr 为原代码，powf 桩用本机 C 库 powf（与原生同一函数）；SimpleLabel 调用、音效、成就、血条、CheckEndGame 记录。300 组、1081 帧（每组 1/3/8 帧连续携带状态），41 帧因 CheckEndGame 结束；各事件类型均出现。

错误副本 21 个全部 exit 1：速度系数 5、进度用旧速度、进度不封顶、Interpolate 权重对调、弧线符号、缩放指数 4、到达改 >1、吸血不封顶、吸血不清零、拖动条件 ≥0、透明度 64、负值也淡出、Initialise 条件反转、火焰偏移不随吸血、尖刺不随火焰上移、扣血下限 −1、火焰成就号、忽略 CheckEndGame、不清 moving、血条总更新、尖刺类型 9。

测试工具注意：Unicorn（本仓库 TCI 构建）在装有 UC_HOOK_MEM_WRITE 时，`it gt; strgt` 条件存储不执行后 IT 状态滞后，下一条 `beq` 落点偏 2 字节。本测试改用代码钩子记录缩放存储；现有测试均未使用内存钩子。T040-E 的写入追踪曾用内存钩子，已用"执行前后 Game 内存比较"（12 组）复核，字段表无遗漏。

## 后续

- ProcessInput 剩余边界：UpdateCrossVisibility（1032 字节，按伤害类型生成路径上的交叉标签，属表现层）、UpdateDimming、ProcessPretzels（400 字节）、SerialiseState（存档，暂缓），见登记 unrecovered_by_size。
- T040-D：Game::Process 中的游戏部分调度（ProcessEffects、ShieldShatter、标签动画对生命/音效/CheckEndGame 的作用、ProcessAttack 调用条件），界面部分为表现层边界。
- 物品模型：Item 构造（Initialise / GenerateName / GenerateStats / MakeStats）仍为边界，完整新局需要它才能得到起始物品属性。
