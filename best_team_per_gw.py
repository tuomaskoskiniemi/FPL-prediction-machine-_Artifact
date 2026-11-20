"""
FPL Paras Joukkue Per Kierros — Integer Linear Programming
==========================================================
Löytää optimaalisen 15 pelaajan joukkueen jokaiselle annetulle kierrokselle.

Säännöt:
  - Joukkue: 2 GKP, 5 DEF, 5 MID, 3 FWD
  - Budjetti: 100.0 M (arvo * 0.1 M)
  - Max 3 pelaajaa samasta seurasta
  - Aloituskokoonpano: 1 GKP + 10 kenttäpelaajaa, validi muodostelma
    (min DEF 3, min MID 2, min FWD 1)
  - Kapteeni: kaksinkertaistaa pisteet
  - Optimoi: aloituskokoonpanon pisteet + kapteenibonus
"""

import json, os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pulp
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
warnings.filterwarnings("ignore")

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_XLS = os.path.join(DATA_DIR, "best_team_per_gw.xlsx")

TARGET_GWS = [5, 10, 15, 20, 25, 30, 35]
BUDGET     = 1000   # 100.0M in 0.1M units
POSITIONS  = ["GKP", "DEF", "MID", "FWD"]

POS_COLORS = {"GKP": "#FFD700", "DEF": "#2196F3", "MID": "#4CAF50", "FWD": "#FF5722"}
POS_SQUAD  = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}
POS_MIN_XI = {"GKP": 1, "DEF": 3, "MID": 2, "FWD": 1}

print("=" * 70)
print("FPL — Paras Joukkue Per Kierros (ILP-optimointi)")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════
# 1. LATAA DATA
# ═══════════════════════════════════════════════════════════════════════════
print("\n[1/4] Ladataan data...")
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)
with open(os.path.join(DATA_DIR, "live_gameweeks.json"), encoding="utf-8") as f:
    live_gws = json.load(f)
with open(os.path.join(DATA_DIR, "player_details.json"), encoding="utf-8") as f:
    player_details = json.load(f)

pos_map  = {t["id"]: t["singular_name_short"] for t in bs["element_types"]}
team_map = {t["id"]: t["short_name"]          for t in bs["teams"]}

# Pelaajan arvo kullakin kierroksella: rakenna aikajana historiasta
print("   Rakennetaan arvotaulukko...")
player_values = {}   # pid -> {gw: value}
for pid_str, detail in player_details.items():
    pid = int(pid_str)
    gw_val = {}
    for h in detail.get("history", []):
        gw_val[h["round"]] = h["value"]
    player_values[pid] = gw_val

def get_value_at_gw(pid, gw):
    """Pelaajan arvo tietyllä kierroksella (lähin aiempi arvo tai bootstrap)."""
    vals = player_values.get(pid, {})
    if gw in vals:
        return vals[gw]
    # Etsi lähin aiempi
    earlier = [v for k, v in vals.items() if k < gw]
    if earlier:
        return earlier[-1]
    # Etsi lähin myöhempi
    later = [v for k, v in vals.items() if k > gw]
    if later:
        return later[0]
    # Fallback: bootstrap now_cost
    for p in bs["elements"]:
        if p["id"] == pid:
            return p["now_cost"]
    return 45  # minimi

# Pelaajametatiedot
players_meta = {}
for p in bs["elements"]:
    players_meta[p["id"]] = {
        "name":     p["web_name"],
        "fullname": f"{p['first_name']} {p['second_name']}",
        "team":     team_map.get(p["team"], "?"),
        "team_id":  p["team"],
        "position": pos_map.get(p["element_type"], "?"),
    }

print(f"   Pelaajia: {len(players_meta)}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. ILP-OPTIMOINTI PER KIERROS
# ═══════════════════════════════════════════════════════════════════════════

def solve_best_team(gw_str, gw_num):
    """
    Ratkaisee parhaan joukkueen ILP:llä.
    Muuttujat:
      x[i] ∈ {0,1} — pelaaja i joukkueessa
      y[i] ∈ {0,1} — pelaaja i aloittaa
      c[i] ∈ {0,1} — pelaaja i on kapteeni
    Tavoite: max Σ(y[i] + c[i]) * pts[i]
    """
    gw_data = live_gws.get(gw_str, {})
    elem_pts = {e["id"]: e["stats"]["total_points"]
                for e in gw_data.get("elements", [])}

    # Rakenna pelaajalistaus
    players = []
    for pid, meta in players_meta.items():
        pts = elem_pts.get(pid, 0)
        val = get_value_at_gw(pid, gw_num)
        players.append({
            "id":       pid,
            "name":     meta["name"],
            "fullname": meta["fullname"],
            "team":     meta["team"],
            "team_id":  meta["team_id"],
            "position": meta["position"],
            "points":   pts,
            "value":    val,
        })

    n   = len(players)
    pos = [p["position"] for p in players]
    pts = [p["points"]   for p in players]
    val = [p["value"]    for p in players]
    tid = [p["team_id"]  for p in players]

    prob = pulp.LpProblem(f"FPL_GW{gw_num}", pulp.LpMaximize)

    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]
    y = [pulp.LpVariable(f"y_{i}", cat="Binary") for i in range(n)]
    c = [pulp.LpVariable(f"c_{i}", cat="Binary") for i in range(n)]

    # Tavoitefunktio: aloituspelaajien pisteet + kapteenibonus
    prob += pulp.lpSum((y[i] + c[i]) * pts[i] for i in range(n))

    # Joukkueen kokoonpano
    for pos_name, count in POS_SQUAD.items():
        prob += pulp.lpSum(x[i] for i in range(n) if pos[i] == pos_name) == count

    # Budjetti
    prob += pulp.lpSum(x[i] * val[i] for i in range(n)) <= BUDGET

    # Max 3 pelaajaa samasta seurasta
    for team_id in set(tid):
        prob += pulp.lpSum(x[i] for i in range(n) if tid[i] == team_id) <= 3

    # Aloituskokoonpano: 11 pelaajaa
    prob += pulp.lpSum(y[i] for i in range(n)) == 11

    # Muodostelmarajoitukset
    prob += pulp.lpSum(y[i] for i in range(n) if pos[i] == "GKP") == 1
    prob += pulp.lpSum(y[i] for i in range(n) if pos[i] == "DEF") >= 3
    prob += pulp.lpSum(y[i] for i in range(n) if pos[i] == "MID") >= 2
    prob += pulp.lpSum(y[i] for i in range(n) if pos[i] == "FWD") >= 1

    # Kapteeni: yksi aloittava pelaaja
    prob += pulp.lpSum(c[i] for i in range(n)) == 1

    # Hierarkia: ei voi aloittaa ellei joukkueessa, ei voi olla kapteeni ellei aloita
    for i in range(n):
        prob += y[i] <= x[i]
        prob += c[i] <= y[i]

    # Ratkaise (hiljaa)
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=30)
    status = prob.solve(solver)

    if pulp.LpStatus[prob.status] not in ("Optimal", "Feasible"):
        print(f"   GW{gw_num}: Ratkaisua ei löydetty! Status: {pulp.LpStatus[prob.status]}")
        return None

    # Kerää tulokset
    squad   = []
    starters = []
    bench   = []
    captain = None

    for i in range(n):
        in_squad  = pulp.value(x[i]) > 0.5
        is_start  = pulp.value(y[i]) > 0.5
        is_cap    = pulp.value(c[i]) > 0.5

        if in_squad:
            p = players[i].copy()
            p["starter"] = is_start
            p["captain"] = is_cap
            squad.append(p)
            if is_start:
                starters.append(p)
            else:
                bench.append(p)
            if is_cap:
                captain = p

    # Laske pisteet
    xi_points  = sum(p["points"] for p in starters)
    cap_bonus  = captain["points"] if captain else 0
    total_pts  = xi_points + cap_bonus
    budget_used = sum(p["value"] for p in squad) / 10.0

    # Muodostelma
    def_count = sum(1 for p in starters if p["position"] == "DEF")
    mid_count = sum(1 for p in starters if p["position"] == "MID")
    fwd_count = sum(1 for p in starters if p["position"] == "FWD")
    formation = f"1-{def_count}-{mid_count}-{fwd_count}"

    return {
        "gw":        gw_num,
        "squad":     squad,
        "starters":  starters,
        "bench":     bench,
        "captain":   captain,
        "formation": formation,
        "xi_pts":    xi_points,
        "cap_bonus": cap_bonus,
        "total_pts": total_pts,
        "budget":    budget_used,
    }


print("\n[2/4] Ratkaistaan optimaaliset joukkueet ILP:llä...")
results = {}
for gw in TARGET_GWS:
    gw_str = str(gw)
    if gw_str not in live_gws:
        print(f"   GW{gw}: data puuttuu, ohitetaan")
        continue
    print(f"   GW{gw}: ratkaistaan...", end="", flush=True)
    res = solve_best_team(gw_str, gw)
    if res:
        results[gw] = res
        cap_name = res["captain"]["name"] if res["captain"] else "?"
        print(f" {res['total_pts']} pts | {res['formation']} | "
              f"{res['budget']:.1f}M | (C) {cap_name}")
    else:
        print(" EPÄONNISTUI")

# ═══════════════════════════════════════════════════════════════════════════
# 3. VISUALISOINNIT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[3/4] Piirretään kuvaajat...")

def draw_team(ax, starters, bench, captain, gw, total_pts, formation, budget):
    """Piirrä jalkapallokenttä joukkueineen."""
    ax.set_facecolor("#2d5a27")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 130)
    ax.axis("off")

    # Kentän viivat
    ax.add_patch(plt.Rectangle((5, 5), 90, 120, fill=False,
                                edgecolor="white", linewidth=2))
    ax.add_patch(plt.Rectangle((25, 5), 50, 22, fill=False,
                                edgecolor="white", linewidth=1.2, alpha=0.7))
    ax.add_patch(plt.Rectangle((25, 103), 50, 22, fill=False,
                                edgecolor="white", linewidth=1.2, alpha=0.7))
    circle = plt.Circle((50, 65), 15, fill=False, edgecolor="white",
                         linewidth=1.2, alpha=0.7)
    ax.add_patch(circle)
    ax.plot([5, 95], [65, 65], "white", linewidth=1.2, alpha=0.7)

    ax.set_title(f"GW{gw} — {formation}  |  {total_pts} pistettä  |  "
                 f"{budget:.1f}M / 100.0M käytetty",
                 fontsize=10, fontweight="bold", color="white",
                 pad=6, backgroundcolor="#1a3a15")

    # Pelaajien sijoittelu kentälle
    # Järjestä aloittajat asemittain
    gkp_s = [p for p in starters if p["position"] == "GKP"]
    def_s = [p for p in starters if p["position"] == "DEF"]
    mid_s = [p for p in starters if p["position"] == "MID"]
    fwd_s = [p for p in starters if p["position"] == "FWD"]

    rows = [
        (gkp_s, 12),
        (def_s, 35),
        (mid_s, 65),
        (fwd_s, 95),
    ]

    for players_row, y_pos in rows:
        if not players_row:
            continue
        n = len(players_row)
        xs = np.linspace(15, 85, n)
        for x_pos, p in zip(xs, sorted(players_row, key=lambda x: -x["points"])):
            is_cap = p.get("captain", False)
            color  = POS_COLORS.get(p["position"], "gray")

            # Pelaajalaatikko
            box = mpatches.FancyBboxPatch((x_pos - 7, y_pos - 5), 14, 10,
                                          boxstyle="round,pad=0.5",
                                          facecolor=color, edgecolor="white",
                                          linewidth=1.5, alpha=0.92)
            ax.add_patch(box)

            # Kapteeni-merkki
            if is_cap:
                cap_circle = plt.Circle((x_pos + 5.5, y_pos + 3.5), 2.5,
                                         color="#FFD700", zorder=5)
                ax.add_patch(cap_circle)
                ax.text(x_pos + 5.5, y_pos + 3.5, "C",
                        ha="center", va="center", fontsize=5.5,
                        fontweight="bold", color="black", zorder=6)

            # Nimi
            name = p["name"][:10]
            ax.text(x_pos, y_pos + 1.5, name, ha="center", va="center",
                    fontsize=7, fontweight="bold", color="white",
                    clip_on=True)
            # Pisteet
            pts_txt = f"{p['points']}{'×2' if is_cap else ''} pts"
            ax.text(x_pos, y_pos - 2.5, pts_txt, ha="center", va="center",
                    fontsize=6.5, color="white", alpha=0.95)

    # Vaihtopelaajat
    bench_sorted = sorted(bench, key=lambda p: POSITIONS.index(p["position"]))
    ax.text(50, 0, "Vaihtopelaajat:", ha="center", va="bottom",
            fontsize=7, color="#CCCCCC", style="italic")

    bench_xs = np.linspace(13, 87, 4)
    for x_b, p in zip(bench_xs, bench_sorted):
        color = POS_COLORS.get(p["position"], "gray")
        box = mpatches.FancyBboxPatch((x_b - 6, -12), 12, 8,
                                      boxstyle="round,pad=0.5",
                                      facecolor=color, edgecolor="white",
                                      linewidth=1, alpha=0.65)
        ax.add_patch(box)
        ax.text(x_b, -7.5, p["name"][:9], ha="center", va="center",
                fontsize=6, color="white", fontweight="bold")
        ax.text(x_b, -10.5, f"{p['points']} pts", ha="center", va="center",
                fontsize=5.5, color="white", alpha=0.85)

    ax.set_ylim(-15, 133)


# Laske grid
n_results = len(results)
cols = min(3, n_results)
rows_g = (n_results + cols - 1) // cols

fig, axes = plt.subplots(rows_g, cols, figsize=(cols * 8.5, rows_g * 13))
fig.patch.set_facecolor("#111111")
fig.suptitle("FPL — Optimaaliset joukkueet valituilla kierroksilla\n"
             "(ILP-optimointi, budjetti 100M, max 3/seura)",
             fontsize=14, fontweight="bold", color="white", y=0.995)

axes_flat = axes.flatten() if n_results > 1 else [axes]

for idx, (gw, res) in enumerate(sorted(results.items())):
    draw_team(axes_flat[idx],
              res["starters"], res["bench"], res["captain"],
              gw, res["total_pts"], res["formation"], res["budget"])

# Piilota tyhjät akselit
for idx in range(len(results), len(axes_flat)):
    axes_flat[idx].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.995])
img_path = os.path.join(DATA_DIR, "best_teams_field_view.png")
fig.savefig(img_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)
print(f"   Kenttäkuva tallennettu")

# ── Yhteenvetokuva: pisteet per kierros ────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(12, 5))
fig2.suptitle("Optimaalinen pistesaalis kierroksittain", fontsize=13, fontweight="bold")

gw_nums   = sorted(results.keys())
xi_pts    = [results[g]["xi_pts"]    for g in gw_nums]
cap_bonus = [results[g]["cap_bonus"] for g in gw_nums]
budgets   = [results[g]["budget"]    for g in gw_nums]
formations = [results[g]["formation"] for g in gw_nums]

x_pos = np.arange(len(gw_nums))
bars1 = ax2.bar(x_pos, xi_pts,    color="#2196F3", label="Aloituskokoonpano", alpha=0.85)
bars2 = ax2.bar(x_pos, cap_bonus, bottom=xi_pts, color="#FFD700", label="Kapteenibonus", alpha=0.9)

for i, (g, total, form, budg) in enumerate(zip(gw_nums,
        [results[g]["total_pts"] for g in gw_nums], formations, budgets)):
    ax2.text(i, total + 0.5, f"{total} pts", ha="center", fontsize=9, fontweight="bold")
    ax2.text(i, -4, f"{form}\n{budg:.1f}M", ha="center", fontsize=7, color="#555555")

ax2.set_xticks(x_pos)
ax2.set_xticklabels([f"GW{g}" for g in gw_nums], fontsize=10)
ax2.set_ylabel("Pisteet")
ax2.set_ylim(-8, max(results[g]["total_pts"] for g in gw_nums) + 8)
ax2.legend(fontsize=9)
ax2.grid(axis="y", alpha=0.3)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout()
img2_path = os.path.join(DATA_DIR, "best_teams_summary_chart.png")
fig2.savefig(img2_path, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"   Yhteenvetokuva tallennettu")

# ═══════════════════════════════════════════════════════════════════════════
# 4. EXCEL-RAPORTTI
# ═══════════════════════════════════════════════════════════════════════════
print("\n[4/4] Kirjoitetaan Excel-raportti...")

wb = Workbook()
thin = Side(style="thin", color="BBBBBB")
brd  = Border(left=thin, right=thin, top=thin, bottom=thin)
center_a = Alignment(horizontal="center", vertical="center")
left_a   = Alignment(horizontal="left",   vertical="center")

DARK  = PatternFill("solid", fgColor="1F3864")
MED   = PatternFill("solid", fgColor="2E75B6")
ALT   = PatternFill("solid", fgColor="D9E1F2")
GOLD  = PatternFill("solid", fgColor="FFD700")
GREEN = PatternFill("solid", fgColor="C6EFCE")
RED   = PatternFill("solid", fgColor="FFC7CE")
BENCH = PatternFill("solid", fgColor="F5F5F5")

def hdr(ws, r, c, v, fill=MED, fc="FFFFFF", sz=10, bold=True, al=center_a):
    cell = ws.cell(row=r, column=c, value=v)
    cell.fill = fill; cell.font = Font(bold=bold, color=fc, size=sz)
    cell.alignment = al; cell.border = brd
    return cell

def dat(ws, r, c, v, bold=False, fmt=None, fill=None, al=center_a):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = Font(bold=bold, size=9)
    cell.alignment = al; cell.border = brd
    if fill: cell.fill = fill
    if fmt:  cell.number_format = fmt
    return cell

# ── Sheet 1: Yhteenveto ───────────────────────────────────────────────────
ws_sum = wb.active
ws_sum.title = "Yhteenveto"

ws_sum.merge_cells("A1:J1")
ws_sum["A1"].value = "FPL — Optimaalinen joukkue per kierros (ILP, 100M budjetti, max 3/seura)"
ws_sum["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws_sum["A1"].fill = DARK; ws_sum["A1"].alignment = center_a
ws_sum.row_dimensions[1].height = 28

# Yhteenvetotaulukko
hdrs_s = ["Kierros", "Muodostelma", "XI Pisteet", "Kapteeni", "Cap. Bonus",
          "Yhteensä", "Budjetti (M)", "TOP Pelaaja", "Pisteet", "Joukkue"]
for j, h in enumerate(hdrs_s, 1):
    hdr(ws_sum, 2, j, h)

for i, gw in enumerate(sorted(results.keys())):
    res  = results[gw]
    cap  = res["captain"]
    top  = max(res["starters"], key=lambda p: p["points"])
    row  = 3 + i
    fill_r = ALT if i % 2 == 0 else None

    vals = [f"GW {gw}", res["formation"], res["xi_pts"],
            cap["name"] if cap else "?", res["cap_bonus"],
            res["total_pts"], res["budget"],
            top["name"], top["points"], top["team"]]
    fmts = [None]*7 + [None, None, None]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        f = GOLD if j == 4 else fill_r
        dat(ws_sum, row, j, v, fmt=fmt, fill=f,
            bold=(j == 6),
            al=left_a if j in (2, 4, 8, 10) else center_a)

for j, w in enumerate([8, 12, 12, 16, 12, 12, 14, 16, 10, 10], 1):
    ws_sum.column_dimensions[get_column_letter(j)].width = w

# Kuvaajat yhteenveto-sheetille
for img_p, anchor in [(img2_path, "A12"), (img_path, "A22")]:
    if os.path.exists(img_p):
        img_obj = XLImage(img_p)
        img_obj.width = 900
        img_obj.height = int(img_obj.width * (0.42 if "summary" in img_p else 1.15))
        ws_sum.add_image(img_obj, anchor)

# ── Sheet per kierros ─────────────────────────────────────────────────────
ROLE_HEADERS = ["Rooli", "Nimi", "Joukkue", "Asema", "Pisteet",
                "Arvo (M)", "Bonus?", "Huomio"]

for gw in sorted(results.keys()):
    res = results[gw]
    ws  = wb.create_sheet(f"GW{gw}")

    # Otsikko
    ws.merge_cells(f"A1:{get_column_letter(len(ROLE_HEADERS))}1")
    ws["A1"].value = (f"GW {gw} — Optimaalinen joukkue  |  "
                      f"{res['formation']}  |  {res['total_pts']} pts  |  "
                      f"{res['budget']:.1f}M / 100.0M")
    ws["A1"].font = Font(bold=True, size=12, color="FFFFFF")
    ws["A1"].fill = DARK; ws["A1"].alignment = center_a
    ws.row_dimensions[1].height = 25

    for j, h in enumerate(ROLE_HEADERS, 1):
        hdr(ws, 2, j, h)

    # Aloittajat asemittain
    row_idx = 3
    pos_order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
    starters_sorted = sorted(res["starters"],
                              key=lambda p: (pos_order.get(p["position"], 9), -p["points"]))

    current_pos = None
    for p in starters_sorted:
        if p["position"] != current_pos:
            current_pos = p["position"]
            # Asemaotsikko
            ws.merge_cells(f"A{row_idx}:{get_column_letter(len(ROLE_HEADERS))}{row_idx}")
            pos_fill = PatternFill("solid",
                                   fgColor=POS_COLORS.get(current_pos, "888888").lstrip("#"))
            ws[f"A{row_idx}"].value = current_pos
            ws[f"A{row_idx}"].font = Font(bold=True, size=10, color="FFFFFF")
            ws[f"A{row_idx}"].fill = pos_fill
            ws[f"A{row_idx}"].alignment = center_a
            row_idx += 1

        is_cap = p.get("captain", False)
        role   = "(C) KAPTEENI" if is_cap else "Aloittaja"
        note   = f"Kaksinkertaiset pisteet: {p['points']}×2 = {p['points']*2}" if is_cap else ""
        fill_r = GOLD if is_cap else None

        vals = [role, p["name"], p["team"], p["position"],
                p["points"], p["value"] / 10.0, "Kyllä" if p["points"] > 0 else "Ei",
                note]
        for j, v in enumerate(vals, 1):
            dat(ws, row_idx, j, v, bold=is_cap, fill=fill_r,
                fmt="0.0" if j == 6 else None,
                al=left_a if j in (2, 3, 8) else center_a)
        row_idx += 1

    # Vaihtopelaajat
    row_idx += 1
    ws.merge_cells(f"A{row_idx}:{get_column_letter(len(ROLE_HEADERS))}{row_idx}")
    ws[f"A{row_idx}"].value = "VAIHTOPELAAJAT (penkki)"
    ws[f"A{row_idx}"].font = Font(bold=True, size=10, color="555555")
    ws[f"A{row_idx}"].fill = PatternFill("solid", fgColor="DDDDDD")
    ws[f"A{row_idx}"].alignment = center_a
    row_idx += 1

    bench_sorted = sorted(res["bench"],
                          key=lambda p: (pos_order.get(p["position"], 9), -p["points"]))
    for p in bench_sorted:
        vals = ["Penkki", p["name"], p["team"], p["position"],
                p["points"], p["value"] / 10.0, "", ""]
        for j, v in enumerate(vals, 1):
            dat(ws, row_idx, j, v, fill=BENCH,
                fmt="0.0" if j == 6 else None,
                al=left_a if j in (2, 3, 8) else center_a)
        row_idx += 1

    # Tilastot
    row_idx += 1
    stats_data = [
        ("Aloituskokoonpano pisteet:", res["xi_pts"]),
        ("Kapteenibonus (+):", res["cap_bonus"]),
        ("KOKONAISPISTEET:", res["total_pts"]),
        ("Budjetti käytetty (M):", f"{res['budget']:.1f}"),
        ("Jäljellä (M):", f"{100.0 - res['budget']:.1f}"),
        ("Muodostelma:", res["formation"]),
    ]
    for label, value in stats_data:
        ws.cell(row=row_idx, column=1, value=label).font = Font(bold=True, size=9)
        ws.cell(row=row_idx, column=2, value=value).font = Font(bold=True, size=9,
            color="1F3864" if "KOKONAIS" in label else "000000")
        row_idx += 1

    for j, w in enumerate([14, 18, 10, 8, 10, 10, 8, 40], 1):
        ws.column_dimensions[get_column_letter(j)].width = w

wb.save(OUTPUT_XLS)
size_kb = os.path.getsize(OUTPUT_XLS) / 1024

# ═══════════════════════════════════════════════════════════════════════════
# LOPPUYHTEENVETO
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("OPTIMAALISTEN JOUKKUEIDEN YHTEENVETO")
print("=" * 70)
print(f"\n{'Kierros':<10} {'Muod.':<12} {'XI pts':<8} {'Cap.':<8} "
      f"{'Cap. bonus':<12} {'TOTAL':<8} {'Budjetti':<10} Kapteeni")
print("-" * 70)
for gw in sorted(results.keys()):
    r = results[gw]
    c = r["captain"]
    print(f"GW {gw:<7} {r['formation']:<12} {r['xi_pts']:<8} "
          f"{c['name']:<8} +{r['cap_bonus']:<11} {r['total_pts']:<8} "
          f"{r['budget']:.1f}M      {c['name']} ({c['points']}pts)")

print(f"\nTiedostot tallennettu kansioon FPL Data/")
print(f"  best_team_per_gw.xlsx ({size_kb:.0f} KB)")
print(f"  best_teams_field_view.png")
print(f"  best_teams_summary_chart.png")
