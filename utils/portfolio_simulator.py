from __future__ import annotations


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def calculate_buy_simulation(
    current_qty: float,
    current_avg_price: float,
    current_market_price: float,
    add_qty: float,
    buy_price: float,
    fx_eur: float = 1.0,
) -> dict:
    """Calculate a buy/add-to-position simulation.

    Values without suffix are in the instrument currency. Values ending in `_eur`
    are converted using `fx_eur`.
    """
    current_qty = safe_float(current_qty)
    current_avg_price = safe_float(current_avg_price)
    current_market_price = safe_float(current_market_price)
    add_qty = safe_float(add_qty)
    buy_price = safe_float(buy_price)
    fx_eur = safe_float(fx_eur, 1.0) or 1.0

    current_cost = current_qty * current_avg_price
    additional_cost = add_qty * buy_price
    new_qty = current_qty + add_qty
    new_total_cost = current_cost + additional_cost
    new_avg_price = new_total_cost / new_qty if new_qty else 0.0
    new_market_value = new_qty * current_market_price
    estimated_gain = new_market_value - new_total_cost
    estimated_gain_pct = estimated_gain / new_total_cost * 100 if new_total_cost else 0.0

    return {
        "current_qty": current_qty,
        "current_avg_price": current_avg_price,
        "current_market_price": current_market_price,
        "current_cost": current_cost,
        "current_cost_eur": current_cost * fx_eur,
        "add_qty": add_qty,
        "buy_price": buy_price,
        "additional_cost": additional_cost,
        "additional_cost_eur": additional_cost * fx_eur,
        "new_qty": new_qty,
        "new_total_cost": new_total_cost,
        "new_total_cost_eur": new_total_cost * fx_eur,
        "new_avg_price": new_avg_price,
        "new_market_value": new_market_value,
        "new_market_value_eur": new_market_value * fx_eur,
        "estimated_gain": estimated_gain,
        "estimated_gain_eur": estimated_gain * fx_eur,
        "estimated_gain_pct": estimated_gain_pct,
    }


def calculate_budget_capacity(budget: float, buy_price: float) -> dict:
    """Calculate how many whole shares can be bought with a budget."""
    budget = safe_float(budget)
    buy_price = safe_float(buy_price)

    if budget <= 0 or buy_price <= 0:
        return {"buyable_qty": 0, "used_budget": 0.0, "remaining_budget": max(budget, 0.0)}

    buyable_qty = int(budget // buy_price)
    used_budget = buyable_qty * buy_price
    remaining_budget = budget - used_budget

    return {
        "buyable_qty": buyable_qty,
        "used_budget": used_budget,
        "remaining_budget": remaining_budget,
    }
