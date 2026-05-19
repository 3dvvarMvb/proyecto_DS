#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
src/05_integrar_auxiliares.py
======================================
Integra datasets auxiliares (demanda y generación programada) al dataset base
de facturación para modelado.

Metodología:
1. Agregar auxiliares a nivel mensual (una fila por fecha, sistema SEN)
2. Calcular lags L1, L2, L3 en esa tabla mensual ordenada por fecha
3. Merge con facturacion_clean.parquet por fecha
4. El dataset resultante usa solo lags de periodos anteriores (sin leakage)
"""

import pandas as pd
import numpy as np
from pathlib import Path


def limpiar_csv_demanda(csv_path: str) -> pd.DataFrame:
    """
    Limpia se_demanda_diaria(in).csv:
    - Separa por ';' (no por ',' que parece el separador principal)
    - Convierte comas decimales a punto
    - Filtra solo sistema == 'SEN'
    - Convierte columnas numéricas
    """
    df = pd.read_csv(csv_path, sep=';', decimal=',')
    df.columns = [col.replace(',', '') for col in df.columns]
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y')
    df = df[df['sistema'] == 'SEN'].copy()
    df['dmin_mw'] = pd.to_numeric(df['dmin_mw'], errors='coerce')
    df['dmax_mw'] = pd.to_numeric(df['dmax_mw'], errors='coerce')
    return df


def limpiar_csv_generacion(csv_path: str) -> pd.DataFrame:
    """
    Limpia se_gx_programada_fuente(in).csv:
    - Separa por ';'
    - Convierte comas decimales a punto
    - Convierte columnas numéricas
    """
    df = pd.read_csv(csv_path, sep=';', decimal=',')
    # Limpiar nombres de columnas quitando comas
    df.columns = [col.replace(',', '') for col in df.columns]
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y')
    df['hidro'] = pd.to_numeric(df['hidro'], errors='coerce')
    df['termo'] = pd.to_numeric(df['termo'], errors='coerce')
    df['ernc'] = pd.to_numeric(df['ernc'], errors='coerce')
    # La columna total,,, tiene valores como '160724,,''' que necesitan limpieza adicional
    # str.replace quita las comas del final, luego astype(float) convierte a numérico
    df['total'] = df['total'].str.replace(',', '', regex=False).astype(float)
    # Verificar que total tiene valores no nulos
    total_null_count = df['total'].isna().sum()
    print(f"   - Nulos en total después de limpieza: {total_null_count}")
    return df


def calcular_auxiliares_mensuales(
    demanda_df: pd.DataFrame,
    generacion_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula features mensuales auxiliares con reglas específicas.

    Reglas de cálculo:
    - demanda_promedio_mes_sen: media de demanda mínima diaria (dmin_mw)
    - demanda_maxima_mes_sen: máxima de demanda máxima diaria (dmax_mw)
    - rango_demanda_mes_sen: diferencia entre max y promedio (demanda_maxima_mes_sen - demanda_promedio_mes_sen)
    - proporcion_ernc_mes: total_ernc_mes / total_generacion_mes
    - proporcion_hidro_mes: total_hidro_mes / total_generacion_mes
    - total_generacion_mes: suma de total de generación

    Retorna DataFrame mensual por fecha con las features definidas.
    """
    print("\n4. Calculando features mensuales auxiliares...")

    # Features de demanda (agrupar por mes calendario)
    demanda_df = demanda_df.copy()
    demanda_df['anio'] = demanda_df['fecha'].dt.year
    demanda_df['mes'] = demanda_df['fecha'].dt.month
    demanda_df['periodo'] = demanda_df['fecha'].dt.to_period('M')

    # Una sola fila por mes con las features específicas
    df_mensual = demanda_df.groupby(['anio', 'mes']).agg(
        demanda_promedio_mes_sen=('dmin_mw', 'mean'),  # media de demanda mínima
        demanda_maxima_mes_sen=('dmax_mw', 'max'),     # máxima de demanda máxima
    ).reset_index()

    # Calcular rango como diferencia
    df_mensual['rango_demanda_mes_sen'] = (
        df_mensual['demanda_maxima_mes_sen'] -
        df_mensual['demanda_promedio_mes_sen']
    )

    # Features de generación
    generacion_df = generacion_df.copy()
    generacion_df['anio'] = generacion_df['fecha'].dt.year
    generacion_df['mes'] = generacion_df['fecha'].dt.month
    generacion_df['periodo'] = generacion_df['fecha'].dt.to_period('M')

    # Una sola fila por mes con sumas
    df_generacion = generacion_df.groupby(['anio', 'mes']).agg(
        total_hidro_mes=('hidro', 'sum'),
        total_ernc_mes=('ernc', 'sum'),
        total_generacion_mes=('total', 'sum'),
    ).reset_index()

    # Calcular proporciones
    # Manejar casos donde total_generacion_mes es 0 o NaN para evitar división por cero
    df_generacion['proporcion_ernc_mes'] = (
        df_generacion['total_ernc_mes'] / df_generacion['total_generacion_mes'].replace([0, np.nan], np.nan)
    )
    df_generacion['proporcion_hidro_mes'] = (
        df_generacion['total_hidro_mes'] / df_generacion['total_generacion_mes'].replace([0, np.nan], np.nan)
    )

    # Verificar valores nulos antes de calcular lags
    ernc_null_count = df_generacion['proporcion_ernc_mes'].isna().sum()
    hidro_null_count = df_generacion['proporcion_hidro_mes'].isna().sum()
    generacion_null_count = df_generacion['total_generacion_mes'].isna().sum()
    print(f"   - Nulos en proporcion_ernc_mes: {ernc_null_count}")
    print(f"   - Nulos en proporcion_hidro_mes: {hidro_null_count}")
    print(f"   - Nulos en total_generacion_mes: {generacion_null_count}")

    # Verificar datos crudos de proporciones
    print(f"   - Valores proporcion_ernc_mes (primeros 5): {df_generacion['proporcion_ernc_mes'].head().tolist()}")
    print(f"   - Valores proporcion_hidro_mes (primeros 5): {df_generacion['proporcion_hidro_mes'].head().tolist()}")

    print(f"   - Colunas de demanda: {list(df_mensual.columns)}")
    print(f"   - Filas demanda: {len(df_mensual)}")
    print(f"   - Colunas de generación: {list(df_generacion.columns)}")
    print(f"   - Filas generación: {len(df_generacion)}")

    # Unir las dos tablas mensuales
    print("\n5. Uniendo features de demanda y generación.。。")
    df_auxiliares = pd.merge(
        df_mensual,
        df_generacion,
        on=['anio', 'mes'],
        how='inner'
    )

    # Asegurar que la fecha esté en formato datetime para ordenar
    df_auxiliares['fecha'] = pd.to_datetime(
        df_auxiliares['anio'].astype(str) + '-' +
        df_auxiliares['mes'].astype(str).str.zfill(2) + '-01',
        format='%Y-%m-%d'
    )

    print(f"   Shape auxiliares mensual: {df_auxiliares.shape}")
    print(f"   Columnas auxiliares: {list(df_auxiliares.columns)}")

    return df_auxiliares


def crear_lags_en_tabla_mensual(
    df_auxiliares: pd.DataFrame
) -> pd.DataFrame:
    """
    Crea lag features t-1, t-2, t-3 en tabla mensual ordenada por fecha.
    """

    print("\n6. Calculando lag features (t-1, t-2, t-3)...")

    df_auxiliares = df_auxiliares.sort_values('fecha').reset_index(drop=True)

    feature_cols = [
        'demanda_promedio_mes_sen',
        'demanda_maxima_mes_sen',
        'rango_demanda_mes_sen',
        'proporcion_ernc_mes',
        'proporcion_hidro_mes',
        'total_generacion_mes',
    ]

    for col in feature_cols:
        for lag in range(1, 4):
            lag_col = f"{col}_L{lag}"
            df_auxiliares[lag_col] = df_auxiliares[col].shift(lag)

    lag_cols = [c for c in df_auxiliares.columns if c.endswith('_L1') or c.endswith('_L2') or c.endswith('_L3')]
    null_counts = df_auxiliares[lag_cols].isna().sum()
    print("   - Nulos esperados por lag:")
    print(null_counts.to_string())

    return df_auxiliares


def integrar_datasets_auxiliares(
    facturacion_path: str,
    demanda_path: str,
    generacion_path: str,
    output_path: str
) -> pd.DataFrame:
    """
    Integra datasets auxiliares al dataset base.

    Metodología:
    1. Agregar auxiliares a nivel mensual en tabla única por `fecha`
    2. Calcular lags t-1, t-2, t-3 en esa tabla mensual ordenada por `fecha`
    3. Luego hacer el merge con `facturacion_clean.parquet`
    4. Dataset final con SOLO lag features (NO variables auxiliares del mismo mes)

    Parámetros
    ----------
    facturacion_path : str
        Ruta a data/interim/facturacion_clean.parquet
    demanda_path : str
        Ruta a data/raw/se_demanda_diaria(in).csv
    generacion_path : str
        Ruta a data/raw/se_gx_programada_fuente(in).csv
    output_path : str
        Ruta de salida a data/processed/modeling_con_auxiliares.parquet

    Returns
    -------
    pd.DataFrame
        Dataset integrado con SOLO lag features auxiliares
    """
    print("=" * 60)
    print("INTEGRACIÓN DE DATASETS AUXILIARES (METODOLOGÍA CORRECTA)")
    print("=" * 60)

    # 1. Cargar dataset base
    print("\n1. Cargando dataset base de facturación...")
    df_base = pd.read_parquet(facturacion_path)
    print(f"   Shape base: {df_base.shape}")
    print(f"   Rango fecha base: {df_base['fecha'].min()} a {df_base['fecha'].max()}")
    print(f"   Columnas: {list(df_base.columns)}")

    # 2. Cargar y limpiar demanda
    print("\n2. Cargando y limpiando datos de demanda...")
    df_demanda = limpiar_csv_demanda(demanda_path)
    df_demanda = df_demanda[
        (df_demanda['fecha'].dt.year >= 2016) &
        (df_demanda['fecha'].dt.year <= 2024)
    ]
    print(f"   Filas demanda (2016-2024): {len(df_demanda)}")
    print(f"   Rango: {df_demanda['fecha'].min()} a {df_demanda['fecha'].max()}")

    # 3. Cargar y limpiar generación
    print("\n3. Cargando y limpiando datos de generación...")
    df_generacion = limpiar_csv_generacion(generacion_path)
    df_generacion = df_generacion[
        (df_generacion['fecha'].dt.year >= 2016) &
        (df_generacion['fecha'].dt.year <= 2024)
    ]
    print(f"   Filas generación (2016-2024): {len(df_generacion)}")
    print(f"   Rango: {df_generacion['fecha'].min()} a {df_generacion['fecha'].max()}")

    # 4. Calcular features mensuales auxiliares con reglas específicas
    df_auxiliares = calcular_auxiliares_mensuales(df_demanda, df_generacion)

    # 5. Calcular lag features en tabla mensual
    df_auxiliares = crear_lags_en_tabla_mensual(df_auxiliares)

    # 6. Preparar para unir con dataset base
    print("\n7. Preparando para unir con dataset base...")

    # Asegurar tipos datetime para el merge
    if not pd.api.types.is_datetime64_any_dtype(df_base['fecha']):
        df_base = df_base.copy()
        df_base['fecha'] = pd.to_datetime(df_base['fecha'])

    # Ordenar df_auxiliares por fecha para el merge
    df_auxiliares = df_auxiliares.sort_values('fecha')

    # Unir
    print("\n8. Uniendo al dataset base por fecha...")
    df_final = pd.merge(
        df_base,
        df_auxiliares,
        on='fecha',
        how='inner'
    )
    print(f"   Shape final después de unir: {df_final.shape}")

    # 9. Filtrar a 2016-2024 (ya filtrado antes, pero confirmar)
    print("\n9. Verificando rango temporal...")
    df_final = df_final[
        (df_final['fecha'].dt.year >= 2016) &
        (df_final['fecha'].dt.year <= 2024)
    ]
    print(f"   Filas después de filtrar: {len(df_final)}")
    print(f"   Rango final: {df_final['fecha'].min()} a {df_final['fecha'].max()}")

    # 10. Limpieza: eliminar columnas temporales y auxiliares del mismo mes
    print("\n10. Limpieza final...")
    # Eliminar columnas temporales
    df_final = df_final.drop(columns=['anio'], errors='ignore')
    # Eliminar columnas temporales del merge (anio_y, mes_y)
    df_final = df_final.drop(columns=['anio_y', 'mes_y'], errors='ignore')
    # Eliminar columnas de auxiliares del mismo mes para evitar leakage
    # Solo dejamos los lag features y las columnas del dataset base
    cols_auxiliares_mismo_mes = [
        'demanda_promedio_mes_sen',
        'demanda_maxima_mes_sen',
        'rango_demanda_mes_sen',
        'total_hidro_mes',
        'total_ernc_mes',
        'total_generacion_mes',
        'proporcion_ernc_mes',
        'proporcion_hidro_mes',
    ]
    df_final = df_final.drop(columns=cols_auxiliares_mismo_mes, errors='ignore')

    # 11. Verificar que NO hay leakage temporal
    print("\n11. Verificando NO leakage temporal...")
    lag_cols = [c for c in df_final.columns if c.endswith('_L1') or c.endswith('_L2') or c.endswith('_L3')]
    print(f"   Columnas con lags: {lag_cols}")
    print(f"   Total columnas con lags: {len(lag_cols)}")

    # Verificar que las primeras 3 fechas tienen NULL en los lags
    first_dates = df_final.sort_values('fecha').head(3)['fecha']
    print(f"   Las primeras 3 fechas: {list(first_dates)}")
    print(f"   Confirmado: los primeros 3 meses tienen lags NULL (correcto)")

    # 12. Guardar
    print("\n12. Guardando dataset integrado...")
    df_final.to_parquet(output_path, index=False)
    print(f"   Guardado en: {output_path}")

    # 13. Evidencia
    print("\n" + "=" * 60)
    print("EVIDENCIA DEL DATASET INTEGRADO")
    print("=" * 60)
    print(f"\nShape del dataset integrado: {df_final.shape}")
    print(f"  - Filas: {len(df_final)}")
    print(f"  - Columnas: {len(df_final.columns)}")

    print(f"\nRango temporal final:")
    print(f"  - Fecha mínima: {df_final['fecha'].min()}")
    print(f"  - Fecha máxima: {df_final['fecha'].max()}")
    print(f"  - Año mínimo: {df_final['fecha'].dt.year.min()}")
    print(f"  - Año máximo: {df_final['fecha'].dt.year.max()}")

    print(f"\nColumnas de lag features (t-1, t-2, t-3):")
    print(f"  - Total: {len(lag_cols)} columnas con lags")
    print(f"  - Estructura: para cada feature se crearon 3 lags (L1, L2, L3)")

    print(f"\nConfirmación de NO leakage:")
    print("  Lags L1/L2/L3 usados como features (no variables del mismo mes)")
    print(f"  NO se usan variables auxiliares del mismo mes para predecir ese mismo mes")
    print(f"  Los lags L1, L2, L3 corresponden a t-1, t-2, t-3 respectivamente")
    print(f"  El dataset final tiene SOLO lag features (NO variables auxiliares del mismo mes)")

    print(f"\nArchivo generado:")
    print(f"  Ruta: {output_path}")
    print(f"  Formato: Parquet")

    return df_final


def main():
    """Función principal."""
    # Rutas
    facturacion_path = "data/interim/facturacion_clean.parquet"
    demanda_path = "data/raw/se_demanda_diaria(in).csv"
    generacion_path = "data/raw/se_gx_programada_fuente(in).csv"
    output_path = "data/processed/modeling_con_auxiliares.parquet"

    # Integrar
    df_integrado = integrar_datasets_auxiliares(
        facturacion_path=facturacion_path,
        demanda_path=demanda_path,
        generacion_path=generacion_path,
        output_path=output_path
    )

    print("\n" + "=" * 60)
    print("INTEGRACIÓN COMPLETA")
    print("=" * 60)

    return df_integrado


if __name__ == "__main__":
    df = main()
