"""
FPL Pistetekijäanalyysi — Mikä vaikuttaa pelaajan pisteisiin?
=============================================================
- Pearson-korrelaatio kaikille muuttujille
- OLS-monimuuttujaregressio
- Random Forest -tärkeys
- Asemittainen vertailu
- Excel-raportti + PNG-kuvaajat
"""

import json, os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.inspection import permutation_importance
import statsmodels.api as sm
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
warnings.filterwarnings("ignore")

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
OUTPUT_XLS = os.path.join(DATA_DIR, "point_factors_analysis.xlsx")

POS_COLORS = {"GKP": "#FFD700", "DEF": "#2196F3", "MID": "#4CAF50", "FWD": "#FF5722"}
POSITIONS  = ["GKP", "DEF", "MID", "FWD"]

# Muuttujaryhmät — mitä analysoidaan
FEATURE_GROUPS = {
    "Peliaika":        ["minutes", "starts"],
    "Hyokkays":        ["goals_scored", "assists", "expected_goals",
                        "expected_assists", "expected_goal_involvements",
                        "creativity", "threat"],
    "Puolustus":       ["clean_sheets", "goals_conceded", "saves",
                        "clearances_blocks_interceptions", "recoveries",
                        "tackles", "defensive_contribution",
                        "expected_goals_conceded"],
    "Kurinpito":       ["yellow_cards", "red_cards", "own_goals",
                        "penalties_missed", "penalties_saved"],
    "Laatu/bonus":     ["influence", "ict_index", "bps", "bonus"],
    "Konteksti":       ["was_home", "fdr", "value"],
}
ALL_FEATURES = [f for grp in FEATURE_GROUPS.values() for f in grp]

# Värit ryhmittäin
GROUP_COLORS = {
    "Peliaika":    "#607D8B",
    "Hyokkays":    "#E53935",
    "Puolustus":   "#1E88E5",
    "Kurinpito":   "#FB8C00",
    "Laatu/bonus": "#8E24AA",
    "Konteksti":   "#43A047",
}
FEAT_COLOR = {f: GROUP_COLORS[g] for g, feats in FEATURE_GROUPS.items() for f in feats}

print("=" * 65)
print("FPL Pistetekijäanalyysi")
print("=" * 65)

# ═══════════════════════════════════════════════════════════════════════════
# 1. RAKENNA DATASET
# ═══════════════════════════════════════════════════════════════════════════
print("\n[1/6] Ladataan ja rakennetaan dataset...")
with open(os.path.join(DATA_DIR, "bootstrap_static.json"), encoding="utf-8") as f:
    bs = json.load(f)
with open(os.path.join(DATA_DIR, "fixtures.json"), encoding="utf-8") as f:
    fixtures_raw = json.load(f)
with open(os.path.join(DATA_DIR, "player_details.json"), encoding="utf-8") as f:
    player_details = json.load(f)

pos_map  = {t["id"]: t["singular_name_short"] for t in bs["element_types"]}
team_map = {t["id"]: t["short_name"]          for t in bs["teams"]}
fixture_fdr = {
    fix["id"]: {"h": fix["team_h_difficulty"], "a": fix["team_a_difficulty"]}
    for fix in fixtures_raw
}
players_meta = {
    p["id"]: {"name": p["web_name"],
               "team": team_map.get(p["team"], "?"),
               "position": pos_map.get(p["element_type"], "?")}
    for p in bs["elements"]
}

records = []
for pid_str, detail in player_details.items():
    pid  = int(pid_str)
    meta = players_meta.get(pid, {})
    for h in detail.get("history", []):
        fdr_info = fixture_fdr.get(h["fixture"])
        if not fdr_info:
            continue
        fdr = fdr_info["h"] if h["was_home"] else fdr_info["a"]
        rec = {k: (float(v) if isinstance(v, str) else v)
               for k, v in h.items()
               if k not in ["element","fixture","kickoff_time","modified",
                            "opponent_team","team_h_score","team_a_score",
                            "transfers_balance","transfers_in","transfers_out",
                            "selected","round"]}
        rec["fdr"]      = fdr
        rec["position"] = meta.get("position", "?")
        rec["name"]     = meta.get("name", "?")
        rec["team"]     = meta.get("team", "?")
        records.append(rec)

df = pd.DataFrame(records)
df_played = df[df["minutes"] > 0].copy()

# Varmista numeerisuus
for col in ALL_FEATURES + ["total_points"]:
    if col in df_played.columns:
        df_played[col] = pd.to_numeric(df_played[col], errors="coerce")
df_played = df_played.dropna(subset=["total_points"])

print(f"   Otteluita: {len(df_played):,}  |  Pelaajia: {df_played['name'].nunique()}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. PEARSON-KORRELAATIOT
# ═══════════════════════════════════════════════════════════════════════════
print("\n[2/6] Lasketaan korrelaatiot...")

corr_rows = []
for feat in ALL_FEATURES:
    if feat not in df_played.columns:
        continue
    sub = df_played[[feat, "total_points"]].dropna()
    if sub[feat].std() == 0 or len(sub) < 30:
        continue
    r, p = stats.pearsonr(sub[feat], sub["total_points"])
    group = next(g for g, fs in FEATURE_GROUPS.items() if feat in fs)
    corr_rows.append({"feature": feat, "group": group,
                      "pearson_r": r, "p_value": p, "n": len(sub)})

corr_df = (pd.DataFrame(corr_rows)
             .assign(abs_r=lambda x: x["pearson_r"].abs())
             .sort_values("abs_r", ascending=False)
             .reset_index(drop=True))

print(f"\n   TOP 10 korrelaatiot total_points kanssa:")
for _, row in corr_df.head(10).iterrows():
    bar = "+" if row["pearson_r"] > 0 else "-"
    bar *= int(abs(row["pearson_r"]) * 30)
    print(f"   {row['feature']:35s} r={row['pearson_r']:+.4f}  {bar[:20]}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. OLS MONIMUUTTUJAREGRESSIO
# ═══════════════════════════════════════════════════════════════════════════
print("\n[3/6] OLS-regressio...")

# Käytä suoria pelitapahtumia (ei bonus/bps jotka ovat johdettu suureita)
ols_features = [f for f in ALL_FEATURES
                if f not in ["bonus", "bps", "ict_index"]
                and f in df_played.columns]

ols_df = df_played[ols_features + ["total_points"]].dropna()
ols_df = ols_df.apply(pd.to_numeric, errors="coerce").dropna()
X = sm.add_constant(ols_df[ols_features].astype(float))
y = ols_df["total_points"].astype(float)
ols_model = sm.OLS(y, X).fit()

ols_results = pd.DataFrame({
    "feature":    ols_model.params.index,
    "coef":       ols_model.params.values,
    "std_err":    ols_model.bse.values,
    "t_stat":     ols_model.tvalues.values,
    "p_value":    ols_model.pvalues.values,
    "ci_low":     ols_model.conf_int()[0].values,
    "ci_high":    ols_model.conf_int()[1].values,
}).query("feature != 'const'").sort_values("coef", key=abs, ascending=False)

print(f"   R² = {ols_model.rsquared:.4f}  |  Adj.R² = {ols_model.rsquared_adj:.4f}")
print(f"   F-stat = {ols_model.fvalue:.1f}  (p={ols_model.f_pvalue:.2e})")

# ═══════════════════════════════════════════════════════════════════════════
# 4. RANDOM FOREST -TÄRKEYS
# ═══════════════════════════════════════════════════════════════════════════
print("\n[4/6] Random Forest feature importance...")

rf_features = [f for f in ALL_FEATURES if f in df_played.columns]
rf_df = df_played[rf_features + ["total_points"]].dropna()

# Positio numeroksi
pos_enc = LabelEncoder()
df_played["pos_enc"] = pos_enc.fit_transform(df_played["position"].fillna("?"))
rf_features_ext = rf_features  # Ei positiota tässä, analysoidaan erikseen

rf = RandomForestRegressor(n_estimators=200, max_depth=8,
                            min_samples_leaf=5, random_state=42, n_jobs=-1)
rf.fit(rf_df[rf_features], rf_df["total_points"])

rf_imp = pd.DataFrame({
    "feature":    rf_features,
    "importance": rf.feature_importances_,
}).sort_values("importance", ascending=False).reset_index(drop=True)

rf_imp["group"] = rf_imp["feature"].map(
    lambda f: next((g for g, fs in FEATURE_GROUPS.items() if f in fs), "Muu"))

print(f"   RF R² (train) = {rf.score(rf_df[rf_features], rf_df['total_points']):.4f}")
print(f"\n   TOP 10 RF-tärkeys:")
for _, row in rf_imp.head(10).iterrows():
    bar = "█" * int(row["importance"] * 200)
    print(f"   {row['feature']:35s} {row['importance']:.4f}  {bar[:25]}")

# ═══════════════════════════════════════════════════════════════════════════
# 5. ASEMITTAINEN KORRELAATIO
# ═══════════════════════════════════════════════════════════════════════════
print("\n[5/6] Asemittainen analyysi...")

pos_corr_dict = {}
key_features = corr_df.head(12)["feature"].tolist()

for pos in POSITIONS:
    sub = df_played[df_played["position"] == pos]
    pos_corr_dict[pos] = {}
    for feat in key_features:
        if feat not in sub.columns:
            continue
        s = sub[[feat, "total_points"]].dropna()
        if s[feat].std() == 0 or len(s) < 20:
            continue
        r, p = stats.pearsonr(s[feat], s["total_points"])
        pos_corr_dict[pos][feat] = r

pos_corr_pivot = pd.DataFrame(pos_corr_dict).reindex(key_features)

# ═══════════════════════════════════════════════════════════════════════════
# 6. VISUALISOINNIT
# ═══════════════════════════════════════════════════════════════════════════
print("\n   Piirretään kuvaajat...")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25,
    "figure.facecolor": "white",
})

# ── Kuva 1: Pearson-korrelaatiot + RF-tärkeys ──────────────────────────────
fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9))
fig1.suptitle("Mikä vaikuttaa FPL-pisteisiin?\nKaikki muuttujat, pelanneet pelaajat (min>0)",
              fontsize=13, fontweight="bold")

# 1A: Korrelaatiot
plot_df = corr_df.sort_values("pearson_r")
colors1 = [FEAT_COLOR.get(f, "#999999") for f in plot_df["feature"]]
bars = ax1.barh(plot_df["feature"], plot_df["pearson_r"],
                color=colors1, alpha=0.85, height=0.7)
ax1.axvline(0, color="black", linewidth=0.8)
ax1.set_xlabel("Pearson r (korrelaatio total_points kanssa)")
ax1.set_title("Pearson-korrelaatio")
# Arvot palkkeihin
for bar, (_, row) in zip(bars, plot_df.iterrows()):
    x = row["pearson_r"]
    sig = "***" if row["p_value"] < 0.001 else ("**" if row["p_value"] < 0.01 else ("*" if row["p_value"] < 0.05 else ""))
    ax1.text(x + (0.005 if x >= 0 else -0.005), bar.get_y() + bar.get_height()/2,
             f"{x:+.3f}{sig}", va="center", fontsize=7,
             ha="left" if x >= 0 else "right")
# Legenda
legend_patches = [mpatches.Patch(color=c, label=g) for g, c in GROUP_COLORS.items()]
ax1.legend(handles=legend_patches, fontsize=7, loc="lower right")

# 1B: RF-tärkeys
rf_plot = rf_imp.head(15).sort_values("importance")
colors2 = [FEAT_COLOR.get(f, "#999999") for f in rf_plot["feature"]]
ax2.barh(rf_plot["feature"], rf_plot["importance"],
         color=colors2, alpha=0.85, height=0.7)
ax2.set_xlabel("Feature Importance (Random Forest, 200 puuta)")
ax2.set_title("Random Forest -tärkeys (TOP 15)")
for i, (_, row) in enumerate(rf_plot.iterrows()):
    ax2.text(row["importance"] + 0.001, i, f"{row['importance']:.4f}",
             va="center", fontsize=7)
ax2.legend(handles=legend_patches, fontsize=7, loc="lower right")

plt.tight_layout()
img1 = os.path.join(DATA_DIR, "factors_1_correlations_rf.png")
fig1.savefig(img1, dpi=150, bbox_inches="tight")
plt.close(fig1)
print(f"   Kuva 1 OK")

# ── Kuva 2: Asema × tekijä heatmap ────────────────────────────────────────
fig2, ax = plt.subplots(figsize=(13, 7))
fig2.suptitle("Korrelaatio asemittain — TOP 12 tekijää",
              fontsize=13, fontweight="bold")

hm = pos_corr_pivot.values.astype(float)
vmax = max(abs(np.nanmin(hm)), abs(np.nanmax(hm)))
im = ax.imshow(hm, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)
ax.set_xticks(range(len(POSITIONS)))
ax.set_xticklabels(POSITIONS, fontsize=11, fontweight="bold")
ax.set_yticks(range(len(key_features)))
ax.set_yticklabels(pos_corr_pivot.index, fontsize=9)
ax.set_title("Pearson r (tekijä vs. total_points) per asema", pad=10)
for i in range(len(key_features)):
    for j, pos in enumerate(POSITIONS):
        val = hm[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    fontsize=8.5, fontweight="bold",
                    color="white" if abs(val) > vmax * 0.6 else "black")
plt.colorbar(im, ax=ax, label="Pearson r", shrink=0.8)
ax.set_xlabel("Asema", fontsize=10)
ax.set_ylabel("Tekijä", fontsize=10)

plt.tight_layout()
img2 = os.path.join(DATA_DIR, "factors_2_position_heatmap.png")
fig2.savefig(img2, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"   Kuva 2 OK")

# ── Kuva 3: OLS-kertoimet ─────────────────────────────────────────────────
fig3, ax = plt.subplots(figsize=(13, 8))
fig3.suptitle(f"OLS-regressiokertoimet (R²={ols_model.rsquared:.3f})\n"
              "Kuinka monta pistettä yksikön muutos tuo?",
              fontsize=13, fontweight="bold")

ols_plot = ols_results.sort_values("coef")
colors3  = [FEAT_COLOR.get(f, "#999999") for f in ols_plot["feature"]]
sig_mask = ols_plot["p_value"] < 0.05

# Palkit
bars3 = ax.barh(ols_plot["feature"], ols_plot["coef"],
                color=colors3, alpha=0.85, height=0.65,
                xerr=ols_plot["std_err"], capsize=3,
                error_kw={"alpha": 0.5, "elinewidth": 1.2})
# Ei-merkitsevät haalistetaan
for bar, sig in zip(bars3, sig_mask):
    if not sig:
        bar.set_alpha(0.25)

ax.axvline(0, color="black", linewidth=1)
ax.set_xlabel("OLS-kerroin (pisteet per yksikkömuutos)")
ax.set_title(f"Merkitsevät (p<0.05) = tumma  |  Ei-merkitsevät = haalistettu", fontsize=9)

# Arvojen lisäys
for bar, (_, row) in zip(bars3, ols_plot.iterrows()):
    x = row["coef"]
    sig = "***" if row["p_value"] < 0.001 else ("**" if row["p_value"] < 0.01 else ("*" if row["p_value"] < 0.05 else "ns"))
    ax.text(x + (0.02 if x >= 0 else -0.02), bar.get_y() + bar.get_height()/2,
            f"{x:+.3f} {sig}", va="center", fontsize=7.5,
            ha="left" if x >= 0 else "right")

ax.legend(handles=legend_patches, fontsize=8, loc="lower right")
plt.tight_layout()
img3 = os.path.join(DATA_DIR, "factors_3_ols_coefficients.png")
fig3.savefig(img3, dpi=150, bbox_inches="tight")
plt.close(fig3)
print(f"   Kuva 3 OK")

# ── Kuva 4: Scatter TOP 6 tekijää ─────────────────────────────────────────
top6 = corr_df[~corr_df["feature"].isin(["bonus","bps"])].head(6)["feature"].tolist()
fig4, axes4 = plt.subplots(2, 3, figsize=(15, 9))
fig4.suptitle("Pisteiden jakaumat — TOP 6 tekijää (ilman bonus/bps)",
              fontsize=13, fontweight="bold")

for ax, feat in zip(axes4.flatten(), top6):
    sub = df_played[[feat, "total_points", "position"]].dropna()
    color_arr = [POS_COLORS.get(p, "#999999") for p in sub["position"]]
    ax.scatter(sub[feat], sub["total_points"],
               c=color_arr, alpha=0.25, s=8)
    # Trend
    z = np.polyfit(sub[feat], sub["total_points"], 1)
    x_line = np.linspace(sub[feat].min(), sub[feat].max(), 100)
    ax.plot(x_line, np.poly1d(z)(x_line), "k--", linewidth=1.5, alpha=0.8)
    r_val = corr_df[corr_df["feature"] == feat]["pearson_r"].values[0]
    group = corr_df[corr_df["feature"] == feat]["group"].values[0]
    ax.set_title(f"{feat}\n(r={r_val:+.3f}, {group})", fontsize=9)
    ax.set_xlabel(feat, fontsize=8)
    ax.set_ylabel("total_points", fontsize=8)
    # Pieni pos-legenda
    pos_patches = [mpatches.Patch(color=POS_COLORS[p], label=p) for p in POSITIONS]
    ax.legend(handles=pos_patches, fontsize=6, markerscale=0.5)

plt.tight_layout()
img4 = os.path.join(DATA_DIR, "factors_4_scatter_top6.png")
fig4.savefig(img4, dpi=150, bbox_inches="tight")
plt.close(fig4)
print(f"   Kuva 4 OK")

# ═══════════════════════════════════════════════════════════════════════════
# 7. EXCEL-RAPORTTI
# ═══════════════════════════════════════════════════════════════════════════
print("\n[6/6] Kirjoitetaan Excel-raportti...")

wb = Workbook()
thin = Side(style="thin", color="BBBBBB")
brd  = Border(left=thin, right=thin, top=thin, bottom=thin)
center_a = Alignment(horizontal="center", vertical="center")
left_a   = Alignment(horizontal="left",   vertical="center", wrap_text=True)

DARK  = PatternFill("solid", fgColor="1F3864")
MED   = PatternFill("solid", fgColor="2E75B6")
ALT   = PatternFill("solid", fgColor="D9E1F2")
GREEN = PatternFill("solid", fgColor="E2EFDA")
RED   = PatternFill("solid", fgColor="FCE4D6")

def hdr(ws, r, c, v, fill=MED, fc="FFFFFF", sz=10, bold=True, align=center_a):
    cell = ws.cell(row=r, column=c, value=v)
    cell.fill = fill
    cell.font = Font(bold=bold, color=fc, size=sz)
    cell.alignment = align
    cell.border = brd
    return cell

def dat(ws, r, c, v, bold=False, fmt=None, fill=None, align=center_a):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = Font(bold=bold, size=9)
    cell.alignment = align
    cell.border = brd
    if fill: cell.fill = fill
    if fmt:  cell.number_format = fmt
    return cell

# ── Sheet 1: Yhteenveto ───────────────────────────────────────────────────
ws1 = wb.active
ws1.title = "Yhteenveto"

ws1.merge_cells("A1:I1")
ws1["A1"].value = "FPL Pistetekijäanalyysi — Mikä vaikuttaa pisteisiin?"
ws1["A1"].font = Font(bold=True, size=14, color="FFFFFF")
ws1["A1"].fill = DARK; ws1["A1"].alignment = center_a
ws1.row_dimensions[1].height = 30

# -- Korrelaatiotaulukko
ws1.merge_cells("A3:I3")
ws1["A3"].value = "PEARSON-KORRELAATIOT (total_points, pelanneet pelaajat min>0)"
ws1["A3"].font = Font(bold=True, size=11, color="FFFFFF"); ws1["A3"].fill = MED
ws1["A3"].alignment = center_a

hdrs = ["Sija", "Tekijä", "Ryhmä", "Pearson r", "Abs(r)", "p-arvo",
        "Merkitsevyys", "N", "Tulkinta"]
for j, h in enumerate(hdrs, 1):
    hdr(ws1, 4, j, h)

interp_map = {
    "bonus":           "Bonus-pisteet — osa total_pointsia suoraan",
    "bps":             "BPS-pisteet — maaraa bonuksen",
    "goals_scored":    "Maali = 4-6 pistetta asemasta riippuen",
    "assists":         "Syotto = 3 pistetta",
    "clean_sheets":    "Puhdas peli = 1-4 pistetta (ei FWD)",
    "minutes":         "Peliaika: 1 piste 45+ min, 2 piste 60+ min",
    "saves":           "Torjunta = 1/3 piste (maalivahdille)",
    "ict_index":       "ICT = influence+creativity+threat yhdistetty",
    "influence":       "FPL:n laskennainen vaikuttavuusarvo",
    "goals_conceded":  "Paastetty maali miinuspisteet puolustukselle",
    "expected_goals":  "xG — odotetut maalit (ei suoraan pisteet)",
    "expected_goal_involvements": "xGI — xG+xA yhteensa",
    "creativity":      "Syottomahdollisuudet, korreloi syoton kanssa",
    "threat":          "Maaliuhat, korreloi maalin kanssa",
    "defensive_contribution": "Puolustuspanos — ei suoraan pisteisiin",
    "starts":          "Aloittaminen vs. vaihtopelaajana tulo",
    "expected_assists": "xA — odotetut syotot",
    "clearances_blocks_interceptions": "Puolustussuoritukset — BPS:aan",
    "recoveries":      "Pallonpalautukset — BPS:aan",
    "tackles":         "Taklaukset — ei suoraan pisteisiin",
    "was_home":        "Kotietu — marginaalinen vaikutus",
    "fdr":             "Vastustajanvaikeus — negatiivinen korrelaatio",
    "value":           "Pelaajan hinta — kalliimpi = parempi?",
    "yellow_cards":    "Keltainen kortti = -1 piste",
    "red_cards":       "Punainen kortti = -3 pistetta",
    "own_goals":       "Oma maali = -2 pistetta",
    "penalties_missed":"Hylätty rangaistuspotku = -2 pistetta",
    "penalties_saved": "Torjuttu rangaistuspotku = 5 pistetta (GKP)",
    "expected_goals_conceded": "xGC — odotetut paastetyt maalit",
}

for i, (_, row) in enumerate(corr_df.iterrows()):
    r_row = 5 + i
    fill_row = ALT if i % 2 == 0 else None
    grp_fill = PatternFill("solid", fgColor=GROUP_COLORS.get(row["group"], "#CCCCCC").lstrip("#"))
    sig = ("*** p<0.001" if row["p_value"] < 0.001
           else ("** p<0.01" if row["p_value"] < 0.01
           else ("* p<0.05"  if row["p_value"] < 0.05 else "ns")))
    direction_fill = GREEN if row["pearson_r"] > 0 else RED
    vals = [i+1, row["feature"], row["group"], row["pearson_r"],
            row["abs_r"], row["p_value"], sig, int(row["n"]),
            interp_map.get(row["feature"], "")]
    fmts = [None, None, None, "0.0000", "0.0000", "0.000E+00", None, None, None]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        f = (grp_fill if j == 3
             else direction_fill if j == 4
             else fill_row)
        dat(ws1, r_row, j, v, fmt=fmt, fill=f,
            align=left_a if j in (2, 3, 9) else center_a)

widths1 = [5, 20, 15, 12, 10, 14, 14, 8, 52]
for j, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(j)].width = w
ws1.freeze_panes = "A5"

# ── Sheet 2: OLS-regressio ────────────────────────────────────────────────
ws2 = wb.create_sheet("OLS-regressio")
ws2.merge_cells("A1:G1")
ws2["A1"].value = (f"OLS-monimuuttujaregressio: total_points ~ kaikki tekijat  "
                   f"|  R²={ols_model.rsquared:.4f}  Adj.R²={ols_model.rsquared_adj:.4f}"
                   f"  |  F={ols_model.fvalue:.1f} (p={ols_model.f_pvalue:.2e})")
ws2["A1"].font = Font(bold=True, size=11, color="FFFFFF")
ws2["A1"].fill = DARK; ws2["A1"].alignment = center_a
ws2.row_dimensions[1].height = 28

for j, h in enumerate(["Tekija","Kerroin","Std.virhe","t-stat","p-arvo","95% CI ala","95% CI yla"], 1):
    hdr(ws2, 2, j, h)

for i, (_, row) in enumerate(ols_results.iterrows()):
    r_row = 3 + i
    fill_row = (GREEN if row["coef"] > 0 and row["p_value"] < 0.05
                else RED if row["coef"] < 0 and row["p_value"] < 0.05
                else ALT if i % 2 == 0 else None)
    sig = ("***" if row["p_value"] < 0.001
           else ("**" if row["p_value"] < 0.01
           else ("*" if row["p_value"] < 0.05 else "ns")))
    vals = [row["feature"], row["coef"], row["std_err"],
            row["t_stat"], row["p_value"], row["ci_low"], row["ci_high"]]
    fmts = [None,"0.0000","0.0000","0.000","0.000E+00","0.0000","0.0000"]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        dat(ws2, r_row, j, v, fmt=fmt, fill=fill_row,
            align=left_a if j == 1 else center_a)

ws2.cell(row=3 + len(ols_results) + 1, column=1,
         value="Vihrea = positiivinen ja merkitseva | Punainen = negatiivinen ja merkitseva | Harmaa = ei merkitseva (p>0.05)")
ws2.cell(row=3 + len(ols_results) + 1, column=1).font = Font(italic=True, size=8, color="666666")
ws2.merge_cells(f"A{3+len(ols_results)+1}:G{3+len(ols_results)+1}")

widths2 = [22, 12, 12, 10, 14, 12, 12]
for j, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(j)].width = w

# ── Sheet 3: RF-tärkeys ───────────────────────────────────────────────────
ws3 = wb.create_sheet("RF-tarkeys")
ws3.merge_cells("A1:E1")
ws3["A1"].value = f"Random Forest Feature Importance (200 puuta, max_depth=8)  |  Train R²={rf.score(rf_df[rf_features], rf_df['total_points']):.4f}"
ws3["A1"].font = Font(bold=True, size=11, color="FFFFFF")
ws3["A1"].fill = DARK; ws3["A1"].alignment = center_a

for j, h in enumerate(["Sija","Tekija","Ryhmä","Tärkeys","Kumulatiivinen %"], 1):
    hdr(ws3, 2, j, h)

cum = 0
for i, (_, row) in enumerate(rf_imp.iterrows()):
    r_row = 3 + i
    cum += row["importance"]
    grp_fill = PatternFill("solid", fgColor=GROUP_COLORS.get(row["group"], "#CCCCCC").lstrip("#"))
    fill_row = ALT if i % 2 == 0 else None
    vals = [i+1, row["feature"], row["group"], row["importance"], cum]
    fmts = [None, None, None, "0.0000", "0.00%"]
    for j, (v, fmt) in enumerate(zip(vals, fmts), 1):
        dat(ws3, r_row, j, v, fmt=fmt,
            fill=grp_fill if j == 3 else fill_row,
            align=left_a if j in (2,3) else center_a)

widths3 = [5, 30, 16, 12, 18]
for j, w in enumerate(widths3, 1):
    ws3.column_dimensions[get_column_letter(j)].width = w

# ── Sheet 4: Asemataulukko ────────────────────────────────────────────────
ws4 = wb.create_sheet("Asemittain")
ws4.merge_cells(f"A1:{get_column_letter(1+len(POSITIONS))}1")
ws4["A1"].value = "Pearson r asemittain — TOP 12 tekijaa"
ws4["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws4["A1"].fill = DARK; ws4["A1"].alignment = center_a

hdr(ws4, 2, 1, "Tekija")
for j, pos in enumerate(POSITIONS, 2):
    pos_fill = PatternFill("solid", fgColor=POS_COLORS[pos].lstrip("#"))
    hdr(ws4, 2, j, pos, fill=pos_fill, fc="000000")

for i, feat in enumerate(key_features):
    r_row = 3 + i
    fill_row = ALT if i % 2 == 0 else None
    dat(ws4, r_row, 1, feat, bold=True, fill=fill_row, align=left_a)
    for j, pos in enumerate(POSITIONS, 2):
        val = pos_corr_pivot.at[feat, pos] if feat in pos_corr_pivot.index else None
        if val is not None and not np.isnan(val):
            cell_fill = (PatternFill("solid", fgColor="C6EFCE") if val > 0.3
                         else PatternFill("solid", fgColor="FFEB9C") if val > 0.1
                         else PatternFill("solid", fgColor="FFC7CE") if val < -0.05
                         else fill_row)
            dat(ws4, r_row, j, round(float(val), 4), fmt="0.0000", fill=cell_fill)
        else:
            dat(ws4, r_row, j, "N/A", fill=fill_row)

widths4 = [28, 12, 12, 12, 12]
for j, w in enumerate(widths4, 1):
    ws4.column_dimensions[get_column_letter(j)].width = w

# ── Sheet 5: Kuvaajat ─────────────────────────────────────────────────────
ws5 = wb.create_sheet("Kuvaajat")
ws5["A1"].value = "Visualisoinnit — FPL Pistetekijät"
ws5["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws5["A1"].fill = DARK; ws5["A1"].alignment = center_a
ws5.merge_cells("A1:Z1")

anchors = [(img1, "A3"), (img2, "A58"), (img3, "A108"), (img4, "A158")]
for img_path, anchor in anchors:
    if os.path.exists(img_path):
        img_obj = XLImage(img_path)
        img_obj.width = 920
        img_obj.height = int(img_obj.width * 0.60)
        ws5.add_image(img_obj, anchor)

wb.save(OUTPUT_XLS)
size_kb = os.path.getsize(OUTPUT_XLS) / 1024

# ═══════════════════════════════════════════════════════════════════════════
# LOPPUYHTEENVETO
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("TULOKSET — TOP TEKIJAT (korrelaatio total_points kanssa)")
print("=" * 65)
print(f"\nDatapisteet: {len(df_played):,} ottelua  |  OLS R²={ols_model.rsquared:.4f}\n")

print("Sija  Tekija                           r        Ryhmä")
print("-" * 65)
for i, (_, row) in enumerate(corr_df.iterrows(), 1):
    sig = "***" if row["p_value"] < 0.001 else ""
    print(f"  {i:2d}. {row['feature']:32s} {row['pearson_r']:+.4f}  {sig:3s}  [{row['group']}]")
    if i >= 15:
        print(f"  ... (yhteensa {len(corr_df)} tekijaa)")
        break

print(f"\nExcel + 4 PNG-kuvaa tallennettu kansioon FPL Data/")
print(f"  point_factors_analysis.xlsx ({size_kb:.0f} KB)")
