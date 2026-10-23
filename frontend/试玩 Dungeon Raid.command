#!/bin/sh
# 双击这个文件就能试玩 Dungeon Raid 重制原型（T050-A）。
# 它会：找到 Godot → 用最新的规则源码重新编译游戏库（失败就用上次编好的）→ 打开游戏窗口。
cd "$(dirname "$0")" || exit 1
GODOT=/Applications/Godot.app/Contents/MacOS/Godot
[ -x "$GODOT" ] || GODOT="$HOME/Applications/Godot.app/Contents/MacOS/Godot"
if [ ! -x "$GODOT" ]; then
    echo "没有找到 Godot。请从 https://godotengine.org/download/macos/ 下载，把 Godot.app 放进「应用程序」文件夹。"
    echo "按回车键关闭。"; read -r _; exit 1
fi
LIB=godot/bin/libdungeonraid.macos.template_debug.arm64.dylib
echo "正在准备游戏库……"
if ! /usr/bin/python3 gdext/build.py extension > /tmp/dungeonraid-build.log 2>&1; then
    if [ -f "$LIB" ]; then
        echo "（这次编译没成功，先用上次编好的版本。详情见 /tmp/dungeonraid-build.log）"
    else
        echo "游戏库编译失败，详情见 /tmp/dungeonraid-build.log。按回车键关闭。"; read -r _; exit 1
    fi
fi
if [ ! -f godot/.godot/extension_list.cfg ]; then
    echo "第一次运行，正在让 Godot 登记游戏库……"
    "$GODOT" --headless --path godot --import > /dev/null 2>&1
fi
echo "游戏窗口打开了就可以玩。关掉游戏窗口后，这个黑色窗口也可以关掉。"
"$GODOT" --path godot > /tmp/dungeonraid-game.log 2>&1
