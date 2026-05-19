# Predicción de energía eléctrica facturada en Chile

Proyecto de ciencia de datos para la predicción mensual de la energía eléctrica facturada a clientes regulados en Chile, desagregada por comuna, tipo de cliente y tarifa.

## Pregunta de investigación

¿Es posible predecir la energía total mensual facturada (kWh) por combinación de comuna, tipo de cliente y tarifa, utilizando datos históricos de facturación y contexto del sistema eléctrico nacional?

## Tipo de problema

Aprendizaje supervisado — regresión sobre panel temporal. El dataset corresponde a series de tiempo mensuales múltiples indexadas por unidad geográfica y tarifaria.

## Estructura del repositorio

```
proyecto_DS/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                   # Datasets originales (sin modificar)
│   └── README.md              # Fuentes y descripción de archivos raw
├── notebooks/
│   └── analisis_reproducible.ipynb
├── docs/                      # Informe escrito (PDF u otros documentos)
├── src/
│   ├── 01_inventario_datasets.py
│   ├── 02_limpieza_facturacion.py
│   ├── 03_analisis_exploratorio.py
│   ├── 04_preparar_datasets_modelado.py
│   ├── 05_integrar_auxiliares.py
│   ├── 06_auditoria_datos.py
│   ├── 07_graficos_presentacion.py
│   ├── 08_modelo_energia.py
│   └── 09_seleccion_modelo_correlacion.py
└── reports/
    ├── auditoria_datos.md
    ├── calidad_target_energia.md
    ├── auditoria_modelo.md
    ├── seleccion_modelo_y_correlacion.md
    ├── resumen_analisis_exploratorio.md
    ├── resumen_modelo_energia.md
    ├── guion_presentacion.md
    └── Imagenes/            # 17 figuras generadas por los scripts
```

## Reproducción del pipeline

Los scripts deben ejecutarse en orden desde la raíz del repositorio. Los archivos intermedios y procesados se generan localmente y están excluidos del control de versiones (`.gitignore`).

```bash
python src/01_inventario_datasets.py             # inventario de archivos raw
python src/02_limpieza_facturacion.py            # → data/interim/facturacion_clean.parquet
python src/03_analisis_exploratorio.py           # EDA básico
python src/04_preparar_datasets_modelado.py      # → data/processed/modeling_*.parquet
python src/05_integrar_auxiliares.py             # → data/processed/modeling_con_auxiliares.parquet
python src/06_auditoria_datos.py                 # → reports/auditoria_datos.md
python src/07_graficos_presentacion.py           # → reports/Imagenes/ (01–07)
python src/08_modelo_energia.py                  # → reports/resumen_modelo_energia.md
python src/09_seleccion_modelo_correlacion.py    # → reports/Imagenes/ (08–16)
```

El notebook `notebooks/analisis_reproducible.ipynb` replica las conclusiones principales de la Presentación 1 en un único archivo ejecutable.

## Dependencias

Ver `requirements.txt`. Instalación:

```bash
pip install -r requirements.txt
```

## Resultados principales (Presentación 1)

| Modelo | MAE (kWh) | RMSE (kWh) | R² |
|---|---:|---:|---:|
| RandomForest (n=100, d=10) | 127 376 | 392 873 | 0.9699 |
| DecisionTree (d=10) | 138 622 | 452 808 | 0.9601 |
| Ridge (α=1) | 331 047 | 765 307 | 0.8860 |
| DummyRegressor (media) | 804 823 | 2 266 224 | ≈ 0.00 |

Validación: holdout temporal 80/20 por fecha única (train 2018-04 → 2023-07, test 2023-08 → 2024-12). Sin tuning de hiperparámetros.

La variable `clientes_facturados` explica la mayor parte del R² (importancia ≈ 0.89 en el RandomForest). Sin ella el R² baja de 0.97 a 0.80. Esto se analiza en detalle en `reports/auditoria_modelo.md`.

## Limitaciones declaradas

- `clientes_facturados` es casi contemporánea con el target; para predicción de meses futuros debería usarse su lag.
- Los auxiliares SEN (demanda y generación nacional) son agregados por mes y no aportan varianza a nivel de comuna.
- La clave panel `(fecha, region, comuna, tipo_clientes, tarifa)` no es única en el dataset original (5 275 filas en 4 990 grupos); la dimensión faltante no fue identificada.

## Autores

Proyecto de la asignatura de Inteligencia de Negocios / Ciencia de Datos.
Repositorio preparado para entrega académica del proyecto de Data Science.
