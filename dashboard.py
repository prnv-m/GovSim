"""
GOVIM Dashboard — Compare governance model runs side-by-side.

Run:
    streamlit run dashboard.py
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RESULTS_DIR = Path("data/results")

# ── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GOVIM Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS injection ─────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Base dark background ── */
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #0d1117;
    color: #c9d1d9;
}
[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

/* ── Headers ── */
h1, h2, h3, h4 { color: #e6edf3 !important; }
h1 { font-size: 2rem !important; letter-spacing: -0.5px; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
[data-testid="metric-container"] label { color: #8b949e !important; font-size: 0.78rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #58a6ff !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: #161b22;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border-bottom: 1px solid #30363d;
}
[data-testid="stTabs"] button[role="tab"] {
    background: transparent;
    color: #8b949e !important;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
    font-weight: 500;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: #21262d !important;
    color: #58a6ff !important;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] th {
    background: #161b22 !important;
    color: #8b949e !important;
    font-weight: 600;
}
[data-testid="stDataFrame"] td { color: #c9d1d9 !important; }

/* ── General elements ── */
.stSelectbox label, .stMultiSelect label, .stCheckbox label { color: #8b949e !important; }
.stMarkdown p, .stCaption { color: #8b949e !important; }
hr { border-color: #30363d !important; }

/* ── Custom hero cards ── */
.hero-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
.hero-card:hover { transform: translateY(-2px); }
.hero-card .model-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #58a6ff;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.hero-card .big-number {
    font-size: 3rem;
    font-weight: 800;
    line-height: 1;
    margin: 8px 0;
}
.hero-card .sub-label {
    font-size: 0.8rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.hero-card .badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 12px;
}
.badge-safe { background: rgba(63,185,80,0.2); color: #3fb950; border: 1px solid #3fb950; }
.badge-warn { background: rgba(210,153,34,0.2); color: #d29922; border: 1px solid #d29922; }
.badge-danger { background: rgba(248,81,73,0.2); color: #f85149; border: 1px solid #f85149; }

/* ── Section headers ── */
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #30363d;
}

/* ── Divider ── */
.govim-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #30363d, transparent);
    margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Plotly dark theme defaults ────────────────────────────────────────────────

PLOTLY_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#161b22",
    font_color="#c9d1d9",
)
CHART_MARGIN = dict(l=20, r=20, t=50, b=20)

MODEL_COLORS = {
    "centralized":   "#58a6ff",
    "decentralized": "#f85149",
    "hybrid":        "#3fb950",
}

def model_color(model: str) -> str:
    return MODEL_COLORS.get(model.lower(), "#c9d1d9")


def hex_to_rgba(hex_color: str, alpha: float = 0.08) -> str:
    """Convert #rrggbb to rgba(r,g,b,alpha)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_runs():
    runs = []
    for path in sorted(RESULTS_DIR.glob("run_*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["_file"] = path.name
        runs.append(data)
    return runs


def run_label(run):
    meta = run["meta"]
    ts = meta["timestamp"][:16].replace("T", " ")
    mode_tag = "[SYBIL]" if meta.get("sybil_mode") else "[NORMAL]"
    return f"{meta['model'].upper()}  {mode_tag}  —  {ts}"


def augment_normal_run(run):
    """Back-fill attack stats for normal runs saved before is_attack was set correctly."""
    s = run.get("summary", {})
    if not run["meta"].get("sybil_mode") and s.get("attacks_attempted", 0) == 0:
        malicious = [p for p in run.get("pr_log", []) if p.get("is_malicious")]
        if malicious:
            attempted = len(malicious)
            succeeded = sum(1 for p in malicious if p["decision"] == "approve")
            blocked = attempted - succeeded
            s["attacks_attempted"] = attempted
            s["attacks_succeeded"] = succeeded
            s["attacks_blocked"] = blocked
            s["false_positives"] = sum(1 for p in run.get("pr_log", []) if p.get("was_false_positive"))
            s["detection_rate"] = round(blocked / attempted, 4) if attempted > 0 else None
            s["sybil_defeated"] = succeeded == 0
    return run


# ── Load data ─────────────────────────────────────────────────────────────────

all_runs = [augment_normal_run(r) for r in load_all_runs()]

if not all_runs:
    st.markdown("""
    <div style='text-align:center; padding: 80px 0;'>
        <div style='font-size:4rem;'>🏛️</div>
        <h2 style='color:#58a6ff;'>No simulation data found</h2>
        <p style='color:#8b949e;'>Run the simulation to generate results:</p>
    </div>
    """, unsafe_allow_html=True)
    st.code(
        "# No sybil attack (normal mode)\n"
        "python main.py --model centralized\n"
        "python main.py --model decentralized\n"
        "python main.py --model hybrid\n\n"
        "# With sybil ring attack\n"
        "python main.py --model centralized --sybil\n"
        "python main.py --model decentralized --sybil\n"
        "python main.py --model hybrid --sybil",
        language="bash"
    )
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 16px 0 24px 0;'>
        <div style='font-size:2.5rem;'>🏛️</div>
        <div style='font-size:1.1rem; font-weight:700; color:#58a6ff; letter-spacing:2px;'>GOVIM</div>
        <div style='font-size:0.7rem; color:#8b949e; letter-spacing:1px;'>GOVERNANCE SIMULATION</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Filter by Mode</div>', unsafe_allow_html=True)
    sybil_filter = st.radio(
        "Mode filter",
        options=["All", "Sybil Only", "Normal Only"],
        index=0,
        label_visibility="collapsed",
        horizontal=False,
    )

    # Pre-filter runs by sybil mode
    if sybil_filter == "Sybil Only":
        filtered_runs = [r for r in all_runs if r["meta"].get("sybil_mode")]
    elif sybil_filter == "Normal Only":
        filtered_runs = [r for r in all_runs if not r["meta"].get("sybil_mode")]
    else:
        filtered_runs = all_runs

    st.markdown('<div class="section-header">Select Runs</div>', unsafe_allow_html=True)
    labels = [run_label(r) for r in filtered_runs]
    selected_labels = st.multiselect(
        "Runs to compare",
        options=labels,
        default=labels,
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-header">Model Legend</div>', unsafe_allow_html=True)
    for model, color in MODEL_COLORS.items():
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:{color};"></div>'
            f'<span style="color:#c9d1d9;font-size:0.85rem;">{model.capitalize()}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="section-header">Mode Legend</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.8rem;color:#c9d1d9;margin:4px 0;">'
        '<span style="color:#f85149;font-weight:600;">[SYBIL]</span> &nbsp;3 coordinated attackers</div>'
        '<div style="font-size:0.8rem;color:#c9d1d9;margin:4px 0;">'
        '<span style="color:#3fb950;font-weight:600;">[NORMAL]</span> &nbsp;Standard simulation</div>',
        unsafe_allow_html=True
    )

if not selected_labels:
    st.info("Select at least one run from the sidebar.")
    st.stop()

selected_runs = [r for r, l in zip(filtered_runs, labels) if l in selected_labels]

# ── Page title ────────────────────────────────────────────────────────────────

st.markdown("""
<div style='padding: 8px 0 24px 0;'>
    <h1 style='margin:0;'>🏛️ GOVIM <span style='color:#58a6ff;'>Governance</span> Dashboard</h1>
    <p style='color:#8b949e; margin:4px 0 0 0; font-size:0.9rem;'>
        Sybil attack simulation · Centralized · Decentralized · Hybrid
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_overview, tab_security, tab_reputation, tab_prs, tab_analysis, tab_compare = st.tabs([
    "⚡ Overview", "🛡️ Security", "📈 Reputation", "🔍 PR Log", "🔬 Analysis", "⚔️ Sybil vs Normal"
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ═══════════════════════════════════════════════════════════════════════════

with tab_overview:

    # ── Hero cards ──
    cols = st.columns(len(selected_runs))
    for col, run in zip(cols, selected_runs):
        s = run.get("summary", {})
        m = run["meta"]
        model = m["model"].lower()
        is_sybil = m.get("sybil_mode", False)
        color = model_color(model)
        total_prs = s.get("total_prs", 0)

        if is_sybil:
            dr = s.get("detection_rate")
            big_num = f"{dr*100:.0f}%" if dr is not None else "N/A"
            sub_label = "Detection Rate"
            defeated = s.get("sybil_defeated", False)
            badge_cls = "badge-safe" if defeated else "badge-danger"
            badge_txt = "RING DEFEATED" if defeated else "RING SUCCEEDED"
            stat1_val = s.get("attacks_blocked", 0)
            stat1_label = "Blocked"
            stat1_color = "#3fb950"
            stat2_val = s.get("attacks_succeeded", 0)
            stat2_label = "Succeeded"
            stat2_color = "#f85149"
            stat3_val = s.get("false_positives", 0)
            stat3_label = "False Pos"
            stat3_color = "#ffa657"
        else:
            atk = s.get("attacks_attempted", 0)
            if atk > 0:
                dr = s.get("detection_rate")
                big_num = f"{dr*100:.0f}%" if dr is not None else "N/A"
                sub_label = "Detection Rate"
                succeeded = s.get("attacks_succeeded", 0)
                badge_cls = "badge-safe" if succeeded == 0 else "badge-danger"
                badge_txt = "ATTACK BLOCKED" if succeeded == 0 else "ATTACK MERGED"
                stat1_val = s.get("attacks_blocked", 0)
                stat1_label = "Blocked"
                stat1_color = "#3fb950"
                stat2_val = succeeded
                stat2_label = "Succeeded"
                stat2_color = "#f85149"
                stat3_val = s.get("false_positives", 0)
                stat3_label = "False Pos"
                stat3_color = "#ffa657"
            else:
                merged = s.get("total_merged", 0)
                merge_rate = round(merged / total_prs * 100) if total_prs > 0 else 0
                big_num = f"{merge_rate}%"
                sub_label = "Merge Rate"
                badge_cls = "badge-safe"
                badge_txt = "NORMAL RUN"
                stat1_val = total_prs
                stat1_label = "Total PRs"
                stat1_color = "#58a6ff"
                stat2_val = merged
                stat2_label = "Merged"
                stat2_color = "#3fb950"
                stat3_val = s.get("total_rejected", 0)
                stat3_label = "Rejected"
                stat3_color = "#f85149"

        with col:
            st.markdown(f"""
            <div class="hero-card">
                <div class="model-name" style="color:{color};">{model.upper()}</div>
                <div class="big-number" style="color:{color};">{big_num}</div>
                <div class="sub-label">{sub_label}</div>
                <div style="display:flex; justify-content:space-between; margin-top:16px; gap:8px;">
                    <div style="flex:1; background:#21262d; border-radius:8px; padding:10px;">
                        <div style="font-size:1.4rem; font-weight:700; color:{stat1_color};">{stat1_val}</div>
                        <div style="font-size:0.7rem; color:#8b949e;">{stat1_label}</div>
                    </div>
                    <div style="flex:1; background:#21262d; border-radius:8px; padding:10px;">
                        <div style="font-size:1.4rem; font-weight:700; color:{stat2_color};">{stat2_val}</div>
                        <div style="font-size:0.7rem; color:#8b949e;">{stat2_label}</div>
                    </div>
                    <div style="flex:1; background:#21262d; border-radius:8px; padding:10px;">
                        <div style="font-size:1.4rem; font-weight:700; color:{stat3_color};">{stat3_val}</div>
                        <div style="font-size:0.7rem; color:#8b949e;">{stat3_label}</div>
                    </div>
                </div>
                <span class="badge {badge_cls}">{badge_txt}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

    # ── Radar chart ──
    col_radar, col_bar = st.columns([1, 1])

    with col_radar:
        st.markdown('<div class="section-header">Model Comparison Radar</div>', unsafe_allow_html=True)

        categories = ["Detection Rate", "Low False Pos", "Low False Neg", "Merge Rate", "Efficiency"]
        fig_radar = go.Figure()

        for run in selected_runs:
            s = run.get("summary", {})
            model = run["meta"]["model"].lower()
            total_prs = max(s.get("total_prs", 1), 1)
            atk = max(s.get("attacks_attempted", 1), 1)
            benign_prs = total_prs - atk

            dr = s.get("detection_rate") or 0
            fp_rate = 1 - (s.get("false_positives", 0) / max(benign_prs, 1))
            fn_rate = 1 - (s.get("false_negatives", 0) / atk)
            merge_rate = s.get("total_merged", 0) / total_prs
            efficiency = s.get("total_merged", 0) / max(benign_prs, 1)

            values = [dr, fp_rate, fn_rate, merge_rate, min(efficiency, 1)]
            values += [values[0]]  # close loop
            cats = categories + [categories[0]]

            fig_radar.add_trace(go.Scatterpolar(
                r=values, theta=cats,
                fill="toself",
                name=model.upper(),
                line_color=model_color(model),
                fillcolor=model_color(model),
                opacity=0.25,
            ))

        fig_radar.update_layout(
            **PLOTLY_DARK,
            polar=dict(
                bgcolor="#161b22",
                radialaxis=dict(visible=True, range=[0, 1], color="#8b949e", tickfont_size=10, gridcolor="#30363d"),
                angularaxis=dict(color="#8b949e", gridcolor="#30363d"),
            ),
            showlegend=True,
            legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
            margin=CHART_MARGIN,
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_bar:
        st.markdown('<div class="section-header">PR Outcomes</div>', unsafe_allow_html=True)

        rows = []
        for run in selected_runs:
            s = run.get("summary", {})
            model = run["meta"]["model"].upper()
            rows += [
                {"Model": model, "Outcome": "Merged", "Count": s.get("total_merged", 0)},
                {"Model": model, "Outcome": "Rejected", "Count": s.get("total_rejected", 0)},
            ]

        df_outcomes = pd.DataFrame(rows)
        fig_outcomes = px.bar(
            df_outcomes, x="Model", y="Count", color="Outcome", barmode="stack",
            color_discrete_map={"Merged": "#3fb950", "Rejected": "#f85149"},
        )
        fig_outcomes.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=380,
            showlegend=True,
            legend=dict(font_color="#c9d1d9", bgcolor="rgba(0,0,0,0)", bordercolor="#30363d"),
            xaxis=dict(gridcolor="#30363d"),
            yaxis=dict(gridcolor="#30363d"),
        )
        fig_outcomes.update_traces(marker_line_width=0)
        st.plotly_chart(fig_outcomes, use_container_width=True)

    # ── Summary table ──
    st.markdown('<div class="section-header">Full Summary Table</div>', unsafe_allow_html=True)

    table_rows = []
    for run in selected_runs:
        s = run.get("summary", {})
        m = run["meta"]
        dr = s.get("detection_rate")
        table_rows.append({
            "Model": m["model"].upper(),
            "Rounds": m["rounds"],
            "Total PRs": s.get("total_prs", 0),
            "Merged": s.get("total_merged", 0),
            "Rejected": s.get("total_rejected", 0),
            "Attacks": s.get("attacks_attempted", 0),
            "Blocked": s.get("attacks_blocked", 0),
            "Succeeded": s.get("attacks_succeeded", 0),
            "Detection %": f"{dr*100:.0f}%" if dr is not None else "N/A",
            "False Pos": s.get("false_positives", 0),
            "False Neg": s.get("false_negatives", 0),
            "Agents Blocked": s.get("agents_blocked", 0),
            "Verdict": (
                "✅ Defeated" if s.get("sybil_defeated")
                else ("❌ Vulnerable" if m.get("sybil_mode")
                else "— Normal Run")
            ),
        })

    df_summary = pd.DataFrame(table_rows)
    st.dataframe(df_summary.set_index("Model"), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — Security
# ═══════════════════════════════════════════════════════════════════════════

with tab_security:

    # Warn if all selected runs are normal (no attack data to show)
    all_normal = all(not r["meta"].get("sybil_mode") for r in selected_runs)
    if all_normal:
        st.info(
            "All selected runs are **Normal** (no sybil attack). "
            "Attack metrics (detection rate, blocked, false positives) are not applicable. "
            "Switch to **Sybil Only** in the sidebar to see security stats."
        )

    # ── Detection rate gauges ──
    st.markdown('<div class="section-header">Detection Rate Gauges</div>', unsafe_allow_html=True)

    gauge_cols = st.columns(len(selected_runs))
    for col, run in zip(gauge_cols, selected_runs):
        s = run.get("summary", {})
        model = run["meta"]["model"]
        dr = (s.get("detection_rate") or 0) * 100
        color = model_color(model)

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=dr,
            delta={"reference": 50, "valueformat": ".0f", "suffix": "%"},
            number={"suffix": "%", "font": {"size": 36, "color": color}},
            title={"text": model.upper(), "font": {"size": 14, "color": "#8b949e"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e", "tickfont": {"color": "#8b949e"}},
                "bar": {"color": color, "thickness": 0.25},
                "bgcolor": "#21262d",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(248,81,73,0.15)"},
                    {"range": [40, 70], "color": "rgba(210,153,34,0.15)"},
                    {"range": [70, 100], "color": "rgba(63,185,80,0.15)"},
                ],
                "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.8, "value": dr},
            },
        ))
        fig_gauge.update_layout(
            **PLOTLY_DARK,
            margin=dict(l=20, r=20, t=60, b=20),
            height=260,
        )
        with col:
            st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

    col_atk, col_err = st.columns(2)

    with col_atk:
        st.markdown('<div class="section-header">Attack Outcomes</div>', unsafe_allow_html=True)

        sec_rows = []
        for run in selected_runs:
            s = run.get("summary", {})
            model = run["meta"]["model"].upper()
            sec_rows += [
                {"Model": model, "Metric": "Attempted", "Count": s.get("attacks_attempted", 0)},
                {"Model": model, "Metric": "Blocked",   "Count": s.get("attacks_blocked", 0)},
                {"Model": model, "Metric": "Succeeded", "Count": s.get("attacks_succeeded", 0)},
            ]

        df_sec = pd.DataFrame(sec_rows)
        fig_atk = px.bar(
            df_sec, x="Model", y="Count", color="Metric", barmode="group",
            color_discrete_map={"Attempted": "#58a6ff", "Blocked": "#3fb950", "Succeeded": "#f85149"},
        )
        fig_atk.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=340,
            legend=dict(font_color="#c9d1d9", bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#30363d"),
            yaxis=dict(gridcolor="#30363d"),
        )
        fig_atk.update_traces(marker_line_width=0)
        st.plotly_chart(fig_atk, use_container_width=True)

    with col_err:
        st.markdown('<div class="section-header">Classification Errors</div>', unsafe_allow_html=True)

        err_rows = []
        for run in selected_runs:
            s = run.get("summary", {})
            model = run["meta"]["model"].upper()
            err_rows += [
                {"Model": model, "Type": "False Positives", "Count": s.get("false_positives", 0)},
                {"Model": model, "Type": "False Negatives", "Count": s.get("false_negatives", 0)},
            ]

        df_err = pd.DataFrame(err_rows)
        fig_err = px.bar(
            df_err, x="Model", y="Count", color="Type", barmode="group",
            color_discrete_map={"False Positives": "#ffa657", "False Negatives": "#f85149"},
        )
        fig_err.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=340,
            legend=dict(font_color="#c9d1d9", bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#30363d"),
            yaxis=dict(gridcolor="#30363d"),
        )
        fig_err.update_traces(marker_line_width=0)
        st.plotly_chart(fig_err, use_container_width=True)

    # ── Per-round attack timeline ──
    st.markdown('<div class="section-header">Attack Timeline (Per Round)</div>', unsafe_allow_html=True)

    round_rows = []
    for run in selected_runs:
        model = run["meta"]["model"].upper()
        for rd in run.get("rounds", []):
            round_rows.append({
                "Model": model,
                "Round": rd["round"],
                "Attacks Attempted": rd.get("attacks_attempted", 0),
                "Attacks Blocked": rd.get("attacks_blocked", 0),
                "PRs Submitted": rd.get("prs_submitted", 0),
            })

    if round_rows:
        df_rounds = pd.DataFrame(round_rows)
        fig_tl = px.line(
            df_rounds, x="Round", y="Attacks Attempted", color="Model",
            color_discrete_map={m.upper(): c for m, c in MODEL_COLORS.items()},
            markers=True,
            line_shape="spline",
        )
        fig_tl.update_traces(line_width=2.5, marker_size=8)
        fig_tl.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=280,
            xaxis=dict(gridcolor="#30363d", dtick=1),
            yaxis=dict(gridcolor="#30363d"),
            legend=dict(font_color="#c9d1d9", bgcolor="rgba(0,0,0,0)"),
        )
        # Add shaded area under each line
        for run in selected_runs:
            model = run["meta"]["model"].upper()
            sub = df_rounds[df_rounds["Model"] == model]
            fig_tl.add_trace(go.Scatter(
                x=sub["Round"], y=sub["Attacks Attempted"],
                fill="tozeroy",
                fillcolor=hex_to_rgba(model_color(run["meta"]["model"]), 0.08),
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ))
        st.plotly_chart(fig_tl, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — Reputation
# ═══════════════════════════════════════════════════════════════════════════

with tab_reputation:

    run_choice = st.selectbox(
        "Select run to inspect",
        options=[run_label(r) for r in selected_runs],
        key="rep_run",
        label_visibility="collapsed",
    )
    run = next(r for r in selected_runs if run_label(r) == run_choice)
    model_name = run["meta"]["model"].upper()

    # Build a UUID→name map to handle old run files that stored agent UUIDs as keys
    _name_set = {a["name"] for a in run.get("agents", [])}
    _uuid_to_name = {}
    first_round_keys = set(run["rounds"][0].get("agent_reputations", {}).keys()) if run.get("rounds") else set()
    if first_round_keys and not first_round_keys.issubset(_name_set):
        # Old format: keys are UUIDs — map by position (order is stable within a run)
        agent_names_ordered = [a["name"] for a in run.get("agents", [])]
        for i, uid in enumerate(sorted(first_round_keys)):
            if i < len(agent_names_ordered):
                _uuid_to_name[uid] = agent_names_ordered[i]

    rep_rows = []
    for rd in run.get("rounds", []):
        for agent_key, rep in rd.get("agent_reputations", {}).items():
            agent_name = _uuid_to_name.get(agent_key, agent_key)
            rep_rows.append({"Round": rd["round"], "Agent": agent_name, "Reputation": rep})

    if rep_rows:
        df_rep = pd.DataFrame(rep_rows)
        agent_types = {a["name"]: a["type"] for a in run.get("agents", [])}
        df_rep["Type"] = df_rep["Agent"].map(lambda n: agent_types.get(n, "unknown"))

        color_map = {}
        benign_blues  = ["#58a6ff", "#79c0ff", "#388bfd", "#1f6feb", "#0d419d"]
        sybil_reds    = ["#f85149", "#ff7b72", "#ffa198", "#ff4040", "#cc2222"]
        b_idx = s_idx = 0
        for name, atype in agent_types.items():
            if atype == "benign":
                color_map[name] = benign_blues[b_idx % len(benign_blues)]
                b_idx += 1
            else:
                color_map[name] = sybil_reds[s_idx % len(sybil_reds)]
                s_idx += 1

        col_line, col_final = st.columns([3, 2])

        with col_line:
            st.markdown(f'<div class="section-header">Reputation Over Time — {model_name}</div>', unsafe_allow_html=True)

            fig_rep = px.line(
                df_rep, x="Round", y="Reputation", color="Agent",
                color_discrete_map=color_map,
                markers=True,
                line_shape="spline",
                range_y=[0, 1],
            )
            fig_rep.add_hrect(y0=0.6, y1=1.0, fillcolor="rgba(63,185,80,0.05)",
                              line_width=0, annotation_text="Trust zone", annotation_position="top left",
                              annotation_font_color="#3fb950")
            fig_rep.add_hrect(y0=0, y1=0.4, fillcolor="rgba(248,81,73,0.05)",
                              line_width=0, annotation_text="Danger zone", annotation_position="bottom left",
                              annotation_font_color="#f85149")
            fig_rep.add_hline(y=0.6, line_dash="dash", line_color="#3fb950", line_width=1.5,
                              annotation_text="", annotation_position="right")
            fig_rep.add_hline(y=0.4, line_dash="dash", line_color="#f85149", line_width=1.5)
            fig_rep.update_traces(line_width=2.5, marker_size=8)
            fig_rep.update_layout(
                **PLOTLY_DARK,
                margin=CHART_MARGIN,
                height=400,
                xaxis=dict(gridcolor="#30363d", dtick=1),
                yaxis=dict(gridcolor="#30363d", tickformat=".0%"),
                legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
            )
            # Distinguish sybil agents with dashed lines
            for trace in fig_rep.data:
                if color_map.get(trace.name) in sybil_reds:
                    trace.line.dash = "dot"
            st.plotly_chart(fig_rep, use_container_width=True)
            st.caption("— Solid = Benign agents · · · Dotted = Sybil attackers")

        with col_final:
            st.markdown('<div class="section-header">Final Reputation</div>', unsafe_allow_html=True)

            final_agents = run.get("agents", [])
            if final_agents:
                # Prefer maintainer_reputation (matches terminal output) if available
                for a in final_agents:
                    if a.get("maintainer_reputation") is not None:
                        a["display_reputation"] = a["maintainer_reputation"]
                    else:
                        a["display_reputation"] = a["final_reputation"]
                df_fa = pd.DataFrame(final_agents).sort_values("display_reputation", ascending=True)
                bar_colors = [color_map.get(n, "#8b949e") for n in df_fa["name"]]
                fig_final = go.Figure(go.Bar(
                    x=df_fa["display_reputation"],
                    y=df_fa["name"],
                    orientation="h",
                    marker_color=bar_colors,
                    marker_line_width=0,
                    text=[f"{v:.0%}" for v in df_fa["display_reputation"]],
                    textposition="outside",
                    textfont=dict(color="#c9d1d9", size=11),
                ))
                fig_final.add_vline(x=0.6, line_dash="dash", line_color="#3fb950", line_width=1.5)
                fig_final.add_vline(x=0.4, line_dash="dash", line_color="#f85149", line_width=1.5)
                fig_final.update_layout(
                    **PLOTLY_DARK,
                    margin=dict(l=20, r=60, t=20, b=20),
                    height=400,
                    xaxis=dict(range=[0, 1.1], gridcolor="#30363d", tickformat=".0%"),
                    yaxis=dict(gridcolor="#30363d"),
                )
                st.plotly_chart(fig_final, use_container_width=True)

        # ── Reputation heatmap ──
        st.markdown('<div class="section-header">Reputation Heatmap</div>', unsafe_allow_html=True)

        df_pivot = df_rep.pivot(index="Agent", columns="Round", values="Reputation")
        # Sort: benign on top, sybil at bottom
        agent_order = (
            [n for n, t in agent_types.items() if t == "benign"] +
            [n for n, t in agent_types.items() if t != "benign"]
        )
        df_pivot = df_pivot.reindex([a for a in agent_order if a in df_pivot.index])

        fig_heat = go.Figure(go.Heatmap(
            z=df_pivot.values,
            x=[f"R{c}" for c in df_pivot.columns],
            y=df_pivot.index.tolist(),
            colorscale=[
                [0.0, "#f85149"],
                [0.4, "#d29922"],
                [0.6, "#3fb950"],
                [1.0, "#58a6ff"],
            ],
            zmin=0, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in df_pivot.values],
            texttemplate="%{text}",
            textfont_size=11,
            showscale=True,
            colorbar=dict(
                tickformat=".0%",
                tickcolor="#8b949e",
                outlinecolor="#30363d",
            ),
        ))
        # Add a horizontal separator between benign and sybil
        n_benign = sum(1 for t in agent_types.values() if t == "benign")
        fig_heat.add_hline(
            y=n_benign - 0.5,
            line_color="#30363d",
            line_width=2,
            line_dash="solid",
        )
        fig_heat.update_layout(
            **PLOTLY_DARK,
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis=dict(side="top"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("Top section: benign agents · Bottom section: sybil attackers · Color = trust level")

    else:
        st.info("No round-level reputation data in this run file.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — PR Log
# ═══════════════════════════════════════════════════════════════════════════

with tab_prs:

    run_choice_pr = st.selectbox(
        "Select run",
        options=[run_label(r) for r in selected_runs],
        key="pr_run",
        label_visibility="collapsed",
    )
    run_pr = next(r for r in selected_runs if run_label(r) == run_choice_pr)
    pr_log = run_pr.get("pr_log", [])

    if pr_log:
        df_pr = pd.DataFrame(pr_log)

        # ── Mini stats row ──
        col_d, col_a, col_r, col_fp = st.columns(4)
        with col_d:
            st.metric("Total PRs", len(df_pr))
        with col_a:
            st.metric("Approved", int((df_pr["decision"].str.lower() == "approve").sum()))
        with col_r:
            st.metric("Rejected", int(df_pr["decision"].str.lower().isin(["reject","block_agent"]).sum()))
        with col_fp:
            st.metric("False Positives", int(df_pr["was_false_positive"].sum()))

        st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

        col_pie, col_trust = st.columns(2)

        with col_pie:
            st.markdown('<div class="section-header">Decision Distribution</div>', unsafe_allow_html=True)
            dec_counts = df_pr["decision"].value_counts().reset_index()
            dec_counts.columns = ["Decision", "Count"]
            dec_color_map = {
                "approve": "#3fb950", "reject": "#f85149",
                "block_agent": "#ff7b72", "pending": "#8b949e",
                # legacy uppercase keys from older run files
                "APPROVE": "#3fb950", "REJECT": "#f85149",
                "BLOCK_AGENT": "#ff7b72", "PENDING": "#8b949e",
            }
            fig_pie = px.pie(
                dec_counts, names="Decision", values="Count",
                color="Decision", color_discrete_map=dec_color_map,
                hole=0.55,
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                textfont_color="#c9d1d9",
                marker_line_color="#0d1117",
                marker_line_width=2,
            )
            fig_pie.update_layout(
                **PLOTLY_DARK,
                margin=CHART_MARGIN,
                height=300,
                showlegend=False,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_trust:
            st.markdown('<div class="section-header">Trust Score Distribution</div>', unsafe_allow_html=True)
            fig_hist = px.histogram(
                df_pr, x="trust_score", color="decision", nbins=20,
                color_discrete_map=dec_color_map,
                barmode="overlay",
                opacity=0.75,
            )
            fig_hist.update_layout(
                **PLOTLY_DARK,
                margin=CHART_MARGIN,
                height=300,
                xaxis=dict(title="Trust Score", gridcolor="#30363d"),
                yaxis=dict(title="Count", gridcolor="#30363d"),
                legend=dict(font_color="#c9d1d9", bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        # ── Filters ──
        st.markdown('<div class="section-header">Filter PR Log</div>', unsafe_allow_html=True)
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 1, 1])
        with col_f1:
            filter_decision = st.multiselect(
                "Decision", options=df_pr["decision"].unique().tolist(),
                default=df_pr["decision"].unique().tolist()
            )
        with col_f2:
            filter_attack = st.multiselect(
                "Attack mode", options=[True, False], default=[True, False]
            )
        with col_f3:
            filter_fp = st.checkbox("False positives only")
        with col_f4:
            filter_fn = st.checkbox("False negatives only")

        mask = (
            df_pr["decision"].isin(filter_decision)
            & df_pr["in_attack_mode"].isin(filter_attack)
        )
        if filter_fp:
            mask &= df_pr["was_false_positive"]
        if filter_fn:
            mask &= df_pr["was_false_negative"]

        df_display = df_pr[mask][[
            "round", "pr_number", "agent", "agent_type", "in_attack_mode",
            "decision", "trust_score", "approvals", "rejections",
            "was_false_positive", "was_false_negative",
        ]].rename(columns={
            "round": "Round", "pr_number": "PR#", "agent": "Agent",
            "agent_type": "Type", "in_attack_mode": "Attack?",
            "decision": "Decision", "trust_score": "Trust",
            "approvals": "Approvals", "rejections": "Rejections",
            "was_false_positive": "FP", "was_false_negative": "FN",
        })

        st.dataframe(df_display, use_container_width=True, height=400)
        st.caption(f"Showing {len(df_display)} of {len(df_pr)} PRs")

    else:
        st.info("No PR log data in this run file.")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — Analysis
# ═══════════════════════════════════════════════════════════════════════════

with tab_analysis:

    # ── Helper: build per-run analytics ──────────────────────────────────────
    def compute_analytics(run):
        s   = run.get("summary", {})
        pr  = run.get("pr_log", [])
        rds = run.get("rounds", [])
        model = run["meta"]["model"].lower()

        total_prs   = max(s.get("total_prs", 1), 1)
        atk_total   = max(s.get("attacks_attempted", 1), 1)
        benign_prs  = total_prs - s.get("attacks_attempted", 0)

        # 1. Security vs Productivity
        detection   = s.get("detection_rate") or 0
        benign_merged = sum(
            1 for p in pr
            if not p.get("in_attack_mode") and p.get("decision", "").lower() == "approve"
        )
        productivity = benign_merged / max(benign_prs, 1)

        # 2. Time-to-first-detection (round number)
        ttd = None
        for rd in rds:
            if rd.get("attacks_blocked", 0) > 0:
                ttd = rd["round"]
                break

        # 3. Per-round attack success rate
        round_atk = []
        for rd in rds:
            attempted = rd.get("attacks_attempted", 0)
            blocked   = rd.get("attacks_blocked", 0)
            succeeded = attempted - blocked
            if attempted > 0:
                round_atk.append({
                    "round": rd["round"],
                    "attempted": attempted,
                    "blocked": blocked,
                    "succeeded": succeeded,
                    "success_rate": succeeded / attempted,
                })

        # 4. Trust at time of attack (per sybil agent)
        rep_by_round = {rd["round"]: rd.get("agent_reputations", {}) for rd in rds}
        first_attack_pr = {}
        for p in pr:
            if p.get("in_attack_mode"):
                agent = p["agent"]
                if agent not in first_attack_pr:
                    first_attack_pr[agent] = p["round"]

        trust_at_attack = {}
        for agent, rnd in first_attack_pr.items():
            rep = rep_by_round.get(rnd, {}).get(agent)
            if rep is not None:
                trust_at_attack[agent] = rep

        # 5. Vote polarization per PR (|approve - reject| / total_votes)
        polarizations = []
        for p in pr:
            total_v = p.get("approvals", 0) + p.get("rejections", 0)
            if total_v > 0:
                pol = abs(p.get("approvals", 0) - p.get("rejections", 0)) / total_v
                polarizations.append(pol)
        avg_polarization = sum(polarizations) / len(polarizations) if polarizations else 0

        return {
            "model":            model,
            "detection":        detection,
            "productivity":     productivity,
            "ttd":              ttd,
            "round_atk":        round_atk,
            "trust_at_attack":  trust_at_attack,
            "avg_polarization": avg_polarization,
            "polarizations":    polarizations,
        }

    analytics = [compute_analytics(r) for r in selected_runs]

    # ── 1. Security vs Productivity scatter ──────────────────────────────────
    st.markdown('<div class="section-header">1 · Security vs Productivity Trade-off</div>', unsafe_allow_html=True)
    st.caption("Ideal model sits in the top-right corner: high detection AND high benign merge rate.")

    scatter_rows = [{
        "Model": a["model"].upper(),
        "Detection Rate": a["detection"],
        "Benign Merge Rate": a["productivity"],
        "color": model_color(a["model"]),
    } for a in analytics]
    df_scatter = pd.DataFrame(scatter_rows)

    fig_scatter = go.Figure()
    # Quadrant shading
    fig_scatter.add_shape(type="rect", x0=0.5, x1=1.01, y0=0.5, y1=1.01,
                          fillcolor="rgba(63,185,80,0.07)", line_width=0)
    fig_scatter.add_shape(type="rect", x0=0, x1=0.5, y0=0, y1=0.5,
                          fillcolor="rgba(248,81,73,0.07)", line_width=0)
    fig_scatter.add_annotation(x=0.75, y=0.97, text="✅ Ideal zone", showarrow=False,
                               font=dict(color="#3fb950", size=11))
    fig_scatter.add_annotation(x=0.25, y=0.03, text="❌ Worst zone", showarrow=False,
                               font=dict(color="#f85149", size=11))
    # Reference lines
    fig_scatter.add_hline(y=0.5, line_dash="dot", line_color="#30363d", line_width=1)
    fig_scatter.add_vline(x=0.5, line_dash="dot", line_color="#30363d", line_width=1)

    for _, row in df_scatter.iterrows():
        fig_scatter.add_trace(go.Scatter(
            x=[row["Detection Rate"]], y=[row["Benign Merge Rate"]],
            mode="markers+text",
            marker=dict(size=28, color=row["color"], line=dict(color="#0d1117", width=3)),
            text=[row["Model"]], textposition="top center",
            textfont=dict(color=row["color"], size=12, family="monospace"),
            name=row["Model"],
            showlegend=False,
        ))

    fig_scatter.update_layout(
        **PLOTLY_DARK,
        xaxis=dict(title="Detection Rate", range=[-0.05, 1.1],
                   tickformat=".0%", gridcolor="#30363d"),
        yaxis=dict(title="Benign Merge Rate", range=[-0.05, 1.1],
                   tickformat=".0%", gridcolor="#30363d"),
        height=420,
        margin=dict(l=20, r=20, t=20, b=40),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

    # ── 2. Time-to-first-detection ───────────────────────────────────────────
    col_ttd, col_pol = st.columns(2)

    with col_ttd:
        st.markdown('<div class="section-header">2 · Time-to-First-Detection</div>', unsafe_allow_html=True)
        st.caption("First round in which at least one attack was successfully blocked.")

        ttd_rows = []
        for a in analytics:
            ttd_rows.append({
                "Model": a["model"].upper(),
                "Round": a["ttd"] if a["ttd"] is not None else 0,
                "Label": f"Round {a['ttd']}" if a["ttd"] is not None else "Never",
                "color": model_color(a["model"]),
            })
        df_ttd = pd.DataFrame(ttd_rows)

        fig_ttd = go.Figure()
        for _, row in df_ttd.iterrows():
            fig_ttd.add_trace(go.Bar(
                x=[row["Model"]], y=[row["Round"]],
                marker_color=row["color"] if row["Round"] > 0 else "#30363d",
                marker_line_width=0,
                text=[row["Label"]],
                textposition="outside",
                textfont=dict(color="#c9d1d9", size=13),
                name=row["Model"],
                showlegend=False,
            ))

        max_rounds = max(r["meta"]["rounds"] for r in selected_runs)
        fig_ttd.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=320,
            yaxis=dict(title="Round #", range=[0, max_rounds + 1.5],
                       gridcolor="#30363d", dtick=1),
            xaxis=dict(gridcolor="#30363d"),
            barmode="group",
        )
        st.plotly_chart(fig_ttd, use_container_width=True)

    # ── 5. Vote polarization ─────────────────────────────────────────────────
    with col_pol:
        st.markdown('<div class="section-header">5 · Vote Polarization</div>', unsafe_allow_html=True)
        st.caption("How decisive were votes? 1.0 = unanimous, 0.0 = perfectly split.")

        fig_pol = go.Figure()
        for a in analytics:
            if a["polarizations"]:
                fig_pol.add_trace(go.Violin(
                    y=a["polarizations"],
                    name=a["model"].upper(),
                    line_color=model_color(a["model"]),
                    fillcolor=hex_to_rgba(model_color(a["model"]), 0.2),
                    meanline_visible=True,
                    box_visible=True,
                    points="all",
                    jitter=0.3,
                    marker=dict(size=5, color=model_color(a["model"]), opacity=0.6),
                ))
        fig_pol.add_hline(y=0.5, line_dash="dot", line_color="#8b949e", line_width=1,
                          annotation_text="50% split", annotation_font_color="#8b949e")
        fig_pol.update_layout(
            **PLOTLY_DARK,
            margin=CHART_MARGIN,
            height=320,
            yaxis=dict(title="Polarization Score", range=[0, 1.05],
                       gridcolor="#30363d", tickformat=".0%"),
            xaxis=dict(gridcolor="#30363d"),
            showlegend=False,
        )
        st.plotly_chart(fig_pol, use_container_width=True)

    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

    # ── 3. Attack success rate by round ──────────────────────────────────────
    st.markdown('<div class="section-header">3 · Attack Success Rate by Round</div>', unsafe_allow_html=True)
    st.caption("Did the sybil ring get more or less effective as rounds progressed?")

    has_round_atk = any(a["round_atk"] for a in analytics)
    if has_round_atk:
        fig_asr = go.Figure()
        for a in analytics:
            if not a["round_atk"]:
                continue
            df_ra = pd.DataFrame(a["round_atk"])
            color = model_color(a["model"])
            # Bar: attempted vs blocked stacked
            fig_asr.add_trace(go.Bar(
                x=df_ra["round"], y=df_ra["blocked"],
                name=f"{a['model'].upper()} Blocked",
                marker_color=hex_to_rgba(color, 0.7),
                marker_line_width=0,
                legendgroup=a["model"],
            ))
            fig_asr.add_trace(go.Bar(
                x=df_ra["round"], y=df_ra["succeeded"],
                name=f"{a['model'].upper()} Succeeded",
                marker_color="#f85149",
                marker_line_width=0,
                legendgroup=a["model"],
                marker_pattern_shape="/",
            ))
            # Overlay line for success rate
            fig_asr.add_trace(go.Scatter(
                x=df_ra["round"], y=df_ra["success_rate"],
                name=f"{a['model'].upper()} Success %",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color=color, width=2.5, dash="dot"),
                marker=dict(size=8, color=color),
                legendgroup=a["model"],
            ))

        fig_asr.update_layout(
            **PLOTLY_DARK,
            barmode="stack",
            margin=CHART_MARGIN,
            height=360,
            xaxis=dict(title="Round", gridcolor="#30363d", dtick=1),
            yaxis=dict(title="Attacks (count)", gridcolor="#30363d"),
            yaxis2=dict(
                title="Success Rate",
                overlaying="y", side="right",
                range=[0, 1.05], tickformat=".0%",
                gridcolor="#30363d", showgrid=False,
            ),
            legend=dict(font_color="#c9d1d9", bgcolor="#161b22",
                        bordercolor="#30363d", orientation="h",
                        yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_asr, use_container_width=True)
    else:
        st.info("No attack rounds found in selected runs.")

    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)

    # ── 4. Trust at time of attack ────────────────────────────────────────────
    st.markdown('<div class="section-header">4 · Agent Reputation When Switching to Attack Mode</div>', unsafe_allow_html=True)
    st.caption("How much trust did sybil agents accumulate before they struck?")

    trust_rows = []
    for a in analytics:
        for agent, rep in a["trust_at_attack"].items():
            trust_rows.append({
                "Agent": agent,
                "Model": a["model"].upper(),
                "Reputation": rep,
                "color": model_color(a["model"]),
            })

    if trust_rows:
        df_tat = pd.DataFrame(trust_rows).sort_values("Reputation", ascending=True)

        fig_tat = go.Figure()
        for model_val in df_tat["Model"].unique():
            sub = df_tat[df_tat["Model"] == model_val]
            color = model_color(model_val.lower())
            fig_tat.add_trace(go.Bar(
                x=sub["Reputation"], y=sub["Agent"] + f" ({model_val})",
                orientation="h",
                marker_color=color,
                marker_line_width=0,
                text=[f"{v:.0%}" for v in sub["Reputation"]],
                textposition="outside",
                textfont=dict(color="#c9d1d9", size=11),
                name=model_val,
            ))

        fig_tat.add_vline(x=0.5, line_dash="dash", line_color="#8b949e",
                          annotation_text="Starting rep (0.5)",
                          annotation_font_color="#8b949e",
                          annotation_position="top")
        fig_tat.add_vline(x=0.6, line_dash="dash", line_color="#3fb950",
                          annotation_text="Trust threshold",
                          annotation_font_color="#3fb950",
                          annotation_position="top")
        fig_tat.update_layout(
            **PLOTLY_DARK,
            barmode="group",
            margin=dict(l=20, r=80, t=40, b=20),
            height=max(280, len(trust_rows) * 45 + 80),
            xaxis=dict(range=[0, 1.1], gridcolor="#30363d", tickformat=".0%",
                       title="Reputation at First Attack"),
            yaxis=dict(gridcolor="#30363d"),
            legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
        )
        st.plotly_chart(fig_tat, use_container_width=True)
    else:
        st.info("No attack PRs with reputation data found. Ensure sybil mode was active.")

    # ── Summary insight cards ─────────────────────────────────────────────────
    st.markdown('<div class="govim-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Insights Summary</div>', unsafe_allow_html=True)

    insight_cols = st.columns(len(analytics))
    for col, a in zip(insight_cols, analytics):
        model = a["model"].upper()
        color = model_color(a["model"])
        ttd_str = f"Round {a['ttd']}" if a["ttd"] else "Never"
        pol_str = f"{a['avg_polarization']:.0%}"
        prod_str = f"{a['productivity']:.0%}"
        det_str = f"{a['detection']:.0%}"
        avg_trust = (
            sum(a["trust_at_attack"].values()) / len(a["trust_at_attack"])
            if a["trust_at_attack"] else None
        )
        trust_str = f"{avg_trust:.0%}" if avg_trust is not None else "N/A"

        with col:
            st.markdown(f"""
            <div class="hero-card" style="text-align:left;">
                <div class="model-name" style="color:{color};">{model}</div>
                <table style="width:100%;border-collapse:collapse;font-size:0.82rem;">
                    <tr>
                        <td style="color:#8b949e;padding:4px 0;">Detection</td>
                        <td style="color:#c9d1d9;text-align:right;font-weight:600;">{det_str}</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:4px 0;">Productivity</td>
                        <td style="color:#c9d1d9;text-align:right;font-weight:600;">{prod_str}</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:4px 0;">1st Detection</td>
                        <td style="color:#c9d1d9;text-align:right;font-weight:600;">{ttd_str}</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:4px 0;">Vote Polarization</td>
                        <td style="color:#c9d1d9;text-align:right;font-weight:600;">{pol_str}</td>
                    </tr>
                    <tr>
                        <td style="color:#8b949e;padding:4px 0;">Avg Trust at Attack</td>
                        <td style="color:#c9d1d9;text-align:right;font-weight:600;">{trust_str}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 6 — Sybil vs Normal comparison
# ═══════════════════════════════════════════════════════════════════════════

with tab_compare:
    sybil_runs  = [r for r in all_runs if r["meta"].get("sybil_mode")]
    normal_runs = [r for r in all_runs if not r["meta"].get("sybil_mode")]

    if not sybil_runs or not normal_runs:
        st.info(
            "This tab requires at least one SYBIL run and one NORMAL run.\n\n"
            "```bash\n"
            "python main.py --model decentralized          # normal\n"
            "python main.py --model decentralized --sybil  # sybil\n"
            "```"
        )
    else:
        st.markdown("""
        <div style='padding:8px 0 20px 0;'>
            <h2 style='margin:0;color:#e6edf3;'>Sybil Attack Impact</h2>
            <p style='color:#8b949e;margin:4px 0 0 0;font-size:0.9rem;'>
                Side-by-side: how each governance model performs with vs without a coordinated ring attack
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Build a combined dataframe keyed by (model, mode)
        def run_to_row(run):
            s = run.get("summary", {})
            m = run["meta"]
            total_prs = max(s.get("total_prs", 1), 1)
            atk = max(s.get("attacks_attempted", 1), 1)
            benign = max(total_prs - atk, 1)
            return {
                "model": m["model"].lower(),
                "mode": "Sybil" if m.get("sybil_mode") else "Normal",
                "detection": (s.get("detection_rate") or 0) * 100,
                "merged": s.get("total_merged", 0),
                "rejected": s.get("total_rejected", 0),
                "total_prs": total_prs,
                "attacks": s.get("attacks_attempted", 0),
                "blocked": s.get("attacks_blocked", 0),
                "succeeded": s.get("attacks_succeeded", 0),
                "false_pos": s.get("false_positives", 0),
                "benign_merge_rate": s.get("total_merged", 0) / benign * 100,
                "merge_rate": s.get("total_merged", 0) / total_prs * 100,
            }

        compare_rows = [run_to_row(r) for r in all_runs]
        df_cmp = pd.DataFrame(compare_rows)

        # ── Detection rate grouped bar ──
        st.markdown('<div class="section-header">Detection Rate: Sybil vs Normal</div>', unsafe_allow_html=True)

        fig_det = go.Figure()
        for mode, color in [("Normal", "#3fb950"), ("Sybil", "#f85149")]:
            sub = df_cmp[df_cmp["mode"] == mode].sort_values("model")
            if sub.empty:
                continue
            fig_det.add_trace(go.Bar(
                name=mode,
                x=[m.upper() for m in sub["model"]],
                y=sub["detection"],
                marker_color=color,
                marker_line_width=0,
                text=[f"{v:.0f}%" for v in sub["detection"]],
                textposition="outside",
                textfont=dict(color="#c9d1d9"),
            ))

        fig_det.update_layout(
            **PLOTLY_DARK,
            barmode="group",
            height=340,
            margin=CHART_MARGIN,
            yaxis=dict(range=[0, 115], ticksuffix="%", gridcolor="#30363d",
                       title="Attack Detection Rate"),
            xaxis=dict(gridcolor="#30363d"),
            legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
        )
        st.plotly_chart(fig_det, use_container_width=True)

        # ── Merge rate impact ──
        col_merge, col_attack = st.columns(2)

        with col_merge:
            st.markdown('<div class="section-header">Benign PR Merge Rate</div>', unsafe_allow_html=True)
            fig_mr = go.Figure()
            for mode, color in [("Normal", "#3fb950"), ("Sybil", "#f85149")]:
                sub = df_cmp[df_cmp["mode"] == mode].sort_values("model")
                if sub.empty:
                    continue
                fig_mr.add_trace(go.Bar(
                    name=mode,
                    x=[m.upper() for m in sub["model"]],
                    y=sub["benign_merge_rate"],
                    marker_color=color,
                    marker_line_width=0,
                    text=[f"{v:.0f}%" for v in sub["benign_merge_rate"]],
                    textposition="outside",
                    textfont=dict(color="#c9d1d9"),
                ))
            fig_mr.update_layout(
                **PLOTLY_DARK, barmode="group", height=300, margin=CHART_MARGIN,
                yaxis=dict(range=[0, 115], ticksuffix="%", gridcolor="#30363d"),
                xaxis=dict(gridcolor="#30363d"),
                legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
            )
            st.plotly_chart(fig_mr, use_container_width=True)

        with col_attack:
            st.markdown('<div class="section-header">Attacks Succeeded vs Blocked</div>', unsafe_allow_html=True)
            sybil_only = df_cmp[df_cmp["mode"] == "Sybil"].sort_values("model")
            if not sybil_only.empty:
                fig_ab = go.Figure()
                fig_ab.add_trace(go.Bar(
                    name="Blocked",
                    x=[m.upper() for m in sybil_only["model"]],
                    y=sybil_only["blocked"],
                    marker_color="#3fb950", marker_line_width=0,
                    text=sybil_only["blocked"], textposition="inside",
                    textfont=dict(color="#0d1117", size=12, weight="bold"),
                ))
                fig_ab.add_trace(go.Bar(
                    name="Succeeded",
                    x=[m.upper() for m in sybil_only["model"]],
                    y=sybil_only["succeeded"],
                    marker_color="#f85149", marker_line_width=0,
                    text=sybil_only["succeeded"], textposition="inside",
                    textfont=dict(color="#ffffff", size=12, weight="bold"),
                ))
                fig_ab.update_layout(
                    **PLOTLY_DARK, barmode="stack", height=300, margin=CHART_MARGIN,
                    yaxis=dict(gridcolor="#30363d", title="Attack PRs"),
                    xaxis=dict(gridcolor="#30363d"),
                    legend=dict(font_color="#c9d1d9", bgcolor="#161b22", bordercolor="#30363d"),
                )
                st.plotly_chart(fig_ab, use_container_width=True)
            else:
                st.info("No sybil runs in current selection.")

        # ── Delta table (impact of sybil attack per model) ──
        st.markdown('<div class="section-header">Sybil Attack Delta per Model</div>', unsafe_allow_html=True)

        delta_rows = []
        all_models = df_cmp["model"].unique()
        for mdl in sorted(all_models):
            n = df_cmp[(df_cmp["model"] == mdl) & (df_cmp["mode"] == "Normal")]
            s = df_cmp[(df_cmp["model"] == mdl) & (df_cmp["mode"] == "Sybil")]
            if n.empty or s.empty:
                continue
            n, s = n.iloc[0], s.iloc[0]
            det_delta = s["detection"] - n["detection"]
            merge_delta = s["benign_merge_rate"] - n["benign_merge_rate"]
            delta_rows.append({
                "Model": mdl.upper(),
                "Normal Detection": f"{n['detection']:.0f}%",
                "Sybil Detection": f"{s['detection']:.0f}%",
                "Detection Delta": f"{det_delta:+.0f}%",
                "Normal Merge Rate": f"{n['benign_merge_rate']:.0f}%",
                "Sybil Merge Rate": f"{s['benign_merge_rate']:.0f}%",
                "Merge Rate Delta": f"{merge_delta:+.0f}%",
                "Attacks Succeeded": int(s["succeeded"]),
                "Resilience": "Strong" if s["detection"] >= 80 else ("Moderate" if s["detection"] >= 50 else "Weak"),
            })

        if delta_rows:
            df_delta = pd.DataFrame(delta_rows).set_index("Model")
            st.dataframe(df_delta, use_container_width=True)
        else:
            st.info("Need at least one model with both sybil and normal runs to compute deltas.")

        # ── Scatter: security vs productivity across both modes ──
        st.markdown('<div class="section-header">Security vs Productivity — All Runs</div>', unsafe_allow_html=True)
        st.caption("Each point = one run. Shape = governance model, color = mode (green=normal, red=sybil).")

        scatter_fig = go.Figure()
        mode_colors = {"Normal": "#3fb950", "Sybil": "#f85149"}
        model_symbols = {"centralized": "circle", "decentralized": "square", "hybrid": "diamond"}

        for _, row in df_cmp.iterrows():
            scatter_fig.add_trace(go.Scatter(
                x=[row["benign_merge_rate"]],
                y=[row["detection"]],
                mode="markers+text",
                name=f"{row['model'].upper()} {row['mode']}",
                marker=dict(
                    size=18,
                    color=mode_colors.get(row["mode"], "#c9d1d9"),
                    symbol=model_symbols.get(row["model"], "circle"),
                    line=dict(color="#21262d", width=2),
                    opacity=0.9,
                ),
                text=[f"{row['model'].upper()}<br>{row['mode']}"],
                textposition="top center",
                textfont=dict(size=10, color="#c9d1d9"),
                showlegend=False,
            ))

        scatter_fig.update_layout(
            **PLOTLY_DARK,
            height=420,
            margin=dict(l=40, r=40, t=50, b=60),
            xaxis=dict(range=[-5, 115], ticksuffix="%", gridcolor="#30363d",
                       title="Benign PR Merge Rate (Productivity)"),
            yaxis=dict(range=[-5, 115], ticksuffix="%", gridcolor="#30363d",
                       title="Attack Detection Rate (Security)"),
        )
        # Quadrant shading
        scatter_fig.add_shape(type="rect", x0=50, x1=115, y0=50, y1=115,
                              fillcolor="rgba(63,185,80,0.06)", line_width=0)
        scatter_fig.add_annotation(x=82, y=108, text="Ideal Zone", showarrow=False,
                                   font=dict(color="#3fb950", size=11))
        scatter_fig.add_shape(type="line", x0=50, x1=50, y0=-5, y1=115,
                              line=dict(color="#30363d", dash="dash", width=1))
        scatter_fig.add_shape(type="line", x0=-5, x1=115, y0=50, y1=50,
                              line=dict(color="#30363d", dash="dash", width=1))
        st.plotly_chart(scatter_fig, use_container_width=True)


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='text-align:center; padding:32px 0 16px 0; border-top:1px solid #30363d; margin-top:32px;'>
    <span style='color:#8b949e; font-size:0.75rem;'>GOVIM · Governance Simulation Framework ·
    Sybil &amp; Normal Mode Comparison Dashboard</span>
</div>
""", unsafe_allow_html=True)
