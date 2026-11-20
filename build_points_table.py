"""
Rakentaa pelaaja × pelipäivä -pistetaulukon Excel-muodossa.
"""

import json
import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_FILE = os.path.join(DATA_DIR, "player_points_by_gw.xlsx")

# ── 1. Lataa bootstrap-static ──────────────────────────────────────────────
print("Ladataan bootstrap-static...")
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)

pos_map  = {t["id"]: t["singular_name_short"] for t in bs["element_types"]}
team_map = {t["id"]: t["short_name"]          for t in bs["teams"]}

players = {}
for p in bs["elements"]:
    players[p["id"]] = {
        "name":     p["web_name"],
        "full":     f"{p['first_name']} {p['second_name']}",
        "team":     team_map.get(p["team"], "?"),
        "position": pos_map.get(p["element_type"], "?"),
        "total":    p["total_points"],
    }

# ── 2. Lataa live-gameweek data ────────────────────────────────────────────
print("Ladataan live-gameweek data...")
with open(os.path.join(DATA_DIR, "live_gameweeks.json"), encoding="utf-8") as f:
    live = json.load(f)

gameweeks = sorted(live.keys(), key=lambda x: int(x))
print(f"   Pelipäiviä: {len(gameweeks)}")

# ── 3. Rakenna pistematriisi ───────────────────────────────────────────────
print("Rakennetaan pistematriisi...")
rows = []
for pid, pdata in players.items():
    row = {
        "Nimi":      pdata["name"],
        "Täysinimi": pdata["full"],
        "Joukkue":   pdata["team"],
        "Asema":     pdata["position"],
    }
    season_total = 0
    for gw in gameweeks:
        pts = 0
        for elem in live[gw]["elements"]:
            if elem["id"] == pid:
                pts = elem["stats"]["total_points"]
                break
        col_name = f"GW{int(gw):02d}"
        row[col_name] = pts
        season_total += pts
    row["Yhteensä"] = season_total
    rows.append(row)

df = pd.DataFrame(rows)

# Järjestä: asema, joukkue, nimi
pos_order = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
df["_pos_order"] = df["Asema"].map(pos_order).fillna(5)
df = df.sort_values(["Yhteensä"], ascending=False).drop(columns=["_pos_order"])
df = df.reset_index(drop=True)

print(f"   Pelaajia: {len(df)}")

# ── 4. Tallenna Excel ja muotoile ──────────────────────────────────────────
print("Tallennetaan Exceliin...")
gw_cols = [f"GW{int(g):02d}" for g in gameweeks]
col_order = ["Nimi", "Täysinimi", "Joukkue", "Asema"] + gw_cols + ["Yhteensä"]
df = df[col_order]
df.to_excel(OUTPUT_FILE, index=False, sheet_name="Pisteet")

# ── 5. Tyyli ───────────────────────────────────────────────────────────────
print("Muotoillaan...")
wb = load_workbook(OUTPUT_FILE)
ws = wb.active

HEADER_FILL   = PatternFill("solid", fgColor="1F3864")   # tummansininen
GW_FILL       = PatternFill("solid", fgColor="2E75B6")   # sininen
TOTAL_FILL    = PatternFill("solid", fgColor="375623")   # tummanvihreä
ALT_FILL      = PatternFill("solid", fgColor="D9E1F2")   # vaalea sininen
WHITE_FILL    = PatternFill("solid", fgColor="FFFFFF")
ZERO_FONT     = Font(color="BFBFBF")
HEADER_FONT   = Font(bold=True, color="FFFFFF", size=10)
TOTAL_FONT    = Font(bold=True, color="FFFFFF", size=10)
CELL_FONT     = Font(size=9)
BOLD_FONT     = Font(bold=True, size=9)

thin = Side(style="thin", color="B0B0B0")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

num_cols = len(col_order)

# Otsikkorivi
for col_idx, col_name in enumerate(col_order, 1):
    cell = ws.cell(row=1, column=col_idx)
    if col_name == "Yhteensä":
        cell.fill = TOTAL_FILL
        cell.font = TOTAL_FONT
    elif col_name.startswith("GW"):
        cell.fill = GW_FILL
        cell.font = HEADER_FONT
    else:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border

# Datarivi
for row_idx in range(2, len(df) + 2):
    is_alt = (row_idx % 2 == 0)
    for col_idx in range(1, num_cols + 1):
        cell = ws.cell(row=row_idx, column=col_idx)
        col_name = col_order[col_idx - 1]
        val = cell.value

        if col_name == "Yhteensä":
            cell.fill = PatternFill("solid", fgColor="E2EFDA")
            cell.font = BOLD_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif col_name.startswith("GW"):
            cell.fill = ALT_FILL if is_alt else WHITE_FILL
            if val == 0:
                cell.font = ZERO_FONT
            else:
                cell.font = CELL_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.fill = ALT_FILL if is_alt else WHITE_FILL
            cell.font = BOLD_FONT if col_name == "Nimi" else CELL_FONT
            cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = border

# Sarakeleveydet
ws.column_dimensions["A"].width = 14  # Nimi
ws.column_dimensions["B"].width = 22  # Täysinimi
ws.column_dimensions["C"].width = 8   # Joukkue
ws.column_dimensions["D"].width = 7   # Asema
for i, col_name in enumerate(gw_cols, 5):
    ws.column_dimensions[get_column_letter(i)].width = 5.5
ws.column_dimensions[get_column_letter(num_cols)].width = 10  # Yhteensä

# Jäädytä ensimmäinen rivi + 4 vasenta saraketta
ws.freeze_panes = "E2"

# Rivikorot
ws.row_dimensions[1].height = 30
for row_idx in range(2, len(df) + 2):
    ws.row_dimensions[row_idx].height = 16

wb.save(OUTPUT_FILE)
print(f"\nValmis! Tiedosto tallennettu:")
print(f"  {OUTPUT_FILE}")
size = os.path.getsize(OUTPUT_FILE) / 1024
print(f"  Koko: {size:.1f} KB")
print(f"  Rivejä: {len(df)} pelaajaa | Sarakkeita: {num_cols} (4 info + {len(gw_cols)} GW + 1 total)")
