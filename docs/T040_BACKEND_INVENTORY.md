# T040-M：后端收尾盘点（Claude，2026-10-21）

## 结论（给用户）

- **一局之内已全部恢复**：连线、敌人回合、20 种敌人技能、技能、装备、升级 / 商店 / 装备升级菜单、存档 / 读档 / 继续、最高分、伤害数字。整局测试从开局一直打到游戏结束，与原版逐帧一致（verify_session，33909 帧）。
- **一局之外还有规则没恢复**：开机时的初始状态、开局前的设置（名字、职业、模式、难度）、职业编辑（种族、天赋、缺陷、替换技能）、游戏中菜单的设置开关、帮助提示的排队、局后画面的切换。现在这些由调用方直接写进会话。例如整局演示里的职业名单是演示程序自己编的，不是从原版恢复的。
- 原版的“教程”不是一套单独的关卡，而是“难度设为最低 + 重新打开全部帮助提示”的新局；“挑战”是打开记录模式的新局。三者都很小。
- 待补共 7 项（M1..M7，见下表），估计 AI 连续工作 3～4 天。补完之后，前端只负责画面、声音、平台功能，不用再回头补规则。
- 纯显示、文字内容、平台功能、旧版兼容这几类不在后端补，列在后面供 Godot 计划使用。

## 方法

1. 从原版程序的全部函数（反汇编中 8971 个标签）和直接调用关系出发。入口取 iOS 层（EAGLView 等 Objective-C 方法）直接调用的游戏函数：Game::Process、Game::Render、Game::Start、触摸、启动时的设置读取、成就与音效队列等。
2. 列出从这些入口能走到的游戏函数（约 600 个，不含 OpenFeint 与标准库），标出新代码已恢复的部分：按恢复模块注释里登记的原地址或名字；一局之内的部分另以整局逐帧对照为证。早期模块的注释没写地址，凡在 Game::Process / ProcessInput / EndOfTurn / ProcessAttack 之内、整局对照已覆盖的，都算已恢复。
3. 余下的函数按“改变游戏状态 / 只管显示 / 平台或旧版兼容”分类。分类时看每个函数调用了哪些 Game / CharacterClass 的设置函数，必要时直接读指令。
4. 盘点脚本放在本地临时目录，没有进 Git；结论以本文件为准，补做时逐项再核实。

## 待补的规则（建议顺序）

| 编号 | 内容 | 原版函数（地址，字节数） | 要点 |
| --- | --- | --- | --- |
| M1 | 主菜单的三种开局 | Game::NewGame 0x16590（100）、StartTutorial 0x164c0（108）、StartChallenge 0x1652c（100）；HelpMenu::ResetHelp 0x37528、ClearHelp 0x37540 | 都是先 InitNewGame，再打开开局设置画面。普通：记录模式关（Game+0x14aed = 0），帮助关闭并清空。教程：记录模式关，难度设为 0（Game+0x14ae0），帮助打开，ResetHelp 把 23 条帮助全部重新标为待显示（Game+0x102d0）。挑战：记录模式开，帮助关闭并清空。会话目前没有这三个入口。 |
| M2 | 开机初始状态 | Game::Game 0xdd9c（2272，多为界面对象构造）、Game::Start 0xb880（1184）、CharacterClass::Initialise 0x111e20（2744）、Game::SetCurrentClass 0x1a390（92） | 十个职业各自 CharacterClass::Initialise（盘点时只从中提取了基础技能表，函数本身未恢复——M2 补上）、DeserialiseClasses（已恢复）、SetCurrentClass（Game+0x1648c；Game::Game 之后为 0）、格子位置；伤害标签的颜色和持续时间已在 K6 完成。设置的默认值来自平台层（启动时 EAGLView 调用各 Set 函数）。目标：会话自己建立职业名单，不再由调用方编写。 |
| M3 | 开局设置画面 | NameScreen::Show 0x3bd60（664）/ Process 0x3cac0（664）/ ProcessInput 0x3bff8（2760）/ GenerateRandomName；ModeScreen::Process 0x112c0c（304）；Game::SetCurrentClass 0x1a390、SetMode 0x83e8、SetDifficulty 0x842c、SetName 0x8470；IntroScreen::Initialise 0x2de90（884）/ Process 0x2dd04（396） | 规则：可选哪些职业、模式、难度，随机名字（随机流 0），确认后的顺序是 SetName → IntroScreen::Initialise → InitNewGame（介绍画面的随机抽取在重新播种之前，不影响本局）。介绍画面结束时调用 SerialiseState，所以一开局就有存档——会话目前不在这个时间点存档。 |
| M4 | 职业编辑画面 | ClassScreen::Process 0x10ca70（5044）、Initialise、SelectTab、UpdateRace / UpdatePerks / UpdateAbilities；CharacterClass::CanChooseRace 0x110a54、IsPerkUnlocked 0x111548、GetReplacementSkillsAllowed 0x111590、SetPerk 0x1115e0、SetFlaw 0x111628、IsBaseSkill 0x11198c、SetLevel 0x1119b8、IsReplacementSkill 0x111aa8、GetNonBaseSkillIndex 0x111b54、SetReplacementSkill 0x111b80；Game::IsRaceUnlocked 0x8d88、IsPerkUnlocked 0x8f60 | 规则：按职业等级与解锁情况可选的种族、天赋、缺陷、替换技能；改完后 Validate 与 SerialiseClasses（都已恢复）。画面本身很大，规则部分小得多。 |
| M5 | 游戏中菜单 | GameMenu::Process 0x32580（544）、Game::UpdateHelpState 0x9edc | 设置开关（帮助、攻击变暗、时钟、音效、高帧率）与退出到主菜单。帮助开关经 UpdateHelpState：待显示的帮助（Game+0x102d0 的位，即 HelpMenu+0x38）不为空且帮助关闭时全部清空；为空且帮助打开时 ResetHelp 重新置上 23 条。 |
| M6 | 帮助提示队列 | HelpMenu::QueueHelp 0x38268、Show 0x37f04、Process 0x38128（HelpMenu::Initialise 在局内是已登记的事件边界） | 哪条帮助何时排队、何时出现。提示内容属于显示，但“哪些已看过”是存档里的状态（HelpMenu::Serialise 已在存档中恢复）。 |
| M7 | 局后流程 | GameOverScreen::Process 0x30c28（2068）、ScoreScreen::Process 0x367f8（1152）、MainMenu::Process 0x2e668（1488） | 结束画面 → 最高分页 → 主菜单的切换和按钮（新局、继续、教程、挑战、最高分、音效）；最高分页码 SetScorePage。基本是流程，规则很少。 |

验证方式同前几项：原版画面函数从入口执行，模拟按钮输入，跳过显示调用，比较游戏状态；原生会话增加相应接口（例如开机、三种开局、确认开局设置、职业编辑操作）。

估算：M1 约 0.2 天，M2 约 0.5 天，M3 0.5～1 天，M4 约 1 天，M5 与 M6 合计约 0.5 天，M7 约 0.5 天，合计 3～4 天（AI 连续工作，不含等待）。

## 进度

- M1（2026-10-21）：dr_session_start_game，与原版三个入口逐帧对照一致（verify_session 新局阶段）。
- M2（2026-10-21）：dr_class_initialise 与 dr_current_class，dr_session_create 自建职业名单（verify_class_init.py）。
- M4a（2026-10-21）：职业编辑的规则函数与“哪些图标可拖”（recovered_progression、dr_class_choices；verify_class_screen.py）。会话接口（M4b）其后。
- M3（2026-10-21）：开局设置画面的规则与接口（dr_session_set_mode / set_difficulty / set_name、dr_session_setup_random_name / select_class / mode / difficulty / start、dr_session_intro_done，SessionObjects.setup）。屏幕键盘、按钮布局、淡入淡出、按原版字体宽度截短名字归前端；名字最多 16 个字符（随机名字可能是 17 个，SetName 只存 16 个）。

## 归前端或平台（后端不补）

- **显示**：所有 Render；Quad / QuadStrip / Font / Label / Tooltip / Arrow / Particles；图标贴图坐标（CharacterClass::Get*IconCoords、Skill::GetIconUVs、Tile::GetEnemyUV、Upgrade::GetIconUVs）；生命 / 经验 / 金币 / 升级点条与阴影（Interface::Update*Bar、Set*shadow、UpdateHealthColour、ProcessHeartbeat）；统计菜单 StatsMenu（只读显示）；解锁提示 UnlockMenu；当前伤害标签与标签池。
- **文字内容**：职业、种族、天赋、缺陷、技能、敌人、物品的名字与说明（CharacterClass::Get*Name / Get*Description、Skill::GetSkillName / GetSkillDescription、Tile::GetEnemyName / GetEnemyDescription、Item::MakeStatLabels、ItemUpgrade::GetDescription 等）。做多语言时要提取成文字表，归 M4 完善版。
- **平台**：音效与成就队列（Game::GetNextSound、GetNextAchievement）；设置的保存与读取（启动时 EAGLView 调用 SetMode / SetDifficulty / SetName / SetScorePage / SetClockState / SetAttackDimmingState / SetHighFramerate / SetTimeToTrophy）；帧率与时间（CalculateFPS、UpdateTime）；渲染初始化（SetupRenderer、CreateFont）；触摸（TouchDrag / TouchEnd / TouchInterrupted 只记录触摸阶段，已由会话的 frame 参数覆盖）。
- **旧版兼容，不需要**：Game::DeserialiseState1、ScoreScreen::DeserialiseLegacyState、Item / Tile::Deserialise1（更早的存档格式）；OpenFeint（含从成就恢复职业等级：Game::SetClassLevel、FinishedLoadingClassesFromAchievements）。
- **推广画面**：Game::ShowNagScreen、ShowMoreGames、ShowBonusRequest、BonusPromptClosed——是否保留由用户决定，默认不做。

## 尚未独立复核

一局之内的恢复都只经过本工具自己写的对照测试，还没有其他 AI（如 Codex）独立复核。复核可以与 M1..M7 并行，由用户决定何时安排。
