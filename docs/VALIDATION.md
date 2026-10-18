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
