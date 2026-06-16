from __future__ import annotations

import plotly.express as px

ALLOCATION_COLORS = [
    "#3b82f6",
    "#22c55e",
    "#f59e0b",
    "#a855f7",
    "#06b6d4",
    "#ef4444",
    "#84cc16",
    "#f97316",
    "#14b8a6",
    "#e879f9",
    "#60a5fa",
    "#facc15",
]


def _base_layout(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=18, r=18, t=42, b=18),
        font=dict(color="#e6edf3", family="Arial"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=11)),
    )
    return fig


def _display_col(position_allocation) -> str:
    return "display_symbol" if "display_symbol" in position_allocation.columns else "ticker"


def create_position_donut(position_allocation, total_label: str):
    display_col = _display_col(position_allocation)
    fig = px.pie(
        position_allocation,
        names="titolo",
        values="value_eur",
        hole=0.58,
        color_discrete_sequence=ALLOCATION_COLORS,
        custom_data=[display_col, "weight_pct", "value_eur"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate="**%{label}**<br>Simbolo: %{customdata[0]}<br>Peso: %{customdata[1]:.2f}%<br>Valore: %{customdata[2]:,.2f} EUR",
        marker=dict(line=dict(color="rgba(13,17,23,0.85)", width=2)),
    )
    fig.add_annotation(text=total_label, x=0.5, y=0.5, showarrow=False, font=dict(size=15, color="#f9fafb"), align="center")
    fig.update_layout(title="Allocazione per titolo")
    return _base_layout(fig)


def create_position_bar(position_allocation):
    display_col = _display_col(position_allocation)
    fig = px.bar(
        position_allocation.sort_values("weight_pct", ascending=True),
        x="weight_pct",
        y="titolo",
        orientation="h",
        color="titolo",
        color_discrete_sequence=ALLOCATION_COLORS,
        custom_data=[display_col, "value_eur"],
        text="weight_pct",
    )
    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate="**%{y}**<br>Simbolo: %{customdata[0]}<br>Peso: %{x:.2f}%<br>Valore: %{customdata[1]:,.2f} EUR",
    )
    fig.update_layout(title="Peso posizioni", xaxis_title="Peso %", yaxis_title="", showlegend=False)
    return _base_layout(fig)


def create_group_bar(group_df, group_col: str, title: str):
    fig = px.bar(
        group_df.sort_values("weight_pct", ascending=True),
        x="weight_pct",
        y=group_col,
        orientation="h",
        color=group_col,
        color_discrete_sequence=ALLOCATION_COLORS,
        text="weight_pct",
        custom_data=["value_eur"],
    )
    fig.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
        hovertemplate="**%{y}**<br>Peso: %{x:.2f}%<br>Valore: %{customdata[0]:,.2f} EUR",
    )
    fig.update_layout(title=title, xaxis_title="Peso %", yaxis_title="", showlegend=False)
    return _base_layout(fig)
