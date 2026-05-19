"""
Modelo v2 - 4 escenarios honestos para `energia_kwh`.

Escenarios:
  A. Base con `clientes_facturados`         (referencia, sesgada por feature contemporánea)
  B. Base sin `clientes_facturados`         (mide señal identidad + tiempo)
  C. Base + `clientes_facturados`, vista filtrada `energia_kwh > 0` y `clientes_facturados > 0`
  D. Con auxiliares (base + lags L1/L2/L3) sobre la cohorte aux

Validación: split por fecha única (80/20), `max(train) < min(test)`.

Cohorte temporal compartida (A, B, C, D): el rango aux 2018-04 → 2024-12,
sólo fechas con todos los lags válidos en aux (el split es idéntico en todos los
escenarios para que la comparación sea justa).

Modelos: DummyRegressor (media), Ridge (alpha=1, scaled), RandomForest (n=100, depth=10).

Sin tuning. Sin XGBoost/LightGBM. Sin redes.

Outputs:
  - reports/resumen_modelo_energia.md
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "data" / "interim" / "facturacion_clean.parquet"
AUX_PATH = ROOT / "data" / "processed" / "modeling_con_auxiliares.parquet"
OUT = ROOT / "reports" / "resumen_modelo_energia.md"

TARGET = "energia_kwh"
CAT_FEATURES = ["region", "comuna", "tipo_clientes", "tarifa"]
NUM_TIME = ["anio", "mes"]
LAG_SUFFIXES = ("_L1", "_L2", "_L3")


def temporal_split(unique_dates):
    unique_dates = sorted(unique_dates)
    n_train = int(len(unique_dates) * 0.8)
    return set(unique_dates[:n_train]), set(unique_dates[n_train:])


def build_pre(cat_cols, num_cols, scale: bool):
    num_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    if scale:
        num_pipe.steps.append(("scaler", StandardScaler()))
    cat_pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", drop="first")),
        ]
    )
    return ColumnTransformer(
        [("num", num_pipe, num_cols), ("cat", cat_pipe, cat_cols)],
        remainder="drop",
    )


def fit_eval(name, model, X_tr, y_tr, X_te, y_te):
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    mae = mean_absolute_error(y_te, pred)
    rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
    r2 = r2_score(y_te, pred)
    return {"modelo": name, "MAE": mae, "RMSE": rmse, "R2": r2}


def run_scenario(label, df, feature_cols, cat_cols, num_cols, train_dates, test_dates):
    train = df[df["fecha"].isin(train_dates)]
    test = df[df["fecha"].isin(test_dates)]
    X_tr, y_tr = train[feature_cols], train[TARGET]
    X_te, y_te = test[feature_cols], test[TARGET]
    results = []
    results.append(fit_eval("Baseline (media train)", DummyRegressor(strategy="mean"), X_tr, y_tr, X_te, y_te))
    pre = build_pre(cat_cols, num_cols, scale=True)
    results.append(fit_eval("Ridge (α=1, scaled)", Pipeline([("pre", pre), ("m", Ridge(alpha=1.0))]), X_tr, y_tr, X_te, y_te))
    pre = build_pre(cat_cols, num_cols, scale=False)
    results.append(fit_eval(
        "RandomForest (n=100, depth=10)",
        Pipeline([("pre", pre), ("m", RandomForestRegressor(n_estimators=100, max_depth=10, n_jobs=-1, random_state=42))]),
        X_tr, y_tr, X_te, y_te))
    return {
        "label": label,
        "n_train": len(train), "n_test": len(test),
        "fechas_train": (min(train_dates), max(train_dates)),
        "fechas_test": (min(test_dates), max(test_dates)),
        "feature_cols": feature_cols,
        "results": results,
    }


def main() -> int:
    if not BASE_PATH.exists() or not AUX_PATH.exists():
        print("ERROR: datasets requeridos no existen", file=sys.stderr)
        return 1

    base = pd.read_parquet(BASE_PATH)
    aux = pd.read_parquet(AUX_PATH)
    base["fecha"] = pd.to_datetime(base["fecha"])
    aux["fecha"] = pd.to_datetime(aux["fecha"])
    if "anio_x" in aux.columns:
        aux = aux.rename(columns={"anio_x": "anio", "mes_x": "mes"})

    lag_cols = [c for c in aux.columns if c.endswith(LAG_SUFFIXES)]
    aux_full = aux.dropna(subset=lag_cols).copy()
    fair_dates = sorted(aux_full["fecha"].unique())
    base_fair = base[base["fecha"].isin(fair_dates)].copy()

    train_dates, test_dates = temporal_split(fair_dates)
    assert max(train_dates) < min(test_dates)
    assert not (train_dates & test_dates)

    # A: con clientes_facturados
    feat_a = NUM_TIME + ["clientes_facturados"] + CAT_FEATURES
    res_a = run_scenario("A. Base con clientes_facturados", base_fair, feat_a, CAT_FEATURES, NUM_TIME + ["clientes_facturados"], train_dates, test_dates)

    # B: sin clientes_facturados
    feat_b = NUM_TIME + CAT_FEATURES
    res_b = run_scenario("B. Base sin clientes_facturados", base_fair, feat_b, CAT_FEATURES, NUM_TIME, train_dates, test_dates)

    # C: base + cf, vista filtrada
    base_filt = base_fair[(base_fair["energia_kwh"] > 0) & (base_fair["clientes_facturados"] > 0)].copy()
    res_c = run_scenario("C. Base + cf, filtrado (energia>0 & cf>0)", base_filt, feat_a, CAT_FEATURES, NUM_TIME + ["clientes_facturados"], train_dates, test_dates)

    # D: con auxiliares
    feat_d = feat_a + lag_cols
    num_d = NUM_TIME + ["clientes_facturados"] + lag_cols
    res_d = run_scenario("D. Con auxiliares (lags)", aux_full, feat_d, CAT_FEATURES, num_d, train_dates, test_dates)

    # ---------- Render markdown ----------
    lines: list[str] = []
    lines.append("# Presentación 1 - Primer modelo v2 (4 escenarios)\n")
    lines.append("\n## Diseño experimental\n\n")
    lines.append("- Target: `energia_kwh` (regresión).\n")
    lines.append(f"- Cohorte temporal usable: {len(fair_dates)} meses ({min(fair_dates).date()} → {max(fair_dates).date()}).\n")
    lines.append(f"- Split por fecha única 80/20:\n")
    lines.append(f"  - Train: {min(train_dates).date()} → {max(train_dates).date()} ({len(train_dates)} meses).\n")
    lines.append(f"  - Test: {min(test_dates).date()} → {max(test_dates).date()} ({len(test_dates)} meses).\n")
    lines.append("- `max(train) < min(test)` y meses disjuntos: VERIFICADO en código.\n")
    lines.append("- Métricas: MAE, RMSE, R². MAPE no se reporta (ceros y negativos en target).\n")
    lines.append("\n## Resultados por escenario\n\n")
    for res in (res_a, res_b, res_c, res_d):
        lines.append(f"### {res['label']}\n\n")
        lines.append(f"- Filas train: {res['n_train']:,} · test: {res['n_test']:,}\n".replace(",", " "))
        lines.append(f"- Features pre-OHE: {len(res['feature_cols'])}\n\n")
        lines.append("| Modelo | MAE | RMSE | R² |\n|---|---:|---:|---:|\n")
        for r in res["results"]:
            lines.append(f"| {r['modelo']} | {r['MAE']:,.0f} | {r['RMSE']:,.0f} | {r['R2']:.4f} |\n".replace(",", " "))
        lines.append("\n")

    # Tabla comparativa de mejores modelos
    def best_rf(res):
        return next(r for r in res["results"] if r["modelo"].startswith("RandomForest"))

    def best_ridge(res):
        return next(r for r in res["results"] if r["modelo"].startswith("Ridge"))

    lines.append("## Comparación: RandomForest entre escenarios\n\n")
    lines.append("| Escenario | n train | n test | MAE | RMSE | R² |\n|---|---:|---:|---:|---:|---:|\n")
    for res in (res_a, res_b, res_c, res_d):
        r = best_rf(res)
        lines.append(f"| {res['label']} | {res['n_train']:,} | {res['n_test']:,} | {r['MAE']:,.0f} | {r['RMSE']:,.0f} | {r['R2']:.4f} |\n".replace(",", " "))
    lines.append("\n## Comparación: Ridge entre escenarios\n\n")
    lines.append("| Escenario | MAE | RMSE | R² |\n|---|---:|---:|---:|\n")
    for res in (res_a, res_b, res_c, res_d):
        r = best_ridge(res)
        lines.append(f"| {res['label']} | {r['MAE']:,.0f} | {r['RMSE']:,.0f} | {r['R2']:.4f} |\n".replace(",", " "))

    lines.append("\n## Interpretación\n\n")
    lines.append(
        "- Escenario A (con `clientes_facturados`): el R² alto del RF refleja que el modelo está capturando una identidad casi contable (`energia ≈ kWh_por_cliente × clientes`). Es plausible pero **no demuestra capacidad predictiva genuina**.\n"
    )
    lines.append(
        "- Escenario B (sin `clientes_facturados`): mide cuánto puede predecir el modelo sólo con identidad geográfica/tarifaria + tiempo. La diferencia A-B cuantifica la dependencia del modelo en esa feature contemporánea.\n"
    )
    lines.append(
        "- Escenario C (con cf, filtrado `energia>0 & cf>0`): elimina ruido de filas degeneradas; sirve para una lectura más limpia del rendimiento real.\n"
    )
    lines.append(
        "- Escenario D (con auxiliares): los lags son agregados nacionales SEN, idénticos para todas las filas del mismo mes. Aportan poca varianza intra-mes y pueden dañar la generalización a meses fuera del rango entrenado.\n"
    )
    lines.append("\n## Recomendación para presentación\n\n")
    lines.append("- Mostrar los **4 escenarios** y declarar honestamente la dependencia del R² alto en `clientes_facturados`.\n")
    lines.append("- El primer modelo defendible para la entrega es A (referencia) **acompañado** del B (límite inferior honesto).\n")
    lines.append("- Marcar D como hallazgo metodológico: agregar features auxiliares mal diseñadas no garantiza mejora.\n")
    lines.append("\n## Advertencias metodológicas\n\n")
    lines.append("- `clientes_facturados` no es leakage temporal (no usa información futura), pero es **casi contemporánea** con el target.\n")
    lines.append("- Para predicción real a un mes futuro habría que usar `clientes_facturados_lag1` (no disponible aún).\n")
    lines.append("- Ridge sigue dependiendo de un buen scaling; con auxiliares hay shift de distribución entre train y test.\n")
    lines.append("- Sin tuning. Hiperparámetros por defecto.\n")
    lines.append("- Sólo holdout temporal simple. Próximo paso: TimeSeriesSplit con varios folds.\n")

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"OK - {OUT}")
    print()
    for res in (res_a, res_b, res_c, res_d):
        print(f"[{res['label']}] n_train={res['n_train']} n_test={res['n_test']}")
        for r in res["results"]:
            print(f"  {r['modelo']:>32} MAE={r['MAE']:.0f} RMSE={r['RMSE']:.0f} R2={r['R2']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
