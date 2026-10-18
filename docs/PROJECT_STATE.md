# 当前状态

更新：2026-10-18（America/Los_Angeles）。维护者：Codex（T020 第一单元）。当前阶段：首次 Codex → Claude → Codex 接力已完成，Codex 已继续恢复敌人攻击中的护甲损耗片段；Gemini 尚未接入。

## 已核实

- 实际工作区为本 docs/ 的上级目录；创建前无 Git，无已有分支、提交、暂存修改或远端。源码基线提交 `bd9bbd3` 保存了原有 78 个源码/文档/脚本路径（含新增忽略规则）。
- 原有 7,282 个文件、1,207,443,199 字节已记录在本地 `.relay/bootstrap-before.json`，并在验证后重新逐项核对哈希。
- recovered/ 当前存在 20 个 `recovered_*.cpp` 模块、15 个头文件、21 个 verify 脚本、两个独立源码示例。新增 attack_shield 是局部恢复，不计作完整 ProcessAttack；补位、生成、JumpDown/Stab 等既有逻辑继续复用。
- 根外同级 ZIP（2026-10-16）缺少 refill/generation/encounters 三组新源码和四个新验证脚本，rewards_demo.cpp 也较旧；不从 ZIP 覆盖当前代码。
- `/Users/yuchen/Documents/Codex/2026-10-14/new-chat/dungeon-raid-investigation` 是较早研究副本：7 个恢复模块与当前同名源码一致，另有旧版头文件/脚本；未改动或合并覆盖。
- Codex CLI 0.135.0 可执行；Claude Code 以桌面应用会话运行（`claude` 仍不在 PATH，check 如实显示），Gemini CLI 未发现。2026-10-18 Claude 完成 T010 并提交，属于首次实际跨模型接力；Gemini 尚未参与。
- T010：refill/generation/encounters 的 17 个原函数 + Game::Process 下落片段 0x173c8 已登记原地址、字节哈希、状态偏移、hook 与测试（docs/T010_REGISTRY.json）；与 46 流程零重叠且不并入计数。Codex 独立核对全部 18 段字节与反汇编一致。未恢复的玩法回调为 Game::CheckEndGame（测试强制返回 0）；Tile::UpdateCountdown 为未恢复的倒计时 UI 显示，不是推进玩法倒计时。
- T020-A：ProcessAttack 的 55 个直接调用点 / 32 个目标已登记，护甲损耗片段 `[0x147e4,0x1487e)` 已成为独立原生源码并接入统一构建/验证；复用共享棋盘、护甲和六个随机流。前一阶段计算出的已吸收伤害由调用者提供；完整调度和后续生命扣减仍未恢复。

## 验证

2026-10-17 Codex 全套隔离构建通过：19 模块 macOS 双架构库与 iPhone ARM64 静态库、两个无界面源码示例、20 个既有 verify 脚本全部通过。2026-10-18 Claude 默认验证重新执行构建、两个示例及四组验证，通过 522 补位棋盘、3164 生成场景、1992 特殊动作场景，以及 20 个连续手势/1550 步联合链条，没有重跑另 16 个脚本。同日 T010 复核重跑登记检查、独立字节核对及损坏副本拒绝检查；两轮游戏验证的输入指纹与当时源码一致，T010 复核没有重复运行游戏测试。详细历史命令、边界和日志路径见 VALIDATION.md 与 T010_REVIEW.md。

2026-10-18 T020-A 实跑 `./scripts/relay.sh verify --full`：20 模块 macOS 双架构/iPhone ARM64 构建、两个示例、21 个 verify 脚本共 24 步通过。新分支 1510 组场景加 100 连续步骤一致，严格阈值错误副本被拒绝；4 项接力安全测试通过。运行目录 `.relay/runs/20261018T072018.132343Z`，新输入指纹及详细结果见 T020_VALIDATION.json；不再把旧输入指纹当当前验证。

## 本轮修改与继承修改

整理前没有 Git，全部现有文件视为继承成果，已原样建立源码基线；没有清理、stash 或覆盖。新增 AGENTS.md / CLAUDE.md / GEMINI.md、README、docs/、scripts/ 与接力安全测试，单独原子提交；以 `git log` 查看设施提交。忽略的本地材料不在提交内。当前无待转交的继承源码修改；完成后释放 T001 活动锁。

2026-10-18 Claude 接手时工作树干净（HEAD 557cf44），无继承未提交修改。本轮只新增 scripts/t010_registry.py、docs/T010_REGISTRY.json 并更新 docs/ 四个文档，单独提交；recovered/ 源码与原始材料未改动。验证路径见 VALIDATION.md 末节。

2026-10-18 Codex 从干净的 8d9604a 接手复核，仅修正登记/文档中 UpdateCountdown 的 UI 分类、整文件哈希及运行日期描述，并记录复核结论。原有 7282 文件重新逐项核对无内容变化；recovered/ 不改动。完成后 handoff 释放 T010 写入权。

2026-10-18 Codex 从干净的 7652bea 认领 T020，新增护甲损耗源码/测试、调用登记与用户操作说明，扩展 build.sh 和 verify.py；没有继承未提交修改。旧的 19 个模块源码未改动，原有文件仅 build.sh 因增加模块而有必要修改，原程序/素材/证据及其他原文件保持。完成一个可验证单元后提交并保存交接断点，完整 T020 仍保留为未完成。

活动任务与未提交现场实时以 `./scripts/relay.sh check`、`git diff` 和 `.relay/active/owner.json` 为准；文档中的提交号只作里程碑，不用手工维护“永远等于 HEAD”的循环字段。

## 尚未完成及下一步

完整 ProcessAttack、EndOfTurn、输入阶段门槛、新局初始化/存档及整个 Game::Process 尚未形成完整可玩循环；现代 iOS UI、高清、多语言和教程未验收。现有 IPA/宿主为兼容路线，不能当作新源码游戏。

继续 T020 的下一单元：登记护甲片段上游伤害/阶段字段和 DoCounterattack 的依赖，选择一个可单独验收的原指令片段恢复，再逐步接后续生命伤害和完整阶段。现有护甲局部、补位、生成和 Stab/JumpDown 均复用。用户当前选择由 Codex 在本对话继续；额度耗尽后由用户停止当前工具，再用同一目录让下一 AI 接手。简明操作见 用户操作.md。
