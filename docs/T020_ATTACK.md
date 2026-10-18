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
