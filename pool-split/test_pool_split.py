import random

import pytest

from pool_split import split_pool


def total_of(shares):
    return sum(shares)


def test_simple_equal_split_keeps_total():
    # 100 分给三个权重相同的人，原实现会给出 [33, 33, 33]，合计只有 99。
    shares = split_pool(100, [1, 1, 1])
    assert total_of(shares) == 100
    assert shares == [34, 33, 33]


def test_single_person_gets_everything():
    assert split_pool(12345, [7]) == [12345]


def test_zero_weight_gets_nothing():
    assert split_pool(10, [0, 1]) == [0, 10]
    assert split_pool(0, [1, 2, 3]) == [0, 0, 0]


def test_exact_division_has_no_remainder():
    assert split_pool(10000, [1, 1, 1]) == [3334, 3333, 3333]
    assert total_of(split_pool(90, [1, 2, 3])) == 90


def test_tie_breaks_by_original_index():
    # 1 分钱分给两个权重相同的人：按余数相同、下标靠前优先，给第一个人。
    assert split_pool(1, [1, 1]) == [1, 0]
    assert split_pool(2, [1, 1, 1]) == [1, 1, 0]


@pytest.mark.parametrize(
    "pool_cents, weights",
    [
        (100, [1, 1, 1]),
        (1, [1, 1]),
        (7, [1, 2, 3, 4]),
        (999, [5, 5, 5, 5]),
        (100000, [17, 23, 41, 59]),
        (123456789, [1, 999999, 12345]),
        (0, [1, 2]),
        (50, [0, 0, 5]),
    ],
)
def test_total_is_always_conserved(pool_cents, weights):
    shares = split_pool(pool_cents, weights)
    assert len(shares) == len(weights)
    assert all(isinstance(s, int) and s >= 0 for s in shares)
    assert total_of(shares) == pool_cents


def test_each_share_is_one_cent_away_from_exact_value():
    pool_cents = 1000
    weights = [3, 7, 11, 13, 17]
    total = sum(weights)
    for share, weight in zip(split_pool(pool_cents, weights), weights):
        exact = pool_cents * weight / total
        assert abs(share - exact) < 1


def test_random_inputs():
    rng = random.Random(20261117)
    for _ in range(500):
        n = rng.randint(1, 30)
        weights = [rng.randint(0, 1000) for _ in range(n)]
        if sum(weights) == 0:
            weights[rng.randrange(n)] = 1
        pool_cents = rng.randint(0, 10**9)
        shares = split_pool(pool_cents, weights)
        assert len(shares) == n
        assert sum(shares) == pool_cents
        assert min(shares) >= 0


def test_invalid_inputs():
    with pytest.raises(ValueError):
        split_pool(100, [])
    with pytest.raises(ValueError):
        split_pool(100, [0, 0])
    with pytest.raises(ValueError):
        split_pool(100, [-1, 2])
    with pytest.raises(ValueError):
        split_pool(-1, [1, 1])
