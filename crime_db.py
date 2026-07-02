import duckdb
import pandas as pd
import requests
import os
from io import BytesIO

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
PARQUET_URL = "https://raw.githubusercontent.com/bfelix91/crime-dashboard/main/crimes_historical.parquet"
API_URL = "https://data.seattle.gov/resource/tazs-3rd5.json"
DB_PATH = "seattle_crime.db"

# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def clean_and_enrich(df):
    """Bereinigung und neue Spalten berechnen"""
    # Alle Spaltennamen zu lowercase
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Koordinaten bereinigen
    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df = df[~df[col].isin(["REDACTED", "0", "", None])]
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])

    # Datum parsen – API nutzt offense_date und report_date_time
    offense_col = "offense_date" if "offense_date" in df.columns else "offense_date_time"
    report_col  = "report_date_time" if "report_date_time" in df.columns else "report_datetime"

    df["offense_date_parsed"] = pd.to_datetime(df[offense_col], errors="coerce")
    df["report_dt_parsed"]    = pd.to_datetime(df[report_col],  errors="coerce")

    # Dirty Dates filtern
    df = df[df["offense_date_parsed"].dt.year >= 2008]

    # Neue Spalten
    df["stunde"]    = df["report_dt_parsed"].dt.hour
    df["wochentag"] = df["report_dt_parsed"].dt.dayofweek
    df["jahr"]      = df["offense_date_parsed"].dt.year
    df["monat"]     = df["offense_date_parsed"].dt.month

    return df


def load_historical():
    """Historische Daten 2008-2023 von GitHub laden"""
    print("Lade historische Daten von GitHub...")
    response = requests.get(PARQUET_URL, timeout=60)
    response.raise_for_status()
    df = pd.read_parquet(BytesIO(response.content))
    print(f"  → {len(df):,} Zeilen geladen (2008–2023)")
    return df


def load_recent():
    """Aktuelle Daten 2024–heute von der Socrata API laden"""
    print("Lade aktuelle Daten von der Seattle API...")
    all_rows = []
    offset = 0
    limit = 50000

    while True:
        params = {
            "$limit": limit,
            "$offset": offset,
            "$where": "offense_date >= '2024-01-01T00:00:00'",
            "$order": "offense_date ASC"
        }
        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        all_rows.extend(batch)
        offset += limit
        print(f"  → {len(all_rows):,} Zeilen geladen...")

        if len(batch) < limit:
            break

    df = pd.DataFrame(all_rows)
    print(f"  → Insgesamt {len(df):,} aktuelle Zeilen (2024–heute)")
    return df


# ─────────────────────────────────────────────
# HAUPTPROZESS
# ─────────────────────────────────────────────
def build_database():
    print("=== Datenbank aufbauen ===")

    # 1. Daten laden
    df_hist   = load_historical()
    df_recent = load_recent()

    # 2. Aktuelle Daten bereinigen
    df_recent = clean_and_enrich(df_recent)

    # Spaltennamen angleichen
    df_recent.columns = [c.lower().replace(" ", "_") for c in df_recent.columns]
    df_hist.columns   = [c.lower().replace(" ", "_") for c in df_hist.columns]

    # 3. Zusammenführen
    df_all = pd.concat([df_hist, df_recent], ignore_index=True)
    print(f"\nGesamt: {len(df_all):,} Zeilen (2008–heute)")

    # 4. In DuckDB speichern
    conn = duckdb.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS crimes_clean")
    conn.execute("CREATE TABLE crimes_clean AS SELECT * FROM df_all")
    conn.close()

    print(f"Datenbank gespeichert: {DB_PATH}")
    print("=== Fertig! ===")


if __name__ == "__main__":
    build_database()