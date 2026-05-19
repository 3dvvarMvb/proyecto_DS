# Decisión metodológica - calidad de `energia_kwh` y campos asociados

Auditoría realizada con `06_auditoria_datos.py`. Los archivos `data/raw` y `data/interim/facturacion_clean.parquet` no fueron modificados.

## 1. Inventario de anomalías

| Anomalía | Conteo | Notas |
|---|---:|---|
| `energia_kwh` < 0 | 1 191 | Concentrados en No Residencial (1 107 / 1 191) y tarifas industriales (AT4.x, AT2PP, AT3PP, BT4.1). Crecen año a año (80 en 2015 → 199 en 2024). |
| `energia_kwh` == 0 | 13 283 | Distribuidos a lo largo de todos los años. Ratio 13 283 / 490 753 ≈ 2.7 %. |
| `energia_kwh` > 0 | 476 279 | Distribución muy sesgada: máx = 1.12e8 kWh (Santiago Residencial BT1A, 2019-08). |
| `clientes_facturados` == 0 | 6 623 | Cuando `cf == 0`, `energia_kwh` mediana = 0 → el grupo "sin clientes" coincide con "sin energía". |
| `clientes_facturados` < 0 | 1 | Valor `-10` (error claro, fila única). |
| `clientes_facturados` NaN | 1 | Una sola fila. |
| Duplicados sobre clave `(fecha, region, comuna, tipo_clientes, tarifa)` | 5 275 filas en 4 990 grupos | **NO son duplicados verdaderos**: en 4 987/4 990 grupos `energia_kwh` y `clientes_facturados` difieren entre filas. La clave panel asumida no es única. |
| Consistencia `energia_kwh ≈ e1 + e2` | 441 198 / 443 025 (filas con e1 y e2 no nulos) | Diferencia residual `|Δ| ≤ 1` por redondeo float→int. Sólido. |

## 2. ¿Qué podría significar cada anomalía?

### 2.1 `energia_kwh` negativos
**Hipótesis plausibles** (no verificadas con la fuente operativa):
- **Refacturaciones / ajustes contables**: cuando una distribuidora corrige una facturación previa, registra el contra-asiento. Coherente con la concentración en tarifas industriales (clientes con consumos grandes y reliquidaciones más frecuentes).
- **Inyección neta de generación distribuida (net billing)**: clientes con paneles solares que en algunos meses inyectaron más de lo que consumieron. Coherente con el crecimiento sostenido (80 → 199 por año entre 2015 y 2024) que acompaña el despliegue de PMGD.
- **Errores de medición o de carga**: minoría plausible.

### 2.2 `energia_kwh` cero
**Hipótesis plausibles**:
- Filas con `clientes_facturados == 0` (6 623 casos) — combinación geográfica × tarifa que ese mes no tuvo clientes activos. Coherente.
- Reporte vacío de la distribuidora codificado como cero (en lugar de NaN).
- Mes con corte total de servicio en una comuna pequeña.

### 2.3 Duplicados sobre clave panel
- Los 5 275 registros sobre la misma `(fecha, region, comuna, tipo_clientes, tarifa)` con valores distintos sugieren que **falta una dimensión** en la clave (p. ej. distribuidora / concesión / nivel de submedida) que el dataset original no expuso. La dimensión exacta es desconocida sin acceso a la fuente operativa.

## 3. Recomendación para Presentación 1

**Principio: no transformar el dataset limpio. Documentar y crear vistas filtradas para el modelado.**

### 3.1 Tratamiento sugerido

| Anomalía | Decisión Presentación 1 | Justificación |
|---|---|---|
| `energia_kwh < 0` | Reportar conteo, NO eliminar de `facturacion_clean.parquet`. Crear *vista* `energia_kwh > 0` para el modelo, comparar con escenario sin filtrado. | Eliminarlas en limpio borraría la señal de net billing/refacturaciones, que es real. |
| `energia_kwh == 0` | Mantener. Mencionar en EDA. Los ceros son "no consumo", no errores. | El target puede tomar 0 legítimamente. |
| Outliers extremos (>1e8 kWh) | Mantener. Son consumos reales de comunas grandes (Santiago, Las Condes, Maipú) en Residencial BT1A. | Verificado caso por caso: corresponden a comunas pobladas en meses de invierno. |
| `clientes_facturados ≤ 0` | Filtrar en el escenario de modelado, mantener en `clean`. | Sin clientes no hay facturación interpretable; introduce ruido al ajustar. |
| `clientes_facturados` NaN (1) | Imputar con mediana en pipeline (ya hecho). | Cantidad despreciable. |
| Duplicados de clave panel | **Documentar como limitación**. No agregar (sumar) sin entender la dimensión faltante. | Sumar puede deformar el target; podríamos estar agregando dos sub-categorías legítimas. |
| `e1_kwh`, `e2_kwh` nulos (1 368 / 47 728) | Mantener. No son inputs del modelo principal. | Sólo se usa `energia_kwh` como target/feature. |

### 3.2 Vista de modelado recomendada para Presentación 1

Construir, **sólo en el script de modelado**, la cohorte:

```
modelable = clean[(clean['energia_kwh'] > 0) &
                  (clean['clientes_facturados'] > 0)]
```

Esto da una cohorte bien definida y reproducible sin tocar archivos. El reporte debe incluir el escenario "con filtrado" como variante adicional.

### 3.3 Lo que se deja para la próxima entrega

- Investigar la dimensión faltante en la clave panel (distribuidora / concesión).
- Estrategia formal de imputación / log-transformación del target.
- Revisión con la fuente sobre el origen de los negativos (refacturación vs net billing).
- Tratamiento explícito de outliers extremos (winsorización vs log).

## 4. Resumen ejecutivo

- El dataset limpio **no es estrictamente único** sobre la clave panel asumida; afecta sólo a ~1 % de las filas pero debe declararse.
- Los negativos y ceros son menores en proporción (≈3 % combinado) y **plausiblemente legítimos**; eliminarlos en limpio sería una decisión irreversible.
- Para la Presentación 1 se recomienda **mantener `clean` intacto** y construir una *vista filtrada* sólo dentro del pipeline de modelado, comparándola con el escenario sin filtro.
- Pregunta abierta: cuál es la dimensión faltante que explicaría los 4 990 grupos no únicos en la clave panel.
