# Dungeon Raid 重制版

[English](README.md) | **简体中文**

**Dungeon Raid**（Firemint，2011）是一款三消加地牢冒险的游戏。这是它的非官方、非商业重制版，可以在现在的 iPhone 和 Mac 上玩。

原版早已从 App Store 下架，在新版 iOS 上也打不开了。这个项目把原版的规则还原成源代码，重新做了前端，支持新款 iPhone 全屏，加了高清画面和六种语言。

> **需要你自己的原版游戏。** 本仓库**不含任何游戏内容**：没有原版的程序、美术、音效、字体和英文文字。要玩，你得有自己的一份 Dungeon Raid 1.3.4 原版。详见[法律说明](#法律说明)。

<p align="center"><img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/hero.png" alt="iPhone 上的 Dungeon Raid 重制版"></p>

| <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/menu-en.png" width="200" alt="主菜单"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/board-en.png" width="200" alt="连线消除"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/attack-en.png" width="200" alt="怪物进攻"> |
|---|---|---|
| 主菜单 | 连线消除 | 怪物进攻 |

| <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/setup-zh.png" width="200" alt="开局设置（中文）"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/board-zh.png" width="200" alt="棋盘（中文）"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/settings-en.png" width="200" alt="设置页"> | <img src="https://github.com/yyc0409-ui/dungeon-raid-remake/releases/download/media/languages-en.png" width="200" alt="语言页"> |
|---|---|---|---|
| 开局设置（中文） | 棋盘（中文） | 设置页 | 语言页 |

*截图来自 iPhone 18 Pro 模拟器，高清画面。*

## 它是什么，不是什么

**它是：**

- **把原版规则还原成源代码。** 决定一局胜负的所有规则，都从原版程序还原成了可读的 C++（`recovered/`）：连线消除、攻击、护甲、敌人和它们的能力、回合结束、升级、商店、装备强化、技能、职业、计分和存档。不是模拟器跑老程序。
- **逐帧核对过。** 有一个对照台（`frontend/tools/lockstep.py`），让原版程序和重制版玩同样的对局，每一帧都比较。最近一次跑了 25,925 帧，没有一处不同，连原版发出的每个音效都一致。
- **全新的前端。** 用 [Godot 4.7](https://godotengine.org) 做，原版画什么、画在哪里，就照样画。新款 iPhone 上画面铺满整屏，启动画面也重做了。
- **高清画面。** 原版图片用 Real-ESRGAN 放大 4 倍，再人工修过。随时可以切回原版像素。
- **六种语言。** 英文、简体中文、繁体中文、日文、韩文、西班牙文。全部文字都翻译了，包括 61 段开场故事和画在图片里的字。中日韩文字用思源黑体，韩文按空格换行，日文的小假名不放在行首。
- **新的设置页。** 有单独的语言页、音量、振动、高清/原版画面、原版的几个开关（流畅、攻击时变暗、时钟），以及动画速度。
- **静音模式下也有声音。** 声音跟随媒体音量，和其他游戏一样，不受静音开关影响。

**它不是：**

- 官方产品。和 Firemint、EA 都没有关系。
- 游戏素材的来源。原版文件要你自己提供。
- 已经完工的作品。见[进度](#进度)。

## 进度

| 部分 | 状态 |
|---|---|
| 规则（一局之内和一局之外） | 已还原，并和原版核对 |
| Mac 版 | 能玩 |
| iPhone 版（iOS 16 以上） | 能玩；需要在 Mac 上编译安装 |
| 语言 | 6 种，全部文字和图片 |
| 高清画面 | 已完成（4 倍） |
| 不用 Mac 的安装方式（不含游戏内容的安装包，导入你自己的原版） | 正在做 |
| 为长屏 iPhone 重新设计的界面 | 设计中 |
| 安卓、Windows | 计划中（用同一个 Godot 项目） |
| 新内容（技能、职业） | 以后，等重制完成 |

## 开始使用

目前需要在 Mac 上编译：Apple 芯片的 Mac，装好 Xcode 和 Python 3。

1. **准备原版。** 你自己的 Dungeon Raid 1.3.4（IPA 文件），程序要是未加密的。
2. **准备工具。**
   - [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/)，放在 `/Applications`，并装上它的导出模板。
   - [godot-cpp](https://github.com/godotengine/godot-cpp) 10.0.0-stable，放在 `frontend/gdext/godot-cpp/`。
   - Python 3，以及 Pillow 和 NumPy。
   - [思源黑体](https://github.com/adobe-fonts/source-han-sans)（CN、TW、JP、KR）的四种粗细，放在 `frontend/tools/fonts/`，各语言要用。
   - 可选：[Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)（ncnn-vulkan，macOS 版），做高清图用。
3. **从你的原版生成游戏文件。** `frontend/tools/import_original_assets.py` 会把原版的图片、字体、音效和文字放进 `frontend/godot/assets/original/`，这个文件夹 Git 不收录。然后：
   - 用 `localise_atlas.py <语言>` 和 `make_cjk_font.py <语言>` 生成各语言的图片和字；
   - 用 `make_hd.py` 生成高清图。

   一步完成以上全部的工具正在写。在那之前，这些脚本需要事先解出来的文件，摆放方式见 `frontend/README.md`。
4. **开始玩。**
   - Mac：运行 `python3 frontend/gdext/build.py app`，然后打开 `frontend/dist/Dungeon Raid.app`。
   - iPhone 模拟器：运行 `frontend/tools/ios.sh simulator`。
   - 你的 iPhone：在 `frontend/godot/team_id.local` 里写上你的 Apple 开发者团队编号。编号是 10 位字母和数字，在 Xcode 的 Signing & Capabilities 里能看到。然后连上手机，运行 `frontend/tools/ios.sh device`。免费的 Apple ID 也行，但每 7 天要重装一次。

玩法：在棋盘上按住，拖过 3 个以上相连的同类格子再松开。剑和骷髅可以连在一起。

## 原理

```
 原版程序 ──（逆向还原）──▶ recovered/   C++ 规则核心，不含平台代码
                                │
                                ▼
            frontend/gdext/   Godot 插件：运行规则核心的会话，告诉前端画什么
                                │
                                ▼
            frontend/godot/   Godot 项目：绘制、触摸、音效、存档（Mac、iPhone）
```

- `recovered/`：规则，每个部分一个模块，各带检查脚本（`verify_*.py`）。检查时，让原版函数和还原的函数从同一状态出发，比较两者的结果。
- `frontend/gdext/src/ui/`：各个画面（棋盘、菜单、商店、职业画面、设置、故事），按原版的方式绘制。
- `frontend/tools/`：逐帧对照台（`lockstep.py`）、iPhone 编译（`ios.sh`），以及生成图片、字和高清图的工具。
- `docs/`：进度、决定，以及每个还原函数的证据。`docs/REVERSE_ENGINEERING.md` 记录了对原版已知的内容。

## 检查

```bash
python3 frontend/tools/lockstep.py 80
```

```bash
/Applications/Godot.app/Contents/MacOS/Godot --headless --path frontend/godot -s res://tests/smoke.gd
```

第一条把 80 局的操作分别交给原版和重制版，报告哪些帧不一样。它需要原版程序和本地的测试运行器。第二条只用重制版玩 20 个回合。

## 参与

非常欢迎翻译、报告问题、提供真机截图，请开 issue。如果发现某条规则和原版玩起来不一样，请说明发生了什么。可以的话附上存档，就是 App 文件夹里的 `Documents/`。

项目的工作规则（给人和 AI 编程工具看的）在 [AGENTS.md](AGENTS.md)。

## 法律说明

- Dungeon Raid 是 Firemint Pty Ltd 的游戏（2011），后来归 Electronic Arts 所有。它的名字、美术、音效、音乐、字体和文字归各自的权利人所有。本项目与 Firemint、EA 没有任何关系，也没有得到它们的认可。
- 本仓库不含任何原版内容，用本项目做出的安装包也不得包含原版内容。请只使用你合法拥有的那份原版里的文件。任何人分发游戏内容或含有游戏内容的安装包，与本项目作者无关。
- 这里的代码用于学习、保存老游戏和个人游玩，不用于商业用途。
- 如果你是权利人，对本项目有疑虑，请开 issue，我们会尽快处理。

## 致谢

- 感谢 Firemint 做出原版游戏。
- [Godot 引擎](https://godotengine.org)（MIT）和 [godot-cpp](https://github.com/godotengine/godot-cpp)（MIT）。
- Adobe 的[思源黑体](https://github.com/adobe-fonts/source-han-sans)（SIL 开放字体许可 1.1）。
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)（BSD 3-Clause），用来放大图片。

## 许可证

本仓库的代码使用 [MIT 许可证](LICENSE)。它只适用于本项目自己的代码和文档，绝不适用于原版游戏的内容。第三方代码使用各自的许可证。
