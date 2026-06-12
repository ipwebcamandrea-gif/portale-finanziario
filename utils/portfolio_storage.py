from pathlib import Path

import pandas as pd


PORTFOLIO_COLUMNS = [
    "ticker",
    "titolo",
    "mercato",
    "strumento",
    "valuta",
    "quantita",
    "prezzo_medio",
    "prezzo_mercato",
    "prezzo_precedente",
    "yf_symbol",
    "tv_symbol",
]

TEXT_COLUMNS = [
    "ticker",
    "titolo",
    "mercato",
    "strumento",
    "valuta",
    "yf_symbol",
    "tv_symbol",
]
NUMERIC_COLUMNS = ["quantita", "prezzo_medio", "prezzo_mercato", "prezzo_precedente"]


def ensure_portfolio_file(csv_path: Path) -> None:
    """Create the portfolio CSV if it does not exist yet."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        df = pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        df.to_csv(csv_path, index=False)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in PORTFOLIO_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[PORTFOLIO_COLUMNS].copy()

    for col in TEXT_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["ticker"] = df["ticker"].str.upper()
    df["mercato"] = df["mercato"].str.upper()
    df["valuta"] = df["valuta"].str.upper()
    df["yf_symbol"] = df["yf_symbol"].str.upper()
    df["tv_symbol"] = df["tv_symbol"].str.upper()

    return df


def load_portfolio(csv_path: Path) -> pd.DataFrame:
    """Load portfolio positions from CSV and normalize expected columns."""
    ensure_portfolio_file(csv_path)
    df = pd.read_csv(csv_path)
    return _normalize_df(df)


def save_portfolio(df: pd.DataFrame, csv_path: Path) -> None:
    """Persist portfolio positions to CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = _normalize_df(df)
    df.to_csv(csv_path, index=False)


def add_position(csv_path: Path, position: dict) -> None:
    """Append a new portfolio position."""
    df = load_portfolio(csv_path)
    new_row = {col: position.get(col, "") for col in PORTFOLIO_COLUMNS}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_portfolio(df, csv_path)


def update_position(csv_path: Path, row_index: int, position: dict) -> None:
    """Update a portfolio position by row index."""
    df = load_portfolio(csv_path)

    if row_index < 0 or row_index >= len(df):
        return

    for col in PORTFOLIO_COLUMNS:
        if col in position:
            df.at[row_index, col] = position[col]

    save_portfolio(df, csv_path)


def delete_position(csv_path: Path, row_index: int) -> None:
    """Delete a portfolio position by row index."""
    df = load_portfolio(csv_path)

    if row_index < 0 or row_index >= len(df):
        return

    df = df.drop(index=row_index).reset_index(drop=True)
    save_portfolio(df, csv_path)
