# src/01_inventario_datasets.py
# Inventario de datasets para el proyecto de predicción de energía eléctrica

import os
import csv
from datetime import datetime

# Configuración de rutas
RAW_DIR = "data/raw"
REPORTS_DIR = "reports"

def leer_csv_seguro(ruta, max_filas=1000):
    """Lee un CSV de forma segura, manejando archivos grandes."""
    try:
        with open(ruta, 'rb') as f:
            sample = f.read(1024)
            # Detectar separador
            if b';' in sample:
                sep = ';'
            else:
                sep = ','
        with open(ruta, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter=sep)
            filas = list(reader)[:max_filas]
        return filas, sep
    except Exception as e:
        return [], ','

def obtener_estadisticas(ruta):
    """Obtiene estadísticas del archivo."""
    estadisticas = {
        "nombre_archivo": os.path.basename(ruta),
        "tamano_bytes": 0,
        "tamano_mb": 0,
        "filas_totales": 0,
        "filas_muestreo": 0,
        "columnas": [],
        "num_columnas": 0
    }

    if not os.path.exists(ruta):
        return estadisticas, "Archivo no encontrado"

    try:
        estadisticas["tamano_bytes"] = os.path.getsize(ruta)
        estadisticas["tamano_mb"] = round(estadisticas["tamano_bytes"] / (1024 * 1024), 2)

        # Detectar separador
        with open(ruta, 'rb') as f:
            sample = f.read(1024)
            sep = ';' if b';' in sample else ','

        # Leer primeras filas
        filas, _ = leer_csv_seguro(ruta, max_filas=1000)
        if filas:
            encabezados = filas[0]
            estadisticas["columnas"] = list(encabezados)
            estadisticas["num_columnas"] = len(encabezados)
            estadisticas["filas_muestreo"] = len(filas)

        # Contar filas aproximadas leyendo todo el archivo
        try:
            with open(ruta, 'r', encoding='utf-8', errors='replace') as f:
                filas_completas = sum(1 for _ in f)
                estadisticas["filas_totales"] = filas_completas
        except:
            # Fallback si falla
            estadisticas["filas_totales"] = len(filas)

    except Exception as e:
        estadisticas["errores"] = str(e)

    return estadisticas, None

def inferir_frecuencia(estadisticas, nombre_archivo):
    """Infere la frecuencia temporal del dataset."""
    nombre = nombre_archivo.lower()
    rango = estadisticas.get("rango_fechas", "")

    if "diaria" in rango.lower() or "dia" in rango.lower() or estadisticas.get("filas_totales", 0) > 1000:
        return "diaria"
    elif "mensual" in rango.lower() or "2019" in rango.lower():
        return "mensual"
    elif "2009" in rango.lower() and "2013" in rango.lower():
        return "anual"
    elif estadisticas.get("filas_totales", 0) < 100:
        return "anual"
    else:
        return "diaria"

def obtener_claves_union(estadisticas):
    """Identifica posibles claves de unión."""
    claves = []
    for col in estadisticas.get("columnas", []):
        col_lower = col.lower()
        if any(x in col_lower for x in ['id', 'num', 'codigo', 'key']):
            claves.append(col)
        elif col_lower in ['fecha', 'anio', 'mes', 'region', 'comuna', 'sistema', 'tipo', 'tipo_clientes']:
            claves.append(col)
    return claves

def evaluar_utilidad(estadisticas, nombre_archivo):
    """Evalúa si un dataset sirve para predicción de consumo mensual."""
    nombre = nombre_archivo.lower()

    # Facturación: SÍ, son la base principal de predicción
    if "facturacion" in nombre:
        return True, "Contiene mediciones de energía (kWh) de clientes regulados por región, comuna y tipo de cliente"

    # Demanda diaria: útil para features temporales
    if "demanda_diaria" in nombre:
        return True, "Proporciona demanda diaria, útil para features temporales de alta frecuencia"

    # Balance/regional: datos contextuales
    if "balance" in nombre or "generacion" in nombre or "regional" in nombre:
        return True, "Datos de balance regional de capacidad y demanda para features contextuales"

    # Demanda máxima sobre capacidad: útil para features
    if "demanda_máx" in nombre:
        return True, "Demanda máxima sobre capacidad instalada, útil para features de capacidad"

    # Programación de red
    if "dx" in nombre or "gx" in nombre or "programada" in nombre:
        return True, "Datos de programación de red para features de infraestructura"

    return False, "No cumple criterios principales para predicción de consumo"

def generar_reporte():
    """Genera el reporte de inventario completo."""
    archivos = [
        "se_balance_energia_regional(in).csv",
        "se_demanda_diaria(in).csv",
        "se_demanda_máx_sobre_cap_instalada_anuario_2019(Hoja2).csv",
        "se_dx_programada(in).csv",
        "se_facturacion_clientes_regulados(in).csv",
        "se_facturacion_clientes_regulados(in)(1).csv",
        "se_gx_programada_fuente(in).csv"
    ]

    resultados = []
    print("\n" + "="*60)
    print(" ANALIZANDO DATASETS")
    print("="*60)

    for archivo in archivos:
        ruta = os.path.join(RAW_DIR, archivo)
        print(f"\n📄 Analizando: {archivo}")
        estadisticas, _ = obtener_estadisticas(ruta)

        if _ is not None:
            print(f"  Aviso: Error: {_}")
        else:
            print(f"  Tamano: {estadisticas['tamano_mb']} MB")
            print(f"  Filas: {estadisticas['filas_totales']}")
            print(f"  Columnas: {estadisticas['num_columnas']}")

            # Inferir frecuencia
            frecuencia = inferir_frecuencia(estadisticas, archivo)
            estadisticas["frecuencia_temporal"] = frecuencia
            print(f"  Frecuencia: {frecuencia}")

            # Claves
            claves = obtener_claves_union(estadisticas)
            estadisticas["claves_union"] = claves

            # Evaluar utilidad
            sirve, justificacion = evaluar_utilidad(estadisticas, archivo)
            estadisticas["sirve_predicion"] = sirve
            estadisticas["justificacion"] = justificacion[:100]
            print(f"  Sirve: {'SÍ' if sirve else 'NO'}")

        resultados.append(estadisticas)

    # Comparar archivos de facturacion
    print("\n" + "="*60)
    print(" COMPARACIÓN DE ARCHIVOS DE FACTURACIÓN")
    print("="*60)

    r1 = resultados[4]
    r2 = resultados[5]

    print(f"\nArchivo 1: {r1['nombre_archivo']}")
    print(f"  - Filas: {r1['filas_totales']}")
    print(f"  - Columnas: {r1['num_columnas']}")
    print(f"  - Tamaño: {r1['tamano_bytes']} bytes")

    print(f"\nArchivo 2: {r2['nombre_archivo']}")
    print(f"  - Filas: {r2['filas_totales']}")
    print(f"  - Columnas: {r2['num_columnas']}")
    print(f"  - Tamaño: {r2['tamano_bytes']} bytes")

    print(f"\n¿Son idénticos? ", end="")
    if r1['filas_totales'] == r2['filas_totales'] and \
       r1['num_columnas'] == r2['num_columnas'] and \
       r1['tamano_bytes'] == r2['tamano_bytes']:
        print("SÍ, tienen el mismo contenido y tamaño.")
    else:
        print("ERROR: NO, tienen diferencias detectadas.")

    # Identificar diferencia en nombres
    if r1['nombre_archivo'] == r2['nombre_archivo']:
        print("Aviso:  Los archivos tienen el mismo nombre (posible duplicado).")
    elif r1['nombre_archivo'].replace('(1)', '') == r2['nombre_archivo'].replace('(1)', ''):
        print("Aviso:  Los archivos tienen nombres similares (probable duplicado o versión).")

    return resultados

def generar_markdown(resultados):
    """Genera el reporte en Markdown."""
    lines = []
    lines.append("# 📊 Inventario de Datasets - proyecto_DS")
    lines.append(f"\n**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Directorio fuente:** `data/raw/`")
    lines.append(f"**Total de datasets:** {len(resultados)}")
    lines.append("")

    # Resumen ejecutivo
    lines.append("## 🎯 Resumen Ejecutivo")
    lines.append("")
    lines.append("| Dataset | Sirve para predicción | Justificación |")
    lines.append("|---------|----------------------|---------------|")

    for r in resultados:
        nombre = r.get("nombre_archivo", "N/A")
        sirve = "SÍ" if r.get("sirve_predicion", False) else "ERROR: NO"
        justificacion = r.get("justificacion", "N/A")
        justificacion = justificacion.replace('\n', ' ').strip()
        if len(justificacion) > 70:
            justificacion = justificacion[:67] + "..."
        lines.append(f"| {nombre} | {sirve} | {justificacion} |")

    lines.append("")

    # Comparación de archivos
    lines.append("##  Comparación: Archivos de Facturación")
    lines.append("")

    r1 = resultados[4]
    r2 = resultados[5]

    nombre1 = r1.get("nombre_archivo", "")
    nombre2 = r2.get("nombre_archivo", "")
    r1_filas = r1.get("filas_totales", "")
    r2_filas = r2.get("filas_totales", "")
    r1_cols = r1.get("num_columnas", "")
    r2_cols = r2.get("num_columnas", "")
    r1_tamano = r1.get("tamano_bytes", "")
    r2_tamano = r2.get("tamano_bytes", "")

    iguales = (r1_filas == r2_filas and r1_cols == r2_cols and r1_tamano == r2_tamano)

    lines.append(f"| Propiedad | `{nombre1}` | `{nombre2}` | Igualdad |")
    lines.append(f"|-----------|-------------|-------------|----------|")
    lines.append(f"| Filas | {r1_filas} | {r2_filas} | {'SÍ' if iguales else 'ERROR: NO'} |")
    lines.append(f"| Columnas | {r1_cols} | {r2_cols} | {'SÍ' if iguales else 'ERROR: NO'} |")
    lines.append(f"| Tamaño | {r1_tamano} bytes | {r2_tamano} bytes | {'SÍ' if iguales else 'ERROR: NO'} |")
    lines.append("")

    if iguales:
        conclusion = "**Conclusión:** Los archivos son idénticos (probablemente duplicado o backup)."
    else:
        conclusion = "**Conclusión:** Los archivos tienen diferencias. Verificar contenido completo."
    lines.append(conclusion)
    lines.append("")

    # Detalle por dataset
    lines.append("## 📄 Detalle por Dataset")
    lines.append("")

    for r in resultados:
        lines.append(f"### `{r.get('nombre_archivo', 'N/A')}`")
        lines.append("")

        nombre = r.get("nombre_archivo", "N/A")
        tamano_mb = r.get("tamano_mb", "N/A")
        filas = r.get("filas_totales", "N/A")
        num_cols = r.get("num_columnas", "N/A")
        frecuencia = r.get("frecuencia_temporal", "N/A")
        claves = r.get("claves_union", [])
        sirve = "SÍ" if r.get("sirve_predicion", False) else "ERROR: NO"
        justificacion = r.get("justificacion", "N/A")

        lines.append(f"**Tamaño:** `{tamano_mb}` MB")
        lines.append(f"**Filas:** `{filas:,}`")
        lines.append(f"**Columnas:** `{num_cols}`")
        lines.append("")
        lines.append("### Columnas")
        lines.append("")
        for col in r.get("columnas", [])[:15]:
            lines.append(f"- `{col}`")
        if len(r.get("columnas", [])) > 15:
            lines.append(f"- ... y {len(r.get('columnas', [])) - 15} más")
        lines.append("")
        lines.append("### Información Temporal")
        lines.append("")
        lines.append(f"- **Frecuencia:** `{frecuencia}`")
        lines.append("")
        lines.append("### Claves de Unión")
        lines.append("")
        if claves:
            for clave in claves:
                lines.append(f"- `{clave}`")
        else:
            lines.append("- Sin claves identificadas")
        lines.append("")
        lines.append("### Evaluación para Predicción de Consumo Mensual")
        lines.append("")
        lines.append(f"| Criterio | Valor |")
        lines.append("|----------|-------|")
        lines.append(f"| Sirve para predicción | `{sirve}` |")
        lines.append(f"| Justificación | `{justificacion}` |")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

def generar_csv(resultados):
    """Genera las filas CSV para el reporte."""
    import io

    # Usar csv.writer para formateo correcto
    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados
    headers = [
        "nombre_archivo", "tamano_bytes", "tamano_mb", "columnas", "num_columnas",
        "cantidad_filas", "frecuencia_temporal", "claves_union", "sirve_predicion",
        "justificacion"
    ]
    writer.writerow(headers)

    # Filas de datos
    for r in resultados:
        try:
            nombre = r.get("nombre_archivo", "")
            tamano_bytes = str(r.get("tamano_bytes", ""))
            tamano_mb = str(r.get("tamano_mb", ""))
            columnas = r.get("columnas", [])
            num_columnas = str(r.get("num_columnas", ""))
            cantidad_filas = str(r.get("filas_totales", ""))
            claves = "; ".join(r.get("claves_union", []))
            sirve = "si" if r.get("sirve_predicion", False) else "no"
            justificacion = r.get("justificacion", "")
            # Truncar nombre de columna si es muy largo
            columnas_limpio = [c[:50] for c in columnas[:10]]  # Max 10 columnas, max 50 chars
        except:
            nombre = ""
            tamano_bytes = ""
            tamano_mb = ""
            columnas_limpio = []
            num_columnas = ""
            cantidad_filas = ""
            claves = ""
            sirve = "no"
            justificacion = ""

        writer.writerow([
            nombre, tamano_bytes, tamano_mb,
            ",".join(columnas_limpio), num_columnas,
            cantidad_filas, r.get("frecuencia_temporal", ""),
            claves, sirve, justificacion
        ])

    return output.getvalue()

def main():
    """Función principal para generar el inventario."""
    print(" Generando inventario de datasets...")
    print("="*60)

    # Generar reporte
    resultados = generar_reporte()

    if resultados:
        # Generar contenido Markdown
        md_content = generar_markdown(resultados)
        md_path = os.path.join(REPORTS_DIR, "dataset_inventory.md")

        # Escribir Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"\nGuardado: {md_path}")

        # Generar contenido CSV
        csv_content = generar_csv(resultados)
        csv_path = os.path.join(REPORTS_DIR, "dataset_inventory.csv")

        # Escribir CSV
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)
        print(f"Guardado: {csv_path}")

        print("\n" + "="*60)
        print("INVENTARIO GENERADO")
        print("="*60)
        print("\n📁 Archivos generados:")
        print(f"  1. src/01_inventario_datasets.py (script)")
        print(f"  2. reports/dataset_inventory.md (reporte Markdown)")
        print(f"  3. reports/dataset_inventory.csv (exportación CSV)")

if __name__ == "__main__":
    main()
