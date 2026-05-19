#!/usr/bin/env python3
"""
src/02_limpieza_facturacion.py
Limpieza y estandarización del dataset base de facturación.

Transforma el CSV crudo en facturacion_clean.parquet:
- fecha como datetime (primer día del mes)
- consumo_promedio_cliente_kwh = NaN cuando clientes_facturados == 0
"""

import pandas as pd
import os

# Configuración
RAW_FILE = "data/raw/se_facturacion_clientes_regulados(in).csv"
INTERIM_DIR = "data/interim"
REPORTS_DIR = "reports"
OUTPUT_PARQUET = os.path.join(INTERIM_DIR, "facturacion_clean.parquet")
OUTPUT_CSV = os.path.join(INTERIM_DIR, "facturacion_clean.csv")
REPORT_FILE = os.path.join(REPORTS_DIR, "facturacion_clean_summary.md")


def main():
    """Limpia y estandariza facturacion_clean.parquet desde el CSV crudo."""
    print("Limpiando dataset de facturación...")

    # Paso 1: Leer CSV (detectar separador)
    print("\n PASO 1: Leyendo archivo CSV...")
    try:
        df = pd.read_csv(RAW_FILE, sep=';', encoding='utf-8', dtype=str)
        print(f"    Leído {len(df):,} filas")
        print(f"    Columnas originales: {list(df.columns)}")
        print(f"    Tipo de datos originales: {df.dtypes.to_dict()}")
    except Exception as e:
        print(f"    ERROR: ERROR leyendo archivo: {e}")
        return

    # Paso 2: Estandarizar nombres a snake_case
    print("\n📝 PASO 2: Estandarizando nombres de columnas...")
    df.columns = [col.strip().lower().replace(' ', '_').replace("'", '').replace('(', '').replace(')', '')
                  for col in df.columns]
    print(f"    Columnas estandarizadas: {list(df.columns)}")

    # Paso 3: Limpiar strings (trim)
    print("\n🧹 PASO 3: Limpiando strings (trim de espacios)...")
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    print(f"    Trim aplicado a {len(df.select_dtypes(include=['object']).columns)} columnas de texto")

    # Paso 4: Corregir tipos de datos
    print("\n🔧 PASO 4: Corrigiendo tipos de datos...")

    # Columnas numéricas (enteros)
    cols_entero = ['anio', 'mes', 'clientes_facturados']
    for col in cols_entero:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            print(f"    {col}: convertido a Int64 (nulos: {int(df[col].isna().sum()):,})")

    # Columnas flotantes (numéricas con decimales)
    cols_float = ['e1_kwh', 'e2_kwh', 'energia_kwh']
    for col in cols_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            print(f"    {col}: convertido a Float64 (nulos: {int(df[col].isna().sum()):,})")

    # Mantener tarifa como string/categórica
    if 'tarifa' in df.columns:
        print(f"    tarifa: mantenido como string (nulos: {int(df['tarifa'].isna().sum()):,})")

    # Paso 5: Crear columna fecha como datetime real (YYYY-MM-01)
    print("\n📅 PASO 5: Creando columna fecha datetime real (YYYY-MM-01)...")
    if 'anio' in df.columns and 'mes' in df.columns:
        # Crear formato YYYY-MM (sin espacios extraños)
        df['fecha_str'] = (df['anio'].astype(str) + '-' + df['mes'].astype(str).str.zfill(2))
        # Convertir directamente a datetime (primer día del mes: 01)
        df['fecha'] = pd.to_datetime(df['fecha_str'], format='%Y-%m', errors='coerce')
        count_valid = int(df['fecha'].notna().sum())
        print(f"    Columna 'fecha' creada como datetime: {count_valid:,} valores válidos")
        print(f"    Tipo de 'fecha': {df['fecha'].dtype}")
        del df['fecha_str']
    else:
        df['fecha'] = pd.NaT
        print(f"    Aviso:  No se pudo crear columna 'fecha' (falta 'anio' o 'mes')")

    # Paso 6: Revisar nulos
    print("\n PASO 6: Revisando nulos por columna...")
    nulos = df.isnull().sum()
    total_nulos = int(nulos.sum())
    print(f"    Nulos totales: {total_nulos:,}")
    print(f"    Distribución:")
    for col, nulo in nulos.items():
        pct = (nulo / len(df)) * 100 if len(df) > 0 else 0
        print(f"        - {col}: {nulo:,} ({pct:.2f}%)")

    # Paso 7: Revisar duplicados
    print("\n🔄 PASO 7: Revisando duplicados...")
    dup_exactos = int(df.duplicated().sum())
    print(f"    Duplicados exactos detectados: {dup_exactos:,}")

    if dup_exactos > 0:
        dup_counts = df.groupby(['anio', 'mes', 'region', 'comuna', 'tipo_clientes']).size()
        dup_counts = dup_counts[dup_counts > 1]
        if not dup_counts.empty:
            print(f"    Aviso:  {int(len(dup_counts))} grupos con duplicados exactos")
            for idx in list(dup_counts.head(5).index):
                print(f"        - {idx[0]}-{idx[1]}, {idx[2][:30]}, {idx[3]}, {idx[4]}: {int(dup_counts[idx]):,} duplicados")

    # Paso 8: Crear consumo_promedio_cliente_kwh con NaN (no ceros artificiales)
    print("\n📊 PASO 8: Calculando consumo_promedio_cliente_kwh (NaN para casos inválidos)...")
    # Identificar filas con datos válidos para el cálculo
    valido = (
        df['clientes_facturados'].notna() &
        (df['clientes_facturados'] > 0) &
        df['energia_kwh'].notna()
    )
    # Calcular solo para filas válidas
    df.loc[valido, 'consumo_promedio_cliente_kwh'] = (
        df.loc[valido, 'energia_kwh'] / df.loc[valido, 'clientes_facturados']
    )
    # Dejar NaN en filas inválidas
    df.loc[~valido, 'consumo_promedio_cliente_kwh'] = pd.NA
    nulos_consumo = int(df['consumo_promedio_cliente_kwh'].isna().sum())
    print(f"    Columna creada")
    print(f"    Nulos en consumo_promedio_cliente_kwh: {nulos_consumo:,}")
    print(f"    Valores válidos: {int((df['consumo_promedio_cliente_kwh'].notna()).sum()):,}")
    print(f"    Valores NaN (correctos, no artificiales)")

    # Paso 9: Eliminar duplicados exactos
    print("\n🗑️  PASO 9: Eliminando duplicados exactos...")
    df_limpio = df.drop_duplicates()
    duplicados_eliminados = len(df) - len(df_limpio)
    print(f"    Duplicados eliminados: {duplicados_eliminados:,}")
    print(f"    Filas finales: {len(df_limpio):,}")

    # Paso 10: Verificar tipos finales
    print("\n PASO 10: Verificando tipos finales...")
    for col in df_limpio.columns:
        print(f"    - {col}: {df_limpio[col].dtype}")

    # Paso 11: Escribir parquet
    print("\n💾 PASO 11: Escribiendo archivo Parquet...")
    os.makedirs(INTERIM_DIR, exist_ok=True)
    df_limpio.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"    Guardado en: {OUTPUT_PARQUET}")

    # Paso 12: Escribir CSV también
    print("\n💾 PASO 12: Escribiendo archivo CSV...")
    os.makedirs(INTERIM_DIR, exist_ok=True)
    df_limpio.to_csv(OUTPUT_CSV, index=False)
    print(f"    Guardado en: {OUTPUT_CSV}")

    # Paso 13: Generar reporte Markdown
    print("\n📝 PASO 13: Generando reporte Markdown...")

    # Obtener estadísticas
    anio_min = int(df_limpio['anio'].min()) if not df_limpio['anio'].isna().all() else None
    anio_max = int(df_limpio['anio'].max()) if not df_limpio['anio'].isna().all() else None
    mes_min = int(df_limpio['mes'].min()) if not df_limpio['mes'].isna().all() else None
    mes_max = int(df_limpio['mes'].max()) if not df_limpio['mes'].isna().all() else None

    # Estadísticas de consumo
    consumo_validos = int(df_limpio['consumo_promedio_cliente_kwh'].notna().sum())
    consumo_nulos = int(df_limpio['consumo_promedio_cliente_kwh'].isna().sum())
    if not df_limpio['consumo_promedio_cliente_kwh'].isna().all():
        consumo_min = df_limpio['consumo_promedio_cliente_kwh'].min()
        consumo_max = df_limpio['consumo_promedio_cliente_kwh'].max()
    else:
        consumo_min = None
        consumo_max = None

    # Verificar tipo de fecha
    tipo_fecha = str(df_limpio['fecha'].dtype)
    print(f"    Tipo de 'fecha' en dataset final: {tipo_fecha}")

    report = f"""# 🧹 Limpieza del Dataset Base de Facturación

**Fecha de generación:** 2026-04-08
**Archivo fuente:** `{RAW_FILE}`

## 📊 Resumen de Limpieza

| Métrica | Valor |
|---------|-------|
| Filas originales | {len(df):,} |
| Filas finales | {len(df_limpio):,} |
| Duplicados exactos detectados | {dup_exactos:,} |
| Duplicados eliminados | {duplicados_eliminados:,} |
| Nulos totales (antes) | {total_nulos:,} |

## 📈 Distribución de Nulos por Columna

| Columna | Nulos | Porcentaje |
|---------|-------|-----------|
"""

    for col in df_limpio.columns:
        nulo = int(df_limpio[col].isna().sum())
        pct = (nulo / len(df_limpio)) * 100 if len(df_limpio) > 0 else 0
        report += f"| {col} | {nulo:,} | {pct:.2f}% |\n"

    report += f"""
## 📅 Información Temporal

- **Columna anio:** {anio_min}-{anio_max}
- **Columna mes:** {mes_min}-{mes_max}
- **Columna fecha:** {tipo_fecha} (datetime, formato YYYY-MM-01)
- **Fechas únicas:** {len(df_limpio['fecha'].unique())} valores

## 📑 Tipos Finales de Columna

| Columna | Tipo | Descripción |
|---------|------|------------|
"""

    for col in df_limpio.columns:
        dtype = str(df_limpio[col].dtype)
        desc = get_descripcion_columna(col)
        report += f"| {col} | {dtype} | {desc} |\n"

    report += f"""
## 📊 Estadísticas del Consumo Promedio

| Métrica | Valor |
|---------|-------|
| Filas con valor válido | {consumo_validos:,} |
| Filas con NaN (correcto) | {consumo_nulos:,} |
| Valor mínimo | {consumo_min:.2f} |
| Valor máximo | {consumo_max:.2f} |

**Nota:** `consumo_promedio_cliente_kwh` tiene `NaN` (no ceros) cuando `clientes_facturados` es nulo, cero o `energia_kwh` no numérico.

## 📁 Archivos Generados

1. **Parquet:** `{OUTPUT_PARQUET}`
2. **CSV:** `{OUTPUT_CSV}`
3. **Reporte:** `reports/facturacion_clean_summary.md`
"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"    Reporte guardado en: {REPORT_FILE}")

    # Paso 14: Verificar parquet con pandas
    print("\n PASO 14: Verificando que el Parquet se puede leer correctamente...")
    try:
        df_verify = pd.read_parquet(OUTPUT_PARQUET)
        print(f"    Parquet leído correctamente")
        print(f"    Filas leídas: {len(df_verify):,}")
        print(f"    Columnas: {list(df_verify.columns)}")
        print(f"    Tipos: {df_verify.dtypes.to_dict()}")

        # Verificar tipo de fecha
        print(f"\n    Tipo de 'fecha': {df_verify['fecha'].dtype}")

        # Verificar nulos en consumo_promedio
        nulos_consumo_verify = int(df_verify['consumo_promedio_cliente_kwh'].isna().sum())
        print(f"    Nulos en 'consumo_promedio_cliente_kwh': {nulos_consumo_verify:,}")

        # Verificar ceros (valores válidos - bloques pueden tener 0 consumo)
        ceros = int((df_verify['consumo_promedio_cliente_kwh'] == 0).sum())
        print(f"    Ceros (valores válidos) en 'consumo_promedio_cliente_kwh': {ceros:,}")

        # Total con valor (no NaN)
        total_val = int(df_verify['consumo_promedio_cliente_kwh'].notna().sum())
        print(f"    Total con valor (incluyendo 0) en 'consumo_promedio_cliente_kwh': {total_val:,}")

    except Exception as e:
        print(f"    ERROR: ERROR leyendo parquet: {e}")
        return

    # Resumen final
    print("\n" + "=" * 70)
    print("PROCESO DE LIMPIEZA COMPLETADO")
    print("=" * 70)
    print(f"\n📊 Dataset final: {len(df_limpio):,} filas, {len(df_limpio.columns)} columnas")
    print(f"\n📁 Archivos creados:")
    print(f"   1. {OUTPUT_PARQUET}")
    print(f"   2. {OUTPUT_CSV}")
    print(f"   3. {REPORT_FILE}")
    print(f"\n📑 Columnas finales:")
    for col in df_limpio.columns:
        print(f"    - {col}")
    print(f"\n Resumen:")
    print(f"    - Archivo fuente: {RAW_FILE}")
    print(f"    - Filas originales: {len(df):,}")
    print(f"    - Filas finales: {len(df_limpio):,}")
    print(f"    - Duplicados eliminados: {duplicados_eliminados:,}")
    print(f"    - Nulos en consumo_promedio_cliente_kwh: {int(df_limpio['consumo_promedio_cliente_kwh'].isna().sum()):,}")
    print(f"    - Tipo de 'fecha': {df_limpio['fecha'].dtype}")


def get_descripcion_columna(col):
    """Devuelve descripción para una columna."""
    descripciones = {
        'anio': 'Año del dato (ej: 2015)',
        'mes': 'Mes del año (1-12)',
        'region': 'Región de Chile',
        'comuna': 'Comuna dentro de la región',
        'tipo_clientes': 'Tipo de cliente (Residencial, Comercial, Industrial)',
        'tarifa': 'Tarifa aplicada en pesos (string categórica)',
        'clientes_facturados': 'Cantidad de clientes facturados',
        'e1_kwh': 'Consumo en bloque e1 (kWh)',
        'e2_kwh': 'Consumo en bloque e2 (kWh)',
        'energia_kwh': 'Consumo total de energía (kWh)',
        'fecha': 'Fecha datetime mensual (YYYY-MM-01)',
        'consumo_promedio_cliente_kwh': 'Consumo promedio por cliente (kWh, NaN si inválido)'
    }
    return descripciones.get(col, 'Variable no especificada')


if __name__ == "__main__":
    main()
