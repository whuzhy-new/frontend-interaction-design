# 前端交互设计 / Frontend Interaction Design Skill

一个用于**前端交互设计与走查**的 Agent Skill（Claude Code / Codex / DSH 等兼容目录结构的 Agent 均可使用）。

它把"交互设计"从"好看的界面"拉回到可验证的工程问题：**用户在每个状态下都能预期下一步，出错能回来，且不用为系统的复杂度买单。**

## 能做什么

| 场景 | 产出 |
|---|---|
| 给需求、PRD、线框或一句"帮我设计个 X" | 交互规格 + 验收清单（状态机、五态、异步与错误、键盘与无障碍） |
| 截图、线上页面、组件代码、Figma 稿 | 分级走查报告（P0/P1/P2、逐条证据→影响→修法→验证、需确认、验收动作） |
| 整个项目、多个页面或入口一起看 | 主线报告 + 分册附录：按用户旅程切分、同一口径走查、合并去重后重新校准分级 |
| 新增/修改前端组件、样式、页面 | 复用检查 + token 约束 + 自检与回归记录 |
| 多个入口同一功能不一致、全站组件梳理、统一 Token | 功能组件地图 + 重复差异清单 + 统一规则 + 入口验收 |

## 安装

把本仓库整个目录放到 Agent 的 skills 目录下，目录名保持 `frontend-interaction-design`：

```sh
git clone https://github.com/whuzhy-new/frontend-interaction-design ~/.dsh/skills/frontend-interaction-design   # DeepSeek Harness
# 或
git clone https://github.com/whuzhy-new/frontend-interaction-design ~/.codex/skills/frontend-interaction-design # Codex
# 或
git clone https://github.com/whuzhy-new/frontend-interaction-design ~/.claude/skills/frontend-interaction-design # Claude Code
```

安装后在对话里描述任务即可触发，例如：

- 「这个设置页的保存按钮感觉怪怪的，帮我看看有没有交互问题」
- 「给电商结账流程写一份交互规格」
- 「review 整个项目的前端交互」
- 「首页和栏目页的新闻卡片样式不一致，帮我统一一下」
- 「这个按钮颜色写死成 #2563EB 了，怎么改成 token」

## 目录结构

```
SKILL.md                         # 入口：任务类型、五种模式、高风险自检、交付前自检
references/
  review.md                      # 走查方法：取证、运行时动作、分级校准、误报、报告写作
  checklists.md                  # 13 节检查清单（状态/反馈/表单/控件/导航/动效/触屏/数据/AI/无障碍/…）
  components.md                  # 组件交互规格库
  flows.md                       # 流程级交互（登录、支付、上传、权限、错误恢复、通知…）
  states.md                      # 五态、异步状态矩阵、加载策略、空态、错误文案、竞态
  pages.md                       # 页面类型（问题页、确认页、错误页、404、快速离开…）
  forms.md                       # 表单与校验
  data-ui.md                     # 数据界面：口径、时间、权限、对比、核对成本、导出
  consistency.md                 # 实现一致性：写码约束 + 按功能统一多入口
  product-context.md             # 值不值得做：场景、需求翻译、首发范围、指标
  research.md                    # 用户研究方法
  sources.md                     # 出处与延伸阅读
assets/
  spec-template.md               # 交互规格模板
  component-spec-template.md     # 单组件规格模板
  review-template.md             # 单页/组件走查模板
  project-review-template.md     # 全项目/多入口走查模板
scripts/
  scan_ui.py                     # 扫描 HTML/JSX/TSX/Vue，输出待确认的交互线索（线索不是判决）
  check_hardcodes.py             # 扫描裸颜色/px/字体/z-index/圆角线索（写后自检）
evals/                           # 技能触发与输出的评测用例
```

## 方法要点

- **先定主任务**：这个界面为谁完成什么，用户最可能在哪一步失败或放弃；优先级围绕它排。
- **证据分四级**：运行时 > 代码 > 截图 > 口述；只有代码时声明静态走查，运行时结论进「需确认」。
- **四段式问题**：证据（位置/行号/操作路径）→ 影响（谁、什么条件下）→ 修法（最小可行 → 重构）→ 验证（怎么确认改好了）。
- **统一分级**：P0 阻断/数据丢失/无法恢复；P1 明显摩擦或误解；P2 打磨。频率不自动降级，数字/时间/口径错误按 P1 起。
- **高风险自检 10 项**：状态复位、重复提交、超时与结果未知、竞态、错误恢复、键盘焦点、破坏性操作、未保存离开、三态区分、成功判定。
- **全项目走查**：按用户旅程切分 → 同口径分册 → 合并去重并重新校准分级 → 主报告 + 分册附录 + 截图。

## 脚本

```sh
python3 scripts/scan_ui.py <项目源码目录>
python3 scripts/check_hardcodes.py <改动路径...> [--json] [--fail]
```

两个脚本都只输出**线索**：报告里只写人工核对过的条目。

## 评测

`evals/` 提供触发用例与三类输出用例（走查、流程规格、组件规格），可用于本 Skill 修改后的回归。

## License

MIT
