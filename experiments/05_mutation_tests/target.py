"""Target module under test: pricing/eligibility logic rich in mutation points."""

def discount_rate(qty, is_member):
    """Tiered discount. qty>=100 -> 0.2; qty>=50 -> 0.1; else 0. Members get +0.05."""
    if qty >= 100:
        rate = 0.2
    elif qty >= 50:
        rate = 0.1
    else:
        rate = 0.0
    if is_member:
        rate = rate + 0.05
    return rate

def final_price(unit_price, qty, is_member):
    if qty <= 0:
        return 0.0
    rate = discount_rate(qty, is_member)
    gross = unit_price * qty
    return gross * (1 - rate)

def shipping_fee(weight, express):
    """Free over 20kg (standard). Express always 15. Else 5 + 0.5/kg."""
    if express:
        return 15.0
    if weight > 20:
        return 0.0
    return 5.0 + 0.5 * weight

def is_eligible(age, score, banned):
    """Eligible if not banned, age>=18, and score>=700."""
    if banned:
        return False
    return age >= 18 and score >= 700

def late_fee(days_late, amount):
    if days_late <= 0:
        return 0.0
    fee = amount * 0.01 * days_late
    if fee > amount * 0.25:
        fee = amount * 0.25
    return fee
