# Predicción de energía eléctrica facturada — Avance Presentación 1

Guión de contenidos para la presentación. Estructura en 16 diapositivas con notas de expositor.
Todos los valores numéricos citados provienen de los reportes en `reports/`.

---

## Diapositiva 1 — Portada

- **Título:** *Predicción de energía eléctrica facturada en Chile - Avance 1*
- **Texto:** Equipo, asignatura, profesor, fecha (2026).
- **Gráfico:** Logo institucional / silueta de Chile.
- **Nota del expositor:** "Trabajamos con datos públicos del sector eléctrico chileno (2015-2024) para predecir cuánta energía se factura cada mes a nivel comuna × tipo cliente × tarifa."

---

## Diapositiva 2 — Contexto y motivación

- **Título:** *¿Por qué predecir el consumo eléctrico?*
- **Texto (bullets):**
  - Sector estratégico: planificación, tarifas, integración de ERNC.
  - Datos públicos abiertos a nivel comunal y de sistema (SEN).
  - Aplicaciones: planificación de infraestructura, detección de anomalías, soporte a políticas tarifarias.
- **Gráfico:** [`reports/figures_v2/01_evolucion_mensual_nacional.png`](figures_v2/01_evolucion_mensual_nacional.png)
- **Nota del expositor:** "La energía facturada es un proxy del consumo real; sus variaciones reflejan crecimiento, estacionalidad moderada y eventos específicos."

---

## Diapositiva 3 — Pregunta de investigación

- **Título:** *Pregunta principal*
- **Texto:**
  > ¿Podemos predecir la energía total mensual facturada (kWh) por comuna / tipo cliente / tarifa usando datos históricos y contexto del sistema eléctrico?
- **Subtexto:** Target principal: `energia_kwh`. Target alternativo: `consumo_promedio_cliente_kwh` (no priorizado en esta entrega).
- **Gráfico:** ninguno.
- **Nota del expositor:** "Elegimos `energia_kwh` porque es la variable operativa relevante y permite resultados preliminares robustos."

---

## Diapositiva 4 — Tipo de problema

- **Título:** *Tipo de problema*
- **Texto:**
  - Aprendizaje **supervisado**.
  - Tarea de **regresión** (target continuo `energia_kwh`).
  - Estructura **panel temporal**: unidad = `region × comuna × tipo_clientes × tarifa`, eje temporal = mes (2015-01 a 2024-12).
  - Equivale a un conjunto de **series de tiempo múltiples** mensuales.
  - **Métrica análoga a `accuracy` para regresión: R²** (coeficiente de determinación). `accuracy` no aplica.
- **Gráfico:** Diagrama esquemático del panel temporal.
- **Nota del expositor:** "No es una sola serie nacional ni clasificación: es un panel longitudinal con miles de series mensuales que comparten estructura."

---

## Diapositiva 5 — Metodología OSEMN

- **Título:** *Framework metodológico - OSEMN*
- **Texto:**
  - **O**btain — descarga de datasets públicos.
  - **S**crub — limpieza, anomalías, formatos.
  - **E**xplore — EDA descriptivo, **heatmap de correlación**.
  - **M**odel — comparación de 7 modelos, selección formal.
  - i**N**terpret — variable dominante, limitaciones, próximos pasos.
- **Gráfico:** Pipeline horizontal con los 5 pasos.
- **Nota del expositor:** "OSEMN guía la entrega; usamos un loop honesto Modelo ↔ Interpretación antes de subir complejidad."

---

## Diapositiva 6 — Fuentes de datos y períodos

- **Título:** *Datos utilizados*
- **Texto:**
  - **Facturación clientes regulados** (CSV mensual, 490 753 filas, 2015-01 → 2024-12). Fuente: portal de datos públicos del sector eléctrico chileno (CNE / Energía Abierta). **URL exacta: pendiente de confirmar antes de la presentación**, no se inventa.
  - **Demanda diaria SEN** (Coordinador Eléctrico Nacional), agregada a mensual con lags L1/L2/L3.
  - **Generación programada por fuente** (Coordinador Eléctrico Nacional). Variables: `proporcion_ernc`, `proporcion_hidro`, `total_generacion` con lags L1/L2/L3.
  - **Período integrado con auxiliares:** 2018-01 → 2024-12 (84 meses).
- **Gráfico:** ninguno; slide de texto/links.
- Fuente pendiente de confirmar.

---

## Diapositiva 7 — Preparación y calidad de datos

- **Título:** *Preparación y calidad*
- **Texto:**
  - Dataset base limpio (`facturacion_clean.parquet`): 490 753 filas × 12 columnas, 16 regiones, 330 comunas, 31 tarifas.
  - **Anomalías documentadas (no removidas en `clean`)**:
    - `energia_kwh < 0`: 1 191 (≈ 0.24 %) → plausible refacturación / generación distribuida.
    - `energia_kwh == 0`: 13 283 (≈ 2.7 %) → ceros **reales del dataset original**, no producto de lags.
    - `clientes_facturados ≤ 0`: 6 624.
    - 5 275 filas en grupos no únicos sobre `(fecha, region, comuna, tipo_clientes, tarifa)` → falta una dimensión en la clave panel.
  - Consistencia `energia_kwh ≈ e1 + e2`: 441 198 / 443 025 cuadran (|Δ| ≤ 1).
  - **Tratamiento aplicado**: imputación en pipeline; **vista filtrada** `energia>0 & cf>0` se aplica **sólo dentro del modelo**, sin tocar `clean`.
  - Auxiliares: 18 columnas lag (L1/L2/L3), **sin variables del mismo mes** (no hay leakage temporal).
  - **Aclaración importante**: los **ceros del target** son del dataset original; los **nulos en `_L1/_L2/_L3`** vienen del diseño temporal de los lags. Son fenómenos **distintos**.
- **Gráfico:** [`reports/figures_v2/06_anomalias_por_anio.png`](figures_v2/06_anomalias_por_anio.png)
- **Nota del expositor:** "Mantenemos `clean` intacto y trazable; las decisiones quedan en `reports/calidad_target_energia.md`."

---

## Diapositiva 8 — EDA: hallazgos verificados

- **Título:** *Hallazgos del análisis exploratorio*
- **Texto (cifras del repo):**
  - **Tipo cliente**: Residencial 146 TWh vs No Residencial 131 TWh (2015–2024 acumulado). Razón ≈ **1.11×**, no 3-4×. Hasta 2017 dominaba No Residencial; desde 2019 Residencial supera.
  - **Top regiones acumuladas (TWh)**: RM 124.6 >> Valparaíso 27.8 > Biobío 20.4 > Maule 16.5 > O'Higgins 15.1. Antofagasta está en posición 9 (8.3 TWh) — no entre las líderes.
  - **Estacionalidad**: máximo agregado nacional en julio, mínimo en noviembre; amplitud ≈ 23 %. Moderada a nivel nacional.
  - **Distribución del target**: muy sesgada (cola larga).
- **Gráfico recomendado:** [`reports/figures_v2/02_evolucion_tipo_cliente.png`](figures_v2/02_evolucion_tipo_cliente.png) y [`reports/figures_v2/03_energia_por_region.png`](figures_v2/03_energia_por_region.png).
- **Nota del expositor:** "Hay heterogeneidad fuerte entre comunas/tipos. Esto justifica modelar a nivel panel y no agregar al país."

---

## Diapositiva 9 — Correlation heatmap

- **Título:** *Correlación entre variables numéricas*
- **Texto:**
  - Pearson sobre la vista filtrada (`energia > 0 & cf > 0`):

    | variable | energia_kwh | clientes_facturados | anio | mes |
    |---|---:|---:|---:|---:|
    | energia_kwh | 1.000 | **0.886** | -0.005 | -0.003 |
    | clientes_facturados | **0.886** | 1.000 | 0.005 | -0.001 |
    | anio | -0.005 | 0.005 | 1.000 | -0.076 |
    | mes | -0.003 | -0.001 | -0.076 | 1.000 |

  - Pearson en **log-log** (`log1p(energia)` vs `log1p(cf)`) = **0.818**, Spearman log = 0.874.
  - **Advertencia metodológica**: el heatmap **no captura** el efecto de variables categóricas (`region`, `comuna`, `tarifa`, `tipo_clientes`). Ese efecto se mide indirectamente en el modelo vía OneHotEncoder.
- **Gráfico:** [`reports/figures_v2/13_matriz_correlacion_numerica.png`](figures_v2/13_matriz_correlacion_numerica.png) y [`reports/figures_v2/14_matriz_correlacion_log.png`](figures_v2/14_matriz_correlacion_log.png).
- **Nota del expositor:** "La única correlación lineal alta entre numéricas es `clientes_facturados` con `energia_kwh` (0.89). Año y mes no aportan linealmente, pero el modelo de árboles captura la estacionalidad de forma no lineal."

---

## Diapositiva 10 — Diseño del primer modelo

- **Título:** *Diseño experimental - modelo v2*
- **Texto:**
  - 4 escenarios para honestar el aporte de cada feature:
    - **A**. Base con `clientes_facturados` (referencia).
    - **B**. Base **sin** `clientes_facturados` (mide señal puramente identitaria + temporal).
    - **C**. A filtrado `energia>0 & cf>0`.
    - **D**. Con auxiliares (lags L1/L2/L3 de demanda SEN y generación).
  - **Validación temporal**: split por **fecha única** 80/20, cohorte 2018-04 → 2024-12 (81 meses). Train 64 meses, test 17 meses. `max(train) < min(test)` verificado.
  - Métricas reportadas: MAE, MSE, RMSE, R², MAPE. MAPE válido sólo en la vista filtrada (`y_true > 0`).
- **Gráfico:** Diagrama de la línea temporal con corte train/test.
- **Nota del expositor:** "El experimento está diseñado para que cualquier diferencia entre A y B se atribuya a una sola variable: `clientes_facturados`."

---

## Diapositiva 11 — Selección formal del modelo (slide nueva)

- **Título:** *Selección de modelo - 7 regresores comparados*
- **Texto:**
  - Modelos comparados: Dummy(mean), LinearRegression, Ridge(α=1), DecisionTree(d=10), RandomForest(n=100, d=10), ExtraTrees(n=100, d=10), KNN(k=5, scaled).
  - Mismas features, mismo split temporal, misma vista filtrada.
  - **`accuracy` NO aplica** (problema de regresión). La métrica análoga es **R²**.

  | Modelo | MAE | MSE | RMSE | R² | MAPE |
  |---|---:|---:|---:|---:|---:|
  | RandomForest(n=100, d=10) | **127 376** | 1.54e+11 | **392 873** | **0.9699** | **7.77** |
  | ExtraTrees(n=100, d=10) | 139 120 | 1.54e+11 | 392 524 | 0.9700 | 58.28 |
  | DecisionTree(d=10) | 138 622 | 2.05e+11 | 452 808 | 0.9601 | 7.52 |
  | KNN(k=5, scaled, submuestra 50k) | 160 964 | 3.32e+11 | 575 965 | 0.9354 | 30.07 |
  | LinearRegression | 330 804 | 5.86e+11 | 765 216 | 0.8860 | 286.42 |
  | Ridge(α=1) | 331 047 | 5.86e+11 | 765 307 | 0.8860 | 283.57 |
  | DummyRegressor(mean) | 804 823 | 5.14e+12 | 2 266 224 | -0.0000 | 699.63 |

- **Notas en la slide**:
  - ExtraTrees y RandomForest están en **empate técnico** (|ΔR²| < 0.001). Desempate por **menor MAE** → ganador **RandomForest**.
  - **KNN** entrenado sobre submuestra de 50 000 filas del train para evitar O(n²) con OHE de alta cardinalidad; comparación es informativa, no estrictamente justa.
- **Gráfico:** [`reports/figures_v2/08_comparacion_r2_modelos.png`](figures_v2/08_comparacion_r2_modelos.png) y [`reports/figures_v2/09_comparacion_rmse_modelos.png`](figures_v2/09_comparacion_rmse_modelos.png).
- **Nota del expositor:** "Probamos siete modelos. Los lineales se quedan cortos (R² ≈ 0.89). Los árboles llegan a R² ≈ 0.97. Elegimos RandomForest porque empata en R² con ExtraTrees pero gana claramente en MAE y MAPE."

---

## Diapositiva 12 — Resultados del mejor modelo y comparación con/sin `cf`

- **Título:** *Resultados RandomForest entre escenarios*
- **Texto:**

  | Escenario | n train | n test | MAE | RMSE | R² |
  |---|---:|---:|---:|---:|---:|
  | A. Base con `clientes_facturados` | 265 558 | 71 985 | 124 419 | 391 092 | **0.9694** |
  | B. Base sin `clientes_facturados` | 265 558 | 71 985 | 334 624 | 1 003 554 | 0.7988 |
  | C. A filtrado (`energia>0 & cf>0`) | 257 663 | 70 047 | 127 376 | 392 873 | **0.9699** |
  | D. Con auxiliares (lags L1/L2/L3) | 265 558 | 71 985 | 185 707 | 1 121 251 | 0.7489 |

  - Diferencia A vs B: **ΔR² ≈ +0.17** atribuible a `clientes_facturados`.
  - C ≈ A (mejora marginal +0.0005 al filtrar ceros/negativos).
  - **D no ayuda**: los auxiliares son agregados SEN nacionales, idénticos para todas las filas del mismo mes → sin varianza intra-mes.
- **Gráfico:** [`reports/figures_v2/11_prediccion_vs_real.png`](figures_v2/11_prediccion_vs_real.png) y [`reports/figures_v2/12_residuos_modelo.png`](figures_v2/12_residuos_modelo.png).
- **Nota del expositor:** "El R² alto del escenario A está dominado por `clientes_facturados`. La pregunta interesante es B/C, donde se mide el aporte real del modelo."

---

## Diapositiva 13 — Variable dominante: `clientes_facturados` (slide nueva)

- **Título:** *Una variable explica la mayor parte del R²*
- **Texto:**
  - Evidencia cuantitativa (vista filtrada completa, sólo cohorte 2018-04 → 2024-12):
    - Pearson(`cf`, `energia`) = **0.886**.
    - Spearman = 0.874.
    - Pearson log-log = 0.818, Spearman log = 0.874.
    - R² univariado (sólo `cf` → `energia`, regresión lineal, split temporal) = **0.8414**.
    - Feature importance del RandomForest: `clientes_facturados` ≈ **0.89** (≈ 89 % de la importancia total).
  - Modelo v2: con `cf` R² = 0.97 vs sin `cf` R² = 0.80 → **ΔR² ≈ 0.17 atribuible a esta única variable**.

  **¿Es leakage?**
  - Temporal **estricto**: no. `cf` se conoce al facturar el mismo mes, no usa información futura.
  - Práctico de **utilidad**: sí es problemático para predicción futura real. Conviene usar `clientes_facturados_L1`.

- **Gráfico:** [`reports/figures_v2/15_clientes_vs_energia_loglog.png`](figures_v2/15_clientes_vs_energia_loglog.png).
- **Nota del expositor:** "`clientes_facturados` es la variable estrella. No es leakage temporal, pero es casi contemporánea con el target — el R² alto se apoya en una identidad estructural. En la siguiente entrega usaremos su lag para una evaluación predictiva más honesta."

---

## Diapositiva 14 — Feature importance del mejor modelo (slide nueva)

- **Título:** *Importancia de variables (RandomForest)*
- **Texto:**
  - Top 10 importancias (sobre features post-OHE):

    | feature | importance |
    |---|---:|
    | clientes_facturados | 0.886 |
    | tarifa_AT4.3 | 0.028 |
    | comuna_Santiago | 0.018 |
    | region_Región Metropolitana de Santiago | 0.014 |
    | mes | 0.013 |
    | comuna_Las Condes | 0.007 |
    | anio | 0.007 |
    | tarifa_BT4.3 | 0.003 |
    | comuna_Providencia | 0.002 |
    | tarifa_BT3PP | 0.002 |

  - Después de `clientes_facturados`, las features importantes son tarifas industriales (AT4.3, BT4.3), grandes comunas (Santiago, Las Condes) y `mes` (estacionalidad).
- **Gráfico:** [`reports/figures_v2/16_importancia_variables.png`](figures_v2/16_importancia_variables.png).
- **Nota del expositor:** "La importancia confirma lo que sospechábamos: la geografía y la tarifa importan, pero el motor del modelo es el número de clientes facturados. Esto define la agenda de la entrega 2: features que aporten señal independiente."

---

## Diapositiva 15 — Limitaciones (declaradas honestamente)

- **Título:** *Limitaciones reconocidas*
- **Texto:**
  - `clientes_facturados` es **casi-contemporánea** con el target.
  - Auxiliares SEN son agregados **nacionales** → no varían intra-mes.
  - Sin tuning. Sin XGBoost/LightGBM. Sin redes.
  - Cohorte con auxiliares 2018-2024 (más corta que el base 2015-2024).
  - KNN entrenado sobre submuestra para evitar O(n²) con OHE de alta cardinalidad.
  - Heatmap no incluye categóricas.
  - 5 275 filas en grupos no únicos sobre la clave panel → falta una dimensión en el dataset original.
  - Sólo un holdout temporal único (80/20), sin TimeSeriesSplit.
  - URLs exactas de descarga **pendientes de confirmar**.
- **Gráfico:** ninguno; slide tipo lista.
- **Nota del expositor:** "Reconocer las limitaciones es parte de la calidad metodológica que pidió el profesor."

---

## Diapositiva 16 — Próximos pasos

- **Título:** *Próximos pasos hacia la entrega 2*
- **Texto:**
  - Sustituir `clientes_facturados` por su `lag1` para predicción a futuro real.
  - Reformular auxiliares para que **varíen por comuna** (clima, IDH, PIB regional).
  - Tratamiento explícito de outliers; explorar log-target.
  - Probar **XGBoost / LightGBM** con baseline aprobado.
  - **TimeSeriesSplit** con 3-5 folds para estabilidad de métricas.
  - Investigar la dimensión faltante en la clave panel (distribuidora / concesión).
  - Confirmar URLs canónicas de las fuentes.
  - Documentar decisiones en ADR (`/.kb/decisions/`).
- **Gráfico:** Roadmap horizontal hacia la entrega final.
- **Nota del expositor:** "Tenemos un baseline competente y sabemos por dónde subir. La entrega 2 se centra en feature engineering específico y modelos más potentes."

---

## Apéndice (slides opcionales)

- **A1 — Calidad del target**: [`reports/figures_v2/06_anomalias_por_anio.png`](figures_v2/06_anomalias_por_anio.png).
- **A2 — Distribución log**: [`reports/figures_v2/04_distribucion_log_energia.png`](figures_v2/04_distribucion_log_energia.png).
- **A3 — Boxplot por tipo cliente**: [`reports/figures_v2/05_boxplot_tipo_cliente.png`](figures_v2/05_boxplot_tipo_cliente.png).
- **A4 — Energía vs demanda SEN L1**: [`reports/figures_v2/07_energia_vs_demanda_sen_lag1.png`](figures_v2/07_energia_vs_demanda_sen_lag1.png) con disclaimer (serie nacional, no comunal).
- **A5 — Heatmap extendido con auxiliares**: [`reports/figures_v2/13b_corr_heatmap_aux.png`](figures_v2/13b_corr_heatmap_aux.png).
- **A6 — Notebook reproducible**: [`notebooks/analisis_reproducible.ipynb`](../notebooks/analisis_reproducible.ipynb).

---

## Tabla final consolidada (para slide 11 o backup)

| Modelo | MAE | MSE | RMSE | R² | MAPE | nota |
|---|---:|---:|---:|---:|---:|---|
| **RandomForest(n=100,d=10)** | **127 376** | 1.54e+11 | **392 873** | **0.9699** | **7.77** | **modelo seleccionado** |
| ExtraTrees(n=100,d=10) | 139 120 | 1.54e+11 | 392 524 | 0.9700 | 58.28 | empate técnico, peor MAE |
| DecisionTree(d=10) | 138 622 | 2.05e+11 | 452 808 | 0.9601 | 7.52 |  |
| KNN(k=5, scaled) | 160 964 | 3.32e+11 | 575 965 | 0.9354 | 30.07 | submuestra 50k del train |
| LinearRegression | 330 804 | 5.86e+11 | 765 216 | 0.8860 | 286.42 | OHE+scaler |
| Ridge(α=1) | 331 047 | 5.86e+11 | 765 307 | 0.8860 | 283.57 | OHE+scaler |
| DummyRegressor(mean) | 804 823 | 5.14e+12 | 2 266 224 | -0.0000 | 699.63 | baseline |

> `accuracy` no aplica (regresión). MAPE válido sólo en vista filtrada (`y_true > 0`).

---

## Decisiones que quedan pendientes para el equipo

1. Confirmar URL exacta de la fuente de facturación.
2. Decidir si en la presentación se muestra el escenario A (impactante) o A+B (más honesto). Recomendación: **mostrar ambos** para sostener el R² alto sin esconder la dependencia.
3. Decidir si se elimina el dataset duplicado en raw (`...(in)(1).csv` byte-idéntico a `(in).csv`).
4. Verificar qué columnas auxiliares del parquet (`total_hidro_mes_L*`, `total_ernc_mes_L*`) están realmente disponibles antes de citarlas en la presentación.
