import pytest
from target import discount_rate, final_price, shipping_fee, is_eligible, late_fee


class TestDiscountRate:
    def test_qty_below_50_non_member(self):
        assert discount_rate(1, False) == 0.0

    def test_qty_below_50_member(self):
        assert discount_rate(1, True) == pytest.approx(0.05)

    def test_qty_zero_non_member(self):
        assert discount_rate(0, False) == 0.0

    def test_qty_49_non_member(self):
        assert discount_rate(49, False) == 0.0

    def test_qty_50_boundary_non_member(self):
        assert discount_rate(50, False) == pytest.approx(0.1)

    def test_qty_50_boundary_member(self):
        assert discount_rate(50, True) == pytest.approx(0.15)

    def test_qty_99_non_member(self):
        assert discount_rate(99, False) == pytest.approx(0.1)

    def test_qty_100_boundary_non_member(self):
        assert discount_rate(100, False) == pytest.approx(0.2)

    def test_qty_100_boundary_member(self):
        assert discount_rate(100, True) == pytest.approx(0.25)

    def test_qty_large_non_member(self):
        assert discount_rate(1000, False) == pytest.approx(0.2)

    def test_qty_large_member(self):
        assert discount_rate(1000, True) == pytest.approx(0.25)

    def test_negative_qty_non_member(self):
        assert discount_rate(-5, False) == 0.0

    def test_negative_qty_member(self):
        assert discount_rate(-5, True) == pytest.approx(0.05)


class TestFinalPrice:
    def test_zero_qty_returns_zero(self):
        assert final_price(10.0, 0, False) == 0.0

    def test_negative_qty_returns_zero(self):
        assert final_price(10.0, -5, True) == 0.0

    def test_positive_qty_no_discount_non_member(self):
        assert final_price(10.0, 1, False) == pytest.approx(10.0)

    def test_positive_qty_no_discount_member(self):
        assert final_price(10.0, 1, True) == pytest.approx(1 * 10.0 * (1 - 0.05))

    def test_qty_at_50_tier_non_member(self):
        result = final_price(10.0, 50, False)
        expected = 50 * 10.0 * (1 - 0.1)
        assert result == pytest.approx(expected)

    def test_qty_at_50_tier_member(self):
        result = final_price(10.0, 50, True)
        expected = 50 * 10.0 * (1 - 0.15)
        assert result == pytest.approx(expected)

    def test_qty_at_100_tier_non_member(self):
        result = final_price(20.0, 100, False)
        expected = 100 * 20.0 * (1 - 0.2)
        assert result == pytest.approx(expected)

    def test_qty_at_100_tier_member(self):
        result = final_price(20.0, 100, True)
        expected = 100 * 20.0 * (1 - 0.25)
        assert result == pytest.approx(expected)

    def test_zero_unit_price(self):
        assert final_price(0.0, 100, True) == 0.0

    def test_qty_49_boundary_below_tier(self):
        result = final_price(10.0, 49, False)
        expected = 49 * 10.0
        assert result == pytest.approx(expected)

    def test_qty_99_boundary_below_top_tier(self):
        result = final_price(10.0, 99, False)
        expected = 99 * 10.0 * (1 - 0.1)
        assert result == pytest.approx(expected)


class TestShippingFee:
    def test_express_true_overrides_everything(self):
        assert shipping_fee(0, True) == 15.0

    def test_express_true_with_heavy_weight(self):
        assert shipping_fee(1000, True) == 15.0

    def test_express_false_weight_zero(self):
        assert shipping_fee(0, False) == pytest.approx(5.0)

    def test_express_false_weight_below_20(self):
        assert shipping_fee(10, False) == pytest.approx(5.0 + 0.5 * 10)

    def test_express_false_weight_at_20_boundary(self):
        # weight > 20 is required for free shipping; 20 itself is not free
        assert shipping_fee(20, False) == pytest.approx(5.0 + 0.5 * 20)

    def test_express_false_weight_just_above_20(self):
        assert shipping_fee(20.0001, False) == 0.0

    def test_express_false_weight_well_above_20(self):
        assert shipping_fee(50, False) == 0.0

    def test_express_false_negative_weight(self):
        assert shipping_fee(-5, False) == pytest.approx(5.0 + 0.5 * -5)


class TestIsEligible:
    def test_banned_overrides_all(self):
        assert is_eligible(30, 800, True) is False

    def test_banned_overrides_even_when_otherwise_ineligible(self):
        assert is_eligible(10, 100, True) is False

    def test_eligible_when_all_conditions_met(self):
        assert is_eligible(18, 700, False) is True

    def test_age_below_18(self):
        assert is_eligible(17, 800, False) is False

    def test_age_at_18_boundary(self):
        assert is_eligible(18, 700, False) is True

    def test_age_above_18_with_low_score(self):
        assert is_eligible(30, 699, False) is False

    def test_score_at_700_boundary(self):
        assert is_eligible(20, 700, False) is True

    def test_score_below_700(self):
        assert is_eligible(20, 699, False) is False

    def test_score_above_700(self):
        assert is_eligible(20, 701, False) is True

    def test_both_conditions_fail(self):
        assert is_eligible(10, 500, False) is False

    def test_not_banned_explicit_false(self):
        assert is_eligible(25, 750, False) is True


class TestLateFee:
    def test_zero_days_late_returns_zero(self):
        assert late_fee(0, 1000.0) == 0.0

    def test_negative_days_late_returns_zero(self):
        assert late_fee(-3, 1000.0) == 0.0

    def test_one_day_late_below_cap(self):
        assert late_fee(1, 1000.0) == pytest.approx(10.0)

    def test_days_late_just_below_cap(self):
        # cap triggers when fee > 25% of amount i.e. days_late*1% > 25% -> days_late > 25
        assert late_fee(25, 1000.0) == pytest.approx(250.0)

    def test_days_late_at_cap_boundary(self):
        # 25 days -> fee == 25% exactly, not > 25%, so not capped (same as above)
        result = late_fee(25, 1000.0)
        assert result == pytest.approx(1000.0 * 0.25)

    def test_days_late_just_above_cap_boundary(self):
        result = late_fee(26, 1000.0)
        assert result == pytest.approx(1000.0 * 0.25)

    def test_days_late_far_above_cap(self):
        result = late_fee(1000, 1000.0)
        assert result == pytest.approx(1000.0 * 0.25)

    def test_zero_amount(self):
        assert late_fee(10, 0.0) == 0.0

    def test_fractional_days_late(self):
        result = late_fee(2.5, 1000.0)
        assert result == pytest.approx(25.0)

import target


# --- mutation-targeted tests ---
def test_discount_rate_boundary_100():
    assert target.discount_rate(100, False) == 0.2

def test_final_price_zero_qty():
    assert target.final_price(10, 0, False) == 0.0

def test_late_fee_zero_days():
    assert target.late_fee(0, 1000) == 0.0

def test_late_fee_cap_boundary():
    assert target.late_fee(25, 1000) == 250.0



# --- mutation-targeted tests ---
def test_discount_rate_boundary_100():
    assert target.discount_rate(100, False) == 0.2

def test_final_price_zero_qty():
    assert target.final_price(10.0, 0, False) == 0.0

def test_late_fee_zero_days():
    assert target.late_fee(0, 1000.0) == 0.0

def test_late_fee_cap_boundary():
    assert target.late_fee(25, 1000.0) == 250.0



# --- mutation-targeted tests ---
def test_discount_rate_boundary_100():
    assert target.discount_rate(100, False) == 0.2

def test_final_price_zero_qty():
    assert target.final_price(10.0, 0, False) == 0.0

def test_late_fee_zero_days():
    assert target.late_fee(0, 1000.0) == 0.0

def test_late_fee_cap_boundary():
    assert target.late_fee(25, 1000.0) == 250.0

