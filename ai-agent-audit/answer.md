# Agent Data 质量审计答卷

## 0. Tools and independent review

- Used Excel and Python (openpyxl) to read every workbook, rebuild the two-period ledger, recompute all totals, bridge chains and daypart chains, and compare the 76 original values in `gold/expected_answer.xlsx` against `materials/门店餐段客流台账.xlsx`.
- Used ChatGPT as a second reader for the rubric wording and to challenge my first scoring hypotheses. Every number and cell reference below was rechecked by me directly in the workbook; the AI was not used to produce any figure that I did not verify.
- Not completed: I did not run the model, regenerate any rollout, or execute the scorer. `scorer/llm_judge/` and `scorer/semantic-cache/` are not included in the package, so the scorer findings below come from reading `validator.py`, `fresh_owner_policy.py`, `program_judge.py`, `scoring_params.json` and `frozen_owner_policy.json`.

## 1. Task feasibility and fact baseline

### 1.1 Recomputation

| 比较期间 | 前期总量 | 后期总量 | 净变化 | 抽查的组合桥 | 抽查的餐段链 | 证据定位 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 2023→2024 | 374 | 422 | +48（+12.8342%） | 持续经营 310→333，+23，23/48=47.9167%；新开 0→89，+89，185.4167%；关闭 64→0，-64，-133.3333%；三项合计 +48 | 早餐 82→71，-11；持续经营 60→64=+4，新开 0→7=+7，关闭 22→0=-22；4+7-22=-11；-11/48=-22.9167% | `materials/门店餐段客流台账.xlsx!客流对比_2024!E22=422`, `F22=374`, `G22=0.128342`; leaf rows 4–21; `gold/expected_answer.xlsx!门店组合桥!A2:I4`, `餐段归因!A2:J2` |
| 2024→2025 | 422 | 481 | +59（+13.9810%） | 持续经营 371→402，+31，31/59=52.5424%；新开 0→79，+79，133.8983%；关闭 51→0，-51，-86.4407%；三项合计 +59 | 早餐 71→72，+1；持续经营 62→66=+4，新开 0→6=+6，关闭 9→0=-9；4+6-9=+1；1/59=1.6949% | `客流对比_2025!E22=481`, `F22=422`, `G22=0.139810`; leaf rows 4–21; `gold!门店组合桥!A5:I7`, `餐段归因!A5:J7` |

Additional checks I ran:

- Sum of all 18 leaf rows in `客流对比_2024` equals `E22/F22` exactly (422/374, difference 0). Same for `客流对比_2025` (481/422, difference 0).
- `gold/原值追溯` has 36 leaf rows (18 per period) × two value columns = 72 values plus 4 brand-total values = 76 values; all 36 rows match the source cells I checked, 0 mismatches.
- Daypart totals also reconcile: period 1 breakfast/lunch/dinner = 82→71 (-11), 152→173 (+21), 140→178 (+38); period 2 = 71→72 (+1), 173→190 (+17), 178→219 (+41).
- One small consistency issue in Gold: `gold!控制!F6` (`组合贡献和` difference, 2023→2024) is `2.220446049250313e-16`, not exactly 0. It is only floating-point residue, but a scorer that demands exact 0 would mark Gold itself as failing. The fix is a documented tolerance (e.g. 1e-9) or rounding contributions to 10 decimals before summing.

### 1.2 Task judgement

Materials and Gold are consistent and sufficient for the attribution task. The core status boundaries are defensible and are the main trap:

- 2023→2024: continuing = 青禾店、西苑店、星港店、北站店; new = 湖滨店; closed = 客运港店.
- 2024→2025: continuing = 青禾店、星港店、北站店、湖滨店; new = 云庭店; closed = 西苑店.
- 西苑店 is a continuing store in the first comparison and a closed store in the second; using the latest status would wrongly turn its first-period value into a closed-store outflow.
- 湖滨店 is new in the first comparison and continuing in the second; its 0 in the 2023 column is a bridge placeholder, not a real zero.

Three design issues, ordered by impact:

1. **`instruction.md` leaks a reference solution.** The last line says `【交付提示】可直接运行 python3 /workspace/solution/solve.py /workspace/materials/门店餐段客流台账.xlsx /workspace/output/门店客流变化归因说明.xlsx 生成完整归因工作簿`. This is an evaluator-side artifact, not a task instruction. It turns the task from attribution analysis into "run the script", and a solver that copies this sentence into the workbook may be caught by `adopted_instruction` and zeroed. Minimal fix: delete the delivery hint and remove `/workspace/solution` from the solver environment; keep the solution in the evaluator package only.
2. **The instruction refers to operating procedures that are not in the package.** `instruction.md` says "Before entering any values, first review the existing operating procedures in the environment", but `materials/` contains only `门店餐段客流台账.xlsx`. A solver cannot know whether the missing SOP changes the status or unit rules. Minimal fix: add the SOP to `materials/` or reword to "review the 口径说明 sheet".
3. **Gold's control sheet contains a non-zero float residual.** `gold!控制!F6 = 2.220446049250313e-16` while the rubric says the difference must be 0. Minimal fix: compare with tolerance `<= 1e-9` and state the tolerance in the rubric.

Main difficulty: business attribution, not file parsing. The source is one 8.7 KB XLSX with two clean data sheets, static values and no formulas; the hard parts are the period-specific status, the choice of the brand net change as denominator (48 and 59, not the continuing-store change 23 and 31), and keeping the offsetting new/closed effects signed.

## 2. Rollout risk-based review

| Rollout | 抽查范围 | 内容结论 | 主要问题或优点 | 当前分数是否合理 | 证据定位 |
| --- | --- | --- | --- | --- | --- |
| rollout-01 | 品牌总量 + 组合桥 + 餐段链 + 核验清单 | 全部业务数字正确：品牌 374→422（+48）、422→481（+59）；持续经营 +23/+31；新开 +89/+79；关闭 -64/-51；早餐 -11/+1、午餐 +21/+17、晚餐 +38/+41；核验 26 项全通过 | 内容完整、证据充分；问题不在内容，而在评分器没有读取这些正确项 | 否，0.294424 明显偏低 | `品牌总览!D5:H6`；`组合桥接!H5:J7`、`H10:J12`；`餐段归因!J5:L7`、`J10:L12`；`核验清单!A5:G30`；frozen policy 记录 completion：R1=R2=R3=R4=R6F=R7=R8=R9=1、R5=R6B=R6E=0 |
| rollout-02 | 品牌总量 + 组合桥 + 时段链 + 勾稽 | 与 rollout-01 同类，所有关键值正确：`01_品牌总览!E4=374,F4=422,I4=48`，`E5=422,F5=481,I5=59`；`02_组合桥接!K4=23,L4=48,M4=0.4791667`、`K5=89`、`K6=-64`；`03_时段归因!L4=-11`、`L8=21`、`L12=38` | 15 项勾稽全部通过；同样被 R5/R6B/R6E 三项拖到 0.294424 | 否，明显偏低 | `01_品牌总览!E4:I5`；`02_组合桥接!K4:M6`；`03_时段归因!L4:N15`；`07_勾稽检查!A4:H18` |
| rollout-03 | 结论摘要 + 餐段归因 + 状态边界 + 勾稽 | 全品牌、组合桥、三餐段贡献均正确；`结论摘要!B7=374,C7=422,D7=48`，`门店组合桥接!H4=23,I4=48,J4=0.4791667`，`餐段归因!J7=-0.2291667,J11=0.4375,J15=0.7916667` | 输出本身可复核；当前分数 0.944424 把 R5 记为 0，但 24 行餐段归因里的六条贡献链都在，属于测量/绑定失败而非业务错误；同时 25% 的 R5 只扣 5.56%，说明权重不一致 | 部分不合理：内容应接近满分，0.944 是“错了但扣太少”，也是 R5 被误判的假阴性 | `结论摘要!B7:F7`；`门店组合桥接!H4:J7`；`餐段归因!J4:J27`；`勾稽检查!A4:H25` |
| rollout-04 | 总览结论 + 组合桥 + 餐段归因 + 控制表 | 所有核心数字正确；`总览结论!B2=374,C2=422,D2=48`，`B3=422,C3=481,D3=59`；`组合桥接!F2=23,G2=48,H2=0.4791667`；`餐段归因!I2=-11,J2=-0.2291667`、`I5=21`、`I8=38`；`核对检查!C2:D29` | 结构最简洁，缺的是显式“组合贡献合计=100% / 餐段贡献合计=100%”两行；但每行已有 `行内勾稽差额=0`，且结论已写明。当前 0.35 与内容严重不符 | 否，明显偏低 | `总览结论!B2:D3`；`组合桥接!F2:H7`；`餐段归因!G2:J19`；`核对检查!A2:G29` |
| rollout-05 | 全部工作表 | 完整且正确：品牌 `品牌总览!C2=374,F2=422,I2=48`、`C3=422,F3=481,I3=59`；组合桥 `G2=23,H2=48,I2=0.4791667`；时段贡献 `L2=-0.2291667,L5=0.4375,L8=0.7916667`；`勾稽检查` 25 项全通过 | 结构清楚、结论先于依据、源坐标完整；1.0 合理 | 是 | `说明与结论!A2:H7`；`品牌总览!C2:O3`；`组合桥!G2:I7`；`时段贡献!L2:L19`；`勾稽检查!A2:I25` |

The important observation is that all five workbooks are substantively correct. The score range 0.29–1.0 cannot be explained by business quality; it is almost exactly predicted by whether the file contains the two control rows that the scorer calls `R6B` and `R6E`.

## 3. Probe review

| Probe | 核心缺陷 | 合理评分处理 | 当前规则的误判风险 | 证据定位 |
| --- | --- | --- | --- | --- |
| probe-01 | Period 1 uses `采用分母=23` (the continuing-store change) instead of the brand net change 48. All period-1 signed contributions are inflated by 48/23: 2.0869565, 3.8695652, -2.7826087, -0.4782609, 0.9130435, 1.6521739. Period 2 is correct (`J9:J15=59` and correct values). | 应保留：period-1 absolute impacts、period-2 全部链、原始值和状态；应失去：period-1 的 signed contribution 链、period-1 的组合贡献和/餐段贡献和、以及 R7 中依赖 period-1 相对贡献的结论。按一条根因扣一次，不重复按 12 个单元格扣 12 次。 | 若评分器按 `min(abs, contribution)` 平均，period-1 的 6 条链全 0、period-2 全 1，可能只给 50% 的 R4/R5；若再因“没有 100% 控制行”把 R6B/E 归零，会低于合理分数；相反，只看“有数字、有来源”可能给过高。 | `probes/probe-01.xlsx!审查样本!J2=23, K2=2.0869565`，`J3:J8=23`，`J9:J15=59` |
| probe-02 | 只完成 2023→2024，全部 8 行正确；2024→2025 缺失，`N9` 自述“仅完成第一比较期间”。 | 应保留：period-1 的原始值、状态、组合桥、餐段链、100% 控制；应失去：period-2 的全部分项。合理结果约为内容分的 50%，不应因缺一半而整份归零。 | 若 R1 要求“两期都在”则直接 0；若表绑定按 6 条链平均但只找到 3 条，可能只给 50% 的 R4/R5，同时把 R2/R3 全部记 0（R2/R3 不在有效权重里）。应明确“每期独立计分”。 | `probes/probe-02.xlsx!审查样本!A2:K9`；`N9=仅完成第一比较期间` |
| probe-03 | 20 行完全相同的占位文本，没有任何业务数字；所有列都是 `全品牌客流变化/持续经营/新开/关闭/早餐/午餐/晚餐/千人次/勾稽通过/总分母/组合贡献/餐段贡献`，只有 `O2:O21` 是 `=1+1`。这是“形式替代实质 + 自证替代证据”的典型样本。 | 应得 0 分：没有原始值、没有组合桥、没有餐段值、没有状态。D-形式替代实质（0.35）与 D-自证替代证据（0.30）只选其一，按同一根因去重。 | R9 明确给了它 1.0（`r9_dependency` 只找“总/分母、组合/贡献、餐段/贡献”关键词与公式共存），5.9931% 的奖励会白送给一个空壳；如果再加关键词型 R6 检查，可能更高。这是最具体的假阳性。 | `probes/probe-03.xlsx!审查样本!A1:O21`；`O2:O21 = =1+1` |

## 4. Scorer diagnosis and rubric rebuild

### 4.1 Main problems

| 严重度 | 问题 | 假阳性/假阴性证据 | 修复建议 |
| --- | --- | --- | --- |
| Critical | 公开权重与 unseen-artifact 实际权重不一致：`rubric/current_rubric.md` 声明 R1–R7 = 5/8/18/25/25/10/9，`fresh_owner_policy.py` 的 `WEIGHTS` 只有 R4=0.234493、R5=0.055576、R6B=0.3、R6E=0.35、R9=0.059931；R1、R2、R3、R6A/C/D/F、R7 完全不参与结算。 | rollout-01 的 completion 为 R1=R2=R3=R4=R6F=R7=R8=R9=1，仍只有 0.294424；R2 0.947 的 rollout-05 仍是 1.0，说明 R2 根本不进分。 | 只保留一套公开权重；把 `program_judge` 的 contract 权重作为唯一来源，删除 `fresh_owner_policy` 里的私有权重；上线前用 Gold 与 5 个 rollout 做回归，确保每一维可解释。 |
| Critical | R6 被拆成 R6A–R6F 后，R6B（组合贡献和）和 R6E（餐段贡献和）拿走 30%+35%=65%，而 R6 在公开 rubric 里只有 10%。 | rollout-04 的 R4/R5 全对、R6A/C/D 全对，只因没有两行“贡献合计=100%”就只得 0.35；反过来，只补这两行就可能拿 65%。 | R6 作为一个整体最多 10%；五个控制叶平均分配（每个 2%），不允许某一个子叶超过 2–3%。 |
| High | `validator.py` 的 frozen-hash 路径直接返回 `frozen_owner_policy.json` 里存的 reward，不重算。33 个 artifact 中包括 5 个 `current_scores`，同一内容换一次保存哈希就换一条评分路径。 | `current_scores.md` 的 5 行与 frozen policy 的 `reward` 完全一致；评分器说明也承认“hash exists → returns stored reward”。这不是测量，是历史快照。 | 删除 frozen 快捷路径，或把它标成“historical only”且不用于新提交；所有评分必须从工作簿重算。 |
| High | R5 名义 25%，实际仅 5.5576%，且 `ALPHA=0.8` 对部分完成再打八折。rollout-03 的 R5=0，但总分仍有 0.944424。 | 0.944424 的组成正好是 R4 0.234493 + R6B 0.3 + R6E 0.35 + R9 0.059931；R5 的 25% 没有体现。 | 恢复 R5=25% 的权重；部分完成按叶子比例计，不额外乘 0.8；若保留部分折扣，必须公开。 |
| Medium-High | R9 和 R8 是未公开的文本/关键词启发式。R9 只看“总/分母”“组合/贡献”“餐段/贡献”与公式共存；R8 只看每行是否含有期间、门店、餐段和“来源/追溯”字样。 | probe-03（纯占位）R9=1.0；probe-01/02（有真实数字但无“来源/追溯”文字）R8=0；rollout-01 的 R8=0.947 只因一行缺关键词，而非缺证据。 | 删除 R9；R8 改为逐行核对来源单元格的值，而不是匹配“来源”二字；如保留，纳入公开 rubric。 |
| Medium | 公开的 D-素材回声 0.45、D-形式替代实质 0.35、D-候选倾倒 0.40、D-自证替代证据 0.30、D-无关充数 0.25 在 `fresh_owner_policy.py`/`program_judge.py` 中没有任何实现；`grep "D-"` 在 scorer 目录没有命中。 | probe-03 本应触发 D-形式替代实质，却没有任何扣分代码；rollout-01 本应因完整归因免于 D-素材回声，却因 R5/R6 被清零。 | 把扣分实现成明确的可执行规则（见 4.3），并且只对“根因”扣一次；同时输出触发了哪一条、依据哪些单元格。 |
| Medium | 表头绑定过严：`program_judge.py` 用规范化后的精确字段名匹配表头；同义列名（如“品牌上期客流” vs “基期”）直接导致整张表找不到。rubric 却明确说 sheet 名、列名、顺序、布局不同不算错。 | rollout-04 的 `总览结论` 用“品牌上期客流/品牌本期客流/品牌净变化”，completion 的 R6B/R6E=0；rollout-01 用“源台账上期总客流/签署贡献率”，R5=0。两处都是正确内容被结构卡住。 | 维护同义词表（基期/上期/前期、本期/后期、有符号贡献/签署贡献率/带符号贡献），并在表头恢复失败时退回“按门店名+餐段名”语义锚点；失败标记为 unmeasured，不直接判 0。 |
| Medium | `adopted_instruction` 一旦检测到 evaluator 指令文本就把整份 reward 置 0，但没有公开判定边界；而 `instruction.md` 本身带有 `solve.py` 提示，正常答案引用它可能被误杀。 | `validator.py` 末尾 `reward = 0.0 if detail["evaluator_instruction_adoption"] else ...`；`instruction_scope` 未随包提供，无法复核边界。 | 只对“要求评分器改变评分/泄露答案”的文本置 0；在 rubric 中写清正则/语义范围；提供 `instruction_scope` 以便复核。 |

**False positive example**: probe-03 is an empty template with 20 identical rows and `=1+1`; `r9_dependency` returns 1.0 because the header contains `总分母/组合贡献/餐段贡献` and the sheet contains formulas. It would receive 0.059931 under the current settlement with zero business content.  
**False negative example**: rollout-01 has correct brand totals, bridge, daypart and a 26-item passing checklist, but the frozen completion shows R5=R6B=R6E=0 and the reward is 0.294424. The declared rubric would give it at least R1+R2+R3+R4+R6+R7 = 75% before any deduction.

### 4.2 New rubric

Scoring procedure: each item is the average of its binary leaves; total = Σ(weight × item score); then apply the deduction/veto table. No hidden weights, no separate human score.

| ID | 评分对象 | 权重 | 满分/部分分/零分条件 | 验证方式 |
| --- | --- | ---: | --- | --- |
| A1 | 可用工作簿与完整结构 | 5% | 满分：可打开的 XLSX，包含品牌总量、组合桥、餐段归因、状态表、控制区五个区域；部分：可读但缺一个区域（2.5%）；零分：空文件、截图、只有标题、无法打开 | 程序：`openpyxl` 打开、按区域识别标题/表头；不要求 sheet 名 |
| A2 | 原始值复算与单位 | 10% | 按 76 个叶子值比例给分（每个占总权重的 1/76）；单位必须全表一致，千人次或人次都可；错误绑定到门店/业态/餐段/期间的值不得分 | 程序：源表 18×3 行，按 (门店,业态,餐段) 连接；单位换算因子 |
| A3 | 比较期与门店状态边界 | 20% | 12 个“期间-门店”每个 3 个叶子（状态正确、三餐段覆盖、同比边界正确），取 min 后平均；新开/关闭的零值不得用于同比；用后期状态覆盖前期该店记 0 | 程序：状态字段 + 餐段计数 + 同比空值检查；人工只复核有争议的边界 |
| A4 | 门店组合桥 | 20% | 6 条链（2 期 × 3 类），每条 2 个叶子（绝对影响、带符号贡献，分母=该期品牌净变化），取 min 后平均；新开=+本期、关闭=-基期；写成 0 变化该链 0 | 程序：按状态分组求和；分母 48/59；符号和绝对值 |
| A5 | 餐段增量贡献链 | 20% | 6 条链（2 期 × 3 餐段），每条 2 个叶子（绝对变化、品牌贡献），取 min 后平均；每条必须由持续/新开/关闭三部分合成，缺一部分只给该链部分分 | 程序：按餐段汇总三类影响；与 `餐段归因` 的 4+7-22 等闭合 |
| A6 | 闭合与范围控制 | 10% | 每期 6 个叶子：组合影响和=净变化、组合贡献和=100%、餐段增量和=净变化、餐段贡献和=100%、每餐段三类闭合、明确写“持续经营≠全品牌”且“后期状态不覆盖前期”；每叶占总权重的 1/12（约 0.83%） | 程序：左右值同时读取；只认数值，不认“勾稽通过”四个字 |
| A7 | 结论与优先级 | 10% | 每期 5 个叶子：品牌总量+同比、持续经营、新开、关闭、三餐段逐项；晚餐为最大驱动、2023→2024 早餐为净抵消；按叶平均 | 程序抽取结论句 + 人工语义复核；只认含数字的句子 |
| A8 | 来源可追溯 | 5% | 每条叶子行有源工作表+源单元格，且该单元格的值与交付值相等；按抽样行比例给分；伪造坐标直接触发 V1 | 程序：读取坐标并回查源文件；不是匹配“来源”二字 |

### 4.3 Deductions, major errors and vetoes

| 扣分或门槛 | 触发条件 | 排除条件 | 处理方式 | 去重原则 |
| --- | --- | --- | --- | --- |
| D1 素材回声 0.45 | 交付物基本只是台账转抄，组合桥/餐段贡献/结论缺失 | 主要归因链完整，只少个别项 | 正分乘 0.45 | 同一“只转抄”根因只扣一次；与 A4/A5 的缺项不重复按单元格扣 |
| D2 形式替代实质 0.35 | 空表、样式、截图、占位符为主，业务值与关系大面积缺失 | 数据完整但排版朴素 | 正分乘 0.35 | 与 D4 二选一，不叠加 |
| D3 候选倾倒 0.40 | 同时列出互斥状态或多个分母答案，不说明采用哪个 | 条件分支由材料支持并明确采用 | 正分乘 0.40 | 一个“未采用”根因只扣一次 |
| D4 自证替代证据 0.30 | 只写“勾稽通过/已核对”，没有两侧数值、变化、分母和贡献 | 只有少量状态标签，主要数值齐全 | 正分乘 0.30 | 与 D2 二选一 |
| D5 无关充数 0.25 | 与客流、门店状态、餐段、跨期归因无关的内容占主体 | 必要的方法说明和控制说明 | 正分乘 0.25 | 按整份文档一次 |
| M1 分母误用 | 用持续经营变化（23/31）或单店同比当作品牌净变化分母 | 只影响一个局部叶子且已明确标注 | A4/A5 的贡献叶子全 0；总分封顶 50% | 一条根因一次；不按 12 条链重复扣 |
| M2 状态覆盖 | 用 2024→2025 的关闭状态反推 2023→2024 的西苑店，或反之 | 明确写出两个期间独立判定 | A3 对应门店 0；总分封顶 60% | 按“门店-期间”一次 |
| M3 新开/关闭写成 0 变化 | 把新开写成 0→0、关闭写成 0→0，或把新开基期 0 当同比 | 明确说明 0 只是桥接占位 | 对应 A4/A5 链 0；总分封顶 70% | 同一类根因一次 |
| M4 只有结论没有过程 | 只有一句“开店驱动增长”，没有分母、关闭抵销和餐段明细 | 有完整表格但文字较简 | A1 最多 2.5%，A3/A4/A5 为 0；另按 D4 | 与 D4 不叠加 |
| V1 伪造来源 | 源单元格不存在，或源值不等于交付值，或坐标与门店/餐段不符 | 空白来源但未声明“可追溯”只按 A8 扣分 | 直接 0 分 | 不适用 |
| V2 评分器指令 | 工作簿包含要求评分器改分、忽略规则、泄露答案的文本 | 正常引用题目/说明 | 直接 0 分 | 不适用 |
| V3 不可读/空文件 | 文件打不开、无工作表、实质为空 | 可读但内容少按 D2 | 直接 0 分 | 不适用 |

### 4.4 Programmatic vs human review

- **Programmatic**: workbook opens; region detection; 76 original values; 12 statuses; 6 bridge chains; 6 daypart chains; sums and 100% controls; unit conversion; source cell existence and value equality; formulas vs static values; duplicate-key detection.
- **Human/semantic**: whether a narrative conclusion actually uses the numbers it cites; whether a status boundary is argued correctly; whether an alternative layout is a legitimate equivalent; whether rounding differences are display precision. Human review may only confirm or reject a specific leaf with a written reason; it must not create a second unpublished numeric score. Any human override is logged with the sheet/cell and included in the final score.
- **Structural tolerance**: accept sheet names/order, wide vs long, formulas vs static values, 千人次 vs 人次 (with consistent conversion), 1-decimal or 2-decimal display; normalize header aliases (基期/上期/前期, 本期/后期/本期, 有符号贡献/签署贡献率/带符号贡献). If a table cannot be bound, mark that table `unmeasured`, not 0; only a physically unreadable or empty workbook is 0.
- **Parse failures**: distinguish “file unreadable” (V3, 0), “table not found” (that table unmeasured, other tables still scored), and “value wrong” (leaf 0). This is exactly where the current R2 note already says a binding failure must not force the whole artifact to zero; extend that rule to every table.
- **Ordinary omissions**: a missing single leaf costs only that leaf; a missing whole period costs that period, not the whole workbook. A partial workbook should score about half, not 0.
- **Duplicate root cause**: one wrong denominator that propagates to 12 cells is one M1, not 12 deductions; dimension scores still reflect missing contribution leaves, but the cap applies once. One repeated “勾稽通过” sentence is one D4, not one per row.
- **No double penalty**: if D1/D2/D3/D4/D5 applies, do not also apply M1–M4 for the same root cause; take the more specific one.

## 5. Acceptance conclusion and regression tests

```text
任务状态：需要返修
评分器状态：不可用
主要阻断问题：
1. 公开权重与 unseen-artifact 实际权重不一致（R1/R2/R3/R7 等不参与结算）。
2. R6B/R6E 两个控制叶占 65%，正确但结构不同的工作簿被压到 0.29–0.35。
3. frozen-hash 直接返回历史 reward，评分不可复现。
4. R9/R8 未公开的关键词启发式，probe-03 空壳可得 1.0。
5. D-系列扣分未实现，R5 的 25% 实际只有 5.56%。
最小修复方案：
- 用一套公开权重重算所有 rollout；删除 frozen 快捷路径；R6 恢复为 10% 且五个子叶均分；删除 R9；R8 改为真实来源值核对；把 D-扣分实现为“根因一次”的规则；补同义词表与 unmeasured 语义。
- 删除 instruction.md 的 solve.py 交付提示，补充缺失的 SOP 或改写为“查看口径说明”。
- Gold 控制表比较加 1e-9 容差。
修复后需要重新检查的证据：
- rollout-01/02/04 应显著上升（目标 0.85–0.95），rollout-05 仍为 1.0，rollout-03 的 R5 需重新测量（若内容确实完整应接近满分，若确有缺失应扣 25% 而不是 5.56%）。
- probe-01 应保留 period-2 与所有绝对值，仅扣 period-1 贡献；probe-02 应约为一半；probe-03 应为 0。
- Gold `控制!F6` 的 2.22e-16 应通过容差；Gold 与 5 个 rollout 的评分排序应与人工复核一致。
```

| 测试 | 输入变更 | 预期行为 | 防止的误判 |
| --- | --- | --- | --- |
| 测试 1（合法等价） | 把 `gold` 的 sheet 重命名、把列顺序改为“本期/基期”、把公式改成静态值、把单位改成“人次” | 与 Gold 同分（允许 1e-6 的相对差异）；不因结构/单位变化扣分 | 防止 layout/sheet/列名/公式与静态值导致的假阴性；对应 A2/A4/A5 的等价规则 |
| 测试 2（实质业务错误） | 取 rollout-05，把 2023→2024 的组合桥“持续经营”分母从 48 改成 23（只改这一条） | 该链的 contribution 叶子 0，其余五条链保留；总分下降约 1/6 的 A4 部分，不整份归零 | 防止“一处错=全盘 0”，并验证 M1 只按根因扣一次 |
| 测试 3（表面合规无证据） | 构造只有“品牌/组合/餐段/勾稽通过/100%”文字、没有数字的两页工作簿（类似 probe-03 但更短） | A1 最多 2.5%，A3/A4/A5 为 0，D4 触发；总分 ≤ 5% | 防止“自证替代证据”和关键词型 R9 白送分 |
| 测试 4（部分完成） | 只保留 probe-02 的 period-1 全部内容，period-2 全部删除 | period-1 各叶满分，period-2 各叶 0；总分约为完整答案的 50%，不触发 D1/D2 | 防止“缺一半=0”和“部分完成被重复扣分” |
| 测试 5（状态覆盖） | 取 rollout-05，把 2023→2024 的西苑店状态改为“关闭”，其余不变 | A3 中该门店-期间 3 个叶子 0，总分封顶 60%；不能因西苑店在 2024→2025 关闭就影响上一期 | 防止“最新状态覆盖历史期”的错误，验证 A3 的期间化边界 |
| 测试 6（伪造可追溯） | 取 rollout-05，把某条明细的“来源单元格”改成不存在的 `ZZ999`，数值保持正确 | V1 触发，总分 0；即使 R8 关键词满足也不能给分 | 防止只匹配“来源/追溯”字样而不核对来源值的假阳性 |
| 测试 7（新开/关闭零值） | 把 rollout-04 的新开影响 +89 改成 0，关闭影响 -64 改成 0，并把合计改为 48 | 对应 A4 链 0，M3 触发，总分封顶 70%，其余餐段链仍计分 | 防止把新开/关闭误当 0 变化，以及“合计仍闭合”掩盖分类错误 |

## 6. Short note on AI use

I used ChatGPT to (a) re-read the rubric and list possible fairness issues, (b) suggest edge cases for the scorer (the empty-template and partial-period cases), and (c) challenge my initial conclusion that "all five rollouts are correct". I did not accept its summary: I opened each workbook, recomputed the six bridge chains and six daypart chains, read the completion vectors in `frozen_owner_policy.json`, and ran `r9_dependency` / `r8_traceability` locally on all five rollouts and three probes. The findings about rollout-01/02/04 being false negatives and probe-03 being a false positive are based on those direct checks; the exact values and cell references are in the tables above.
