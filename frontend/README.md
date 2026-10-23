# Dungeon Raid 重制版：Godot 前端（T050-A / T050-B）

画面、动画、音效、文字都按原版（原版贴图、字体、音效、英文文字只在本机使用，不进 Git，见 `tools/import_original_assets.py`）；规则全部在 `recovered/` 的规则核心里。

## 怎么玩

- **Mac**：双击 `dist/Dungeon Raid.app`（由 `python3 frontend/gdext/build.py app` 生成，自带 Godot 运行库，不用另装）。
- **iPhone 真机**：手机和这台 Mac 配对过（数据线连过一次并点“信任”），运行 `frontend/tools/ios.sh device`，会编译、签名、装到手机上并打开。用的是个人免费开发者账号，**签名 7 天后过期**，过期后再运行一次这条命令即可。
- **iPhone 模拟器**：`frontend/tools/ios.sh simulator`（默认 iPhone 18 Pro，可在后面写别的机型名）。
- 玩法：在棋盘上按住拖过 3 个以上相连的同类格子再松开；剑和骷髅可以连在一起。

iPhone 版需要：Xcode、`/Applications` 里的 Godot 4.7.2 和它的官方导出模板（2026-10-23 经用户同意下载安装到 `~/Library/Application Support/Godot/export_templates/4.7.2.stable/`）。Godot 官方模板里的“模拟器版引擎”只有 Intel 版，新版模拟器跑不了，所以模拟器用 `tools/sim_retarget.py` 把真机版引擎改标成模拟器版（只改平台标记，代码不变）；真机用官方引擎原样。

## 语言（T050-D）

主菜单原来的 OpenFeint 按钮（那个服务早已关闭）改成了“设置 / Settings”，里面可以选 English 或中文，选完画面会重新载入成新语言；第一次打开时跟随系统语言。中文是新做的内容：

- 文字：`godot/assets/lang/zh/texts.txt`（约 1060 条，按原版文字的键覆盖；格式里的 %d / %s 与原文一一对应）。
- 字体：思源黑体（Adobe，SIL OFL 1.1，免费可随游戏发布；2026-10-23 经用户同意下载到 `tools/fonts/`，不进 Git），`tools/make_cjk_font.py` 按游戏用到的字生成三种字体的字图（贴图编号 7–9）。
- 图片里的英文字（主菜单按钮、“Level Up!”、弹出标签、游戏菜单按钮、确认框等 88 处）：`tools/localise_atlas.py zh` 在原图同样位置画成中文（`lang/zh/tiles.png`、`menus.png`）；英文只把 OpenFeint 改成 Settings（`lang/en/tiles.png`，用原版菜单字体拼出）。
- 中文按字换行，句末标点不放行首；英文的排版与原版逐帧一致（对照台 `lockstep.py 80` 已复验）。

这些文件和原版素材一样只在本机（`godot/assets/lang/` 不进 Git），iPhone 导出时一起打包。生成顺序：`python3 frontend/tools/localise_atlas.py zh`、`localise_atlas.py en`，再 `python3 frontend/tools/make_cjk_font.py zh`。

## 结构

- `gdext/`：Godot 插件（C++）。`src/dr_bridge.*` 是不依赖 Godot 的转接层，`src/dungeon_raid_session.*` 把它包装成 Godot 对象 `DungeonRaidSession`。规则源码直接从 `recovered/` 编译（文件列表取自 `recovered/run_session_demo.sh`），不复制。
- `godot/`：Godot 项目。`original.gd`（主场景 `original.tscn`）把插件交回的原版绘制画出来，并负责触摸输入、音效和存档读写（`user://`）；`main.gd` 是早期的简单图形原型。`export_presets.cfg` 是 iPhone 导出设置（开发者团队、App 标识 `com.yuchen.dungeonraid.remake`）。
- `tools/ios.sh`：iPhone 版一条命令编译、导出、安装；`tools/sim_retarget.py` 见上。
- `gdext/godot-cpp/`：Godot 官方的 godot-cpp 10.0.0-stable（MIT，2026-10-21 经用户同意下载，不进 Git）。

## 检查命令

```
python3 frontend/gdext/build.py test                    # 转接层自测（不需要 Godot）
python3 frontend/gdext/build.py extension               # 编译插件库到 frontend/godot/bin/
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot -s res://tests/smoke.gd
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot --quit-after 40000 -- --autoplay
```

最后一条让游戏自己点主菜单、开局设置和菜单，用提示线连线，一直打到游戏结束（存档放在单独的 `user://autoplay/`，不影响玩家存档）。加 `--shots=<文件夹>` 并去掉 `--headless`，会在各个画面截图。
