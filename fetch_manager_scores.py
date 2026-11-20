"""
FPL Manageri-pistetilasto — Top 5% analyysi
============================================
Hakee FPL API:sta otantapisteet eri rank-tasoilta,
estimoi top 5%:n keskiarvopisteet per kierros ja kaudelle.
"""

import json, os, time, requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_XLS = os.path.join(DATA_DIR, "manager_top5pct_analysis.xlsx")
BASE_URL   = "https://fantasy.premierleague.com/api"
HEADERS    = {"User-Agent": "Mozilla/5.0"}

def fetch(url, desc=""):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  FAIL: {desc} — {e}")
                return None

print("=" * 65)
print("FPL Top 5% Managerianalyysi")
print("=" * 65)

# ── 1. Bootstrap ────────────────────────────────────────────────────────────
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)

total_managers = bs["total_players"]
top5_rank      = int(total_managers * 0.05)   # ~655 000
top1_rank      = int(total_managers * 0.01)
top10_rank     = int(total_managers * 0.10)

print(f"\nKokonaismanagerit : {total_managers:,}")
print(f"Top 5% raja-rank  : {top5_rank:,}")
print(f"Top 1% raja-rank  : {top1_rank:,}")
print(f"Top 10% raja-rank : {top10_rank:,}")

# Per-kierros tiedot bootstrapista (avg + max)
events = bs["events"]
gw_bootstrap = {}
for e in events:
    if e.get("finished"):
        gw_bootstrap[e["id"]] = {
            "avg":     e["average_entry_score"],
            "highest": e["highest_score"],
            "ranked":  e.get("ranked_count", total_managers),
        }

print(f"\nKierrosaveraget bootstrapista: {len(gw_bootstrap)} kierrosta")

# ── 2. Kokonaispistetilasto: otanta eri rank-tasoilta ──────────────────────
print("\n[1/3] Haetaan kokonaispisteet eri rank-tasoilta (overall standings)...")

# Sivukoko = 50 → sivu missä tietty rank on: ceil(rank / 50)
import math
def rank_to_page(rank):
    return math.ceil(rank / 50)

# Otanta-rankit (logaritmisesti tasainen väliltä 1…top5_rank)
sample_ranks = sorted(set([
    1, 10, 50, 100, 500, 1_000, 2_500, 5_000,
    10_000, 25_000, 50_000, 100_000, 200_000,
    top1_rank, top5_rank, top10_rank,
]))

overall_url = f"{BASE_URL}/leagues-classic/314/standings/"

sample_scores = {}   # rank → total_score
fetched_pages = {}   # page → data

for rank in sample_ranks:
    page = rank_to_page(rank)
    if page not in fetched_pages:
        url  = f"{overall_url}?page_standings={page}"
        data = fetch(url, f"standings page {page}")
        if data:
            fetched_pages[page] = data
            results = data.get("standings", {}).get("results", [])
            for entry in results:
                sample_scores[entry["rank"]] = entry["total"]
        time.sleep(0.4)
    print(f"   Rank {rank:>8,}  → sivu {page:>6,}  | "
          f"pisteet: {sample_scores.get(rank, '?')}")

# ── 3. Haetaan per-kierros pisteet top-managereille ────────────────────────
print("\n[2/3] Haetaan per-kierros-data top managereille...")

# Kerää entry_id:t eri rank-tasoilta
entry_ids = {}   # entry_id → rank
for page_data in fetched_pages.values():
    for entry in page_data.get("standings", {}).get("results", []):
        if entry["rank"] <= top5_rank + 50:
            entry_ids[entry["entry"]] = entry["rank"]

# Valitse ~80 tasaisesti jakautunutta managerien historiaa
targets = {}
rank_buckets = list(np.linspace(1, top5_rank, 80).astype(int))
for rank in rank_buckets:
    closest = min(entry_ids.keys(),
                  key=lambda eid: abs(entry_ids[eid] - rank),
                  default=None)
    if closest:
        targets[closest] = entry_ids[closest]

print(f"   Haetaan historiat {len(targets)} managerille...")
manager_gw_scores = []   # {entry_id, rank, gw1..gw38, total}

fetched = 0
for entry_id, rank in sorted(targets.items(), key=lambda x: x[1]):
    hist = fetch(f"{BASE_URL}/entry/{entry_id}/history/", f"entry {entry_id}")
    if hist:
        current = hist.get("current", [])
        row = {"entry_id": entry_id, "rank": rank}
        for gw_entry in current:
            row[f"gw{gw_entry['event']}"] = gw_entry["points"]
        row["total"] = sum(gw_entry["points"] for gw_entry in current)
        manager_gw_scores.append(row)
    fetched += 1
    if fetched % 10 == 0:
        print(f"   {fetched}/{len(targets)} haettu...", end="\r")
    time.sleep(0.25)

print(f"\n   Haettu {len(manager_gw_scores)} managerin historia")

df_mgr = pd.DataFrame(manager_gw_scores)
if not df_mgr.empty:
    df_mgr = df_mgr.sort_values("rank").reset_index(drop=True)

# ── 4. LASKENTA ─────────────────────────────────────────────────────────────
print("\n[3/3] Lasketaan tilastot...")

# Kokonaispistejakaumasta interpoloi top5% avg ja raja
sorted_ranks = sorted(sample_scores.keys())
sorted_scores = [sample_scores[r] for r in sorted_ranks]

top5_threshold  = sample_scores.get(min(sample_scores.keys(),
                  key=lambda r: abs(r - top5_rank)), None)
top1_threshold  = sample_scores.get(min(sample_scores.keys(),
                  key=lambda r: abs(r - top1_rank)), None)
top10_threshold = sample_scores.get(min(sample_scores.keys(),
                  key=lambda r: abs(r - top10_rank)), None)

# Top 5%:n keskiarvo otannasta
top5_scores  = [s for r, s in sample_scores.items() if r <= top5_rank]
top1_scores  = [s for r, s in sample_scores.items() if r <= top1_rank]
top10_scores = [s for r, s in sample_scores.items() if r <= top10_rank]

if df_mgr.empty:
    print("   VAROITUS: Managerihistoriat puuttuvat, käytetään otantaa")

# Per-GW tilastot
gw_cols = [c for c in df_mgr.columns if c.startswith("gw")] if not df_mgr.empty else []
gw_nums = sorted([int(c[2:]) for c in gw_cols]) if gw_cols else []

# Yhdistä bootstrap-averaget + top5% per-GW
per_gw_stats = []
for gw in sorted(gw_bootstrap.keys()):
    row = {
        "gw":         gw,
        "avg_all":    gw_bootstrap[gw]["avg"],
        "highest_gw": gw_bootstrap[gw]["highest"],
    }
    if not df_mgr.empty and f"gw{gw}" in df_mgr.columns:
        top5_gw  = df_mgr[f"gw{gw}"].mean()
        top1_gw  = df_mgr[df_mgr["rank"] <= max(1, int(len(df_mgr) * 0.01))][f"gw{gw}"].mean()
        row["avg_top5pct"] = round(top5_gw, 1)
        row["avg_top1pct"] = round(top1_gw, 1)
        row["diff_vs_avg"] = round(top5_gw - gw_bootstrap[gw]["avg"], 1)
    per_gw_stats.append(row)

df_gw = pd.DataFrame(per_gw_stats)

# Kokonaistilasto
overall_stats = {
    "Kokonaismanagerit":       total_managers,
    "Top 5% raja (rank)":      top5_rank,
    "Top 5% pisteet (min)":    top5_threshold,
    "Top 1% pisteet (min)":    top1_threshold,
    "Top 10% pisteet (min)":   top10_threshold,
    "Otantaan perustuva avg (top5%)":
        round(np.mean(top5_scores), 1) if top5_scores else "N/A",
}

print("\n  Kokonaispistetilasto:")
for k, v in overall_stats.items():
    print(f"   {k:<38}: {v}")

if not df_gw.empty and "avg_top5pct" in df_gw.columns:
    season_top5_avg = df_gw["avg_top5pct"].sum()
    season_all_avg  = df_gw["avg_all"].sum()
    print(f"\n   Kauden pisteet (kaikki GW:t laskettu yhteen):")
    print(f"   Kaikki managerit (avg):   {season_all_avg:.0f} pts")
    print(f"   Top 5% (otanta-avg):      {season_top5_avg:.0f} pts")
    print(f"   Ero:                      +{season_top5_avg - season_all_avg:.0f} pts")

# ── 5. VISUALISOINNIT ──────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle("FPL Manager-pistetilasto — Top 5% vs. Kaikki",
             fontsize=14, fontweight="bold")

# 5A: Per-GW pisteet kaikki vs. top 5%
ax = axes[0, 0]
if not df_gw.empty and "avg_top5pct" in df_gw.columns:
    gws = df_gw["gw"].values
    ax.fill_between(gws, df_gw["avg_all"], df_gw["avg_top5pct"],
                    alpha=0.3, color="#2196F3", label="Ero (top5% - avg)")
    ax.plot(gws, df_gw["avg_all"],    "o-", color="#666666",
            linewidth=2, markersize=4, label="Kaikki (avg)")
    ax.plot(gws, df_gw["avg_top5pct"], "o-", color="#2196F3",
            linewidth=2, markersize=4, label="Top 5% (avg)")
    ax.plot(gws, df_gw["highest_gw"],  "^--", color="#FF5722",
            linewidth=1.5, markersize=4, alpha=0.7, label="Kierroksen paras")
ax.set_xlabel("Kierros (GW)"); ax.set_ylabel("Pisteet")
ax.set_title("Kierrospisteet: kaikki vs. top 5%")
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# 5B: Kumulatiiviset pisteet kauden aikana
ax = axes[0, 1]
if not df_gw.empty and "avg_top5pct" in df_gw.columns:
    cum_all  = df_gw["avg_all"].cumsum()
    cum_top5 = df_gw["avg_top5pct"].cumsum()
    cum_high = df_gw["highest_gw"].cumsum()
    gws = df_gw["gw"].values
    ax.fill_between(gws, cum_all, cum_top5, alpha=0.25, color="#2196F3")
    ax.plot(gws, cum_all,  "-",  color="#666666", linewidth=2.5, label="Kaikki")
    ax.plot(gws, cum_top5, "-",  color="#2196F3", linewidth=2.5, label="Top 5%")
    ax.plot(gws, cum_high, "--", color="#FF5722", linewidth=1.5,
            alpha=0.7, label="Kierrosvoittajat (summa)")
ax.set_xlabel("Kierros (GW)"); ax.set_ylabel("Kumulatiiviset pisteet")
ax.set_title("Kumulatiiviset kauden pisteet")
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# 5C: Kokonaispistejakauma (otantapisteet rank:n funktiona)
ax = axes[1, 0]
if sample_scores:
    ranks_  = sorted(sample_scores.keys())
    scores_ = [sample_scores[r] for r in ranks_]
    ax.plot(ranks_, scores_, "o-", color="#4CAF50", markersize=5, linewidth=2)
    if top5_threshold:
        ax.axhline(top5_threshold,  color="#2196F3", linestyle="--",
                   linewidth=1.5, label=f"Top 5% min: {top5_threshold} pts")
    if top1_threshold:
        ax.axhline(top1_threshold, color="#FF5722", linestyle="--",
                   linewidth=1.5, label=f"Top 1% min: {top1_threshold} pts")
    ax.axvline(top5_rank, color="#2196F3", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.set_xscale("log")
    ax.set_xlabel("Rank (log-asteikko)")
    ax.set_ylabel("Kauden kokonaispisteet")
    ax.set_title("Kokonaispisteet rank:n mukaan\n(otanta eri rank-tasoilta)")
    ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# 5D: Kierroksen ero (top5% - avg)
ax = axes[1, 1]
if not df_gw.empty and "diff_vs_avg" in df_gw.columns:
    gws  = df_gw["gw"].values
    diff = df_gw["diff_vs_avg"].values
    colors = ["#2196F3" if d > 0 else "#FF5722" for d in diff]
    ax.bar(gws, diff, color=colors, alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Kierros (GW)")
    ax.set_ylabel("Pisteet yli keskiarvon")
    ax.set_title("Top 5% ylisuoritus per kierros\n(top5% avg − kaikkien avg)")
ax.grid(axis="y", alpha=0.3)

plt.tight_layout()
img_path = os.path.join(DATA_DIR, "manager_top5pct_chart.png")
fig.savefig(img_path, dpi=150, bbox_inches="tight")
plt.close(fig)

# ── 6. EXCEL ───────────────────────────────────────────────────────────────
wb  = Workbook()
thin = Side(style="thin", color="BBBBBB")
brd  = Border(left=thin, right=thin, top=thin, bottom=thin)
ca   = Alignment(horizontal="center", vertical="center")
la   = Alignment(horizontal="left",   vertical="center")

DARK = PatternFill("solid", fgColor="1F3864")
MED  = PatternFill("solid", fgColor="2E75B6")
ALT  = PatternFill("solid", fgColor="D9E1F2")
GOLD = PatternFill("solid", fgColor="FFD700")
GRN  = PatternFill("solid", fgColor="C6EFCE")
RED  = PatternFill("solid", fgColor="FFC7CE")

def hdr(ws, r, c, v, fill=MED, fc="FFFFFF", sz=10, bold=True, al=ca):
    cell = ws.cell(row=r, column=c, value=v)
    cell.fill = fill; cell.font = Font(bold=bold, color=fc, size=sz)
    cell.alignment = al; cell.border = brd; return cell

def dat(ws, r, c, v, bold=False, fmt=None, fill=None, al=ca):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = Font(bold=bold, size=9)
    cell.alignment = al; cell.border = brd
    if fill: cell.fill = fill
    if fmt:  cell.number_format = fmt
    return cell

# Sheet 1: Yhteenveto
ws1 = wb.active; ws1.title = "Yhteenveto"
ws1.merge_cells("A1:G1")
ws1["A1"].value = "FPL Manager-pistetilasto — Top 5% analyysi"
ws1["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws1["A1"].fill = DARK; ws1["A1"].alignment = ca

# Kokonaistilasto
ws1.cell(row=3, column=1, value="KOKONAISTILASTO (kausi)").font = Font(bold=True, size=11)
ws1.merge_cells("A3:G3")
ws1["A3"].fill = MED; ws1["A3"].font = Font(bold=True, size=11, color="FFFFFF")
ws1["A3"].alignment = ca

for j, h in enumerate(["Mittari", "Arvo", "Huomio"], 1):
    hdr(ws1, 4, j, h)

summary_rows = [
    ("Kokonaismanagerit",  f"{total_managers:,}",     "Kauden 2025/26 osallistujat"),
    ("Top 5% raja-rank",   f"{top5_rank:,}",           f"= {total_managers:,} × 0.05"),
    ("Top 5% min. pisteet",f"{top5_threshold or 'N/A'}","Pisteet rank ~{:,}:lla".format(top5_rank)),
    ("Top 1% min. pisteet",f"{top1_threshold or 'N/A'}","Pisteet rank ~{:,}:lla".format(top1_rank)),
    ("Top 10% min. pisteet",f"{top10_threshold or 'N/A'}","Pisteet rank ~{:,}:lla".format(top10_rank)),
]
if not df_gw.empty and "avg_top5pct" in df_gw.columns:
    s_all  = df_gw["avg_all"].sum()
    s_top5 = df_gw["avg_top5pct"].sum()
    summary_rows += [
        ("Kauden avg (kaikki)", f"{s_all:.0f} pts",  "Kierrosavg-summa"),
        ("Kauden avg (top 5%)", f"{s_top5:.0f} pts", "Otantapohjainen estimaatti"),
        ("Ero (top5% - kaikki)", f"+{s_top5-s_all:.0f} pts", "Top5% ylisuoritus kaudessa"),
    ]

for i, (label, val, note) in enumerate(summary_rows):
    row = 5 + i
    fill_r = GOLD if "top 5%" in label.lower() else (ALT if i % 2 == 0 else None)
    dat(ws1, row, 1, label, bold=True, fill=fill_r, al=la)
    dat(ws1, row, 2, val,   bold=True, fill=fill_r)
    dat(ws1, row, 3, note,  fill=fill_r, al=la)

# Per-GW taulukko
r2 = 5 + len(summary_rows) + 2
ws1.merge_cells(f"A{r2}:G{r2}")
ws1[f"A{r2}"].value = "PER-KIERROS PISTEET"
ws1[f"A{r2}"].font = Font(bold=True, size=11, color="FFFFFF")
ws1[f"A{r2}"].fill = MED; ws1[f"A{r2}"].alignment = ca

hdrs_gw = ["GW", "Avg (kaikki)", "Avg (top 5%)", "Avg (top 1%)",
           "Ylisuoritus", "Kierroksen paras", "Top5% / Avg"]
for j, h in enumerate(hdrs_gw, 1):
    hdr(ws1, r2 + 1, j, h)

for i, row_data in df_gw.iterrows():
    row = r2 + 2 + i
    fill_r = ALT if i % 2 == 0 else None
    avg_all  = row_data["avg_all"]
    avg_top5 = row_data.get("avg_top5pct", "N/A")
    avg_top1 = row_data.get("avg_top1pct", "N/A")
    diff     = row_data.get("diff_vs_avg", "N/A")
    ratio    = (round(avg_top5 / avg_all, 3) if avg_top5 != "N/A" and avg_all > 0
                else "N/A")

    diff_fill = (GRN if isinstance(diff, (int, float)) and diff > 0
                 else RED if isinstance(diff, (int, float)) and diff < 0
                 else fill_r)

    vals = [int(row_data["gw"]), avg_all, avg_top5, avg_top1,
            diff, row_data["highest_gw"], ratio]
    fmts = [None, "0.0", "0.0", "0.0", "+0.0;-0.0", None, "0.000"]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        dat(ws1, row, j, v, fmt=fmt,
            fill=diff_fill if j == 5 else fill_r)

for j, w in enumerate([6, 14, 14, 14, 14, 16, 14], 1):
    ws1.column_dimensions[get_column_letter(j)].width = w

# Kuvaaja
if os.path.exists(img_path):
    img_obj = XLImage(img_path)
    img_obj.width = 920; img_obj.height = int(img_obj.width * 0.68)
    ws1.add_image(img_obj, f"A{r2 + len(df_gw) + 4}")

# Sheet 2: Otantapisteet (rank vs. total)
ws2 = wb.create_sheet("Kokonaispistejakauma")
ws2.merge_cells("A1:D1")
ws2["A1"].value = "Kokonaispisteet rank:n mukaan (otanta FPL Overall-liigasta)"
ws2["A1"].font = Font(bold=True, size=11, color="FFFFFF")
ws2["A1"].fill = DARK; ws2["A1"].alignment = ca

for j, h in enumerate(["Rank", "Kokonaispisteet", "Prosenttipiste", "Huomio"], 1):
    hdr(ws2, 2, j, h)

for i, (rank, score) in enumerate(sorted(sample_scores.items())):
    row  = 3 + i
    pct  = round((1 - rank / total_managers) * 100, 2)
    note = ("← Top 1% raja" if abs(rank - top1_rank) < 1000
            else "← Top 5% raja" if abs(rank - top5_rank) < 5000
            else "← Top 10% raja" if abs(rank - top10_rank) < 5000
            else "")
    fill_r = (GOLD if note else (ALT if i % 2 == 0 else None))
    dat(ws2, row, 1, rank,  fill=fill_r, fmt="#,##0")
    dat(ws2, row, 2, score, fill=fill_r, bold=bool(note))
    dat(ws2, row, 3, pct,   fill=fill_r, fmt="0.00")
    dat(ws2, row, 4, note,  fill=fill_r, al=la)

for j, w in enumerate([12, 18, 14, 20], 1):
    ws2.column_dimensions[get_column_letter(j)].width = w

wb.save(OUTPUT_XLS)
print(f"\nExcel tallennettu: {OUTPUT_XLS}")
print(f"Koko: {os.path.getsize(OUTPUT_XLS)/1024:.0f} KB")
