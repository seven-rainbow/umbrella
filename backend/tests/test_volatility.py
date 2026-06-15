from app.services.volatility import volatility_reason, volatility_score


def test_volatility_score_for_new_top_100k_entry():
    assert volatility_score(50_000, None, None, is_new_entry=True) == 0.9


def test_volatility_score_for_large_7_day_surge():
    assert volatility_score(120_000, -80_000, None) == 0.8
    assert volatility_reason(120_000, -80_000, None, False) == "7-day rank surge"


def test_volatility_score_for_large_30_day_drop():
    assert volatility_score(800_000, None, 300_000) == 1
    assert volatility_reason(800_000, None, 300_000, False) == "30-day rank movement"
