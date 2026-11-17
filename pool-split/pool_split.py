"""
pool_split.py —— 每日瓜分奖池的分账逻辑

平台每天放一个奖池，当天达标的用户按贡献权重瓜分。
所有金额都是整数「分」，分完之后所有人的金额之和必须正好等于奖池总额。
"""


def split_pool(pool_cents: int, weights: list[int]) -> list[int]:
    """把 pool_cents 按 weights 的比例分给每个人，返回每人拿到多少分。

    返回列表与 weights 一一对应。
    """
    if not weights:
        raise ValueError("weights 不能为空")
    if any(w < 0 for w in weights):
        raise ValueError("weights 不能包含负数")
    if pool_cents < 0:
        raise ValueError("pool_cents 不能为负数")

    total = sum(weights)
    if total <= 0:
        raise ValueError("weights 之和必须大于 0")

    shares = []
    remainders = []
    for index, weight in enumerate(weights):
        share, remainder = divmod(pool_cents * weight, total)
        shares.append(share)
        remainders.append((remainder, index))

    # 先按整数份额分，剩下的几分钱按余数从大到小补给对应的人。
    # 余数相同时按原始下标靠前的优先，保证同样输入每次结果一致。
    left = pool_cents - sum(shares)
    for _, index in sorted(remainders, key=lambda item: (-item[0], item[1]))[:left]:
        shares[index] += 1

    return shares


if __name__ == "__main__":
    # 一个跑得通的例子：奖池 100 元，三个人权重相同
    print(split_pool(10000, [1, 1, 1]))
