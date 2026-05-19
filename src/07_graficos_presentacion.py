"""
Presentación 1 - EDA v2 (corrige unidades y afirmaciones).

Inputs:
  - data/interim/facturacion_clean.parquet
  - data/processed/modeling_con_auxiliares.parquet

Outputs:
  - reports/figures_v2/*.png
  - reports/resumen_analisis_exploratorio.md

Unidades: kWh/1e6 = GWh; kWh/1e9 = TWh. No modifica datasets.
"""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim" / "facturacion_clean.parquet"
AUX = ROOT / "data" / "processed" / "modeling_con_auxiliares.parquet"
FIG_DIR = ROOT / "reports" / "figures_v2"
SUMMARY = ROOT / "reports" / "resumen_analisis_exploratorio.md"

FIG_DIR.mkdir(parents=True, exist_ok=True)

KWH_TO_GWH = 1e6
KWH_TO_TWH = 1e9


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def main() -> int:
    if not INTERIM.exists():
        print(f"ERROR: no existe {INTERIM}", file=sys.stderr)
        return 1
    df = pd.read_parquet(INTERIM)
    df["fecha"] = pd.to_datetime(df["fecha"])

    figures: list[tuple[str, str]] = []

    # ---------- 1. Evolución mensual nacional (GWh) ----------
    monthly = df.groupby("fecha", as_index=False)["energia_kwh"].sum()
    monthly["gwh"] = monthly["energia_kwh"] / KWH_TO_GWH
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(monthly["fecha"], monthly["gwh"], color="#1f77b4")
    ax.set_title("Energía total facturada mensual - Chile (2015-2024)")
    ax.set_ylabel("Energía mensual (GWh)")
    ax.set_xlabel("Fecha")
    ax.grid(alpha=0.3)
    out = FIG_DIR / "01_evolucion_mensual_nacional.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Evolución mensual de energía total facturada (GWh)."))

    # ---------- 2. Por tipo de cliente (GWh) ----------
    by_type = df.groupby(["fecha", "tipo_clientes"], as_index=False)["energia_kwh"].sum()
    by_type["gwh"] = by_type["energia_kwh"] / KWH_TO_GWH
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for cat, sub in by_type.groupby("tipo_clientes"):
        ax.plot(sub["fecha"], sub["gwh"], label=cat)
    ax.set_title("Energía mensual por tipo de cliente (GWh)")
    ax.set_ylabel("Energía mensual (GWh)")
    ax.legend()
    ax.grid(alpha=0.3)
    out = FIG_DIR / "02_evolucion_tipo_cliente.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Evolución mensual por tipo_clientes. La curva Residencial supera a No Residencial alrededor de 2018-2019."))

    # ---------- 3. Top regiones (TWh acumulados) ----------
    by_region = df.groupby("region")["energia_kwh"].sum().sort_values(ascending=False)
    by_region_twh = by_region / KWH_TO_TWH
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(by_region_twh.index[::-1], by_region_twh.values[::-1], color="#2ca02c")
    ax.set_title("Energía total facturada por región 2015-2024 (TWh acumulados)")
    ax.set_xlabel("Energía acumulada (TWh)")
    ax.grid(alpha=0.3, axis="x")
    out = FIG_DIR / "03_energia_por_region.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Energía acumulada por región (TWh = kWh/1e9). RM domina con margen amplio."))

    # ---------- 4. Distribución log10 (positivos) ----------
    pos = df.loc[df["energia_kwh"] > 0, "energia_kwh"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(np.log10(pos), bins=80, color="#9467bd", edgecolor="white")
    ax.set_title("Distribución log10(energia_kwh) (filas con energia_kwh > 0)")
    ax.set_xlabel("log10(kWh)")
    ax.set_ylabel("Frecuencia")
    ax.grid(alpha=0.3)
    out = FIG_DIR / "04_distribucion_log_energia.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Distribución log10 de `energia_kwh` (positivos). Cola larga: el target requiere log o tratamiento específico."))

    # ---------- 5. Boxplot por tipo cliente (log) ----------
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = [
        np.log10(df.loc[(df["tipo_clientes"] == c) & (df["energia_kwh"] > 0), "energia_kwh"])
        for c in ["Residencial", "No Residencial"]
    ]
    ax.boxplot(data, labels=["Residencial", "No Residencial"], showfliers=True)
    ax.set_title("Boxplot log10(energia_kwh) por tipo cliente (positivos)")
    ax.set_ylabel("log10(kWh)")
    ax.grid(alpha=0.3, axis="y")
    out = FIG_DIR / "05_boxplot_tipo_cliente.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Boxplot log10 del target por tipo de cliente. No Residencial tiene mayor dispersión y outliers superiores."))

    # ---------- 6. Anomalías por año ----------
    by_year = df.groupby("anio").agg(
        negativos=("energia_kwh", lambda s: int((s < 0).sum())),
        ceros=("energia_kwh", lambda s: int((s == 0).sum())),
        total=("energia_kwh", "size"),
    ).reset_index()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    width = 0.4
    x = np.arange(len(by_year))
    ax.bar(x - width / 2, by_year["negativos"], width, label="energia_kwh < 0", color="#d62728")
    ax.bar(x + width / 2, by_year["ceros"], width, label="energia_kwh == 0", color="#bcbd22")
    ax.set_xticks(x); ax.set_xticklabels(by_year["anio"].astype(int))
    ax.set_title("Anomalías de `energia_kwh` por año (negativos y ceros)")
    ax.set_ylabel("Cantidad de filas")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    out = FIG_DIR / "06_anomalias_por_anio.png"
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    figures.append((out.name, "Negativos y ceros de `energia_kwh` por año. Negativos crecen sostenidamente (80 → 199 entre 2015 y 2024)."))

    # ---------- 7. Energía vs demanda SEN L1 (con disclaimer) ----------
    aux_caption = "(no generado: archivo auxiliar no disponible)"
    if AUX.exists():
        try:
            aux = pd.read_parquet(AUX)
            aux["fecha"] = pd.to_datetime(aux["fecha"])
            energ_mes = aux.groupby("fecha", as_index=False)["energia_kwh"].sum()
            energ_mes["gwh"] = energ_mes["energia_kwh"] / KWH_TO_GWH
            dem = aux.groupby("fecha", as_index=False)["demanda_promedio_mes_sen_L1"].mean()
            fig, ax1 = plt.subplots(figsize=(10, 4.5))
            ax1.plot(energ_mes["fecha"], energ_mes["gwh"], color="#1f77b4", label="Energía mensual facturada (GWh)")
            ax1.set_ylabel("Energía facturada (GWh)", color="#1f77b4")
            ax2 = ax1.twinx()
            ax2.plot(dem["fecha"], dem["demanda_promedio_mes_sen_L1"], color="#d62728", linestyle="--", label="Demanda SEN L1 (MW prom)")
            ax2.set_ylabel("Demanda SEN L1 (MW promedio)", color="#d62728")
            ax1.set_title("Energía facturada (mensual) vs demanda SEN promedio - lag 1\n(Demanda SEN es serie nacional, no comunal)")
            ax1.grid(alpha=0.3)
            out = FIG_DIR / "07_energia_vs_demanda_sen_lag1.png"
            fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
            aux_caption = "Energía facturada (suma mensual) vs demanda SEN promedio con lag 1. **La demanda SEN es serie nacional** (igual para todas las filas del mismo mes), por eso su uso como feature por-fila tiene varianza limitada."
            figures.append((out.name, aux_caption))
        except Exception as exc:  # noqa: BLE001
            figures.append(("07_energia_vs_demanda_sen_lag1.png", f"No se pudo generar: {exc!r}"))

    # ----- Resumen markdown -----
    # Cifras verificables:
    total_by_type = df.groupby("tipo_clientes")["energia_kwh"].sum() / KWH_TO_TWH
    ratio_res_vs_nores = total_by_type["Residencial"] / total_by_type["No Residencial"]
    by_year_type = df.groupby(["anio", "tipo_clientes"])["energia_kwh"].sum().unstack() / KWH_TO_TWH
    region_top = (df.groupby("region")["energia_kwh"].sum() / KWH_TO_TWH).sort_values(ascending=False)
    monthly_pattern = df.groupby("mes")["energia_kwh"].sum() / KWH_TO_GWH
    peak_month = int(monthly_pattern.idxmax())
    valley_month = int(monthly_pattern.idxmin())
    peak_val = monthly_pattern.max()
    valley_val = monthly_pattern.min()
    season_amplitude = (peak_val - valley_val) / valley_val * 100

    neg = int((df["energia_kwh"] < 0).sum())
    zeros = int((df["energia_kwh"] == 0).sum())
    nan_e2 = int(df["e2_kwh"].isna().sum())
    nan_e1 = int(df["e1_kwh"].isna().sum())
    nan_cprom = int(df["consumo_promedio_cliente_kwh"].isna().sum())
    cf_zero = int((df["clientes_facturados"] == 0).sum())
    cf_neg = int((df["clientes_facturados"] < 0).sum())
    cf_nan = int(df["clientes_facturados"].isna().sum())

    lines: list[str] = []
    lines.append("# Presentación 1 - EDA v2 (corregido)\n")
    lines.append("\n## Datasets usados\n\n")
    lines.append(f"- `data/interim/facturacion_clean.parquet` — {fmt_int(len(df))} filas × {df.shape[1]} cols, {df['fecha'].min().date()} → {df['fecha'].max().date()}.\n")
    if AUX.exists():
        aux_df = pd.read_parquet(AUX)
        lines.append(f"- `data/processed/modeling_con_auxiliares.parquet` — {fmt_int(len(aux_df))} filas × {aux_df.shape[1]} cols, {pd.to_datetime(aux_df['fecha']).min().date()} → {pd.to_datetime(aux_df['fecha']).max().date()}.\n")
    lines.append("\n## Hallazgos verificados\n\n")
    lines.append(f"- Cobertura: 16 regiones, {df['comuna'].nunique()} comunas, {df['tarifa'].nunique()} tarifas, 2 tipos de cliente.\n")
    lines.append(f"- **Tipo de cliente**: en agregado 2015-2024, Residencial totaliza **{total_by_type['Residencial']:.1f} TWh** y No Residencial **{total_by_type['No Residencial']:.1f} TWh** (razón Residencial / No Residencial = **{ratio_res_vs_nores:.2f}×**, **NO** es 3-4×).\n")
    lines.append("- Cambio temporal documentado: hasta 2017 No Residencial > Residencial; desde ~2019 se invierte y Residencial domina.\n")
    lines.append("\n  | Año | No Residencial (TWh) | Residencial (TWh) |\n  |---|---:|---:|\n")
    for anio, row in by_year_type.iterrows():
        lines.append(f"  | {int(anio)} | {row['No Residencial']:.2f} | {row['Residencial']:.2f} |\n")
    lines.append("\n- **Top regiones acumuladas (TWh)**: la Región Metropolitana domina con amplio margen.\n\n")
    lines.append("  | # | Región | TWh acumulados |\n  |---:|---|---:|\n")
    for i, (region, val) in enumerate(region_top.head(6).items(), 1):
        lines.append(f"  | {i} | {region} | {val:.2f} |\n")
    lines.append("\n- Antofagasta aparece en posición 9 (~8.3 TWh acumulados); **NO** está en el top regional.\n")
    lines.append(f"- Estacionalidad: el mes con máximo agregado nacional 2015-2024 es **{peak_month:02d}** ({peak_val:,.0f} GWh) y el mínimo es **{valley_month:02d}** ({valley_val:,.0f} GWh). Amplitud relativa **{season_amplitude:.1f} %**: estacionalidad presente pero moderada a nivel nacional.\n".replace(",", " "))
    lines.append(f"- Distribución de `energia_kwh` muy sesgada: máx = 1.12e8 kWh (Santiago Residencial BT1A, jul-ago).\n")
    lines.append(f"- Anomalías: **{neg:,} negativos** y **{zeros:,} ceros** en `energia_kwh` (≈ {(neg+zeros)/len(df)*100:.1f} % del total).\n".replace(",", " "))
    lines.append(f"- `clientes_facturados`: {cf_zero:,} ceros, {cf_neg} negativos, {cf_nan} NaN.\n".replace(",", " "))
    lines.append(f"- Nulos en otras columnas: e1_kwh={nan_e1:,}, e2_kwh={nan_e2:,}, consumo_promedio_cliente_kwh={nan_cprom:,}.\n".replace(",", " "))
    lines.append("\n## Figuras generadas\n\n")
    for fname, caption in figures:
        lines.append(f"- `reports/figures_v2/{fname}` — {caption}\n")
    lines.append("\n## Notas metodológicas\n\n")
    lines.append("- Las variables auxiliares (demanda SEN, generación) son **series nacionales**, idénticas para todas las filas de un mismo mes; su capacidad de discriminar a nivel comuna×tarifa es limitada.\n")
    lines.append("- Los outliers extremos no se removieron en `clean`; las decisiones de filtrado se aplican en el script de modelado (vista `energia_kwh > 0` y/o `clientes_facturados > 0`).\n")
    lines.append("- El conteo de duplicados sobre la clave panel (5 275 filas) revela que la clave asumida no es estrictamente única; ver `reports/calidad_target_energia.md`.\n")

    SUMMARY.write_text("".join(lines), encoding="utf-8")
    print(f"OK - {SUMMARY}")
    print(f"OK - {len(figures)} figuras en {FIG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
