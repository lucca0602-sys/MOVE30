from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
ICON_DIR = ROOT / "assets" / "icons"
PALETTE = {
    "navy": "#030B18", "panel": "#071A30", "panel_light": "#0A2340",
    "border": "#16436A", "text": "#F4F8FF", "muted": "#A9C0D9",
    "pre": "#22B8FF", "post": "#13D6A0", "score": "#FFC83D",
    "alert": "#FF5B70", "purple": "#B28BFF",
}
ICONS = {
    "heart": "heart", "star": "star", "brain": "brain", "checklist": "checklist",
    "bulb": "bulb", "ruler": "ruler", "scale": "scale", "calendar": "calendar",
    "activity": "activity", "users": "users", "gauge": "gauge", "donut": "donut",
    "bolt": "bolt", "signal": "signal", "alert": "alert", "clock": "clock",
}
def _icon_path(name: str, color: str | None = None) -> Path:
    icon_name = ICONS.get(name, "activity")
    if icon_name == "heart" and color == PALETTE["post"]:
        icon_name = "heart_green"
    return ICON_DIR / f"{icon_name}.svg"
def _class(color: str | None) -> str:
    colors = {PALETTE["pre"]:"pre", PALETTE["post"]:"post", PALETTE["score"]:"score", PALETTE["alert"]:"alert", PALETTE["purple"]:"purple"}
    return colors.get(color, "pre")
def metric_card(label: str, value: str | int, icon: str, color: str | None = None) -> None:
    with st.container(border=True, key=f"move-kpi-{icon}-{label.lower().replace(' ', '-')}"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.image(str(_icon_path(icon, color)), width=23, alt=f"Ícone de {label}")
            st.caption(label)
        st.html(f'<div class="move-kpi-value move-kpi-value--{_class(color)}">{value}</div>')
def section_heading(label: str, icon: str, color: str | None = None, level: int = 3) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.image(str(_icon_path(icon, color)), width=23, alt=f"Ícone de {label}")
        st.markdown(f'{"#" * max(3, min(level, 4))} {label}')
def status_pill(label: str, icon: str = "signal", color: str | None = None) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.image(str(_icon_path(icon, color or PALETTE["post"])), width=19, alt="")
        st.badge(label, color="green" if color == PALETTE["post"] else "blue")

PLOT_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def style_plotly(fig, height: int = 360, margins: dict | None = None):
    """Apply the MOVE30 performance-console frame and shared chart typography."""
    frame_shapes = [
        dict(type="rect", xref="paper", yref="paper", x0=0, y0=0, x1=1, y1=1,
             line=dict(color="rgba(48,117,166,.42)", width=1), fillcolor="rgba(4,18,37,.72)", layer="below"),
        dict(type="line", xref="paper", yref="paper", x0=.025, y0=.995, x1=.19, y1=.995,
             line=dict(color=PALETTE["pre"], width=2.5), layer="above"),
        dict(type="line", xref="paper", yref="paper", x0=.81, y0=.995, x1=.975, y1=.995,
             line=dict(color=PALETTE["post"], width=2.5), layer="above"),
        dict(type="line", xref="paper", yref="paper", x0=.025, y0=.008, x1=.075, y1=.008,
             line=dict(color="rgba(34,184,255,.55)", width=1.5), layer="above"),
        dict(type="line", xref="paper", yref="paper", x0=.925, y0=.008, x1=.975, y1=.008,
             line=dict(color="rgba(19,214,160,.55)", width=1.5), layer="above"),
    ]
    fig.update_layout(
        height=height,
        margin=margins or dict(l=58, r=24, t=36, b=54),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#041225",
        font=dict(family="Aptos, Segoe UI, sans-serif", size=12, color="#D9E9FA"),
        hoverlabel=dict(bgcolor="#061426", bordercolor="#22B8FF", font=dict(family="Aptos, Segoe UI, sans-serif", size=12, color="#F4F8FF"), align="left", namelength=-1),
        hovermode="closest", transition=dict(duration=260, easing="cubic-in-out"),
        uirevision="move30-dashboard",
        shapes=frame_shapes + list(fig.layout.shapes or []),
    )
    return fig


def style_cartesian_axes(fig, horizontal_bars: bool = False):
    axis_common = dict(automargin=True, linecolor="rgba(80,132,177,.38)", tickfont=dict(family="Aptos, Segoe UI, sans-serif", size=11, color="#AFC6DD"), ticks="outside", ticklen=4, tickcolor="rgba(80,132,177,.38)", zeroline=False, showline=True)
    fig.update_xaxes(**axis_common, showgrid=horizontal_bars, gridcolor="rgba(92,157,205,.16)")
    fig.update_yaxes(**axis_common, showgrid=not horizontal_bars, gridcolor="rgba(92,157,205,.16)")
    return fig
