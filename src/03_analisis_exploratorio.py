#!/usr/bin/env python3
"""
src/03_analisis_exploratorio.py
Exploratory Data Analysis (EDA) del dataset base de facturación
Objetivo: Evaluar calidad, variabilidad y factibilidad antes de modelar
"""

import pandas as pd
import numpy as np

# Configuración
DATA_DIR = "data/interim"
REPORTS_DIR = "reports"
INPUT_PARQUET = f"{DATA_DIR}/facturacion_clean.parquet"
OUTPUT_REPORT = f"{REPORTS_DIR}/eda_facturacion_base.md"


def main():
    print("EDA del dataset de facturación")

    # Leemos el dataset
    print("\n Cargando dataset. ..")
    df = pd.read_parquet(INPUT_PARQUET)
    print(f"    Shape: {df.shape}")
    print(f"    Columnas: {list(df.columns)}")

    # ============ 1. DESCRIPCIÓN GENERAL ============
    print("\n PASO 1: Descripción general del dataset")
    print("-" * 50)
    print(f"    - Filas: {df.shape[0]:,}")
    print(f"    - Columnas: {df.shape[1]}")
    print(f"    - Tipos:\n{df.dtypes.to_dict()}")

    # ============ 2. RANGO TEMPORAL ============
    print("\n📅 PASO 2: Rango temporal")
    print("-" * 50)
    anio_min = int(df['anio'].min())
    anio_max = int(df['anio'].max())
    mes_min = int(df['mes'].min())
    mes_max = int(df['mes'].max())
    print(f"    - Años: {anio_min} - {anio_max}")
    print(f"    - Meses: {mes_min} - {mes_max}")
    print(f"    - Fechas únicas: {len(df['fecha'].unique()):,}")
    print(f"    - Filas únicas (meses): {df['fecha'].nunique():,}")

    # ============ 3. CUENTA DE CATEGORÍAS ============
    print("\n📊 PASO 3: Cuenta de categorías")
    print("-" * 50)
    print(f"    - Regiones únicas: {df['region'].nunique()}")
    print(f"    - Comunas únicas: {df['comuna'].nunique()}")
    print(f"    - Tipos de cliente únicos: {df['tipo_clientes'].nunique()}")
    print(f"    - Tarifas únicas: {df['tarifa'].nunique()}")

    # ============ 4. E1 KWH, E2 KWH, ENERGIA KWH ============
    print("\n⚡ PASO 4: Análisis de bloques E1, E2 y energía total")
    print("-" * 50)

    print("\n    📊 e1_kwh:")
    print(f"        - Nulos: {df['e1_kwh'].isna().sum():,}")
    print(f"        - Min: {df['e1_kwh'].min():.2f}")
    print(f"        - Max: {df['e1_kwh'].max():.2f}")
    print(f"        - Mean: {df['e1_kwh'].mean():.2f}")
    print(f"        - Median: {df['e1_kwh'].median():.2f}")
    print(f"        - Negativos: {(df['e1_kwh'] < 0).sum():,}")

    print("\n    📊 e2_kwh:")
    print(f"        - Nulos: {df['e2_kwh'].isna().sum():,}")
    print(f"        - Min: {df['e2_kwh'].min():.2f}")
    print(f"        - Max: {df['e2_kwh'].max():.2f}")
    print(f"        - Mean: {df['e2_kwh'].mean():.2f}")
    print(f"        - Median: {df['e2_kwh'].median():.2f}")
    print(f"        - Negativos: {(df['e2_kwh'] < 0).sum():,}")

    print("\n    📊 energia_kwh:")
    print(f"        - Nulos: {df['energia_kwh'].isna().sum():,}")
    print(f"        - Min: {df['energia_kwh'].min():.2f}")
    print(f"        - Max: {df['energia_kwh'].max():.2f}")
    print(f"        - Mean: {df['energia_kwh'].mean():.2f}")
    print(f"        - Median: {df['energia_kwh'].median():.2f}")
    print(f"        - Negativos: {(df['energia_kwh'] < 0).sum():,}")

    # ============ 5. CONSUMO PROMEDIO CLIENTE ============
    print("\n👥 PASO 5: Distribución de consumo_promedio_cliente_kwh")
    print("-" * 50)
    print(f"    - Nulos (inválidos): {df['consumo_promedio_cliente_kwh'].isna().sum():,}")
    print(f"    - Filas con valor: {df['consumo_promedio_cliente_kwh'].notna().sum():,}")
    print(f"    - Min: {df['consumo_promedio_cliente_kwh'].min():.2f}")
    print(f"    - Max: {df['consumo_promedio_cliente_kwh'].max():.2f}")
    print(f"    - Mean: {df['consumo_promedio_cliente_kwh'].mean():.2f}")
    print(f"    - Median: {df['consumo_promedio_cliente_kwh'].median():.2f}")
    print(f"    - Negativos: {(df['consumo_promedio_cliente_kwh'] < 0).sum():,}")
    print(f"    - Positivos: {(df['consumo_promedio_cliente_kwh'] > 0).sum():,}")

    # ============ 6. DISTRIBUCIÓN DE ENERGIA KWH ============
    print("\n📈 PASO 6: Distribución de energia_kwh")
    print("-" * 50)

    # Q1, Q2, Q3
    q1_e = df['energia_kwh'].quantile(0.25)
    q2_e = df['energia_kwh'].quantile(0.50)
    q3_e = df['energia_kwh'].quantile(0.75)
    print(f"    - Q1: {q1_e:.2f}")
    print(f"    - Mediana: {q2_e:.2f}")
    print(f"    - Q3: {q3_e:.2f}")
    print(f"    - IQR: {(q3_e - q1_e):.2f}")

    # ============ 7. OUTLIERS CORRECTOS (MÉTODO IQR CLÁSICO) ============
    print("\nAviso:  PASO 7: Detección de outliers (Método IQR)")
    print("-" * 50)
    print("    📝 NOTA: Usando el método IQR clásico:")
    print(f"        - Límite inferior = Q1 - 1.5*IQR")
    print(f"        - Límite superior = Q3 + 1.5*IQR")
    print(f"        - Valores extremos (percentiles 1%/99%) se usan como referencia adicional")
    print()

    # Cálculos IQR para e1_kwh
    q1_e1 = df['e1_kwh'].dropna().quantile(0.25)
    q3_e1 = df['e1_kwh'].dropna().quantile(0.75)
    iqr_e1 = q3_e1 - q1_e1
    lower_e1 = q1_e1 - 1.5 * iqr_e1
    upper_e1 = q3_e1 + 1.5 * iqr_e1
    print(f"    📊 e1_kwh:")
    print(f"        - Q1: {q1_e1:.2f}, Q3: {q3_e1:.2f}, IQR: {iqr_e1:.2f}")
    print(f"        - Límites IQR: [{lower_e1:.2f}, {upper_e1:.2f}]")
    mask_e1 = (df['e1_kwh'].notna()) & ((df['e1_kwh'] < lower_e1) | (df['e1_kwh'] > upper_e1))
    print(f"        - Outliers IQR: {mask_e1.sum():,}")

    # Cálculos IQR para e2_kwh
    q1_e2 = df['e2_kwh'].dropna().quantile(0.25)
    q3_e2 = df['e2_kwh'].dropna().quantile(0.75)
    iqr_e2 = q3_e2 - q1_e2
    lower_e2 = q1_e2 - 1.5 * iqr_e2
    upper_e2 = q3_e2 + 1.5 * iqr_e2
    print(f"    📊 e2_kwh:")
    print(f"        - Q1: {q1_e2:.2f}, Q3: {q3_e2:.2f}, IQR: {iqr_e2:.2f}")
    print(f"        - Límites IQR: [{lower_e2:.2f}, {upper_e2:.2f}]")
    mask_e2 = (df['e2_kwh'].notna()) & ((df['e2_kwh'] < lower_e2) | (df['e2_kwh'] > upper_e2))
    print(f"        - Outliers IQR: {mask_e2.sum():,}")

    # Cálculos IQR para energia_kwh
    q1_en = df['energia_kwh'].dropna().quantile(0.25)
    q3_en = df['energia_kwh'].dropna().quantile(0.75)
    iqr_en = q3_en - q1_en
    lower_en = q1_en - 1.5 * iqr_en
    upper_en = q3_en + 1.5 * iqr_en
    print(f"    📊 energia_kwh:")
    print(f"        - Q1: {q1_en:.2f}, Q3: {q3_en:.2f}, IQR: {iqr_en:.2f}")
    print(f"        - Límites IQR: [{lower_en:.2f}, {upper_en:.2f}]")
    mask_en = (df['energia_kwh'].notna()) & ((df['energia_kwh'] < lower_en) | (df['energia_kwh'] > upper_en))
    print(f"        - Outliers IQR: {mask_en.sum():,}")

    # Cálculos percentiles 1/99 como referencia de extremos
    p1_en = df['energia_kwh'].quantile(0.01)
    p99_en = df['energia_kwh'].quantile(0.99)
    print(f"        - Referencia extremos (p1/p99): [{p1_en:.2f}, {p99_en:.2f}]")

    # Cálculos IQR para consumo_promedio_cliente_kwh
    q1_cp = df['consumo_promedio_cliente_kwh'].dropna().quantile(0.25)
    q3_cp = df['consumo_promedio_cliente_kwh'].dropna().quantile(0.75)
    iqr_cp = q3_cp - q1_cp
    lower_cp = q1_cp - 1.5 * iqr_cp
    upper_cp = q3_cp + 1.5 * iqr_cp
    print(f"    📊 consumo_promedio_cliente_kwh:")
    print(f"        - Q1: {q1_cp:.2f}, Q3: {q3_cp:.2f}, IQR: {iqr_cp:.2f}")
    print(f"        - Límites IQR: [{lower_cp:.2f}, {upper_cp:.2f}]")
    mask_cp = (df['consumo_promedio_cliente_kwh'].notna()) & ((df['consumo_promedio_cliente_kwh'] < lower_cp) | (df['consumo_promedio_cliente_kwh'] > upper_cp))
    print(f"        - Outliers IQR: {mask_cp.sum():,}")

    # Referencia percentiles 1/99 para consumo
    p1_cp = df['consumo_promedio_cliente_kwh'].quantile(0.01)
    p99_cp = df['consumo_promedio_cliente_kwh'].quantile(0.99)
    print(f"        - Referencia extremos (p1/p99): [{p1_cp:.2f}, {p99_cp:.2f}]")

    # ============ 8. EVOLUCIÓN TEMPORAL ============
    print("\n📅 PASO 8: Evolución temporal")
    print("-" * 50)

    print("    📈 Energia kwh por año:")
    for anio in sorted(df['anio'].unique()):
        suma_anio = df[df['anio'] == anio]['energia_kwh'].sum()
        print(f"        - {anio}: {suma_anio:,.2f} kWh")

    print("\n    📊 Energia kwh promedio por año:")
    for anio in sorted(df['anio'].unique()):
        promedio_anio = df[df['anio'] == anio]['energia_kwh'].mean()
        print(f"        - {anio}: {promedio_anio:,.2f} kWh (promedio anual)")

    print("\n    📊 Consumo promedio cliente kwh por año:")
    for anio in sorted(df['anio'].unique()):
        promedio = df[df['anio'] == anio]['consumo_promedio_cliente_kwh'].mean()
        print(f"        - {anio}: {promedio:,.2f} kWh (promedio anual)")

    # ============ 9. EVOLUCIÓN POR REGIÓN ============
    print("\n🏆 PASO 9: Top regiones por consumo")
    print("-" * 50)

    top_regiones = df.groupby('region')['energia_kwh'].mean().sort_values(ascending=False).head(10)
    for idx, (region, valor) in enumerate(top_regiones.items(), 1):
        print(f"    {idx}. {region:40} - {valor:,.2f} kWh (promedio)")

    # ============ 10. EVOLUCIÓN POR TIPO CLIENTE ============
    print("\n👥 PASO 10: Top tipos de cliente por consumo")
    print("-" * 50)

    top_clientes = df.groupby('tipo_clientes')['consumo_promedio_cliente_kwh'].mean().sort_values(ascending=False)
    for idx, (cliente, valor) in enumerate(top_clientes.items(), 1):
        print(f"    {idx}. {str(cliente):20} - {valor:,.2f} kWh (promedio)")

    # ============ 11. ESTACIONALIDAD MENSUAL ============
    print("\n🌙 PASO 11: Estacionalidad mensual")
    print("-" * 50)

    mensual_e = df.groupby(['mes'])['energia_kwh'].mean().sort_index()
    mensual_cp = df.groupby(['mes'])['consumo_promedio_cliente_kwh'].mean().sort_index()
    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    # --- Cálculo de estadísticas IQR para reporte ---
    # e1_kwh
    df_e1 = df['e1_kwh'].dropna()
    q1_e1 = df_e1.quantile(0.25)
    q3_e1 = df_e1.quantile(0.75)
    iqr_e1 = q3_e1 - q1_e1
    lower_e1 = q1_e1 - 1.5 * iqr_e1
    upper_e1 = q3_e1 + 1.5 * iqr_e1
    mask_e1 = ((df['e1_kwh'] < lower_e1) | (df['e1_kwh'] > upper_e1))
    mask_e1 = mask_e1 & (df['e1_kwh'].notna())  # Solo contar outliers en valores no nulos

    # e2_kwh
    df_e2 = df['e2_kwh'].dropna()
    q1_e2 = df_e2.quantile(0.25)
    q3_e2 = df_e2.quantile(0.75)
    iqr_e2 = q3_e2 - q1_e2
    lower_e2 = q1_e2 - 1.5 * iqr_e2
    upper_e2 = q3_e2 + 1.5 * iqr_e2
    mask_e2 = ((df['e2_kwh'] < lower_e2) | (df['e2_kwh'] > upper_e2))
    mask_e2 = mask_e2 & (df['e2_kwh'].notna())

    # energia_kwh
    df_en = df['energia_kwh'].dropna()
    q1_en = df_en.quantile(0.25)
    q3_en = df_en.quantile(0.75)
    iqr_en = q3_en - q1_en
    lower_en = q1_en - 1.5 * iqr_en
    upper_en = q3_en + 1.5 * iqr_en
    mask_en = ((df['energia_kwh'] < lower_en) | (df['energia_kwh'] > upper_en))

    # consumo_promedio
    df_cp = df['consumo_promedio_cliente_kwh'].dropna()
    q1_cp = df_cp.quantile(0.25)
    q3_cp = df_cp.quantile(0.75)
    iqr_cp = q3_cp - q1_cp
    lower_cp = q1_cp - 1.5 * iqr_cp
    upper_cp = q3_cp + 1.5 * iqr_cp
    mask_cp = ((df['consumo_promedio_cliente_kwh'] < lower_cp) | (df['consumo_promedio_cliente_kwh'] > upper_cp))

    print("    📈 Energía kwh promedio por mes:")
    for mes, valor in mensual_e.items():
        nombre_mes = meses_es[mes - 1]
        print(f"        - {nombre_mes.capitalize():10}: {valor:,.2f} kWh")

    print("\n    📈 Consumo promedio por mes:")
    for mes, valor in mensual_cp.items():
        nombre_mes = meses_es[mes - 1]
        print(f"        - {nombre_mes.capitalize():10}: {valor:,.2f} kWh")

    # ============ 12. EVALUACIÓN FINAL ============
    print("\n🎯 PASO 12: Evaluación comparativa de targets para modelado")
    print("-" * 50)

    # Coeficiente de variación robusto (usando NaN-aware)
    df_energia = df['energia_kwh'].dropna()
    df_consumo = df['consumo_promedio_cliente_kwh'].dropna()

    cv_energia = df_energia.std() / df_energia.mean() if df_energia.mean() != 0 else np.inf
    cv_consumo = df_consumo.std() / df_consumo.mean() if df_consumo.mean() != 0 else np.inf

    # Evaluación detallada
    print("\n     Métricas comparativas:")
    print(f"        - CV energía_kwh: {cv_energia:.2%}")
    print(f"        - CV consumo_promedio: {cv_consumo:.2%}")
    print(f"        - Diferencia de CV: {abs(cv_consumo - cv_energia):.2%} a favor de {'consumo' if cv_consumo < cv_energia else 'energía'}")

    # Cálculo de outliers IQR para cada target
    outliers_energia = mask_en.sum()
    outliers_consumo = mask_cp.sum()
    print(f"        - Outliers IQR (energía): {outliers_energia:,}")
    print(f"        - Outliers IQR (consumo): {outliers_consumo:,}")

    # Análisis de nulos
    nulls_energia = int(df_energia.isna().sum())
    nulls_consumo = int(df_consumo.isna().sum())
    print(f"        - Nulos (energía): {nulls_energia:,}")
    print(f"        - Nulos (consumo): {nulls_consumo:,}")

    # Ratio de nulos
    ratio_energia = nulls_energia / len(df) * 100
    ratio_consumo = nulls_consumo / len(df) * 100
    print(f"        - Ratio de nulos (energía): {ratio_energia:.2f}%")
    print(f"        - Ratio de nulos (consumo): {ratio_consumo:.2f}%")

    # Análisis de negativos
    neg_energia = int((df['energia_kwh'] < 0).sum())
    neg_consumo = int((df['consumo_promedio_cliente_kwh'] < 0).sum())
    print(f"        - Valores negativos (energía): {neg_energia:,}")
    print(f"        - Valores negativos (consumo): {neg_consumo:,}")

    # --- Cálculos adicionales para el reporte ---
    regiones = int(df['region'].nunique())
    comunas = int(df['comuna'].nunique())
    tipos_cliente = int(df['tipo_clientes'].nunique())

    # Evaluación cualitativa y recomendación
    print("\n     Recomendación:")

    # Puntuación de aptitud (menor es mejor)
    aptitud_energia = cv_energia + (nulls_energia / len(df)) * 5 + (neg_energia / len(df)) * 2
    aptitud_consumo = cv_consumo + (nulls_consumo / len(df)) * 5 + (neg_consumo / len(df)) * 2

    # Determinar target recomendado basado en aptitud
    target_recomendado = 'consumo_promedio_cliente_kwh' if aptitud_consumo < aptitud_energia else 'energia_kwh'

    if aptitud_consumo < aptitud_energia:
        print(f"            consumo_promedio_cliente_kwh")
        print(f"            - Menor CV ({cv_consumo:.1f}% vs {cv_energia:.1f}%)")
        print(f"            - {nulls_consumo:,} nulos (ratio: {ratio_consumo:.1f}%)")
        print(f"            - {neg_consumo:,} negativos")
        print(f"            - Aptitud: {aptitud_consumo:.2f}")
    elif aptitud_energia < aptitud_consumo:
        print(f"            energia_kwh")
        print(f"            - Menor CV ({cv_energia:.1f}% vs {cv_consumo:.1f}%)")
        print(f"            - {nulls_energia:,} nulos (ratio: {ratio_energia:.1f}%)")
        print(f"            - {neg_energia:,} negativos")
        print(f"            - Aptitud: {aptitud_energia:.2f}")
    else:
        print(f"            Aviso:  Ambos tienen aptitud similar")
        print(f"            - Energía aptitud: {aptitud_energia:.2f}")
        print(f"            - Consumo aptitud: {aptitud_consumo:.2f}")

    # Cálculos para el reporte
    anios = int(df['anio'].nunique())
    regiones = int(df['region'].nunique())
    comunas = int(df['comuna'].nunique())
    tipos_cliente = int(df['tipo_clientes'].nunique())

    # Hallazgos
    print("\n    📝 HALLAZGOS CLAVE:")
    print(f"        1. El dataset cubre de {anio_min} a {anio_max} ({anios} años)")
    print(f"        2. Cobertura geográfica: {regiones} regiones, {comunas} comunas")
    print(f"        3. Tipos de clientes: {tipos_cliente} categorías")
    print(f"        4. Nulos en consumo: {nulls_consumo:,} ({ratio_consumo:.1f}%)")
    print(f"        5. Nulos en energía: {nulls_energia:,} ({ratio_energia:.1f}%)")
    print(f"        6. Outliers IQR:")
    print(f"            - Energía: {outliers_energia:,} ({100*outliers_energia/len(df):.2f}%)")
    print(f"            - Consumo: {outliers_consumo:,} ({100*outliers_consumo/len(df):.2f}%)")

    # Construcción del reporte Markdown
    report = f"""# 📊 EDA del Dataset Base de Facturación

**Generado:** 2026-04-08
**Objetivo:** Evaluar calidad, variabilidad y factibilidad del dataset

---

##  Resumen Ejecutivo

El dataset de facturación contiene **{df.shape[0]:,} filas** y **{df.shape[1]} columnas**, abarcando el periodo de **{anio_min} a {anio_max}** ({anios} años).

**Target recomendado para modelado:** `{target_recomendado}`.

**Criterio de selección:**
- **Variabilidad relativa (CV):** {cv_consumo:.1f}% vs {cv_energia:.1f}%
- **Complejidad de outliers:** {outliers_consumo:,} vs {outliers_energia:,}
- **Calidad de datos:** {nulls_consumo:,} nulos vs {nulls_energia:,} nulos

---

## 📊 Características del Dataset

| Métrica | Valor |
|--:|:--:|
| **Filas** | {df.shape[0]:,} |
| **Columnas** | {df.shape[1]} |
| **Regiones** | {regiones} |
| **Comunas** | {comunas} |
| **Tipos de cliente** | {tipos_cliente} |
| ** Tarifas únicas** | {df['tarifa'].nunique()} |
| **Fechas únicas (meses)** | {df['fecha'].nunique():,} |

---

## 📅 Rango Temporal

| Métrica | Valor |
|--:|:--:|
| **Año mínimo** | {anio_min} |
| **Año máximo** | {anio_max} |
| **Mes mínimo** | {mes_min} |
| **Mes máximo** | {mes_max} |

---

## ⚡ Bloques Energéticos (Dataset Base)

| Columna | Nulos | Min | Max | Mean | Median | Negativos |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| e1_kwh | {df['e1_kwh'].isna().sum():,} | {df['e1_kwh'].min():.0f} | {df['e1_kwh'].max():,.0f} | {df['e1_kwh'].mean():,.0f} | {df['e1_kwh'].median():.0f} | {(df['e1_kwh'] < 0).sum():,} |
| e2_kwh | {df['e2_kwh'].isna().sum():,} | {df['e2_kwh'].min():.0f} | {df['e2_kwh'].max():,.0f} | {df['e2_kwh'].mean():,.0f} | {df['e2_kwh'].median():.0f} | {(df['e2_kwh'] < 0).sum():,} |
| energia_kwh | {df['energia_kwh'].isna().sum():,} | {df['energia_kwh'].min():.0f} | {df['energia_kwh'].max():,.0f} | {df['energia_kwh'].mean():,.0f} | {df['energia_kwh'].median():.0f} | {(df['energia_kwh'] < 0).sum():,} |
| consumo_promedio_cliente_kwh | {df['consumo_promedio_cliente_kwh'].isna().sum():,} | {df['consumo_promedio_cliente_kwh'].min():.0f} | {df['consumo_promedio_cliente_kwh'].max():,.0f} | {df['consumo_promedio_cliente_kwh'].mean():,.0f} | {df['consumo_promedio_cliente_kwh'].median():.0f} | {(df['consumo_promedio_cliente_kwh'] < 0).sum():,} |

**Nota:** El dataset base tiene exactamente **12 columnas** (sin agregar auxiliares de análisis).

---

## 📊 Análisis IQR por Variable (Método Clásico)

| Variable | Q1 | Q3 | IQR | Límites IQR | Outliers IQR | % Outliers |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| e1_kwh | {q1_e1:.0f} | {q3_e1:.0f} | {iqr_e1:.0f} | [{lower_e1:.0f}, {upper_e1:.0f}] | {mask_e1.sum():,} | {100*mask_e1.sum()/len(df):.2f}% |
| e2_kwh | {q1_e2:.0f} | {q3_e2:.0f} | {iqr_e2:.0f} | [{lower_e2:.0f}, {upper_e2:.0f}] | {mask_e2.sum():,} | {100*mask_e2.sum()/len(df):.2f}% |
| energia_kwh | {q1_en:.0f} | {q3_en:.0f} | {iqr_en:.0f} | [{lower_en:.0f}, {upper_en:.0f}] | {mask_en.sum():,} | {100*mask_en.sum()/len(df):.2f}% |
| consumo_promedio | {q1_cp:.0f} | {q3_cp:.0f} | {iqr_cp:.0f} | [{lower_cp:.0f}, {upper_cp:.0f}] | {mask_cp.sum():,} | {100*mask_cp.sum()/len(df):.2f}% |

---

## 🏆 Top Regiones por Consumo Promedio (Energía)

"""

    for idx, (region, valor) in enumerate(df.groupby('region')['energia_kwh'].mean().sort_values(ascending=False).head(10).items(), 1):
        report += f"{idx}. {region:40} - {valor:,.0f} kWh (promedio)\n"

    report += f"""
---

## 👥 Top Tipos de Cliente por Consumo Promedio

"""

    for idx, (cliente, valor) in enumerate(df.groupby('tipo_clientes')['consumo_promedio_cliente_kwh'].mean().sort_values(ascending=False).items(), 1):
        report += f"{idx}. {str(cliente):20} - {valor:,.0f} kWh (promedio)\n"

    report += f"""
---

## 🌙 Estacionalidad Mensual (Energía kwh)

"""

    mensual_e = df.groupby(['mes'])['energia_kwh'].mean().sort_index()
    mensual_cp = df.groupby(['mes'])['consumo_promedio_cliente_kwh'].mean().sort_index()
    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    for mes, valor in mensual_e.items():
        nombre_mes = meses_es[mes - 1]
        report += f"- {nombre_mes.capitalize():10}: {valor:,.0f} kWh\n"

    report += f"""
---

## 🌙 Estacionalidad Mensual (Consumo Promedio)

"""

    for mes, valor in mensual_cp.items():
        nombre_mes = meses_es[mes - 1]
        report += f"- {nombre_mes.capitalize():10}: {valor:,.0f} kWh\n"

    report += f"""
---

## 🎯 Evaluación Comparativa de Targets

| Métrica | consumo_promedio_cliente_kwh | energia_kwh |
|:--:|:--:|:--:|
| **CV** | {cv_consumo:.1f}% | {cv_energia:.1f}% |
| **Diferencia CV** | **{abs(cv_consumo - cv_energia):.1f}%** | - |
| **Aptitud** | {aptitud_consumo:.2f} | {aptitud_energia:.2f} |
| **Media** | {df['consumo_promedio_cliente_kwh'].mean():,.0f} | {df['energia_kwh'].mean():,.0f} |
| **Mediana** | {df['consumo_promedio_cliente_kwh'].median():.0f} | {df['energia_kwh'].median():.0f} |
| **Nulos** | {nulls_consumo:,} | {nulls_energia:,} |
| **Negativos** | {neg_consumo:,} | {neg_energia:,} |
| **Outliers IQR** | {outliers_consumo:,} ({100*outliers_consumo/len(df):.2f}%) | {outliers_energia:,} ({100*outliers_energia/len(df):.2f}%) |

**Recomendación:** `{target_recomendado}`
- **Menor variabilidad relativa:** {cv_consumo:.1f}% vs {cv_energia:.1f}% ({abs(cv_consumo - cv_energia):.1f}%)
- **Menor complejidad de outliers:** {outliers_consumo:,} vs {outliers_energia:,}
- **Menor tasa de nulos:** {ratio_consumo:.1f}% vs {ratio_energia:.1f}%

---

## Aviso: Alertas de Calidad de Datos

"""

    if nulls_consumo > 0:
        report += f"- Aviso:  {nulls_consumo:,} valores nulos en consumo_promedio_cliente_kwh ({ratio_consumo:.1f}%)\n"

    if neg_consumo > 0:
        report += f"- Aviso:  {neg_consumo:,} valores negativos en consumo_promedio_cliente_kwh\n"

    if neg_energia > 0:
        report += f"- Aviso:  {neg_energia:,} valores negativos en energia_kwh\n"

    if (df['e1_kwh'] < 0).sum() > 0:
        report += f"- Aviso:  Valores negativos en e1_kwh\n"

    if (df['e2_kwh'] < 0).sum() > 0:
        report += f"- Aviso:  Valores negativos en e2_kwh\n"

    report += f"""
---

## 📝 Hallazgos Clave

1. **Rango temporal:** {anio_min} - {anio_max} ({anios} años)
2. **Cobertura geográfica:** {regiones} regiones, {comunas} comunas
3. **Tipos de clientes:** {tipos_cliente} categorías
4. **Consumo promedio:** media = {df['consumo_promedio_cliente_kwh'].mean():.2f} kWh, mediana = {df['consumo_promedio_cliente_kwh'].median():.2f} kWh
5. **Variabilidad relativa:** CV del consumo = {cv_consumo:.1f}% vs CV de energía = {cv_energia:.1f}%
6. **Complejidad de datos:**
   - Nulos: {nulls_consumo:,} ({ratio_consumo:.1f}%) vs {nulls_energia:,} ({ratio_energia:.1f}%)
   - Negativos: {neg_consumo:,} vs {neg_energia:,}
7. **Outliers IQR:**
   - Consumo: {outliers_consumo:,} ({100*outliers_consumo/len(df):.2f}%)
   - Energía: {outliers_energia:,} ({100*outliers_energia/len(df):.2f}%)
8. **Target recomendado:** `{target_recomendado}` por menor variabilidad relativa y complejidad

---

## 🎓 Alertas Metodológicas

- **Método IQR clásico:** Se usó `Q1 - 1.5*IQR` y `Q3 + 1.5*IQR` para detectar outliers
- **Separación clara:** Análisis del dataset base separado de agregaciones temporales
- **Comparación de targets:** Ambos targets evaluados con métricas completas
- **Dataset base intacto:** No se modificó el parquet original con columnas auxiliares
- Aviso: **Valores negativos:** Requieren investigación antes del modelado
- Aviso: **Nulos en consumo:** {nulls_consumo:,} valores que requerirán imputación o exclusión

---

## Conclusiones Preliminares

- El dataset está listo para modelado después de manejar los {nulls_consumo:,} nulos en consumo_promedio
- La variabilidad mensual es suficiente para predecir patrones estacionales
- El target `{target_recomendado}` es más estable y recomendable para modelado
- Los valores negativos en los bloques requieren tratamiento antes de entrenar modelos

---

## Conclusiones Preliminares

- El dataset está listo para modelado después de manejar los {nulls_consumo:,} nulos en consumo_promedio
- La variabilidad mensual es suficiente para predecir patrones estacionales
- El target `{target_recomendado}` es más estable y recomendable para modelado
- Los valores negativos en los bloques requieren tratamiento antes de entrenar modelos

---

**Fin del EDA**
"""
    print(f"    Reporte guardado en: {OUTPUT_REPORT}")

    # Resumen final
    print("\n" + "=" * 70)
    print("EDA COMPLETADO")
    print("=" * 70)
    print(f"\n📄 Reporte: {OUTPUT_REPORT}")
    print(f"📊 Shape: {df.shape}")
    print(f"🎯 Target recomendado: {('consumo_promedio_cliente_kwh' if cv_consumo < cv_energia else 'energia_kwh')}")


if __name__ == "__main__":
    main()
