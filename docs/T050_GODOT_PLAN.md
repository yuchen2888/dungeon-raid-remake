# T050-A Godot 试玩原型计划（Claude，2026-10-20，未开始）

目标：用户在 Mac 上用鼠标亲手打完一局（简单方块画面），确认手感与工具链；之后同一项目做 iOS（M5）。规则全部来自 `recovered_session`（原生会话库），Godot 只做画面、触摸与菜单显示。

## 前提（需要用户）

1. 安装 Godot 4（稳定版，标准版即可，不需要 .NET 版）。工具不自动安装；可从 godotengine.org 下载，或 `brew install --cask godot`。
2. GDExtension 需要与 Godot 版本一致的 godot-cpp（GitHub 开源，MIT）。下载属于“从外部获取代码”，需用户同意；也可只用 Godot 自带的 `gdextension_interface.h`（`godot --dump-gdextension-interface` 导出，不需下载），代价是包装代码更啰嗦。建议用 godot-cpp。

## 结构

- `frontend/godot/`（新目录）：Godot 项目（场景、脚本、简单图形）。
- `frontend/gdext/`（新目录）：GDExtension 原生库，C++，编译时直接包含 `recovered/` 的源码（与 `run_session_demo.sh` 的源文件列表相同），不复制规则代码。
- 一个 Godot 节点类 `DungeonRaidSession`：
  - `new_game(seed)`：建会话、写职业表与棋盘布局（同 `session_demo.cpp` 的 main），`dr_session_new_game`。
  - `frame(dt, phase, x, y)`：`dr_session_frame`；phase 0 无触摸、1 按下 / 拖动、2 抬起；坐标为归一化坐标（屏幕宽 = 1，格子间距 pitch = 1/6）。
  - 读取：36 格（类型、特殊类型、敌人类型、血量 / 攻击 / 护甲、选中、变暗 dimmed、下落位置 geometry.center）、路径、资源（生命 / 护甲 / 经验 / 金币 / 升级点 / 等级）、技能槽与冷却、菜单状态（类型、选项、选择、动画计时）、结束画面。
  - 写入（渲染层拥有）：`skill_button` / `menu_button`（触摸下的按钮）、`release_inputs->health_target`（生命条目标点）、`current_label_active`（当前伤害标签是否在显示）。吸血 / 火焰 / 尖刺三个伤害标签由会话自己维护（`SessionObjects.damage_labels`：位置、缩放、字形与顶点、透明度，T040-K6），渲染层只按它们绘制。
  - 存档（T030-N5 已恢复，平台层要做的部分）：每帧检查 `end->flag_146d4`（对局存档变化：`flag_146d0` 为长度，0 表示删除）、`class_save->changed_14adc`（职业进度）与 `dr_session_save_changed_scores`（最高分，按类别 0..5 逐个返回），把对应字节写盘（Godot 的 `user://`）并清标志；启动时依次 `dr_session_restore_classes`、`dr_session_restore_scores`（每个类别）、`dr_session_restore_save`；主菜单在存档长度不为 0 时显示“继续”，点击调用 `dr_session_continue_game`。玩家名写入 `SessionObjects.name`（最多 16 个字符）。另：`match->spawn_dirty_15555` 置位时保存 `match->spawn_remaining_15558`（职业卷轴倒计时），启动时写回。
  - 事件：会话的表现事件（SessionHost.event：来源 + 单元自己的事件结构）转成 Godot 信号，原型只用少数（音效、飞行代币、闪光可先忽略）；代币飞行目标点（SessionHost.target / token_start）给界面布局常量。

## 分步

| 步骤 | 内容 | 完成标志 |
| --- | --- | --- |
| A1 | GDExtension 骨架：构建脚本、Godot 能加载、每帧调用 `frame` | Godot 运行时打印回合数随连线增加 |
| A2 | 棋盘：6×6 方块按类型着色、数字显示敌人血量 / 攻击；鼠标连线（按下、拖过、抬起）；变暗显示 | 能连线消除、补位下落 |
| A3 | 顶部资源条、回合、敌人攻击、结束画面与重新开始；存档写盘、主菜单“继续” | 能打到游戏结束并重开；退出后能继续 |
| A4 | 升级 / 商店 / 装备升级菜单弹窗（选项文字用技能 / 物品类型名）、技能按钮与冷却 | 菜单可选可确认、技能可用 |
| A5 | 导出 Mac 应用给用户试玩 | 用户打完一局并反馈手感 |

## 参考

- `recovered/session_demo.cpp`：不带画面的同一流程（建会话、新局、每帧输入、菜单按钮），A1～A4 的逻辑可直接照搬。
- `recovered/recovered_session.hpp`：SessionObjects（每帧可读写的对象）、SessionSource（事件来源）、SessionHost（回调）。
- 原版画面与素材仅本地保留，不放进仓库；原型用简单图形。高清美术来源待用户决定（ROADMAP 第五节）。
