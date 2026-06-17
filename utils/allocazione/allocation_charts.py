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
    current_margin = fig.layout.margin
    margin = dict(l=18, r=18, t=42, b=18)
    if current_margin is not None:
        margin = dict(
            l=current_margin.l if current_margin.l is not None else 18,
            r=current_margin.r if current_margin.r is not None else 18,
            t=current_margin.t if current_margin.t is not None else 42,
            b=current_margin.b if current_margin.b is not None else 18,
        )

    current_font = fig.layout.font
    font_size = current_font.size if current_font is not None and current_font.size is not None else None
    font = dict(color="#e6edf3", family="Arial")
    if font_size is not None:
        font["size"] = font_size

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=margin,
        font=font,
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


def create_position_bar(position_allocation, mobile: bool = False):
    display_col = _display_col(position_allocation)

    # Use ascending data plus a reversed y-axis so horizontal bars are displayed
    # top-to-bottom from the largest position to the smallest one on both
    # desktop and mobile.
    chart_df = position_allocation.sort_values("weight_pct", ascending=True).copy()

    fig = px.bar(
        chart_df,
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
        cliponaxis=False,
        hovertemplate="**%{y}**<br>Simbolo: %{customdata[0]}<br>Peso: %{x:.2f}%<br>Valore: %{customdata[1]:,.2f} EUR",
    )

    max_weight = float(chart_df["weight_pct"].max()) if not chart_df.empty else 0.0
    safe_x_max = max(10.0, max_weight * (1.22 if mobile else 1.12))

    fig.update_layout(title="Peso posizioni", xaxis_title="Peso %", yaxis_title="", showlegend=False)
    fig.update_xaxes(range=[0, safe_x_max])
    fig.update_yaxes(automargin=True)

    fig.update_yaxes(autorange="reversed")

    if mobile:
        fig.update_layout(
            height=max(420, 42 * len(chart_df) + 120),
            margin=dict(l=0, r=78, t=46, b=46),
            font=dict(size=12),
        )

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
