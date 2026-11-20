"""
FPL: Mitä eroa on Top 5% ja keskivertomanagerilla?
====================================================
Analysoi viisi erottavaa tekijää:
  1. Kapteenipäätökset (suosittu vs. optimaalinen kapteeni per GW)
  2. Differentiaalipelaajat (korkeat pisteet, matala omistus)
  3. Penkkipistehukka (bench wastage)
  4. Siirtotehokkuus (hits + timing)
  5. Joukkueen arvokehitys (team value)
"""

import json, os, time, requests, math, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from scipy import stats
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
warnings.filterwarnings("ignore")

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_XLS = os.path.join(DATA_DIR, "manager_differences.xlsx")
BASE_URL   = "https://fantasy.premierleague.com/api"
HEADERS    = {"User-Agent": "Mozilla/5.0"}

def fetch(url, desc="", silent=False):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                if not silent:
                    print(f"  FAIL {desc}: {e}")
                return None

print("=" * 70)
print("FPL — Top 5% vs. Keskivertomanageri: Erottavat tekijät")
print("=" * 70)

# ── Lataa paikalliset datat ─────────────────────────────────────────────────
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)
with open(os.path.join(DATA_DIR, "live_gameweeks.json"), encoding="utf-8") as f:
    live_gws = json.load(f)
with open(os.path.join(DATA_DIR, "player_details.json"), encoding="utf-8") as f:
    player_details = json.load(f)

total_managers = bs["total_players"]
pos_map  = {t["id"]: t["singular_name_short"] for t in bs["element_types"]}
team_map = {t["id"]: t["short_name"]          for t in bs["teams"]}
name_map = {p["id"]: p["web_name"] for p in bs["elements"]}
events   = {e["id"]: e for e in bs["events"] if e.get("finished")}

# ═══════════════════════════════════════════════════════════════════════════
# ANALYYSI 1: KAPTEENIPÄÄTÖKSET
# ═══════════════════════════════════════════════════════════════════════════
print("\n[1/5] Kapteenianalyysi — suosittu vs. optimaalinen kapteeni...")

captain_rows = []
for gw_id, event in sorted(events.items()):
    gw_str = str(gw_id)
    if gw_str not in live_gws:
        continue

    # Kaikki pelaajat tällä kierroksella
    elements = live_gws[gw_str]["elements"]
    pts_map  = {e["id"]: e["stats"]["total_points"] for e in elements}

    # Suosituin kapteeni (crowd)
    popular_cap_id  = event["most_captained"]
    popular_cap_pts = pts_map.get(popular_cap_id, 0)

    # Optimaalinen kapteeni (korkein yksittäinen pistemäärä)
    optimal_cap_id  = max(pts_map, key=pts_map.get)
    optimal_cap_pts = pts_map[optimal_cap_id]

    # Top-3 kapteenivaihtoehdot
    top3 = sorted(pts_map.items(), key=lambda x: -x[1])[:3]

    captain_rows.append({
        "gw":              gw_id,
        "popular_id":      popular_cap_id,
        "popular_name":    name_map.get(popular_cap_id, "?"),
        "popular_pts":     popular_cap_pts,
        "popular_bonus":   popular_cap_pts,          # kapteeni saa 2× → bonus = 1× extra
        "optimal_id":      optimal_cap_id,
        "optimal_name":    name_map.get(optimal_cap_id, "?"),
        "optimal_pts":     optimal_cap_pts,
        "optimal_bonus":   optimal_cap_pts,
        "gap":             optimal_cap_pts - popular_cap_pts,  # extra points available
        "popular_was_best": popular_cap_id == optimal_cap_id,
        "top3":            [(name_map.get(i,"?"), p) for i, p in top3],
    })

df_cap = pd.DataFrame(captain_rows)
cumulative_gap    = df_cap["gap"].sum()
gws_crowd_correct = df_cap["popular_was_best"].sum()

print(f"   Suosittu kapteeni oli paras: {gws_crowd_correct}/{len(df_cap)} GW:llä")
print(f"   Kumulatiivinen kapteenietu (optimaalinen − suosittu): +{cumulative_gap} ekstra-pts")
print(f"   Per-kierros keskimäärin: +{cumulative_gap/len(df_cap):.1f} pts kapteeniedulla")

# ═══════════════════════════════════════════════════════════════════════════
# ANALYYSI 2: DIFFERENTIAALIPELAAJAT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[2/5] Differentiaalipelaajat — korkeat pisteet, matala omistus...")

diff_rows = []
for pid_str, detail in player_details.items():
    pid  = int(pid_str)
    meta_pos  = pos_map.get(
        next((p["element_type"] for p in bs["elements"] if p["id"] == pid), None), "?")
    meta_team = team_map.get(
        next((p["team"]         for p in bs["elements"] if p["id"] == pid), None), "?")

    for h in detail.get("history", []):
        ownership_pct = (h["selected"] / total_managers * 100) if h["selected"] else 0
        diff_rows.append({
            "pid":       pid,
            "name":      name_map.get(pid, "?"),
            "position":  meta_pos,
            "team":      meta_team,
            "gw":        h["round"],
            "points":    h["total_points"],
            "minutes":   h["minutes"],
            "ownership": ownership_pct,
            "value":     h["value"] / 10.0,
        })

df_diff = pd.DataFrame(diff_rows)
df_diff_played = df_diff[df_diff["minutes"] > 0].copy()

# Differentiaalit: pisteet ≥ 10 ja omistus < 15%
differentials = df_diff_played[
    (df_diff_played["points"] >= 10) &
    (df_diff_played["ownership"] < 15)
].copy()
differentials["diff_value"] = differentials["points"] * (1 - differentials["ownership"]/100)
differentials = differentials.sort_values("diff_value", ascending=False)

# "Crowd traps": suosittu pelaaja (>30% omistus) joka flopasi (≤2 pts)
crowd_traps = df_diff_played[
    (df_diff_played["ownership"] > 30) &
    (df_diff_played["points"] <= 2) &
    (df_diff_played["minutes"] > 45)
].copy()

print(f"   Differentiaalibombit (≥10pts, <15% omistus): {len(differentials)} suoritusta")
print(f"   Crowd trapit (>30% omistus, ≤2pts, yli 45min): {len(crowd_traps)} suoritusta")
print(f"   TOP differentiaalit:")
for _, r in differentials.head(5).iterrows():
    print(f"   GW{int(r['gw'])}: {r['name']:15s} {r['points']}pts  {r['ownership']:.1f}% omistus")

# ═══════════════════════════════════════════════════════════════════════════
# ANALYYSI 3: PENKKIPISTEHUKKA & SIIRTOTEHOKKUUS
# ═══════════════════════════════════════════════════════════════════════════
print("\n[3/5] Haetaan manageriotos: top 5% vs. mediaani...")

def get_entries_at_rank(target_rank, n=15):
    """Hae n manageria läheltä target_rank:ia."""
    page = math.ceil(target_rank / 50)
    data = fetch(f"{BASE_URL}/leagues-classic/314/standings/?page_standings={page}",
                 f"standings p{page}", silent=True)
    entries = []
    if data:
        for entry in data.get("standings", {}).get("results", []):
            entries.append({"entry_id": entry["entry"],
                             "rank": entry["rank"],
                             "total": entry["total"],
                             "name": entry.get("player_name", "?")})
    return entries[:n]

def fetch_manager_history(entry_id):
    """Hae managerin GW-historia."""
    data = fetch(f"{BASE_URL}/entry/{entry_id}/history/", silent=True)
    if not data:
        return None
    rows = []
    for gw in data.get("current", []):
        rows.append({
            "entry_id":    entry_id,
            "gw":          gw["event"],
            "points":      gw["points"],
            "total_pts":   gw["total_points"],
            "overall_rank":gw["overall_rank"],
            "bank":        gw["bank"] / 10.0,
            "value":       gw["value"] / 10.0,
            "transfers":   gw["event_transfers"],
            "hit_cost":    gw["event_transfers_cost"],
            "bench_pts":   gw["points_on_bench"],
        })
    return rows

# Hae top 5% managerit (rank ~1 000 – 655 000)
top5_entries = []
for target in [1000, 50000, 200000, 400000, 600000]:
    top5_entries += get_entries_at_rank(target, n=5)
    time.sleep(0.3)

# Hae mediaanimanagerit (rank ~6 000 000 – 7 000 000)
median_rank = total_managers // 2
median_entries = []
for target in [median_rank - 200000, median_rank, median_rank + 200000]:
    median_entries += get_entries_at_rank(target, n=5)
    time.sleep(0.3)

print(f"   Top 5% managerit haettu: {len(top5_entries)}")
print(f"   Mediaanimanagerit haettu: {len(median_entries)}")

# Hae historiat
def fetch_group(entries, label):
    histories = []
    for e in entries:
        hist = fetch_manager_history(e["entry_id"])
        if hist:
            for row in hist:
                row["group"] = label
                row["total_season"] = e["total"]
                row["rank_group"] = e["rank"]
            histories += hist
        time.sleep(0.2)
    return histories

print("   Haetaan historiat...")
all_histories = fetch_group(top5_entries, "Top 5%") + \
                fetch_group(median_entries, "Mediaani")

df_hist = pd.DataFrame(all_histories)
print(f"   Historia-rivejä: {len(df_hist)}")

# ═══════════════════════════════════════════════════════════════════════════
# ANALYYSI 4: CHIP-AJOITUS
# ═══════════════════════════════════════════════════════════════════════════
print("\n[4/5] Chip-ajoitus...")

chip_data = []
for gw_id, event in sorted(events.items()):
    for chip in event.get("chip_plays", []):
        avg_score = event["average_entry_score"]
        gw_str = str(gw_id)
        best_score = live_gws[gw_str]["elements"] if gw_str in live_gws else []
        # Paras 11 pelaajan pisteet (bench boost paras hyöty)
        top11_pts = sum(sorted(
            [e["stats"]["total_points"] for e in best_score], reverse=True)[:11]) \
            if best_score else 0
        chip_data.append({
            "gw":        gw_id,
            "chip":      chip["chip_name"],
            "plays":     chip["num_played"],
            "avg_score": avg_score,
            "top11_pts": top11_pts,
        })

df_chips = pd.DataFrame(chip_data)
chip_names = {"bboost": "Bench Boost", "3xc": "Triple Captain",
              "freehit": "Free Hit", "wildcard": "Wildcard"}

# ═══════════════════════════════════════════════════════════════════════════
# ANALYYSI 5: VERTAILUTILASTOT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[5/5] Lasketaan vertailutilastot...")

comparison = {}
if not df_hist.empty and "group" in df_hist.columns:
    for metric in ["bench_pts", "hit_cost", "value", "bank", "points"]:
        if metric in df_hist.columns:
            top5_vals   = df_hist[df_hist["group"] == "Top 5%"][metric]
            median_vals = df_hist[df_hist["group"] == "Mediaani"][metric]
            comparison[metric] = {
                "top5_avg":    top5_vals.mean(),
                "median_avg":  median_vals.mean(),
                "diff":        top5_vals.mean() - median_vals.mean(),
                "t_stat":      stats.ttest_ind(top5_vals.dropna(), median_vals.dropna())[0]
                               if len(top5_vals) > 1 and len(median_vals) > 1 else 0,
                "p_value":     stats.ttest_ind(top5_vals.dropna(), median_vals.dropna())[1]
                               if len(top5_vals) > 1 and len(median_vals) > 1 else 1,
            }
    print(f"\n   {'Mittari':<25} {'Top 5%':>10} {'Mediaani':>10} {'Ero':>10}")
    print("   " + "-"*55)
    labels = {"bench_pts": "Penkkipt./kierros",
              "hit_cost":  "Siirtohit/kierros",
              "value":     "Joukkuearvo (M)",
              "bank":      "Pankki (M)",
              "points":    "Pisteet/kierros"}
    for k, v in comparison.items():
        print(f"   {labels.get(k,k):<25} {v['top5_avg']:>10.2f} "
              f"{v['median_avg']:>10.2f} {v['diff']:>+10.2f}")

# ═══════════════════════════════════════════════════════════════════════════
# VISUALISOINNIT
# ═══════════════════════════════════════════════════════════════════════════
print("\n   Piirretään kuvaajat...")

C_TOP5   = "#1565C0"
C_MEDIAN = "#F57F17"
C_DIFF   = "#2E7D32"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25,
    "figure.facecolor": "white",
})

# ── Kuva 1: Kapteenianalyysi (2×2) ─────────────────────────────────────────
fig1, axes = plt.subplots(2, 2, figsize=(15, 10))
fig1.suptitle("TEKIJÄ 1: Kapteenipäätös — suosittu vs. optimaalinen",
              fontsize=13, fontweight="bold")

# 1A: Pisteet kierroksittain
ax = axes[0, 0]
ax.bar(df_cap["gw"], df_cap["popular_pts"], color=C_MEDIAN, alpha=0.7,
       label="Suosituin kapteeni (crowd)", width=0.7)
ax.step(df_cap["gw"], df_cap["optimal_pts"], color=C_TOP5, linewidth=2,
        label="Optimaalinen kapteeni", where="mid")
ax.fill_between(df_cap["gw"], df_cap["popular_pts"], df_cap["optimal_pts"],
                alpha=0.2, color=C_TOP5, label="Menetetty etu")
ax.set_xlabel("Kierros"); ax.set_ylabel("Kapteenin pisteet")
ax.set_title(f"Kapteenin pisteet per kierros\n"
             f"Crowd oikein {gws_crowd_correct}/{len(df_cap)} GW:llä")
ax.legend(fontsize=8)

# 1B: Kumulatiivinen kapteenietu
ax = axes[0, 1]
cum_gap = df_cap["gap"].cumsum()
ax.fill_between(df_cap["gw"], 0, cum_gap, alpha=0.3, color=C_DIFF)
ax.plot(df_cap["gw"], cum_gap, color=C_DIFF, linewidth=2.5)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xlabel("Kierros"); ax.set_ylabel("Kumulatiiviset lisäpisteet")
ax.set_title(f"Kumulatiivinen kapteenietu kaudessa\n"
             f"Täydellinen kapteenitieto = +{cumulative_gap} ekstra-pts")
ax.text(df_cap["gw"].max(), cum_gap.iloc[-1],
        f" +{cumulative_gap} pts", va="center", fontsize=9,
        fontweight="bold", color=C_DIFF)

# 1C: Kapteenietu histogrammi
ax = axes[1, 0]
ax.hist(df_cap["gap"], bins=15, color=C_DIFF, alpha=0.8, edgecolor="white")
ax.axvline(df_cap["gap"].mean(), color="red", linestyle="--", linewidth=2,
           label=f"Keskim. +{df_cap['gap'].mean():.1f} pts/GW")
ax.set_xlabel("Optimaalinen − suosittu (pts)")
ax.set_ylabel("Kierrosten lukumäärä")
ax.set_title("Kapteeniedun jakauma per kierros")
ax.legend(fontsize=8)

# 1D: Suosittu vs. optimaalinen scatter
ax = axes[1, 1]
colors_sc = [C_DIFF if r["popular_was_best"] else C_MEDIAN for _, r in df_cap.iterrows()]
ax.scatter(df_cap["popular_pts"], df_cap["optimal_pts"],
           c=colors_sc, s=80, alpha=0.85, edgecolors="white", linewidth=0.5)
max_val = max(df_cap["optimal_pts"].max(), df_cap["popular_pts"].max())
ax.plot([0, max_val], [0, max_val], "k--", linewidth=1.2, alpha=0.5,
        label="Täydellinen = tällä viivalla")
ax.set_xlabel("Suosituin kapteeni (pts)")
ax.set_ylabel("Optimaalinen kapteeni (pts)")
ax.set_title("Suosittu vs. Optimaalinen kapteeni\n(vihreä = crowd osui oikein)")
ax.legend(fontsize=8)
green_p = mpatches.Patch(color=C_DIFF, label=f"Crowd oikein ({gws_crowd_correct} GW)")
orange_p = mpatches.Patch(color=C_MEDIAN, label=f"Crowd väärässä ({len(df_cap)-gws_crowd_correct} GW)")
ax.legend(handles=[green_p, orange_p], fontsize=8)

plt.tight_layout()
img1 = os.path.join(DATA_DIR, "diff_1_captain.png")
fig1.savefig(img1, dpi=130, bbox_inches="tight"); plt.close(fig1)
print("   Kuva 1 (kapteeni) OK")

# ── Kuva 2: Differentiaalipelaajat ─────────────────────────────────────────
fig2, axes = plt.subplots(1, 2, figsize=(15, 7))
fig2.suptitle("TEKIJÄ 2: Differentiaalipelaajat — matala omistus, korkeat pisteet",
              fontsize=13, fontweight="bold")

# 2A: Scatter omistus vs. pisteet
ax = axes[0]
sample = df_diff_played.sample(min(5000, len(df_diff_played)), random_state=42)
sc = ax.scatter(sample["ownership"], sample["points"],
                alpha=0.15, s=10, c=sample["points"],
                cmap="RdYlGn", vmin=0, vmax=20)
plt.colorbar(sc, ax=ax, label="Pisteet")
# Differentiaalit korostettu
ax.scatter(differentials["ownership"], differentials["points"],
           c=C_DIFF, s=60, alpha=0.8, zorder=5, label=f"Differentiaalit\n(≥10pts, <15% omistus)")
ax.axvline(15,  color="red",    linestyle="--", linewidth=1.2, alpha=0.7, label="15% omistusraja")
ax.axhline(10,  color="orange", linestyle="--", linewidth=1.2, alpha=0.7, label="10 pts -raja")
ax.set_xlabel("Omistusprosentti (%)")
ax.set_ylabel("Pisteet")
ax.set_title(f"Omistus vs. Pisteet (kaikki GW:t)\n{len(differentials)} differentiaalibombia")
ax.legend(fontsize=8)

# 2B: Top differentiaalit palkkikuva
ax = axes[1]
top_diffs = differentials.head(20).sort_values("diff_value")
colors_d  = ["#1B5E20" if o < 5 else "#388E3C" if o < 10 else "#66BB6A"
              for o in top_diffs["ownership"]]
bars = ax.barh([f"GW{int(r['gw'])}: {r['name']}" for _, r in top_diffs.iterrows()],
               top_diffs["points"], color=colors_d, alpha=0.85, height=0.7)
for bar, (_, r) in zip(bars, top_diffs.iterrows()):
    ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
            f"{r['ownership']:.1f}% omistus", va="center", fontsize=7.5)
ax.set_xlabel("Pisteet")
ax.set_title("TOP 20 differentiaalibombia\n(vihreämpi = pienempi omistus)")
ax.set_xlim(0, top_diffs["points"].max() + 8)

plt.tight_layout()
img2 = os.path.join(DATA_DIR, "diff_2_differentials.png")
fig2.savefig(img2, dpi=130, bbox_inches="tight"); plt.close(fig2)
print("   Kuva 2 (differentiaalit) OK")

# ── Kuva 3: Manager vertailu ────────────────────────────────────────────────
if not df_hist.empty and "group" in df_hist.columns and len(df_hist["group"].unique()) > 1:
    fig3, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig3.suptitle("TEKIJÄT 3–5: Top 5% vs. Mediaanimanageri\n(Penkkihukka, Siirtohitit, Joukkuearvo)",
                  fontsize=13, fontweight="bold")

    metrics = [
        ("bench_pts",  "Penkkipisteet / kierros",  "TEKIJÄ 3: Penkkipistehukka"),
        ("hit_cost",   "Siirtohit-pistehukka / GW", "TEKIJÄ 4: Siirtohitit"),
        ("value",      "Joukkueen arvo (M)",         "TEKIJÄ 5: Joukkueen arvo"),
        ("bank",       "Pankki (M)",                 "TEKIJÄ 5b: Pankkivarat"),
        ("points",     "GW-pisteet",                 "Pisteet per kierros"),
        ("hit_cost",   "Kum. hit-kustannus",         "Siirtohitit kaudessa"),
    ]

    for ax, (metric, ylabel, title) in zip(axes.flatten(), metrics):
        top5_d   = df_hist[df_hist["group"] == "Top 5%"]
        median_d = df_hist[df_hist["group"] == "Mediaani"]

        if metric == "hit_cost" and title.startswith("Kum"):
            # Kumulatiivinen versio
            for grp, color, lbl in [("Top 5%", C_TOP5, "Top 5%"),
                                      ("Mediaani", C_MEDIAN, "Mediaani")]:
                sub = df_hist[df_hist["group"] == grp].groupby("gw")["hit_cost"].mean()
                ax.plot(sub.index, sub.cumsum(), color=color, linewidth=2.5, label=lbl)
        elif metric in df_hist.columns:
            for grp, color, lbl in [("Top 5%", C_TOP5, "Top 5%"),
                                      ("Mediaani", C_MEDIAN, "Mediaani")]:
                sub = df_hist[df_hist["group"] == grp].groupby("gw")[metric].mean()
                ax.plot(sub.index, sub, color=color, linewidth=2.5, label=lbl, alpha=0.9)
                # CI-nauha
                sub_std = df_hist[df_hist["group"]==grp].groupby("gw")[metric].std()
                ax.fill_between(sub.index,
                                sub - sub_std/2, sub + sub_std/2,
                                color=color, alpha=0.12)

        ax.set_xlabel("Kierros"); ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.legend(fontsize=8)

    plt.tight_layout()
    img3 = os.path.join(DATA_DIR, "diff_3_manager_comparison.png")
    fig3.savefig(img3, dpi=130, bbox_inches="tight"); plt.close(fig3)
    print("   Kuva 3 (managerivertailu) OK")
else:
    img3 = None
    print("   Kuva 3 ohitettu (ei riittävästi dataa)")

# ── Kuva 4: Chip-ajoitus ───────────────────────────────────────────────────
if not df_chips.empty:
    fig4, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig4.suptitle("TEKIJÄ 6: Chip-ajoitus — milloin pelattu vs. milloin kannattaisi",
                  fontsize=13, fontweight="bold")

    ax = axes[0]
    chip_colors = {"bboost": "#4CAF50", "3xc": "#FFD700",
                   "freehit": "#2196F3", "wildcard": "#FF5722"}
    for chip_name, group in df_chips.groupby("chip"):
        color = chip_colors.get(chip_name, "gray")
        ax.bar(group["gw"] + list(df_chips["chip"].unique()).index(chip_name) * 0.2,
               group["plays"] / 1000,
               width=0.2, color=color, alpha=0.85,
               label=chip_names.get(chip_name, chip_name))
    ax.set_xlabel("Kierros"); ax.set_ylabel("Käyttökerrat (tuhansina)")
    ax.set_title("Chip-käyttö per kierros")
    ax.legend(fontsize=8)

    ax = axes[1]
    gw_avgs = {e["id"]: e["average_entry_score"] for e in bs["events"] if e.get("finished")}
    gws_sorted = sorted(gw_avgs.keys())
    scores = [gw_avgs[g] for g in gws_sorted]
    ax.bar(gws_sorted, scores, color="#BBDEFB", alpha=0.9, label="GW keskiarvo (kaikki)")
    for chip_name, group in df_chips.groupby("chip"):
        color = chip_colors.get(chip_name, "gray")
        for _, row in group.iterrows():
            if row["plays"] > 50000:
                ax.axvline(row["gw"], color=color, linewidth=2, alpha=0.8)
                ax.text(row["gw"] + 0.2,
                        max(scores) * 0.95 - list(df_chips["chip"].unique()).index(chip_name) * 4,
                        chip_names.get(chip_name, chip_name)[:4],
                        fontsize=6.5, color=color, fontweight="bold")
    ax.set_xlabel("Kierros"); ax.set_ylabel("Kierroksen keskiarvopisteet")
    ax.set_title("Suosituimmat chip-kierrokset vs. GW-vaikeus\n(>50k käyttöä)")
    legend_patches = [mpatches.Patch(color=c, label=chip_names.get(n, n))
                      for n, c in chip_colors.items()]
    ax.legend(handles=legend_patches, fontsize=8)

    plt.tight_layout()
    img4 = os.path.join(DATA_DIR, "diff_4_chips.png")
    fig4.savefig(img4, dpi=130, bbox_inches="tight"); plt.close(fig4)
    print("   Kuva 4 (chipit) OK")
else:
    img4 = None

# ═══════════════════════════════════════════════════════════════════════════
# EXCEL-RAPORTTI
# ═══════════════════════════════════════════════════════════════════════════
print("\n   Kirjoitetaan Excel...")

wb = Workbook()
thin = Side(style="thin", color="BBBBBB")
brd  = Border(left=thin, right=thin, top=thin, bottom=thin)
ca   = Alignment(horizontal="center", vertical="center")
la   = Alignment(horizontal="left",   vertical="center")

DARK   = PatternFill("solid", fgColor="1F3864")
MED    = PatternFill("solid", fgColor="2E75B6")
TOP5F  = PatternFill("solid", fgColor="BBDEFB")
MEDF   = PatternFill("solid", fgColor="FFF9C4")
ALT    = PatternFill("solid", fgColor="F5F5F5")
GRN    = PatternFill("solid", fgColor="C8E6C9")
RED    = PatternFill("solid", fgColor="FFCDD2")

def hdr(ws, r, c, v, fill=MED, fc="FFFFFF", sz=10, bold=True, al=ca):
    cell = ws.cell(row=r, column=c, value=v)
    cell.fill = fill; cell.font = Font(bold=bold, color=fc, size=sz)
    cell.alignment = al; cell.border = brd; return cell

def dat(ws, r, c, v, bold=False, fmt=None, fill=None, al=ca):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = Font(bold=bold, size=9)
    cell.alignment = al; cell.border = brd
    if fill: cell.fill = fill
    if fmt:  cell.number_format = fmt; return cell

# ── Sheet 1: Yhteenveto ────────────────────────────────────────────────────
ws1 = wb.active; ws1.title = "Yhteenveto"
ws1.merge_cells("A1:H1")
ws1["A1"].value = "FPL: Top 5% vs. Keskivertomanageri — Erottavat tekijät"
ws1["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws1["A1"].fill = DARK; ws1["A1"].alignment = ca; ws1.row_dimensions[1].height = 28

# Yhteenvetotaulukko
hdr(ws1, 3, 1, "Tekijä"); hdr(ws1, 3, 2, "Top 5%"); hdr(ws1, 3, 3, "Mediaani")
hdr(ws1, 3, 4, "Ero"); hdr(ws1, 3, 5, "Kaus. vaikutus"); hdr(ws1, 3, 6, "Merkitys")

rows_summary = []

# Kapteeni
rows_summary.append({
    "tekija":    "1. Kapteenipäätös",
    "top5":      f"{df_cap['optimal_pts'].mean():.1f} pts/GW (optimaali)",
    "median":    f"{df_cap['popular_pts'].mean():.1f} pts/GW (suosittu)",
    "ero":       f"+{df_cap['gap'].mean():.1f} pts/GW",
    "kausi":     f"+{cumulative_gap} pts kausissa (täydellinen)",
    "merkitys":  "KRIITTINEN — kapteeni 2× pisteet, oikea valinta tekee tai rikkoo viikon",
})

# Differentiaalit
rows_summary.append({
    "tekija":    "2. Differentiaalipelaajat",
    "top5":      f"{len(differentials)} bombia löydetty (<15% omistus)",
    "median":    "Crowd-pelaajat (>30% omistus)",
    "ero":       f"Max +{differentials['points'].max():.0f} pts differentiaalilla",
    "kausi":     "Useita +10-20 pts etuja kaudessa",
    "merkitys":  "TÄRKEÄ — erottaa top 5% pääsarjatasolla, vaikutus kumulatiivinen",
})

# Penkkipisteet
if comparison.get("bench_pts"):
    c = comparison["bench_pts"]
    rows_summary.append({
        "tekija":   "3. Penkkipistehukka",
        "top5":     f"{c['top5_avg']:.1f} pts/GW penkille",
        "median":   f"{c['median_avg']:.1f} pts/GW penkille",
        "ero":      f"{c['diff']:+.1f} pts/GW",
        "kausi":    f"{c['diff']*38:+.0f} pts kaudessa",
        "merkitys": "KOHTALAINEN — pienemmät penkkipisteet = parempi aloitusvalinta",
    })

# Siirtohitit
if comparison.get("hit_cost"):
    c = comparison["hit_cost"]
    rows_summary.append({
        "tekija":   "4. Siirtohitit (-4 pts/hit)",
        "top5":     f"{c['top5_avg']:.2f} pts/GW",
        "median":   f"{c['median_avg']:.2f} pts/GW",
        "ero":      f"{c['diff']:+.2f} pts/GW",
        "kausi":    f"{c['diff']*38:+.0f} pts kaudessa",
        "merkitys": "KOHTALAINEN — turhat hitit syövät pisteitä, top 5% harkitsee siirrot",
    })

# Joukkuearvo
if comparison.get("value"):
    c = comparison["value"]
    rows_summary.append({
        "tekija":   "5. Joukkueen arvokehitys",
        "top5":     f"{c['top5_avg']:.1f}M avg",
        "median":   f"{c['median_avg']:.1f}M avg",
        "ero":      f"{c['diff']:+.1f}M",
        "kausi":    "Korkeampi arvo = enemmän siirtofleksibiliteettia",
        "merkitys": "TÄRKEÄ — arvoetu kertyy kauden mittaan, antaa paremmat siirtovaihtoehdot",
    })

for i, r in enumerate(rows_summary):
    row = 4 + i
    is_alt = i % 2 == 0
    dat(ws1, row, 1, r["tekija"], bold=True, fill=ALT if is_alt else None, al=la)
    dat(ws1, row, 2, r["top5"],   fill=TOP5F, al=la)
    dat(ws1, row, 3, r["median"], fill=MEDF, al=la)
    dat(ws1, row, 4, r["ero"],    bold=True, fill=GRN if "+" in str(r["ero"]) else RED, al=ca)
    dat(ws1, row, 5, r["kausi"],  fill=ALT if is_alt else None, al=la)
    dat(ws1, row, 6, r["merkitys"], fill=ALT if is_alt else None, al=la)

for j, w in enumerate([28, 28, 28, 18, 30, 55], 1):
    ws1.column_dimensions[get_column_letter(j)].width = w

# Kuvaajat
for img_p, anchor in [(img1, "A12"), (img2, "A57"), (img4, "A100")]:
    if img_p and os.path.exists(img_p):
        img_obj = XLImage(img_p)
        img_obj.width = 930
        img_obj.height = int(img_obj.width * 0.68)
        ws1.add_image(img_obj, anchor)

# ── Sheet 2: Kapteenidata ──────────────────────────────────────────────────
ws2 = wb.create_sheet("Kapteenidata")
ws2.merge_cells("A1:H1")
ws2["A1"].value = "Kapteenianalyysi — suosittu vs. optimaalinen kapteeni per kierros"
ws2["A1"].font = Font(bold=True, size=11, color="FFFFFF")
ws2["A1"].fill = DARK; ws2["A1"].alignment = ca

for j, h in enumerate(["GW","Suosituin kapteeni","Pisteet","Optimaalinen","Pisteet",
                        "Etu (opt-pop)","Crowd oikein?","TOP 3 vaihtoehtoa"], 1):
    hdr(ws2, 2, j, h)

for i, (_, r) in enumerate(df_cap.iterrows()):
    row = 3 + i
    correct = r["popular_was_best"]
    fill_r = GRN if correct else (RED if r["gap"] > 8 else (ALT if i%2==0 else None))
    top3_str = " | ".join([f"{n}({p})" for n, p in r["top3"]])
    vals = [int(r["gw"]), r["popular_name"], r["popular_pts"],
            r["optimal_name"], r["optimal_pts"],
            r["gap"], "Kyllä" if correct else "Ei", top3_str]
    for j, v in enumerate(vals, 1):
        dat(ws2, row, j, v, fill=fill_r, al=la if j in (2,4,8) else ca,
            bold=(j == 6 and r["gap"] > 8))

for j, w in enumerate([5, 16, 8, 16, 8, 12, 12, 45], 1):
    ws2.column_dimensions[get_column_letter(j)].width = w

# ── Sheet 3: TOP differentiaalit ──────────────────────────────────────────
ws3 = wb.create_sheet("Differentiaalit")
ws3.merge_cells("A1:H1")
ws3["A1"].value = f"Differentiaalipelaajat — ≥10 pts, <15% omistus (yhteensä {len(differentials)})"
ws3["A1"].font = Font(bold=True, size=11, color="FFFFFF")
ws3["A1"].fill = DARK; ws3["A1"].alignment = ca

for j, h in enumerate(["GW","Pelaaja","Joukkue","Asema","Pisteet",
                        "Omistus %","Diff-arvo","Arvo (M)"], 1):
    hdr(ws3, 2, j, h)

for i, (_, r) in enumerate(differentials.head(100).iterrows()):
    row = 3 + i
    own_fill = (GRN if r["ownership"] < 5
                else PatternFill("solid", fgColor="DCEDC8") if r["ownership"] < 10
                else ALT if i%2==0 else None)
    vals = [int(r["gw"]), r["name"], r["team"], r["position"],
            r["points"], round(r["ownership"],1), round(r["diff_value"],1), r["value"]]
    fmts = [None,None,None,None,None,"0.0","0.0","0.0"]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        dat(ws3, row, j, v, fmt=fmt, fill=own_fill,
            al=la if j in (2,3,4) else ca)

for j, w in enumerate([5,16,8,7,8,10,10,10], 1):
    ws3.column_dimensions[get_column_letter(j)].width = w

# ── Sheet 4: Managerivertailu ─────────────────────────────────────────────
if not df_hist.empty and "group" in df_hist.columns:
    ws4 = wb.create_sheet("Managerivertailu")
    ws4.merge_cells("A1:H1")
    ws4["A1"].value = (f"Top 5% ({len(top5_entries)} manageria) vs. "
                       f"Mediaani ({len(median_entries)} manageria) — GW-historia")
    ws4["A1"].font = Font(bold=True, size=11, color="FFFFFF")
    ws4["A1"].fill = DARK; ws4["A1"].alignment = ca

    metric_labels = {"bench_pts": "Penkkipisteet", "hit_cost": "Hit-kustannus",
                     "value": "Joukkuearvo (M)", "bank": "Pankki (M)", "points": "GW-pisteet"}
    all_metrics = [m for m in metric_labels if m in df_hist.columns]

    hdrs4 = ["GW"] + [f"Top5% {metric_labels[m]}" for m in all_metrics] + \
                     [f"Mediaani {metric_labels[m]}" for m in all_metrics]
    for j, h in enumerate(hdrs4, 1):
        hdr(ws4, 2, j, h,
            fill=TOP5F if "Top5%" in h else (MEDF if "Mediaani" in h else MED),
            fc="000000" if "Top5%" in h or "Mediaani" in h else "FFFFFF")

    top5_gw  = df_hist[df_hist["group"]=="Top 5%"].groupby("gw")[all_metrics].mean()
    medi_gw  = df_hist[df_hist["group"]=="Mediaani"].groupby("gw")[all_metrics].mean()
    all_gws  = sorted(set(top5_gw.index) | set(medi_gw.index))

    for i, gw in enumerate(all_gws):
        row = 3 + i
        fill_r = ALT if i%2==0 else None
        dat(ws4, row, 1, int(gw), fill=fill_r)
        for j, m in enumerate(all_metrics, 2):
            v = top5_gw.at[gw, m] if gw in top5_gw.index else None
            dat(ws4, row, j, round(v,2) if v is not None else "N/A", fill=TOP5F, fmt="0.00")
        for j, m in enumerate(all_metrics, 2 + len(all_metrics)):
            v = medi_gw.at[gw, m] if gw in medi_gw.index else None
            dat(ws4, row, j, round(v,2) if v is not None else "N/A", fill=MEDF, fmt="0.00")

    for j in range(1, len(hdrs4)+1):
        ws4.column_dimensions[get_column_letter(j)].width = 16

    if img3 and os.path.exists(img3):
        img_obj = XLImage(img3)
        img_obj.width = 920; img_obj.height = int(img_obj.width * 0.65)
        ws4.add_image(img_obj, f"A{len(all_gws)+5}")

wb.save(OUTPUT_XLS)
size_kb = os.path.getsize(OUTPUT_XLS)/1024

# ── Loppuyhteenveto ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("YHTEENVETO: Mitä erottaa top 5%:n?")
print("=" * 70)
print(f"\n1. KAPTEENIPÄÄTÖS")
print(f"   Suosittu kapteeni vs. optimaalinen: +{df_cap['gap'].mean():.1f} pts/GW ero")
print(f"   Täydellinen kapteenitieto = +{cumulative_gap} pts kaudessa")
print(f"   Crowd osui oikein: {gws_crowd_correct}/{len(df_cap)} kierroksella")
print(f"\n2. DIFFERENTIAALIPELAAJAT")
print(f"   {len(differentials)} bombia: ≥10 pts, <15% omistus")
print(f"   Paras differentiaali: {differentials.iloc[0]['name']} GW{int(differentials.iloc[0]['gw'])}: "
      f"{int(differentials.iloc[0]['points'])} pts @ {differentials.iloc[0]['ownership']:.1f}% omistus")
top5_diffs = differentials.head(10)
print(f"   Top 10 differentiaalin avg: {top5_diffs['points'].mean():.1f} pts, "
      f"{top5_diffs['ownership'].mean():.1f}% avg omistus")
if comparison:
    print(f"\n3. PENKKIPISTEHUKKA (top5% vs. mediaani)")
    if "bench_pts" in comparison:
        c = comparison["bench_pts"]
        print(f"   Top 5%: {c['top5_avg']:.1f} pts/GW penkille")
        print(f"   Mediaani: {c['median_avg']:.1f} pts/GW penkille")
        print(f"   Kauden vaikutus: {c['diff']*38:+.0f} pts")
    print(f"\n4. SIIRTOHITIT")
    if "hit_cost" in comparison:
        c = comparison["hit_cost"]
        print(f"   Top 5%: {c['top5_avg']:.2f} pts/GW hittikuluihin")
        print(f"   Mediaani: {c['median_avg']:.2f} pts/GW hittikuluihin")
    print(f"\n5. JOUKKUEARVO")
    if "value" in comparison:
        c = comparison["value"]
        print(f"   Top 5%: {c['top5_avg']:.1f}M  |  Mediaani: {c['median_avg']:.1f}M  |  "
              f"Ero: {c['diff']:+.1f}M")
print(f"\nExcel: {OUTPUT_XLS} ({size_kb:.0f} KB)")
