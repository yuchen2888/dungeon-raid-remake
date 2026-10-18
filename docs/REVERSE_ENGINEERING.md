# 逆向证据登记

本文件区分磁盘事实、历史报告和本轮验证。初始文件哈希及 ZIP 差异见 INITIAL_AUDIT.json；新实跑以 VALIDATION.md 和对应 `.relay/runs/` 为准。不要从聊天数字推断完成度。

| 领域 | 静态源码/证据 | 历史报告声称 | 当前边界 |
| --- | --- | --- | --- |
| 基础/输入/职业 | combat/rules/input/progression/selection；原有 provenance 与原结果 fixture | 原函数和重放多组通过 | 职业 fixture 是旧输入；非完整 UI 或局面存档 |
| 随机 | random，原 RNG 地址/字节及 random_provenance.json | 5 个函数、6 流逐步对照 | 原始溢出域、启动取种等以原测试边界为限 |
| 输入/围合 | stroke/preview/rune | 629 手势、1192 预览、594 符文等，集合互有重叠 | 输入门槛预先满足，不能相加为独立游戏覆盖 |
| 消除/奖励/路径 | match/tokens/resources/motion/path | 517 路径、26 联合手势、973 步、412 奖励 | 特殊目标/表现、完整主循环仍是接口 |
| 补位 | refill；MoveMatchedTiles 0x10ed8、PositionTile 0xb3c8（verify_refill.py 实际调用地址）、Tile::Process；对应汇编 | 522 棋盘、108 定位、2705 下落步 | 独立测试对生成/Stab 用确定性回调，另有真实依赖联合测试 |
| 生成 | generation；RandomiseTile 0xf5b8、GenerateStats 0x3e740、SetType 0x3f32c 等 | 3164 场景 | 完整函数/状态清单仍需 T010 补入旧 inventory，不能直接沿用“46 流程”当最新计数 |
| 特殊动作 | encounters；SwapTiles/JumpDown/Stab 对应 evidence/ | 1992 场景（1296 swap/36 jump/360 stab/300 move） | 与补位/生成接通，非完整敌人 ProcessAttack |
| 连续链条 | verify_refill_integration.py、rewards_demo.cpp | 20 手势、1550 步、280 奖励/新格 | 明确没有重开输入或完整回合 |

未核实的聊天说法不能升级为已完成项。本轮已实际复现表中各组现有验证，包括 522、3164、1992 和联合链条，详情见 VALIDATION.md；表中历史数字仍保留其原范围，不与其他组累加。职业档案以原 fixture 重放通过，未重新采集原版档案。旧 generation_failure.json 等失败现场虽与后续 passed 报告并存，也原样保留，不据文件名推断历史失败的修复原因。

原 `reverse-engineering/inventory.json` 的 46 流程只覆盖较早阶段；当前 19 模块不意味着 19 个原函数，也没有恢复百分比。较早 README/REVERSE-ENGINEERING-STATUS 的“16 模块、补位未恢复”已经落后于磁盘。

待恢复：ProcessAttack 0x14118、EndOfTurn 0x13574、ProcessInput 0x16638 门槛、InitNewGame 0x15c50、Game::Process 的完整阶段转换、Healing/CheckEndGame 及存档系统。首先查原指令和现有模块接口，再写差分复现，不用等概率随机或空敌人回调拼成假完整循环。

新增条目必须记录：原符号/地址/字节哈希 → 源码函数与文件 → 状态字段 → 明确回调 → 原版执行或 fixture 重放 → 场景与边界 → 本轮验证来源哈希/退出码。未经逐个核对不要补猜地址或函数数量。
