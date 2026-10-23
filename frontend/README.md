# Dungeon Raid 重制版：Godot 试玩原型（T050-A）

**怎么玩**：在 Finder 里双击 `试玩 Dungeon Raid.command`。需要先安装 Godot 4.5 或更新的版本（放在「应用程序」里）。

- 玩法：在棋盘上按住鼠标，拖过 3 个以上相连的同类格子再松开。剑和骷髅可以连在一起，剑越多伤害越高。
- 快捷键：Esc 回主菜单（每回合结束时会自动存档，可以从「继续上一局」接着玩）；H 显示一条可以连的线。
- 原型里的文字是临时中文，技能名按效果起名，职业叫"职业1～10"；原版文字、高清画面和多语言放在后面的完善版阶段（ROADMAP M4）。

## 结构

- `gdext/`：Godot 插件（C++）。`src/dr_bridge.*` 是不依赖 Godot 的转接层，`src/dungeon_raid_session.*` 把它包装成 Godot 对象 `DungeonRaidSession`。规则源码直接从 `recovered/` 编译（文件列表取自 `recovered/run_session_demo.sh`），不复制。
- `godot/`：Godot 项目。`main.gd` 负责画面、鼠标输入和存档读写（`user://`），规则都在插件里。
- `gdext/godot-cpp/`：Godot 官方的 godot-cpp 10.0.0-stable（MIT，2026-10-21 经用户同意下载，不进 Git）。

## 检查命令

```
python3 frontend/gdext/build.py test                    # 转接层自测（不需要 Godot）
python3 frontend/gdext/build.py extension               # 编译插件库到 frontend/godot/bin/
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot -s res://tests/smoke.gd
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot --quit-after 40000 -- --autoplay
```

最后一条让游戏自己点主菜单、开局设置和菜单，用提示线连线，一直打到游戏结束（存档放在单独的 `user://autoplay/`，不影响玩家存档）。加 `--shots=<文件夹>` 并去掉 `--headless`，会在各个画面截图。
