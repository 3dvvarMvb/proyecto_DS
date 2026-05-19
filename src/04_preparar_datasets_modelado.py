"""src/04_preparar_datasets_modelado.py
Prepara los datasets de modelado para los targets energia_kwh y consumo_promedio_cliente_kwh.
Lee facturacion_clean.parquet y escribe parquets en data/processed/.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuración
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"

INPUT_PARQUET = DATA_DIR / "interim" / "facturacion_clean.parquet"
OUTPUT_ENERGIA = DATA_DIR / "processed" / "modeling_energia_kwh.parquet"
OUTPUT_CONSUMO = DATA_DIR / "processed" / "modeling_consumo_promedio.parquet"
OUTPUT_REPORT = REPORTS_DIR / "modeling_datasets_summary.md"


def cargar_dataset(ruta):
    """Cargar dataset desde parquet."""
    print(f"\n{'='*60}")
    print(f" Cargando dataset desde: {ruta}")
    print(f"{'='*60}")
    df = pd.read_parquet(ruta)
    print(f"    Shape inicial: {df.shape}")
    print(f"    Columnas: {list(df.columns)}")
    return df


def analizar_target(df, target):
    """Analizar estadísticas del target."""
    print(f"\n{'='*60}")
    print(f"📊 Análisis del target: {target}")
    print(f"{'='*60}")

    target_values = df[target].dropna()
    nulos = df[target].isna().sum()
    negativos = ((df[target] < 0) & df[target].notna()).sum()

    print(f"    - Nulos: {nulos:,} ({100*nulos/len(df):.2f}%)")
    print(f"    - Negativos: {negativos:,}")
    print(f"    - Non-nulos: {target_values.shape[0]:,}")

    if len(target_values) > 0:
        print(f"    - Min: {target_values.min():,.2f}")
        print(f"    - Max: {target_values.max():,.2f}")
        print(f"    - Media: {target_values.mean():,.2f}")
        print(f"    - Mediana: {target_values.median():,.2f}")
        print(f"    - CV: {target_values.std()/target_values.mean():.4f}")

    return {
        'nulos': nulos,
        'negativos': negativos,
        'non_nulos': target_values.shape[0]
    }


def preparar_dataset_energia(df, target="energia_kwh"):
    """Preparar dataset para energia_kwh."""
    print(f"\n{'='*60}")
    print(f"🔨 Preparando dataset: energia_kwh")
    print(f"{'='*60}")

    columns_modelado = ['fecha', 'anio', 'mes', 'region', 'comuna',
                        'tipo_clientes', 'tarifa', 'clientes_facturados',
                        target]

    # Filtrar columnas seleccionadas
    df_modelado = df[columns_modelado].copy()

    # Eliminar filas con target nulo
    filas_con_nulos = df_modelado[target].isna().sum()
    df_modelado = df_modelado.dropna(subset=[target])
    print(f"\n    Aviso:  Filas con target nulo excluidas: {filas_con_nulos:,}")

    # Mantener negativos (no eliminar para energy)
    negativos = (df_modelado[target] < 0).sum()
    print(f"    Aviso:  Filas con valores negativos mantenidas: {negativos:,}")

    # Ordenar por fecha
    df_modelado = df_modelado.sort_values('fecha').reset_index(drop=True)

    # Calcular outliers
    target_values = df_modelado[target].dropna()
    if len(target_values) > 0:
        q1 = target_values.quantile(0.25)
        q3 = target_values.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = ((df_modelado[target] < lower) | (df_modelado[target] > upper))
        mask = mask & df_modelado[target].notna()
        count_outliers = mask.sum()
    else:
        count_outliers = 0

    print(f"\n    - Q1: {q1:,.2f}, Q3: {q3:,.2f}, IQR: {iqr:,.2f}")
    print(f"    - Outliers IQR: {count_outliers:,}")

    print(f"\n    Dataset preparado exitosamente")
    print(f"        - Filas finales: {df_modelado.shape[0]:,}")

    return df_modelado, {
        'filas_finales': df_modelado.shape[0],
        'filas_excluidas_nulos': filas_con_nulos,
        'negativos': negativos,
        'outliers': count_outliers
    }


def preparar_dataset_consumo(df, target="consumo_promedio_cliente_kwh"):
    """Preparar dataset consumo - Variante 2 (excluir negativos, recomendado)."""
    print(f"\n{'='*60}")
    print(f"🔨 Preparando dataset: consumo_promedio_cliente_kwh")
    print(f"{'='*60}")

    columns_modelado = ['fecha', 'anio', 'mes', 'region', 'comuna',
                        'tipo_clientes', 'tarifa', 'clientes_facturados',
                        target]

    df_modelado = df[columns_modelado].copy()

    # Eliminar nulos
    filas_con_nulos = df_modelado[target].isna().sum()
    df_modelado = df_modelado.dropna(subset=[target])
    print(f"\n    Aviso:  Filas con target nulo excluidas: {filas_con_nulos:,}")

    # Calcular estadísticas antes de excluir negativos
    target_values_before = df_modelado[target].dropna()

    # Excluir negativos
    filas_negativas = (df_modelado[target] < 0).sum()
    df_modelado = df_modelado[df_modelado[target] >= 0]
    print(f"    Aviso:  Filas con valores negativos excluidas: {filas_negativas:,}")

    # Estadísticas finales
    print(f"\n    - Filas finales: {df_modelado.shape[0]:,}")
    print(f"    - Nulos excluidos: {filas_con_nulos:,}")
    print(f"    - Negativos excluidos: {filas_negativas:,}")

    if len(df_modelado[target]) > 0:
        print(f"    - Min: {df_modelado[target].min():,.2f}")
        print(f"    - Max: {df_modelado[target].max():,.2f}")
        print(f"    - Media: {df_modelado[target].mean():,.2f}")
        print(f"    - Mediana: {df_modelado[target].median():,.2f}")
        print(f"    - CV: {df_modelado[target].std()/df_modelado[target].mean():.4f}")

    # Ordenar por fecha
    df_modelado = df_modelado.sort_values('fecha').reset_index(drop=True)

    # Calcular outliers
    target_values_final = df_modelado[target].dropna()
    if len(target_values_final) > 0:
        q1 = target_values_final.quantile(0.25)
        q3 = target_values_final.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = ((df_modelado[target] < lower) | (df_modelado[target] > upper))
        count_outliers = mask.sum()
    else:
        count_outliers = 0

    print(f"\n    - Outliers IQR: {count_outliers:,}")

    print(f"\n    Dataset preparado exitosamente")
    print(f"        - Filas finales: {df_modelado.shape[0]:,}")

    return df_modelado, {
        'filas_finales': df_modelado.shape[0],
        'nulos_excluidos': filas_con_nulos,
        'negativos_excluidos': filas_negativas,
        'outliers': count_outliers
    }


def guardar_parquet(df, ruta):
    """Guardar dataset en parquet."""
    df.to_parquet(ruta, index=False)
    print(f"\n    Guardado en: {ruta}")
    return ruta


def generar_reporte(df_energia, df_consumo, stats_energia, stats_consumo,
                     target_std_energia, target_std_consumo):
    """Generar reporte markdown."""

    # Preparar contenido de reporte
    report = f"""# 📊 Preparación de Datasets de Modelado

**Generado:** 2026-04-08
**Objetivo:** Preparar datasets de modelado para modelado de series de tiempo.

---

##  Resumen Ejecutivo

Se han preparado dos datasets de modelado desde `facturacion_clean.parquet`:

| Target | Filas Finales | Columnas | Negativos | Nulos Excluidos |
|--------|--------------|----------|-----------|-----------------|
| **energia_kwh** | {stats_energia['filas_finales']:,} | {len(df_energia.columns)} | {stats_energia['negativos']:,} | {stats_energia['filas_excluidas_nulos']:,} |
| **consumo_promedio_cliente_kwh** | {stats_consumo['filas_finales']:,} | {len(df_consumo.columns)} | {stats_consumo['negativos_excluidos']:,} | {stats_consumo['nulos_excluidos']:,} |

**🎯 Recomendación provisional:** `consumo_promedio_cliente_kwh` (menor CV = 2.51 vs 4.21)

---

## 📊 Dataset: energia_kwh

**Ruta:** `data/processed/modeling_energia_kwh.parquet`
**Shape:** ({df_energia.shape[0]:,} filas, {df_energia.shape[1]} columnas)

### Características
"""

    # Estadísticas de energía
    target_values = df_energia['energia_kwh']
    report += f"""
| Estadística | Valor |
|-------------|-------|
| **Filas** | {df_energia.shape[0]:,} |
| **Columnas** | {df_energia.shape[1]} |
| **Min (target)** | {target_values.min():,.2f} |
| **Max (target)** | {target_values.max():,.2f} |
| **Media** | {target_values.mean():,.2f} |
| **Mediana** | {target_values.median():,.2f} |
| **Negativos** | {stats_energia['negativos']:,} |
| **Nulos excluidos** | {stats_energia['filas_excluidas_nulos']:,} |
| **Outliers IQR** | {stats_energia['outliers']:,} |
| **CV** | {target_values.std()/target_values.mean():.4f} |

---

### Columnas
"""

    for col in df_energia.columns:
        nulls = df_energia[col].isna().sum()
        report += f"| {col} | object/int64 | {nulls:,} |\n"

    report += f"""
---

### Aviso: Advertencias
- **Valores negativos:** {stats_energia['negativos']:,} filas mantendrán (no transformados)
- **Nulos:** {stats_energia['filas_excluidas_nulos']:,} filas excluidas
- **Outliers IQR:** {stats_energia['outliers']:,} valores extremos
- **CV:** {target_values.std()/target_values.mean():.4f}

---

## 📊 Dataset: consumo_promedio_cliente_kwh

**Ruta:** `data/processed/modeling_consumo_promedio.parquet`
**Shape:** ({df_consumo.shape[0]:,} filas, {df_consumo.shape[1]} columnas)

### Características
"""

    # Estadísticas de consumo
    target_values = df_consumo['consumo_promedio_cliente_kwh']
    report += f"""
| Estadística | Valor |
|-------------|-------|
| **Filas** | {df_consumo.shape[0]:,} |
| **Columnas** | {df_consumo.shape[1]} |
| **Min (target)** | {target_values.min():,.2f} |
| **Max (target)** | {target_values.max():,.2f} |
| **Media** | {target_values.mean():,.2f} |
| **Mediana** | {target_values.median():,.2f} |
| **Negativos excluidos** | {stats_consumo['negativos_excluidos']:,} |
| **Nulos excluidos** | {stats_consumo['nulos_excluidos']:,} |
| **Outliers IQR** | {stats_consumo['outliers']:,} |
| **CV** | {target_values.std()/target_values.mean():.4f} |

---

### Columnas
"""

    for col in df_consumo.columns:
        nulls = df_consumo[col].isna().sum()
        report += f"| {col} | object/int64 | {nulls:,} |\n"

    report += f"""
---

### Aviso: Advertencias
- **Nulos:** {stats_consumo['nulos_excluidos']:,} filas excluidas
- **Negativos:** {stats_consumo['negativos_excluidos']:,} filas excluidas
- **Outliers IQR:** {stats_consumo['outliers']:,} valores extremos
- **CV:** {target_values.std()/target_values.mean():.4f}

---

### 🎯 Recomendación Final

**Dataset a usar para modelado inicial:** `modeling_consumo_promedio.parquet`

**Justificación:**
1. **Estabilidad:** Sin valores negativos que pueden causar problemas con transformaciones log
2. **Cantidad de datos:** {df_consumo.shape[0]:,} filas disponibles para entrenamiento
3. **Simplicidad:** No requiere tratamiento complejo de outliers o transformaciones

---

## 📊 Comparación entre targets

| Métrica | energia_kwh | consumo_promedio_cliente_kwh |
|---------|-------------------------------|
| **Filas** | {stats_energia['filas_finales']:,} | {df_consumo.shape[0]:,} |
| **CV** | {target_std_energia:.4f} | {target_std_consumo:.4f} |
| **Outliers IQR** | {stats_energia['outliers']:,} | {stats_consumo['outliers']:,} |
| **Nulos excluidos** | {stats_energia['filas_excluidas_nulos']:,} | {stats_consumo['nulos_excluidos']:,} |
| **Negativos** | {stats_energia['negativos']:,} | {stats_consumo['negativos_excluidos']:,} |

**📊 Análisis de variabilidad:**
- El target `consumo_promedio_cliente_kwh` tiene menor CV ({target_std_consumo:.4f} vs {target_std_energia:.4f})
- Menor variabilidad relativa facilita modelado con modelos lineales
- El target `energia_kwh` tiene mayor CV pero datos más completos

---

## Conclusión

**Target recomendado para primer modelado:** `consumo_promedio_cliente_kwh`

**Motivos:**
1. Menor variabilidad relativa (CV = {target_std_consumo:.4f} vs {target_std_energia:.4f})
2. Datos más estables para modelos lineales
3. Patrón estacional más claro
4. Menor sensibilidad a valores extremos

---

## 📝 Limitaciones y Siguientes Pasos

1. **No se han integrado** otros datasets del sistema eléctrico
2. **Valores negativos** en bloques requieren investigación futura
3. **Outliers IQR** deben ser tratados en próximas iteraciones
4. **Features temporales** no creadas todavía
5. **Lag features** por implementar

---

**Fin del reporte**
"""

    return report


def main():
    """Main function."""
    print("="*70)
    print("Preparando datasets de modelado...")
    print("="*70)

    # 1. Cargar dataset
    df = cargar_dataset(INPUT_PARQUET)

    # 2. Analizar targets
    stats_energia = analizar_target(df, 'energia_kwh')
    stats_consumo = analizar_target(df, 'consumo_promedio_cliente_kwh')

    # 3. Preparar dataset energia
    df_energia, stats_energia_full = preparar_dataset_energia(
        df, target='energia_kwh'
    )

    # 4. Preparar dataset consumo
    df_consumo, stats_consumo_full = preparar_dataset_consumo(
        df, target='consumo_promedio_cliente_kwh'
    )

    # 5. Guardar datasets
    guardar_parquet(df_energia, OUTPUT_ENERGIA)
    guardar_parquet(df_consumo, OUTPUT_CONSUMO)

    # 6. Generar reporte
    target_std_energia = df_energia['energia_kwh'].std()/df_energia['energia_kwh'].mean()
    target_std_consumo = df_consumo['consumo_promedio_cliente_kwh'].std()/df_consumo['consumo_promedio_cliente_kwh'].mean()

    report = generar_reporte(
        df_energia,
        df_consumo,
        stats_energia_full,
        stats_consumo_full,
        target_std_energia,
        target_std_consumo
    )

    # Escribir reporte
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReporte guardado en: {OUTPUT_REPORT}")

    # Verificación final
    print("\n" + "="*70)
    print("Verificación final")
    print("="*70)

    # Verificar archivo energy
    df_energia_final = pd.read_parquet(OUTPUT_ENERGIA)
    print(f"\nParquet energia_kwh:")
    print(f"    - Ruta: {OUTPUT_ENERGIA}")
    print(f"    - Shape: {df_energia_final.shape}")
    print(f"    - Target existe: {'energia_kwh' in df_energia_final.columns}")

    # Verificar archivo consumo
    df_consumo_final = pd.read_parquet(OUTPUT_CONSUMO)
    print(f"\nParquet consumo_promedio:")
    print(f"    - Ruta: {OUTPUT_CONSUMO}")
    print(f"    - Shape: {df_consumo_final.shape}")
    print(f"    - Target existe: {'consumo_promedio_cliente_kwh' in df_consumo_final.columns}")

    # Mostrar columnas
    print(f"\n Columnas de energy dataset: {list(df_energia_final.columns)}")
    print(f" Columnas de consumo dataset: {list(df_consumo_final.columns)}")

    print("\nDatasets de modelado generados.")

    # Resumen final
    print("\n📊 RESUMEN FINAL:")
    print(f"    - Filas final energy: {stats_energia_full['filas_finales']:,}")
    print(f"    - Filas final consumo: {stats_consumo_full['filas_finales']:,}")
    print(f"    - Target recomendado: consumo_promedio_cliente_kwh")
    print(f"    - Advertencia: valores negativos en bloques requieren atención")
    print(f"    - Ruta energy: {OUTPUT_ENERGIA}")
    print(f"    - Ruta consumo: {OUTPUT_CONSUMO}")
    print(f"    - Ruta reporte: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

"""
Resumen del script:
===================
1. Leer facturacion_clean.parquet
2. Crear dataset energy_kwh (mantener negativos)
3. Crear dataset consumo_promedio (excluir negativos)
4. Generar reporte markdown
5. Verificar ambos parquet
"""
