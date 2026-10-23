# T050-A Godot 试玩原型计划（Claude，2026-10-20，未开始）

目标：用户在 Mac 上用鼠标亲手打完一局（简单方块画面），确认手感与工具链；之后同一项目做 iOS（M5）。规则全部来自 `recovered_session`（原生会话库），Godot 只做画面、触摸与菜单显示。

## 前提（需要用户）

1. 安装 Godot 4（稳定版，标准版即可，不需要 .NET 版）。工具不自动安装；可从 godotengine.org 下载，或 `brew install --cask godot`。
2. GDExtension 需要与 Godot 版本一致的 godot-cpp（GitHub 开源，MIT）。下载属于“从外部获取代码”，需用户同意；也可只用 Godot 自带的 `gdextension_interface.h`（`godot --dump-gdextension-interface` 导出，不需下载），代价是包装代码更啰嗦。建议用 godot-cpp。

## 结构

- `frontend/godot/`（新目录）：Godot 项目（场景、脚本、简单图形）。
- `frontend/gdext/`（新目录）：GDExtension 原生库，C++，编译时直接包含 `recovered/` 的源码（与 `run_session_demo.sh` 的源文件列表相同），不复制规则代码。
- 一个 Godot 节点类 `DungeonRaidSession`：
  - `new_game(kind, seed)`：建会话（会话自带原版的开机职业名单，T040-M2）、写棋盘布局（同 `session_demo.cpp` 的 main），`dr_session_start_game`（0 普通 / 1 教程 / 2 挑战，T040-M1）。
  - `frame(dt, phase, x, y)`：`dr_session_frame`；phase 0 无触摸、1 按下 / 拖动、2 抬起；坐标为归一化坐标（屏幕宽 = 1，格子间距 pitch = 1/6）。
  - 读取：36 格（类型、特殊类型、敌人类型、血量 / 攻击 / 护甲、选中、变暗 dimmed、下落位置 geometry.center）、路径、资源（生命 / 护甲 / 经验 / 金币 / 升级点 / 等级）、技能槽与冷却、菜单状态（类型、选项、选择、动画计时）、结束画面。
  - 写入（渲染层拥有）：`skill_button` / `menu_button`（触摸下的按钮）、`release_inputs->health_target`（生命条目标点）、`current_label_active`（当前伤害标签是否在显示）。吸血 / 火焰 / 尖刺三个伤害标签由会话自己维护（`SessionObjects.damage_labels`：位置、缩放、字形与顶点、透明度，T040-K6），渲染层只按它们绘制。
  - 存档（T030-N5 已恢复，平台层要做的部分）：每帧检查 `end->flag_146d4`（对局存档变化：`flag_146d0` 为长度，0 表示删除）、`class_save->changed_14adc`（职业进度）与 `dr_session_save_changed_scores`（最高分，按类别 0..5 逐个返回），把对应字节写盘（Godot 的 `user://`）并清标志；启动时依次 `dr_session_restore_classes`、`dr_session_restore_scores`（每个类别）、`dr_session_restore_save`；主菜单在存档长度不为 0 时显示“继续”，点击调用 `dr_session_continue_game`。玩家名写入 `SessionObjects.name`（最多 16 个字符）。另：`match->spawn_dirty_15555` 置位时保存 `match->spawn_remaining_15558`（职业卷轴倒计时），启动时写回。
  - 事件：会话的表现事件（SessionHost.event：来源 + 单元自己的事件结构）转成 Godot 信号，原型只用少数（音效、飞行代币、闪光可先忽略）；代币飞行目标点（SessionHost.target / token_start）给界面布局常量。

## 分步

| 步骤 | 内容 | 完成标志 |
| --- | --- | --- |
| A1 | GDExtension 骨架：构建脚本、Godot 能加载、每帧调用 `frame` | Godot 运行时打印回合数随连线增加 |
| A2 | 棋盘：6×6 方块按类型着色、数字显示敌人血量 / 攻击；鼠标连线（按下、拖过、抬起）；变暗显示 | 能连线消除、补位下落 |
| A3 | 顶部资源条、回合、敌人攻击、结束画面与重新开始；存档写盘、主菜单“继续” | 能打到游戏结束并重开；退出后能继续 |
| A4 | 升级 / 商店 / 装备升级菜单弹窗（选项文字用技能 / 物品类型名）、技能按钮与冷却 | 菜单可选可确认、技能可用 |
| A5 | 导出 Mac 应用给用户试玩 | 用户打完一局并反馈手感 |

## 参考

- `recovered/session_demo.cpp`：不带画面的同一流程（建会话、新局、每帧输入、菜单按钮），A1～A4 的逻辑可直接照搬。
- `recovered/recovered_session.hpp`：SessionObjects（每帧可读写的对象）、SessionSource（事件来源）、SessionHost（回调）。
- 原版画面与素材仅本地保留，不放进仓库；原型用简单图形。高清美术来源待用户决定（ROADMAP 第五节）。

## 进度（Claude 支线会话，2026-10-21）

- 用户已装 Godot 4.7.2（/Applications/Godot.app）。godot-cpp 10.0.0-stable（507ed9d，用户 2026-10-21 同意下载）放在 `frontend/gdext/godot-cpp`，不进 Git；绑定按 API 4.5 生成（裁剪到 RefCounted / OS / Engine），所以 4.5 及以后的 Godot 都能加载。不需要 SCons / CMake：`python3 frontend/gdext/build.py extension` 直接用 clang++ 编译，规则源码按 `recovered/run_session_demo.sh` 的列表从 `recovered/` 编译，不复制。
- A1 完成：转接层 `frontend/gdext/src/dr_bridge.*`（不依赖 Godot）与 Godot 类 `DungeonRaidSession`；Godot 4.7.2 实际加载成功。
- A2、A3 完成，A4 大部分完成（`frontend/godot/main.gd`）：6×6 棋盘（简单图形：药水、骷髅带攻击 / 血量 / 护甲、金币、盾牌、剑，特殊敌人、法力 / 爆炸药水、箭、魔法剑、破损、冻结、燃烧标记），鼠标连线（按下、拖过、松开）、变暗、伤害预览、补位下落；顶部资源条（生命、经验、金币、护甲、升级点）；敌人攻击提示；飞行代币、吸血 / 火焰 / 尖刺标签；技能按钮与冷却；升级 / 商店 / 装备升级弹窗（选项、确定）；游戏结束画面与回主菜单；主菜单（继续、新游戏、教程、挑战）；开局设置（随机名字、职业、难度或挑战模式）与故事画面（文字未接）；存档写 `user://`（先写临时文件再改名，空存档删除）、启动时按 Game::Start 顺序读回。双击入口 `frontend/试玩 Dungeon Raid.command`（每次先重编，失败时用上次的库）。
- 本轮实跑：`build.py test` 通过（经开局设置与故事画面；存档→重启→继续同一回合→打到结束→存档删除→最高分与职业记录读回；同一会话连开教程与挑战；三种菜单与技能都出现）；Godot `tests/smoke.gd` 通过（20 回合，turn 20，已存档）；`--autoplay` 无界面整局到游戏结束（第 55 回合，等级 3，菜单与技能都出现），窗口模式截图检查主菜单、开局设置、故事、连线、敌人攻击、三种菜单、第 20 回合画面。结果随 `recovered/` 源码变化失效（主会话仍在改）。
- 依赖主会话进行中的接口：开局设置与故事画面（`dr_session_setup_*`、`dr_session_intro_done`，T040-M3，截至本轮未提交）。
- 临时替代（代码里有注释）：`Bridge::leave_game_over` 在玩家离开结束画面时清 `end->game_over_screen` 与 `game_over_state_cc1c`，等局后流程（T040-M7）恢复后改为正式接口；开局前同 session_demo 写 pitch 与特性 / 缺陷 255；技能名按效果暂起中文名，职业叫"职业1～10"，装备只区分"武器 / 装备2～5"，原版文字未接。
- 没做：A5（导出独立 Mac 应用需要 Godot 导出模板，约 1 GB 下载，要用户同意；目前用双击入口直接运行项目）；音效、动画细节、帮助提示、游戏中菜单（T040-M5）。
- 待主会话合并：根 `.gitignore` 目前忽略整个 `frontend/`，需加 `!/frontend/`（`frontend/.gitignore` 已忽略 godot-cpp、build、bin、.godot）；TASKS / PROJECT_STATE / VALIDATION 记录上述进度与验证；DECISIONS 记录 godot-cpp 下载同意。

## 第二阶段：与原版一模一样（Claude 支线会话，2026-10-21 起）

用户方向（2026-10-21，经主会话转达）：画面、布局、动画、音效、操作手感、文字（原版英文与原版字体）都和原版一模一样；高清化、多语言、新教程等在这一步全部完成后再做。原版素材只在本机用、不进 Git。

### 做法
- **原版参照（本机，只用于测量）**：`frontend/tools/original_frame.py` 在 Unicorn 模拟器里按 EAGLView 的顺序运行原版程序（Game::Game、各项设置、CreateFont、Game::Start，每帧 Game::Process / Game::Render，触摸经 Game::TouchStart / TouchDrag / TouchEnd），系统库由脚本模拟，OpenGL ES 1.1 调用被记录成“绘制清单”（贴图、混合、变换后的顶点、贴图坐标、颜色、调用链）。`frontend/tools/draw_frame.py` 把清单画成 PNG。已出图：主菜单、开局设置、故事、棋盘、连线中、第 5 回合、商店。原版指令不进入游戏，只用来出标准答案。
- **画面代码恢复**：`frontend/gdext/src/ui/`（C++，与规则一样按原版浮点运算顺序）：gl（OpenGL 替身，记录绘制）、quad（Quad）、text（Font / Label）、presenter（Game::Render 与各画面对象，接收会话的表现事件）。Godot 只负责把绘制清单画出来、放声音、接触摸。
- **对照台**：`frontend/tools/lockstep.py`（先 `build.py check`）让原版与前端吃同样的输入逐帧并跑：比较棋盘状态，再比较已恢复部分的绘制清单（逐顶点、逐位）。
- **素材**：`frontend/tools/import_original_assets.py` 从本机资料取贴图（reference/decoded-assets）、字体（reference/original-assets）、音效（本机 IPA，afconvert 转 WAV）、应用图标，以及从原版程序读出的音效表（GetSoundName / GetSoundVariations / GetSoundVolume：38 种、变体数、音量）到 `frontend/godot/assets/original/`（`frontend/.gitignore` 已排除）。贴图编号（GetTextureName）：1 tiles、2 font、3 icons、4 menus、5 fontMenu、6 fontScore。

### 进度
- A5：`python3 frontend/gdext/build.py app` 生成 `frontend/dist/Dungeon Raid.app`（162 MB，双击即玩，不开终端）：用本机已装 Godot 的运行程序（只取 arm64）运行应用内的项目，不需要下载导出模板；已用 `open` 实测启动并自动打通。正式导出（及 iOS）需 Godot 导出模板（约 1 GB，下载前需用户同意）。
- 已恢复并与原版逐位一致（2026-10-22 本轮实跑 `python3 frontend/gdext/build.py check && python3 -I frontend/tools/lockstep.py 80`：一局玩到第 64 回合角色死亡为止，每一笔连线的每一格、松手后每一帧、菜单的每一帧都比，棋盘状态和全部已恢复绘制逐顶点一致；之后的结束画面与最高分页见下文 2026-10-23 的条目）：
  - 棋盘：Quad、Font、Label、Tile::Render / RenderText / RenderOverlay / RenderCross 及格子的标签、倒计时、敌人图、变暗、冰冻 / 火焰覆盖、宿敌光环。
  - 界面：Interface（顶 / 底面板、血瓶与数值、经验 / 升级条、金币堆、护盾值、毒、阴影预览、心跳、技能槽充能与高亮、已装备技能的图标与等级、菜单 / 属性按钮）、连线箭头 Arrow。
  - 动作与反馈：代币（Token）、消除碎屑（Particles）、各种浮动数字（SimpleLabel 池、击杀标记、当前伤害、吸血 / 火焰 / 尖刺）、闪光（AddFlare）、敌人攻击的红黄条与飞向血条的伤害数字、护盾碎裂。
  - 升级 / 商店 / 升级点菜单（FoldoutMenu，`frontend/gdext/src/ui/menu.*`）：面板拼图、滑入滑出与背景变暗、选项框与两道选中条、确认按钮、技能 / 属性 / 装备 / 装备升级的图标，以及全部文字（名称、按字体宽度换行的说明、冷却与数值行、装备说明两行、商店里比现有装备好的属性绿色 / 差的红色、“Replaces:” 一栏、卷轴缩小）。点击判定（选项 14..17、确认 7）也按原版做，交给会话。对照台这局玩了 5 个菜单：商店、升级、升级点、商店、升级。
  - 游戏中菜单（GameMenu，接 M5）：面板、七个按钮、五个开关的勾（声音 / 帮助 / 时钟 / 攻击变暗 / 高帧率，按会话的设置字节画）、淡入淡出与背景变暗、按下变暗；界面右上 Menu / Stats 按钮按下变暗；时钟开关打开后 Menu 按钮换图并显示当前时间（原版平台每帧写时间，NSDateFormatter 短时间格式，这里按英文 “9:41 PM”）。攻击变暗遮罩改为跟随设置。
  - 属性菜单（StatsMenu，接 M5）：17 行属性名与数值（百分比封顶 100%，有加成时绿色）、难度 / 模式与得分行、五件装备与职业的六个分页（装备页：名称与每项属性一行；职业页：种族与职业、按宽度换行的种族加成、天赋与缺陷说明）、面板高度随页面行数变化、职业头像（QuadStrip）、淡入淡出。点击判定（面板外 −1、分页 10..15、面板内 0）交给会话。
  - 对照台这局还开关了两次游戏中菜单（逐个按开关再关闭，开局一次把攻击变暗打开、第 4 回合关上）、打开四次属性菜单（开局与第 6 / 20 / 40 回合，每个分页都点，再点面板外关闭）；本轮实跑共比了游戏中菜单 1980 笔、属性菜单 63916 笔绘制，全部一致。
  - 原版英文文字：`frontend/tools/import_original_assets.py --texts` 从本机原版程序读出（技能名与说明、属性名、装备前缀与名称表（运行中的原版内存）、装备升级名称与说明、所有格式串，以及属性菜单的行名、装备属性长句、种族 / 职业 / 天赋 / 缺陷 / 难度 / 模式名称（在模拟器里调用原版的查询函数）），写到 `frontend/godot/assets/original/texts.txt`（已被 Git 排除，只在本机），画面层运行时读取。
- Godot：`frontend/godot/original.tscn`（original.gd）已是默认入口：游戏库输出绘制清单，Godot 用原版贴图照画（贴图按原版的预乘透明度加载、线性过滤、边缘夹紧，混合方式同原版），鼠标作触摸，点击菜单按钮交给会话；固定每秒 60 步（原版在 iPhone 上 60 帧；屏幕刷新更快时原版的一些整数截断会让动画卡住，所以不能按实际帧间隔走）。有存档时直接继续上局，否则随机名字开新局；局终后自动开新局；游戏中菜单的 Exit（回主菜单）暂时直接继续存档（主菜单未恢复）。设置（声音 / 时钟 / 攻击变暗 / 高帧率）按原版平台保存（user://settings.bin），首次启动按原版平台的默认（攻击变暗、高帧率开，时钟关；声音由 Game::Game 打开）；高帧率关闭时按原版改为每秒 30 步。`build.py app` 重新打包的 Mac 应用已实测（原版样子的棋盘、技能栏、代币、文字）。原来的中文原型（main.tscn）保留，不再是入口。
- 帮助提示框（HelpMenu，接 M6，`frontend/gdext/src/ui/help.*`）：气泡的框与指向箭头（在点的上方或下方、偏左偏右两种箭头）、按 0.88 宽换行的黑字、贴齐 320 点网格的位置、淡入淡出（透明度 240）、点框内关闭。23 种帮助文字从原版程序读出（help.topic.*）。技能就绪 / 生效的帮助（19 / 20）指向技能槽。对照台开局在游戏中菜单里打开“帮助”，之后弹出的提示逐个点掉：80 回合内 39 个提示、约 6.8 万笔绘制全部一致。开局设置与职业画面的说明文字（100..122）要等这两个画面恢复后才有位置与文字。
- 主菜单（MainMenu，接主会话正在做的 M7，`frontend/gdext/src/ui/screens.*`）：背景、标题、八个按钮（继续、新游戏、挑战、教程、最高分、声音开关（侧放）、OpenFeint、奖励（默认不显示））、More Games 的颜色循环（原版 HSVtoRGB 照搬，含原版的两处小错）、开机标题渐隐与按钮渐显、从游戏菜单 Exit 回来的 0.5 秒淡入、继续游戏的 0.3 秒淡出、有存档时新游戏 / 挑战 / 教程先弹出“会删除当前存档”确认框（淡入淡出、按下的答案变灰）、没有存档 / 没有最高分时对应按钮半透明。画面层在会话处理主菜单前按原版同样的顺序改透明度；点击判定（0..7 按钮、8 More Games、9 奖励、10 / 11 确认框的是 / 否；松手后的下一帧仍按最后的触点判定）交给会话。原版在设置画面打开时只画主菜单与设置画面、在最高分页打开时只画最高分页（淡入淡出时连同主菜单），画面总流程已按此调整。对照台：开机 30 帧、按新游戏、设置画面下的主菜单、第 8 / 30 回合从游戏菜单退出→新游戏→确认框选否→继续，全部一致（约 2000 笔主菜单绘制），继续后棋盘与原版仍一致。
- 对照台新增：绘制带“出自哪个画面”的标记（gl.hpp DrawTag），可以只比某一个画面（开机时会话没有原版的开局棋盘，只比主菜单）。
- 开局设置（NameScreen，`frontend/gdext/src/ui/setup.*`，用 QuadStrip `strip.*`）：名字框与屏幕键盘（滑入滑出、大小写、删除键连按、光标闪烁、最多 15 字）、Random、四个难度（挑战局为两个模式按钮与 Help）、十个职业（未解锁显示锁）、职业属性（职业 / 种族 / 技能图、四个天赋四个缺陷）、Help 气泡（100..104）、Back、Begin。触摸按原版 ProcessInput 判定，会话调用（随机名、难度、模式、职业、开始、帮助、返回）在该帧后由 `front_requests.hpp` 依次执行。对照台：键盘输入、Random、Help 五个气泡、选难度、Begin，约 27 万笔绘制逐位一致。
- 故事（IntroScreen，`frontend/gdext/src/ui/intro.*`）：61 段原版故事（按原版 RandI(0, 60, 第 0 路) 抽取，新局随后会重设全部随机种子，所以画面层在会话随机状态的副本上抽，不改会话）、按宽度在空格处断行居中、1 秒淡入、Begin（按下变暗黄）后 1 秒淡出（淡出时主菜单与设置画面不再画），淡出结束由画面层调用 `dr_session_intro_done` 进入游戏。对照台：故事 180 帧、按 Begin、淡出到进入游戏，约 11.8 万笔绘制逐位一致，进入游戏后棋盘仍与原版一致。
- 模式说明（ModeScreen，`frontend/gdext/src/ui/mode.cpp`，类在 setup.hpp）：挑战局设置画面的 Help 打开；两种模式按钮（选择即会话的 SetMode，下一帧 UpdateMode 刷新文字）、模式图片、四行简介、计分、特殊规则、0.3 秒淡入淡出、Return。面板、按钮、标题与取名画面同一份代码（make_panel / make_button / make_heading_label 已改为共用函数）。对照台：主菜单 Challenge → 挑战设置 → Help → 两种模式来回切换 → Return → 设置 Back 回主菜单，逐帧一致。
- 职业编辑（ClassScreen，`frontend/gdext/src/ui/class_screen.*`）：四个分页（职业 / 种族 / 天赋与缺陷 / 技能）、各页按钮与图标、职业信息与等级行、种族与宿敌说明、天赋缺陷槽、技能格、文字框（含按宽度断行、居中）、Help（帮助文字 105..122 与原版提示位置）、Return（淡出后回设置画面并刷新设置画面的职业图）、拖放（天赋 / 缺陷拖进槽位或拖出、其他技能拖到职业技能上替换或拖出，拖动中技能图标随高度缩放）。规则改动全部经会话（dr_session_class_*），画面层在会话处理后按原版顺序刷新。原版构造过程用 trace_function.py 逐步记录后移植；文字与名称（职业等级说明、宿敌、种族加成名、天赋 / 缺陷名等）加入 import_original_assets.py。对照台 `CLASS_SCREEN=1 python3 frontend/tools/lockstep.py`：先把原版与会话读入同一份职业进度（5 个职业不同等级），再打开 Edit，依次看四个分页、点各种图标、选牧师、换种族、拖入拖出天赋与技能、Help 气泡、Return，约 23 万笔绘制逐位一致（另修正设置画面职业技能图：原版取职业第一个基础技能）。默认不带这段（见需求 24）。
- 结束画面（GameOverScreen，`frontend/gdext/src/ui/gameover.*`，2026-10-23）：胜利绿 / 失败红的底色 2 秒淡入（胜利标题或失败墓碑）、1 秒后转黑（标题随之淡出），然后逐行计数：名字、"Level N 种族 职业"、难度或模式，回合 / 等级 / 经验 / 金币 / 升级点（挑战模式 1 为平均、最长、总数，平均按十分之一显示）的数字从 1 按增长倍率涨到终值，五件装备、技能、天赋、缺陷的图标每 0.2 秒出一个（从右往左，0.4 倍大），分数，最后是棋盘上剩下的敌人（按种类排序，每行最多 11 个居中，宿敌带光环）；10 秒后（点一下即跳过）2 秒淡出到最高分页。计数、等待、状态都是会话的（GameOverTally，主会话 M7），画面层在会话那一步之后按前后状态照原版改透明度、文字与位置。注意：原版 InitIcons 移动的是游戏自己的技能对象，所以结束画面下面界面里的技能图标也跟着挪走——画面层照做（对照台第一次就是在这里发现的）。
- 最高分页（ScoreScreen，`frontend/gdext/src/ui/scores.*`，2026-10-23）：底板、标题条、Back，六张表（四个难度、两个挑战模式）一页一张；三个页面对象（前一页、当前、后一页）随拖动或左右箭头滑动，滑到位后三者轮换、重新填写新的邻页；每页十行（名次、名字、回合、三项数值（挑战模式 1 为 Avg / Max / Total）、分数、四个技能图标），最新一局的那行黄色，空行半透明，最左 / 最右页的箭头按钮变暗；0.3 秒淡入淡出，从结束画面进来时不淡入（结束画面在上面淡出）。Back 回主菜单（主菜单淡入），主菜单的“最高分”按钮也能打开它。点击判定（1 Back、2 左箭头、3 右箭头、在行区域内另加 16 表示可以开始拖动）交给会话；松手那一帧仍按最后的触点判定。
- 对照台 `python3 frontend/tools/lockstep.py 80`（2026-10-23 本轮实跑）：一局玩到第 65 回合角色死亡，结束画面 1877 帧逐帧比较、约 17 万笔结束画面绘制全部一致；之后最高分页：从结束画面接手的 10 帧、向左拖到下一页、左箭头回来、右箭头再过去、Back 淡出到主菜单、主菜单“最高分”打开（淡入）、再 Back，逐帧比较：最高分页约 31.3 万笔、其间主菜单绘制全部一致，退出码 0、没有任何不一致（棋盘 65 回合也始终与原版相同）。
- Godot：启动即原版主菜单 → 新游戏 / 继续（有存档时确认框）→ 原版设置画面（含职业编辑、挑战模式说明）→ 原版故事 → 游戏 → 原版结束画面 → 原版最高分页 → Back 回主菜单，全部可操作；主菜单的“最高分”按钮可用。原来局终后直接回主菜单的临时做法已去掉（`leave_game_over` 只留给旧的中文原型 main.gd）。`--autoplay` 在设置画面点 Random、Begin，在故事点 Begin，结束画面等它自己数完，最高分页停 200 帧后点 Back；`--over-shot=` / `--scores-shot=` 在结束画面第 20 秒、最高分页第 2 秒截图；`--challenge` 让自动试玩开挑战局（截图已查：分数条与回合数）。全程有原版音效。另修正：从原版主菜单“继续”上局时棋盘格子全挤在左上角、无法落子（格子间距等 Game::Start 的初值原来只在转接层自己的开局里设，主菜单由会话直接开局时漏了；现在转接层创建时就设一次，见需求 27）。
- 解锁弹窗（UnlockMenu，`frontend/gdext/src/ui/unlock.*`，接 M8，2026-10-23）：职业卷轴带来的 “Class unlocked: X!”（职业的解锁说明）或 “X level up!”（新等级），九宫格边框按文字大小拼、居中、贴 320 点网格且不出屏，标题与正文之间是职业头像；淡入淡出与开关是会话的（UnlockPopup），画面层按会话的透明度整体设置。英文文字（含 10 个职业的解锁说明）加入 import_original_assets.py。对照台在开局（解锁牧师）与第 10 回合（冒险者升到 2 级）各弹一次：原版直接调用 UnlockMenu::Show，前端用测试接口 `drf_test_unlock` 做会话那一步（打开、未关闭、视作按下），淡入、点击、淡出逐帧比较，约 9800 笔绘制一致。
- 提示框（Tooltip，`frontend/gdext/src/ui/tooltip.*`，2026-10-23）：连线从敌人开始时的敌人名称与说明（职业宿敌为红色并附种族弱点）、按住已装备技能时的技能名、说明与冷却、商店里卷轴的说明；九宫格边框、在点的上方或下方、贴网格不出屏；淡入到 240、按 255×8/秒淡出，都在画面层（Interface::Process 最后一步）。按钮位置表（0x1eac44，静态初始化填的）从运行中的原版读出。另补上：按下技能按钮时按钮变灰（SkillEventKind::ButtonColour）。对照台：正常对局里的敌人提示框，加上第 30、50 回合按住技能按钮 40 帧再松开，约 9100 笔提示框绘制一致。33 种敌人的名称与说明、卷轴 / 冷却 / 宿敌格式串加入 import_original_assets.py。
- 音效（2026-10-23）：原版每帧把要播的声音排进 Game::QueueSound 的队列（Game::Process 开始时清空），EAGLView 画完后逐个取出，GetSoundMapping 用 RandI(0, 录音数−1, 第 0 路) 选录音——这一抽会改变第 0 路随机数，影响之后的画面与游戏（实测：少抽一次心跳声，几帧后代币时序与棋盘都偏离原版）。前端做法：`Presenter::sounds` 按原版顺序收集这一帧的声音（各单元的 Sound 事件、Game::QueueTileSound 按格子类型、各画面自己的按键声：设置画面 12 处、职业编辑 14 处、模式说明 2 处、故事 Begin 18、结束画面 12 / 33、心跳 32），声音关闭时不排队；帧结束后 `play_sounds` 照原版逐个抽录音，Godot（original.gd）按 sounds.json 的音量播放对应 WAV（可同时多个）。对照台每帧读出原版队列（Game+0x13e9c / +0x13ea8）与前端逐个比较，并在原版侧照 EAGLView 调用 RandI 抽同样的数。本轮实跑 `python3 frontend/tools/lockstep.py 80`（含两次解锁弹窗、两次按住技能、结束画面、最高分页）：一局 78 回合、25925 帧里原版排了 1994 个声音，前端逐帧逐个相同，抽数之后棋盘与全部已恢复绘制仍逐位一致，退出码 0；`CLASS_SCREEN=1` 的职业编辑段 64 个声音也一致。
- 挑战模式（2026-10-23）：界面上方的分数条与回合数（Interface::Process 0x20db0 / Render，分数字体、绿色）：这一轮的得分（模式 0 另有奖励）先挂在分数后面（“Score 120 + 30 + 5 bonus”，模式 1 按奖励级别加 ! / !! / !!!），这一轮的格子全部算完后 0.2 秒开始逐帧倒进分数（每帧速度 ×1.5，奖励先）；模式 0 另在右侧显示 “Turn N”。对照台新增 `CHALLENGE=0` / `CHALLENGE=1`：主菜单 Challenge → 设置画面 Random、选模式 → Begin → 故事 → 一局挑战（另修正：设置画面 Random 那一帧原版已有名字，Begin 当帧就开始淡入，前端改为在会话取名之后补做这一帧的淡入）。两种模式前 8 回合棋盘、界面（含分数条）、声音全部一致。整局（本轮实跑）：`CHALLENGE=0 python3 frontend/tools/lockstep.py 120` 一局 28 回合到结束画面与挑战模式的最高分页，11835 帧、777 个声音全部一致；`CHALLENGE=1 ... 400` 一局 122 回合到结束画面（模式 1 的平均长度按十分之一显示、最长、总数）与模式 1 的最高分页（Avg / Max / Total 表头），37278 帧、2520 个声音全部一致，退出码都是 0。
- 接上后端 N1–N5 / M8（2026-10-23）：前端删掉了所有替会话补的临时做法，改用会话自己的：开机状态与 `dr_session_seed`（默认难度、格子间距、下落初值、遮罩 120、伤害数字高度、界面显示值 −1、声音默认开、当前职业副本同步都由会话设）；统一声音队列（各画面的按键声、故事 Begin、结束画面的声音由画面层用 `dr_session_queue_sound` 排进会话的队列，帧后用 `dr_session_next_sound` 逐个取出，录音的第 0 路抽取由会话做；画面层不再自己收集和抽数）；心跳由会话处理（画面层在 InterfaceProcess 前记下 Heartbeat，处理后照原版只更新颜色与数值）；代币的图与宿敌光环速度改为在会话随机状态的副本上抽（会话自己抽真的，画面层不再写 flag_224）；不再写回 bd30 / bd34 与两个缩放；护盾碎裂、碎屑 / 数字池（Pools 事件）、主菜单 Show（MainMenuShow 事件）、故事编号（SetupScreen.story）、打开职业编辑（`dr_session_class_open`）、设置画面 Back（`dr_session_setup_back`）都改用会话的。recovered/ 未改。本轮实跑：`python3 frontend/tools/lockstep.py 80`（78 回合、结束画面、最高分页、两次解锁弹窗、两次技能提示框，1994 个声音）、`CLASS_SCREEN=1 ... 20`（需求 25 的牧师属性 30% 现在一致）、`CHALLENGE=0 ... 120`、`CHALLENGE=1 ... 400`，全部没有任何不一致；Godot `--autoplay` 整局到结束画面与最高分页正常。
- 接上后端 N6（ac641ad，2026-10-23）：结束画面改读 GameOverLine 给的终值、最高分页改在 ScorePageTurn 时轮换三页（需求 28）。本轮实跑 `lockstep.py 80`、`CLASS_SCREEN=1 ... 20`、`CHALLENGE=0 ... 120`、`CHALLENGE=1 ... 400` 全部 0 处不一致、退出码 0（声音分别 1994 / 446 / 777 / 2520 个逐帧相同）；`build.py app` 已重新打包。
- 未完成：奖励提示（UnlockMenu::ShowPromo，原版的推广弹窗，平台的）。

### 给后端（主会话）的需求（对照台发现，前端暂时按原版补在 frontend/）
1. **默认难度**：Game::Game 0xe17c 把难度（Game+0x14ae0，MatchState.spawn_enabled_14ae0）设为 1；会话从 0 开始，敌人属性因此不同（实测骷髅血量 3 对 4）。转接层暂用 dr_session_set_difficulty(1)。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
2. **格子间距**：Game::Start 0xb8fa 设 Game+0x5e50 = 0.165625（geometry.pitch）、+0x5e54 = 0.0828125（half_spacing）；会话留给平台。转接层暂设。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
3. **格子下落初值**：Tile::Tile 0x3e0e6 设 Tile+0x94 = 1.0、+0x98 = 0.5（FallingTile.speed / acceleration）；会话为 0，第一次下落慢一拍。转接层暂设。 **已解决（后端 N3，2026-10-23；前端的临时做法已删，对照台复验一致）。**
4. **Tile::UpdateEnemyUV 0x3ef64 的规则部分**：当前职业的宿敌（CharacterClass::GetMortalEnemyType）时置 Tile+0x224（GeneratedTile.flag_224，棋盘效果的 Spin 读它）并抽 Rand(30, 45, 流 0) 存 Tile+0x228；否则清 flag_224。会话目前把 EnemyUV 只当画面事件、注释写“从不设置”。画面层暂按原版做（写 flag_224、抽随机数），建议移入会话。 **已解决（后端 N3，2026-10-23；前端的临时做法已删，对照台复验一致）。**
5. **音效队列**：原版 Game::QueueSound 0x903c 把各单元的音效编号排进同一个队列，EAGLView drawView 每帧 Render 之后用 Game::GetNextSound 取出，每个经 GetSoundMapping 0x1bdf8（RandI(0, 变体数−1, 流 0)，即使只有一个变体也抽）选文件。会话的音效散在十几种事件里。建议会话提供统一队列（如 dr_session_next_sound）与变体选择（含流 0 抽取），平台按原版顺序取用。**现状（2026-10-23）**：前端已按原版顺序自己收集（含画面自己的按键声与心跳声）并在帧后抽流 0，对照台逐帧比较队列一致；会话若以后提供队列，请保持这个顺序与抽取时刻。注意：这一抽影响之后的随机数，所以声音开关会改变之后的游戏（与原版一致）；不播放声音的平台也必须照抽，否则与原版不同。 **已解决（后端 N4，2026-10-23；前端的临时做法已删，对照台复验一致）。**
6. ~~局后流程前 `Bridge::leave_game_over` 暂清结束画面标志~~：M7 已有结束画面与最高分页，原版样子的入口不再调用它（只剩旧中文原型 main.gd 用）。
7. **代币的图（Tile::GetTileUV 0x3d480）**：Token::InitialiseFromTile 在奖励类型与格子不同时取 GetTileUV，它抽 RandI(0, 7, 流 0)；会话的 MotionEvent TileVisual 没抽。画面层暂从会话的流 0 实抽（与原版同一时刻），建议移入会话（dr_initialise_token）。 **已解决（后端 N3，2026-10-23；前端的临时做法已删，对照台复验一致）。**
8. **攻击变暗遮罩初值（重要，影响时序）**：Game::Start 0xbb5a 把遮罩 Game+0xb91c 设为 (0,0,0,120)；敌人攻击第 1 阶段从这个透明度（Game+0xb92b，会话 overlay_alpha）涨到 200。会话从 0 开始，于是每局第一次敌人攻击晚约 10 帧进入下一阶段（也晚 10 帧恢复操作）。转接层 `Bridge::prepare` 暂设 120。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
9. **攻击伤害数字的高度**：Game::Start 0xba7a 设 Game+0xbd54 = 0.6675（AttackAnimation.label_y）；会话为 0。转接层暂设。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
10. **AttackAnimation 字段含义**：bd30 / bd34 就是伤害数字 Game+0xb9fc 的位置（SimpleLabel+0x334），damage_label_alpha（Game+0xbd38）/ poison_label_alpha（Game+0x15520）是两个攻击数字的**缩放**（SimpleLabel+0x33c，数字缩小飞向血条），不是透明度。会话读 bd30 / bd34 做飞行起点却没人写；画面层每次移动数字时写回，开局写入 (0.5, 0.6675) 与缩放 1。建议改名并在会话里维护。 **已解决（后端 N5，2026-10-23；前端的临时做法已删，对照台复验一致）。**
11. ~~攻击变暗开关~~：M5 已提供（SaveSettings.dimming_13eca），画面层已改为按它画遮罩。
12. **护盾碎裂没接上**：敌人攻击打碎护盾时原版调用 Game::InialiseShieldShatter；会话只转发 AttackShieldEvent ShieldShatter，没调用 dr_initialise_shield_shatter（生成单元的那条已接）。转接层暂在收到该事件时调用。 **已解决（后端 N2，2026-10-23；前端的临时做法已删，对照台复验一致）。**
13. **碎屑 / 数字池的处理时机**：GameFrameHooks.pools（frame_pools）是空函数、不发事件；画面层只能从后续事件推断这一刻（第一个闪光淡出 / 伤害数字 / 攻击事件或 InterfaceProcess）。建议这一步转发一个事件（如 GameFrameEventKind::Pools）。 **已解决（后端 N2，2026-10-23；前端的临时做法已删，对照台复验一致）。**
14. **画面层写回会话的字段**（按会话注释的设计，记录在此）：current_label_active（当前伤害数字是否显示）、AttackAnimation bd30 / bd34 与两个缩放（第 10 条）。
15. **挑战模式回合标签位置**：MatchTiles 的 39 / 40 / 41 号标签（BattleEvent::Label，tile −1）在函数内静态变量 (0.5, 0.5)（0x1e7960，首次调用时赋值）。仅记录，画面层已按此。
16. **界面显示值初值**：Interface::Interface 0x1f6e6 把显示值（Game+0x5994..0x59c8：ResourceState.ui_health / ui_xp / ui_up / ui_gold / ui_armour，PlayerStats.ui_health_ceiling / ui_sword / ui_armour_max / ui_skull）设为 −1，新局第一次更新必定发生；会话为 0。转接层构造时暂设 −1。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
17. **画面随机数的约定（请保持）**：标签、碎屑、闪光的随机数（SimpleLabel::Initialise、Particles、AddFlare）会话只推进流 0、不给结果；画面层在收到事件时从流 0 的副本抽同样的数。这要求会话**先转发事件、再自己抽**（现状如此），改动时请保持这个顺序。
18. **画面层需要每帧固定 dt**：原版 Game::UpdateTime 用真实帧间隔，攻击遮罩等处把 dt×800 截成整数，帧间隔很小时（刷新率高）动画会停住。Godot 前端固定每秒 60 步、dt = 1/60（原版在 iPhone 上就是 60 帧）。仅记录。
19. **开机声音开关**：Game::Game 0xe388 调用 Game::SetSoundState(true)，声音默认开；会话的设置从全 0 开始（声音关）。转接层构造时暂设 sound_13ec6 = 1（改动标志清零）。其余开关的默认值（攻击变暗、高帧率开，时钟关，EAGLView initWithCoder 无存储时）属于平台，转接层 `Bridge::platform_defaults` 设，仅 Godot 入口调用（对照台不调用，与模拟器一致）。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
20. **设置的保存**：原版平台（EAGLView drawView）在 Game+0x13ec7 / 0x13ecc / 0x13ecd / 0x13ece 改动标志置位时保存对应开关并清标志；转接层 `take_changed` 以 “settings”（4 字节：声音、时钟、攻击变暗、高帧率）交给平台，启动时 `restore` 还原。帮助开关不保存（每局由开局设定）。仅记录。
21. **主菜单的画面事件（M7 进行中，请保留或补上）**：画面层需要知道 (a) 主菜单按钮生效（MainMenuButton，已有：继续 / 无存档时的新游戏 / 挑战 / 教程会开局，原版 StartCyclingGamesColour 之后同一帧还走一步颜色循环）、(b) MoreGames（已有：StopCyclingGamesColour）、(c) MainMenu::Show（从最高分页 Back、设置画面 Back 回主菜单时）——目前画面层按“主菜单重新出现且没有淡入”推断，建议发一个事件。另：会话目前依赖本机未提交的 M7 主菜单代码，前端已按它接好并逐帧验证。 **(c) 已解决（后端 N2 的 MainMenuShow 事件，画面层改为收到事件就 Show，不再推断）。**
22. **故事的抽取**：IntroScreen::Initialise 0x2de90 在 Game::InitNewGame 之前抽 RandI(0, 60, 第 0 路) 选故事（Game+0xc330 起的画面），会话的 `dr_session_setup_start` 没有这一步。因为 InitNewGame 随后用时间重设全部 6 路种子，这一抽对之后的游戏没有影响，画面层暂在会话随机状态的副本上抽（`front_requests.hpp`）。建议会话在 setup_start 里照原版抽并记下故事编号（例如 SetupScreen 或 FrameScreens 里一个字段），画面层改读它。 **已解决（后端 N2，2026-10-23；前端的临时做法已删，对照台复验一致）。**
23. **职业编辑切换分页时的 Validate**：ClassScreen::SelectTab 0x10c4ac 每次选分页（包括 Initialise 里的 SelectTab(0)）都先对当前职业记录调用 CharacterClass::Validate；会话的 `dr_session_class_tab` 只保存，打开职业编辑也没有会话调用。建议：`dr_session_class_tab(s, tab)` 先 Validate 再保存，并加一个打开时的调用（或让 tab 调用兼任）。画面层目前未做这一步（只读规则状态）。 **已解决（后端 N2，2026-10-23；前端的临时做法已删，对照台复验一致）。**
24. **开局前“当前职业”的副本没同步（会改坏职业记录）**：会话创建后 `match.perks`、`selection.character.flaws / race` 仍是 0，没有按当前职业记录（全 255）同步；原版在同一时刻两者一致。之后职业编辑里点职业按钮（`dr_session_class_select`）或 Return（`dr_session_class_done`）走 `dr_session_set_current_class`，先把这些 0 写回旧记录，冒险者因此多出天赋 0 与缺陷 0（Validate 后剩第一格），游戏中属性菜单的职业页随之与原版不同（对照台已复现：原版记录仍为 255）。建议在 Game::Start 对应处（读入职业存档之后）按当前记录设好这些副本（`views_from_record`）。对照台的职业编辑段因此默认关闭（`CLASS_SCREEN=1` 才跑）。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
25. **非冒险者职业开局的一项数值**（待后端核对）：`CLASS_SCREEN=1 python3 frontend/tools/lockstep.py 20` 用牧师（10 级，种族改为精灵）开局，20 回合棋盘始终与原版一致，但游戏中属性菜单有一行百分比数值原版为 30%、会话给出 50%（屏幕 y≈0.70 一行，开局即不同；属性菜单的值全部直接读会话状态）。此前对照只用过冒险者，这可能是 InitNewGame 时按职业等级 / 天赋 / 种族给的加成未完全恢复。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
26. **结束画面数天赋 / 缺陷的来源**：GameOverScreen::InitIcons 0x3013c 数的是当前职业**记录**里的天赋与缺陷（Game+0x15574 / +0x15584 + 当前职业 × 0x184，即 ClassProfile.perks / flaws，跳过 255），图标也按记录取；会话的 `game_over_icons` 数的是 `match.perks` / `selection.character.flaws`（游戏中的副本）。两者一致时没有差别（本局对照一致）；与需求 24 有关，建议改读记录。 **后端答复（2026-10-23）：不改——会话的 match.perks / selection.character 副本在设计上始终等于职业记录（原版直接读写记录，会话读写副本、存档时写回），所以数副本与原版读记录结果相同。关闭。**
27. **Game::Start 的初值要在开机时就有**（需求 2、8、9 的补充）：M7 的主菜单在会话内部直接开局或继续（start_menu_game / dr_session_continue_game），不经过转接层的开局函数，于是格子间距（geometry.pitch / half_spacing）一直是 0，所有格子挤在左上角、无法落子（Godot 实测：开机后点“继续”）。转接层现在在创建会话时设一次（与原版 Game::Start 同时）。建议会话在创建时自己设好这些值（pitch 0.165625、half_spacing 0.0828125、遮罩 120、伤害数字高度 0.6675）。 **已解决（后端 N1，2026-10-23；前端的临时做法已删，对照台复验一致）。**
28. **结束画面 / 最高分页的画面靠“前后对比”推断**（仅记录，可选改进）：画面层在会话处理 GameOver / Score 那一步之后，比较之前与之后的状态（GameOverTally、ScorePages），推断这一帧原版 Process 走了哪一段：计数行刚结束（会话随即把 wait 设为 0.5、value 重置为 1）时显示终值，并按原版的 GetScore / GetTotalXP / GetTotalGold / GetTotalUP / 回合 / 等级 / 挑战计数重新取终值；页面滑到位时按 direction 轮换三页。若会话能发事件（如“某行结束及其数值”“页面轮换”）会更直接。另：最高分页最左 / 最右页旁边的页面对象，原版读计数数组两侧的字（最后一条记录的最后一个技能、最新一局的表号）来决定行是否半透明，画面层照读（这两页不显示，只影响以后轮换前的透明度）。 **已改用事件（后端 N6，ac641ad）：GameOverLine（行号、终值）——画面层在这一行结束时直接显示事件给的终值，删掉了自己重新计算终值的 tally_target；ScorePageTurn（页、方向）——三页轮换改在这个事件（原版 SetScorePage 那一刻）做，不再看“滑动刚停”。淡入淡出、按钮按下等其余部分仍按前后状态。**
29. **解锁弹窗的会话调用只能从职业卷轴触发**（仅记录）：前端测试用 `drf_test_unlock` 直接做 unlock_show 那一步（打开、未关闭、视作按下）再让画面层 Show；若会话改了 unlock_show 的内容，请同步告诉前端。 **后端答复：知道了，unlock_show 若有改动会通知前端。**
