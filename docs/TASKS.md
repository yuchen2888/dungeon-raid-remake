# 任务列表

每个任务一次只由一位 AI 认领。填写状态、工具、涉及文件、验收和证据后再写代码。任务顺序对三个工具相同。

| 编号 | 状态 | 目标及验收 | 范围 / 证据 |
| --- | --- | --- | --- |
| T001 | 完成 / Codex | 接力规则、隔离验证、Git 基线；全套现有测试通过，交接安全测试及只读检查；原文件逐项核对 | AGENTS.md、docs/、scripts/、tests/test_relay.py；VALIDATION.md |
| T010 | 完成 / Claude，待 Codex 复核 | 更新恢复函数登记，给 refill/generation/encounters 标明原地址、状态字段、回调和测试；对照现有 46 流程旧清单，不重复计数。结果：17 函数 + 1 片段，零重叠，未建模调用 0 | docs/T010_REGISTRY.json、scripts/t010_registry.py、REVERSE_ENGINEERING.md T010 节；验收 `python3 -I scripts/t010_registry.py --check` 与 `./scripts/relay.sh verify` |
| T020 | 待认领 | 分段恢复 ProcessAttack；先为一个敌人分支建立原版差分复现，再实现并比较逐阶段状态 | 原入口 0x14118；新增专用恢复模块与定向测试；不重新实现 Stab/JumpDown |
| T030 | 待 T020 | 分段恢复 EndOfTurn，验证毒/冻结/能力、再次补位与存档边界 | 原入口 0x13574；连续多回合状态/随机流对照 |
| T040 | 待 T030 | 恢复输入阻塞门槛、新局初始化与完整回合调度 | ProcessInput 0x16638、InitNewGame 0x15c50、Game::Process；同一棋盘可进入下一回合且不执行旧程序 |
| T050 | 待 T040，可独立做标注原型 | 现代 iOS 全屏界面、资源键、中英文和教程 | 实机/模拟器交互验收；原型明确标注，不能替代真实引擎 |

独立小任务：Claude Code 已于 2026-10-18 完成 T010 单元并提交（见 git log），待 Codex 复核：重跑 `--check`、抽查 2–3 个地址与反汇编、确认内联替代判断。Gemini CLI 接力尚未发生。

认领记录：`T010 / claude / 起始 557cf44 / 继承差异：无（工作树干净） / 目标：三模块地址-状态-回调-测试登记 / 文件：scripts/t010_registry.py、docs/T010_REGISTRY.json、docs/*.md / 验收：--check exit 0 + verify 四组 passed / 结果：.relay/runs/20261018T070600.453747Z / 下一步：T020 前用同法给 ProcessAttack 0x14118 列静态调用分类`

认领记录模板：`Txxx / 工具 / 起始 HEAD / 继承差异 / 目标 / 文件 / 验收命令 / 结果路径 / 下一步`。详细活动现场存于 `.relay/active/owner.json`，持久事实随原子提交更新这里和 PROJECT_STATE.md。
