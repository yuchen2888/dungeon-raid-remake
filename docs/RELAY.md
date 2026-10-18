# 三工具接力操作

唯一工作目录：

```sh
cd /Users/yuchen/.codex/.chatgpt-projects/g-p-6ad134357ce081919b8abd0e80cc78bd/dungeon-raid-independent
```

## 用户切换工具

停止前一个 AI 的写入后，在同一终端目录任选一条：

```sh
./scripts/relay.sh start codex
./scripts/relay.sh start claude
./scripts/relay.sh start gemini
```

脚本自动定位项目、检查活动任务、传入统一续做指令，保留工具默认交互/审批设置。它不切换分支、不新建项目、不恢复别家聊天，也不监测额度或自动轮换。

当前可执行 Codex CLI；Claude 桌面应用已安装并完成过本项目的 Code 接力，但 `claude` 命令仍不在 PATH。Gemini CLI 尚未发现。以上 start 命令使用命令行工具；缺工具时会明确停止。使用已有 Claude 桌面应用时，进入「Code → 本电脑」，选择本项目目录，发送下段接手指令即可。要使用终端入口时，再按 [Claude Code 官方安装说明](https://code.claude.com/docs/en/setup) 或 [Gemini CLI 官方安装说明](https://geminicli.com/docs/get-started/installation/) 配置命令行并确认 `claude --version` / `gemini --version` 可执行。

桌面接手指令：“读取 AGENTS.md、PROJECT_STATE.md 和 TASKS.md，先运行 `./scripts/relay.sh check`，检查继承修改，按共享规则认领首个未完成任务；完成一个可验收单元后检查、提交、更新状态并 handoff。”同一目录始终只有一个写入者。

在 Codex 桌面端也可直接选择这个实际项目目录，再输入“读取 AGENTS.md，先做 relay check，按 TASKS.md 从中断处继续”。不要打开旧 ZIP 或较早 investigation 目录继续写。

## 每一位 AI 的操作

```sh
./scripts/relay.sh check
# 阅读完整 git diff、git diff --cached 及未跟踪文件，识别继承修改
./scripts/relay.sh begin claude T010
# 按 TASKS.md 做一个小单元，保存代码并运行针对性验证
./scripts/relay.sh verify
./scripts/relay.sh checkpoint claude '完成内容；失败或边界；下一步'
# 更新状态/任务，仅暂存明确审阅的文件或补丁
git add -- docs/PROJECT_STATE.md docs/TASKS.md
git diff --cached
git diff --cached --check
git commit -m 'docs: record verified recovery evidence'
./scripts/relay.sh handoff claude '完成内容；验证路径；下一任务'
```

以上工具名替换为 codex / gemini 即可。若任务涉及源码，明确追加本轮修改的文件，不照抄文档示例漏提交代码。继承的暂存内容须保持原样并单独审阅，不自动把整个 index 提交出去。没有可验收改动就保留现场和断点，不强行制造提交。

`check` 是只读检查，不运行模型、构建或测试，不写日志/锁。`verify` 在隔离目录构建全部 20 模块并跑两个示例和五组验证（补位、生成、特殊动作、联合链条、攻击护甲损耗）；`verify --full` 跑全部 21 个 verify 脚本。日志及新报告在 `.relay/runs/<时间>/`；`.relay/latest-validation.json` 提供最近运行状态。进行中/失败/输入哈希不一致的报告不能作为通过证据。

## 突然额度中断

1. 先停止旧工具，并在新工具只读运行 `check`、读 diff 和 `.relay/active/owner.json`。
2. 确认旧工具不再写入后，执行下面命令。不要仅凭锁“很旧”就接管。

```sh
./scripts/relay.sh recover gemini T010 --previous-stopped
```

3. 脚本先保存当前现场，再把旧活动记录保留为 `.relay/interrupted-*`，新建接管记录。旧代码、暂存区和未跟踪文件都不覆盖。
4. 阅读最新断点中的 state.json、staged.patch、unstaged.patch、untracked/ 和当前磁盘；补丁用于查证/备份，不直接重复 apply。跑验证，确认断点后从原任务最小步骤继续。

checkpoint 和 handoff 快照只覆盖 Git 中的差异与非忽略未跟踪文件；忽略的原版/素材/大依赖仍保留在原路径，需另行完整离线备份。无 Git/无依赖时不能靠快照伪造一个可运行项目。活动锁为合作式单写入约定，不拦截工具私自写文件；同一工作目录不要并行开多个开发 AI。

## Git 与远端

先做一个通过验证的小改动再原子提交。提交已发布后需要撤销时用新的 revert 提交；不要改写别人的历史。工作区有修改时禁止强切分支、清理、自动 stash 或覆盖。

现在只有本地 main，没有远端。未来明确授权后才讨论私有 GitHub；上传前审查所有待上传路径和完整历史，排除 IPA、原版程序、资源、原始字节/汇编、个人账号及密钥。忽略规则不替代版权/内容审查。不在接力脚本里提供自动 push。

## 入口兼容依据

Codex 本机 `--help` 已核对可使用位置参数传入初始提示。Claude 使用 `claude "提示"`，Gemini 使用 `gemini -i "提示"` 保持交互，依据 [Claude CLI](https://code.claude.com/docs/en/cli-reference) 与 [Gemini CLI](https://geminicli.com/docs/cli/cli-reference/)。CLAUDE.md / GEMINI.md 的 `@AGENTS.md` 依据 [Claude 导入说明](https://code.claude.com/docs/en/memory) 与 [Gemini memory import](https://geminicli.com/docs/reference/memport/)。核对日期为 2026-10-17；安装后仍须确认本机版本及上下文加载。当前没有真实启动 Claude/Gemini 验证账号或模型能力。
