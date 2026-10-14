# Factores asociados a la morosidad (padrón completo vs. morosos)

## 1. Calidad de datos del padrón
- Espacios sobrantes corregidos en condición/grado: 215 celdas
- Grado con mayúsculas inconsistentes unificado ('licenciatura'): 2
- Duplicados por carné: 0; por nombre completo: 0
- Valores faltantes en el padrón: 0
- Carné cuyo año no coincide con la fecha de incorporación: 109 (diferencia en años: {-24: 28, -23: 22, -5: 3, -4: 1, -3: 3, -2: 4, -1: 47, 1: 1}); no se corrigió, no se usa el carné en el análisis
- Registros del padrón: 914
- Morosos de la primera base con datos cruzados: 423; sin celda correspondiente en el padrón: 0. Los 4 morosos sin coincidencia en la segunda base se excluyen del análisis de factores.
- Colegiados en celdas con ambigüedad (celda mixta de morosos y no morosos): 41 de 914 (4.5%). No afecta a las tasas ni a los modelos, que usan conteos por celda.

## 2. Tasa de morosidad
**423 de 914 colegiados (46.3%)** están en la base de morosidad.

### Condición (chi-cuadrado p = 8.8e-146)
| cond                  |   colegiados |   morosos |   tasa_% |   IC95_inf_% |   IC95_sup_% |
|:----------------------|-------------:|----------:|---------:|-------------:|-------------:|
| Activo                |        469.0 |      34.0 |      7.2 |          5.2 |         10.0 |
| Arreglo de pago       |         14.0 |      14.0 |    100.0 |         78.5 |        100.0 |
| Artículo 7 (65+ años) |         27.0 |       1.0 |      3.7 |          0.7 |         18.3 |
| Inactivo              |        403.0 |     374.0 |     92.8 |         89.9 |         94.9 |
| Miembro Honorario     |          1.0 |       0.0 |      0.0 |          0.0 |         79.3 |

### Grado académico (chi-cuadrado p = 0.026)
| grado        |   colegiados |   morosos |   tasa_% |   IC95_inf_% |   IC95_sup_% |
|:-------------|-------------:|----------:|---------:|-------------:|-------------:|
| Bachillerato |        436.0 |     219.0 |     50.2 |         45.6 |         54.9 |
| Doctorado    |         11.0 |       3.0 |     27.3 |          9.7 |         56.6 |
| Licenciatura |        407.0 |     169.0 |     41.5 |         36.8 |         46.4 |
| Maestría     |         60.0 |      32.0 |     53.3 |         40.9 |         65.4 |

### Grupo de edad (chi-cuadrado p = 0.072)
| grupo_edad   |   colegiados |   morosos |   tasa_% |   IC95_inf_% |   IC95_sup_% |
|:-------------|-------------:|----------:|---------:|-------------:|-------------:|
| <35          |        240.0 |     102.0 |     42.5 |         36.4 |         48.8 |
| 35-44        |        296.0 |     142.0 |     48.0 |         42.3 |         53.7 |
| 45-54        |        153.0 |      69.0 |     45.1 |         37.4 |         53.0 |
| 55-64        |        109.0 |      44.0 |     40.4 |         31.6 |         49.8 |
| 65+          |        116.0 |      66.0 |     56.9 |         47.8 |         65.5 |

### Año de incorporación (chi-cuadrado p = 2.8e-10)
| cohorte   |   colegiados |   morosos |   tasa_% |   IC95_inf_% |   IC95_sup_% |
|:----------|-------------:|----------:|---------:|-------------:|-------------:|
| 2012-2013 |        364.0 |     151.0 |     41.5 |         36.5 |         46.6 |
| 2014-2017 |        215.0 |     120.0 |     55.8 |         49.1 |         62.3 |
| 2018-2021 |        180.0 |     109.0 |     60.6 |         53.3 |         67.4 |
| 2022-2026 |        155.0 |      43.0 |     27.7 |         21.3 |         35.3 |

Edad mediana: morosos 42 vs. no morosos 41 (Mann-Whitney p = 0.13). Antigüedad mediana: morosos 10.5 vs. no morosos 11.5 años (p = 0.65).

## 3. Modelos logísticos (odds ratios; se excluyen las 14 personas con arreglo de pago, todas morosas por definición)
**Sin condición** (edad, antigüedad, grado):
|                             |   odds_ratio |   IC95_inf |   IC95_sup |   p_valor |
|:----------------------------|-------------:|-----------:|-----------:|----------:|
| grado_g: Licenciatura       |        0.579 |      0.427 |      0.785 |     0.000 |
| grado_g: Maestría/Doctorado |        0.716 |      0.415 |      1.234 |     0.229 |
| edad (+10 años)             |        1.113 |      0.986 |      1.257 |     0.084 |
| antigüedad (+1 año)         |        1.024 |      0.987 |      1.061 |     0.205 |

**Con condición:**
|                                   |   odds_ratio |   IC95_inf |   IC95_sup |   p_valor |
|:----------------------------------|-------------:|-----------:|-----------:|----------:|
| grado_g: Licenciatura             |        1.203 |      0.661 |      2.188 |     0.545 |
| grado_g: Maestría/Doctorado       |        0.906 |      0.307 |      2.675 |     0.858 |
| cond_g: Exento (Art. 7/Honorario) |        0.278 |      0.034 |      2.268 |     0.232 |
| cond_g: Inactivo                  |      173.134 |    101.382 |    295.666 |     0.000 |
| edad (+10 años)                   |        1.234 |      0.962 |      1.582 |     0.098 |
| antigüedad (+1 año)               |        0.988 |      0.922 |      1.059 |     0.738 |

AUC con validación cruzada por celda: sin condición 0.561, con condición 0.92.

## 4. Severidad entre morosos
- Correlación meses de atraso vs. antigüedad (Spearman): 0.10 (p = 0.05).
- Morosos con más meses de atraso que meses de colegiatura (+1): 20 (revisar: el atraso no puede exceder la antigüedad).
- Proporción mediana del tiempo de colegiatura en atraso: 47%.

## 5. Limitaciones
- Solo hay edad, grado, condición y fecha de incorporación en ambas bases; sexo e institución no están en el padrón, por lo que no se pueden comparar contra los no morosos.
- La condición (p. ej. Inactivo) se mide al corte del padrón y puede ser **consecuencia** de la morosidad, no su causa. Por eso se presentan modelos con y sin ella.
- Asociación no implica causalidad.