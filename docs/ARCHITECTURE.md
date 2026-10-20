# 架构与运行边界

## 现有恢复源码

`recovered/` 是当前主线，保持原有目录和接口；不是作者原始源码，也没有完整游戏入口。

| 层 | 模块 | 已存在的责任 |
| --- | --- | --- |
| 基础 | combat、rules、random | 攻击/毒伤、匹配与伤害分类、原随机流 |
| 输入 | input、selection、stroke、preview、rune | 坐标命中、延伸/回退、输入子分支、资源预览、围合 |
| 消除奖励 | battle、round、match、tokens、resources、motion、path | 单体攻击、路径调度、实际消除、奖励排队/移动/入账和接入适配 |
| 补位生成 | refill、generation、encounters | 下落补位、生成/晋升数值、SwapTiles/JumpDown/Stab；非完整敌人阶段 |
| 敌人阶段 | attack_shield | ProcessAttack 每帧逻辑（dr_process_attack，T020），复用 ResourceState / MatchState / 规则及随机模块 |
| 回合结束 | turn | Game::EndOfTurn 整函数（dr_end_of_turn）、CheckEndGame 与结束结算、Tile::ActivateAbility 及 19 个敌人能力；DestroyUpgrade 与 SerialiseState 仍为边界（T030） |
| 回合调度 | schedule | ProcessInput 门槛（dr_input_gate）与 CountAttackers：何时开始敌人攻击、何时调用 EndOfTurn、何时分派触摸；松手后的 MatchPath 分支、AddRevengeHealth、伤害标签起飞、职业卷轴与公共尾段（dr_release_path / dr_release_class_scroll / dr_release_clear）；新局初始化（dr_init_new_game、dr_calculate_tile_positions）；Process 伤害标签段（dr_process_damage_labels）与棋盘效果段（dr_process_board_effects）（T040） |
| 玩家属性 | stats | Game::UpdateStats（dr_update_stats）：由装备物品与技能重算属性，产生 ProcessAttack 的攻击几率/削弱/全体伤害与回复量（T030-N4a） |
| 职业档案 | progression | 职业进度、编解码、升级/成就；非完整局面存档 |

stroke / selection 持有棋盘；MatchState、PathState、ResourceState、RefillState、GenerationState 通过指针共享状态并用回调承接跨层调用。参考 recovered/rewards_demo.cpp 中的接线；尤其要一起交换生成附加状态，不能只交换格子显示。

当前无界面链条：手势/围合 → MatchTiles/AttackSkull/MatchTile → 队列和奖励 → 真实生成/补位/下落与资源入账。奖励与补位受阶段/动画影响，不能假定为已完成单线回合。完整敌人阶段、结束判断、输入重开与 UI 仍有缺口。

## 两条构建路线

- 恢复源码：`recovered/build.sh` 构建 23 个 macOS arm64+x86_64 动态库、iPhone arm64 对象和静态库（含 attack_shield、turn、stats、schedule）；两个 run_*_demo.sh 现场编译并运行无界面示例。静态库不能安装为 App。
- 兼容运行层：adapter/、unicorn-tci/、dynarmic-api/、liveexec32-source/、mini-gdbstub/、runtime/；旧 ARM32 游戏通过现代宿主/TCI 执行。rebuild.py / build-framework.py / package-app.py 属此路线，本轮不签名、不打包、不将其作为重制验收。

## 验证依赖与隔离

统一入口 `scripts/verify.py` 使用 macOS Python、Xcode SDK、已有源码及以下本地材料：

- `DungeonRaid-original` 与 `armv7-disassembly.txt`：原指令/常量/符号定位。
- `tools/unicorn/`：现有 ARM64 TCI Python 绑定及 libunicorn.2.dylib；`RAID_UNICORN_TCI=1` 选择已有验证支持。旧文档提到 Rosetta/tools-x86，不是本轮默认路径。
- `runtime/liveexec32/original-progression-verification.json`：职业档案原版 fixture；该测试是 fixture 重放，不是本轮重新生成原版档案。
- `recovered/crossing_boundary_paths.json` 及 `*.bin`：已有差分输入/字节证据。

以上资源不进入当前 Git；仅克隆源码时会明确缺依赖。每次复制所需输入到 `.relay/runs/<UTC时间>/work/`，重新编译后执行现有验证，不复制旧 verification 报告或旧动态库。保留每步日志、退出码和输入哈希。check 只读；verify 会写隔离目录。Xcode SDK/TCI 二进制在其他机器可变化，换环境必须重新验证。

reference/ 的解码图集/字体/符号、reverse-engineering/evidence/ 和完整汇编留作本地证据；原样保留并在 INITIAL_AUDIT.json 中记录来源。第三方完整重建依赖版本/许可证仍待专项盘点。
