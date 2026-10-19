# 当前状态

更新：2026-10-19（America/Los_Angeles）。维护者：Claude（T020-H）。当前阶段：Codex → Claude → Codex → Claude 接力；敌人攻击中阶段 1 淡入+InitialiseFlares、阶段 5 结束（吸收+损耗+削弱）、阶段 6 结束（扣血+吸血鬼）、阶段 7 淡出已恢复；Gemini 尚未接入。

## 已核实

- 实际工作区为本 docs/ 的上级目录；创建前无 Git，无已有分支、提交、暂存修改或远端。源码基线提交 `bd9bbd3` 保存了原有 78 个源码/文档/脚本路径（含新增忽略规则）。
- 原有 7,282 个文件、1,207,443,199 字节已记录在本地 `.relay/bootstrap-before.json`，并在验证后重新逐项核对哈希。
- recovered/ 当前存在 20 个 `recovered_*.cpp` 模块、15 个头文件、28 个 verify 脚本、两个独立源码示例。新增 attack_shield 是局部恢复，不计作完整 ProcessAttack；补位、生成、JumpDown/Stab 等既有逻辑继续复用。
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

活动任务与未提交现场实时以 `./scripts/relay.sh check`、`git diff` 和 `.relay/active/owner.json` 为准；文档中的提交号只作里程碑，不用手工维护“永远等于 HEAD”的循环字段。

## 尚未完成及下一步

完整 ProcessAttack、EndOfTurn、输入阶段门槛、新局初始化/存档及整个 Game::Process 尚未形成完整可玩循环；现代 iOS UI、高清、多语言和教程未验收。现有 IPA/宿主为兼容路线，不能当作新源码游戏。

继续 T020 的下一单元，两个候选：(1) 阶段 2..4（0x141c6 起）：光效动画（以 Game+0xbd8c 计数遍历光效，需先确认 AddFlare 的列表结构）、阶段 4 中调用 DoCounterattack 0x143a4（未恢复的玩法函数），再到阶段 5 标签动画；(2) 0x14938 起的 Game+0xbe68 全体伤害——清 Game+0xbfa4..0xbfb7，列优先对未出手敌人 AttackSkull（击杀 2 号敌人成就 43），随后 MoveMatchedTiles，0x14b66 循环清全部 attack_flag，回到 0x14ae4；需要复用 dr_attack_skull（经 recovered_path.cpp 适配器）、dr_move_matched_tiles 及补位/生成接线。不重写已恢复部分。额度耗尽后由用户停止当前工具，再用同一目录让下一 AI 接手。简明操作见 用户操作.md。
