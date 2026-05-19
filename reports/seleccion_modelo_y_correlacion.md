# Selección de modelo + correlación - reporte (presentación 1)

## 1. Objetivo de la etapa

Cerrar la entrega de la Presentación 1 con: (a) selección formal del modelo entre 7 regresores, (b) tabla comparativa con métricas reproducibles, (c) heatmaps de correlación, (d) análisis cuantitativo de `clientes_facturados` como variable dominante, (e) feature importance del mejor modelo basado en árboles.

## 2. Dataset usado

- Archivo: `data/interim/facturacion_clean.parquet` (490 753 filas  12 columnas).
- Cohorte temporal: 2018-04-01 → 2024-12-01 (337 543 filas en cohorte).
- Vista de modelado: `energia_kwh > 0 AND clientes_facturados > 0` → **327 710 filas**.
- El archivo `clean` no se modifica; la vista se aplica sólo dentro del pipeline.

### 2.1 Aclaración importante: ceros del target vs nulos de lags

- Los **ceros de `energia_kwh`** son valores reales del dataset original (13 283 filas en `clean`, 2.7 %). NO son artefactos de generar lags.
- Los **nulos en columnas `_L1`, `_L2`, `_L3`** vienen del diseño temporal de los lags: los primeros meses no tienen historia previa.
- En escenarios con auxiliares, los primeros meses sin lags válidos se eliminan explícitamente (`dropna(subset=lag_cols)`).
- Ambos fenómenos son **distintos** y no deben mezclarse en interpretación.

## 3. Split temporal

- 81 meses únicos, split 80/20.
- Train: 2018-04-01 → 2023-07-01 (64 meses  257 663 filas).
- Test:  2023-08-01 → 2024-12-01 (17 meses  70 047 filas).
- `max(train) < min(test)` y meses disjuntos: verificado mediante assert.

## 4. Tabla comparativa de modelos

Ordenada por R² (desc), RMSE (asc), MAE (asc). Métricas calculadas sobre el test set definido arriba.

| Modelo | MAE | MSE | RMSE | R² | MAPE | fit s | nota |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ExtraTrees(n=100,d=10) | 139 120 | 1.54e+11 | 392 524 | 0.9700 | 58.284 | 15.4 |  |
| RandomForest(n=100,d=10) | 127 376 | 1.54e+11 | 392 873 | 0.9699 | 7.769 | 19.1 |  |
| DecisionTree(d=10) | 138 622 | 2.05e+11 | 452 808 | 0.9601 | 7.524 | 1.0 |  |
| KNN(k=5,scaled) | 160 964 | 3.32e+11 | 575 965 | 0.9354 | 30.072 | 0.1 | submuestra de train de 50 000 filas para evitar O(n²) |
| LinearRegression | 330 804 | 5.86e+11 | 765 216 | 0.8860 | 286.423 | 0.6 |  |
| Ridge(α=1) | 331 047 | 5.86e+11 | 765 307 | 0.8860 | 283.569 | 0.4 |  |
| DummyRegressor(mean) | 804 823 | 5.14e+12 | 2 266 224 | -0.0000 | 699.635 | 0.0 |  |

> **`accuracy` NO aplica**: este problema es de **regresión**, no de clasificación. La métrica análoga es R² (coeficiente de determinación).

> **MAPE** sólo se reporta en esta vista porque por construcción `y_true > 0` (filtro). En el dataset completo (con ceros y negativos) MAPE divide por cero y no es métricamente válido.

> **KNN**: el modelo se entrenó sobre una submuestra del train (declarado en la columna `nota`) para evitar el costo O(n²) con OHE de alta cardinalidad. La comparación con los otros modelos es informativa, no estrictamente justa.

## 5. Modelo seleccionado

**RandomForest(n=100,d=10)**.

Se detectaron **2 modelos empatados** dentro de 0.001 puntos de R² (top R² = 0.9700):

| Modelo | R² | RMSE | MAE | MAPE | fit s |
|---|---:|---:|---:|---:|---:|
| RandomForest(n=100 d=10) | 0.9699 | 392 873 | 127 376 | 7.769 | 19.1 |
| ExtraTrees(n=100 d=10) | 0.9700 | 392 524 | 139 120 | 58.284 | 15.4 |

Regla de desempate: **menor MAE**. Ganador: `RandomForest(n=100 d=10)` (MAE = 127 376 kWh).
Motivo: con R² indistinguibles, el MAE refleja error absoluto promedio y es más interpretable para la presentación. Adicionalmente, los modelos con mayor varianza interna (p.ej. ExtraTrees) tienden a generar MAPE inflado por inestabilidad en valores pequeños del target.

Justificación adicional del modelo elegido:

- R² = 0.9699; RMSE = 392 873 kWh; MAE = 127 376 kWh; MAPE = 7.769.
- Captura interacciones no lineales entre `tarifa`, `tipo_clientes`, `region` y `clientes_facturados`.
- Tiempos de entrenamiento aceptables para el tamaño actual.
- No requiere transformación logarítmica del target ni escalado.
- Consistente con la elección del modelo v2 (`reports/resumen_modelo_energia.md`).

## 6. Heatmaps de correlación

### 6.1 Variables numéricas (`13_matriz_correlacion_numerica.png`)

| variable | energia_kwh | clientes_facturados | anio | mes |
|---|---:|---:|---:|---:|
| energia_kwh | 1.000 | 0.886 | -0.005 | -0.003 |
| clientes_facturados | 0.886 | 1.000 | 0.005 | -0.001 |
| anio | -0.005 | 0.005 | 1.000 | -0.076 |
| mes | -0.003 | -0.001 | -0.076 | 1.000 |

### 6.2 Variables log-transformadas (`14_matriz_correlacion_log.png`)

| variable | log_energia | log_clientes | anio | mes |
|---|---:|---:|---:|---:|
| log_energia_kwh | 1.000 | 0.818 | -0.007 | -0.005 |
| log_clientes_facturados | 0.818 | 1.000 | 0.003 | -0.005 |
| anio | -0.007 | 0.003 | 1.000 | -0.076 |
| mes | -0.005 | -0.005 | -0.076 | 1.000 |

### Heatmap extendido con auxiliares SEN (`13b_corr_heatmap_aux.png`)

Columnas auxiliares incluidas (verificadas en parquet): `demanda_promedio_mes_sen_L1, demanda_maxima_mes_sen_L1, rango_demanda_mes_sen_L1, proporcion_ernc_mes_L1, proporcion_hidro_mes_L1, total_generacion_mes_L1`.  
Todas las columnas pedidas existen.

**Advertencia**: el heatmap sólo refleja correlaciones lineales entre **variables numéricas**. La señal real de `region`, `comuna`, `tarifa` y `tipo_clientes` es categórica y **no aparece** aquí. Su efecto se mide indirectamente vía OneHotEncoder en el modelo.

## 7. Variable dominante: `clientes_facturados`

Evidencia cuantitativa (calculada sobre la vista filtrada del test set y la vista completa para correlaciones):

- Correlación Pearson (raw) `corr(clientes_facturados, energia_kwh)` = **0.886**.
- Correlación Spearman (raw) = **0.874**.
- Correlación Pearson (log-log) = **0.818**.
- Correlación Spearman (log-log) = **0.874**.
- R² de regresión lineal univariada usando sólo `clientes_facturados` → `energia_kwh` (sin OHE, sin tarifa) en este split temporal: **0.8414**.
- Ver gráfico `15_clientes_vs_energia_loglog.png`: la relación log-log es claramente positiva y aproximadamente lineal, con dispersión por tipo de cliente.

**Diferencia A (con cf) vs B (sin cf)** según el modelo v2:

- A. RandomForest **con** `clientes_facturados`: R² = 0.9694, RMSE ≈ 391 092.
- B. RandomForest **sin** `clientes_facturados`: R² = 0.7988, RMSE ≈ 1 003 554.
- Diferencia ΔR² ≈ 0.17 atribuible a `clientes_facturados`.

**¿Constituye leakage?**

- En sentido **temporal estricto**: no. `clientes_facturados` se conoce en el momento de facturar el mismo mes, no usa información futura.
- En sentido **práctico de utilidad**: sí es problemático. Para predecir el mes futuro no se conoce el `clientes_facturados` de ese mes; debería usarse su lag (`clientes_facturados_L1`).
- Para presentación: declararlo abiertamente. El R² alto es **plausible** pero está apoyado en una identidad casi contable.

## 8. Feature importance (top 15)

Importancias del mejor modelo basado en árboles (ver figura `16_importancia_variables.png`).

| feature | importance |
| --- | --- |
| clientes_facturados | 0.8857 |
| tarifa_AT4.3 | 0.0284 |
| comuna_Santiago | 0.0182 |
| region_Región Metropolitana de Santiago | 0.0140 |
| mes | 0.0128 |
| comuna_Las Condes | 0.0071 |
| anio | 0.0068 |
| tarifa_BT4.3 | 0.0032 |
| comuna_Providencia | 0.0022 |
| tarifa_BT3PP | 0.0017 |
| comuna_Colina | 0.0014 |
| comuna_Lo Barnechea | 0.0014 |
| comuna_Maipú | 0.0011 |
| region_Región de Coquimbo | 0.0010 |
| comuna_Quilicura | 0.0009 |

## 9. Limitaciones

- Sin hiperparameter tuning. Las cifras son una primera referencia, no un techo.
- Sólo holdout temporal único 80/20. Falta TimeSeriesSplit con varios folds.
- `clientes_facturados` casi contemporáneo con el target inflará el R². Para predicción genuina del mes futuro se necesita `clientes_facturados_L1`.
- Heatmap no incluye categóricas (region/comuna/tarifa/tipo) — su efecto no se ve en el plot.
- KNN se entrenó sobre submuestra; comparación con árboles es informativa, no concluyente.
- 5 275 filas duplicadas sobre la clave panel (4 990 grupos) — limitación del dataset original, no resuelta aquí.

## 10. Texto sugerido para la presentación (slide de selección)

> "Comparamos 7 modelos de regresión con la misma cohorte temporal (2018-04 → 2024-12) y el mismo split 80/20 por fecha. "
> "El mejor desempeño lo obtuvo **RandomForest(n=100 d=10)** con R² = 0.9699 y RMSE ≈ 392 873 kWh sobre el test. "
> "La métrica `accuracy` no aplica: este es un problema de **regresión**, no de clasificación. "
> "`clientes_facturados` es la variable dominante. Con ella el R² sube de 0.80 a 0.97; sin ella, el modelo retiene poder predictivo razonable basado en geografía y tarifa. "
> "No es leakage temporal estricto, pero es una feature casi contemporánea: en próximas entregas usaremos su lag para una evaluación predictiva más honesta."
