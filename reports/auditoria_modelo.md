# Auditoría del modelo — primer modelo v2

## 1. Resumen ejecutivo

| Aspecto | Veredicto | Evidencia |
|---|---|---|
| Split temporal por fecha única | **OK** | `assert max(train) < min(test)` y disjunción de meses verificadas en código y log de ejecución. |
| Cohorte alineada base vs auxiliares | **OK** | Ambos escenarios usan las mismas fechas, mismas filas (n_train=265 558, n_test=71 985 en ambos). |
| Inclusión de `clientes_facturados` como feature | **WARNING crítico** | Es casi-contemporánea con el target; explica gran parte del R² alto. Ver §2. |
| R² = 0.97 del escenario BASE | **PLAUSIBLE pero engañoso** | Verificado por construcción del target: `energia_kwh ≈ kWh_por_cliente × clientes_facturados`, y `kWh_por_cliente` es estable dentro de (tipo, tarifa). Ver §3. |
| Ridge con auxiliares: R² ≈ -1.4e11 | **WARNING** | Numéricamente inestable. Hipótesis: extrapolación del scaler entre 2018-2022 (train) y 2023-2024 (test) en columnas lag con tendencia. No es leakage; es shift de distribución. |
| Comparación BASE vs CON aux justa | **OK metodológicamente, pero no informativa** | Usa misma cohorte; el problema es que las features auxiliares son **constantes por mes a nivel sistema**, no aportan varianza intra-mes. |
| Necesidad de escenario sin `clientes_facturados` | **REQUERIDO** | Sin él podemos saber cuánta señal viene de la identidad (region/comuna/tarifa/tipo) + tiempo, vs cuánta del conteo de clientes. |

## 2. Riesgo de la feature `clientes_facturados`

**Evidencia empírica** (subset 2018-04 → 2024-12, n = 337 543):

- Correlación cruda `corr(clientes_facturados, energia_kwh) = 0.89`.
- Regresión lineal univariada **dentro de cada grupo (tipo_cliente, tarifa)** clientes_facturados → energia_kwh:
  - R² mediano entre grupos = **0.56**.
  - R² del cuartil 75 = 0.71.
  - Grupos con R² > 0.90: BT3PP, BT3PPP, BT1a, BT1A, BT4.3.
- La relación es estructural: el target se construye como `Σ consumo_individual = consumo_promedio × clientes_facturados`. La identidad y la tarifa fijan el orden de magnitud del consumo por cliente.

**Implicación**: en este momento el modelo está casi reconstruyendo una identidad contable, no descubriendo dinámica predictiva. Esto es honesto declararlo en la presentación.

**¿Constituye leakage?**
- En sentido **temporal estricto**: no. `clientes_facturados` se conoce al momento de facturar el mismo mes.
- En sentido **práctico de utilidad**: sí es problemático para predicción real. Para predecir el mes siguiente se necesitaría `clientes_facturados_L1`.

## 3. ¿Es plausible el R² ≈ 0.97?

Sí, dado el diseño:
- `clientes_facturados` aporta el orden de magnitud.
- `tarifa` (31 niveles) + `tipo_clientes` (2) + `region` × `comuna` (16 × 330) refinan el consumo por cliente.
- El RandomForest con depth=10 y 100 árboles puede capturar las interacciones tarifa × cliente × tiempo.
- Resultado plausible para un modelo que tiene un **proxy directo del target** entre sus features.

Si quitamos `clientes_facturados`, esperamos un R² claramente menor — eso lo medimos en el escenario B del modelo v2.

## 4. Sobre la inestabilidad de Ridge con auxiliares

Hipótesis (a verificar formalmente más adelante):
- Las columnas lag son **idénticas para todas las filas de un mismo mes** (son agregados nacionales SEN). Tras el OneHotEncoder con `drop='first'` y mezcla con 18 numéricas escaladas, la matriz puede quedar mal condicionada.
- El test set (2023-08 → 2024-12) puede tener valores de demanda fuera del rango entrenado por el `StandardScaler` (post-pandemia, recuperación), y Ridge con α=1 no contiene la extrapolación.
- **Esto no es leakage**, es shift de distribución temporal.

## 5. Recomendaciones para Presentación 1

1. Reportar **cuatro escenarios** (modelo v2):
   - A. Base con `clientes_facturados` — referencia (R² alto pero condicionado a feature contemporánea).
   - B. Base sin `clientes_facturados` — mide señal puramente identitaria + temporal.
   - C. Variante con `energia_kwh > 0` y `clientes_facturados > 0` (vista limpia) usando features de A.
   - D. Con auxiliares (lags L1/L2/L3). Mantener para mostrar el resultado contraintuitivo.
2. Explicar honestamente en la presentación: el R² alto del escenario A está dominado por `clientes_facturados`. La pregunta interesante es B/C, donde se mide poder predictivo independiente.
3. **No hacer tuning** todavía. El primer modelo de presentación debe ser entendible.
4. Documentar Ridge como inestable con aux y dejar la solución para la próxima entrega.

## 6. Preguntas abiertas

- No se tiene certeza de por qué el cohorte con auxiliares pierde R² incluso en RandomForest. Hipótesis razonable: ruido + reducción efectiva del set por filtrado de lags y un test fuera de la distribución entrenada. Requiere análisis adicional con TimeSeriesSplit.
- No se puede determinar si los registros con `clientes_facturados == 0` y `energia_kwh < 0` corresponden a refacturaciones, generación distribuida o errores sin acceso a la fuente operativa.
