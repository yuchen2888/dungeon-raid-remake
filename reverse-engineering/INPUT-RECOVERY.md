# 输入和资源预览源码恢复

后续更新（2026-10-17）：实际单格消除、奖励移动和到达入账已在新的联合场景接通，见 `MATCH-REWARDS-RECOVERY.md`。下文是较早阶段的验证记录，其未完成描述保留当时范围。
后续更新：符文扫描已恢复，新增松手前置处理和预览重置，见 `RUNE-RECOVERY.md`。下文保留输入/资源预览阶段的验证范围；当前 build.sh 为 11 个模块，独立示例已增加符文围合和消除请求。

2026-10-16。目的：把“手指选第一格、继续连线、回退或取消、看到预估收益”变成可以继续开发的 C++ 源码。不是作者原工程的逐字还原，也不是完整游戏。

## 新增内容

| 源码 | 恢复内容 | 来源 |
|---|---|---|
| recovered_stroke.cpp/.hpp | 起笔、已有路径延伸、取消、松手后路线判断 | Game::ProcessInput，0x16638，部分分支 |
| recovered_preview.cpp/.hpp | 药水、敌人经验、金币、盾牌盈余的计数及显示预览；特殊模式预览总数 | Game::ProcessResourceShadows，0xefe0，0x320 字节含常量 |
| stroke_demo.cpp | 将上述源码连起来的无界面运行示例 | 新写的接入示例，不计入恢复函数数量 |

`StrokeState` 持有选择状态和资源计数；`ResourcePreviewState` 提供护甲、加成及药水状态。收到 `SelectionEvent::ResourceShadows` 时调用 `dr_preview_resources`，由后者返回四种 UI 预览事件。示例展示了这个接法。

原版的两个容易误改的细节：短路径缺陷判断使用包含特殊桥接格的路径总长度，而计数跳过桥接格；盾牌数量先扣除补足当前护甲所需数量，再算升级点预览。代码保持原版整数回绕、浮点精度和转换顺序，不按常识改写规则。

## 实际验证结果

| 验证 | 结果 | 范围 |
|---|---|---|
| verify_stroke.py | 629 场景 / 1,781 操作步骤通过 | 首次命中、冻结限制、敌人/剑块、火焰、连续连线、回退、取消、回调顺序 |
| 同上，松手路线 | 270 例通过 | 普通清理 142、提交路径 126、职业卷轴 2；仅分支判断 |
| verify_preview.py，独立函数 | 1,192 例通过 | 各类格、路径长度、缺陷、桥接格、药水标志、损坏盾、倍增、模式、除零及选定整数边界 |
| 同上，连续联动 | 623 场景 / 1,727 步通过 | 原输入和选择函数实际调用原资源预览，与 native 源码联动比较 |
| build.sh | 10 模块编译通过 | macOS ARM64/x86_64、iPhone ARM64 静态库；不是 IPA 或真机验收 |
| run_stroke_demo.sh | 成功运行，退出码 0 | 三格金币预览 2→4→6、识别 MatchPath、取消后预览隐藏 |

手势测试不是独立样本的累加：联合测试沿用输入用例，并去掉 6 个专用于测试假定回调修改伤害的场景。

原版对照实际执行原 Mach-O 的 ARMv7 指令，包括 ProcessInput 原入口、已有路径选择与资源计算。原 std::list/set 存储、绘图/音频/UI 和平台 ceilf 通过适配器承接。联合验证中的资源计算不是空回调。原版二进制只用于对照；示例程序只编译 C++，不链接 Unicorn，也不读取原版。

## 明确未完成的部分

- 测试预先满足“棋子不在移动、无等待奖励、无技能菜单、输入可用”等条件；完整输入门槛和阶段调度尚未恢复。
- 本文阶段的 `ProcessRune` 曾是接口，后续已恢复扫描和消除请求，实际 MatchTile 仍未实现；`ProcessPretzels` 仍是接口。
- `dr_release_route` 是在原 `ProcessRune(true)` 之后的状态上作判断。调用者必须先完成该处理；现在不能直接用它替代完整松手逻辑。
- 资源预览不改变玩家的真实金币、经验、生命或升级数值；真实入账属于后续奖励事件与 `AddResource`。
- UI 回调在本轮资源计算验证中只记录输出，不修改游戏状态；没有证明任意外部回调改动下的等价性。
- 输入限定正常棋盘几何、有限坐标、有效且不重复的路径、桥接格为路径子集，药水状态为布尔值。
- 消除、完整奖励事件、生成补位、敌人行动、回合收尾、存档、UIKit 接入仍未连成完整游戏。
- 全屏、HD 美术、中文、多语言、教程目前仍是后续产品目标，不能用规则对照结果代替验收。

## 复现

在包根目录运行（本机需 Xcode 和命令行工具）：

```sh
sh recovered/build.sh
python3 recovered/verify_stroke.py
python3 recovered/verify_preview.py
sh recovered/run_stroke_demo.sh
python3 reverse-engineering/audit.py --reference reference
```

原指令对照依赖包中保留的本机 ARM64 TCI 工具；它不是未来 iOS App 的运行依赖。只运行最后的源码示例不需要 Python 或原游戏文件。

对应证据是 `stroke_provenance.json`、`preview_provenance.json`、两份 verification JSON 以及原汇编片段。`inventory.json` 将 ProcessInput 分支单列为 partial_functions，避免误报完整恢复。

## 接下来的实际开发

ProcessRune 扫描已在后续恢复，接下来沿松手路径恢复 `MatchTile` 的依赖，明确消除状态与奖励事件，再接实际入账和补位。完成这一段后才能用同一个棋盘状态验证一整回合。显示层可另行制作全屏、中文和高清素材原型，但需要标注原型，最终接入这套规则源码。
