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
| T040 | 待 T030 | 恢复输入阻塞门槛、新局初始化与完整回合调度 | ProcessInput 0x16638、InitNewGame 0x15c50、Game::Process；同一棋盘可进入下一回合且不执行旧程序 |
| T050 | 待 T040，可独立做标注原型 | 现代 iOS 全屏界面、资源键、中英文和教程 | 实机/模拟器交互验收；原型明确标注，不能替代真实引擎 |

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

认领记录模板：`Txxx / 工具 / 起始 HEAD / 继承差异 / 目标 / 文件 / 验收命令 / 结果路径 / 下一步`。详细活动现场存于 `.relay/active/owner.json`，持久事实随原子提交更新这里和 PROJECT_STATE.md。
