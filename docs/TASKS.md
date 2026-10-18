# 任务列表

每个任务一次只由一位 AI 认领。填写状态、工具、涉及文件、验收和证据后再写代码。任务顺序对三个工具相同。

| 编号 | 状态 | 目标及验收 | 范围 / 证据 |
| --- | --- | --- | --- |
| T001 | 完成 / Codex | 接力规则、隔离验证、Git 基线；全套现有测试通过，交接安全测试及只读检查；原文件逐项核对 | AGENTS.md、docs/、scripts/、tests/test_relay.py；VALIDATION.md |
| T010 | 待认领 | 更新恢复函数登记，给 refill/generation/encounters 标明原地址、状态字段、回调和测试；对照现有 46 流程旧清单，不重复计数 | docs/REVERSE_ENGINEERING.md、现有 provenance、reverse-engineering/evidence/；先只读审计，形成可审阅清单 |
| T020 | 待认领 | 分段恢复 ProcessAttack；先为一个敌人分支建立原版差分复现，再实现并比较逐阶段状态 | 原入口 0x14118；新增专用恢复模块与定向测试；不重新实现 Stab/JumpDown |
| T030 | 待 T020 | 分段恢复 EndOfTurn，验证毒/冻结/能力、再次补位与存档边界 | 原入口 0x13574；连续多回合状态/随机流对照 |
| T040 | 待 T030 | 恢复输入阻塞门槛、新局初始化与完整回合调度 | ProcessInput 0x16638、InitNewGame 0x15c50、Game::Process；同一棋盘可进入下一回合且不执行旧程序 |
| T050 | 待 T040，可独立做标注原型 | 现代 iOS 全屏界面、资源键、中英文和教程 | 实机/模拟器交互验收；原型明确标注，不能替代真实引擎 |

独立小任务：在用户安装/登录 Claude Code 和 Gemini CLI 后，由下一工具完成一个 T010 单元并提交，再交回 Codex 复核。这才是实质的跨模型接力验证；当前只读本地演练不冒充它。

认领记录模板：`Txxx / 工具 / 起始 HEAD / 继承差异 / 目标 / 文件 / 验收命令 / 结果路径 / 下一步`。详细活动现场存于 `.relay/active/owner.json`，持久事实随原子提交更新这里和 PROJECT_STATE.md。
