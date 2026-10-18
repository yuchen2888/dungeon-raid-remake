# 当前状态

更新：2026-10-18（America/Los_Angeles）。维护者：Codex（复核 Claude 的 T010 提交 8d9604a）。当前阶段：保留现有逆向成果，Codex → Claude 桌面 Code → Codex 复核的首次接力已完成；Gemini 尚未接入。

## 已核实

- 实际工作区为本 docs/ 的上级目录；创建前无 Git，无已有分支、提交、暂存修改或远端。源码基线提交 `bd9bbd3` 保存了原有 78 个源码/文档/脚本路径（含新增忽略规则）。
- 原有 7,282 个文件、1,207,443,199 字节已记录在本地 `.relay/bootstrap-before.json`，并在验证后重新逐项核对哈希。
- recovered/ 实际存在 19 个 `recovered_*.cpp` 模块、14 个头文件、20 个 verify 脚本、两个独立源码示例。源码结构包含补位、生成、JumpDown/Stab，见 ARCHITECTURE.md。
- 根外同级 ZIP（2026-10-16）缺少 refill/generation/encounters 三组新源码和四个新验证脚本，rewards_demo.cpp 也较旧；不从 ZIP 覆盖当前代码。
- `/Users/yuchen/Documents/Codex/2026-10-14/new-chat/dungeon-raid-investigation` 是较早研究副本：7 个恢复模块与当前同名源码一致，另有旧版头文件/脚本；未改动或合并覆盖。
- Codex CLI 0.135.0 可执行；Claude Code 以桌面应用会话运行（`claude` 仍不在 PATH，check 如实显示），Gemini CLI 未发现。2026-10-18 Claude 完成 T010 并提交，属于首次实际跨模型接力；Gemini 尚未参与。
- T010：refill/generation/encounters 的 17 个原函数 + Game::Process 下落片段 0x173c8 已登记原地址、字节哈希、状态偏移、hook 与测试（docs/T010_REGISTRY.json）；与 46 流程零重叠且不并入计数。Codex 独立核对全部 18 段字节与反汇编一致。未恢复的玩法回调为 Game::CheckEndGame（测试强制返回 0）；Tile::UpdateCountdown 为未恢复的倒计时 UI 显示，不是推进玩法倒计时。

## 验证

2026-10-17 Codex 全套隔离构建通过：19 模块 macOS 双架构库与 iPhone ARM64 静态库、两个无界面源码示例、20 个既有 verify 脚本全部通过。2026-10-18 Claude 默认验证重新执行构建、两个示例及四组验证，通过 522 补位棋盘、3164 生成场景、1992 特殊动作场景，以及 20 个连续手势/1550 步联合链条，没有重跑另 16 个脚本。本次 Codex 复核重跑登记检查、独立字节核对及损坏副本拒绝检查；两轮游戏验证的输入指纹均与当前源码一致，未重复运行游戏测试。详细命令、边界和日志路径见 VALIDATION.md 与 T010_REVIEW.md。

## 本轮修改与继承修改

整理前没有 Git，全部现有文件视为继承成果，已原样建立源码基线；没有清理、stash 或覆盖。新增 AGENTS.md / CLAUDE.md / GEMINI.md、README、docs/、scripts/ 与接力安全测试，单独原子提交；以 `git log` 查看设施提交。忽略的本地材料不在提交内。当前无待转交的继承源码修改；完成后释放 T001 活动锁。

2026-10-18 Claude 接手时工作树干净（HEAD 557cf44），无继承未提交修改。本轮只新增 scripts/t010_registry.py、docs/T010_REGISTRY.json 并更新 docs/ 四个文档，单独提交；recovered/ 源码与原始材料未改动。验证路径见 VALIDATION.md 末节。

2026-10-18 Codex 从干净的 8d9604a 接手复核，仅修正登记/文档中 UpdateCountdown 的 UI 分类、整文件哈希及运行日期描述，并记录复核结论。原有 7282 文件重新逐项核对无内容变化；recovered/ 不改动。完成后 handoff 释放 T010 写入权。

活动任务与未提交现场实时以 `./scripts/relay.sh check`、`git diff` 和 `.relay/active/owner.json` 为准；文档中的提交号只作里程碑，不用手工维护“永远等于 HEAD”的循环字段。

## 尚未完成及下一步

完整 ProcessAttack、EndOfTurn、输入阶段门槛、新局初始化/存档及整个 Game::Process 尚未形成完整可玩循环；现代 iOS UI、高清、多语言和教程未验收。现有 IPA/宿主为兼容路线，不能当作新源码游戏。

T010 已由 Claude 完成并经 Codex 复核通过（见 T010_REVIEW.md）。下一项 T020：先用同样只读方法列出 ProcessAttack 0x14118 的直接调用并按 46 流程/T010/hook/未恢复分类，再选一个敌人分支做原版差分。不要重做补位、生成和 Stab/JumpDown。本轮仅完成交接验收，没有开始 T020 的游戏代码开发。
