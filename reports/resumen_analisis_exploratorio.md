# Presentación 1 - EDA v2 (corregido)

## Datasets usados

- `data/interim/facturacion_clean.parquet` — 490 753 filas × 12 cols, 2015-01-01 → 2024-12-01.
- `data/processed/modeling_con_auxiliares.parquet` — 349 411 filas × 30 cols, 2018-01-01 → 2024-12-01.

## Hallazgos verificados

- Cobertura: 16 regiones, 330 comunas, 31 tarifas, 2 tipos de cliente.
- **Tipo de cliente**: en agregado 2015-2024, Residencial totaliza **146.2 TWh** y No Residencial **131.2 TWh** (razón Residencial / No Residencial = **1.11×**, **NO** es 3-4×).
- Cambio temporal documentado: hasta 2017 No Residencial > Residencial; desde ~2019 se invierte y Residencial domina.

  | Año | No Residencial (TWh) | Residencial (TWh) |
  |---|---:|---:|
  | 2015 | 18.27 | 12.62 |
  | 2016 | 18.54 | 12.87 |
  | 2017 | 17.12 | 13.32 |
  | 2018 | 14.48 | 13.69 |
  | 2019 | 12.59 | 14.93 |
  | 2020 | 10.33 | 15.43 |
  | 2021 | 9.79 | 15.80 |
  | 2022 | 9.37 | 15.08 |
  | 2023 | 10.40 | 16.06 |
  | 2024 | 10.31 | 16.44 |

- **Top regiones acumuladas (TWh)**: la Región Metropolitana domina con amplio margen.

  | # | Región | TWh acumulados |
  |---:|---|---:|
  | 1 | Región Metropolitana de Santiago | 124.57 |
  | 2 | Región de Valparaíso | 27.83 |
  | 3 | Región del Biobío | 20.40 |
  | 4 | Región del Maule | 16.45 |
  | 5 | Región del Libertador Gral. Bernardo O’Higgins | 15.07 |
  | 6 | Región de Los Lagos | 14.23 |

- Antofagasta aparece en posición 9 (~8.3 TWh acumulados); **NO** está en el top regional.
- Estacionalidad: el mes con máximo agregado nacional 2015-2024 es **07** (26 172 GWh) y el mínimo es **11** (21 291 GWh). Amplitud relativa **22.9 %**: estacionalidad presente pero moderada a nivel nacional.
- Distribución de `energia_kwh` muy sesgada: máx = 1.12e8 kWh (Santiago Residencial BT1A, jul-ago).
- Anomalías: **1 191 negativos** y **13 283 ceros** en `energia_kwh` (≈ 2.9 % del total).
- `clientes_facturados`: 6 623 ceros  1 negativos  1 NaN.
- Nulos en otras columnas: e1_kwh=1 368  e2_kwh=47 728  consumo_promedio_cliente_kwh=6 625.

## Figuras generadas

- `reports/Imagenes/01_evolucion_mensual_nacional.png` — Evolución mensual de energía total facturada (GWh).
- `reports/Imagenes/02_evolucion_tipo_cliente.png` — Evolución mensual por tipo_clientes. La curva Residencial supera a No Residencial alrededor de 2018-2019.
- `reports/Imagenes/03_energia_por_region.png` — Energía acumulada por región (TWh = kWh/1e9). RM domina con margen amplio.
- `reports/Imagenes/04_distribucion_log_energia.png` — Distribución log10 de `energia_kwh` (positivos). Cola larga: el target requiere log o tratamiento específico.
- `reports/Imagenes/05_boxplot_tipo_cliente.png` — Boxplot log10 del target por tipo de cliente. No Residencial tiene mayor dispersión y outliers superiores.
- `reports/Imagenes/06_anomalias_por_anio.png` — Negativos y ceros de `energia_kwh` por año. Negativos crecen sostenidamente (80 → 199 entre 2015 y 2024).
- `reports/Imagenes/07_energia_vs_demanda_sen_lag1.png` — Energía facturada (suma mensual) vs demanda SEN promedio con lag 1. **La demanda SEN es serie nacional** (igual para todas las filas del mismo mes), por eso su uso como feature por-fila tiene varianza limitada.

## Notas metodológicas

- Las variables auxiliares (demanda SEN, generación) son **series nacionales**, idénticas para todas las filas de un mismo mes; su capacidad de discriminar a nivel comuna×tarifa es limitada.
- Los outliers extremos no se removieron en `clean`; las decisiones de filtrado se aplican en el script de modelado (vista `energia_kwh > 0` y/o `clientes_facturados > 0`).
- El conteo de duplicados sobre la clave panel (5 275 filas) revela que la clave asumida no es estrictamente única; ver `reports/calidad_target_energia.md`.
