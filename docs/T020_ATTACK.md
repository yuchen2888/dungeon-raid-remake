# T020：敌人阶段第一单元

日期：2026-10-18（America/Los_Angeles）。执行者：Codex。起始提交：7652bea，接手工作树干净。完整 T020 仍未完成；本轮只完成护甲损耗子段与完整原函数的静态调用盘点。

## 原函数及调用盘点

原入口 `Game::ProcessAttack` 为 0x14118，按现有反汇编符号范围 2796 字节。`docs/T020_ATTACK_CALLS.json` 登记 55 个直接调用点、32 个目标，包含具名 C++ 调用和数值地址的平台 stub；不是完整控制流图，不覆盖间接调用。

原版字节哈希、目标地址和分类由 `scripts/t020_attack_audit.py` 只读提取，复用 T010 的 Mach-O / 反汇编读取器。检查命令：

```sh
python3 scripts/t020_attack_audit.py --check --out docs/T020_ATTACK_CALLS.json
```

已有 GetEnemyCount、AttackSkull、MoveMatchedTiles、RNG 按已有登记/源码引用；不重新实现。DoCounterattack、ProcessVampires 仍是未恢复的玩法依赖。数学 helper、表现/帮助/UI/音效与成就调用另外标明，不用空回调宣称完整玩法已恢复。

## 本轮实际新增源码

`recovered/recovered_attack_shield.cpp/.hpp` 实现 `dr_process_attack_shield_wear`，只对应 ProcessAttack 的 `[0x147e4,0x1487e)`，154 字节原范围，SHA-256：`f4da372aa5cc61765dd417e05d7e2518d691beecf5e295bb7fe0d9d2d7750e4a`。它是局部流程，不增加完整原函数计数。

共享数据直接使用 ResourceState → MatchState → Stroke/Preview；没有新增第二份持久棋盘或随机状态。为调用已有 dr_enemy_count，临时构造 RuleTile 只读视图。

| 输入/状态 | 原位置 | 行为 |
| --- | --- | --- |
| 已吸收伤害 | R10，前一段 min(伤害,护甲) | 由调用者提供，合法域 0≤值≤当前护甲；这次未恢复其上游计算 |
| 特殊敌人 29 | 现有 Game 棋盘 | 原 GetEnemyCount >0 时，每个吸收点必损耗一点护甲，不消耗 RNG |
| 损耗阈值 | Game+0xbdc8 | 无该敌人时逐点调用 RandI(0,100,5)，严格小于阈值才损耗；不是 ≤ |
| 护甲 / UI 护甲 | Game+0xbda4 / +0x59c0 | 仅损耗>0 时扣除；UI 值不同才同步并发 ShieldValue |
| 表现事件 | 原 UI/音效调用 | 损耗>0 发 ShieldShatter 和声音 16；无损耗发声音 15；顺序保留 |
| 六个随机流 | 0x1eac20 | 调用既有 dr_random_int，仅普通分支消耗流 5，比较全部种子 |

未恢复：前置阶段、护甲/伤害计算、后续生命扣减、反击、吸血敌人、阶段结束与下一回合输入；没有把新片段接入示例后冒充完整回合。

## 原版差分验证

`recovered/verify_attack_shield.py` 从真实原版内存进入 0x147e5（Thumb），设置 R8=Game、R10=已吸收伤害，在 0x1487e 前停止。实际执行该片段、原 GetEnemyCount、RandI、RandUnitF、Clamp；只适配平台 floorf、护甲显示/破碎及音效接口。

- 810 组边界场景，含 0 损伤、阈值 -1/0/1/50/100/101、零/最大种子、敌人 29 出现在敌人/非敌人格、UI 相等/不同。
- 700 组随机棋盘场景。
- 100 个连续步骤，在同一棋盘、护甲与随机状态上携带结果，不在每步重置种子。
- 合计观察 23,417 次真实随机调用，446 个包含强制损耗敌人的场景/步骤。上述不是互不重叠的完整游戏覆盖数。
- 每步比较损耗量、护甲、UI 护甲、六个种子和有序回调；原版 Game 状态区除两个护甲字段外不得有其他写入，原生棋盘及其余 ResourceState 必须保持。
- 对隔离副本故意将 `<` 改为 `<=` 后测试 exit 1：阈值 0、原版损耗 0，错误副本损耗 1。副本和失败现场保存在 `.relay/reviews/T020-mutant/`，实际源码未改坏。

统一入口已扩展：build.sh 构建第 20 个模块及 iPhone 静态库对象，默认 verify 包含新测试，full 自动枚举 21 个验证脚本。最终运行结果见 T020_VALIDATION.json 和 VALIDATION.md 的 T020 节。

## 下一单元

先登记上游伤害/护甲输入、攻击阶段字段与 DoCounterattack 的依赖，选择一段建立实际原指令对照；继续复用已有随机、棋盘和战斗状态。完整 ProcessAttack、EndOfTurn 和输入重开仍待接通。

## T020-B：护甲吸收片段（Claude，2026-10-18）

起始提交 1b1ad9f，接手工作树干净，无继承未提交修改。只恢复 T020-A 的上游 `[0x14790,0x147e4)`（84 字节，SHA-256 `de77208b45497a3c081768728801be020d659df0b69c533b8993804b8098cd98`），加入同一 attack_shield 模块，未新增模块、未改 build.sh。

| 字段 | 原位置 | 来源 / 行为 |
| --- | --- | --- |
| 本轮来袭伤害 | Game+0xbe84 | InitialiseFlares 在 0xda28 起累加攻击者 Tile::GetAttack；此段写回 伤害−护甲，可为 0 或负数（原样保留，不夹到 0） |
| 吸收量 | R10 | min(伤害, 护甲)，有符号比较；即 T020-A 原先由调用者提供的输入 |
| 攻击阶段 | Game+0xb8a8 | ProcessAttack 按 1..7 分支；剩余伤害 ≤0 时置 7（跳过扣血阶段） |
| 9 号敌人伤害 | Game+0x1553c | InitialiseFlares 对 enemy_type 9 额外累加；仅在全部吸收且 >0 时出标签（类型 7、颜色 15、0.5 倍）并清零 |
| 表现 | SimpleLabel::SetNumber / AddSimpleLabel | 剩余 >0 只更新伤害数字；标签固定位置 Game+0x15518；均为事件，不实现 UI |

原生接口：`AttackDamageState{resources, phase, incoming_damage, enemy9_damage}` + `dr_process_attack_armour_absorb`，护甲直接读 resources→match→preview，不复制第二份。

验证 `recovered/verify_attack_absorb.py`：每个场景在同一原版内存上跑两次——单段 `[0x14790,0x147e4)` 对 absorb；连续 `[0x14790,0x1487e)` 对 absorb 后接已恢复的 shield wear，因此 R10 由原指令算出而非假设。入口 R4/R5/R6 按前一段 phase-5 代码留下的值设置（Game+0xbe84、Game+0xbda4、0.5f）。

- 288 组边界（伤害 0/1/4/5/6/40 × 护甲 0/1/5/40 × 9 号值 −1/0/3 × 阶段 5/7 × 是否有 29 号敌人）+ 600 组随机，各比较单段与连续两次，共 1776 次；另 80 个连续步骤在同一棋盘/护甲/随机流上携带状态。
- 比较吸收量、阶段、剩余伤害、9 号值、护甲/UI、六个种子和有序事件；原版 Game 区除允许字段外无其他写入。五个分支点均被执行。
- 错误副本：`>0` 改 `>=0`（恰好吸收完时不进阶段 7）、9 号 `>0` 改 `!=0`（负值误出标签），在隔离开发副本中均 exit 1；真实源码未改。

仍未恢复：phase 1..4 与 phase 5 前半段（含 DoCounterattack 调用点 0x143a4）；0x1487e 之后读 Game+0xbe6c / +0xbe68 的分支（含 AttackSkull 0x149dc、MoveMatchedTiles 0x14a0c 调用点）；phase≠5 时 0x146d8 跳往的 0x14a14 起代码（读 0xbe84 出标签，0x14a9c 处置阶段 7 并读生命 0xbd98）；ProcessVampires 和阶段收尾。以上只是静态阅读到的位置，段边界和阶段语义尚未核实。

下一单元候选：0x14a14 起的剩余伤害/扣血代码。先核实段边界、入口寄存器与阶段号，再同法差分；继续复用 T020-A/B、AttackSkull、MoveMatchedTiles，不重写。

## T020-C：阶段 6 扣血片段（Claude，2026-10-18）

起始提交 929526b（自身上一单元），工作树干净。阶段结构经静态阅读核实：0x1457c 起阶段 5、6 共用一段标签动画，进度到 1 时置完成标志；0x146ce 处阶段 5 完成→置 6 并进入 T020-B 吸收段，阶段 6 完成→0x146d8 跳到 0x14a14。本单元恢复 `[0x14a14,0x14ae4)`（208 字节，SHA-256 `f16f6bd0faef2eb9695078ade4d80ea635d0f5096be81ebfbf690fa9779be19e`），在 attack_shield 模块追加 `dr_process_attack_health_damage`。

| 步骤 | 原位置 | 行为 |
| --- | --- | --- |
| 音效 17、伤害标签 | QueueSound / AddSimpleLabel | 标签类型 2，位置 Game+0xbd30，数值为剩余伤害 Game+0xbe84，颜色 11、0.5 倍 |
| 毒 | Game+0x15540（ResourceState.poison） | poison = max(9 号敌人伤害 Game+0x1553c, poison)，有符号；随后 SetPoison 事件。9 号敌人即施毒者 |
| 9 号标签 | Game+0x15518 | 9 号伤害 >0 时出标签（类型 7、颜色 15）并清零，与 T020-B 全吸收分支同一标签 |
| 吸血 | Game::ProcessVampires 0xdaf8 | **未恢复**：原调用在此处，原生发有序 Vampires 事件由调用方执行。已核对它只写吸血敌人格自身生命（Tile+0xac），不写本段比较的字段 |
| 帮助 | Interface::ShowHelpHealth | UI 事件 |
| 扣血 | Game+0xbd98 / +0x5994 | 阶段置 7；health = health − 剩余伤害（回绕减法），负数归 0；与 UI 生命不同时同步并发 HealthBar |

验证 `recovered/verify_attack_health.py`：
- 单段 1280 组边界（生命 0/1/5/30/100 × UI 同/异 × 剩余伤害 −3..200 八值 × 9 号 −1/0/3/50 × 毒 −1/0/3/10）+ 800 组随机（含任意初始阶段）。
- 连续回合：6 局 × 40 回合在同一棋盘/护甲/生命/毒/随机流上携带状态；每回合按 0x146e0 置阶段 6，先跑原版吸收段，仍为阶段 6 才跑扣血段，原生同序调用 absorb + health。168 回合进入扣血。
- 共 2320 次比较；比较阶段、剩余伤害、9 号值、生命/UI 生命、毒、护甲/UI 和有序事件；原版 Game 区除允许字段外无写入；五个分支点均执行。
- 错误副本：去掉生命下限、交换 Vampires 与 HelpHealth 顺序，均 exit 1；真实源码未改。

仍未恢复：阶段 1..4（含 DoCounterattack 调用点 0x143a4）、阶段 5/6 标签动画本身、0x1487e 之后读 Game+0xbe6c/+0xbe68 的分支（AttackSkull 0x149dc、MoveMatchedTiles 0x14a0c 调用点）、阶段 7 收尾（0x14ae4 起）、ProcessVampires、游戏结束判断。

下一单元候选：ProcessVampires 0xdaf8（130 行，只改吸血敌人格生命，依赖 GetMortalEnemyType/GetAttack/AddHealth/UpdateText），恢复后把本段的 Vampires 事件换成真实调用并重跑连续回合。

## T020-D：ProcessVampires 与 Tile::AddHealth（Claude，2026-10-18）

起始提交 496d9aa。恢复两个**完整原函数**（不是片段），放在 encounters 模块（与 Stab/JumpDown 同属特殊敌人行为）：

| 原函数 | 地址 | 原生函数 | 行为 |
| --- | --- | --- | --- |
| Game::ProcessVampires | 0xdaf8 | dr_process_vampires | 先取玩家职业种族的宿敌类型；按列 x 外层、行 y 内层遍历，未匹配（Tile+0x84=0）、类型 1、敌人 20（吸血鬼）的格子回血；然后出标签 26（数值为攻击力、颜色 34、1.0 倍，位置为格子中心 Tile+0x54）和音效 23 |
| 　回血（宿敌≠20） | 0xdb3c | 同上 | 生命 ≥ max_health（Tile+0xb0）时整格跳过（无标签无音效）；否则 生命 = min(攻击 + 生命, max_health)，UpdateText(0,0,1) |
| 　回血（宿敌=20） | 0xdb4c | 同上 | 调 Tile::AddHealth(攻击)，不封顶 |
| Tile::AddHealth | 0x3dc6c | dr_tile_add_health | 生命 += 值（回绕加法），UpdateText(0,0,1)，若超过 max_health 则抬高 max_health |

攻击力复用已恢复的 dr_get_attack（含毒和种族），宿敌复用 dr_mortal_enemy；为此 build.sh 给 encounters 的链接依赖加入 recovered_rules.cpp（唯一的 build.sh 改动）。EncounterEventKind 末尾追加 Text=7，已有编号不变。

验证 `recovered/verify_vampires.py`：原版完整执行 ProcessVampires、AddHealth、GetMortalEnemyType、Tile::GetAttack，只适配 UpdateText/AddSimpleLabel/QueueSound。
- AddHealth 直接 100 组（含负数、INT_MAX 回绕、抬高上限）。
- ProcessVampires 480 组边界（10 个种族 × 6 种生命/上限关系 × 4 种攻击 × 毒有无，含已匹配、其他敌人、非敌人类型的干扰格）+ 400 组随机棋盘 + 10 局 × 12 次在携带状态上重复回血。
- 共 1100 次比较，3443 次回血；宿敌路径 486 次、封顶路径 2957 次。比较整盘、combat、max_health、生成状态、随机种子和有序事件。
- 错误副本：遍历改为行优先、封顶判断 `>=` 改 `>`，均 exit 1；真实源码未改。

尚未完成：T020-C 扣血段仍以 Vampires 事件把调用交给调用方，测试里该段的原版 ProcessVampires 仍是存根。把两边接成同一状态的连续回合（同时跑真实 ProcessVampires）需要合并 attack_shield 与 encounters 两套测试状态，留作下一单元。

## T020-E：扣血段接真实 ProcessVampires（Claude，2026-10-18）

起始提交 77307b3。没有新增或修改恢复源码，只新增链式测试 `recovered/verify_attack_vampires.py`，把 T020-C 中仍是存根的吸血调用换成真实逻辑：

- 原版侧：ProcessAttack `[0x14a14,0x14ae4)` 中的 ProcessVampires 调用**实际执行**原函数（连同 GetMortalEnemyType、Tile::GetAttack、Tile::AddHealth）；只有标签/文字/音效等表现调用记录为事件。原版内存除阶段、9 号值、生命、UI 生命、毒以及各格生命/上限外不得写入。
- 原生侧：`dr_process_attack_health_damage` 的 Vampires 事件同步调用 `dr_process_vampires`；GenerationState → RefillState → PathState 与 attack_shield 的 ResourceState 共用同一 MatchState、棋盘和 resources。
- 单段 300 组（10 个种族 × 30 块随机棋盘，约 30% 吸血鬼，含已匹配、带毒、满血、超上限）+ 10 局 × 30 回合吸收→扣血携带状态（232 回合进入扣血）；共 600 次比较、5448 个吸血相关事件，宿敌路径 397 次、封顶路径 1419 次。
- 反向检查：把原生侧吸血回调换成空函数后测试失败（各格生命与事件不一致），证明这一步不是空回调也能通过的。

至此 ProcessAttack 内"阶段 5 结束→吸收→护甲损耗；阶段 6 结束→扣血→吸血鬼回血→阶段 7"这一条路径都由恢复源码执行。仍未恢复：阶段 1..4（含 DoCounterattack 0x143a4）、阶段 5/6 标签动画、0x1487e 后读 Game+0xbe6c / +0xbe68 的分支（AttackSkull 0x149dc、MoveMatchedTiles 0x14a0c）、阶段 7 收尾（0x14ae4 起）、游戏结束判断。

## T020-F：敌人削弱片段（Claude，2026-10-18）

起始提交 98a112a。阶段 5 结束路径在护甲损耗（T020-A）之后紧接两个效果：Game+0xbe6c 削弱、Game+0xbe68 全体伤害。本单元只恢复前者：`[0x1487e,0x14938)` 加上它跳转经过的两段循环块 `[0x14b56,0x14b5e)`、`[0x14b9c,0x14bbe)`（合并 SHA-256 `62f2ff31beff7910153a9b26a20fa6882183d41c8394389404dc403220ef13cd`），在 attack_shield 模块追加 `dr_process_attack_weaken(PathState*, weaken, hooks)`。

| 项 | 原位置 | 行为 |
| --- | --- | --- |
| 削弱值 | Game+0xbe6c | ≤0 时直接到 0x14938；ItemUpgrade::GetRandomStat 也读取它（装备/升级属性），写入者未定位，由调用者传入 |
| 遍历 | 列 x 外层、行 y 内层 | 类型 1、attack_flag（Tile+0x86）为 0、攻击（Tile+0xa4）>1 的敌人 |
| 削弱 | Tile+0xa4 | 攻击 = 攻击 − 削弱值（回绕减法），低于 1 则为 1 |
| 表现 | QueueSound / UpdateText / GetAttackLabelPosition / AddSimpleLabel / AddParticles | 第一个命中的敌人前播一次音效 30；每格 UpdateText(1,0,0)、标签 4（数值为削弱值而非实际减少量，颜色 14、1.0 倍）、粒子 3 |

验证 `recovered/verify_attack_weaken.py`：336 组边界（削弱 −1/0/1/2/4/100 × 攻击 −3..101 × 类型 × attack_flag）+ 600 组随机 + 5 局 × 15 次携带状态重复削弱，共 1011 次比较；8307 次削弱、3230 次结果为 1。原版 Game 区除各格攻击外无写入。错误副本：攻击门槛 `<=1` 改 `<1`、每格都播音效，均 exit 1。

仍未恢复：0x14938 起的 Game+0xbe68 全体伤害（清 Game+0xbfa4..0xbfb7 五个计数；对未出手敌人逐个 AttackSkull，击杀 2 号敌人时成就 43；随后 MoveMatchedTiles 并清全部 attack_flag，回到 0x14ae4）。它要接战斗、补位和生成整条链，适合作为单独单元，复用 dr_attack_skull、dr_move_matched_tiles 及 refill_integration 的接线方式。

## T020-G：阶段 7 遮罩淡出（Claude，2026-10-19）

起始提交 43a2c7f。恢复 `[0x14ae4,0x14b56)`（110 字节，SHA-256 `89b6df8a811bdbeb830eb1cf950583ad6f02f2a47d6fe8de282f902ac2d723e2`）为 `dr_process_attack_fade(AttackDamageState*, uint8_t* overlay_alpha, float dt, bool alternate_quad, hooks)`。

| 项 | 原位置 | 行为 |
| --- | --- | --- |
| 进入条件 | Game+0xb8a8 | 阶段 ≠7 直接到 0x14be0 返回 |
| 计时 | Game+0xb92b | 遮罩 Quad（Game+0xb91c）顶点 0 的 alpha 字节，兼作阶段计时器 |
| 公式 | Game+4 帧时间、字面量 0xc4610000 | alpha = 向零截断(float(alpha) + dt × −900)，VMUL/VADD 分别舍入 |
| 切换 | Game+0xb8a8 | 结果 <0 时 alpha 记 0、阶段置 8（阶段 8 在 ProcessAttack 外处理） |
| 表现 | Quad::SetAlpha | 遮罩及（Game+0xbfba ? Game+0xb98c : Game+0xb8ac）两个 Quad 设同一 alpha；原函数只把字节写到四个顶点 |

原生侧把新 alpha 写回 `*overlay_alpha` 并发 SetAlpha 事件（quad 0/1/2）。

验证 `recovered/verify_attack_fade.py`：原版 Quad::SetAlpha **真实执行**，测试核对四个顶点字节都被写成同一值。720 组边界（阶段 6/7/8 × 交替标志 × 10 个 alpha × 12 个 dt，含次正规数、1/900、255/900、256/900）+ 1500 组随机 + 30 局逐帧从 255 淡到阶段 8（357 帧），共 2577 次比较、947 次进入阶段 8。

过程记录：初版源码把常量误读为 −160（把 0xc4610000 看错），测试在 alpha=0、dt=1/240 处即失败，查字面量后改为 −900 才通过——这本身证明了测试对常量敏感。另一个错误副本 `alpha<0` 改 `<=0` 也 exit 1。

有效域：有限且 0≤dt≤10；超出范围时 VCVT 的饱和行为未建模。

## T020-H：InitialiseFlares 与阶段 1 淡入（Claude，2026-10-19）

起始提交 4fa6eba。恢复一个**完整原函数**和一个片段，放在 attack_shield 模块（为调用 dr_get_attack，build.sh 给 attack_shield 的链接依赖加入 recovered_combat.cpp）：

| 原代码 | 地址 | 原生函数 | 行为 |
| --- | --- | --- | --- |
| Game::InitialiseFlares | 0xd9b0（整函数） | dr_initialise_flares | 清零光效计数 Game+0xbd8c、来袭伤害 +0xbe84、9 号敌人伤害 +0x1553c；**行优先**（外层行、内层列）遍历，类型 1、未出手（Tile+0x86=0）、未冻结（Tile+0x255=0）的格子把 Tile::GetAttack 加到来袭伤害，9 号敌人另加到 9 号伤害；除"32 号敌人且状态≠0"外，每个这样的格子两只眼各加一个光效（类型 0、白色） |
| ProcessAttack 阶段 1 | [0x14126,0x141c6) | dr_process_attack_fade_in | alpha = 向零截断(alpha + dt×800)；>200 时音效 14、阶段 2、Game+0xbd90=0 与 +0xbd94=1.0f、调用 InitialiseFlares、alpha 定为 200；随后遮罩 SetAlpha，四个界面阴影（生命/XP/UP/金币）设 −1 |

这样 T020-B 的来袭伤害与 9 号伤害有了已恢复的来源，阶段 1→2 的切换也由恢复源码执行。

**登记修正**：Codex 的调用登记原把 InitialiseFlares 归入"表现/成就边界"。实际上它计算来袭伤害，属于玩法逻辑，现已改为 `T020-H:dr_initialise_flares`。

边界：Tile::GetEyePosition、Game::AddFlare 为表现调用。原 AddFlare 还会把光效加入列表并维护 Game+0xbd8c 计数（阶段 2/3 用它遍历光效），原生侧只清零计数，追加和计数要由调用方负责，后续恢复阶段 2/3 时必须接上。

验证 `recovered/verify_attack_flares.py`：InitialiseFlares 整函数原版执行（含 Tile::GetAttack），阶段 1 片段执行时其中的 InitialiseFlares 也是原函数，Quad::SetAlpha 真实执行。
- InitialiseFlares：540 组边界（种族 × 敌人 0/9/32 × 状态 × 攻击 × 毒 × 出手/冻结）+ 500 组随机。
- 阶段 1：180 组边界（阶段 0/1/2 × alpha × 10 个 dt）+ 800 组随机 + 30 局逐帧从 0 淡入到阶段 2（408 帧）。
- 共 2428 次比较，572 次进入阶段 2，35990 个光效事件；比较来袭伤害、9 号伤害、计数、阶段、抖动字段、alpha 与有序事件，并要求棋盘与 combat 不变。
- 错误副本：列优先遍历、去掉冻结判断、`>200` 改 `>=200`，均 exit 1。

## T020-I：全体伤害片段与共享状态全链测试（Claude，2026-10-19）

起始提交 536b68a。恢复 `[0x14938,0x14a14)` 加两段块 `[0x14b5e,0x14b9c)`、`[0x14bbe,0x14be0)`（合并 SHA-256 `d7d4cfb8c23a69b86061118978b789f6e416a9ea3f9cbcba7705bffaec168399`）为 `dr_process_attack_damage_all(PathState*, amount, AttackAllHooks*)`：

| 步骤 | 原位置 | 行为 |
| --- | --- | --- |
| 进入 | Game+0xbe68 | ≤0 时直接到 0x14ae4；写入者未定位（与 +0xbe6c 相邻，疑为装备/升级属性），由调用者传入 |
| 清计数 | Game+0xbfa4..0xbfb7 | MatchState.matched_counts[0..4] 清零 |
| 逐个攻击 | 列优先 | 类型 1、attack_flag=0 的格子：第一个之前音效 3；标签 5（数值、颜色 16、1.0 倍，位置为格子中心）；先记下敌人类型，再 AttackSkull(amount, effects=false)；返回击杀且原类型为 2 时成就 43（100.0） |
| 收尾 | 0x14a0c、0x14b66 | MoveMatchedTiles；然后清全部 36 格 attack_flag，回到 0x14ae4 |

AttackSkull 与 MoveMatchedTiles 是同步玩法依赖，通过回调接入：
- 新增集成适配器 `dr_path_attack_skull`（recovered_path.cpp）：复用 dr_commit_path 的 RoundState 视图，对单格执行已恢复的 dr_attack_skull。**它不是新恢复的原函数**，只是让单次攻击能独立调用。
- MoveMatchedTiles 接 `dr_move_matched_tiles`，其中的 Randomise / Stab / JumpDown 照旧接到生成与特殊敌人模块。

验证 `recovered/verify_attack_all.py`，建立在 refill_integration 的全量测试类上：
- 原版侧执行该片段时，其中的 AttackSkull 与 MoveMatchedTiles 都是原函数：前者含 MatchTile、代币、奖励；后者含 RandomiseTile、生成、Stab、JumpDown。测试只在进出每个被调函数时切换已有子系统钩子的开关。
- 原生侧在同一共享状态上调用恢复源码。比较 path 状态（战斗、combat、计数、代币、动画）、整盘补位/生成/特殊敌人状态、随机流和全部有序事件。
- 40 组边界（数值 −1/0/1/3/100）+ 120 组随机棋盘 + 6 局 × 4 次连续攻击；每次攻击后逐帧下落直到落定（246 帧，原版 Game::Process 下落片段对原生）。共 430 次比较，2367 次 AttackSkull，699 次击杀。
- 错误副本：行优先、不清 attack_flag、跳过 MoveMatchedTiles（空回调），均 exit 1。

**顺带修正的测试框架近似**：`verify_motion.py` 原生侧在代币位置覆盖时，取的是用例初始配置里的格子中心。原版传的是 `&tile->center`，即当前中心。格子被补位移动后两者会差一行。本单元在不下落、连续攻击时暴露了这一点。已改为读当前状态的格子中心，全部既有测试仍通过（见 VALIDATION.md）。

仍未恢复：阶段 2..4（光效动画、DoCounterattack 0x11214 的调用点 0x143a4）、阶段 5/6 标签动画、Game+0xbe68 / +0xbe6c 的来源。DoCounterattack 同样调用 AttackSkull、MoveMatchedTiles、GetAttack，可直接复用本单元的回调接线与测试类。

## T020-J：DoCounterattack（Claude，2026-10-19）

起始提交 72bf218。恢复**完整原函数** Game::DoCounterattack 0x11214（296 字节，SHA-256 `e9cacdab40fcf7c559ef54503627ab92aac13b8499d77b82e7fe0a05ed50ad1b`）为 `dr_do_counterattack(PathState*, AttackAllHooks*)`，与全体伤害共用回调接线：

- 清 matched_counts[0..4]。
- 列优先遍历类型 1、attack_flag=0 的格子：先出标签 2（数值为该格 Tile::GetAttack、颜色 11、0.5 倍，位置是 Game+0xb400 静止位置表，不是当前中心）；再用该格自己的 GetAttack 作为伤害对它 AttackSkull。effects 参数传的是 attack_flag 字节，此时恒为 0。返回值不使用。
- MoveMatchedTiles，然后清全部 attack_flag。
- 阶段 3 的 0x143a4 处调用它，那段调度尚未恢复。

至此 ProcessAttack 的直接调用里，所有玩法函数都有了恢复实现（AttackSkull、MoveMatchedTiles、GetEnemyCount、随机数、InitialiseFlares、ProcessVampires、DoCounterattack）。调用登记中 DoCounterattack 已改为 `T020-J:dr_do_counterattack`。

验证 `recovered/verify_counterattack.py`：原版完整执行 DoCounterattack，其中的 GetAttack、AttackSkull（含 MatchTile、代币）、MoveMatchedTiles（含生成、Stab、JumpDown）都是原函数，测试类与 T020-I 相同（本单元把 verify_attack_all.py 的地址范围、入口、停止点和标签位置换算改为可覆盖的类属性，原测试结果不变）。
- 150 组随机棋盘 + 30 组种族 × 毒（覆盖 GetAttack 的种族 1 带毒减半）+ 6 局 × 4 次连续反击，每次反击后逐帧下落至落定（382 帧）。
- 共 586 次比较，2863 次 AttackSkull，960 次击杀。
- 错误副本：行优先、伤害改用基础攻击力（绕过 GetAttack），均 exit 1。

## T020-K：阶段 2..4 共享计时、光效动画与阶段 3（Claude，2026-10-19）

起始提交 3b0ce5f。恢复 `[0x141c6,0x143ca)` 为 `dr_process_attack_flares(AttackDamageState*, AttackAnimation*, dt, AttackAnimHooks*)`。新增 `AttackAnimation` 结构保存原先没有归属的动画字段：标签进度 Game+0xbd58、标签 y 坐标 +0xbd54、伤害标签 alpha +0xbd38、毒标签 alpha +0x15520、光效数量 +0xbd8c、反击标志 +0xbfba。两个计时器是 MatchState 已有的 shake_progress_bd90 / shake_scale_bd94（原名沿用；它们在攻击动画中被复用为计时器）。

| 步骤 | 行为 |
| --- | --- |
| 进入 | 阶段不是 2/3/4 时直接到 0x143ca |
| 计时 | A += dt；B += dt×(−4.5) |
| B < 0.5 | 阶段 2 时：有反击标志则音效 27、阶段 3、进度 0；否则阶段 4、进度 0，伤害标签显示来袭伤害（位置 (0.5, y)）、伤害 alpha=1，毒标签显示 9 号伤害（位置 (0.5, y+0.05)）、毒 alpha=1。随后 B<0 时 B=0、光效数=0，记"光效结束" |
| 光效 | 每个光效（Game+0xbd80 数组，步长 0x70）：alpha = u8(u32(B×255))，+0x64/+0x68 = A |
| 阶段 3 | 进度 += 3dt；>1 时进度=1，且本帧光效结束时置阶段 7 并调用 DoCounterattack；最后 Quad 0xb98c 的 alpha = u8(u32(进度×255)) |

VCVT.U32.F32 的语义按 ARM 实现：向零截断，负数与 NaN 得 0，过大饱和。阶段 2 刚切到 3 的同一帧也会执行阶段 3 块，与原版一致。

验证 `recovered/verify_attack_flare_phases.py`，继承 T020-J 的全链测试类：
- 原版侧光效数组放在模拟内存（Game+0xbd80 指向它），Quad::SetAlpha 真实执行，结束后读回每个光效四个顶点的 alpha 和 +0x64/+0x68。阶段 3 结束时原版 DoCounterattack 及其 AttackSkull、MoveMatchedTiles 全部真实执行；原生侧回调 dr_do_counterattack。
- 420 组边界（阶段 1..5 × B 六个值 × 反击标志 × 7 个 dt）+ 300 组随机 + 24 局从阶段 2（A=0、B=1）逐帧推进到阶段 4 或 7（269 帧）。共 989 次比较，其中 65 次触发完整反击链。
- 错误副本：`>1` 改 `>=1`、光效 alpha 改用计时 A、不等光效结束就反击，均 exit 1。
- 调试中发现并修正一个测试自身的问题：判断"调用来自本段"时用了 `lr < END`，而本段最后一条 bl 的返回地址正好是 END，导致漏记事件。已改为 `ENTRY < lr <= END`。之前各单元的测试没有按 lr 区间过滤结尾调用，或最后一个调用不在区间末尾，因此不受影响。

边界：SimpleLabel::SetNumber/SetPosition 与 QueueSound 为表现调用；光效列表由 AddFlare 建立，测试直接布置；未模拟 NEON 对次正规数的冲零。阶段 4 在 0x143ca 之后的部分是下一单元。

## T020-L：阶段 4（Claude，2026-10-19）

起始提交 b9d8ec3。恢复 `[0x143ca,0x1457c)` 为 `dr_process_attack_phase4(AttackDamageState*, AttackAnimation*, flares_done, dt, hooks)`。原版用栈上 `[sp,#0x2c]` 把"本帧光效刚结束"从共享部分传到阶段 4，因此 `dr_process_attack_flares` 改为返回这个标志（原为 void；T020-K 测试照常通过）。AttackAnimation 末尾追加阶段 5/6 标签运动参数 bd30..bd7c；含义要等阶段 5/6 动画恢复后才能确认，暂按 Game 偏移命名。

| 步骤 | 行为 |
| --- | --- |
| 进入 | 阶段 ≠4 时到 0x1457c |
| 进度 | 进度 += 8dt；>1 时进度=1，且本帧光效刚结束时继续下面两行 |
| 护甲 >0 | 阶段 5；bd60=1.290625（0x3fa53333）、bd5c=0.5、bd78=0.8；Rand(0.4, 1.0, 流 0) → bd7c |
| 否则 | 阶段 6；bd60=1.29375（0x3fa5999a）、bd5c=0.8625、bd78=0.2；Rand(0.4, 0.8, 流 0) → bd7c |
| 公共 | bd68=bd34、bd64=bd30、bd6c=0、bd70=1；HelpMenu::Initialise(bd30, bd34, 0, 0, 16) |
| 每帧 | bd74 = 伤害标签 alpha（bd38）；Quad 0xb8ac 与两个标签的 alpha = u8(u32(进度×255)) |

随机数复用已恢复的 dr_random_float，消耗共享六流中的流 0。

验证 `recovered/verify_attack_phase4.py`：原版从 0x141c6 连续执行到 0x1457c，让栈上标志自然传递；原生侧依次调用 flares 与 phase4。Rand(float) 和 Quad::SetAlpha 是原函数，到达时 DoCounterattack 也是完整原版链。
- 320 组边界（护甲 −1/0/1/7 × 计时 B 四值 × 进度五值 × 四个 dt）+ 300 组随机 + 24 局从阶段 2 逐帧推进到阶段 5 或 6（236 帧）。共 856 次比较，阶段 5、6 各进入 82 次，205 次原版 Rand(float)。
- 错误副本：护甲 `>=0`、随机流改 1、bd64/bd68 来源互换，均 exit 1。

## T020-M：阶段 5/6 标签运动（Claude，2026-10-19）

起始提交 6b049e7。恢复 `[0x1457c,0x146ce)` 为 `dr_process_attack_label_motion(AttackDamageState*, AttackAnimation*, dt, hooks)`，返回"本帧运动完成"。完成时原版继续执行 0x146ce（下一单元），否则跳到 0x14ae4。

| 步骤 | 行为 |
| --- | --- |
| 进入 | 阶段不是 5/6 时跳到 0x14ae4 |
| 速度与进度 | bd70 += 20dt；bd6c += bd70×dt；>1 时为 1，记完成 |
| 位置 | Interpolate(GLfloat2 (bd64,bd68), (bd5c,bd60), t) = (1−t)·起点 + t·终点（逐分量，乘法分别舍入后相加）；弧线 = (0.25 − Sqr(0.5−t))×bd7c，阶段 5 从 x 减、阶段 6 从 y 减；标签 0 设到该点，标签 1 设到 (x, y+0.05) |
| alpha | 伤害标签 alpha（bd38）= Interpolate(float bd78, bd74, powf(t,5)) = bd78·p + (1−p)·bd74，并复制到毒标签 alpha（+0x15520） |

注意：Interpolate 的标量版与二维版插值方向相反（标量版第一个参数乘 t），两种都已按原指令逐条核对。由此可以看出 bd64/bd68 是标签起点，bd5c/bd60 是终点，bd7c 是弧高，bd74/bd78 是起止 alpha，bd70/bd6c 是速度与进度。字段名暂仍沿用偏移。

验证 `recovered/verify_attack_label_motion.py`：原版从 0x141c6 连续执行到 0x146ce 或 0x14ae4，同一帧内依次经过共享计时、阶段 4、阶段 5/6；原生侧依次调用三个函数，用返回值选择同一出口。Interpolate 两个重载和 Sqr 作为原函数执行。平台 powf 存根由测试用本机 C 库 powf 应答，原生实现也调用同一个 powf；这是平台库边界，原 iOS 设备上的 powf 末位可能不同。
- 320 组边界（阶段 4..7 × 进度五值 × 速度四值 × 四个 dt）+ 400 组随机 + 24 局从阶段 4 推进到运动完成（281 帧）。共 1001 次比较，296 次完成。
- 错误副本：标量插值方向反转、阶段 5 弧线加到 y、`>1` 改 `>=1`，均 exit 1。
- 基础测试类 verify_attack_all.py 增加可选的多个停止点（extra_stops），默认为空，原测试不变。
