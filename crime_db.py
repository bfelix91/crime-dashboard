# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
#------------------------------------------------------------------------------
# Vorbereitung
#------------------------------------------------------------------------------

import duckdb
import os

# Pfad zum Projektordner
os.chdir('/Users/felix/Documents/Felix/Studium/4. Semester/Projekt Crime Dashboard')

# Einlesen der CSV in die DuckDB
conn = duckdb.connect("seattle_crime.db")

conn.execute("""
    CREATE TABLE IF NOT EXISTS crimes AS 
    SELECT * FROM read_csv_auto('Crime_Data__2008-Present.csv')
""")

# Anzahl Zeilen
print(conn.execute("SELECT COUNT(*) FROM crimes").fetchone()[0])

# Spaltennamen anzeigen
print(conn.execute("DESCRIBE crimes").df())

# Erste 5 Zeilen
conn.execute("SELECT * FROM crimes LIMIT 5").df()


#------------------------------------------------------------------------------
# Datenaufbereitung
#------------------------------------------------------------------------------



# Datentypen und fehlende Werte prüfen
print(conn.execute("""
    SELECT 
        COUNT(*) as gesamt,
        COUNT(Latitude) as mit_koordinaten,
        COUNT(Neighborhood) as mit_neighborhood,
        MIN("Offense Date") as aeltester_eintrag,
        MAX("Offense Date") as neuester_eintrag
    FROM crimes
""").df())

# Top 10 häufigste Delikte
conn.execute("""
    SELECT "Offense Category", COUNT(*) as anzahl
    FROM crimes
    GROUP BY "Offense Category"
    ORDER BY anzahl DESC
    LIMIT 10
""").df()


conn.execute("""
    CREATE TABLE IF NOT EXISTS crimes_clean AS
    SELECT *,
        strptime("Offense Date", '%Y %b %d %I:%M:%S %p') AS offense_date_parsed,
        EXTRACT(hour FROM strptime("Report DateTime", '%Y %b %d %I:%M:%S %p')) AS stunde,
        DAYOFWEEK(strptime("Report DateTime", '%Y %b %d %I:%M:%S %p')) AS wochentag,
        YEAR(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS jahr,
        MONTH(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) AS monat
    FROM crimes
    WHERE 
        YEAR(strptime("Offense Date", '%Y %b %d %I:%M:%S %p')) >= 2008
        AND Latitude IS NOT NULL
        AND Longitude IS NOT NULL
        AND Latitude != 'REDACTED'
        AND Longitude != 'REDACTED'
        AND Latitude != '0'
        AND Longitude != '0'
""")

print(conn.execute("SELECT COUNT(*) FROM crimes_clean").fetchone()[0])

# Verteilung über die Jahre – gibt es Ausreißer?
conn.execute("""
    SELECT jahr, COUNT(*) as anzahl
    FROM crimes_clean
    GROUP BY jahr
    ORDER BY jahr
""").df()

# Wie viele REDACTED wurden entfernt?
print(conn.execute("""
    SELECT COUNT(*) FROM crimes 
    WHERE Latitude = 'REDACTED'
""").fetchone()[0])