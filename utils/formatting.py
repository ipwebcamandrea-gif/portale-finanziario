from html import escape


# =========================
# FORMATTAZIONE WATCHLIST
# =========================

def formatta_prezzo(value, currency):
    if value is None:
        return "N/D"

    suffix = " " + currency if currency else ""

    return f"{value:.2f}{suffix}"


def formatta_percentuale(value):
    if value is None:
        return "N/D"

    return f"{value:.2f} %"


def classe_percentuale(value):
    if value is None:
        return "tv-neutral-inline"

    if value > 0:
        return "tv-positive-inline"

    if value < 0:
        return "tv-negative-inline"

    return "tv-neutral-inline"


def classe_zona_sma(value):
    # Evidenzia in arancione sia la zona operativa ±10% sia tutto ciò che è sotto SMA200W.
    # Quindi resta normale solo sopra +10%.
    if value is not None and value <= 10:
        return "tv-zone-text-inline"

    return classe_percentuale(value)


def cell_html(label, value, css_class="tv-cell-value"):
    return (
        f'<div class="tv-cell-label">{escape(label)}</div>'
        f'<div class="{css_class}">{escape(value)}</div>'
    )
