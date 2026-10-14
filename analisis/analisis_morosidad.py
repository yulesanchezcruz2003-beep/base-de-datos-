"""Análisis de morosidad - Colegio de Profesionales en Sociología.

Uso:  python analisis/analisis_morosidad.py
Entrada:  datos/Base_Morosidad_completada.xlsx
Salida:   analisis/graficos/*.png, analisis/resultados/*.csv|xlsx|md

Objetivos
1. Caracterizar el perfil de las personas en morosidad.
2. Reconocer patrones y factores asociados a la morosidad (monto de la deuda
   y meses de atraso), dado que la base solo contiene personas morosas.
Moneda: colones costarricenses (CRC).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy import stats

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "datos" / "Base_Morosidad_completada.xlsx"
GRAF = RAIZ / "analisis" / "graficos"
RES = RAIZ / "analisis" / "resultados"
GRAF.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="notebook")
COLOR = "#1f5f8b"
ORDEN_TRAMOS = ["0-12 meses", "13-24 meses", "25-48 meses", "49-72 meses", "73-96 meses", "97+ meses"]


def crc(x):
    return f"₡{x:,.0f}"


def guardar(nombre):
    plt.tight_layout()
    plt.savefig(GRAF / nombre, dpi=150)
    plt.close()


# ---------------------------------------------------------------- 1. Carga y limpieza
def cargar():
    df = pd.read_excel(ENTRADA)
    df.columns = ["sexo", "edad", "institucion", "meses_atraso", "deuda",
                  "condicion", "grado", "fecha_incorp", "calidad_emp"]
    bitacora = []

    n_dup = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    bitacora.append(f"Filas idénticas en las 9 columnas eliminadas: {n_dup} (la base no tiene identificador; confirmar que no son personas distintas)")

    # Categorías con espacios/mayúsculas inconsistentes
    antes = df["institucion"].nunique()
    df["institucion"] = (df["institucion"].str.strip()
                         .replace({"Consultoría/Propio": "Consultoría/propio"}))
    bitacora.append(f"Categorías de institución normalizadas: {antes} -> {df['institucion'].nunique()}")

    df["sexo"] = df["sexo"].map({"F": "Mujer", "M": "Hombre"})
    df["condicion"] = df["condicion"].replace({"Articulo 7 (Edad 65 años)": "Artículo 7 (65+ años)"})

    # Los 4 registros sin coincidencia en la segunda base no tienen condición,
    # grado ni fecha de incorporación: se conservan en lo demográfico/deuda.
    sin_match = int(df["condicion"].isna().sum())
    bitacora.append(f"Registros sin coincidencia en 2.ª base (condición/grado/fecha vacíos): {sin_match}")

    df["tramo_atraso"] = pd.cut(df["meses_atraso"], [0, 12, 24, 48, 72, 96, 999],
                                labels=ORDEN_TRAMOS)
    df["grupo_edad"] = pd.cut(df["edad"], [0, 34, 44, 54, 64, 120],
                              labels=["<35", "35-44", "45-54", "55-64", "65+"])
    df["anio_incorp"] = df["fecha_incorp"].dt.year
    df["cuota_implicita"] = df["deuda"] / df["meses_atraso"]
    df["sin_labor"] = np.where(df["institucion"] == "No labora", "No labora", "Labora")
    df["inactivo"] = (df["condicion"] == "Inactivo").astype(float).where(df["condicion"].notna())
    return df, bitacora


# ---------------------------------------------------------------- 2. Calidad
def calidad(df):
    d = pd.DataFrame({
        "tipo": df.dtypes.astype(str),
        "nulos": df.isna().sum(),
        "pct_nulos": (df.isna().mean() * 100).round(1),
        "unicos": df.nunique(),
    })
    d.to_csv(RES / "01_calidad_datos.csv")
    cuota = df["cuota_implicita"].describe()
    return cuota


# ---------------------------------------------------------------- 3. Perfil
def tabla_freq(df, col):
    t = df[col].value_counts(dropna=False).rename("n").to_frame()
    t["%"] = (t["n"] / len(df) * 100).round(1)
    return t


def perfil(df):
    salidas = {}
    for col in ["sexo", "grupo_edad", "institucion", "condicion", "grado",
                "calidad_emp", "tramo_atraso"]:
        salidas[col] = tabla_freq(df, col)
    resumen_num = df[["edad", "meses_atraso", "deuda"]].describe().T.round(1)
    resumen_num["mediana"] = df[["edad", "meses_atraso", "deuda"]].median().round(1)
    salidas["numericas"] = resumen_num

    with pd.ExcelWriter(RES / "02_perfil_morosidad.xlsx") as xw:
        for k, v in salidas.items():
            v.to_excel(xw, sheet_name=k[:31])

    # Gráficos
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    sns.histplot(df["edad"], bins=15, color=COLOR, ax=ax[0]); ax[0].set(title="Edad", xlabel="Años", ylabel="Personas")
    sns.histplot(df["meses_atraso"], bins=20, color=COLOR, ax=ax[1]); ax[1].set(title="Meses de atraso", xlabel="Meses", ylabel="")
    sns.histplot(df["deuda"] / 1e3, bins=20, color=COLOR, ax=ax[2]); ax[2].set(title="Deuda", xlabel="Miles de colones", ylabel="")
    fig.suptitle("Distribución de las variables numéricas (n=%d)" % len(df))
    guardar("01_distribuciones.png")

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for a, (col, tit) in zip(axes.ravel(), [("sexo", "Sexo"), ("institucion", "Institución"),
                                           ("condicion", "Condición"), ("grado", "Grado académico"),
                                           ("tramo_atraso", "Tramo de atraso"), ("grupo_edad", "Grupo de edad")]):
        t = df[col].value_counts(dropna=True)
        if col == "tramo_atraso": t = t.reindex(ORDEN_TRAMOS)
        if col == "grupo_edad": t = t.reindex(["<35", "35-44", "45-54", "55-64", "65+"])
        sns.barplot(x=t.values, y=t.index.astype(str), color=COLOR, ax=a)
        for i, v in enumerate(t.values):
            a.text(v, i, f" {v} ({v/len(df)*100:.0f}%)", va="center", fontsize=8)
        a.set(title=tit, xlabel="Personas", ylabel="")
        a.set_xlim(0, t.max() * 1.3)
    fig.suptitle("Perfil de las personas morosas")
    guardar("02_perfil_categorico.png")

    fig, ax = plt.subplots(figsize=(9, 4))
    t = df["anio_incorp"].value_counts().sort_index()
    sns.barplot(x=t.index.astype(int), y=t.values, color=COLOR, ax=ax)
    ax.set(title="Año de incorporación al Colegio de las personas morosas", xlabel="Año", ylabel="Personas")
    guardar("03_anio_incorporacion.png")
    return salidas


# ---------------------------------------------------------------- 4. Factores asociados
def asociaciones(df):
    filas = []
    # Variables categóricas vs. meses de atraso y deuda (Kruskal-Wallis / Mann-Whitney)
    for col in ["sexo", "grupo_edad", "institucion", "condicion", "grado", "sin_labor"]:
        sub = df.dropna(subset=[col])
        grupos = [g["meses_atraso"].values for _, g in sub.groupby(col, observed=True) if len(g) >= 5]
        if len(grupos) < 2:
            continue
        h, p = stats.kruskal(*grupos)
        eps2 = (h - len(grupos) + 1) / (len(sub) - len(grupos))  # epsilon² (tamaño del efecto)
        filas.append({"variable": col, "prueba": "Kruskal-Wallis", "vs": "meses_atraso",
                      "estadistico": round(h, 2), "p_valor": p, "tamano_efecto(eps2)": round(eps2, 3),
                      "grupos_usados": len(grupos)})
    # Numéricas
    for col in ["edad", "anio_incorp"]:
        sub = df.dropna(subset=[col])
        r, p = stats.spearmanr(sub[col], sub["meses_atraso"])
        filas.append({"variable": col, "prueba": "Spearman", "vs": "meses_atraso",
                      "estadistico": round(r, 3), "p_valor": p, "tamano_efecto(eps2)": round(r**2, 3),
                      "grupos_usados": None})
    # Chi-cuadrado entre variables categóricas clave (inactivo vs. resto)
    for col in ["sexo", "grupo_edad", "institucion", "grado"]:
        sub = df.dropna(subset=[col, "condicion"])
        tab = pd.crosstab(sub[col], sub["condicion"] == "Inactivo")
        tab = tab[tab.sum(axis=1) >= 5]
        chi2, p, _, _ = stats.chi2_contingency(tab)
        v = np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1)))
        filas.append({"variable": col, "prueba": "Chi-cuadrado", "vs": "condicion==Inactivo",
                      "estadistico": round(chi2, 2), "p_valor": p, "tamano_efecto(eps2)": round(v, 3),
                      "grupos_usados": tab.shape[0]})
    res = pd.DataFrame(filas)
    res["p_valor"] = res["p_valor"].round(4)
    res = res.rename(columns={"tamano_efecto(eps2)": "tamano_efecto"})
    res["significativo_5%"] = res["p_valor"] < 0.05
    res.to_csv(RES / "03_pruebas_asociacion.csv", index=False)

    # Gráficos
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for a, col in zip(axes, ["institucion", "condicion", "grado"]):
        orden = df.groupby(col)["meses_atraso"].median().sort_values().index
        sns.boxplot(data=df, y=col, x="meses_atraso", order=orden, color="#9cc3dc", ax=a)
        a.set(title=f"Meses de atraso por {col}", xlabel="Meses de atraso", ylabel="")
    guardar("04_atraso_por_categoria.png")

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    sns.scatterplot(data=df, x="edad", y="meses_atraso", hue="sexo", alpha=.6, ax=axes[0]); axes[0].set(title="Edad vs. meses de atraso")
    sns.scatterplot(data=df, x="meses_atraso", y=df["deuda"] / 1e3, alpha=.6, color=COLOR, ax=axes[1])
    axes[1].set(title="Meses de atraso vs. deuda", ylabel="Deuda (miles ₡)")
    sns.boxplot(data=df, x="sexo", y=df["deuda"] / 1e3, color="#9cc3dc", ax=axes[2]); axes[2].set(title="Deuda por sexo", ylabel="Deuda (miles ₡)")
    guardar("05_relaciones.png")

    # Heatmap: mediana de meses de atraso por institución x grupo de edad
    piv = df.pivot_table(index="institucion", columns="grupo_edad", values="meses_atraso", aggfunc="median", observed=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.heatmap(piv, annot=True, fmt=".0f", cmap="Blues", ax=ax, cbar_kws={"label": "Mediana meses"})
    ax.set(title="Mediana de meses de atraso: institución × edad", xlabel="Grupo de edad", ylabel="")
    guardar("06_heatmap_institucion_edad.png")
    return res


def modelos(df):
    d = df.dropna(subset=["condicion", "grado", "anio_incorp"]).copy()
    d["condicion_g"] = d["condicion"].where(d["condicion"].isin(["Inactivo", "Activo"]), "Otra")
    d["grado_g"] = d["grado"].replace({"Doctorado": "Maestría/Doctorado", "Maestría": "Maestría/Doctorado"})
    d["inst_g"] = d["institucion"].replace({"Consultoría/propio": "Consultoría/propio"})
    f = ("np.log(meses_atraso) ~ edad + C(sexo) + C(inst_g, Treatment('Institución Pública')) "
         "+ C(condicion_g, Treatment('Inactivo')) + C(grado_g, Treatment('Bachillerato'))")
    m = smf.ols(f, data=d).fit(cov_type="HC3")
    coef = pd.DataFrame({"coef": m.params, "IC95_inf": m.conf_int()[0], "IC95_sup": m.conf_int()[1],
                         "p_valor": m.pvalues})
    coef["efecto_%_sobre_meses"] = ((np.exp(coef["coef"]) - 1) * 100).round(1)
    coef = coef.round(4)
    coef.to_csv(RES / "04_modelo_ols_log_meses_atraso.csv")

    # Modelo logístico: ser Inactivo vs. Activo/otra condición
    d["inactivo_i"] = (d["condicion"] == "Inactivo").astype(int)
    fl = ("inactivo_i ~ edad + C(sexo) + C(inst_g, Treatment('Institución Pública')) "
          "+ C(grado_g, Treatment('Bachillerato')) + meses_atraso")
    lg = smf.logit(fl, data=d).fit(disp=0)
    orr = pd.DataFrame({"odds_ratio": np.exp(lg.params), "IC95_inf": np.exp(lg.conf_int()[0]),
                        "IC95_sup": np.exp(lg.conf_int()[1]), "p_valor": lg.pvalues}).round(4)
    orr.to_csv(RES / "05_modelo_logit_inactivo.csv")

    # Gráfico de efectos (OLS, excluyendo intercepto)
    c = coef.drop("Intercept")
    c.index = (c.index.str.replace(r"C\(.*?\)\[T\.", "", regex=True).str.replace("]", "", regex=False))
    c = c.sort_values("efecto_%_sobre_meses")
    lo, hi = (np.exp(c["IC95_inf"]) - 1) * 100, (np.exp(c["IC95_sup"]) - 1) * 100
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(c["efecto_%_sobre_meses"], range(len(c)), xerr=[c["efecto_%_sobre_meses"] - lo, hi - c["efecto_%_sobre_meses"]],
                fmt="o", color=COLOR, capsize=3)
    ax.axvline(0, color="grey", ls="--"); ax.set_yticks(range(len(c))); ax.set_yticklabels(c.index)
    ax.set(title="Efecto ajustado sobre los meses de atraso (IC 95%)", xlabel="% de cambio en meses de atraso")
    guardar("07_efectos_modelo.png")
    return m, coef, lg, orr


def segmentos(df):
    t = (df.groupby("institucion").agg(personas=("deuda", "size"), deuda_total=("deuda", "sum"),
                                       deuda_mediana=("deuda", "median"), meses_mediana=("meses_atraso", "median"),
                                       edad_mediana=("edad", "median"))
         .sort_values("deuda_total", ascending=False))
    t["%_deuda"] = (t["deuda_total"] / t["deuda_total"].sum() * 100).round(1)
    t.to_csv(RES / "06_segmentos_institucion.csv")
    tr = (df.groupby("tramo_atraso", observed=True).agg(personas=("deuda", "size"), deuda_total=("deuda", "sum"))
          .reindex(ORDEN_TRAMOS))
    tr["%_personas"] = (tr["personas"] / tr["personas"].sum() * 100).round(1)
    tr["%_deuda"] = (tr["deuda_total"] / tr["deuda_total"].sum() * 100).round(1)
    tr.to_csv(RES / "07_tramos_atraso.csv")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.barplot(x=tr.index, y=tr["deuda_total"] / 1e6, color=COLOR, ax=ax)
    for i, (v, p) in enumerate(zip(tr["deuda_total"] / 1e6, tr["%_deuda"])):
        ax.text(i, v, f"{v:,.1f} M\n({p:.0f}%)", ha="center", va="bottom", fontsize=8)
    ax.set(title="Deuda acumulada por tramo de atraso", xlabel="", ylabel="Millones de colones")
    ax.set_ylim(0, (tr["deuda_total"] / 1e6).max() * 1.2)
    plt.xticks(rotation=20)
    guardar("08_deuda_por_tramo.png")

    # Prioridad de cobro: deuda y antigüedad (sin datos identificativos: solo posición en base)
    df2 = df.copy()
    df2["prioridad_cobro"] = np.select(
        [df2["condicion"].isin(["Activo", "Arreglo de pago"]) & (df2["meses_atraso"] <= 24),
         df2["condicion"].isin(["Activo", "Arreglo de pago"])],
        ["A - Recuperable: colegiado activo/arreglo", "B - Activo con atraso largo"],
        default="C - Inactivo/sin dato (cobro difícil)")
    p = df2.groupby("prioridad_cobro").agg(personas=("deuda", "size"), deuda_total=("deuda", "sum"))
    p["%_deuda"] = (p["deuda_total"] / p["deuda_total"].sum() * 100).round(1)
    p.to_csv(RES / "08_prioridad_cobro.csv")
    return t, tr, p


# ---------------------------------------------------------------- 5. Informe
def informe(df, bit, cuota, perf, pruebas, ols, orr, seg, tr, prio):
    n = len(df)
    deuda = df["deuda"].sum()
    top = lambda col: perf[col].index[0]
    pct = lambda col: perf[col]["%"].iloc[0]
    sig = pruebas[pruebas["significativo_5%"]]
    md = [f"# Informe de morosidad – Colegio de Profesionales en Sociología\n",
          f"*Moneda: colones (₡). Registros analizados: {n}.*\n",
          "## 1. Calidad de los datos", *[f"- {b}" for b in bit],
          f"- La deuda equivale a una cuota casi constante de **{crc(cuota['50%'])}/mes** de atraso "
          f"(rango {crc(cuota['min'])}–{crc(cuota['max'])}). Es decir, **la deuda es prácticamente "
          "función lineal de los meses de atraso**; no aporta información independiente.",
          "- La base contiene **solo personas morosas**: no hay grupo de comparación (al día), por lo que "
          "no se puede estimar qué factores *causan* o predicen caer en mora, sino qué se asocia con "
          "*mayor atraso/deuda* dentro de los morosos.\n",
          "## 2. Perfil de las personas morosas (Objetivo 1)",
          f"- **Monto total adeudado:** {crc(deuda)}; mediana por persona {crc(df['deuda'].median())} "
          f"(media {crc(df['deuda'].mean())}).",
          f"- **Atraso:** mediana {df['meses_atraso'].median():.0f} meses (≈{df['meses_atraso'].median()/12:.1f} años); "
          f"{(df['meses_atraso']>48).mean()*100:.0f}% supera 4 años.",
          f"- **Sexo:** {pct('sexo'):.0f}% {'mujeres' if top('sexo') == 'Mujer' else 'hombres'}.",
          f"- **Edad:** mediana {df['edad'].median():.0f} años (rango {df['edad'].min()}–{df['edad'].max()}).",
          f"- **Institución:** predomina «{top('institucion')}» ({pct('institucion'):.0f}%); "
          f"«No labora» {perf['institucion'].loc['No labora','%']:.0f}%.",
          f"- **Condición:** {perf['condicion'].loc['Inactivo','%']:.0f}% inactivos; "
          f"{perf['condicion'].loc['Activo','%']:.0f}% activos; "
          f"{perf['condicion'].loc['Arreglo de pago','%']:.0f}% con arreglo de pago.",
          f"- **Grado:** {top('grado')} {pct('grado'):.0f}%.",
          f"- **Incorporación:** {(df['anio_incorp'].isin([2012,2013])).mean()*100:.0f}% se incorporó en 2012–2013.\n",
          "### Distribución por tramo de atraso", tr.round(1).to_markdown(floatfmt=",.1f", ), "",
          "### Segmentación por institución", seg.round(1).to_markdown(floatfmt=",.1f", ), "",
          "### Prioridad de cobro (propuesta)", prio.round(1).to_markdown(floatfmt=",.1f", ), "",
          "## 3. Factores asociados (Objetivo 2)",
          "Pruebas bivariadas con significancia al 5 %:",
          sig[["variable", "prueba", "vs", "estadistico", "p_valor", "tamano_efecto"]].to_markdown(floatfmt=".4g", index=False)
          if len(sig) else "Ninguna prueba resultó significativa.", "",
          "Modelo de regresión (log de meses de atraso, errores robustos HC3) – efecto % sobre meses de atraso:",
          ols[["efecto_%_sobre_meses", "p_valor"]].to_markdown(floatfmt=",.1f", ), "",
          "Regresión logística de ser *Inactivo* (odds ratios):", orr.to_markdown(floatfmt=",.1f", ), "",
          "## 4. Limitaciones",
          "- Sin grupo de comparación de personas al día → no se puede modelar el riesgo de caer en mora.",
          "- Deuda y meses de atraso están casi perfectamente relacionadas (cuota fija implícita).",
          "- 4 registros sin coincidencia en la segunda base; calidad de emparejamiento «Revisar» en "
          f"{(df['calidad_emp'].str.startswith('Revisar')).sum()} registros (sexo no coincide) y «Media» en "
          f"{(df['calidad_emp'].str.startswith('Media')).sum()}: los campos cruzados (condición, grado, fecha) pueden contener errores.",
          "- Asociación no implica causalidad.\n"]
    (RES / "informe_morosidad.md").write_text("\n".join(md), encoding="utf-8")


def main():
    df, bit = cargar()
    cuota = calidad(df)
    perf = perfil(df)
    pruebas = asociaciones(df)
    m, ols, lg, orr = modelos(df)
    seg, tr, prio = segmentos(df)
    df.to_csv(RES / "base_limpia.csv", index=False)
    informe(df, bit, cuota, perf, pruebas, ols, orr, seg, tr, prio)
    print((RES / "informe_morosidad.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
