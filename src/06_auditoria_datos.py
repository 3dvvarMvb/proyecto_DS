"""
Auditoría exhaustiva de contratos de datos.

Inputs (no se modifican):
  - data/raw/*.csv
  - data/interim/facturacion_clean.parquet
  - data/processed/modeling_energia_kwh.parquet
  - data/processed/modeling_consumo_promedio.parquet
  - data/processed/modeling_con_auxiliares.parquet

Output:
  - reports/auditoria_datos.md (con secciones OK/Warning/Error por dataset)

El script no modifica archivos; registra errores tal cual si una validación falla.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim" / "facturacion_clean.parquet"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "auditoria_datos.md"

LAG_SUFFIXES = ("_L1", "_L2", "_L3")

# Auxiliares previamente documentadas en reports/integracion_auxiliares_summary.md
DOCUMENTED_AUX_LAGS = [
    "demanda_promedio_mes_sen_L1", "demanda_promedio_mes_sen_L2", "demanda_promedio_mes_sen_L3",
    "demanda_maxima_mes_sen_L1", "demanda_maxima_mes_sen_L2", "demanda_maxima_mes_sen_L3",
    "rango_demanda_mes_sen_L1", "rango_demanda_mes_sen_L2", "rango_demanda_mes_sen_L3",
    "total_hidro_mes_L1", "total_hidro_mes_L2", "total_hidro_mes_L3",
    "total_ernc_mes_L1", "total_ernc_mes_L2", "total_ernc_mes_L3",
    "proporcion_ernc_mes_L1", "proporcion_ernc_mes_L2", "proporcion_ernc_mes_L3",
    "proporcion_hidro_mes_L1", "proporcion_hidro_mes_L2", "proporcion_hidro_mes_L3",
    "total_generacion_mes_L1", "total_generacion_mes_L2", "total_generacion_mes_L3",
]


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def kind(name: str) -> str:
    return name


def section(title: str) -> str:
    return f"\n## {title}\n\n"


def status(level: str, msg: str) -> str:
    return f"- **{level}** — {msg}\n"


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def df_to_md(df: pd.DataFrame) -> str:
    """Minimal markdown table without tabulate."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |"]
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        vals = []
        for v in row:
            if isinstance(v, float):
                vals.append(f"{v:,.2f}".replace(",", " "))
            elif isinstance(v, (int,)):
                vals.append(f"{v:,}".replace(",", " "))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def audit_raw() -> list[str]:
    out: list[str] = []
    files = sorted(RAW_DIR.glob("*.csv"))
    out.append(f"Archivos raw: {len(files)}\n")
    out.append("\n| archivo | bytes | md5 (8 hex) |\n|---|---:|---|\n")
    md5_map: dict[str, list[str]] = {}
    for f in files:
        h = md5(f)
        md5_map.setdefault(h, []).append(f.name)
        out.append(f"| {f.name} | {fmt_int(f.stat().st_size)} | `{h[:8]}` |\n")
    out.append("\n### Hallazgos raw\n")
    dups = [(h, names) for h, names in md5_map.items() if len(names) > 1]
    if dups:
        for h, names in dups:
            out.append(status("WARNING", f"Duplicado byte-a-byte md5 `{h[:8]}`: {', '.join(names)}"))
    else:
        out.append(status("OK", "No hay archivos raw byte-idénticos"))

    # Sample columns and separators
    out.append("\n### Encabezados (separador detectado)\n\n")
    for f in files:
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                head = fh.readline().rstrip("\n")
            sep = ";" if head.count(";") >= head.count(",") else ","
            out.append(f"- `{f.name}` (sep=`{sep}`): `{head[:160]}`\n")
        except Exception as exc:
            out.append(status("ERROR", f"No se pudo leer {f.name}: {exc!r}"))
    return out


def audit_interim() -> list[str]:
    out: list[str] = []
    if not INTERIM.exists():
        return [status("ERROR", f"No existe {INTERIM}")]
    df = pd.read_parquet(INTERIM)
    out.append(f"Shape: {df.shape[0]:,} filas × {df.shape[1]} columnas\n".replace(",", " "))
    out.append(f"\nColumnas: `{list(df.columns)}`\n")
    out.append("\n**Tipos**:\n\n")
    for c, t in df.dtypes.items():
        out.append(f"- `{c}`: {t}\n")
    out.append(f"\nRango fechas: {df['fecha'].min().date()} → {df['fecha'].max().date()}, meses únicos: {df['fecha'].nunique()}\n")
    out.append(f"\nRegiones: {df['region'].nunique()}, comunas: {df['comuna'].nunique()}, tarifas: {df['tarifa'].nunique()}, tipos cliente: {sorted(df['tipo_clientes'].unique())}\n")

    nulls = df.isna().sum()
    out.append("\n**Nulos por columna**:\n\n")
    for c, v in nulls.items():
        if v:
            out.append(f"- `{c}`: {fmt_int(v)}\n")
    if (nulls == 0).all():
        out.append("- (sin nulos)\n")

    # Dups
    key_cols = ["fecha", "region", "comuna", "tipo_clientes", "tarifa"]
    dups = df.duplicated(subset=key_cols).sum()
    out.append(f"\nDuplicados sobre `{key_cols}`: {fmt_int(dups)}\n")

    # energia_kwh anomalies
    neg = int((df["energia_kwh"] < 0).sum())
    zero = int((df["energia_kwh"] == 0).sum())
    pos = int((df["energia_kwh"] > 0).sum())
    out.append(f"\n`energia_kwh`: positivos={fmt_int(pos)}, ceros={fmt_int(zero)}, negativos={fmt_int(neg)}\n")
    out.append(f"\n`energia_kwh` describe:\n```\n{df['energia_kwh'].describe()}\n```\n")

    # Top extreme
    out.append("\n**Top 5 mayores `energia_kwh`**:\n\n")
    top = df.nlargest(5, "energia_kwh")[key_cols + ["clientes_facturados", "energia_kwh"]]
    out.append(top.pipe(df_to_md) + "\n")
    out.append("\n**Top 5 menores `energia_kwh` (más negativos)**:\n\n")
    bot = df.nsmallest(5, "energia_kwh")[key_cols + ["clientes_facturados", "energia_kwh"]]
    out.append(bot.pipe(df_to_md) + "\n")

    # Consistency e1+e2 vs energia_kwh
    mask = df[["e1_kwh", "e2_kwh"]].notna().all(axis=1)
    if mask.any():
        diff = df.loc[mask, "energia_kwh"] - (df.loc[mask, "e1_kwh"] + df.loc[mask, "e2_kwh"])
        match = (diff.abs() < 1).sum()
        total = mask.sum()
        out.append(f"\nConsistencia `energia_kwh ≈ e1 + e2` (filas con e1 y e2 no nulos): {fmt_int(match)} / {fmt_int(total)} cuadran (tolerancia |Δ|<1).\n")
        out.append(f"Δ describe:\n```\n{diff.describe()}\n```\n")

    # clientes_facturados
    cf_neg = int((df["clientes_facturados"] <= 0).sum())
    cf_null = int(df["clientes_facturados"].isna().sum())
    out.append(f"\n`clientes_facturados`: nulos={cf_null}, ≤0={cf_neg}\n")

    # status
    out.append("\n### Hallazgos interim\n")
    out.append(status("OK" if dups == 0 else "WARNING", f"{fmt_int(dups)} duplicados sobre clave panel"))
    out.append(status("WARNING" if neg or zero else "OK", f"`energia_kwh` con {fmt_int(neg)} negativos y {fmt_int(zero)} ceros (calidad pendiente)"))
    out.append(status("WARNING" if cf_null else "OK", f"`clientes_facturados` con {cf_null} nulo(s)"))
    return out


def audit_processed_simple(path: Path, expected_target: str) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return [status("ERROR", f"No existe {path}")]
    df = pd.read_parquet(path)
    out.append(f"Shape: {df.shape[0]:,} × {df.shape[1]}\n".replace(",", " "))
    out.append(f"\nColumnas: `{list(df.columns)}`\n")
    if "fecha" in df.columns:
        f = pd.to_datetime(df["fecha"])
        out.append(f"\nRango fechas: {f.min().date()} → {f.max().date()}, meses únicos: {f.nunique()}\n")
    nulls = df.isna().sum()
    null_lines = [f"- `{c}`: {fmt_int(v)}\n" for c, v in nulls.items() if v]
    if null_lines:
        out.append("\n**Nulos**:\n\n")
        out.extend(null_lines)
    if expected_target in df.columns:
        out.append(f"\nTarget `{expected_target}` describe:\n```\n{df[expected_target].describe()}\n```\n")
    else:
        out.append(status("ERROR", f"Falta target esperado `{expected_target}`"))
    return out


def audit_aux() -> list[str]:
    out: list[str] = []
    path = PROC / "modeling_con_auxiliares.parquet"
    if not path.exists():
        return [status("ERROR", f"No existe {path}")]
    df = pd.read_parquet(path)
    out.append(f"Shape: {df.shape[0]:,} × {df.shape[1]}\n".replace(",", " "))
    out.append(f"\nColumnas: `{list(df.columns)}`\n")
    f = pd.to_datetime(df["fecha"])
    out.append(f"\nRango: {f.min().date()} → {f.max().date()}, meses únicos: {f.nunique()}\n")

    lag_cols = [c for c in df.columns if c.endswith(LAG_SUFFIXES)]
    out.append(f"\nColumnas lag detectadas ({len(lag_cols)}): `{lag_cols}`\n")

    # Same-month aux columns (non-lag aux)
    aux_root_keywords = ("demanda_promedio_mes_sen", "demanda_maxima_mes_sen", "rango_demanda_mes_sen",
                        "total_hidro_mes", "total_ernc_mes", "proporcion_ernc_mes",
                        "proporcion_hidro_mes", "total_generacion_mes")
    same_month_aux = [c for c in df.columns if c in aux_root_keywords]  # exact name without lag suffix
    if same_month_aux:
        out.append(status("ERROR", f"Columnas auxiliares del mismo mes detectadas (posible leakage): {same_month_aux}"))
    else:
        out.append(status("OK", "No hay columnas auxiliares del mismo mes (sólo lags)"))

    # Documented but missing
    missing = [c for c in DOCUMENTED_AUX_LAGS if c not in df.columns]
    extra = [c for c in lag_cols if c not in DOCUMENTED_AUX_LAGS]
    if missing:
        out.append(status("ERROR", f"Columnas documentadas en `integracion_auxiliares_summary.md` que **no existen** en el parquet: {missing}"))
    if extra:
        out.append(status("WARNING", f"Columnas lag presentes pero no documentadas previamente: {extra}"))
    if not missing and not extra:
        out.append(status("OK", "Set de lags coincide con la documentación"))

    # Nulos por lag
    nulls = df[lag_cols].isna().sum()
    out.append("\n**Nulos por lag**:\n\n")
    for c, v in nulls.items():
        out.append(f"- `{c}`: {fmt_int(v)}\n")
    n_complete = df.dropna(subset=lag_cols).shape[0]
    out.append(f"\nFilas con todos los lags válidos: {fmt_int(n_complete)} de {fmt_int(len(df))}\n")

    # anio_x / mes_x: posible duplicación de claves del merge
    if "anio_x" in df.columns or "mes_x" in df.columns:
        out.append(status("WARNING", "Columnas `anio_x` / `mes_x` quedaron del merge (no se renombraron a `anio`/`mes`)"))

    return out


def main() -> int:
    lines: list[str] = []
    lines.append("# Auditoría de contratos de datos\n")

    lines.append(section("1. Raw (`data/raw`)"))
    lines.extend(audit_raw())

    lines.append(section("2. Interim — `data/interim/facturacion_clean.parquet`"))
    lines.extend(audit_interim())

    lines.append(section("3. Processed — `modeling_energia_kwh.parquet`"))
    lines.extend(audit_processed_simple(PROC / "modeling_energia_kwh.parquet", "energia_kwh"))

    lines.append(section("4. Processed — `modeling_consumo_promedio.parquet`"))
    lines.extend(audit_processed_simple(PROC / "modeling_consumo_promedio.parquet", "consumo_promedio_cliente_kwh"))

    lines.append(section("5. Processed — `modeling_con_auxiliares.parquet`"))
    lines.extend(audit_aux())

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"OK - {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
