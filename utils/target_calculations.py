from __future__ import annotations

from utils.portfolio_fx import convert_to_eur


def safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def pct_change(target: float | None, current: float | None) -> float | None:
    target = safe_float(target)
    current = safe_float(current)
    if target is None or current in (None, 0):
        return None
    return ((target - current) / current) * 100.0


def convert_amount_to_eur(amount: float | None, currency: str) -> dict:
    if amount is None:
        return {"ok": False, "value": None, "error": "Importo non disponibile"}
    return convert_to_eur(float(amount), currency)


def eur_budget_to_instrument_currency(budget_eur: float, currency: str) -> dict:
    clean_currency = str(currency or "EUR").upper()
    if clean_currency == "EUR":
        return {"ok": True, "value": float(budget_eur), "rate": 1.0, "source": "EUR", "error": ""}
    one_unit = convert_to_eur(1.0, clean_currency)
    if not one_unit.get("ok") or not one_unit.get("rate"):
        return {"ok": False, "value": None, "rate": None, "source": "", "error": one_unit.get("error", "Cambio non disponibile")}
    rate = float(one_unit.get("rate"))
    if rate <= 0:
        return {"ok": False, "value": None, "rate": None, "source": "", "error": "Cambio non valido"}
    return {"ok": True, "value": float(budget_eur) / rate, "rate": rate, "source": one_unit.get("source", ""), "error": ""}


def build_target_scenarios(target_data: dict, quantity: float | None = None, avg_price: float | None = None) -> list[dict]:
    current = safe_float(target_data.get("current_price"))
    currency = str(target_data.get("currency") or "").upper()
    scenarios = []
    for key, label in (("target_low", "Target minimo"), ("target_mean", "Target medio"), ("target_high", "Target massimo")):
        target = safe_float(target_data.get(key))
        diff_per_share = target - current if target is not None and current is not None else None
        gain_current = diff_per_share * quantity if diff_per_share is not None and quantity else None
        gain_from_cost = (target - avg_price) * quantity if target is not None and avg_price is not None and quantity else None
        future_value = target * quantity if target is not None and quantity else None
        scenarios.append({
            "key": key,
            "label": label,
            "target": target,
            "upside_pct": pct_change(target, current),
            "diff_per_share": diff_per_share,
            "future_value": future_value,
            "gain_current": gain_current,
            "gain_from_cost": gain_from_cost,
            "future_value_eur": convert_amount_to_eur(future_value, currency) if future_value is not None else {"ok": False},
            "gain_current_eur": convert_amount_to_eur(gain_current, currency) if gain_current is not None else {"ok": False},
            "gain_from_cost_eur": convert_amount_to_eur(gain_from_cost, currency) if gain_from_cost is not None else {"ok": False},
        })
    return scenarios


def build_simulation_scenarios(target_data: dict, budget_eur: float) -> dict:
    current = safe_float(target_data.get("current_price"))
    currency = str(target_data.get("currency") or "EUR").upper()
    converted_budget = eur_budget_to_instrument_currency(float(budget_eur), currency)
    if current in (None, 0) or not converted_budget.get("ok"):
        return {"ok": False, "error": converted_budget.get("error") or "Prezzo corrente non disponibile", "budget_currency": converted_budget, "quantity": None, "scenarios": []}
    budget_in_currency = float(converted_budget.get("value"))
    quantity = budget_in_currency / float(current)
    scenarios = []
    for base in build_target_scenarios(target_data, quantity=quantity, avg_price=current):
        future_value = base.get("future_value")
        gain = base.get("gain_current")
        scenarios.append({
            **base,
            "future_value_eur": convert_amount_to_eur(future_value, currency),
            "gain_eur": convert_amount_to_eur(gain, currency),
        })
    return {"ok": True, "budget_currency": converted_budget, "quantity": quantity, "scenarios": scenarios}
