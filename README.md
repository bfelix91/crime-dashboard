# Seattle Crime Dashboard

> Open-Source Nachbau des [Seattle Police Department Crime Dashboards](https://www.seattle.gov/police/information-and-data/data/crime-dashboard)  
> Modul: Datenaufbereitung und Visualisierung | THWS | Felix Beck

---

## Projektbeschreibung

Dieses Projekt ist eine vollständige Open-Source-Nachbildung des öffentlich zugänglichen Crime Dashboards der Stadt Seattle, das ursprünglich mit proprietären Tools (ArcGIS / Tableau) umgesetzt wurde.

**Ziel:** Die gesamte Nachbau – von der Rohdatenaufbereitung bis zum interaktiven Dashboard – ausschließlich mit freien, quelloffenen Werkzeugen nachbauen.

Das Original-Dashboard basiert auf **Tableau** ([Fallstudie](https://www.tableau.com/solutions/workbook/visualizing-crime-and-increasing-transparency-in-seattle)) 
und **ArcGIS** ([Dashboard](https://www.arcgis.com/home/item.html?id=241ee9264d4b4d9e8ab902a78e19a48c)).

---

## Tech Stack

| Tool | Version | Zweck |
|------|---------|-------|
| Python | 3.12 | Programmiersprache |
| Streamlit | ≥ 1.30 | Web-Interface |
| DuckDB | ≥ 0.9 | Datenbank & SQL-Abfragen |
| Pandas | ≥ 2.0 | Datenverarbeitung |
| Plotly | ≥ 5.0 | Zeitreihen & Charts |
| Folium | ≥ 0.15 | Interaktive Karte |
| streamlit-folium | ≥ 0.18 | Folium in Streamlit |

---

## Datenbasis

**Datensatz:** [SPD Crime Data: 2008–Present](https://data.seattle.gov)  
**Bereitgestellt von:** Seattle Police Department  
**Lizenz:** Public Domain

| Merkmal | Wert |
|---------|------|
| Zeilen (gesamt) | 1.54 M |
| Zeilen (bereinigt) | 1.296.053 (85%) |
| Spalten | 20 |
| Zeitraum | 2008 – 2026 |
| Dateigröße | ca. 382 MB |

---

## Projektstruktur

```
crime-dashboard/
├── sc_dashboard_neu.py      ← Streamlit App (Hauptdatei)
├── crime_db.py              ← Datenaufbereitung & DuckDB Import
├── handout.qmd              ← Quarto Dokumentation
├── requirements.txt         ← Python Pakete
├── .gitignore               ← CSV & DB ausgeschlossen
└── README.md                ← Diese Datei
```

> **Hinweis:** Die Rohdaten (`Crime_Data__2008-Present.csv`) und die Datenbank (`seattle_crime.db`) sind aus Größengründen nicht im Repository enthalten.

---

## Installation & Start

**1. Repository klonen:**
```bash
git clone git@github.com:FelixB54/crime-dashboard.git
cd crime-dashboard
```

**2. Pakete installieren:**
```bash
pip install streamlit duckdb pandas plotly folium streamlit-folium
```

**3. Datensatz herunterladen:**  
[SPD Crime Data von data.seattle.gov](https://data.seattle.gov/Public-Safety/SPD-Crime-Data-2008-Present/tazs-3rd5) als CSV herunterladen und in den Projektordner legen.

**4. Datenbank aufbauen:**
```bash
python crime_db.py
```

**5. Dashboard starten:**
```bash
streamlit run sc_dashboard_neu.py
```

---

## Datenaufbereitung

### Qualitätsprobleme & Lösungen

| Problem | Umfang | Lösung |
|---------|--------|--------|
| `REDACTED` Koordinaten | ~220k Zeilen | Gefiltert |
| Dirty Dates (1900-01-01) | Vereinzelt | Jahr < 2008 gefiltert |
| Nullwerte Neighborhood/Precinct | Gering | Gefiltert |

### Bereinigungsschritt
```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS crimes_clean AS
    SELECT *,
        EXTRACT(hour FROM strptime("Report DateTime", '%Y %b %d %I:%M:%S %p')) AS stunde,
        DAYOFWEEK(strptime("Report DateTime", '%Y %b %d %I:%M:%S %p')) AS wochentag,
        YEAR(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS jahr,
        MONTH(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS monat
    FROM crimes
    WHERE YEAR(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) >= 2008
        AND Latitude NOT IN ('REDACTED', '0')
        AND Longitude NOT IN ('REDACTED', '0')
""")
```

---

## Dashboard-Komponenten

### Filter-System
6 interaktive Popover-Filter in einer kompakten dunklen Leiste:
&nbsp;
![KPI Karten](screenshots/filter.png)
&nbsp;
- **Jahr** – 2008 bis 2026
- **Offense Category** – VIOLENT CRIME, PROPERTY CRIME, ALL OTHER
- **Offense Sub Category** – Granulare Deliktarten
- **Precinct** – 5 Polizeibezirke
- **Beat** – Untereinheiten der Precincts
- **Neighborhood** – 70+ Stadtteile

### KPI-Karten
Drei Kennzahlen direkt unterhalb des Headers:
![KPI Karten](screenshots/header_kpi.png)
&nbsp;

| Karte | Inhalt |
|-------|--------|
| Violent Crime | Absolute Anzahl Gewaltdelikte |
| Property Crime | Absolute Anzahl Eigentumsdelikte |
| All Other | Absolute Anzahl sonstiger Delikte |

### Offense Totals Tabelle

Gruppierte Tabelle nach Kategorie → Subkategorie mit einer Spalte pro ausgewähltem Jahr. Neuestes Jahr wird orange hervorgehoben.
![KPI Karten](screenshots/offense_totals.png)

### Crime Hotspot-Karte
Interaktive Folium-Karte mit Choropleth-Darstellung nach Precinct (GeoJSON via GitHub). Fallback: Neighborhood-Karte mit skalierten Kreisen.
![KPI Karten](screenshots/map.png)


### Monthly Trend
Zeitreihen-Chart mit einer Linie pro Jahr, Datenpunkten mit Werten direkt auf der Linie, automatischem Ausblenden überlappender Labels.
![KPI Karten](screenshots/monatlicher_trend.png)


---

## Vergleich: Original vs. Nachbau

| Komponente | Original (Tableau) | Nachbau (Streamlit) |
|---|---|---|
| KPI-Karten | ✅ | ✅ |
| 6-Filter-System | ✅ | ✅ |
| Offense Totals Tabelle | ✅ | ✅ |
| Mehrjahres-Vergleich | ✅ | ✅ |
| Choropleth-Karte | ✅ | ✅ |
| Monthly Trend | ✅ | ✅ |
| Lizenzkosten | 💰 | ✅ kostenlos |
| Reproduzierbarkeit | ❌ | ✅ |

---

## Bekannte Einschränkungen

- **REDACTED-Koordinaten:** ~15% der Daten haben keine GPS-Koordinaten (Datenschutz)
- **Systemwechsel 2019:** RMS → NIBRS kann Brüche in Zeitreihen verursachen
- **Keine Echtzeit-Updates:** Manueller CSV-Download notwendig
- **GeoJSON:** Offizielle Seattle Precinct-Grenzen waren nicht über die öffentliche API abrufbar

---

## Dokumentation

Eine ausführliche Dokumentation aller Schritte (Datenaufbereitung, Architektur, Visualisierungen, kritische Reflexion) ist im [Quarto Handout](handout.qmd) verfügbar.

---

## Quellen

- [Seattle Open Data Portal](https://data.seattle.gov)
- [SPD Crime Dashboard (Original)](https://www.seattle.gov/police/information-and-data/data/crime-dashboard)
- [NIBRS Dokumentation](https://ucr.fbi.gov/nibrs/2019/resource-pages/nibrs_techspec-2019_f.pdf)
- [DuckDB Dokumentation](https://duckdb.org/docs)
- [Streamlit Dokumentation](https://docs.streamlit.io)

---

*Erstellt im Rahmen des Moduls „Datenaufbereitung und Visualisierung" an der THWS*
