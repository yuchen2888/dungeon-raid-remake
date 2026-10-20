# 本轮验证记录

日期：2026-10-17（America/Los_Angeles）。以下均为本轮实际执行；历史报告未覆盖。

## 执行入口

`./scripts/relay.sh verify --full` 返回 0。19 模块完整重编译、两个源码示例与 20 个既有验证脚本共 23 步全部通过。来源输入哈希在运行前后相同。

- 本地完整结果：`/Users/yuchen/.codex/.chatgpt-projects/g-p-6ad134357ce081919b8abd0e80cc78bd/dungeon-raid-independent/.relay/runs/20261018T065100.380122Z/result.json`
- 新报告和新库：`/Users/yuchen/.codex/.chatgpt-projects/g-p-6ad134357ce081919b8abd0e80cc78bd/dungeon-raid-independent/.relay/runs/20261018T065100.380122Z/work/recovered/`
- 结构化摘要：`docs/VALIDATION.json`
- 输入指纹：`b3586780dcd6890c5fca4f3f1cb168341f938988db0d75d239f5302eeb5c0d00`

| 步骤 | 结果 | 秒 |
| --- | --- | --- |
| build | passed / exit 0 | 10.86 |
| stroke_demo | passed / exit 0 | 0.35 |
| rewards_demo | passed / exit 0 | 1.77 |
| verify_battle | passed / exit 0 | 1.47 |
| verify_encounters | passed / exit 0 | 39.55 |
| verify_generation | passed / exit 0 | 19.61 |
| verify_input | passed / exit 0 | 0.66 |
| verify_match | passed / exit 0 | 5.63 |
| verify_motion | passed / exit 0 | 5.44 |
| verify_original | passed / exit 0 | 0.96 |
| verify_path | passed / exit 0 | 32.13 |
| verify_preview | passed / exit 0 | 3.26 |
| verify_progression | passed / exit 0 | 0.29 |
| verify_random | passed / exit 0 | 0.4 |
| verify_refill | passed / exit 0 | 7.08 |
| verify_refill_integration | passed / exit 0 | 5.83 |
| verify_resources | passed / exit 0 | 5.89 |
| verify_round | passed / exit 0 | 5.91 |
| verify_rules | passed / exit 0 | 1.28 |
| verify_rune | passed / exit 0 | 3.76 |
| verify_selection | passed / exit 0 | 3.83 |
| verify_stroke | passed / exit 0 | 2.14 |
| verify_tokens | passed / exit 0 | 8.62 |

## 关键复现及边界

- build：19 个 macOS 双架构动态库、19 个 iPhone arm64 对象及静态库；使用已安装 macOS SDK 27.0 / iPhone SDK 27.1，编译选项继承原 build.sh。不是 App 构建验收。
- refill：522 棋盘、108 定位、2705 下落步；隔离测试的生成/Stab 是明确回调。
- generation：3164 场景；真实原版生成、晋升、数值与随机指令对照。
- encounters：1992 场景，包含 1296 swap、36 jump、360 stab、300 move；完整敌人调度未验证。
- refill_integration：20 连续手势、1550 操作/帧、280 奖励及新格；真实补位、生成与特殊动作接通。没有重开下一回合输入。
- rewards_demo：周边 8 格加圈内 1 格消除，26 帧后奖励和落格结束，金币 0→18，补入 9 格，额外推进不重复入账。示例不执行原版程序，无界面，停在完整敌人阶段之前。
- progression：本轮用原有 original-progression-verification.json 做原生 fixture 重放；不是本轮重新执行原版职业存档采集。其他测试以各报告的 original/boundaries/scope 为准。
- 不累加重叠场景，不将这些通过结果写成完整游戏、真实触摸或现代 iOS 试玩通过。

## 接力安全验证

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_relay.py -v`：4 项通过。覆盖脏工作树/暂存/二进制未跟踪文件保留、锁冲突/错误释放拒绝、显式接管保留旧 owner、check 零文件副作用，以及三种启动参数/同目录（本地替身程序）。
本地日志 `.relay/relay-safety-tests.log`。启动测试曾遇 macOS /var 与 /private/var 的路径别名，已改为解析后比较并复验通过。没有真实启动 Claude/Gemini 或使用模型额度。

## 原文件保护与交接演练

原有 7282 个文件逐项检查：缺失/内容变化 0，含源码、旧报告、大 fixture、原始程序、素材、构建产物和第三方依赖。完整基线 `.relay/bootstrap-before.json`；结果 `.relay/preservation-check.json`。根外 ZIP 与旧研究副本未修改。

真实项目的只读交接演练结果记录在本节末尾；它不等同于另一模型开发并提交。

已在真实项目执行 `./scripts/relay.sh check`（保留本轮暂存中的新增文件与活动任务），退出码 0。比较运行前后 7654 个文件的内容哈希：变化/增删 0，Git 暂存和未暂存状态保持。输出能定位当前源码、验证结果和下一项 T010。日志 `.relay/read-only-handoff.log`，结构结果 `.relay/read-only-handoff.json`。

## 2026-10-18 T010 接力验证（Claude）

源码未改动；只新增只读登记脚本和文档。

- `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/t010_registry.py` → exit 0，17 函数，problems 0，未建模调用 0；`--check` → exit 0（matches true）。把一个 size 改成错值的副本做 `--check --out` → exit 1，确认比较有效。
- `./scripts/relay.sh verify`（默认集：build、两个示例、verify_refill/generation/encounters/refill_integration）→ exit 0，结果 `.relay/runs/20261018T070600.453747Z/result.json`；输入指纹 `b3586780…5c0d00`，与 2026-10-17 full run 相同，inputs_unchanged true。四组计数复现 522/108/2705、3164、1992、20/1550/280。
- `python3 -m unittest discover -s tests -p test_relay.py` → 4 项通过。
- 未运行 `verify --full`（其余 16 个 verify 的输入未变化，指纹相同）。

## 2026-10-18 T010 交接复核（Codex）

从干净的 `8d9604a` 接手。本轮重跑 `python3 -I scripts/t010_registry.py --check`，修正登记说明并重新生成 JSON 后再次通过（matches true、problems 0、17 函数）。独立逐字节核对全部 17 个完整函数和 1 个片段，与原可执行文件和反汇编一致；损坏登记副本被 --check 拒绝（exit 1）。原有 7282 文件再次核对无变化。

修正 UpdateCountdown 为 UI 显示边界、可执行文件整文件哈希描述和直接具名调用的统计范围。现有两轮游戏验证的输入指纹与当前源码一致，本次未重复运行构建或游戏测试。详细证据和内联替代核对见 T010_REVIEW.md，本地独立核对结果 `.relay/reviews/T010-codex/independent-check.json`，最终登记检查日志 `.relay/reviews/T010-codex/final-check.log`。

## 2026-10-18 T020-A：护甲损耗局部（Codex）

`./scripts/relay.sh verify --full` 返回 0，目录 `/Users/yuchen/.codex/.chatgpt-projects/g-p-6ad134357ce081919b8abd0e80cc78bd/dungeon-raid-independent/.relay/runs/20261018T072018.132343Z`；20 模块构建、两个示例、21 个 verify 共 24 步全部通过，运行前后输入指纹一致。新分支 810 边界场景 + 700 随机场景 + 100 连续步骤一致，观察 23417 个真实 RNG 调用；原片段、GetEnemyCount 与原 RNG 执行，仅适配 floorf 和护甲/音效表现。错误阈值 `<`→`<=` 的隔离副本被拒绝（exit 1）。

4 项接力安全测试通过；T020 调用登记 --check 通过。原有 7282 文件中仅 build.sh 因增加模块有必要修改，其余原文件哈希不变。完整结果见 T020_VALIDATION.json，范围和下一单元见 T020_ATTACK.md。完整 ProcessAttack / 敌人回合尚未完成。

## 2026-10-18 T020-B：护甲吸收片段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：20 模块 macOS 双架构 / iPhone ARM64 构建、2 个示例、22 个 verify 脚本共 25 步全部通过。运行目录 `.relay/runs/20261018T073147.680153Z`，输入指纹 `68591a33…4478e3`（源码已变，旧指纹不再代表当前源码），inputs_unchanged true。
- 新 verify_attack_absorb：1856 次比较（288 边界 + 600 随机场景，各单段 / 连续链两次 = 1776，加 80 连续步骤），731 次进入阶段 7，连续链中 12361 次真实 RandI；单段字节 SHA-256 `de77208b…98cd98`。T020-A verify_attack_shield 仍 1610 场景通过。
- 错误副本（隔离开发副本，非 .relay/runs）：吸收判断 `>0`→`>=0`、9 号敌人 `>0`→`!=0`，均 exit 1 并在 0x147e4 处出现阶段/标签差异；真实源码与副本对比一致。
- `python3 -m unittest discover -s tests -p test_relay.py` → 4 项通过；`t010_registry.py --check`、`t020_attack_audit.py --check` 均 matches true。
- 边界：入口 R4/R5/R6 由测试按前一段代码设置；标签/音效/护甲 UI 为事件；不是完整 ProcessAttack 或可玩回合。

## 2026-10-18 T020-C：阶段 6 扣血片段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、23 个 verify 脚本共 26 步通过。运行目录 `.relay/runs/20261018T151443.228996Z`，输入指纹 `2467ca02…14f9ed`，inputs_unchanged true。
- 新 verify_attack_health：2320 次比较（1280 边界 + 800 随机单段 + 6 局 × 40 回合吸收→扣血连续链，其中 168 回合进入扣血），单段字节 SHA-256 `f16f6bd0…79be19e`。T020-A/B 的测试同次通过。
- 错误副本（隔离开发副本）：去掉生命下限、交换 Vampires/HelpHealth 顺序，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；`t010_registry.py --check`、`t020_attack_audit.py --check` 均 matches true。
- 边界：ProcessVampires 为有序回调（未恢复）；阶段 6 由测试按 0x146e0 设置；无阶段动画、调度或游戏结束判断。

## 2026-10-18 T020-D：ProcessVampires / Tile::AddHealth（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建（encounters 新增 rules 依赖）、2 个示例、24 个 verify 脚本共 27 步通过。运行目录 `.relay/runs/20261018T152206.412664Z`，输入指纹 `e4cb980a…d6203`，与提交时源码一致。encounters 原 1992 场景仍通过。
- 新 verify_vampires：1100 次比较（AddHealth 100、边界 480、随机 400、重复回合 120），3443 次回血；宿敌不封顶路径 486 次、封顶路径 2957 次。
- 错误副本（隔离开发副本）：行优先遍历、封顶判断 `>`，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；`t010_registry.py --check`、`t020_attack_audit.py --check` 均 matches true。
- 注意：本次第一次后台启动因相对路径从 scripts/ 目录解析失败（exit 127，未运行任何测试），已用绝对路径重跑；上面结果来自重跑。

## 2026-10-18 T020-E：扣血段接真实 ProcessVampires（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、25 个 verify 脚本共 28 步通过。运行目录 `.relay/runs/20261018T152729.642962Z`，输入指纹 `dc6d62a9…2545ed`，与提交时源码一致。
- 新 verify_attack_vampires：600 次比较（单段 300 + 携带状态回合 300，其中 232 回合进入扣血），5448 个吸血相关事件；宿敌路径 397 次、封顶路径 1419 次。原版侧 ProcessVampires 真实执行。
- 反向检查（开发副本，运行时把原生吸血回调换成空函数）：测试失败，差异在各格生命与事件。
- 无恢复源码改动；接力单测与两份登记 --check 同前通过。

## 2026-10-18 T020-F：敌人削弱片段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、26 个 verify 脚本共 29 步通过。运行目录 `.relay/runs/20261018T153217.706047Z`，输入指纹 `4d3f45ca…c9be77`，与提交时源码一致。
- 新 verify_attack_weaken：1011 次比较（边界 336、随机 600、重复 75），8307 次削弱、3230 次结果为 1；合并字节 SHA-256 `62f2ff31…ef13cd`。
- 错误副本（隔离开发副本）：攻击门槛 `<1`、每格都播音效，均 exit 1；开发副本已复原，真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-G：阶段 7 遮罩淡出（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、27 个 verify 脚本共 30 步通过。运行目录 `.relay/runs/20261019T070907.639964Z`，输入指纹 `ff71ce19…5d6b42`，与提交时源码一致。
- 新 verify_attack_fade：2577 次比较（边界 720、随机 1500、逐帧 357），947 次进入阶段 8；字节 SHA-256 `89b6df8a…2723e2`。原版 Quad::SetAlpha 真实执行。
- 错误版本：初版常量 −160（误读）在开发副本中失败；`alpha<=0` 副本 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-H：InitialiseFlares 与阶段 1（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建（attack_shield 新增 combat 依赖）、2 个示例、28 个 verify 脚本共 31 步通过。运行目录 `.relay/runs/20261019T071544.763865Z`，输入指纹 `0f9ffd45…9fa442`，与提交时源码一致。
- 新 verify_attack_flares：2428 次比较，572 次进入阶段 2，35990 个光效事件；InitialiseFlares 字节 SHA-256 `14ee6460…86c5d7`，阶段 1 片段 `cf758d93…1214cd`。
- 错误副本（隔离开发副本）：列优先、去掉冻结判断、`>=200`，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-I：全体伤害与共享状态全链（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、29 个 verify 脚本共 32 步通过。运行目录 `.relay/runs/20261019T074616.568344Z`，输入指纹 `37c3e345…0d5c79`，与提交时源码一致。
- 新 verify_attack_all：430 次比较（边界 40、随机 120、连续攻击 24、下落帧 246），原版与原生各 2367 次 AttackSkull、699 次击杀；合并字节 SHA-256 `d7d4cfb8…168399`。
- verify_motion.py 修正（代币位置覆盖取当前格子中心）后，既有测试数字不变：motion 923 初始化 / 20627 帧、path 517 场景 / 973 步、refill_integration 20 手势 / 1550 步 / 280 奖励。
- 错误副本（隔离开发副本）：行优先、不清 attack_flag、跳过 MoveMatchedTiles，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-J：DoCounterattack（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、30 个 verify 脚本共 33 步通过。运行目录 `.relay/runs/20261019T075510.798248Z`，输入指纹 `fba35d3b…129f76`，与提交时源码一致。
- 新 verify_counterattack：586 次比较（随机 150、种族/毒 30、连续反击 24、下落帧 382），2863 次 AttackSkull、960 次击杀；字节 SHA-256 `e9cacdab…50ad1b`。参数化后的 verify_attack_all 仍为 430 次比较、2367 次攻击、699 次击杀。
- 错误副本（隔离开发副本）：行优先、改用基础攻击力，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-K：阶段 2..4 共享部分（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、31 个 verify 脚本共 34 步通过。运行目录 `.relay/runs/20261019T080548.798273Z`，输入指纹 `3b948cef…502520`，与提交时源码一致。
- 新 verify_attack_flare_phases：989 次比较（边界 420、随机 300、逐帧 269），65 次完整反击链；片段字节 SHA-256 `10d33f17…a09534`。
- 错误副本（隔离开发副本）：`>=1`、光效 alpha 用计时 A、不等光效结束就反击，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-L：阶段 4（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、32 个 verify 脚本共 35 步通过。运行目录 `.relay/runs/20261019T081607.563943Z`，输入指纹 `8f572953…3cab4e`，与提交时源码一致。
- 新 verify_attack_phase4：856 次比较（边界 320、随机 300、逐帧 236），阶段 5、6 各进入 82 次，205 次原版 Rand(float)；片段字节 SHA-256 `36dc7ee2…fafc6c4`。T020-K 测试在 flares 改返回 bool 后照常通过。
- 错误副本（隔离开发副本）：护甲 `>=0`、随机流 1、bd64/bd68 互换，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-M：阶段 5/6 标签运动（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、33 个 verify 脚本共 36 步通过。运行目录 `.relay/runs/20261019T082459.918587Z`，输入指纹 `f7a8d1c0…94bcb9`，与提交时源码一致。
- 新 verify_attack_label_motion：1001 次比较（边界 320、随机 400、逐帧 281），296 次运动完成；片段字节 SHA-256 `8fca30c0…ffe599e4`。verify_attack_all 加入可选多停止点后，依赖它的测试数字不变。
- 错误副本（隔离开发副本）：标量插值方向反、阶段 5 弧线加到 y、`>=1`，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-N：阶段 5 完成准备块（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、34 个 verify 脚本共 37 步通过。运行目录 `.relay/runs/20261019T083259.063272Z`，输入指纹 `eb9f3f48…32dc74`，与提交时源码一致。
- 新 verify_attack_phase5_done：653 次比较，三个出口 0x14790 / 0x14a14 / 0x14ae4 分别 199 / 103 / 351 次；片段字节 SHA-256 `ce170d81…a1765159e`。
- 错误副本（隔离开发副本）：不取最小值、bd74 取错、随机上限 1.0，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T020-O：完整 ProcessAttack 整函数逐帧差分（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、35 个 verify 脚本共 38 步通过。运行目录 `.relay/runs/20261019T084730.273863Z`，输入指纹 `e8f55e42…9c46dc`，与提交时源码一致。
- 新 verify_process_attack（30.5 秒）：24 局 × 2 次完整攻击 = 48 次、1985 帧（阶段 1..8 帧数 507/192/295/131/96/301/415/48）、攻击间下落 458 帧、22 次完整反击链。每帧从原版入口 0x14118 调整函数。
- 编排错误副本（隔离开发副本）：削弱/全体伤害对调、阶段 1 放在共享块之后、跳过完成准备块，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；两份登记 --check 均 matches true。

## 2026-10-19 T030-B：MimicDefence / Resurrect / ProcessCripples（Claude）

- `./scripts/relay.sh verify --full` → exit 0：21 模块（新增 turn）macOS 双架构 / iPhone ARM64 构建、2 个示例、36 个 verify 脚本共 39 步通过。运行目录 `.relay/runs/20261019T090215.018187Z`，输入指纹 `98cfd5c5…a1a811`，与提交时源码一致。
- 新 verify_turn_small：420 次比较（MimicDefence 240、Resurrect 60、ProcessCripples 120），64 个骷髅经原版 MatchTile 消灭。
- 错误副本（隔离开发副本）：去掉种族判断、`>=` 改 `>`、列优先，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；T030 登记 --check matches true（未恢复数 27→24）。

## 2026-10-19 T030-C / T030-D 与测试去墙钟超时（Claude）

- 先前一次 verify --full 在系统负载平均值约 74 时，verify_counterattack 与 verify_encounters 因 emu_start 墙钟超时失败（不是结果不一致），该运行已手动终止并作废（日志 `.relay/runs/20261019T091547.451970Z`）。
- 自写测试改为 timeout=0 后重跑：`./scripts/relay.sh verify --full` → exit 0，21 模块构建、2 个示例、38 个 verify 脚本共 41 步通过。运行目录 `.relay/runs/20261019T171541.668427Z`（UTC），输入指纹 `ec460f5f…1664f1`，与本次提交后的源码一致；该次运行覆盖 a638bfd（超时修改）与随后 T030-C/D 提交的合并状态。
- 新 verify_turn_burn：400 次比较（SetFlameVisibility 240、循环 160），108 次烧死；SetFlameVisibility 字节 SHA-256 `d31d3448…bb5e3`。
- 新 verify_turn_regen：900 次比较，122 次结束；段字节 SHA-256 `3a34e905…e706f944`。
- 错误副本（隔离开发副本）：T030-C 三个、T030-D 三个，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；T030 登记 --check matches true。

## 2026-10-19 T030-E：CheckEndGame 判断与免死段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、39 个 verify 脚本共 42 步通过。运行目录 `.relay/runs/20261019T172605.544713Z`（UTC），输入指纹 `5b7b3827…9b2b35`，与提交时源码一致。
- 新 verify_check_end_game：588 次比较（结果：继续 266、已结束 175、负 111、胜 36）；判断段字节 SHA-256 `a698234c…b0002358`。
- 错误副本（隔离开发副本）：mode==1、`>=0`、不清 0x164a5，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；T030 登记 --check matches true。

## 2026-10-19 T030-F：CheckEndGame 结束结算与计分函数（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、40 个 verify 脚本共 43 步通过。运行目录 `.relay/runs/20261019T173621.851181Z`（UTC），输入指纹 `fbbf488b…379c6e`，与提交时源码一致。
- 新 verify_game_over：600 次比较（按难度记分 260、按模式 186、不记分 86、未结束 68）；CheckEndGame 整函数字节 SHA-256 `b5d44ded…52cec490`，GetScore `f4f76f0c…0d65a9ae`。
- 错误副本（隔离开发副本）：有符号最高分比较、胜利不翻倍、等级系数 10，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；T030 登记 --check matches true（未恢复数 22）。

## 2026-10-19 T030-G：EndOfTurn 开头段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、41 个 verify 脚本共 44 步通过。运行目录 `.relay/runs/20261019T174750.679489Z`（UTC），输入指纹 `eae69423…87fa96`，`relay.sh check` 显示与当前源码一致。
- 新 verify_turn_begin：400 次比较（边界 120、随机 200、连续回合 80）；160 次由 CheckEndGame 结束，39 次技能就绪音效。段字节 SHA-256 `81d983d3…d2cd6cd5`。
- 错误副本（隔离开发副本）：冷却忽略 15 号敌人、不轮换金币标志、箭头条件忽略 0x16492，均 exit 1；真实源码对比一致。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 21）。

## 2026-10-19 T030-H / T030-I：EndOfTurn 中毒敌人循环与尾段（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、43 个 verify 脚本共 46 步通过。运行目录 `.relay/runs/20261019T180432.798177Z`（UTC），输入指纹 `9a0aae1d…7dfe96e3`，`relay.sh check` 显示与当前源码一致。
- 新 verify_turn_poison：240 次比较（存活粒子 1337、种族 1 成就 449）；新 verify_turn_finish：262 次比较（164 次有生成事件；保存 / 第一次结束 / 第二次结束 / 第 100 回合胜利均出现）。段字节 SHA-256 05915cf3…7b3d4a4e / dd46c0a1…0e49363f。
- 错误副本（隔离开发副本）：H——行优先遍历、不写回毒队列、`>=0` 判存活；I——帮助循环不 break、计时器按旧值判断下限、胜利条件漏 mode；均 exit 1。真实源码对比一致。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 21）。

## 2026-10-19 T030-G 修正：开头段标志归属（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、43 个 verify 脚本共 46 步通过。运行目录 `.relay/runs/20261019T182510.962112Z`（UTC），输入指纹 `07951088…080f9136`，与当前源码一致。
- verify_turn_begin 改为从 SelectionState / 预览状态 / RuneState 读回 Game+0xbe74..77 与 0x16491：400 次比较通过。错误副本"不写预览 double_*"exit 1。
- 发现途径：开发中的 EndOfTurn 整函数差分在 Game+0x165d0（AddToken 累计，读 0xbe75..77）上出现 120 vs 80。

## 2026-10-19 T030-J / K / L：ActivateAbility、能力段与 EndOfTurn 整函数（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、46 个 verify 脚本共 49 步通过。运行目录 `.relay/runs/20261019T183618.202762Z`（UTC），输入指纹 `498f4b02…ee9864cc`，与当前源码一致。
- verify_activate_ability 995 次（敌人类型 0..34）；verify_turn_abilities 200 次；verify_end_of_turn 230 次（存档 200，第 1/2/3/4 次 CheckEndGame 结束 18/7/2/3）。能力段 / EndOfTurn 整函数字节 SHA-256 33ec3742…5539335a / 0a00b29d…bc2b06fd。
- 错误副本（隔离开发副本）：J——去掉一次性守卫、复活不消耗 flag_25e、倒计时 `<=0`；K——不清 activated、行优先、ProcessCripples 置后；L——忽略回复段结束返回、能力段先于中毒敌人段；均 exit 1。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 20）。

## 2026-10-19 T030-M：第一批 8 个敌人能力（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T184823.531264Z`（UTC），输入指纹 `2af61aa6…d08792e6`，与当前源码一致。
- 新 verify_abilities：8 个函数各 80 组，共 640 次比较；verify_activate_ability 995、verify_turn_abilities 200、verify_end_of_turn 230（这 8 个能力在其中以原代码执行）。
- 错误副本（隔离开发副本）：ExplodeEnemy 不设下限 1、LowerSkulls 不排除自身、ConvertSwordToSkull 行优先、StabAttack 忽略宿敌分支、FleeUp 顶行判断（原生越界崩溃 exit 139）、LowerSkulls 不接线，均被拒。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 12：11 个能力 + SerialiseState）。

## 2026-10-19 T030-N1：MakeAcidPotion、FreezeTiles、BreakRandomShieldSword（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T190406.888724Z`（UTC），输入指纹 `0f8babdb…8ef01341`，与当前源码一致。
- verify_abilities：11 个函数共 880 次比较；activate / 能力段 / 整函数测试均通过（这 3 个能力以原代码执行）。
- 错误副本（隔离开发副本）：冰冻候选不排除已冰冻、普通药水漏 0x234、破损候选含魔剑、破损候选不排除已破损、FreezeTiles 不接线，均被拒。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 9：8 个能力 + SerialiseState）。

## 2026-10-19 T030-N2：ConvertRandomTiles、JumpEnemy、AttractSkulls、AttractShieldsSwords（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T222010.290295Z`（UTC），输入指纹 `72c0ba46…6dd727a6`，与当前源码一致。
- verify_abilities：15 个函数共 1200 次比较（JumpEnemy 交换 80、吸引类交换 417）；activate / 能力段 / 整函数测试通过。
- 错误副本（隔离开发副本）：ConvertRandomTiles 排除已冰冻、只做一轮；JumpEnemy 不排除自身、匹配目的地；吸引距离"或"改"且"、闪光顺序对调；均 exit 1。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 5：4 个能力 + SerialiseState）。

## 2026-10-19 T030-N3a：HealOrBless（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T223308.730696Z`（UTC），与当前源码一致。
- verify_abilities：16 个函数共 1280 次比较（治疗 72、祝福 88）；activate / 能力段 / 整函数测试通过。
- 错误副本（隔离开发副本）：治疗条件 `>=` 改 `>`、不排除自身、只处理一格，均 exit 1。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 4：3 个能力 + SerialiseState）。

## 2026-10-19 T030-N3b：ThrowSkull 与代币直接入队（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T225529.249948Z`（UTC），输入指纹 `1d7e5df4…48d64d42`，与当前源码一致（此前一次运行 20261019T224444.101086Z 也通过；提交前删去 verify_activate_ability.py 的一处行尾空格后重跑）。
- verify_abilities：17 个函数共 1360 次比较（ThrowSkull 生成代币 70 个，数值经代币动作状态 amount 比较）；activate / 能力段 / 整函数测试通过。含测试框架修正：RandomiseTile 同时启用补位/生成/遭遇钩子（JumpDown）。
- 错误副本（隔离开发副本）：不检查 attack_flag、行优先、代币数值改用攻击力，均 exit 1。
- 接力单测 4 项通过；T020 / T030 登记 --check matches true（T030 未恢复数 3：StealGold、DestroyUpgrade、SerialiseState）。

## 2026-10-19 T030-N3c：StealGold（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、47 个 verify 脚本共 50 步通过。运行目录 `.relay/runs/20261019T230736.815473Z`（UTC），输入指纹 `1db063a2…eebb7295`，与当前源码一致。
- verify_abilities：18 个函数共 1440 次比较（StealGold 生成代币 176 个、金币条更新 32 次）；activate / 能力段 / 整函数测试通过。
- 错误副本（隔离开发副本）：不标记金币已匹配、改位置后不重算距离、宿敌判断改 14、金币条件 `>=0`，均 exit 1。
- 接力单测 4 项通过；T010 / T020 / T030 登记 --check matches true（T030 未恢复数 2：DestroyUpgrade、SerialiseState）。

## 2026-10-19 T030-N4a：Game::UpdateStats（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建（22 个模块）、2 个示例、48 个 verify 脚本共 51 步通过。运行目录 `.relay/runs/20261019T232625.381198Z`（UTC），输入指纹 `e1d21e75…b28ea5fb`，与当前源码一致。
- 新 verify_stats：400 次比较（血条 735、剑值 355、骷髅值 386、护盾 699、技能刷新 208 次）；加成增/减/不变、冷却 ±1、record 模式跳过与各限幅分支均到达。
- 错误副本（隔离开发副本）：忽略缺陷 5、护甲流失阈值 `<4`、跳过条件 mode==0、GetStat(2)=1、技能当前值不截断，均 exit 1。
- 接力单测 4 项通过；T010 / T020 / T030 登记 --check matches true。

## 2026-10-19 T030-N4b：DestroyUpgrade 与升降级量（Claude）

- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、48 个 verify 脚本共 51 步通过。运行目录 `.relay/runs/20261019T234233.587642Z`（UTC），输入指纹 `2a2d837e…98b39fd3`，与当前源码一致。
- verify_stats：UpdateStats 400 + DestroyUpgrade 300，共 700 次比较（271 次实际削减属性）；降级/升级各档、特长两种结果与无正值属性分支均到达。
- 错误副本（隔离开发副本）：降级按升级档、去掉下限 0、type 10 只看 record、特长结果对调，均 exit 1；"去掉 min(几率,100)"为等价变异。
- 接力单测 4 项通过；T010 / T020 / T030 登记 --check matches true（T030 未恢复数 1：SerialiseState）。

## 2026-10-19 测试稳定性：去掉继承测试的墙钟超时（Claude）

- 现象：T040-B 的一次全套运行（`.relay/runs/20261020T012132.253858Z`）中 verify_encounters 失败，停在 0x3f3a4；该测试经 verify_refill.py 的 `emu_start(..., timeout=1000000, count=1000000)` 带 1 秒墙钟限制，单独重跑两次均通过——系统负载下的假失败。
- 修改：18 个继承的 verify 脚本里 19 处 `emu_start` 的墙钟超时改为 0，指令数上限不变（与 a638bfd 对自写测试的处理一致）。只改这些参数，比较逻辑不变。
- 验证：`./scripts/relay.sh verify --full` → exit 0，构建、2 个示例、49 个 verify 脚本共 52 步通过。运行目录 `.relay/runs/20261020T013826.005802Z`，输入指纹 `6c002e88…3056f5a3`，与提交时源码一致（该运行同时覆盖随后的 T040-A/B 提交）。

## 2026-10-19 T040-A / T040-B：调度调用登记与 ProcessInput 门槛（Claude）

- 同一次全套运行 `.relay/runs/20261020T013826.005802Z`（52 步通过，指纹 `6c002e88…3056f5a3`）。
- T040-A：`scripts/t040_process_audit.py --check --out docs/T040_PROCESS_CALLS.json` matches true（Process 76 / ProcessInput 74 / InitNewGame 51 个直接调用点）。顺带把 T030 登记的未恢复列表排序改为（大小，符号），消除同大小项受哈希随机化影响的潜在不确定。
- T040-B：新 verify_input_gate 600 次比较（阻塞 407、空闲 101、分派 70、开始攻击 22；73 次调用 EndOfTurn），CountAttackers 整函数同时比较；特长跳过、开始攻击、阶段 1..7 阻塞、EndOfTurn、分派分支均到达。错误副本：回合阈值 `<4`、阶段 8 也阻塞、CountAttackers 不排除冰冻、代币条件 `!=0`、忽略输入目标，均 exit 1。
- 接力单测 4 项通过；T010 / T020 / T030 / T040 登记 --check matches true。

## 2026-10-19 T040-C：松手 MatchPath 分支、短路径与公共尾段（Claude）

- 新 verify_release 500 次比较（MatchPath 276、短路径清除 203、卷轴入口 21）：原版 ProcessInput 从入口执行到尾声，Rand / list::size / AddRevengeHealth 为原代码；18 个分支全部到达，含治疗后血条不变。比较事件（含标签位置）、选择状态、三个 LabelFlight、计数、flag_1554c、生命、36 格 attack、路径与 fake、随机种子。
- 错误副本 18 个全部 exit 1（明细见 T040_SCHEDULE.md）。"MatchTiles 前不清 kill_count"最初存活：测试把 MatchTiles 结果写成覆盖值；改为与原 MatchTiles 一致的累加后被拒。
- `./scripts/relay.sh verify --full` → exit 0：构建、2 个示例、50 个 verify 脚本共 53 步通过。运行目录 `.relay/runs/20261020T032836.370195Z`，输入指纹 `5c1a9aa2…df285c233`，inputs_unchanged true。
- `scripts/t040_process_audit.py --check --out docs/T040_PROCESS_CALLS.json` matches true（ProcessInput 未恢复目标 16 个）。
