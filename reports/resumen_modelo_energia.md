# Presentación 1 - Primer modelo v2 (4 escenarios)

## Diseño experimental

- Target: `energia_kwh` (regresión).
- Cohorte temporal usable: 81 meses (2018-04-01 → 2024-12-01).
- Split por fecha única 80/20:
  - Train: 2018-04-01 → 2023-07-01 (64 meses).
  - Test: 2023-08-01 → 2024-12-01 (17 meses).
- `max(train) < min(test)` y meses disjuntos: verificado mediante assert.
- Métricas: MAE, RMSE, R². MAPE no se reporta (ceros y negativos en target).

## Resultados por escenario

### A. Base con clientes_facturados

- Filas train: 265 558 · test: 71 985
- Features pre-OHE: 7

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline (media train) | 786 558 | 2 237 454 | -0.0000 |
| Ridge (α=1  scaled) | 326 376 | 759 357 | 0.8848 |
| RandomForest (n=100  depth=10) | 124 419 | 391 092 | 0.9694 |

### B. Base sin clientes_facturados

- Filas train: 265 558 · test: 71 985
- Features pre-OHE: 6

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline (media train) | 786 558 | 2 237 454 | -0.0000 |
| Ridge (α=1  scaled) | 745 094 | 1 794 903 | 0.3565 |
| RandomForest (n=100  depth=10) | 334 624 | 1 003 554 | 0.7988 |

### C. Base + cf, filtrado (energia>0 & cf>0)

- Filas train: 257 663 · test: 70 047
- Features pre-OHE: 7

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline (media train) | 804 823 | 2 266 224 | -0.0000 |
| Ridge (α=1  scaled) | 331 047 | 765 307 | 0.8860 |
| RandomForest (n=100  depth=10) | 127 376 | 392 873 | 0.9699 |

### D. Con auxiliares (lags)

- Filas train: 265 558 · test: 71 985
- Features pre-OHE: 25

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline (media train) | 786 558 | 2 237 454 | -0.0000 |
| Ridge (α=1  scaled) | 757 059 377 236 | 844 590 933 073 | -142490195990.8875 |
| RandomForest (n=100  depth=10) | 185 707 | 1 121 251 | 0.7489 |

## Comparación: RandomForest entre escenarios

| Escenario | n train | n test | MAE | RMSE | R² |
|---|---:|---:|---:|---:|---:|
| A. Base con clientes_facturados | 265 558 | 71 985 | 124 419 | 391 092 | 0.9694 |
| B. Base sin clientes_facturados | 265 558 | 71 985 | 334 624 | 1 003 554 | 0.7988 |
| C. Base + cf  filtrado (energia>0 & cf>0) | 257 663 | 70 047 | 127 376 | 392 873 | 0.9699 |
| D. Con auxiliares (lags) | 265 558 | 71 985 | 185 707 | 1 121 251 | 0.7489 |

## Comparación: Ridge entre escenarios

| Escenario | MAE | RMSE | R² |
|---|---:|---:|---:|
| A. Base con clientes_facturados | 326 376 | 759 357 | 0.8848 |
| B. Base sin clientes_facturados | 745 094 | 1 794 903 | 0.3565 |
| C. Base + cf  filtrado (energia>0 & cf>0) | 331 047 | 765 307 | 0.8860 |
| D. Con auxiliares (lags) | 757 059 377 236 | 844 590 933 073 | -142490195990.8875 |

## Interpretación

- Escenario A (con `clientes_facturados`): el R² alto del RF refleja que el modelo está capturando una identidad casi contable (`energia ≈ kWh_por_cliente × clientes`). Es plausible pero **no demuestra capacidad predictiva genuina**.
- Escenario B (sin `clientes_facturados`): mide cuánto puede predecir el modelo sólo con identidad geográfica/tarifaria + tiempo. La diferencia A-B cuantifica la dependencia del modelo en esa feature contemporánea.
- Escenario C (con cf, filtrado `energia>0 & cf>0`): elimina ruido de filas degeneradas; sirve para una lectura más limpia del rendimiento real.
- Escenario D (con auxiliares): los lags son agregados nacionales SEN, idénticos para todas las filas del mismo mes. Aportan poca varianza intra-mes y pueden dañar la generalización a meses fuera del rango entrenado.

## Recomendación para presentación

- Mostrar los **4 escenarios** y declarar honestamente la dependencia del R² alto en `clientes_facturados`.
- El primer modelo defendible para la entrega es A (referencia) **acompañado** del B (límite inferior honesto).
- Marcar D como hallazgo metodológico: agregar features auxiliares mal diseñadas no garantiza mejora.

## Advertencias metodológicas

- `clientes_facturados` no es leakage temporal (no usa información futura), pero es **casi contemporánea** con el target.
- Para predicción real a un mes futuro habría que usar `clientes_facturados_lag1` (no disponible aún).
- Ridge sigue dependiendo de un buen scaling; con auxiliares hay shift de distribución entre train y test.
- Sin tuning. Hiperparámetros por defecto.
- Sólo holdout temporal simple. Próximo paso: TimeSeriesSplit con varios folds.
