#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import streamlit as st
import duckdb
import plotly.express as px
import folium
from streamlit.components.v1 import html as st_html
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Seattle Crime Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
    <style>
        .main { background-color: #f4f6f9; color: #1a1a2e; }
        .block-container { padding-top: 1rem !important; }

        /* ── HEADER ── */
        .header-box {
            background-color: #c8c8c8;
            text-align: center;
            padding: 15px 15px 15px 15px;
            margin-bottom: 0px;
        }
        .header-title {
            font-size: 1.9rem;
            font-weight: 800;
            color: #5b9bd5;
            margin-top: 12px;
        }
        .header-sub {
            font-size: 0.85rem;
            color: #333;
            margin-top: 2px;
            font-weight: 700;
        }
        .header-update {
            font-size: 0.85rem;
            color: #5b9bd5;
            font-weight: 700;
        }

        /* ── KPI KARTEN ── */
        .kpi-row {
            display: flex;
            border: 1px solid #ccc;
            background: white;
        }
        .kpi-card {
            flex: 1;
            padding: 16px 20px;
            text-align: center;
            border-right: 1px solid #ccc;
        }
        .kpi-card:last-child { border-right: none; }
        .kpi-category {
            font-size: 1.15rem;
            font-weight: 800;
            color: #1a6bb5;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .kpi-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #1a6bb5;
            margin-top: 2px;
        }

        /* ── FILTER BAR ── */
        /* Dunkle Leiste */
        [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
            background-color: #3d3d3d;
            padding: 6px 12px 8px 12px;
            margin-bottom: 0px;
            gap: 6px;
        }
        /* Popover: volle Breite */
        [data-testid="stPopover"] { width: 100%; }
        /* Label über Popover-Button (via st.markdown davor) */
        .filter-col-label {
            color: #cccccc;
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 2px;
            margin-top: 2px;
        }
        /* Popover-Button als kompaktes Dropdown */
        [data-testid="stPopover"] button[kind="secondary"] {
            width: 100% !important;
            background-color: #ffffff !important;
            color: #1a1a1a !important;
            border: 1px solid #888 !important;
            border-radius: 3px !important;
            font-size: 0.78rem !important;
            padding: 3px 8px !important;
            min-height: 30px !important;
            text-align: left !important;
            justify-content: space-between !important;
        }
        /* Popover-Inhalt: hellgrauer Hintergrund, weiße Schrift */
        [data-testid="stPopoverBody"],
        [data-testid="stPopoverBody"] > div,
        [data-testid="stPopoverBody"] > div > div,
        [data-testid="stPopoverBody"] section,
        [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"],
        [data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #b0b0b0 !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stPopoverBody"] label,
        [data-testid="stPopoverBody"] p,
        [data-testid="stPopoverBody"] span {
            color: #ffffff !important;
        }
        /* Checkbox-Farbe blau */
        [data-testid="stPopoverBody"] input[type="checkbox"] {
            accent-color: #1a6bb5 !important;
        }
        [data-testid="stPopoverBody"] button[kind="primary"] {
            background-color: #1a6bb5 !important;
            border-color: #1a6bb5 !important;
            color: #ffffff !important;
        }
        [data-testid="stPopoverBody"] button[kind="primary"]:hover {
            background-color: #155a9a !important;
            border-color: #155a9a !important;
        }

        /* ── SUBHEADER BALKEN ── */
        [data-testid="stHeading"] {
            background-color: #e2e2e2;
            padding: 2px 15px;
            margin-bottom: 0px;
            min-height: 0px;
            text-align: center;
        }
        [data-testid="stHeading"] div { text-align: center !important; width: 100% !important; }
        h2, h3 { color: #1a3a5c !important; }
        hr { border-color: #d0dce8; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATENBANKVERBINDUNG
# ─────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "seattle_crime.db")

@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        import crime_db
        crime_db.DB_PATH = DB_PATH
        with st.spinner("Datenbank wird erstmalig aufgebaut – das kann einen Moment dauern..."):
            crime_db.build_database()
    return duckdb.connect(DB_PATH, read_only=True)

conn = get_connection()

# ─────────────────────────────────────────────
# GEOJSON – Seattle Precincts (gecacht)
# ─────────────────────────────────────────────
def load_precinct_geojson():
    import json as _json
    local = os.path.join(BASE_DIR, "spd-precincts.geojson")
    if os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            return _json.load(f)
    return None

# GeoJSON nutzt Kürzel (N, E, S, W, SW) → Mapping auf volle Namen wie in den Daten
PRECINCT_MAP = {"N": "North", "E": "East", "S": "South", "W": "West", "SW": "Southwest"}

precinct_geojson = load_precinct_geojson()

# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
@st.cache_data
def load_filter_options(_conn):
    jahre = _conn.execute("""
        SELECT DISTINCT jahr FROM crimes_clean
        WHERE jahr BETWEEN 2008 AND 2026
        ORDER BY jahr DESC
    """).df()["jahr"].tolist()

    kategorien = _conn.execute("""
        SELECT DISTINCT "Offense Category" FROM crimes_clean
        WHERE "Offense Category" IS NOT NULL ORDER BY 1
    """).df()["Offense Category"].tolist()

    subkategorien = _conn.execute("""
        SELECT DISTINCT "Offense Sub Category" FROM crimes_clean
        WHERE "Offense Sub Category" IS NOT NULL ORDER BY 1
    """).df()["Offense Sub Category"].tolist()

    precincts = _conn.execute("""
        SELECT DISTINCT Precinct FROM crimes_clean
        WHERE Precinct IS NOT NULL AND Precinct != '' ORDER BY 1
    """).df()["Precinct"].tolist()

    beats = _conn.execute("""
        SELECT DISTINCT Beat FROM crimes_clean
        WHERE Beat IS NOT NULL AND Beat != '' ORDER BY 1
    """).df()["Beat"].tolist()

    neighborhoods = _conn.execute("""
        SELECT DISTINCT Neighborhood FROM crimes_clean
        WHERE Neighborhood IS NOT NULL AND Neighborhood != '' ORDER BY 1
    """).df()["Neighborhood"].tolist()

    return jahre, kategorien, subkategorien, precincts, beats, neighborhoods


def build_where(jahre_sel, kat_sel, sub_sel, pre_sel, beat_sel, nb_sel):
    return f"""
        jahr IN ({', '.join(str(j) for j in jahre_sel)})
        AND "Offense Category"    IN ({', '.join(f"'{k}'" for k in kat_sel)})
        AND "Offense Sub Category" IN ({', '.join(f"'{s}'" for s in sub_sel)})
        AND Precinct   IN ({', '.join(f"'{p}'" for p in pre_sel)})
        AND Beat       IN ({', '.join(f"'{b}'" for b in beat_sel)})
        AND Neighborhood IN ({', '.join(f"'{n}'" for n in nb_sel)})
    """


def query_data(_conn, jahre_sel, kat_sel, sub_sel, pre_sel, beat_sel, nb_sel):
    return _conn.execute(f"""
        SELECT * FROM crimes_clean
        WHERE {build_where(jahre_sel, kat_sel, sub_sel, pre_sel, beat_sel, nb_sel)}
    """).df()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
today_str = date.today().strftime("%d.%m.%Y")
st.markdown(f"""
    <div class="header-box">
        <div class="header-title">Year to Date Totals</div>
        <div class="header-sub">By count of Offense ID</div>
        <div class="header-update">Last Update: {today_str}</div>
    </div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PLATZHALTER für KPI Karten
# ─────────────────────────────────────────────
kpi_placeholder = st.empty()

# ─────────────────────────────────────────────
# FILTER – 6 Spalten, kompakt, dunkle Leiste
# ─────────────────────────────────────────────
jahre_alle, kat_alle, sub_alle, pre_alle, beat_alle, nb_alle = load_filter_options(conn)

# Session State initialisieren (nur beim ersten Aufruf)
for key, default in [
    ("ms_jahr", jahre_alle[:1]),   # Standard: nur neuestes Jahr
    ("ms_kat",  kat_alle),
    ("ms_sub",  sub_alle),
    ("ms_pre",  pre_alle),
    ("ms_beat", beat_alle),
    ("ms_nb",   nb_alle),
]:
    if key not in st.session_state:
        st.session_state[key] = default[:]

# Checkbox-States für alle Filter initialisieren
_cb_init = [
    ("ms_jahr", jahre_alle, "cb_jahr_"),
    ("ms_kat",  kat_alle,   "cb_kat_"),
    ("ms_sub",  sub_alle,   "cb_sub_"),
    ("ms_pre",  pre_alle,   "cb_pre_"),
    ("ms_beat", beat_alle,  "cb_beat_"),
    ("ms_nb",   nb_alle,    "cb_nb_"),
]
for ms_key, opts, prefix in _cb_init:
    for opt in opts:
        cb_key = f"{prefix}{opt}"
        if cb_key not in st.session_state:
            st.session_state[cb_key] = opt in st.session_state[ms_key]


def render_checkbox_popover(col, label, ms_key, opts, prefix, default):
    with col:
        st.markdown(f'<div class="filter-col-label">{label}</div>', unsafe_allow_html=True)
        with st.popover(sel_label(ms_key, opts), use_container_width=True):
            for opt in opts:
                st.checkbox(str(opt), key=f"{prefix}{opt}")
            if st.button("Übernehmen", use_container_width=True, type="primary", key=f"btn_{ms_key}"):
                selected = [opt for opt in opts if st.session_state.get(f"{prefix}{opt}", False)]
                st.session_state[ms_key] = selected if selected else default[:]
                st.rerun()
    return st.session_state[ms_key]


def sel_label(key: str, all_opts: list) -> str:
    sel = st.session_state.get(key, all_opts)
    if len(sel) == 0:             return "(Keine) ▾"
    if len(sel) == len(all_opts): return "(Alle) ▾"
    if len(sel) == 1:             return f"{sel[0]} ▾"
    return f"{len(sel)} ausgewählt ▾"


col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([1, 1.6, 2, 1.2, 1.2, 1.8])

jahre_sel = render_checkbox_popover(col_f1, "Jahr",                 "ms_jahr", jahre_alle, "cb_jahr_", jahre_alle[:1])
kat_sel   = render_checkbox_popover(col_f2, "Offense Category",     "ms_kat",  kat_alle,   "cb_kat_",  kat_alle)
sub_sel   = render_checkbox_popover(col_f3, "Offense Sub Category", "ms_sub",  sub_alle,   "cb_sub_",  sub_alle)
pre_sel   = render_checkbox_popover(col_f4, "Precinct",             "ms_pre",  pre_alle,   "cb_pre_",  pre_alle)
beat_sel  = render_checkbox_popover(col_f5, "Beat",                 "ms_beat", beat_alle,  "cb_beat_", beat_alle)
nb_sel    = render_checkbox_popover(col_f6, "Neighborhood",         "ms_nb",   nb_alle,    "cb_nb_",   nb_alle)

if not jahre_sel or not kat_sel or not sub_sel or not pre_sel or not beat_sel or not nb_sel:  # noqa
    st.warning("⚠️ Bitte mindestens eine Option pro Filter auswählen.")
    st.stop()

# ─────────────────────────────────────────────
# DATEN LADEN
# ─────────────────────────────────────────────
with st.spinner("Daten werden geladen..."):
    df = query_data(conn, jahre_sel, kat_sel, sub_sel, pre_sel, beat_sel, nb_sel)

# ─────────────────────────────────────────────
# KPI KARTEN
# ─────────────────────────────────────────────
with kpi_placeholder.container():
    violent_count  = len(df[df["Offense Category"] == "VIOLENT CRIME"])  if not df.empty else 0
    property_count = len(df[df["Offense Category"] == "PROPERTY CRIME"]) if not df.empty else 0
    other_count    = len(df[df["Offense Category"] == "ALL OTHER"])       if not df.empty else 0

    st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-category">Violent Crime</div>
                <div class="kpi-value">{violent_count:,}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-category">Property Crime</div>
                <div class="kpi-value">{property_count:,}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-category">All Other</div>
                <div class="kpi-value">{other_count:,}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# WHERE-Klausel für Chart-Queries
# ─────────────────────────────────────────────
where = build_where(jahre_sel, kat_sel, sub_sel, pre_sel, beat_sel, nb_sel)

# ─────────────────────────────────────────────
# CHARTS – TABELLE & KARTE
# ─────────────────────────────────────────────
col_verteilung, col_karte = st.columns([1, 1])

with col_verteilung:
    _js = sorted(jahre_sel, reverse=True)
    if len(_js) == 1:
        jahr_label = str(_js[0])
    elif len(_js) <= 3:
        jahr_label = ", ".join(str(j) for j in _js)
    else:
        jahr_label = ", ".join(str(j) for j in _js[:3]) + f" und {len(_js)-3} mehr"
    st.markdown(
        f'<div style="background-color:#e2e2e2;padding:2px 15px;">'
        f'<h3 style="margin:0;font-size:1.1rem;line-height:1.4;color:#1a3a5c;">'
        f'Offense Totals by Year <span style="color:#5b9bd5;">{jahr_label}</span>'
        f'</h3>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Pivot: eine Spalte pro Jahr via CASE WHEN
    jahre_sorted = sorted(jahre_sel, reverse=True)
    year_cols_sql = ", ".join(
        f'SUM(CASE WHEN jahr = {j} THEN 1 ELSE 0 END) as "{j}"'
        for j in jahre_sorted
    )
    tabelle_df = conn.execute(f"""
        SELECT
            "Offense Category"     as kategorie,
            "Offense Sub Category" as subkategorie,
            {year_cols_sql}
        FROM crimes_clean
        WHERE {where}
          AND "Offense Sub Category" IS NOT NULL
        GROUP BY "Offense Category", "Offense Sub Category"
        ORDER BY "Offense Category", "{jahre_sorted[0]}" DESC
    """).df()

    j_cols = [str(j) for j in jahre_sorted]

    html = """
    <style>
        .crime-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        .crime-table th { padding: 5px 7px; background: #e8edf2; color: #1a3a5c;
                          font-weight: 700; border-bottom: 2px solid #ccc; text-align: left; }
        .crime-table th.num { text-align: right; }
        .crime-table td { padding: 3px 7px; border-bottom: 1px solid #e8edf2; }
        .cat-row td { font-weight: 700; color: #1a3a5c; background: #f0f4f8; }
        .sub-row td:nth-child(2) { padding-left: 16px; color: #444; }
        .total-row td { font-weight: 700; color: #e67e22; }
        .grand-total td { font-weight: 800; color: #e67e22; background: #f0f4f8; }
        .num { text-align: right; }
        .cur { color: #e67e22 !important; font-weight: 700; }
    </style>
    <table class="crime-table"><tr>
        <th>Offense</th><th>Offense Sub Category</th>
    """
    for j in j_cols:
        html += f'<th class="num">{j}</th>'
    html += "</tr>"

    grand_totals = {j: 0 for j in j_cols}

    for kat in ["VIOLENT CRIME", "PROPERTY CRIME", "ALL OTHER"]:
        subset = tabelle_df[tabelle_df["kategorie"] == kat]
        if subset.empty:
            continue
        kat_totals = {j: int(subset[j].sum()) for j in j_cols}
        for j in j_cols:
            grand_totals[j] += kat_totals[j]

        # Kategorie-Zeile
        html += f'<tr class="cat-row"><td>{kat}</td><td></td>'
        for j in j_cols:
            html += '<td class="num"></td>'
        html += "</tr>"

        # Sub-Kategorien
        for _, row in subset.iterrows():
            html += f'<tr class="sub-row"><td></td><td>{row["subkategorie"]}</td>'
            for idx, j in enumerate(j_cols):
                val = int(row[j])
                css = ' class="num cur"' if idx == 0 else ' class="num"'
                html += f'<td{css}>{val:,}</td>'
            html += "</tr>"

        # Gesamtwert-Zeile
        html += '<tr class="total-row"><td></td><td>Gesamtwert</td>'
        for idx, j in enumerate(j_cols):
            css = ' class="num cur"' if idx == 0 else ' class="num"'
            html += f'<td{css}>{kat_totals[j]:,}</td>'
        html += "</tr>"

    # Gesamtsumme
    html += '<tr class="grand-total"><td>Gesamtsumme</td><td></td>'
    for idx, j in enumerate(j_cols):
        css = ' class="num"'
        html += f'<td{css}>{grand_totals[j]:,}</td>'
    html += "</tr></table>"

    st.markdown(f"""
    <div style="height:460px;overflow-y:auto;overflow-x:auto;border:1px solid #d0dce8;
                border-radius:4px;padding:8px;background:white;max-width:100%;">
        {html}
    </div>
    """, unsafe_allow_html=True)

with col_karte:
    precinct_df = conn.execute(f"""
        SELECT Precinct, COUNT(*) as anzahl
        FROM crimes_clean
        WHERE {where}
          AND Precinct IS NOT NULL AND Precinct != ''
        GROUP BY Precinct
    """).df()

    m = folium.Map(location=[47.6062, -122.3321], zoom_start=11, tiles="CartoDB positron")

    if precinct_geojson is not None:
        import copy
        anzahl_lookup = dict(zip(precinct_df["Precinct"], precinct_df["anzahl"]))
        geo_enriched = copy.deepcopy(precinct_geojson)
        for feat in geo_enriched["features"]:
            abbr = feat["properties"].get("name", "")
            full = PRECINCT_MAP.get(abbr, abbr)
            feat["properties"]["precinct_full"] = full
            feat["properties"]["anzahl"] = f'{anzahl_lookup.get(full, 0):,}'

        _choro = folium.Choropleth(
            geo_data=geo_enriched,
            data=precinct_df,
            columns=["Precinct", "anzahl"],
            key_on="feature.properties.precinct_full",
            fill_color="Blues",
            fill_opacity=0.6,
            line_opacity=0.8,
            line_color="#1a3a5c",
            legend_name="Anzahl Delikte",
            nan_fill_color="#f0f0f0",
            highlight=True,
        )
        _choro.color_scale.add_to = lambda *_, **__: None
        _choro.add_to(m)
        folium.GeoJson(
            geo_enriched,
            style_function=lambda _: {"fillOpacity": 0, "weight": 0},
            tooltip=folium.GeoJsonTooltip(
                fields=["precinct_full", "anzahl"],
                aliases=["Precinct:", "Delikte:"],
                style="font-size:13px;"
            )
        ).add_to(m)

    map_html = m.get_root().render()
    st_html(map_html, height=495, scrolling=False)

# ─────────────────────────────────────────────
# CHART – MONATLICHER TREND (eine Linie pro Jahr, Gesamt)
# ─────────────────────────────────────────────
trend_df = conn.execute(f"""
    SELECT
        jahr,
        monat,
        COUNT(*) as anzahl
    FROM crimes_clean
    WHERE {where}
    GROUP BY jahr, monat
    ORDER BY jahr, monat
""").df()

# Monatsnamen für X-Achse
monat_namen = {1:"Jan",2:"Feb",3:"Mär",4:"Apr",5:"Mai",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Okt",11:"Nov",12:"Dez"}
trend_df["monat_name"] = trend_df["monat"].map(monat_namen)
trend_df["jahr"] = trend_df["jahr"].astype(str)

# Farbpalette: neuestes Jahr dunkler, ältere heller
jahre_im_trend = sorted(trend_df["jahr"].unique(), reverse=True)
grau_stufen = ["#1a6bb5", "#e67e22", "#27ae60", "#c0392b", "#8e44ad",
               "#16a085", "#d35400", "#2980b9", "#7f8c8d", "#c0392b",
               "#f39c12", "#1abc9c", "#9b59b6", "#e74c3c", "#2ecc71"]
farb_map = {j: grau_stufen[i % len(grau_stufen)] for i, j in enumerate(jahre_im_trend)}

# Überschrift: links "Monthly Trend", daneben die Jahres-Legende als farbige Punkte
_legend_items = "".join(
    f'<span style="display:inline-flex;align-items:center;gap:5px;margin-left:14px;">'
    f'<span style="width:12px;height:12px;background:{farb_map[j]};display:inline-block;border-radius:2px;"></span>'
    f'<span style="font-size:0.78rem;color:#333;font-weight:600;">{j}</span>'
    f'</span>'
    for j in jahre_im_trend
)
st.markdown(
    f'<div style="background-color:#e2e2e2;padding:3px 15px;display:flex;'
    f'align-items:center;gap:4px;">'
    f'<span style="font-size:1.05rem;font-weight:700;color:#1a3a5c;">Monthly Trend</span>'
    f'{_legend_items}'
    f'</div>',
    unsafe_allow_html=True
)

fig_trend = px.line(
    trend_df,
    x="monat_name",
    y="anzahl",
    color="jahr",
    markers=True,
    text="anzahl",
    labels={"monat_name": "", "anzahl": "Anzahl von Offense Id", "jahr": "Jahr"},
    color_discrete_map=farb_map,
    category_orders={"monat_name": list(monat_namen.values())}
)

fig_trend.update_traces(
    textfont=dict(size=13, color="#333333"),
    marker=dict(size=6),
    mode="lines+markers+text",
    cliponaxis=False
)

# Labels je Linie abwechselnd oben/unten versetzen
positions = ["top center", "bottom center", "top center", "bottom center", "top center"]
for i, trace in enumerate(fig_trend.data):
    trace.textposition = positions[i % len(positions)]

# ── Überlappende Labels ausblenden ──
# Schätze Labelgröße in Dateneinheiten (Chartgröße 300px, Font 13px)
_y_range = (trend_df["anzahl"].max() * 1.25) - 0
_label_h  = (18 / 300) * _y_range   # 18px Sicherheitsabstand

# Texte pro Trace als veränderliche Liste speichern
_texts = {t.name: list(t.text) if t.text is not None else []
          for t in fig_trend.data}
_tpos  = {fig_trend.data[i].name: positions[i % len(positions)]
          for i in range(len(fig_trend.data))}

for _m_idx, _month in enumerate(monat_namen.values()):
    # Alle Punkte dieses Monats sammeln
    _pts = []
    for _trace in fig_trend.data:
        if _m_idx < len(_trace.x) and _trace.x[_m_idx] == _month and _m_idx < len(_texts[_trace.name]):
            _y   = _trace.y[_m_idx]
            _pos = _tpos[_trace.name]
            _ly  = _y + _label_h * 0.7 if "top" in _pos else _y - _label_h * 0.7
            _pts.append({"ly": _ly, "name": _trace.name, "midx": _m_idx})

    # Paare auf Überlappung prüfen
    for _a in range(len(_pts)):
        for _b in range(_a + 1, len(_pts)):
            if abs(_pts[_a]["ly"] - _pts[_b]["ly"]) < _label_h:
                # Jüngeres Trace (höherer Index) behält Label, älteres wird ausgeblendet
                _hide = _pts[_b]["name"]
                _mi   = _pts[_b]["midx"]
                if _mi < len(_texts[_hide]):
                    _texts[_hide][_mi] = ""

# Aktualisierte Texte zurückschreiben
for _trace in fig_trend.data:
    if _texts[_trace.name]:
        _trace.text = _texts[_trace.name]
fig_trend.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color="#1a3a5c"),
    showlegend=False,
    hovermode="x unified",
    height=280,
    margin=dict(l=10, r=10, t=35, b=10),
    xaxis=dict(
        showgrid=False,
        tickfont=dict(color="#1a3a5c"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#e8edf2",
        tickfont=dict(color="#1a3a5c"),
        title_font=dict(color="#1a3a5c"),
        tick0=0,
        dtick=2000,
        range=[0, trend_df["anzahl"].max() * 1.18],
    )
)

st.plotly_chart(fig_trend, use_container_width=True, height=350)

# ─────────────────────────────────────────────
# HEATMAP – auskommentiert
# ─────────────────────────────────────────────
# with col_heatmap:
#     st.subheader("Heatmap – Time × Day")
#     heatmap_df = conn.execute(f"""
#         SELECT wochentag, stunde, COUNT(*) as anzahl
#         FROM crimes_clean WHERE {where}
#         GROUP BY wochentag, stunde ORDER BY wochentag, stunde
#     """).df()
#     tage = {0:"So",1:"Mo",2:"Di",3:"Mi",4:"Do",5:"Fr",6:"Sa"}
#     heatmap_df["tag_name"] = heatmap_df["wochentag"].map(tage)
#     pivot = heatmap_df.pivot_table(index="tag_name",columns="stunde",values="anzahl",aggfunc="sum",fill_value=0)
#     pivot = pivot.reindex(["Mo","Di","Mi","Do","Fr","Sa","So"])
#     pivot = pivot.reindex(columns=range(24), fill_value=0)
#     fig_heat = px.imshow(pivot, labels=dict(x="Uhrzeit",y="Wochentag",color="Delikte"),
#         color_continuous_scale=["#e8f4fd","#1a6bb5","#c0392b"], aspect="auto")
#     st.plotly_chart(fig_heat, use_container_width=True)

# ─────────────────────────────────────────────
# ROHDATEN – auskommentiert
# ─────────────────────────────────────────────
# with st.expander("🔎 Rohdaten anzeigen"):
#     st.dataframe(df.head(500), use_container_width=True)