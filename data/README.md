# Datos del proyecto

## Datasets raw (`data/raw/`)

Los archivos originales no se modifican. Todos los datos de facturación provienen del sistema eléctrico chileno (CNE / Coordinador Eléctrico Nacional).

| Archivo | Descripción | Fuente |
|---|---|---|
| `se_facturacion_clientes_regulados(in).csv` | Facturación mensual de clientes regulados 2015–2024 por región, comuna, tipo de cliente y tarifa | CNE / Energía Abierta (URL pendiente de confirmar) |
| `se_demanda_diaria(in).csv` | Demanda diaria del sistema eléctrico nacional (SEN) | Coordinador Eléctrico Nacional |
| `se_gx_programada_fuente(in).csv` | Generación programada por fuente (hidro, termo, ERNC) a nivel mensual | Coordinador Eléctrico Nacional |

## Archivos generados (no versionados)

Los siguientes archivos se generan al ejecutar el pipeline y no están incluidos en el repositorio:

| Carpeta | Archivos | Generado por |
|---|---|---|
| `data/interim/` | `facturacion_clean.parquet`, `facturacion_clean.csv` | `src/02_limpieza_facturacion.py` |
| `data/processed/` | `modeling_energia_kwh.parquet`, `modeling_consumo_promedio.parquet`, `modeling_con_auxiliares.parquet` | `src/04_preparar_datasets_modelado.py`, `src/05_integrar_auxiliares.py` |

Para regenerar los archivos intermedios ejecutar el pipeline descrito en el `README.md` principal.
