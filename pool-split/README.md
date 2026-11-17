# 奖池分账 pool_split

## 1. 一组会出错的输入

`pool_cents = 100`，`weights = [1, 1, 1]`。

当前实现返回 `[33, 33, 33]`：

- 实际的和：`99`
- 应有的和：`100`
- 差 `1` 分，属于"有人的钱没有发出去"。

原因是代码对每个人单独调用 `round()`，三个 `33.333...` 都被舍成 `33`，没有人负责把剩下的 1 分补上。`round()` 本身还是银行家舍入，遇到 `.5` 时结果也不直观，例如 `split_pool(1, [1, 1])` 会返回 `[0, 0]`，合计 0。

## 2. 修改 split_pool

改法是"先整除、再按余数补分"（最大余数法）：

1. 用 `divmod(pool_cents * weight, total)` 算出每人的整数份额和余数，全程整数运算，不经过浮点；
2. 把剩下的 `pool_cents - sum(shares)` 分，按余数从大到小依次补 1 分；
3. 余数相同时按原始下标靠前的优先，保证同一输入的结果稳定、可复现。

这样每个人的份额与精确值的差都小于 1 分，且总和严格等于 `pool_cents`。奖池为 0、某个人权重为 0、只有一个人参与这些情况也都成立。权重为空、权重和为 0、出现负数时直接抛 `ValueError`，不返回一个看起来正常但其实是错的结果。

完整代码见 `pool_split.py`。

## 3. 测试与两次运行输出

测试文件是 `test_pool_split.py`，覆盖：

- 100 分、`[1, 1, 1]` 这类会暴露问题的输入；
- 单人、零权重、奖池为 0、整除等边界；
- 8 组参数化输入 + 500 组固定种子的随机输入，逐组检查 `sum(result) == pool_cents`、份额非负且为整数、与精确值的误差小于 1 分；
- 空权重、权重和 0、负权重、负奖池的异常输入。

运行命令：

```bash
python -m pytest -q test_pool_split.py
```

### 3.1 未修改的代码上运行（失败）

把原始 `pool_split.py` 和同一份测试放在一起运行，结果：

```text
F..FFFF.FF....FF                                                         [100%]
...
FAILED test_pool_split.py::test_simple_equal_split_keeps_total - assert 99 ==...
FAILED test_pool_split.py::test_exact_division_has_no_remainder - assert [333...
FAILED test_pool_split.py::test_tie_breaks_by_original_index - assert [0, 0] ...
FAILED test_pool_split.py::test_total_is_always_conserved[100-weights0] - ass...
FAILED test_pool_split.py::test_total_is_always_conserved[1-weights1] - asser...
FAILED test_pool_split.py::test_total_is_always_conserved[999-weights3] - ass...
FAILED test_pool_split.py::test_total_is_always_conserved[100000-weights4] - ...
FAILED test_pool_split.py::test_random_inputs - assert 323991555 == 323991556
FAILED test_pool_split.py::test_invalid_inputs - Failed: DID NOT RAISE ValueE...
9 failed, 7 passed in 0.13s
```

关键的一条是 `test_simple_equal_split_keeps_total`：

```text
assert 99 == 100
 +  where 99 = total_of([33, 33, 33])
```

### 3.2 修改后的代码上运行（通过）

```text
................                                                         [100%]
16 passed in 0.05s
```

原始输出文件也放在 `_before/run_before.txt` 和 `run_after.txt`。

## 4. AI 使用说明

用了 ChatGPT 和 GitHub Copilot 辅助，具体过程如下。

**提问 1**：把原始 `split_pool` 发给 ChatGPT，问"这段代码在什么输入下会破坏总额相等，为什么"。

**回答**：它指出每个人独立 `round()` 会导致舍入误差累加，并给了 `100 / [1, 1, 1]` 和 `0.5` 两个方向；还提到 Python 3 的 `round` 是银行家舍入。

**是否直接采用**：没有。例子我自己在本地跑了一遍，`100 / [1, 1, 1]` 确实得到 `[33, 33, 33]`、合计 99；`split_pool(1, [1, 1])` 确实得到 `[0, 0]`。确认它说的现象属实，才把它写进第 1 节。

**提问 2**：问"保证总和不变有哪几种常见分法，哪个更适合这个场景"。

**回答**：给了"最后一个人兜底差额"和"最大余数法"两种。前者实现最简单，但差额永远落在最后一个人身上，权重相同时不公平；后者按余数分配，比较符合"按贡献分"的语义。

**是否直接采用**：采用了最大余数法的思路，但没有照抄它给的浮点版本。我自己改用 `divmod` 做整数运算，避免大数相乘后转 float 丢精度；补分顺序固定成"余数降序、下标升序"，保证结果可复现。

**提问 3**：让 Copilot 帮忙看测试有没有漏掉的边界。它提醒补"权重全为 0""奖池为 0""单人"这几种。我补进 `test_invalid_inputs` 和参数化用例里，并加了 500 组固定种子随机测试。

**如何确认正确**：所有测试都在本机实际运行过，未修改版本 9 条失败、修改后 16 条全过；随机测试的种子固定为 `20261117`，可以重复。代码里没有保留任何 AI 生成的注释或说明，最终版本我逐行读过。

## 5. 可选问题

- **测试覆盖**：8 组参数化 + 500 组随机 + 边界异常，除了"总额相等"还检查了每人份额与精确值的误差小于 1 分。
- **多出来/少掉的分给谁**：按余数从大到小补；余数相同给下标靠前的人。换一个人可行，只要把 tie-break 规则写清楚并固定下来即可，结果仍然满足总额相等。
- **还有哪些会出错的输入**：`pool_cents` 很小而人数很多（大量 0 分）、权重极大导致浮点精度丢失（原实现用 `/` 会出问题）、`weights` 含 0、`pool_cents = 0`、空列表。修改后的版本对这些都做了处理或明确抛错。
