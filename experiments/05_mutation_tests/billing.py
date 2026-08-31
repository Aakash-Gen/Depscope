"""Subscription billing engine: tiered discounts, proration, tax, overage, credits,
late fees, refunds. Deliberately branch-heavy with subtle boundaries -- a realistic
module where one-shot LLM tests may leave real gaps."""


def prorate(amount, days_used, days_in_period):
    """Charge for days actually used. Clamps to [0, amount]."""
    if days_in_period <= 0:
        return 0.0
    if days_used <= 0:
        return 0.0
    if days_used >= days_in_period:
        return round(amount, 2)
    return round(amount * days_used / days_in_period, 2)


def tier_discount(monthly_spend):
    """Loyalty discount by spend tier. >=1000 -> 15%; >=500 -> 10%; >=100 -> 5%; else 0."""
    if monthly_spend >= 1000:
        return 0.15
    elif monthly_spend >= 500:
        return 0.10
    elif monthly_spend >= 100:
        return 0.05
    return 0.0


def volume_price(units, unit_price):
    """Bulk pricing: first 10 units full price; 11-50 get 10% off; 51+ get 20% off.
    Discount applies per-unit within each band (graduated)."""
    if units <= 0:
        return 0.0
    total = 0.0
    full = min(units, 10)
    total += full * unit_price
    if units > 10:
        mid = min(units - 10, 40)
        total += mid * unit_price * 0.9
    if units > 50:
        high = units - 50
        total += high * unit_price * 0.8
    return round(total, 2)


def tax(amount, rate, exempt):
    if exempt:
        return 0.0
    if amount <= 0:
        return 0.0
    return round(amount * rate, 2)


def overage_charge(used, included, rate):
    """Charge for usage beyond the included allowance."""
    if used <= included:
        return 0.0
    return round((used - included) * rate, 2)


def apply_credit(amount, credit):
    """Apply account credit; balance never negative, unused credit is returned."""
    if credit <= 0:
        return amount, 0.0
    if credit >= amount:
        return 0.0, round(credit - amount, 2)
    return round(amount - credit, 2), 0.0


def late_fee(days_late, balance):
    """1.5% per week late, capped at 10% of balance. Partial weeks count as full."""
    if days_late <= 0:
        return 0.0
    if balance <= 0:
        return 0.0
    weeks = (days_late + 6) // 7
    fee = balance * 0.015 * weeks
    cap = balance * 0.10
    if fee > cap:
        fee = cap
    return round(fee, 2)


def refund(amount, days_used, days_in_period, full_refund_window):
    """Refund policy: within the full-refund window -> full refund; otherwise prorated
    refund for unused days; no refund if fully used."""
    if days_used <= full_refund_window:
        return round(amount, 2)
    if days_used >= days_in_period:
        return 0.0
    unused = days_in_period - days_used
    return round(amount * unused / days_in_period, 2)


def final_invoice(base, units, unit_price, monthly_spend, used, included,
                  overage_rate, tax_rate, exempt, credit):
    """Combine the pieces into a final invoice total (>= 0)."""
    line = base + volume_price(units, unit_price)
    disc = tier_discount(monthly_spend)
    line = line * (1 - disc)
    line += overage_charge(used, included, overage_rate)
    t = tax(line, tax_rate, exempt)
    total = line + t
    total, _ = apply_credit(round(total, 2), credit)
    return round(total, 2)
