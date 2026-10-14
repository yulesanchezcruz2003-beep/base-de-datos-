"""Factores asociados a la morosidad: padrón completo de colegiados vs. morosos.

Uso:  python analisis/factores_morosidad.py
Entradas: datos/Padron_colegiados.xlsx (todos los colegiados, con nombres)
          datos/Base_Morosidad_completada.xlsx (solo morosos, sin nombres)
Salidas:  analisis/graficos/f*.png, analisis/resultados/f*.csv, informe_factores.md

Método (sin identificar personas): la base de morosos no trae nombre ni carné,
así que NO se cruza persona a persona. Se agrupan ambas bases en celdas con las
variables comunes (edad, fecha de incorporación, condición, grado). En cada
celda se conoce cuántos colegiados hay (N) y cuántos son morosos (n); eso basta
para estimar tasas y modelos logísticos exactos con esas variables.
Los nombres del padrón nunca se imprimen ni se guardan en las salidas.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analisis"))
from analisis_morosidad import cargar  # noqa: E402

PADRON = RAIZ / "datos" / "Padron_colegiados.xlsx"
GRAF = RAIZ / "analisis" / "graficos"
RES = RAIZ / "analisis" / "resultados"
FECHA_REF = pd.Timestamp("2026-09-02")  # fecha de corte del padrón (según el nombre del archivo)
COLOR, COLOR2 = "#1f5f8b", "#c8553d"
sns.set_theme(style="whitegrid", context="notebook")
CLAVE = ["edad", "fecha", "cond", "grado"]


def guardar(n):
    plt.tight_layout(); plt.savefig(GRAF / n, dpi=150); plt.close()


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return c - h, c + h


# ------------------------------------------------------------------ carga y limpieza
def cargar_padron():
    p = pd.read_excel(PADRON)
    p.columns = ["ap1", "ap2", "nom", "edad", "cond", "fecha", "carne", "grado"]
    bit = []
    n0 = len(p)
    esp = sum(int((p[c] != p[c].str.strip()).sum()) for c in ["cond", "grado"])
    bit.append(f"Espacios sobrantes corregidos en condición/grado: {esp} celdas")
    p["grado"] = p["grado"].str.strip()
    n_may = int((p["grado"] != p["grado"].str.capitalize()).sum())
    p["grado"] = p["grado"].str.capitalize()
    bit.append(f"Grado con mayúsculas inconsistentes unificado ('licenciatura'): {n_may}")
    p["cond"] = p["cond"].str.strip().replace({"Articulo 7 (Edad 65 años)": "Artículo 7 (65+ años)"})
    bit.append(f"Duplicados por carné: {int(p['carne'].duplicated().sum())}; por nombre completo: "
               f"{int(p.duplicated(['ap1', 'ap2', 'nom']).sum())}")
    bit.append(f"Valores faltantes en el padrón: {int(p.isna().sum().sum())}")
    anio_carne = p["carne"].str[:2].astype(int) + 2000
    dif = (anio_carne - p["fecha"].dt.year)
    bit.append(f"Carné cuyo año no coincide con la fecha de incorporación: {int((dif != 0).sum())} "
               f"(diferencia en años: {dif[dif != 0].value_counts().sort_index().to_dict()}); no se corrigió, no se usa el carné en el análisis")
    bit.append(f"Registros del padrón: {n0}")
    return p.drop(columns=["ap1", "ap2", "nom", "carne"]), bit


def preparar():
    p, bit = cargar_padron()
    m, _ = cargar()
    m = m.dropna(subset=["condicion"]).rename(columns={"fecha_incorp": "fecha", "condicion": "cond"})
    m = m.rename(columns={"grado": "grado"})
    sin_celda = int(len(m) - len(m.merge(p[CLAVE].drop_duplicates(), on=CLAVE)))
    N = p.groupby(CLAVE).size().rename("N")
    n = m.groupby(CLAVE).size().rename("n")
    c = pd.concat([N, n], axis=1).fillna(0).astype(int).reset_index()
    return p, m, c, bit, sin_celda


# ------------------------------------------------------------------ expansión a nivel individual (equivalente)
def expandir(c):
    """Una fila por colegiado; en cada celda n morosos y N-n no morosos (mismas covariables)."""
    pos = c.loc[c.index.repeat(c["n"])].assign(moroso=1)
    neg = c.loc[c.index.repeat(c["N"] - c["n"])].assign(moroso=0)
    d = pd.concat([pos, neg], ignore_index=True)
    d["celda"] = d.groupby(CLAVE).ngroup()
    d["antig"] = (FECHA_REF - d["fecha"]).dt.days / 365.25
    d["edad10"] = d["edad"] / 10
    d["grupo_edad"] = pd.cut(d["edad"], [0, 34, 44, 54, 64, 120], labels=["<35", "35-44", "45-54", "55-64", "65+"])
    d["cohorte"] = pd.cut(d["fecha"].dt.year, [2011, 2013, 2017, 2021, 2030],
                          labels=["2012-2013", "2014-2017", "2018-2021", "2022-2026"])
    d["grado_g"] = d["grado"].replace({"Doctorado": "Maestría/Doctorado", "Maestría": "Maestría/Doctorado"})
    return d


def tasas(d, col):
    t = d.groupby(col, observed=True)["moroso"].agg(colegiados="size", morosos="sum")
    t["tasa_%"] = (t["morosos"] / t["colegiados"] * 100).round(1)
    ci = [wilson(k, n) for k, n in zip(t["morosos"], t["colegiados"])]
    t["IC95_inf_%"] = [round(a * 100, 1) for a, _ in ci]
    t["IC95_sup_%"] = [round(b * 100, 1) for _, b in ci]
    tab = np.array([t["morosos"], t["colegiados"] - t["morosos"]])
    ok = tab.sum(axis=0) >= 5
    chi2, pv, _, _ = stats.chi2_contingency(tab[:, ok])
    return t, pv


def main():
    p, m, c, bit, sin_celda = preparar()
    d = expandir(c)
    n_mor, n_tot = int(d["moroso"].sum()), len(d)
    celdas_amb = c[(c["n"] > 0) & (c["n"] < c["N"])]
    amb_personas = int(celdas_amb["N"].sum())

    # ---- tasas por factor
    pv = {}
    with pd.ExcelWriter(RES / "f01_tasas_morosidad.xlsx") as xw:
        for col in ["cond", "grado", "grupo_edad", "cohorte"]:
            t, pv[col] = tasas(d, col)
            t.to_excel(xw, sheet_name=col)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for a, (col, tit) in zip(axes.ravel(), [("cond", "Condición en el Colegio"), ("grado", "Grado académico"),
                                           ("grupo_edad", "Grupo de edad"), ("cohorte", "Año de incorporación")]):
        t, _ = tasas(d, col)
        t = t[t["colegiados"] >= 5]
        y = np.arange(len(t))
        a.barh(y, t["tasa_%"], color=COLOR)
        a.errorbar(t["tasa_%"], y, xerr=[t["tasa_%"] - t["IC95_inf_%"], t["IC95_sup_%"] - t["tasa_%"]],
                   fmt="none", ecolor="#333", capsize=3)
        for yi, (r, hi, k, n) in enumerate(zip(t["tasa_%"], t["IC95_sup_%"], t["morosos"], t["colegiados"])):
            a.text(min(hi + 2, 100), yi, f"{r:.0f}% ({k}/{n})", va="center", fontsize=8)
        a.set_yticks(y); a.set_yticklabels(t.index.astype(str)); a.invert_yaxis()
        a.axvline(n_mor / n_tot * 100, color=COLOR2, ls="--", lw=1)
        a.set(title=tit, xlabel="% de colegiados en morosidad", xlim=(0, 125))
    fig.suptitle(f"Tasa de morosidad por factor (línea roja = promedio {n_mor / n_tot * 100:.0f}%; barras = IC 95%)")
    guardar("f01_tasas_morosidad.png")

    # ---- modelos logísticos (binomial sobre celdas; equivalente al individual)
    # Arreglo de pago: todos son morosos por definición (separación perfecta) -> se excluyen de los modelos.
    d["cond_g"] = d["cond"].replace({"Miembro Honorario": "Exento (Art. 7/Honorario)",
                                     "Artículo 7 (65+ años)": "Exento (Art. 7/Honorario)"})
    d = d[d["cond"] != "Arreglo de pago"].reset_index(drop=True)
    base = "moroso ~ edad10 + antig + C(grado_g, Treatment('Bachillerato'))"
    m_sin = smf.logit(base, data=d).fit(disp=0)
    m_con = smf.logit(base + " + C(cond_g, Treatment('Activo'))", data=d).fit(disp=0)

    def orr(m):
        o = pd.DataFrame({"odds_ratio": np.exp(m.params), "IC95_inf": np.exp(m.conf_int()[0]),
                          "IC95_sup": np.exp(m.conf_int()[1]), "p_valor": m.pvalues}).drop("Intercept")
        o.index = (o.index.str.replace(r"C\((.*?), Treatment\('(.*?)'\)\)\[T\.", r"\1: ", regex=True)
                   .str.replace("]", "", regex=False).str.replace("edad10", "edad (+10 años)")
                   .str.replace("antig", "antigüedad (+1 año)"))
        return o.round(4)
    o_sin, o_con = orr(m_sin), orr(m_con)
    o_sin.to_csv(RES / "f02_modelo_sin_condicion.csv"); o_con.to_csv(RES / "f03_modelo_con_condicion.csv")

    # ---- validación: AUC con validación cruzada por celda
    X1 = pd.get_dummies(d[["edad10", "antig", "grado_g"]], drop_first=True).astype(float)
    X2 = pd.get_dummies(d[["edad10", "antig", "grado_g", "cond_g"]], drop_first=True).astype(float)
    auc = {}
    for nom, X in [("sin condición", X1), ("con condición", X2)]:
        pred = np.zeros(len(d))
        for tr, te in GroupKFold(5).split(X, d["moroso"], d["celda"]):
            pred[te] = LogisticRegression(max_iter=2000).fit(X.iloc[tr], d["moroso"].iloc[tr]).predict_proba(X.iloc[te])[:, 1]
        auc[nom] = round(roc_auc_score(d["moroso"], pred), 3)

    # ---- gráfico de odds ratios
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharex=False)
    for a, (o, tit) in zip(axes, [(o_sin, "Sin condición (edad, antigüedad, grado)"), (o_con, "Con condición en el Colegio")]):
        o = o.sort_values("odds_ratio"); y = np.arange(len(o))
        a.errorbar(o["odds_ratio"], y, xerr=[o["odds_ratio"] - o["IC95_inf"], o["IC95_sup"] - o["odds_ratio"]],
                   fmt="o", color=COLOR, capsize=3)
        a.axvline(1, color="grey", ls="--"); a.set_xscale("log")
        a.set_yticks(y); a.set_yticklabels(o.index); a.set_title(tit); a.set_xlabel("Odds ratio (escala log, IC 95%)")
    fig.suptitle("Factores asociados a estar en morosidad")
    guardar("f02_odds_ratios.png")

    # ---- severidad entre morosos: atraso vs. antigüedad
    m = m.copy()
    m["antig_meses"] = (FECHA_REF - m["fecha"]).dt.days / 30.44
    m["prop_atraso"] = m["meses_atraso"] / m["antig_meses"]
    sev_sup = int((m["meses_atraso"] > m["antig_meses"] + 1).sum())
    r, rp = stats.spearmanr(m["antig_meses"], m["meses_atraso"])
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(m["antig_meses"], m["meses_atraso"], s=14, alpha=.5, color=COLOR)
    lim = max(m["antig_meses"].max(), m["meses_atraso"].max())
    ax.plot([0, lim], [0, lim], color=COLOR2, ls="--", label="atraso = antigüedad (máximo posible)")
    ax.set(title="Meses de atraso vs. meses desde la incorporación", xlabel="Meses desde incorporación", ylabel="Meses de atraso")
    ax.legend(); guardar("f03_atraso_vs_antiguedad.png")

    # ---- perfil comparativo morosos vs no morosos
    comp = pd.DataFrame({
        "edad_mediana_morosos": [d.loc[d.moroso == 1, "edad"].median()],
        "edad_mediana_no_morosos": [d.loc[d.moroso == 0, "edad"].median()],
        "antig_mediana_morosos_años": [round(d.loc[d.moroso == 1, "antig"].median(), 1)],
        "antig_mediana_no_morosos_años": [round(d.loc[d.moroso == 0, "antig"].median(), 1)]})
    comp.to_csv(RES / "f04_comparacion_edad_antiguedad.csv", index=False)
    u, pu = stats.mannwhitneyu(d.loc[d.moroso == 1, "edad"], d.loc[d.moroso == 0, "edad"])
    u2, pu2 = stats.mannwhitneyu(d.loc[d.moroso == 1, "antig"], d.loc[d.moroso == 0, "antig"])

    # ---- informe
    T = {k: pd.read_excel(RES / "f01_tasas_morosidad.xlsx", sheet_name=k, index_col=0) for k in ["cond", "grado", "grupo_edad", "cohorte"]}
    md = ["# Factores asociados a la morosidad (padrón completo vs. morosos)\n",
          "## 1. Calidad de datos del padrón", *[f"- {b}" for b in bit],
          f"- Morosos de la primera base con datos cruzados: {len(m)}; sin celda correspondiente en el padrón: {sin_celda}. "
          "Los 4 morosos sin coincidencia en la segunda base se excluyen del análisis de factores.",
          f"- Colegiados en celdas con ambigüedad (celda mixta de morosos y no morosos): {amb_personas} de {n_tot} "
          f"({amb_personas / n_tot * 100:.1f}%). No afecta a las tasas ni a los modelos, que usan conteos por celda.\n",
          "## 2. Tasa de morosidad", f"**{n_mor} de {n_tot} colegiados ({n_mor / n_tot * 100:.1f}%)** están en la base de morosidad.\n"]
    for col, tit in [("cond", "Condición"), ("grado", "Grado académico"), ("grupo_edad", "Grupo de edad"), ("cohorte", "Año de incorporación")]:
        md += [f"### {tit} (chi-cuadrado p = {pv[col]:.2g})", T[col].to_markdown(floatfmt=".1f"), ""]
    md += [f"Edad mediana: morosos {comp.iloc[0, 0]:.0f} vs. no morosos {comp.iloc[0, 1]:.0f} (Mann-Whitney p = {pu:.2g}). "
           f"Antigüedad mediana: morosos {comp.iloc[0, 2]} vs. no morosos {comp.iloc[0, 3]} años (p = {pu2:.2g}).\n",
           "## 3. Modelos logísticos (odds ratios; se excluyen las 14 personas con arreglo de pago, todas morosas por definición)", "**Sin condición** (edad, antigüedad, grado):", o_sin.to_markdown(floatfmt=".3f"), "",
           "**Con condición:**", o_con.to_markdown(floatfmt=".3f"), "",
           f"AUC con validación cruzada por celda: sin condición {auc['sin condición']}, con condición {auc['con condición']}.\n",
           "## 4. Severidad entre morosos",
           f"- Correlación meses de atraso vs. antigüedad (Spearman): {r:.2f} (p = {rp:.2g}).",
           f"- Morosos con más meses de atraso que meses de colegiatura (+1): {sev_sup} (revisar: el atraso no puede exceder la antigüedad).",
           f"- Proporción mediana del tiempo de colegiatura en atraso: {m['prop_atraso'].median() * 100:.0f}%.\n",
           "## 5. Limitaciones",
           "- Solo hay edad, grado, condición y fecha de incorporación en ambas bases; sexo e institución no están en el padrón, "
           "por lo que no se pueden comparar contra los no morosos.",
           "- La condición (p. ej. Inactivo) se mide al corte del padrón y puede ser **consecuencia** de la morosidad, no su causa. "
           "Por eso se presentan modelos con y sin ella.",
           "- Asociación no implica causalidad."]
    (RES / "informe_factores.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
