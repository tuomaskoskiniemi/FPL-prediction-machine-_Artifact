"""
FPL FDR–Pisteet Korrelaatioanalyysi
====================================
Analysoi miten Fixture Difficulty Rating (FDR) korreloi pelaajapisteiden kanssa.
- Per ottelu -taso (player_details history)
- FDR haetaan fixtures.json:sta was_home -kentän avulla
- Analyysi: kokonais, asemittain, koti/vieras, tilastolliset testit
- Tulostaa Excel-raportin + PNG-kuvat FPL Data -kansioon
"""

import json, os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from scipy import stats
from openpyxl import load_workbook, Workbook
from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                              GradientFill)
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import DataPoint
warnings.filterwarnings("ignore")

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_XLS = os.path.join(DATA_DIR, "fdr_correlation_analysis.xlsx")
IMG_DIR    = DATA_DIR

# ── Väripaletti ────────────────────────────────────────────────────────────
FDR_COLORS = {1: "#00FF87", 2: "#B8FFDF", 3: "#EAEAEA", 4: "#FF6B6B", 5: "#C00000"}
POS_COLORS = {"GKP": "#FFD700", "DEF": "#00C0FF", "MID": "#7FFF00", "FWD": "#FF6347"}
POSITIONS  = ["GKP", "DEF", "MID", "FWD"]

# ═══════════════════════════════════════════════════════════════════════════
# 1. LATAA DATA
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("FPL FDR–Pisteet Korrelaatioanalyysi")
print("=" * 60)

print("\n[1/5] Ladataan datatiedostot...")
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)
with open(os.path.join(DATA_DIR, "fixtures.json"), encoding="utf-8") as f:
    fixtures_raw = json.load(f)
with open(os.path.join(DATA_DIR, "player_details.json"), encoding="utf-8") as f:
    player_details = json.load(f)

pos_map  = {t["id"]: t["singular_name_short"] for t in bs["element_types"]}
team_map = {t["id"]: t["short_name"]          for t in bs["teams"]}

# Fixture-hakemisto: fixture_id → {team_h_difficulty, team_a_difficulty}
fixture_fdr = {
    fix["id"]: {
        "h_diff": fix["team_h_difficulty"],
        "a_diff": fix["team_a_difficulty"],
    }
    for fix in fixtures_raw
}

players_meta = {
    p["id"]: {
        "name":     p["web_name"],
        "team":     team_map.get(p["team"], "?"),
        "position": pos_map.get(p["element_type"], "?"),
    }
    for p in bs["elements"]
}
print(f"   Pelaajia: {len(players_meta)}  |  Otteluita: {len(fixture_fdr)}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. RAKENNA ANALYYSI-DATASET
# ═══════════════════════════════════════════════════════════════════════════
print("\n[2/5] Rakennetaan analyysidataset...")
records = []
for pid_str, detail in player_details.items():
    pid = int(pid_str)
    meta = players_meta.get(pid, {})
    for h in detail.get("history", []):
        fix_id   = h["fixture"]
        fdr_info = fixture_fdr.get(fix_id)
        if not fdr_info:
            continue
        fdr = fdr_info["h_diff"] if h["was_home"] else fdr_info["a_diff"]
        records.append({
            "player_id":  pid,
            "name":       meta.get("name", "?"),
            "team":       meta.get("team", "?"),
            "position":   meta.get("position", "?"),
            "gw":         h["round"],
            "fixture_id": fix_id,
            "fdr":        fdr,
            "points":     h["total_points"],
            "minutes":    h["minutes"],
            "was_home":   h["was_home"],
            "goals":      h["goals_scored"],
            "assists":    h["assists"],
            "cs":         h["clean_sheets"],
            "bonus":      h["bonus"],
        })

df = pd.DataFrame(records)
print(f"   Rivejä (kaikki pelit): {len(df):,}")

# Suodata: vain pelatut ottelut (minutes > 0)
df_played = df[df["minutes"] > 0].copy()
print(f"   Rivejä (pelanneet, min>0): {len(df_played):,}")
print(f"   FDR-jakauma:\n{df_played['fdr'].value_counts().sort_index().to_string()}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. TILASTOLLISET LASKELMAT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[3/5] Lasketaan tilastot...")

def corr_stats(data, label=""):
    x = data["fdr"].values
    y = data["points"].values
    pearson_r,  pearson_p  = stats.pearsonr(x, y)
    spearman_r, spearman_p = stats.spearmanr(x, y)
    return {
        "label":      label,
        "n":          len(data),
        "pearson_r":  pearson_r,
        "pearson_p":  pearson_p,
        "spearman_r": spearman_r,
        "spearman_p": spearman_p,
    }

# 3a. Kokonaiskorrelaatio
overall = corr_stats(df_played, "Kaikki pelaajat")
print(f"\n   Kokonais Pearson r = {overall['pearson_r']:.4f}  (p={overall['pearson_p']:.2e})")
print(f"   Kokonais Spearman rho = {overall['spearman_r']:.4f}  (p={overall['spearman_p']:.2e})")

# 3b. Asemittainen korrelaatio
pos_corr = [corr_stats(df_played[df_played["position"] == pos], pos) for pos in POSITIONS]

# 3c. Koti/vieras
home_corr = corr_stats(df_played[df_played["was_home"]], "Koti")
away_corr = corr_stats(df_played[~df_played["was_home"]], "Vieras")

# 3d. Pisteet FDR-tasoa kohti (mean, median, std, n)
fdr_stats = (
    df_played.groupby("fdr")["points"]
    .agg(["mean", "median", "std", "count"])
    .rename(columns={"mean": "Keskiarvo", "median": "Mediaani",
                     "std": "Std", "count": "N"})
    .reset_index()
)

# 3e. Asema × FDR pivot
pos_fdr_pivot = (
    df_played.groupby(["position", "fdr"])["points"]
    .mean()
    .unstack("fdr")
    .reindex(POSITIONS)
)

# 3f. Koti/vieras × FDR
home_fdr = df_played.groupby(["was_home", "fdr"])["points"].mean().unstack("fdr")

# 3g. Lineaarinen regressio per asema
regression = {}
for pos in POSITIONS:
    sub = df_played[df_played["position"] == pos]
    slope, intercept, r, p, se = stats.linregress(sub["fdr"], sub["points"])
    regression[pos] = {"slope": slope, "intercept": intercept, "r": r, "p": p}

print("\n   Asemittainen korrelaatio (Pearson r):")
for c in pos_corr:
    sig = "***" if c["pearson_p"] < 0.001 else ("**" if c["pearson_p"] < 0.01 else ("*" if c["pearson_p"] < 0.05 else ""))
    print(f"   {c['label']:4s}: r={c['pearson_r']:+.4f}  {sig}")

# ═══════════════════════════════════════════════════════════════════════════
# 4. VISUALISOINNIT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[4/5] Piirretään kuvaajat...")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3,
    "figure.facecolor": "white",
})

# ── Kuva 1: Pääyhteenveto (2×2) ────────────────────────────────────────────
fig1, axes = plt.subplots(2, 2, figsize=(14, 10))
fig1.suptitle("FDR vs. Pisteet — Yhteenveto", fontsize=14, fontweight="bold", y=0.98)

# 1A: Boxplot kaikki asema × FDR
ax = axes[0, 0]
fdr_levels = sorted(df_played["fdr"].unique())
box_data = [df_played[df_played["fdr"] == f]["points"].values for f in fdr_levels]
bp = ax.boxplot(box_data, labels=fdr_levels, patch_artist=True,
                medianprops=dict(color="black", linewidth=2),
                flierprops=dict(marker=".", markersize=2, alpha=0.3))
for patch, fdr in zip(bp["boxes"], fdr_levels):
    patch.set_facecolor(FDR_COLORS.get(fdr, "#CCCCCC"))
    patch.set_alpha(0.8)
ax.set_xlabel("FDR-taso")
ax.set_ylabel("Pisteet per ottelu")
ax.set_title("Pisteiden jakauma FDR-tasoittain (kaikki)")
means = [df_played[df_played["fdr"] == f]["points"].mean() for f in fdr_levels]
ax.plot(range(1, len(fdr_levels)+1), means, "D--", color="#333333",
        markersize=6, label="Keskiarvo", zorder=5)
ax.legend(fontsize=8)

# 1B: Asema × FDR heatmap (keskiarvopisteet)
ax = axes[0, 1]
hm_data = pos_fdr_pivot.values
im = ax.imshow(hm_data, cmap="RdYlGn", aspect="auto",
               vmin=hm_data[~np.isnan(hm_data)].min(),
               vmax=hm_data[~np.isnan(hm_data)].max())
ax.set_xticks(range(len(fdr_levels)))
ax.set_xticklabels([f"FDR {f}" for f in fdr_levels])
ax.set_yticks(range(len(POSITIONS)))
ax.set_yticklabels(POSITIONS)
ax.set_title("Keskiarvopisteet: Asema × FDR")
for i in range(len(POSITIONS)):
    for j in range(len(fdr_levels)):
        val = hm_data[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=9, fontweight="bold",
                    color="black" if 2 < val < 6 else "white")
plt.colorbar(im, ax=ax, label="Keskim. pisteet")

# 1C: Viivakuva asemittain – FDR vs keskiarvopisteet
ax = axes[1, 0]
for pos in POSITIONS:
    sub = df_played[df_played["position"] == pos]
    means_pos = sub.groupby("fdr")["points"].mean()
    ax.plot(means_pos.index, means_pos.values, "o-",
            color=POS_COLORS[pos], linewidth=2, markersize=7, label=pos)
    # Regressioviiva
    reg = regression[pos]
    x_line = np.array(fdr_levels)
    y_line = reg["intercept"] + reg["slope"] * x_line
    ax.plot(x_line, y_line, "--", color=POS_COLORS[pos], linewidth=1, alpha=0.5)
ax.set_xlabel("FDR-taso")
ax.set_ylabel("Keskim. pisteet")
ax.set_title("Keskim. pisteet FDR:n mukaan asemittain\n(katkoviiva = lineaarinen trendi)")
ax.legend(fontsize=8)
ax.set_xticks(fdr_levels)

# 1D: Korrelaatiokertoimet (Pearson r) palkkikuva
ax = axes[1, 1]
labels_all = ["Kaikki"] + POSITIONS + ["Koti", "Vieras"]
r_values   = (
    [overall["pearson_r"]]
    + [c["pearson_r"] for c in pos_corr]
    + [home_corr["pearson_r"], away_corr["pearson_r"]]
)
p_values = (
    [overall["pearson_p"]]
    + [c["pearson_p"] for c in pos_corr]
    + [home_corr["pearson_p"], away_corr["pearson_p"]]
)
colors_bar = (
    ["#555555"]
    + [POS_COLORS[p] for p in POSITIONS]
    + ["#1E88E5", "#E53935"]
)
bars = ax.barh(labels_all, r_values, color=colors_bar, alpha=0.85, height=0.6)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Pearson r")
ax.set_title("Korrelaatio (FDR vs pisteet)\n*** p<0.001  ** p<0.01  * p<0.05")
for bar, r, p in zip(bars, r_values, p_values):
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    ax.text(r + (0.001 if r >= 0 else -0.001), bar.get_y() + bar.get_height()/2,
            f"  {r:+.4f} {sig}", va="center", fontsize=8,
            ha="left" if r >= 0 else "right")
ax.set_xlim(min(r_values) - 0.08, max(r_values) + 0.12)

plt.tight_layout()
img1_path = os.path.join(IMG_DIR, "fdr_analysis_1_overview.png")
fig1.savefig(img1_path, dpi=150, bbox_inches="tight")
plt.close(fig1)
print(f"   Kuva 1 tallennettu: {os.path.basename(img1_path)}")

# ── Kuva 2: Asemittaiset boxplotit ─────────────────────────────────────────
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 9))
fig2.suptitle("FDR vs. Pisteet asemittain", fontsize=13, fontweight="bold")

for ax, pos in zip(axes2.flatten(), POSITIONS):
    sub = df_played[df_played["position"] == pos]
    bdata = [sub[sub["fdr"] == f]["points"].values for f in fdr_levels]
    bp = ax.boxplot(bdata, labels=fdr_levels, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2),
                    flierprops=dict(marker=".", markersize=2, alpha=0.3))
    for patch, fdr in zip(bp["boxes"], fdr_levels):
        patch.set_facecolor(FDR_COLORS.get(fdr, "#CCCCCC"))
        patch.set_alpha(0.85)
    # Regressiosuora
    reg = regression[pos]
    x_r = np.array([fdr_levels[0] - 0.3, fdr_levels[-1] + 0.3])
    y_r = reg["intercept"] + reg["slope"] * x_r
    ax.plot([1, len(fdr_levels)], y_r, "k--", linewidth=1.5, alpha=0.7, label=f"r={reg['r']:+.3f}")
    means_pos = [sub[sub["fdr"] == f]["points"].mean() for f in fdr_levels]
    ax.plot(range(1, len(fdr_levels)+1), means_pos, "D",
            color=POS_COLORS[pos], markersize=8, zorder=5)
    ax.set_title(f"{pos}  (n={len(sub):,})", fontsize=11, fontweight="bold",
                 color=POS_COLORS[pos])
    ax.set_xlabel("FDR-taso")
    ax.set_ylabel("Pisteet")
    ax.legend(fontsize=8)

plt.tight_layout()
img2_path = os.path.join(IMG_DIR, "fdr_analysis_2_by_position.png")
fig2.savefig(img2_path, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"   Kuva 2 tallennettu: {os.path.basename(img2_path)}")

# ── Kuva 3: Koti vs. vieras + piste-FDR scatter ────────────────────────────
fig3, axes3 = plt.subplots(1, 2, figsize=(13, 6))
fig3.suptitle("Koti/Vieras & Pisteiden hajonta FDR:n mukaan",
              fontsize=13, fontweight="bold")

# 3A: Koti vs vieras boxplot
ax = axes3[0]
width = 0.35
x_pos = np.arange(len(fdr_levels))
df_home = df_played[df_played["was_home"]]
df_away = df_played[~df_played["was_home"]]
means_home = [df_home[df_home["fdr"] == f]["points"].mean() for f in fdr_levels]
means_away = [df_away[df_away["fdr"] == f]["points"].mean() for f in fdr_levels]
std_home   = [df_home[df_home["fdr"] == f]["points"].std()  for f in fdr_levels]
std_away   = [df_away[df_away["fdr"] == f]["points"].std()  for f in fdr_levels]
bars_h = ax.bar(x_pos - width/2, means_home, width, label="Koti", color="#1E88E5",
                yerr=std_home, capsize=4, error_kw={"alpha": 0.5}, alpha=0.85)
bars_a = ax.bar(x_pos + width/2, means_away, width, label="Vieras", color="#E53935",
                yerr=std_away, capsize=4, error_kw={"alpha": 0.5}, alpha=0.85)
ax.set_xticks(x_pos)
ax.set_xticklabels([f"FDR {f}" for f in fdr_levels])
ax.set_ylabel("Keskim. pisteet")
ax.set_title("Keskim. pisteet: Koti vs. Vieras\n(virhepalkit = ±1 std)")
ax.legend()

# 3B: Violinplot kaikki
ax = axes3[1]
vp_data = [df_played[df_played["fdr"] == f]["points"].values for f in fdr_levels]
vp = ax.violinplot(vp_data, positions=fdr_levels, showmedians=True, showmeans=False)
for i, (body, fdr) in enumerate(zip(vp["bodies"], fdr_levels)):
    body.set_facecolor(FDR_COLORS.get(fdr, "#CCCCCC"))
    body.set_alpha(0.75)
vp["cmedians"].set_color("black")
vp["cmedians"].set_linewidth(2)
ax.set_xlabel("FDR-taso")
ax.set_ylabel("Pisteet")
ax.set_title("Pisteiden jakaumamuoto FDR-tasoittain\n(violinplot, mediaani merkitty)")
fdr_patches = [mpatches.Patch(color=FDR_COLORS[f], label=f"FDR {f}") for f in fdr_levels]
ax.legend(handles=fdr_patches, fontsize=8)

plt.tight_layout()
img3_path = os.path.join(IMG_DIR, "fdr_analysis_3_home_away.png")
fig3.savefig(img3_path, dpi=150, bbox_inches="tight")
plt.close(fig3)
print(f"   Kuva 3 tallennettu: {os.path.basename(img3_path)}")

# ═══════════════════════════════════════════════════════════════════════════
# 5. EXCEL-RAPORTTI
# ═══════════════════════════════════════════════════════════════════════════
print("\n[5/5] Kirjoitetaan Excel-raportti...")

wb = Workbook()

# Tyylit
H1 = Font(bold=True, color="FFFFFF", size=12)
H2 = Font(bold=True, color="FFFFFF", size=10)
H3 = Font(bold=True, size=10)
NORM = Font(size=9)
DARK_FILL  = PatternFill("solid", fgColor="1F3864")
MED_FILL   = PatternFill("solid", fgColor="2E75B6")
GREEN_FILL = PatternFill("solid", fgColor="375623")
ALT_FILL   = PatternFill("solid", fgColor="D9E1F2")
YELL_FILL  = PatternFill("solid", fgColor="FFFF99")
thin = Side(style="thin", color="BBBBBB")
brd  = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal="center", vertical="center")
left   = Alignment(horizontal="left",   vertical="center")

def style_header(ws, row, col, value, fill=DARK_FILL, font=H2, align=center):
    c = ws.cell(row=row, column=col, value=value)
    c.fill = fill; c.font = font; c.alignment = align; c.border = brd
    return c

def style_cell(ws, row, col, value, bold=False, fmt=None, fill=None, align=center):
    c = ws.cell(row=row, column=col, value=value)
    c.font = H3 if bold else NORM
    c.alignment = align; c.border = brd
    if fill: c.fill = fill
    if fmt:  c.number_format = fmt
    return c

# ────────────────────────────────────────────────────────────────────────────
# Sheet 1: Yhteenveto
# ────────────────────────────────────────────────────────────────────────────
ws1 = wb.active
ws1.title = "Yhteenveto"

ws1.merge_cells("A1:H1")
t = ws1["A1"]
t.value = "FPL FDR–Pisteet Korrelaatioanalyysi"
t.font = Font(bold=True, size=14, color="FFFFFF")
t.fill = DARK_FILL; t.alignment = center

ws1.row_dimensions[1].height = 30

# ── Korrelaatiotaulukko ──────────────────────────────────────────────────
ws1.cell(row=3, column=1, value="KORRELAATIOKERTOIMET").font = H3
ws1.merge_cells("A3:H3")
ws1["A3"].fill = MED_FILL
ws1["A3"].font = H1
ws1["A3"].alignment = center

headers_corr = ["Ryhmä", "N", "Pearson r", "p-arvo", "Spearman rho", "p-arvo (S)", "Merkitsevyys", "Tulkinta"]
for j, h in enumerate(headers_corr, 1):
    style_header(ws1, 4, j, h)

all_corrs = [overall] + pos_corr + [home_corr, away_corr]
for i, c in enumerate(all_corrs):
    row = 5 + i
    fill = ALT_FILL if i % 2 == 0 else None
    sig = ("*** p<0.001" if c["pearson_p"] < 0.001
           else ("** p<0.01" if c["pearson_p"] < 0.01
           else ("* p<0.05" if c["pearson_p"] < 0.05 else "ns")))
    direction = ("Negatiivinen ✓ (korkeampi FDR → vähemmän pisteitä)"
                 if c["pearson_r"] < -0.02
                 else ("Positiivinen (korkeampi FDR → enemmän pisteitä)"
                 if c["pearson_r"] > 0.02 else "Ei selvää yhteyttä"))
    data = [c["label"], c["n"], c["pearson_r"], c["pearson_p"],
            c["spearman_r"], c["spearman_p"], sig, direction]
    for j, val in enumerate(data, 1):
        fmt = "0.0000" if j in (3, 5) else ("0.000E+00" if j in (4, 6) else None)
        style_cell(ws1, row, j, val, fill=fill, fmt=fmt,
                   align=left if j in (1, 8) else center)

# ── Pisteet FDR-tasoittain ────────────────────────────────────────────────
r_start = 5 + len(all_corrs) + 2
ws1.merge_cells(f"A{r_start}:H{r_start}")
ws1[f"A{r_start}"].value = "PISTEET FDR-TASOITTAIN (vain pelanneet, min>0)"
ws1[f"A{r_start}"].font = H1
ws1[f"A{r_start}"].fill = MED_FILL
ws1[f"A{r_start}"].alignment = center

headers_fdr = ["FDR", "N (ottelut)", "Keskim. pisteet", "Mediaani", "Std", "Min", "Maks", "Tulkinta"]
for j, h in enumerate(headers_fdr, 1):
    style_header(ws1, r_start + 1, j, h)

fdr_interp = {1: "Helppo ottelu", 2: "Melko helppo", 3: "Neutraali",
              4: "Melko vaikea", 5: "Vaikea ottelu"}
for i, (_, row_data) in enumerate(fdr_stats.iterrows()):
    fdr_val = int(row_data["fdr"])
    sub = df_played[df_played["fdr"] == fdr_val]["points"]
    row = r_start + 2 + i
    fdr_fill = PatternFill("solid", fgColor=FDR_COLORS[fdr_val].lstrip("#"))
    vals = [fdr_val, int(row_data["N"]), row_data["Keskiarvo"],
            row_data["Mediaani"], row_data["Std"],
            sub.min(), sub.max(), fdr_interp[fdr_val]]
    for j, val in enumerate(vals, 1):
        fmt = "0.00" if j in (3, 4, 5) else None
        c = style_cell(ws1, row, j, val, fmt=fmt, align=left if j == 8 else center)
        if j == 1:
            c.fill = fdr_fill
            c.font = Font(bold=True, size=10)

# ── Asema × FDR pivot ────────────────────────────────────────────────────
r2 = r_start + 2 + len(fdr_stats) + 2
ws1.merge_cells(f"A{r2}:H{r2}")
ws1[f"A{r2}"].value = "KESKIM. PISTEET: ASEMA × FDR"
ws1[f"A{r2}"].font = H1
ws1[f"A{r2}"].fill = MED_FILL
ws1[f"A{r2}"].alignment = center

style_header(ws1, r2 + 1, 1, "Asema")
for j, fdr_val in enumerate(fdr_levels, 2):
    style_header(ws1, r2 + 1, j, f"FDR {fdr_val}",
                 fill=PatternFill("solid", fgColor=FDR_COLORS[fdr_val].lstrip("#")))
style_header(ws1, r2 + 1, 2 + len(fdr_levels), "Muutos FDR1→5", fill=GREEN_FILL)

for i, pos in enumerate(POSITIONS):
    row = r2 + 2 + i
    pos_fill = PatternFill("solid", fgColor=POS_COLORS[pos].lstrip("#"))
    style_cell(ws1, row, 1, pos, bold=True, fill=pos_fill, align=center)
    vals = pos_fdr_pivot.loc[pos].values
    for j, val in enumerate(vals, 2):
        style_cell(ws1, row, j, round(float(val), 2), fmt="0.00",
                   fill=ALT_FILL if i % 2 == 0 else None)
    # Muutos FDR1→5
    delta = vals[-1] - vals[0]
    d_fill = PatternFill("solid", fgColor="FFB3B3") if delta > 0 else PatternFill("solid", fgColor="B3FFB3")
    style_cell(ws1, row, 2 + len(fdr_levels), round(float(delta), 2), fmt="+0.00;-0.00", fill=d_fill)

# Sarakeleveydet
col_widths = [18, 12, 14, 12, 10, 14, 22, 48]
for j, w in enumerate(col_widths, 1):
    ws1.column_dimensions[get_column_letter(j)].width = w

# ────────────────────────────────────────────────────────────────────────────
# Sheet 2: Regressioanalyysi
# ────────────────────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Regressio")
ws2.merge_cells("A1:F1")
ws2["A1"].value = "Lineaarinen regressio: Pisteet ~ FDR  (pelanneet pelaajat)"
ws2["A1"].font = H1; ws2["A1"].fill = DARK_FILL; ws2["A1"].alignment = center
ws2.row_dimensions[1].height = 28

headers_reg = ["Asema", "Kulmakerr. (slope)", "Vakio (intercept)",
               "Pearson r", "R²", "p-arvo"]
for j, h in enumerate(headers_reg, 1):
    style_header(ws2, 2, j, h)

for i, pos in enumerate(POSITIONS):
    reg = regression[pos]
    row = 3 + i
    pos_fill = PatternFill("solid", fgColor=POS_COLORS[pos].lstrip("#"))
    vals = [pos, reg["slope"], reg["intercept"], reg["r"], reg["r"]**2, reg["p"]]
    fmts = [None, "0.0000", "0.0000", "0.0000", "0.0000", "0.000E+00"]
    for j, (val, fmt) in enumerate(zip(vals, fmts), 1):
        c = style_cell(ws2, row, j, val if not fmt or j == 1 else round(float(val), 6),
                       fmt=fmt, fill=pos_fill if j == 1 else (ALT_FILL if i % 2 == 0 else None))

# Seliteteksti
ws2.cell(row=8, column=1, value="Tulkinta:").font = H3
note = ("Negatiivinen kulmakertoimen arvo tarkoittaa, että pisteet laskevat FDR:n kasvaessa. "
        "Esim. slope = -0.20 tarkoittaa: jokaisesta FDR-yksikön noususta → ~0.20 pistettä vähemmän ottelua kohti. "
        "R² kertoo selitysasteen: kuinka suuri osuus pisteiden vaihtelusta selittyy FDR:llä.")
ws2.merge_cells("B8:F10")
c = ws2["B8"]
c.value = note; c.alignment = Alignment(wrap_text=True, vertical="top")
c.font = Font(size=9); c.border = brd

for j, w in enumerate([12, 18, 18, 12, 10, 14], 1):
    ws2.column_dimensions[get_column_letter(j)].width = w

# ────────────────────────────────────────────────────────────────────────────
# Sheet 3: Raakadata (näyte)
# ────────────────────────────────────────────────────────────────────────────
ws3 = wb.create_sheet("Raakadata (näyte)")
sample = df_played.sort_values("points", ascending=False).head(10000)
cols_out = ["name", "team", "position", "gw", "fdr", "points", "minutes",
            "was_home", "goals", "assists", "cs", "bonus"]
headers_raw = ["Pelaaja", "Joukkue", "Asema", "GW", "FDR", "Pisteet", "Minuutit",
               "Koti?", "Maalit", "Syötöt", "CS", "Bonus"]

ws3.merge_cells(f"A1:{get_column_letter(len(cols_out))}1")
ws3["A1"].value = f"Raakadata — TOP 10 000 suoritusta pisteiden mukaan (kaikista {len(df_played):,} pelatusta ottelusta)"
ws3["A1"].font = H1; ws3["A1"].fill = DARK_FILL; ws3["A1"].alignment = center

for j, h in enumerate(headers_raw, 1):
    style_header(ws3, 2, j, h)

for i, (_, row_data) in enumerate(sample.iterrows()):
    row = 3 + i
    fill = ALT_FILL if i % 2 == 0 else None
    for j, col in enumerate(cols_out, 1):
        val = row_data[col]
        if col == "fdr":
            c_fill = PatternFill("solid", fgColor=FDR_COLORS.get(int(val), "#CCCCCC").lstrip("#"))
        else:
            c_fill = fill
        style_cell(ws3, row, j, val, fill=c_fill,
                   align=left if j in (1, 2, 3) else center)

raw_widths = [16, 8, 7, 5, 5, 8, 9, 7, 7, 7, 5, 6]
for j, w in enumerate(raw_widths, 1):
    ws3.column_dimensions[get_column_letter(j)].width = w
ws3.freeze_panes = "A3"

# ────────────────────────────────────────────────────────────────────────────
# Sheet 4: Kuvaajat
# ────────────────────────────────────────────────────────────────────────────
ws4 = wb.create_sheet("Kuvaajat")
ws4.merge_cells("A1:Z1")
ws4["A1"].value = "Visualisoinnit — FDR vs. Pisteet"
ws4["A1"].font = H1; ws4["A1"].fill = DARK_FILL; ws4["A1"].alignment = center

for img_path, anchor in [
    (img1_path, "A3"),
    (img2_path, "A58"),
    (img3_path, "A113"),
]:
    if os.path.exists(img_path):
        img_obj = XLImage(img_path)
        img_obj.width  = 900
        img_obj.height = int(img_obj.width * 0.72)
        ws4.add_image(img_obj, anchor)

wb.save(OUTPUT_XLS)
size_kb = os.path.getsize(OUTPUT_XLS) / 1024
print(f"   Excel-raportti tallennettu: {OUTPUT_XLS}")
print(f"   Koko: {size_kb:.0f} KB")

# ═══════════════════════════════════════════════════════════════════════════
# LOPPUYHTEENVETO
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("ANALYYSIN YHTEENVETO")
print("=" * 60)
print(f"\nDatapisteitä: {len(df_played):,} ottelua ({len(players_meta)} pelaajaa, 38 GW)")
print(f"\nKokonais Pearson r  = {overall['pearson_r']:+.4f}  (p={overall['pearson_p']:.2e})")
print(f"Kokonais Spearman rho = {overall['spearman_r']:+.4f}  (p={overall['spearman_p']:.2e})")
print(f"\nKeskiarvopisteet FDR-tasoittain:")
for _, row_data in fdr_stats.iterrows():
    bar = "█" * int(row_data["Keskiarvo"] * 4)
    print(f"  FDR {int(row_data['fdr'])}: {row_data['Keskiarvo']:.2f} pts  {bar}")
print(f"\nAsemittainen korrelaatio:")
for c, pos in zip(pos_corr, POSITIONS):
    sig = "***" if c["pearson_p"] < 0.001 else ("**" if c["pearson_p"] < 0.01 else ("*" if c["pearson_p"] < 0.05 else "ns"))
    reg = regression[pos]
    print(f"  {pos}: r={c['pearson_r']:+.4f} {sig}  |  slope={reg['slope']:+.4f} pts/FDR-yksikkö")
print(f"\nTiedostot:")
for fname in ["fdr_analysis_1_overview.png", "fdr_analysis_2_by_position.png",
              "fdr_analysis_3_home_away.png", "fdr_correlation_analysis.xlsx"]:
    fpath = os.path.join(DATA_DIR, fname)
    if os.path.exists(fpath):
        print(f"  ✓ {fname} ({os.path.getsize(fpath)/1024:.0f} KB)")
print("\nValmis!")
