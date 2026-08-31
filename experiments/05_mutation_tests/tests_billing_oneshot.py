import billing


import pytest


class TestProrate:
    def test_days_in_period_zero(self):
        assert billing.prorate(100, 5, 0) == 0.0

    def test_days_in_period_negative(self):
        assert billing.prorate(100, 5, -10) == 0.0

    def test_days_used_zero(self):
        assert billing.prorate(100, 0, 30) == 0.0

    def test_days_used_negative(self):
        assert billing.prorate(100, -5, 30) == 0.0

    def test_days_used_equals_period(self):
        assert billing.prorate(100, 30, 30) == 100.0

    def test_days_used_greater_than_period(self):
        assert billing.prorate(100, 45, 30) == 100.0

    def test_normal_proration(self):
        assert billing.prorate(300, 15, 30) == 150.0

    def test_rounding(self):
        assert billing.prorate(100, 1, 3) == round(100 / 3, 2)


class TestTierDiscount:
    def test_at_1000_boundary(self):
        assert billing.tier_discount(1000) == 0.15

    def test_above_1000(self):
        assert billing.tier_discount(1500) == 0.15

    def test_just_below_1000(self):
        assert billing.tier_discount(999.99) == 0.10

    def test_at_500_boundary(self):
        assert billing.tier_discount(500) == 0.10

    def test_just_below_500(self):
        assert billing.tier_discount(499.99) == 0.05

    def test_at_100_boundary(self):
        assert billing.tier_discount(100) == 0.05

    def test_just_below_100(self):
        assert billing.tier_discount(99.99) == 0.0

    def test_zero(self):
        assert billing.tier_discount(0) == 0.0

    def test_negative(self):
        assert billing.tier_discount(-50) == 0.0


class TestVolumePrice:
    def test_zero_units(self):
        assert billing.volume_price(0, 10) == 0.0

    def test_negative_units(self):
        assert billing.volume_price(-5, 10) == 0.0

    def test_exactly_10_units(self):
        assert billing.volume_price(10, 10) == 100.0

    def test_below_10_units(self):
        assert billing.volume_price(5, 10) == 50.0

    def test_11_units(self):
        # 10 full price + 1 at 10% off
        expected = round(10 * 10 + 1 * 10 * 0.9, 2)
        assert billing.volume_price(11, 10) == expected

    def test_exactly_50_units(self):
        # 10 full + 40 at 10% off
        expected = round(10 * 10 + 40 * 10 * 0.9, 2)
        assert billing.volume_price(50, 10) == expected

    def test_51_units(self):
        # 10 full + 40 at 10% off + 1 at 20% off
        expected = round(10 * 10 + 40 * 10 * 0.9 + 1 * 10 * 0.8, 2)
        assert billing.volume_price(51, 10) == expected

    def test_100_units(self):
        expected = round(10 * 10 + 40 * 10 * 0.9 + 50 * 10 * 0.8, 2)
        assert billing.volume_price(100, 10) == expected

    def test_1_unit(self):
        assert billing.volume_price(1, 25) == 25.0


class TestTax:
    def test_exempt_true(self):
        assert billing.tax(100, 0.1, True) == 0.0

    def test_exempt_true_ignores_amount(self):
        assert billing.tax(-50, 0.1, True) == 0.0

    def test_amount_zero(self):
        assert billing.tax(0, 0.1, False) == 0.0

    def test_amount_negative(self):
        assert billing.tax(-10, 0.1, False) == 0.0

    def test_normal_tax(self):
        assert billing.tax(100, 0.08, False) == 8.0

    def test_rounding(self):
        assert billing.tax(33.333, 0.1, False) == round(33.333 * 0.1, 2)


class TestOverageCharge:
    def test_used_equals_included(self):
        assert billing.overage_charge(100, 100, 1.0) == 0.0

    def test_used_below_included(self):
        assert billing.overage_charge(50, 100, 1.0) == 0.0

    def test_used_above_included(self):
        assert billing.overage_charge(150, 100, 2.0) == 100.0

    def test_zero_included(self):
        assert billing.overage_charge(10, 0, 1.5) == 15.0

    def test_rounding(self):
        assert billing.overage_charge(103, 100, 0.333) == round(3 * 0.333, 2)


class TestApplyCredit:
    def test_credit_zero(self):
        assert billing.apply_credit(100, 0) == (100, 0.0)

    def test_credit_negative(self):
        assert billing.apply_credit(100, -10) == (100, 0.0)

    def test_credit_equals_amount(self):
        assert billing.apply_credit(100, 100) == (0.0, 0.0)

    def test_credit_greater_than_amount(self):
        assert billing.apply_credit(100, 150) == (0.0, 50.0)

    def test_credit_less_than_amount(self):
        assert billing.apply_credit(100, 40) == (60.0, 0.0)

    def test_rounding_partial(self):
        result = billing.apply_credit(100, 33.333)
        assert result == (round(100 - 33.333, 2), 0.0)

    def test_rounding_leftover(self):
        result = billing.apply_credit(10, 33.333)
        assert result == (0.0, round(33.333 - 10, 2))


class TestLateFee:
    def test_days_late_zero(self):
        assert billing.late_fee(0, 1000) == 0.0

    def test_days_late_negative(self):
        assert billing.late_fee(-5, 1000) == 0.0

    def test_balance_zero(self):
        assert billing.late_fee(10, 0) == 0.0

    def test_balance_negative(self):
        assert billing.late_fee(10, -100) == 0.0

    def test_one_day_late_partial_week(self):
        # 1 day -> 1 week (ceil)
        assert billing.late_fee(1, 1000) == round(1000 * 0.015 * 1, 2)

    def test_exactly_7_days(self):
        assert billing.late_fee(7, 1000) == round(1000 * 0.015 * 1, 2)

    def test_8_days_rounds_to_2_weeks(self):
        assert billing.late_fee(8, 1000) == round(1000 * 0.015 * 2, 2)

    def test_14_days_exactly_2_weeks(self):
        assert billing.late_fee(14, 1000) == round(1000 * 0.015 * 2, 2)

    def test_cap_applied(self):
        # many weeks late should hit the 10% cap
        assert billing.late_fee(365, 1000) == round(1000 * 0.10, 2)

    def test_cap_boundary(self):
        # find weeks where fee exactly equals cap: 0.015*w = 0.10 -> w ~ 6.67 -> w=7 exceeds
        # w=6 -> fee = 9% < cap; w=7 -> fee=10.5% > cap -> capped at 10%
        days = 7 * 7  # 49 days -> 7 weeks
        assert billing.late_fee(days, 1000) == round(1000 * 0.10, 2)

    def test_no_cap_when_under(self):
        days = 6 * 7  # 42 days -> 6 weeks -> 9% fee, under cap
        assert billing.late_fee(days, 1000) == round(1000 * 0.015 * 6, 2)


class TestRefund:
    def test_within_full_refund_window(self):
        assert billing.refund(300, 5, 30, 10) == 300.0

    def test_exactly_at_window_boundary(self):
        assert billing.refund(300, 10, 30, 10) == 300.0

    def test_just_past_window(self):
        expected = round(300 * (30 - 11) / 30, 2)
        assert billing.refund(300, 11, 30, 10) == expected

    def test_days_used_equals_period(self):
        assert billing.refund(300, 30, 30, 10) == 0.0

    def test_days_used_exceeds_period(self):
        assert billing.refund(300, 35, 30, 10) == 0.0

    def test_partial_unused(self):
        expected = round(300 * (30 - 20) / 30, 2)
        assert billing.refund(300, 20, 30, 10) == expected

    def test_zero_window_zero_days_used(self):
        # days_used(0) <= window(0) -> full refund
        assert billing.refund(300, 0, 30, 0) == 300.0

    def test_zero_window_some_days_used(self):
        expected = round(300 * (30 - 5) / 30, 2)
        assert billing.refund(300, 5, 30, 0) == expected


class TestFinalInvoice:
    def test_basic_no_discount_no_overage_no_tax_no_credit(self):
        result = billing.final_invoice(
            base=100, units=0, unit_price=0, monthly_spend=0,
            used=0, included=100, overage_rate=1.0,
            tax_rate=0.1, exempt=True, credit=0
        )
        assert result == 100.0

    def test_with_volume_and_tier_discount(self):
        base = 0
        units = 20
        unit_price = 10
        monthly_spend = 1000
        used = 0
        included = 100
        overage_rate = 1.0
        tax_rate = 0.0
        exempt = True
        credit = 0

        vol = billing.volume_price(units, unit_price)
        line = base + vol
        line = line * (1 - 0.15)
        expected = round(line, 2)
        result = billing.final_invoice(base, units, unit_price, monthly_spend,
                                        used, included, overage_rate, tax_rate,
                                        exempt, credit)
        assert result == expected

    def test_with_overage_and_tax(self):
        base = 50
        units = 0
        unit_price = 0
        monthly_spend = 0
        used = 150
        included = 100
        overage_rate = 2.0
        tax_rate = 0.1
        exempt = False
        credit = 0

        line = base + billing.volume_price(units, unit_price)
        line = line * (1 - billing.tier_discount(monthly_spend))
        line += billing.overage_charge(used, included, overage_rate)
        t = billing.tax(line, tax_rate, exempt)
        total = line + t
        expected = round(total, 2)
        result = billing.final_invoice(base, units, unit_price, monthly_spend,
                                        used, included, overage_rate, tax_rate,
                                        exempt, credit)
        assert result == expected

    def test_with_credit_fully_covering(self):
        result = billing.final_invoice(
            base=50, units=0, unit_price=0, monthly_spend=0,
            used=0, included=100, overage_rate=1.0,
            tax_rate=0.0, exempt=True, credit=1000
        )
        assert result == 0.0

    def test_with_credit_partial(self):
        base = 100
        credit = 30
        line = base
        expected_before_credit = round(line, 2)
        total, _ = billing.apply_credit(expected_before_credit, credit)
        result = billing.final_invoice(
            base=base, units=0, unit_price=0, monthly_spend=0,
            used=0, included=100, overage_rate=1.0,
            tax_rate=0.0, exempt=True, credit=credit
        )
        assert result == round(total, 2)

    def test_full_combination(self):
        base = 200
        units = 60
        unit_price = 15
        monthly_spend = 750
        used = 500
        included = 300
        overage_rate = 0.5
        tax_rate = 0.07
        exempt = False
        credit = 50

        line = base + billing.volume_price(units, unit_price)
        line = line * (1 - billing.tier_discount(monthly_spend))
        line += billing.overage_charge(used, included, overage_rate)
        t = billing.tax(line, tax_rate, exempt)
        total = line + t
        total, _ = billing.apply_credit(round(total, 2), credit)
        expected = round(total, 2)

        result = billing.final_invoice(base, units, unit_price, monthly_spend,
                                        used, included, overage_rate, tax_rate,
                                        exempt, credit)
        assert result == expected

    def test_result_never_negative(self):
        result = billing.final_invoice(
            base=10, units=0, unit_price=0, monthly_spend=0,
            used=0, included=100, overage_rate=1.0,
            tax_rate=0.0, exempt=True, credit=9999
        )
        assert result >= 0.0