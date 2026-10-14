"""Genera el libro de Excel con tablas y gráficos de morosidad.

Uso:  python analisis/generar_excel.py   (antes correr analisis_morosidad.py y factores_morosidad.py)
Salida: analisis/resultados/Informe_morosidad.xlsx

Solo contiene datos agregados (sin nombres ni filas de personas). Los conteos son
entradas (texto azul) tomadas de los scripts de análisis; porcentajes, totales,
tasas e intervalos de confianza son fórmulas de Excel.
"""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analisis"))
from analisis_morosidad import ORDEN_TRAMOS, cargar  # noqa: E402

RES = RAIZ / "analisis" / "resultados"
SALIDA = RES / "Informe_morosidad.xlsx"

FONT = "Arial"
AZUL_IN = Font(name=FONT, size=10, color="0000FF")
NORMAL = Font(name=FONT, size=10)
NEGRITA = Font(name=FONT, size=10, bold=True)
TITULO = Font(name=FONT, size=14, bold=True, color="1F3A5F")
SUB = Font(name=FONT, size=9, italic=True, color="595959")
HEAD_FILL = PatternFill("solid", fgColor="1F5F8B")
HEAD_FONT = Font(name=FONT, size=10, bold=True, color="FFFFFF")
TOTAL_FILL = PatternFill("solid", fgColor="E8EEF4")
FINO = Side(style="thin", color="BFBFBF")
BORDE = Border(left=FINO, right=FINO, top=FINO, bottom=FINO)
CRC = '"₡"#,##0'
PCT = "0.0%"
ENT = "#,##0"

wb = Workbook()


def hoja(nombre, titulo, subtitulo, anchos):
    ws = wb.create_sheet(nombre)
    ws.sheet_view.showGridLines = False
    ws["A1"], ws["A1"].font = titulo, TITULO
    ws["A2"], ws["A2"].font = subtitulo, SUB
    for i, a in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = a
    return ws


def encabezado(ws, fila, cols, col0=1):
    for j, c in enumerate(cols):
        x = ws.cell(fila, col0 + j, c)
        x.font, x.fill, x.border = HEAD_FONT, HEAD_FILL, BORDE
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[fila].height = 30


def celda(ws, fila, col, valor, fmt=None, entrada=False, negrita=False, fill=None, wrap=False):
    x = ws.cell(fila, col, valor)
    x.font = AZUL_IN if entrada else (NEGRITA if negrita else NORMAL)
    x.border = BORDE
    if fmt:
        x.number_format = fmt
    if fill:
        x.fill = fill
    if wrap:
        x.alignment = Alignment(wrap_text=True, vertical="top")
    return x


def grafico(ws, ancla, titulo, cats, vals, y_titulo, fmt=None, w=16, h=7.5, etiquetas=True):
    ch = BarChart()
    ch.type, ch.style = "col", 10
    ch.title, ch.legend = titulo, None
    ch.y_axis.title = y_titulo
    ch.y_axis.majorGridlines = None
    ch.add_data(vals, titles_from_data=True)
    ch.set_categories(cats)
    ch.series[0].graphicalProperties.solidFill = "1F5F8B"
    if etiquetas:
        ch.dataLabels = DataLabelList()
        ch.dataLabels.showVal = True
        ch.dataLabels.showSerName = ch.dataLabels.showCatName = ch.dataLabels.showLegendKey = False
        if fmt:
            ch.dataLabels.numFmt = fmt
    if fmt:
        ch.y_axis.numFmt = fmt
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.width, ch.height = w, h
    ws.add_chart(ch, ancla)


# ------------------------------------------------------------------ datos de entrada
df, _ = cargar()
tasas = {k: pd.read_excel(RES / "f01_tasas_morosidad.xlsx", sheet_name=k, index_col=0) for k in ["cond", "grado", "grupo_edad", "cohorte"]}
or_sin = pd.read_csv(RES / "f02_modelo_sin_condicion.csv", index_col=0)
or_con = pd.read_csv(RES / "f03_modelo_con_condicion.csv", index_col=0)

# ================================================================== 1. Tramos (primero: otras hojas la referencian)
ws_t = hoja("Tramos", "Cartera por tramos de atraso",
            "Moneda: colones (₡). Texto azul = dato de entrada; negro = fórmula. Fuente: Base_Morosidad_completada.xlsx (427 morosos únicos).",
            [20, 12, 14, 18, 14, 4])
encabezado(ws_t, 4, ["Tramo de atraso", "Personas", "% de personas", "Deuda (₡)", "% de la deuda"])
g = df.groupby("tramo_atraso", observed=False).agg(n=("deuda", "size"), monto=("deuda", "sum")).reindex(ORDEN_TRAMOS)
f0 = 5
for i, (tr, r) in enumerate(g.iterrows()):
    f = f0 + i
    celda(ws_t, f, 1, tr.replace("meses", "meses"))
    celda(ws_t, f, 2, int(r["n"]), ENT, entrada=True)
    celda(ws_t, f, 3, f"=B{f}/B${f0 + 6}", PCT)
    celda(ws_t, f, 4, float(r["monto"]), CRC, entrada=True)
    celda(ws_t, f, 5, f"=D{f}/D${f0 + 6}", PCT)
ft = f0 + 6
for c, v, fm in [(1, "Total", None), (2, f"=SUM(B{f0}:B{ft - 1})", ENT), (3, f"=SUM(C{f0}:C{ft - 1})", PCT),
                 (4, f"=SUM(D{f0}:D{ft - 1})", CRC), (5, f"=SUM(E{f0}:E{ft - 1})", PCT)]:
    celda(ws_t, ft, c, v, fm, negrita=True, fill=TOTAL_FILL)
ws_t.cell(ft + 2, 1, "Nota: el atraso se registra en meses (mínimo 4). En los tramos de 30, 60 y 90 días, el 100% de la cartera cae en 90+ días, por eso se usan tramos en meses.").font = SUB
grafico(ws_t, "G4", "Deuda acumulada por tramo de atraso", Reference(ws_t, min_col=1, min_row=f0, max_row=ft - 1),
        Reference(ws_t, min_col=4, min_row=4, max_row=ft - 1), "Colones", '#,##0,,"M"')
grafico(ws_t, "G20", "Personas por tramo de atraso", Reference(ws_t, min_col=1, min_row=f0, max_row=ft - 1),
        Reference(ws_t, min_col=2, min_row=4, max_row=ft - 1), "Personas")
TR_TOTAL_N, TR_TOTAL_D = f"Tramos!$B${ft}", f"Tramos!$D${ft}"

# ================================================================== 2. Perfil
ws_p = hoja("Perfil", "Perfil de las personas morosas",
            "n = 427 morosos únicos. Texto azul = dato de entrada; negro = fórmula. Fuente: Base_Morosidad_completada.xlsx.",
            [26, 12, 14, 4, 4])
bloques = [
    ("Sexo", df["sexo"].value_counts(), ["Mujer", "Hombre"]),
    ("Grupo de edad", df["grupo_edad"].value_counts(), ["<35", "35-44", "45-54", "55-64", "65+"]),
    ("Institución", df["institucion"].value_counts(), ["Institución Pública", "No labora", "Institución Privada", "Consultoría/propio"]),
    ("Condición", df["condicion"].fillna("Sin dato").value_counts(), ["Inactivo", "Activo", "Arreglo de pago", "Artículo 7 (65+ años)", "Sin dato"]),
    ("Grado académico", df["grado"].fillna("Sin dato").value_counts(), ["Bachillerato", "Licenciatura", "Maestría", "Doctorado", "Sin dato"]),
]
fila = 4
anclas_perfil = []
for titulo, vc, orden in bloques:
    ws_p.cell(fila, 1, titulo).font = NEGRITA
    encabezado(ws_p, fila + 1, [titulo, "Personas", "% del total"])
    ini = fila + 2
    for i, k in enumerate(orden):
        f = ini + i
        celda(ws_p, f, 1, k)
        celda(ws_p, f, 2, int(vc.get(k, 0)), ENT, entrada=True)
        celda(ws_p, f, 3, f"=B{f}/B${ini + len(orden)}", PCT)
    fin = ini + len(orden)
    celda(ws_p, fin, 1, "Total", negrita=True, fill=TOTAL_FILL)
    celda(ws_p, fin, 2, f"=SUM(B{ini}:B{fin - 1})", ENT, negrita=True, fill=TOTAL_FILL)
    celda(ws_p, fin, 3, f"=SUM(C{ini}:C{fin - 1})", PCT, negrita=True, fill=TOTAL_FILL)
    anclas_perfil.append((titulo, ini, fin - 1, fila))
    fila = fin + 3
for k, (titulo, ini, fin, f_ini) in enumerate(anclas_perfil):
    grafico(ws_p, f"I{4 + k * 17}", f"Morosos por {titulo.lower()}", Reference(ws_p, min_col=1, min_row=ini, max_row=fin),
            Reference(ws_p, min_col=2, min_row=ini - 1, max_row=fin), "Personas", w=14, h=7.5)

# institución: segmentación
fila_i = fila
ws_p.cell(fila_i, 1, "Segmentación por institución").font = NEGRITA
encabezado(ws_p, fila_i + 1, ["Institución", "Personas", "Deuda total (₡)", "Edad mediana", "Atraso mediano (meses)", "Deuda mediana (₡)", "% de la deuda"])
for c in range(4, 8):
    ws_p.column_dimensions[get_column_letter(c)].width = 14
seg = df.groupby("institucion").agg(n=("deuda", "size"), tot=("deuda", "sum"), ed=("edad", "median"),
                                    me=("meses_atraso", "median"), dm=("deuda", "median")).sort_values("tot", ascending=False)
ini = fila_i + 2
for i, (k, r) in enumerate(seg.iterrows()):
    f = ini + i
    celda(ws_p, f, 1, k)
    celda(ws_p, f, 2, int(r.n), ENT, entrada=True)
    celda(ws_p, f, 3, float(r.tot), CRC, entrada=True)
    celda(ws_p, f, 4, float(r.ed), "0", entrada=True)
    celda(ws_p, f, 5, float(r.me), "0.0", entrada=True)
    celda(ws_p, f, 6, float(r.dm), CRC, entrada=True)
    celda(ws_p, f, 7, f"=C{f}/C${ini + len(seg)}", PCT)
fin = ini + len(seg)
celda(ws_p, fin, 1, "Total", negrita=True, fill=TOTAL_FILL)
celda(ws_p, fin, 2, f"=SUM(B{ini}:B{fin - 1})", ENT, negrita=True, fill=TOTAL_FILL)
celda(ws_p, fin, 3, f"=SUM(C{ini}:C{fin - 1})", CRC, negrita=True, fill=TOTAL_FILL)
celda(ws_p, fin, 7, f"=SUM(G{ini}:G{fin - 1})", PCT, negrita=True, fill=TOTAL_FILL)
for c in (4, 5, 6):
    celda(ws_p, fin, c, None, fill=TOTAL_FILL)
fila_r = fin + 2
ws_p.cell(fila_r, 1, "Estadísticos generales").font = NEGRITA
stats = [("Edad mediana (años)", float(df.edad.median()), "0"), ("Atraso mediano (meses)", float(df.meses_atraso.median()), "0"),
         ("Deuda mediana por persona (₡)", float(df.deuda.median()), CRC), ("Deuda media por persona (₡)", float(df.deuda.mean()), CRC)]
for i, (k, v, fm) in enumerate(stats):
    celda(ws_p, fila_r + 1 + i, 1, k)
    celda(ws_p, fila_r + 1 + i, 2, v, fm, entrada=True)
ws_p.column_dimensions["A"].width = 30
MED_DEUDA = f"Perfil!$B${fila_r + 3}"
MED_ATRASO = f"Perfil!$B${fila_r + 2}"

# ================================================================== 3. Tasas por factor
ws_f = hoja("Factores", "Tasa de morosidad por factor (padrón completo vs. morosos)",
            "Colegiados = padrón de 914 personas; morosos = personas del padrón presentes en la base de morosidad (423 con datos cruzados). Azul = dato; negro = fórmula.",
            [18, 24, 12, 11, 11, 11, 11])
ws_f["A3"], ws_f["A3"].font = "Valor z (IC 95%)", NORMAL
celda(ws_f, 3, 2, 1.96, "0.00", entrada=True)
ws_f["C3"], ws_f["C3"].font = "Supuesto: intervalo de Wilson al 95%.", SUB
encabezado(ws_f, 5, ["Factor", "Grupo", "Colegiados", "Morosos", "Tasa de morosidad", "IC 95% inferior", "IC 95% superior"])
orden_cond = ["Activo", "Inactivo", "Arreglo de pago", "Artículo 7 (65+ años)", "Miembro Honorario"]
conj = [("Condición", tasas["cond"], orden_cond),
        ("Incorporación", tasas["cohorte"], list(tasas["cohorte"].index)),
        ("Grado", tasas["grado"], ["Bachillerato", "Licenciatura", "Maestría", "Doctorado"]),
        ("Edad", tasas["grupo_edad"], list(tasas["grupo_edad"].index))]
f = 6
bloques_f = {}
for factor, t, orden in conj:
    ini = f
    for k in orden:
        celda(ws_f, f, 1, factor)
        celda(ws_f, f, 2, str(k))
        celda(ws_f, f, 3, int(t.loc[k, "colegiados"]), ENT, entrada=True)
        celda(ws_f, f, 4, int(t.loc[k, "morosos"]), ENT, entrada=True)
        celda(ws_f, f, 5, f"=D{f}/C{f}", PCT)
        celda(ws_f, f, 6, f"=(E{f}+$B$3^2/(2*C{f})-$B$3*SQRT(E{f}*(1-E{f})/C{f}+$B$3^2/(4*C{f}^2)))/(1+$B$3^2/C{f})", PCT)
        celda(ws_f, f, 7, f"=(E{f}+$B$3^2/(2*C{f})+$B$3*SQRT(E{f}*(1-E{f})/C{f}+$B$3^2/(4*C{f}^2)))/(1+$B$3^2/C{f})", PCT)
        f += 1
    bloques_f[factor] = (ini, f - 1)
# total (se calcula sobre el bloque Condición, que cubre a los 914)
c0, c1 = bloques_f["Condición"]
celda(ws_f, f, 1, "Total padrón", negrita=True, fill=TOTAL_FILL)
celda(ws_f, f, 2, None, fill=TOTAL_FILL)
celda(ws_f, f, 3, f"=SUM(C{c0}:C{c1})", ENT, negrita=True, fill=TOTAL_FILL)
celda(ws_f, f, 4, f"=SUM(D{c0}:D{c1})", ENT, negrita=True, fill=TOTAL_FILL)
celda(ws_f, f, 5, f"=D{f}/C{f}", PCT, negrita=True, fill=TOTAL_FILL)
celda(ws_f, f, 6, None, fill=TOTAL_FILL); celda(ws_f, f, 7, None, fill=TOTAL_FILL)
F_TOTAL = f
ws_f.cell(f + 2, 1, "Nota: la condición se mide al corte del padrón (2-sep-2026) y puede ser consecuencia de la morosidad, no su causa. Miembro Honorario (1 persona) se omite del gráfico.").font = SUB
pos = [("Condición", "I5", c0, c0 + 3), ("Incorporación", "I21", *bloques_f["Incorporación"]),
       ("Grado", "S5", *bloques_f["Grado"]), ("Edad", "S21", *bloques_f["Edad"])]
for factor, anc, a, b in pos:
    grafico(ws_f, anc, f"Tasa de morosidad según {factor.lower()}", Reference(ws_f, min_col=2, min_row=a, max_row=b),
            Reference(ws_f, min_col=5, min_row=a, max_row=b), "% de colegiados morosos", fmt="0%", w=15, h=7.5)
ws_f.column_dimensions["A"].width = 16

# ================================================================== 4. Modelos
ws_m = hoja("Modelos", "Modelos de regresión logística (odds ratios)",
            "Odds ratio > 1: más probabilidad de morosidad. Se excluyen las 14 personas con arreglo de pago (todas morosas por definición). Valores calculados en Python (statsmodels).",
            [46, 14, 14, 14, 12, 4])


def tabla_or(ws, fila, titulo, o, auc):
    ws.cell(fila, 1, titulo).font = NEGRITA
    encabezado(ws, fila + 1, ["Variable", "Odds ratio", "IC 95% inferior", "IC 95% superior", "Valor p"])
    for i, (k, r) in enumerate(o.iterrows()):
        f = fila + 2 + i
        celda(ws, f, 1, k)
        for j, c in enumerate(["odds_ratio", "IC95_inf", "IC95_sup"], 2):
            celda(ws, f, j, float(r[c]), "0.00", entrada=True)
        celda(ws, f, 5, float(r["p_valor"]), "0.000", entrada=True)
    f = fila + 2 + len(o)
    celda(ws, f, 1, "Poder de predicción (AUC, validación cruzada)", negrita=True, fill=TOTAL_FILL)
    celda(ws, f, 2, auc, "0.00", entrada=True, fill=TOTAL_FILL)
    return f + 3


fila = tabla_or(ws_m, 4, "Modelo sin condición (edad, antigüedad, grado)", or_sin, 0.56)
fila = tabla_or(ws_m, fila, "Modelo con condición", or_con, 0.92)
ws_m.cell(fila, 1, "Lectura: sin la condición, las variables disponibles casi no predicen la morosidad (AUC cercano a 0,5). Estar inactivo multiplica el odds por ~173.").font = SUB

# ================================================================== 5. Cobro
ws_c = hoja("Cobro", "Prioridad de cobro (propuesta)", "A = colegiado activo o con arreglo y hasta 24 meses de atraso; B = activo/arreglo con más atraso; C = inactivo o sin dato.",
            [46, 12, 18, 14, 4])
d2 = df.copy()
act = d2["condicion"].isin(["Activo", "Arreglo de pago"])
d2["prio"] = "C - Inactivo o sin dato (cobro difícil)"
d2.loc[act, "prio"] = "B - Activo con atraso largo (>24 meses)"
d2.loc[act & (d2.meses_atraso <= 24), "prio"] = "A - Activo o con arreglo, atraso hasta 24 meses"
pr = d2.groupby("prio").agg(n=("deuda", "size"), tot=("deuda", "sum"))
encabezado(ws_c, 4, ["Prioridad", "Personas", "Deuda (₡)", "% de la deuda"])
for i, (k, r) in enumerate(pr.iterrows()):
    f = 5 + i
    celda(ws_c, f, 1, k)
    celda(ws_c, f, 2, int(r.n), ENT, entrada=True)
    celda(ws_c, f, 3, float(r.tot), CRC, entrada=True)
    celda(ws_c, f, 4, f"=C{f}/C$8", PCT)
celda(ws_c, 8, 1, "Total", negrita=True, fill=TOTAL_FILL)
celda(ws_c, 8, 2, "=SUM(B5:B7)", ENT, negrita=True, fill=TOTAL_FILL)
celda(ws_c, 8, 3, "=SUM(C5:C7)", CRC, negrita=True, fill=TOTAL_FILL)
celda(ws_c, 8, 4, "=SUM(D5:D7)", PCT, negrita=True, fill=TOTAL_FILL)
grafico(ws_c, "F4", "Deuda por prioridad de cobro", Reference(ws_c, min_col=1, min_row=5, max_row=7),
        Reference(ws_c, min_col=3, min_row=4, max_row=7), "Colones", '#,##0,,"M"', w=16)

# ================================================================== 6. Calidad
ws_q = hoja("Calidad", "Calidad de los datos", "Problemas detectados y acción tomada.", [30, 12, 56, 52])
encabezado(ws_q, 4, ["Problema", "Base", "Hallazgo", "Acción"])
filas_q = [
    ("Filas duplicadas", "Morosos", "2 pares idénticos en las 9 columnas; la base no tiene identificador", "Se eliminó una fila de cada par; confirmar en la fuente"),
    ("Institución: espacios y mayúsculas", "Morosos", "9 categorías aparentes, en realidad 4", "Unificadas en 4"),
    ("Condición y grado con espacios", "Padrón", "215 celdas", "Espacios recortados"),
    ("Grado con mayúsculas inconsistentes", "Padrón", "2 casos ('licenciatura')", "Unificado"),
    ("Valores faltantes", "Morosos", "4 registros sin condición, grado ni fecha (sin coincidencia en la segunda base)", "Conservados para edad, sexo, institución y deuda; excluidos de los análisis de factores"),
    ("Emparejamiento dudoso", "Morosos", "41 con sexo en conflicto y 88 con sexo no verificable", "No eliminados; sus datos cruzados pueden tener errores"),
    ("Atraso mayor que la antigüedad", "Morosos", "20 registros con más meses de atraso que meses de colegiatura", "Sin cambios; revisar en la fuente"),
    ("Carné no coincide con la fecha", "Padrón", "109 casos (47 con 1 año de diferencia; 50 con 23-24 años)", "No corregido; el carné no se usó"),
    ("Deuda = cuota fija × meses", "Morosos", "Cuota implícita de ₡5.861 por mes (rango ₡5.333 a ₡7.000)", "La deuda no aporta información independiente"),
]
for i, fila_q in enumerate(filas_q):
    for j, v in enumerate(fila_q, 1):
        celda(ws_q, 5 + i, j, v, wrap=True)
    ws_q.row_dimensions[5 + i].height = 32

# ================================================================== 0. Resumen
ws = wb["Sheet"]
ws.title = "Resumen"
ws.sheet_view.showGridLines = False
ws.column_dimensions["A"].width = 46
ws.column_dimensions["B"].width = 22
ws.column_dimensions["C"].width = 70
ws["A1"], ws["A1"].font = "Informe de morosidad – Colegio de Profesionales en Sociología", TITULO
ws["A2"], ws["A2"].font = "Moneda: colones. Los indicadores se calculan con fórmulas desde las demás hojas. Corte del padrón: 2-sep-2026.", SUB
encabezado(ws, 4, ["Indicador", "Valor", "Detalle"])
kpis = [
    ("Personas morosas (únicas)", f"={TR_TOTAL_N}", ENT, "Base de morosidad tras eliminar duplicados"),
    ("Deuda acumulada (₡)", f"={TR_TOTAL_D}", CRC, "Suma de la deuda de todas las personas morosas"),
    ("Colegiados en el padrón", f"=Factores!C{F_TOTAL}", ENT, "Todas las condiciones"),
    ("Tasa de morosidad", f"=Factores!E{F_TOTAL}", PCT, "Morosos con datos cruzados / colegiados del padrón"),
    ("Deuda mediana por persona (₡)", f"={MED_DEUDA}", CRC, "Mitad de los morosos debe menos que esto"),
    ("Atraso mediano (meses)", f"={MED_ATRASO}", "0", "Equivale a unos 3,8 años"),
    ("Tasa de morosidad: inactivos", f"=Factores!E{bloques_f['Condición'][0] + 1}", PCT, "Factor principal"),
    ("Tasa de morosidad: activos", f"=Factores!E{bloques_f['Condición'][0]}", PCT, "La condición puede ser consecuencia de la mora"),
    ("Deuda en tramo 97+ meses", f"=Tramos!E{f0 + 5}", PCT, "% de la deuda total que llevan más de 8 años en atraso"),
    ("Deuda recuperable (prioridad A)", "=Cobro!D5", PCT, "% de la deuda de personas activas o con arreglo y atraso hasta 24 meses"),
]
for i, (a, b, fm, c) in enumerate(kpis):
    celda(ws, 5 + i, 1, a, negrita=True)
    celda(ws, 5 + i, 2, b, fm)
    celda(ws, 5 + i, 3, c)
ws["A16"], ws["A16"].font = "Hallazgos principales", NEGRITA
hall = [
    "1. La morosidad se concentra en personas inactivas: 93% de los inactivos frente a 7% de los activos (hoja Factores).",
    "2. La cohorte incorporada en 2018-2021 tiene la tasa más alta (61%); la de 2022-2026, la más baja (28%).",
    "3. Edad y sexo explican poco; tener licenciatura se asocia con menos morosidad que el bachillerato (hoja Modelos).",
    "4. El 17% de los morosos, con más de 8 años de atraso, acumula el 35% de la deuda (hoja Tramos).",
    "5. Solo 1,4% de la deuda corresponde a personas activas o con arreglo y hasta 24 meses de atraso (hoja Cobro).",
]
for i, t in enumerate(hall):
    ws.cell(17 + i, 1, t).font = NORMAL
ws["A23"], ws["A23"].font = "Limitaciones: asociaciones, no causas. Sexo e institución no están en el padrón. Ver hoja Calidad.", SUB
ws["A24"], ws["A24"].font = "Leyenda: texto azul = dato de entrada tomado de los scripts de análisis; texto negro = fórmula.", SUB

wb._sheets = [wb[n] for n in ["Resumen", "Tramos", "Perfil", "Factores", "Modelos", "Cobro", "Calidad"]]
wb.save(SALIDA)
print("Guardado:", SALIDA)
