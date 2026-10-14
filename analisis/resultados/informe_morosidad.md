# Informe de morosidad – Colegio de Profesionales en Sociología

*Moneda: colones (₡). Registros analizados: 427.*

## 1. Calidad de los datos
- Filas idénticas en las 9 columnas eliminadas: 2 (la base no tiene identificador; confirmar que no son personas distintas)
- Categorías de institución normalizadas: 9 -> 4
- Registros sin coincidencia en 2.ª base (condición/grado/fecha vacíos): 4
- La deuda equivale a una cuota casi constante de **₡5,861/mes** de atraso (rango ₡5,333–₡7,000). Es decir, **la deuda es prácticamente función lineal de los meses de atraso**; no aporta información independiente.
- La base contiene **solo personas morosas**: no hay grupo de comparación (al día), por lo que no se puede estimar qué factores *causan* o predicen caer en mora, sino qué se asocia con *mayor atraso/deuda* dentro de los morosos.

## 2. Perfil de las personas morosas (Objetivo 1)
- **Monto total adeudado:** ₡131,119,250; mediana por persona ₡263,750 (media ₡307,071).
- **Atraso:** mediana 45 meses (≈3.8 años); 47% supera 4 años.
- **Sexo:** 66% mujeres.
- **Edad:** mediana 42 años (rango 25–78).
- **Institución:** predomina «Institución Pública» (41%); «No labora» 34%.
- **Condición:** 88% inactivos; 8% activos; 3% con arreglo de pago.
- **Grado:** Bachillerato 51%.
- **Incorporación:** 35% se incorporó en 2012–2013.

### Distribución por tramo de atraso
| tramo_atraso   |   personas |   deuda_total |   %_personas |   %_deuda |
|:---------------|-----------:|--------------:|-------------:|----------:|
| 0-12 meses     |       73.0 |   4,091,000.0 |         17.1 |       3.1 |
| 13-24 meses    |       69.0 |   7,573,000.0 |         16.2 |       5.8 |
| 25-48 meses    |       83.0 |  17,785,750.0 |         19.4 |      13.6 |
| 49-72 meses    |       64.0 |  23,308,500.0 |         15.0 |      17.8 |
| 73-96 meses    |       66.0 |  32,650,750.0 |         15.5 |      24.9 |
| 97+ meses      |       72.0 |  45,710,250.0 |         16.9 |      34.9 |

### Segmentación por institución
| institucion         |   personas |   deuda_total |   deuda_mediana |   meses_mediana |   edad_mediana |   %_deuda |
|:--------------------|-----------:|--------------:|----------------:|----------------:|---------------:|----------:|
| Institución Pública |      176.0 |  49,870,000.0 |       212,000.0 |            36.0 |           51.0 |      38.0 |
| No labora           |      144.0 |  48,876,500.0 |       318,375.0 |            54.5 |           36.0 |      37.3 |
| Institución Privada |       85.0 |  24,546,250.0 |       229,250.0 |            39.0 |           39.0 |      18.7 |
| Consultoría/propio  |       22.0 |   7,826,500.0 |       396,000.0 |            68.0 |           58.0 |       6.0 |

### Prioridad de cobro (propuesta)
| prioridad_cobro                           |   personas |   deuda_total |   %_deuda |
|:------------------------------------------|-----------:|--------------:|----------:|
| A - Recuperable: colegiado activo/arreglo |       30.0 |   1,829,000.0 |       1.4 |
| B - Activo con atraso largo               |       18.0 |   5,794,000.0 |       4.4 |
| C - Inactivo/sin dato (cobro difícil)     |      379.0 | 123,496,250.0 |      94.2 |

## 3. Factores asociados (Objetivo 2)
Pruebas bivariadas con significancia al 5 %:
| variable    | prueba         | vs                  |   estadistico |   p_valor |   tamano_efecto |
|:------------|:---------------|:--------------------|--------------:|----------:|----------------:|
| grupo_edad  | Kruskal-Wallis | meses_atraso        |        37.93  |    0      |           0.08  |
| institucion | Kruskal-Wallis | meses_atraso        |         8.25  |    0.0411 |           0.012 |
| condicion   | Kruskal-Wallis | meses_atraso        |        40.39  |    0      |           0.091 |
| sin_labor   | Kruskal-Wallis | meses_atraso        |         6.91  |    0.0086 |           0.014 |
| edad        | Spearman       | meses_atraso        |         0.145 |    0.0026 |           0.021 |
| institucion | Chi-cuadrado   | condicion==Inactivo |        14.33  |    0.0025 |           0.184 |

Modelo de regresión (log de meses de atraso, errores robustos HC3) – efecto % sobre meses de atraso:
|                                                                    |   efecto_%_sobre_meses |   p_valor |
|:-------------------------------------------------------------------|-----------------------:|----------:|
| Intercept                                                          |                1,318.5 |       0.0 |
| C(sexo)[T.Mujer]                                                   |                    1.9 |       0.8 |
| C(inst_g, Treatment('Institución Pública'))[T.Consultoría/propio]  |                   26.0 |       0.2 |
| C(inst_g, Treatment('Institución Pública'))[T.Institución Privada] |                   24.5 |       0.1 |
| C(inst_g, Treatment('Institución Pública'))[T.No labora]           |                   78.0 |       0.0 |
| C(condicion_g, Treatment('Inactivo'))[T.Activo]                    |                  -65.1 |       0.0 |
| C(condicion_g, Treatment('Inactivo'))[T.Otra]                      |                  -31.2 |       0.1 |
| C(grado_g, Treatment('Bachillerato'))[T.Licenciatura]              |                  -13.3 |       0.1 |
| C(grado_g, Treatment('Bachillerato'))[T.Maestría/Doctorado]        |                    1.8 |       0.9 |
| edad                                                               |                    1.9 |       0.0 |

Regresión logística de ser *Inactivo* (odds ratios):
|                                                                    |   odds_ratio |   IC95_inf |   IC95_sup |   p_valor |
|:-------------------------------------------------------------------|-------------:|-----------:|-----------:|----------:|
| Intercept                                                          |          5.8 |        1.0 |       35.1 |       0.1 |
| C(sexo)[T.Mujer]                                                   |          0.6 |        0.3 |        1.3 |       0.2 |
| C(inst_g, Treatment('Institución Pública'))[T.Consultoría/propio]  |          0.1 |        0.0 |        0.2 |       0.0 |
| C(inst_g, Treatment('Institución Pública'))[T.Institución Privada] |          0.6 |        0.3 |        1.6 |       0.3 |
| C(inst_g, Treatment('Institución Pública'))[T.No labora]           |          0.5 |        0.2 |        1.3 |       0.2 |
| C(grado_g, Treatment('Bachillerato'))[T.Licenciatura]              |          0.5 |        0.2 |        1.0 |       0.0 |
| C(grado_g, Treatment('Bachillerato'))[T.Maestría/Doctorado]        |          0.7 |        0.2 |        3.0 |       0.7 |
| edad                                                               |          1.0 |        1.0 |        1.0 |       0.7 |
| meses_atraso                                                       |          1.0 |        1.0 |        1.0 |       0.0 |

## 4. Limitaciones
- Sin grupo de comparación de personas al día → no se puede modelar el riesgo de caer en mora.
- Deuda y meses de atraso están casi perfectamente relacionadas (cuota fija implícita).
- 4 registros sin coincidencia en la segunda base; calidad de emparejamiento «Revisar» en 41 registros (sexo no coincide) y «Media» en 88: los campos cruzados (condición, grado, fecha) pueden contener errores.
- Asociación no implica causalidad.
