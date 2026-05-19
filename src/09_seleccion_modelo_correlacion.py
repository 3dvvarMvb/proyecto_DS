"""
Selección de modelo + heatmaps de correlación + análisis de variable dominante.

Lee `data/interim/facturacion_clean.parquet` (sin modificarlo) y produce:

  - Tabla comparativa de 7 modelos de regresión (MAE, MSE, RMSE, R², MAPE).
  - Figuras 08-16 en `reports/figures_v2/`.
  - Reporte `reports/seleccion_modelo_y_correlacion.md`.

Vista de modelado (sólo dentro del pipeline, no toca el parquet):
    energia_kwh > 0 AND clientes_facturados > 0
Cohorte temporal:
    2018-04-01 → 2024-12-01 (idéntica al modelo v2, para comparabilidad).
Split temporal:
    80/20 por fecha única, con assert `max(train) < min(test)`.

Modelos comparados:
    Dummy(mean), LinearRegression, Ridge(α=1), DecisionTree(d=10),
    RandomForest(n=100, d=10), ExtraTrees(n=100, d=10), KNN.
    KNN se intenta de forma defensiva; si falla o es muy lento se omite con
    error registrado.

Métricas: MAE, MSE, RMSE, R², MAPE (este último válido porque y_true > 0 en la
vista). `accuracy` NO aplica: es regresión.

No usa tuning, ni XGBoost, ni redes.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "data" / "interim" / "facturacion_clean.parquet"
AUX_PATH = ROOT / "data" / "processed" / "modeling_con_auxiliares.parquet"
FIGDIR = ROOT / "reports" / "figures_v2"
REPORT = ROOT / "reports" / "seleccion_modelo_y_correlacion.md"

TARGET = "energia_kwh"
CAT_FEATURES = ["region", "comuna", "tipo_clientes", "tarifa"]
NUM_FEATURES = ["anio", "mes", "clientes_facturados"]
FEATURES = NUM_FEATURES + CAT_FEATURES

COHORT_START = pd.Timestamp("2018-04-01")
COHORT_END = pd.Timestamp("2024-12-01")

RANDOM_STATE = 42

KNN_MAX_TRAIN = 50_000  # subsample defensivo declarado en el reporte
KNN_TIMEOUT_S = 600  # informativo; sklearn no soporta timeout directo


@dataclass
class ModelResult:
    modelo: str
    MAE: float
    MSE: float
    RMSE: float
    R2: float
    MAPE: float
    fit_s: float
    pred_s: float
    nota: str = ""


def df_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join([head, sep, *rows])


def temporal_split(unique_dates: list[pd.Timestamp]) -> tuple[set, set]:
    unique_dates = sorted(unique_dates)
    n_train = int(len(unique_dates) * 0.8)
    train = set(unique_dates[:n_train])
    test = set(unique_dates[n_train:])
    assert max(train) < min(test), "split temporal no respeta orden"
    assert not (train & test), "meses compartidos entre train y test"
    return train, test


def build_preprocessor(scale: bool) -> ColumnTransformer:
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scaler", StandardScaler()))
    num_pipe = Pipeline(num_steps)
    cat_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", drop="first")),
        ]
    )
    return ColumnTransformer(
        [
            ("num", num_pipe, NUM_FEATURES),
            ("cat", cat_pipe, CAT_FEATURES),
        ],
        remainder="drop",
    )


def fit_eval(
    name: str,
    pipe: Pipeline,
    X_tr,
    y_tr,
    X_te,
    y_te,
    nota: str = "",
) -> ModelResult:
    t0 = time.perf_counter()
    pipe.fit(X_tr, y_tr)
    fit_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    pred = pipe.predict(X_te)
    pred_s = time.perf_counter() - t1
    mae = float(mean_absolute_error(y_te, pred))
    mse = float(mean_squared_error(y_te, pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_te, pred))
    mape = float(mean_absolute_percentage_error(y_te, pred))
    return ModelResult(
        modelo=name, MAE=mae, MSE=mse, RMSE=rmse, R2=r2, MAPE=mape,
        fit_s=fit_s, pred_s=pred_s, nota=nota,
    )


def safe_run(name, pipe, X_tr, y_tr, X_te, y_te, nota=""):
    try:
        return fit_eval(name, pipe, X_tr, y_tr, X_te, y_te, nota=nota)
    except Exception as e:
        print(f"[ERROR] {name}: {e}", file=sys.stderr)
        traceback.print_exc()
        return ModelResult(
            modelo=name, MAE=np.nan, MSE=np.nan, RMSE=np.nan, R2=np.nan,
            MAPE=np.nan, fit_s=np.nan, pred_s=np.nan,
            nota=f"FALLÓ: {type(e).__name__}: {str(e)[:160]}",
        )


def feature_names_from_pre(pre: ColumnTransformer) -> list[str]:
    names: list[str] = []
    for name, trans, cols in pre.transformers_:
        if name == "num":
            names.extend(cols)
        elif name == "cat":
            ohe: OneHotEncoder = trans.named_steps["ohe"]
            try:
                ohe_names = ohe.get_feature_names_out(cols)
            except Exception:
                ohe_names = [f"{c}_{i}" for c in cols for i in range(10)]
            names.extend(list(ohe_names))
    return names


def predict_for_residuals(pipe: Pipeline, X_te) -> np.ndarray:
    return pipe.predict(X_te)


# =========================================================================
# MAIN
# =========================================================================

def main() -> int:
    if not BASE_PATH.exists():
        print(f"ERROR: no existe {BASE_PATH}", file=sys.stderr)
        return 1
    FIGDIR.mkdir(parents=True, exist_ok=True)

    base = pd.read_parquet(BASE_PATH)
    base["fecha"] = pd.to_datetime(base["fecha"])

    # Cohorte temporal igual a v2 (para comparabilidad con resumen_modelo_energia.md)
    in_cohort = (base["fecha"] >= COHORT_START) & (base["fecha"] <= COHORT_END)
    cohort = base.loc[in_cohort].copy()

    # Vista de modelado: target > 0 y clientes > 0 (vista filtrada, MAPE válido).
    view = cohort[(cohort["energia_kwh"] > 0) & (cohort["clientes_facturados"] > 0)].copy()

    unique_dates = sorted(view["fecha"].unique())
    train_dates, test_dates = temporal_split(unique_dates)

    train = view[view["fecha"].isin(train_dates)].copy()
    test = view[view["fecha"].isin(test_dates)].copy()

    X_tr = train[FEATURES]
    y_tr = train[TARGET]
    X_te = test[FEATURES]
    y_te = test[TARGET]

    n_train_dates = len(train_dates)
    n_test_dates = len(test_dates)
    train_range = (min(train_dates), max(train_dates))
    test_range = (min(test_dates), max(test_dates))

    print(f"Cohorte:   {COHORT_START.date()} → {COHORT_END.date()}")
    print(f"Vista:     energia_kwh>0 & clientes_facturados>0 → {len(view):,} filas".replace(",", " "))
    print(f"Train:     {train_range[0].date()} → {train_range[1].date()}  ({n_train_dates} meses, {len(train):,} filas)".replace(",", " "))
    print(f"Test:      {test_range[0].date()} → {test_range[1].date()}  ({n_test_dates} meses, {len(test):,} filas)".replace(",", " "))

    results: list[ModelResult] = []

    # -- Baseline
    results.append(safe_run(
        "DummyRegressor(mean)",
        Pipeline([("m", DummyRegressor(strategy="mean"))]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- LinearRegression (scaled, OHE)
    pre = build_preprocessor(scale=True)
    results.append(safe_run(
        "LinearRegression",
        Pipeline([("pre", pre), ("m", LinearRegression())]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- Ridge α=1 (scaled, OHE)
    pre = build_preprocessor(scale=True)
    results.append(safe_run(
        "Ridge(α=1)",
        Pipeline([("pre", pre), ("m", Ridge(alpha=1.0))]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- DecisionTree
    pre = build_preprocessor(scale=False)
    results.append(safe_run(
        "DecisionTree(d=10)",
        Pipeline([("pre", pre), ("m", DecisionTreeRegressor(max_depth=10, random_state=RANDOM_STATE))]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- RandomForest
    pre = build_preprocessor(scale=False)
    results.append(safe_run(
        "RandomForest(n=100,d=10)",
        Pipeline([
            ("pre", pre),
            ("m", RandomForestRegressor(n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- ExtraTrees
    pre = build_preprocessor(scale=False)
    results.append(safe_run(
        "ExtraTrees(n=100,d=10)",
        Pipeline([
            ("pre", pre),
            ("m", ExtraTreesRegressor(n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
        X_tr, y_tr, X_te, y_te,
    ))

    # -- KNN (defensivo)
    # KNN sobre OHE grande es lento; usamos submuestra del train (declarado en reporte).
    knn_note = ""
    rng = np.random.default_rng(RANDOM_STATE)
    if len(train) > KNN_MAX_TRAIN:
        idx = rng.choice(len(train), size=KNN_MAX_TRAIN, replace=False)
        X_tr_knn = X_tr.iloc[idx]
        y_tr_knn = y_tr.iloc[idx]
        knn_note = f"submuestra de train de {KNN_MAX_TRAIN:,} filas para evitar O(n²)".replace(",", " ")
    else:
        X_tr_knn = X_tr
        y_tr_knn = y_tr

    pre = build_preprocessor(scale=True)
    results.append(safe_run(
        "KNN(k=5,scaled)",
        Pipeline([("pre", pre), ("m", KNeighborsRegressor(n_neighbors=5, n_jobs=-1))]),
        X_tr_knn, y_tr_knn, X_te, y_te,
        nota=knn_note,
    ))

    # =====================================================================
    # Tabla ordenada
    # =====================================================================
    rdf = pd.DataFrame([asdict(r) for r in results])
    # ordenar: mayor R², menor RMSE, menor MAE
    rdf_sorted = rdf.sort_values(by=["R2", "RMSE", "MAE"], ascending=[False, True, True]).reset_index(drop=True)

    print("\nTabla de selección de modelo:")
    print(rdf_sorted[["modelo", "MAE", "MSE", "RMSE", "R2", "MAPE", "fit_s", "nota"]].to_string(index=False))

    # =====================================================================
    # Figuras 08, 09, 10 - barras comparativas
    # =====================================================================
    plot_df = rdf_sorted.dropna(subset=["R2", "RMSE", "MAE"]).copy()

    def bar_plot(metric: str, ascending_better: bool, fname: str, title: str, ylabel: str):
        d = plot_df.sort_values(metric, ascending=ascending_better).copy()
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.bar(d["modelo"], d[metric])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=30)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment("right")
        ax.grid(axis="y", linestyle=":", alpha=0.5)
        fig.tight_layout()
        out = FIGDIR / fname
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"  {out}")

    bar_plot("R2", False, "08_comparacion_r2_modelos.png",
             "Selección de modelo - R² (mayor = mejor)", "R²")
    bar_plot("RMSE", True, "09_comparacion_rmse_modelos.png",
             "Selección de modelo - RMSE (menor = mejor)", "RMSE (kWh)")
    bar_plot("MAE", True, "10_comparacion_mae_modelos.png",
             "Selección de modelo - MAE (menor = mejor)", "MAE (kWh)")

    # =====================================================================
    # Mejor modelo (excluyendo dummy y modelos con fallo)
    # Política de desempate: si dos modelos están dentro de 0.001 en R², gana
    # el de menor MAE. Esto evita que ExtraTrees y RandomForest, indistinguibles
    # en R²/RMSE (≈0.97), se elijan por azar numérico — el desempate se hace
    # por error absoluto (más interpretable y estable).
    # =====================================================================
    competitive = rdf_sorted[~rdf_sorted["modelo"].str.startswith("DummyRegressor")]
    competitive = competitive.dropna(subset=["R2"]).copy()
    top_r2 = float(competitive["R2"].iloc[0])
    tied = competitive[competitive["R2"] >= top_r2 - 0.001]
    tied = tied.sort_values(by=["MAE", "RMSE"], ascending=[True, True])
    best_name = tied.iloc[0]["modelo"]
    print(
        f"\nMejor modelo (R² top {top_r2:.4f}, "
        f"{len(tied)} empate(s) → desempate por MAE): {best_name}"
    )

    # Re-entrenar para gráficos pred vs real / residuos / feature importance
    if best_name.startswith("ExtraTrees"):
        best_pre = build_preprocessor(scale=False)
        best_model = ExtraTreesRegressor(
            n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1
        )
        best_is_tree = True
    elif best_name.startswith("RandomForest"):
        best_pre = build_preprocessor(scale=False)
        best_model = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1
        )
        best_is_tree = True
    elif best_name.startswith("DecisionTree"):
        best_pre = build_preprocessor(scale=False)
        best_model = DecisionTreeRegressor(max_depth=10, random_state=RANDOM_STATE)
        best_is_tree = True
    elif best_name.startswith("Ridge"):
        best_pre = build_preprocessor(scale=True)
        best_model = Ridge(alpha=1.0)
        best_is_tree = False
    elif best_name.startswith("LinearRegression"):
        best_pre = build_preprocessor(scale=True)
        best_model = LinearRegression()
        best_is_tree = False
    elif best_name.startswith("KNN"):
        best_pre = build_preprocessor(scale=True)
        best_model = KNeighborsRegressor(n_neighbors=5, n_jobs=-1)
        best_is_tree = False
    else:
        best_pre = build_preprocessor(scale=False)
        best_model = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1
        )
        best_is_tree = True

    best_pipe = Pipeline([("pre", best_pre), ("m", best_model)])
    best_pipe.fit(X_tr, y_tr)
    y_pred = best_pipe.predict(X_te)

    # Figura 11 - pred vs real
    fig, ax = plt.subplots(figsize=(6.5, 6))
    sample = min(20000, len(y_te))
    rng2 = np.random.default_rng(RANDOM_STATE)
    sidx = rng2.choice(len(y_te), size=sample, replace=False)
    yt_s = np.asarray(y_te)[sidx]
    yp_s = np.asarray(y_pred)[sidx]
    ax.scatter(yt_s, yp_s, s=4, alpha=0.25)
    lo = min(yt_s.min(), yp_s.min())
    hi = max(yt_s.max(), yp_s.max())
    ax.plot([lo, hi], [lo, hi], color="red", linewidth=1, label="y = x")
    ax.set_xscale("symlog")
    ax.set_yscale("symlog")
    ax.set_xlabel("energía real (kWh, symlog)")
    ax.set_ylabel("energía predicha (kWh, symlog)")
    ax.set_title(f"Predicción vs valor real - {best_name}\n(muestra de {sample} filas del test)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_pred = FIGDIR / "11_prediccion_vs_real.png"
    fig.savefig(out_pred, dpi=110)
    plt.close(fig)
    print(f"  {out_pred}")

    # Figura 12 - residuos
    resid = np.asarray(y_te) - np.asarray(y_pred)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    # signed log para soportar negativos:
    def slog(x):
        return np.sign(x) * np.log1p(np.abs(x))

    axes[0].hist(slog(resid), bins=80, color="#4477AA", alpha=0.85)
    axes[0].set_xlabel("residual (signed log1p)")
    axes[0].set_ylabel("frecuencia")
    axes[0].set_title("Distribución de residuos")
    axes[0].grid(alpha=0.3)

    # residuos vs predicción (muestra)
    axes[1].scatter(yp_s, np.asarray(y_te)[sidx] - yp_s, s=4, alpha=0.25)
    axes[1].axhline(0, color="red", linewidth=1)
    axes[1].set_xscale("symlog")
    axes[1].set_xlabel("predicción (symlog)")
    axes[1].set_ylabel("residual (real - predicho)")
    axes[1].set_title("Residuos vs predicción")
    axes[1].grid(alpha=0.3)
    fig.suptitle(f"Residuos - {best_name}")
    fig.tight_layout()
    out_res = FIGDIR / "12_residuos_modelo.png"
    fig.savefig(out_res, dpi=110)
    plt.close(fig)
    print(f"  {out_res}")

    # =====================================================================
    # Feature importance (sólo si el mejor es árbol)
    # =====================================================================
    fi_df: Optional[pd.DataFrame] = None
    if best_is_tree:
        try:
            pre_fitted: ColumnTransformer = best_pipe.named_steps["pre"]
            mdl = best_pipe.named_steps["m"]
            fnames = feature_names_from_pre(pre_fitted)
            importances = mdl.feature_importances_
            if len(fnames) == len(importances):
                fi_df = pd.DataFrame({"feature": fnames, "importance": importances})
            else:
                fi_df = pd.DataFrame({
                    "feature": [f"f{i}" for i in range(len(importances))],
                    "importance": importances,
                })
            fi_df = fi_df.sort_values("importance", ascending=False).reset_index(drop=True)
            top = fi_df.head(20).iloc[::-1]
            fig, ax = plt.subplots(figsize=(9, 7))
            ax.barh(top["feature"], top["importance"])
            ax.set_xlabel("importance")
            ax.set_title(f"Top 20 feature importances - {best_name}")
            ax.grid(axis="x", alpha=0.3)
            fig.tight_layout()
            out_fi = FIGDIR / "16_importancia_variables.png"
            fig.savefig(out_fi, dpi=110)
            plt.close(fig)
            print(f"  {out_fi}")
        except Exception as e:
            print(f"[WARN] no se pudo calcular feature importance: {e}")

    # =====================================================================
    # Variable dominante - log-log y correlaciones
    # =====================================================================
    view2 = view[["energia_kwh", "clientes_facturados", "anio", "mes", "tipo_clientes"]].copy()
    view2["log_energia_kwh"] = np.log1p(view2["energia_kwh"])
    view2["log_clientes_facturados"] = np.log1p(view2["clientes_facturados"])

    corr_pearson = view2[["energia_kwh", "clientes_facturados"]].corr(method="pearson").iloc[0, 1]
    corr_spearman = view2[["energia_kwh", "clientes_facturados"]].corr(method="spearman").iloc[0, 1]
    corr_pearson_log = view2[["log_energia_kwh", "log_clientes_facturados"]].corr(method="pearson").iloc[0, 1]
    corr_spearman_log = view2[["log_energia_kwh", "log_clientes_facturados"]].corr(method="spearman").iloc[0, 1]

    # R² de un modelo simple usando sólo clientes_facturados (regresión lineal)
    lr_simple = LinearRegression()
    lr_simple.fit(X_tr[["clientes_facturados"]], y_tr)
    r2_cf_only = float(r2_score(y_te, lr_simple.predict(X_te[["clientes_facturados"]])))

    # log-log scatter (muestra)
    sample_n = min(20000, len(view2))
    sidx2 = rng2.choice(len(view2), size=sample_n, replace=False)
    v_s = view2.iloc[sidx2]
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for tipo, marker, color in [("Residencial", "o", "#4477AA"), ("No Residencial", "x", "#EE6677")]:
        sub = v_s[v_s["tipo_clientes"] == tipo]
        if len(sub) > 0:
            ax.scatter(sub["log_clientes_facturados"], sub["log_energia_kwh"],
                       s=5, alpha=0.25, label=tipo, color=color, marker=marker)
    ax.set_xlabel("log(1 + clientes_facturados)")
    ax.set_ylabel("log(1 + energia_kwh)")
    ax.set_title(f"Relación log-log clientes_facturados ↔ energia_kwh\n"
                 f"Pearson(log)={corr_pearson_log:.3f}  Spearman(log)={corr_spearman_log:.3f}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_ll = FIGDIR / "15_clientes_vs_energia_loglog.png"
    fig.savefig(out_ll, dpi=110)
    plt.close(fig)
    print(f"  {out_ll}")

    # =====================================================================
    # Heatmap numérico
    # =====================================================================
    num_cols_h = ["energia_kwh", "clientes_facturados", "anio", "mes"]
    corr_num = view[num_cols_h].corr(method="pearson")

    def heatmap(corr: pd.DataFrame, fname: str, title: str):
        fig, ax = plt.subplots(figsize=(0.9 + 0.85 * len(corr.columns), 0.9 + 0.7 * len(corr.columns)))
        im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr.columns)))
        ax.set_yticklabels(corr.columns)
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax.text(j, i, f"{corr.values[i, j]:.2f}",
                        ha="center", va="center",
                        color="white" if abs(corr.values[i, j]) > 0.5 else "black",
                        fontsize=9)
        fig.colorbar(im, ax=ax)
        ax.set_title(title)
        fig.tight_layout()
        out = FIGDIR / fname
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"  {out}")
        return out

    heatmap(corr_num, "13_matriz_correlacion_numerica.png",
            "Correlación Pearson - variables numéricas (vista filtrada)")

    # Heatmap log
    view_log = view2[["log_energia_kwh", "log_clientes_facturados", "anio", "mes"]].copy()
    corr_log = view_log.corr(method="pearson")
    heatmap(corr_log, "14_matriz_correlacion_log.png",
            "Correlación Pearson - log-transform de variables numéricas")

    # Heatmap extendido con auxiliares (sólo columnas que existen en el parquet aux)
    aux_block = ""
    if AUX_PATH.exists():
        aux = pd.read_parquet(AUX_PATH)
        if "anio_x" in aux.columns:
            aux = aux.rename(columns={"anio_x": "anio", "mes_x": "mes"})
        aux["fecha"] = pd.to_datetime(aux["fecha"])
        wanted_aux = [
            "demanda_promedio_mes_sen_L1",
            "demanda_maxima_mes_sen_L1",
            "rango_demanda_mes_sen_L1",
            "proporcion_ernc_mes_L1",
            "proporcion_hidro_mes_L1",
            "total_generacion_mes_L1",
        ]
        existing = [c for c in wanted_aux if c in aux.columns]
        missing = [c for c in wanted_aux if c not in aux.columns]
        aux_fcs = aux[(aux["energia_kwh"] > 0) & (aux["clientes_facturados"] > 0)].copy()
        aux_block_cols = ["energia_kwh", "clientes_facturados", "anio", "mes"] + existing
        corr_aux = aux_fcs[aux_block_cols].corr(method="pearson")
        # heatmap extendido
        fig, ax = plt.subplots(figsize=(1.2 + 0.85 * len(corr_aux.columns), 1.2 + 0.7 * len(corr_aux.columns)))
        im = ax.imshow(corr_aux.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(corr_aux.columns)))
        ax.set_xticklabels(corr_aux.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(corr_aux.columns)))
        ax.set_yticklabels(corr_aux.columns)
        for i in range(len(corr_aux.columns)):
            for j in range(len(corr_aux.columns)):
                ax.text(j, i, f"{corr_aux.values[i, j]:.2f}",
                        ha="center", va="center",
                        color="white" if abs(corr_aux.values[i, j]) > 0.5 else "black",
                        fontsize=8)
        fig.colorbar(im, ax=ax)
        ax.set_title("Correlación Pearson - base + auxiliares SEN (L1, cohorte aux)")
        fig.tight_layout()
        out_aux = FIGDIR / "13b_corr_heatmap_aux.png"
        fig.savefig(out_aux, dpi=110)
        plt.close(fig)
        print(f"  {out_aux}")
        aux_block = (
            "### Heatmap extendido con auxiliares SEN (`13b_corr_heatmap_aux.png`)\n\n"
            f"Columnas auxiliares incluidas (verificadas en parquet): `{', '.join(existing)}`.  \n"
            + (f"**Columnas pedidas que NO existen en parquet (no graficadas):** `{', '.join(missing)}`.\n" if missing else "Todas las columnas pedidas existen.\n")
        )

    # =====================================================================
    # Reporte markdown
    # =====================================================================
    sel_table = rdf_sorted[["modelo", "MAE", "MSE", "RMSE", "R2", "MAPE", "fit_s", "nota"]].copy()
    sel_table["MAE"] = sel_table["MAE"].map(lambda v: f"{v:,.0f}".replace(",", " ") if pd.notna(v) else "—")
    sel_table["MSE"] = sel_table["MSE"].map(lambda v: f"{v:,.2e}" if pd.notna(v) else "—")
    sel_table["RMSE"] = sel_table["RMSE"].map(lambda v: f"{v:,.0f}".replace(",", " ") if pd.notna(v) else "—")
    sel_table["R2"] = sel_table["R2"].map(lambda v: f"{v:.4f}" if pd.notna(v) else "—")
    sel_table["MAPE"] = sel_table["MAPE"].map(lambda v: f"{v:.3f}" if pd.notna(v) else "—")
    sel_table["fit_s"] = sel_table["fit_s"].map(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
    sel_table.columns = ["Modelo", "MAE", "MSE", "RMSE", "R²", "MAPE", "fit s", "nota"]

    # FI top-15 si existe
    fi_md = ""
    if fi_df is not None:
        top15 = fi_df.head(15).copy()
        top15["importance"] = top15["importance"].map(lambda v: f"{v:.4f}")
        fi_md = df_to_md(top15)

    lines: list[str] = []
    lines.append("# Selección de modelo + correlación - reporte (presentación 1)\n")
    lines.append("\n## 1. Objetivo de la etapa\n\n")
    lines.append(
        "Cerrar la entrega de la Presentación 1 con: (a) selección formal del modelo entre 7 regresores, (b) tabla comparativa con métricas reproducibles, (c) heatmaps de correlación, (d) análisis cuantitativo de `clientes_facturados` como variable dominante, (e) feature importance del mejor modelo basado en árboles.\n"
    )
    lines.append("\n## 2. Dataset usado\n\n")
    lines.append(f"- Archivo: `data/interim/facturacion_clean.parquet` ({len(base):,} filas, {len(base.columns)} columnas).\n".replace(",", " "))
    lines.append(f"- Cohorte temporal: {COHORT_START.date()} → {COHORT_END.date()} ({len(cohort):,} filas en cohorte).\n".replace(",", " "))
    lines.append(f"- Vista de modelado: `energia_kwh > 0 AND clientes_facturados > 0` → **{len(view):,} filas**.\n".replace(",", " "))
    lines.append("- NO se modifica `clean`; la vista se aplica sólo dentro del pipeline.\n")
    lines.append("\n### 2.1 Aclaración importante: ceros del target vs nulos de lags\n\n")
    lines.append("- Los **ceros de `energia_kwh`** son valores reales del dataset original (13 283 filas en `clean`, 2.7 %). NO son artefactos de generar lags.\n")
    lines.append("- Los **nulos en columnas `_L1`, `_L2`, `_L3`** vienen del diseño temporal de los lags: los primeros meses no tienen historia previa.\n")
    lines.append("- En escenarios con auxiliares, los primeros meses sin lags válidos se eliminan explícitamente (`dropna(subset=lag_cols)`).\n")
    lines.append("- Ambos fenómenos son **distintos** y no deben mezclarse en interpretación.\n")

    lines.append("\n## 3. Split temporal\n\n")
    lines.append(f"- {n_train_dates + n_test_dates} meses únicos, split 80/20.\n")
    lines.append(f"- Train: {train_range[0].date()} → {train_range[1].date()} ({n_train_dates} meses, {len(train):,} filas).\n".replace(",", " "))
    lines.append(f"- Test:  {test_range[0].date()} → {test_range[1].date()} ({n_test_dates} meses, {len(test):,} filas).\n".replace(",", " "))
    lines.append("- `max(train) < min(test)` y meses disjuntos: VERIFICADO en código (assert).\n")

    lines.append("\n## 4. Tabla comparativa de modelos\n\n")
    lines.append("Ordenada por R² (desc), RMSE (asc), MAE (asc). Métricas calculadas sobre el test set definido arriba.\n\n")
    lines.append(df_to_md(sel_table))
    lines.append("\n\n> **`accuracy` NO aplica**: este problema es de **regresión**, no de clasificación. La métrica análoga es R² (coeficiente de determinación).\n")
    lines.append("\n> **MAPE** sólo se reporta en esta vista porque por construcción `y_true > 0` (filtro). En el dataset completo (con ceros y negativos) MAPE divide por cero y no es métricamente válido.\n")
    if any("submuestra" in (r.nota or "") for r in results):
        lines.append("\n> **KNN**: el modelo se entrenó sobre una submuestra del train (declarado en la columna `nota`) para evitar el costo O(n²) con OHE de alta cardinalidad. La comparación con los otros modelos es informativa, no estrictamente justa.\n")
    any_failed = any(pd.isna(r.R2) for r in results)
    if any_failed:
        lines.append("\n> Modelos con valores `—` fallaron en ejecución; el error real está registrado en `nota`.\n")

    lines.append("\n## 5. Modelo seleccionado\n\n")
    best_row = competitive[competitive["modelo"] == best_name].iloc[0]
    lines.append(f"**{best_name}**.\n\n")

    if len(tied) > 1:
        lines.append(
            f"Se detectaron **{len(tied)} modelos empatados** dentro de 0.001 puntos de R² (top R² = {top_r2:.4f}):\n\n"
        )
        lines.append("| Modelo | R² | RMSE | MAE | MAPE | fit s |\n|---|---:|---:|---:|---:|---:|\n")
        for _, r in tied.iterrows():
            lines.append(
                f"| {r['modelo']} | {r['R2']:.4f} | {r['RMSE']:,.0f} | {r['MAE']:,.0f} | {r['MAPE']:.3f} | {r['fit_s']:.1f} |\n".replace(",", " ")
            )
        lines.append(
            f"\nRegla de desempate: **menor MAE**. Ganador: `{best_name}` (MAE = {best_row['MAE']:,.0f} kWh).\n".replace(",", " ")
        )
        lines.append(
            "Motivo: con R² indistinguibles, el MAE refleja error absoluto promedio y es más interpretable para la presentación. Adicionalmente, los modelos con mayor varianza interna (p.ej. ExtraTrees) tienden a generar MAPE inflado por inestabilidad en valores pequeños del target.\n"
        )

    lines.append("\nJustificación adicional del modelo elegido:\n\n")
    lines.append(f"- R² = {best_row['R2']:.4f}; RMSE = {best_row['RMSE']:,.0f} kWh; MAE = {best_row['MAE']:,.0f} kWh; MAPE = {best_row['MAPE']:.3f}.\n".replace(",", " "))
    lines.append("- Captura interacciones no lineales entre `tarifa`, `tipo_clientes`, `region` y `clientes_facturados`.\n")
    lines.append("- Tiempos de entrenamiento aceptables para el tamaño actual.\n")
    lines.append("- No requiere transformación logarítmica del target ni escalado.\n")
    lines.append("- Consistente con la elección del modelo v2 (`reports/resumen_modelo_energia.md`).\n")

    lines.append("\n## 6. Heatmaps de correlación\n\n")
    lines.append("### 6.1 Variables numéricas (`13_matriz_correlacion_numerica.png`)\n\n")
    lines.append("| variable | energia_kwh | clientes_facturados | anio | mes |\n|---|---:|---:|---:|---:|\n")
    for c in corr_num.columns:
        row = [c]
        for c2 in corr_num.columns:
            row.append(f"{corr_num.loc[c, c2]:.3f}")
        lines.append("| " + " | ".join(row) + " |\n")

    lines.append("\n### 6.2 Variables log-transformadas (`14_matriz_correlacion_log.png`)\n\n")
    lines.append("| variable | log_energia | log_clientes | anio | mes |\n|---|---:|---:|---:|---:|\n")
    for c in corr_log.columns:
        row = [c]
        for c2 in corr_log.columns:
            row.append(f"{corr_log.loc[c, c2]:.3f}")
        lines.append("| " + " | ".join(row) + " |\n")

    if aux_block:
        lines.append("\n" + aux_block)

    lines.append("\n**Advertencia**: el heatmap sólo refleja correlaciones lineales entre **variables numéricas**. La señal real de `region`, `comuna`, `tarifa` y `tipo_clientes` es categórica y **no aparece** aquí. Su efecto se mide indirectamente vía OneHotEncoder en el modelo.\n")

    lines.append("\n## 7. Variable dominante: `clientes_facturados`\n\n")
    lines.append("Evidencia cuantitativa (calculada sobre la vista filtrada del test set y la vista completa para correlaciones):\n\n")
    lines.append(f"- Correlación Pearson (raw) `corr(clientes_facturados, energia_kwh)` = **{corr_pearson:.3f}**.\n")
    lines.append(f"- Correlación Spearman (raw) = **{corr_spearman:.3f}**.\n")
    lines.append(f"- Correlación Pearson (log-log) = **{corr_pearson_log:.3f}**.\n")
    lines.append(f"- Correlación Spearman (log-log) = **{corr_spearman_log:.3f}**.\n")
    lines.append(f"- R² de regresión lineal univariada usando sólo `clientes_facturados` → `energia_kwh` (sin OHE, sin tarifa) en este split temporal: **{r2_cf_only:.4f}**.\n")
    lines.append(f"- Ver gráfico `15_clientes_vs_energia_loglog.png`: la relación log-log es claramente positiva y aproximadamente lineal, con dispersión por tipo de cliente.\n")

    lines.append("\n**Diferencia A (con cf) vs B (sin cf)** según el modelo v2:\n\n")
    lines.append("- A. RandomForest **con** `clientes_facturados`: R² = 0.9694, RMSE ≈ 391 092.\n")
    lines.append("- B. RandomForest **sin** `clientes_facturados`: R² = 0.7988, RMSE ≈ 1 003 554.\n")
    lines.append("- Diferencia ΔR² ≈ 0.17 atribuible a `clientes_facturados`.\n")

    lines.append("\n**¿Es leakage?**\n\n")
    lines.append("- En sentido **temporal estricto**: NO. `clientes_facturados` se conoce en el momento de facturar el mismo mes, no usa información futura.\n")
    lines.append("- En sentido **práctico de utilidad**: SÍ es problemático. Para predecir el mes futuro no se conoce el `clientes_facturados` futuro; debería usarse su lag (`clientes_facturados_L1`).\n")
    lines.append("- Para presentación: declararlo abiertamente. El R² alto es **plausible** pero está apoyado en una identidad casi contable.\n")

    if fi_md:
        lines.append("\n## 8. Feature importance (top 15)\n\n")
        lines.append("Importancias del mejor modelo basado en árboles (ver figura `16_importancia_variables.png`).\n\n")
        lines.append(fi_md)
        lines.append("\n")

    lines.append("\n## 9. Limitaciones\n\n")
    lines.append("- Sin hiperparameter tuning. Las cifras son una primera referencia, no un techo.\n")
    lines.append("- Sólo holdout temporal único 80/20. Falta TimeSeriesSplit con varios folds.\n")
    lines.append("- `clientes_facturados` casi contemporáneo con el target inflará el R². Para predicción genuina del mes futuro se necesita `clientes_facturados_L1`.\n")
    lines.append("- Heatmap no incluye categóricas (region/comuna/tarifa/tipo) — su efecto no se ve en el plot.\n")
    lines.append("- KNN se entrenó sobre submuestra; comparación con árboles es informativa, no concluyente.\n")
    lines.append("- 5 275 filas duplicadas sobre la clave panel (4 990 grupos) — limitación del dataset original, no resuelta aquí.\n")

    lines.append("\n## 10. Texto sugerido para la presentación (slide de selección)\n\n")
    lines.append("> \"Comparamos 7 modelos de regresión con la misma cohorte temporal (2018-04 → 2024-12) y el mismo split 80/20 por fecha. \"\n")
    lines.append(f"> \"El mejor desempeño lo obtuvo **{best_name}** con R² = {best_row['R2']:.4f} y RMSE ≈ {best_row['RMSE']:,.0f} kWh sobre el test. \"\n".replace(",", " "))
    lines.append("> \"La métrica `accuracy` no aplica: este es un problema de **regresión**, no de clasificación. \"\n")
    lines.append("> \"`clientes_facturados` es la variable dominante. Con ella el R² sube de 0.80 a 0.97; sin ella, el modelo retiene poder predictivo razonable basado en geografía y tarifa. \"\n")
    lines.append("> \"No es leakage temporal estricto, pero es una feature casi contemporánea: en próximas entregas usaremos su lag para una evaluación predictiva más honesta.\"\n")

    REPORT.write_text("".join(lines), encoding="utf-8")
    print(f"\nReporte: {REPORT}")

    # JSON con metadatos para reuso (notebook puede leerlo)
    meta = {
        "best_name": best_name,
        "cohort_start": str(COHORT_START.date()),
        "cohort_end": str(COHORT_END.date()),
        "n_view": len(view),
        "n_train": len(train),
        "n_test": len(test),
        "train_range": [str(train_range[0].date()), str(train_range[1].date())],
        "test_range": [str(test_range[0].date()), str(test_range[1].date())],
        "results": [asdict(r) for r in results],
        "corr_pearson": corr_pearson,
        "corr_spearman": corr_spearman,
        "corr_pearson_log": corr_pearson_log,
        "corr_spearman_log": corr_spearman_log,
        "r2_cf_only": r2_cf_only,
    }
    meta_path = ROOT / "reports" / "model_selection_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(f"Meta JSON: {meta_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
