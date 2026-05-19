# Auditoría de contratos de datos

## 1. Raw (`data/raw`)

Archivos raw: 7

| archivo | bytes | md5 (8 hex) |
|---|---:|---|
| se_balance_energia_regional(in).csv | 26 536 | `6a41bbea` |
| se_demanda_diaria(in).csv | 379 794 | `9e48d137` |
| se_demanda_máx_sobre_cap_instalada_anuario_2019(Hoja2).csv | 1 473 | `a2528863` |
| se_dx_programada(in).csv | 88 559 | `f706dd7b` |
| se_facturacion_clientes_regulados(in)(1).csv | 40 503 487 | `bc6db208` |
| se_facturacion_clientes_regulados(in).csv | 40 503 487 | `bc6db208` |
| se_gx_programada_fuente(in).csv | 230 353 | `d738ccee` |

### Hallazgos raw
- **WARNING** — Duplicado byte-a-byte md5 `bc6db208`: se_facturacion_clientes_regulados(in)(1).csv, se_facturacion_clientes_regulados(in).csv

### Encabezados (separador detectado)

- `se_balance_energia_regional(in).csv` (sep=`;`): `anio;mes;region_nombre;region_cod;generacion_mwh;cltes_libres_mwh;cltes_regulados_mwh,,,`
- `se_demanda_diaria(in).csv` (sep=`;`): `fecha;sistema;dmin_mw;dmax_mw,,`
- `se_demanda_máx_sobre_cap_instalada_anuario_2019(Hoja2).csv` (sep=`,`): `A�o,Sistema,Capacidad Instalada MW,Demanda m�xima MW,Demanda/Capacidad,,,,,,,,,,,,,,,,,,,,,,,,`
- `se_dx_programada(in).csv` (sep=`;`): `fecha;valor,`
- `se_facturacion_clientes_regulados(in)(1).csv` (sep=`;`): `anio;mes;region;comuna;tipo_clientes;tarifa;clientes_facturados;e1_kwh;e2_kwh;energia_kwh`
- `se_facturacion_clientes_regulados(in).csv` (sep=`;`): `anio;mes;region;comuna;tipo_clientes;tarifa;clientes_facturados;e1_kwh;e2_kwh;energia_kwh`
- `se_gx_programada_fuente(in).csv` (sep=`;`): `fecha;hidro;termo;ernc;total,,,,`

## 2. Interim — `data/interim/facturacion_clean.parquet`

Shape: 490 753 filas × 12 columnas

Columnas: `['anio', 'mes', 'region', 'comuna', 'tipo_clientes', 'tarifa', 'clientes_facturados', 'e1_kwh', 'e2_kwh', 'energia_kwh', 'fecha', 'consumo_promedio_cliente_kwh']`

**Tipos**:

- `anio`: int64
- `mes`: int64
- `region`: object
- `comuna`: object
- `tipo_clientes`: object
- `tarifa`: object
- `clientes_facturados`: float64
- `e1_kwh`: float64
- `e2_kwh`: float64
- `energia_kwh`: int64
- `fecha`: datetime64[ns]
- `consumo_promedio_cliente_kwh`: float64

Rango fechas: 2015-01-01 → 2024-12-01, meses únicos: 120

Regiones: 16, comunas: 330, tarifas: 31, tipos cliente: ['No Residencial', 'Residencial']

**Nulos por columna**:

- `clientes_facturados`: 1
- `e1_kwh`: 1 368
- `e2_kwh`: 47 728
- `consumo_promedio_cliente_kwh`: 6 625

Duplicados sobre `['fecha', 'region', 'comuna', 'tipo_clientes', 'tarifa']`: 5 275

`energia_kwh`: positivos=476 279, ceros=13 283, negativos=1 191

`energia_kwh` describe:
```
count    4.907530e+05
mean     5.652958e+05
std      2.382539e+06
min     -4.812180e+06
25%      6.775000e+03
50%      3.025400e+04
75%      1.779590e+05
max      1.120400e+08
Name: energia_kwh, dtype: float64
```

**Top 5 mayores `energia_kwh`**:

| fecha | region | comuna | tipo_clientes | tarifa | clientes_facturados | energia_kwh |
|---|---|---|---|---|---|---|
| 2019-08-01 00:00:00 | Región Metropolitana de Santiago | Santiago | Residencial | BT1A | 476 166.00 | 112 039 986 |
| 2020-07-01 00:00:00 | Región Metropolitana de Santiago | Las Condes | Residencial | BT1A | 139 228.00 | 109 282 840 |
| 2020-07-01 00:00:00 | Región Metropolitana de Santiago | Maipú | Residencial | BT1A | 166 043.00 | 107 637 889 |
| 2019-07-01 00:00:00 | Región Metropolitana de Santiago | Santiago | Residencial | BT1A | 476 148.00 | 104 950 620 |
| 2020-07-01 00:00:00 | Región Metropolitana de Santiago | Santiago | Residencial | BT1A | 239 535.00 | 94 490 574 |

**Top 5 menores `energia_kwh` (más negativos)**:

| fecha | region | comuna | tipo_clientes | tarifa | clientes_facturados | energia_kwh |
|---|---|---|---|---|---|---|
| 2024-04-01 00:00:00 | Región Metropolitana de Santiago | Alhué | No Residencial | AT4.3 | 28.00 | -4 812 180 |
| 2024-11-01 00:00:00 | Región Metropolitana de Santiago | Pedro Aguirre Cerda | No Residencial | AT4.3 | 46.00 | -2 847 035 |
| 2024-07-01 00:00:00 | Región Metropolitana de Santiago | Pedro Aguirre Cerda | No Residencial | AT4.3 | 47.00 | -2 738 732 |
| 2024-01-01 00:00:00 | Región Metropolitana de Santiago | Pedro Aguirre Cerda | No Residencial | AT4.3 | 51.00 | -1 933 539 |
| 2024-02-01 00:00:00 | Región Metropolitana de Santiago | Huechuraba | No Residencial | AT3PPP | 41.00 | -1 841 914 |

Consistencia `energia_kwh ≈ e1 + e2` (filas con e1 y e2 no nulos): 441 198 / 443 025 cuadran (tolerancia |Δ|<1).
Δ describe:
```
count    443025.000000
mean         -0.000115
std           0.064218
min          -1.000000
25%           0.000000
50%           0.000000
75%           0.000000
max           1.000000
dtype: float64
```

`clientes_facturados`: nulos=1, ≤0=6624

### Hallazgos interim
- **WARNING** — 5 275 duplicados sobre clave panel
- **WARNING** — `energia_kwh` con 1 191 negativos y 13 283 ceros (calidad pendiente)
- **WARNING** — `clientes_facturados` con 1 nulo(s)

## 3. Processed — `modeling_energia_kwh.parquet`

Shape: 490 753 × 9

Columnas: `['fecha', 'anio', 'mes', 'region', 'comuna', 'tipo_clientes', 'tarifa', 'clientes_facturados', 'energia_kwh']`

Rango fechas: 2015-01-01 → 2024-12-01, meses únicos: 120

**Nulos**:

- `clientes_facturados`: 1

Target `energia_kwh` describe:
```
count    4.907530e+05
mean     5.652958e+05
std      2.382539e+06
min     -4.812180e+06
25%      6.775000e+03
50%      3.025400e+04
75%      1.779590e+05
max      1.120400e+08
Name: energia_kwh, dtype: float64
```

## 4. Processed — `modeling_consumo_promedio.parquet`

Shape: 482 944 × 9

Columnas: `['fecha', 'anio', 'mes', 'region', 'comuna', 'tipo_clientes', 'tarifa', 'clientes_facturados', 'consumo_promedio_cliente_kwh']`

Rango fechas: 2015-01-01 → 2024-12-01, meses únicos: 120

Target `consumo_promedio_cliente_kwh` describe:
```
count    4.829440e+05
mean     4.953228e+03
std      1.232190e+04
min      0.000000e+00
25%      8.060000e+02
50%      2.041200e+03
75%      4.275000e+03
max      1.705000e+06
Name: consumo_promedio_cliente_kwh, dtype: float64
```

## 5. Processed — `modeling_con_auxiliares.parquet`

Shape: 349 411 × 30

Columnas: `['anio_x', 'mes_x', 'region', 'comuna', 'tipo_clientes', 'tarifa', 'clientes_facturados', 'e1_kwh', 'e2_kwh', 'energia_kwh', 'fecha', 'consumo_promedio_cliente_kwh', 'demanda_promedio_mes_sen_L1', 'demanda_promedio_mes_sen_L2', 'demanda_promedio_mes_sen_L3', 'demanda_maxima_mes_sen_L1', 'demanda_maxima_mes_sen_L2', 'demanda_maxima_mes_sen_L3', 'rango_demanda_mes_sen_L1', 'rango_demanda_mes_sen_L2', 'rango_demanda_mes_sen_L3', 'proporcion_ernc_mes_L1', 'proporcion_ernc_mes_L2', 'proporcion_ernc_mes_L3', 'proporcion_hidro_mes_L1', 'proporcion_hidro_mes_L2', 'proporcion_hidro_mes_L3', 'total_generacion_mes_L1', 'total_generacion_mes_L2', 'total_generacion_mes_L3']`

Rango: 2018-01-01 → 2024-12-01, meses únicos: 84

Columnas lag detectadas (18): `['demanda_promedio_mes_sen_L1', 'demanda_promedio_mes_sen_L2', 'demanda_promedio_mes_sen_L3', 'demanda_maxima_mes_sen_L1', 'demanda_maxima_mes_sen_L2', 'demanda_maxima_mes_sen_L3', 'rango_demanda_mes_sen_L1', 'rango_demanda_mes_sen_L2', 'rango_demanda_mes_sen_L3', 'proporcion_ernc_mes_L1', 'proporcion_ernc_mes_L2', 'proporcion_ernc_mes_L3', 'proporcion_hidro_mes_L1', 'proporcion_hidro_mes_L2', 'proporcion_hidro_mes_L3', 'total_generacion_mes_L1', 'total_generacion_mes_L2', 'total_generacion_mes_L3']`
- **OK** — No hay columnas auxiliares del mismo mes (sólo lags)
- **ERROR** — Columnas documentadas en `integracion_auxiliares_summary.md` que **no existen** en el parquet: ['total_hidro_mes_L1', 'total_hidro_mes_L2', 'total_hidro_mes_L3', 'total_ernc_mes_L1', 'total_ernc_mes_L2', 'total_ernc_mes_L3']

**Nulos por lag**:

- `demanda_promedio_mes_sen_L1`: 3 956
- `demanda_promedio_mes_sen_L2`: 7 912
- `demanda_promedio_mes_sen_L3`: 11 868
- `demanda_maxima_mes_sen_L1`: 3 956
- `demanda_maxima_mes_sen_L2`: 7 912
- `demanda_maxima_mes_sen_L3`: 11 868
- `rango_demanda_mes_sen_L1`: 3 956
- `rango_demanda_mes_sen_L2`: 7 912
- `rango_demanda_mes_sen_L3`: 11 868
- `proporcion_ernc_mes_L1`: 3 956
- `proporcion_ernc_mes_L2`: 7 912
- `proporcion_ernc_mes_L3`: 11 868
- `proporcion_hidro_mes_L1`: 3 956
- `proporcion_hidro_mes_L2`: 7 912
- `proporcion_hidro_mes_L3`: 11 868
- `total_generacion_mes_L1`: 3 956
- `total_generacion_mes_L2`: 7 912
- `total_generacion_mes_L3`: 11 868

Filas con todos los lags válidos: 337 543 de 349 411
- **WARNING** — Columnas `anio_x` / `mes_x` quedaron del merge (no se renombraron a `anio`/`mes`)
