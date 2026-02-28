"""
reporte_tesoreria.py
====================
Automatización de reportes operativos de tesorería.

Flujo:
  1. Lee movimientos.csv y productos.csv
  2. Limpieza y validación de datos
  3. Calcula KPIs: flujo neto diario, saldo acumulado,
     resumen por producto, top contrapartes, alertas
  4. Exporta reporte Excel con múltiples hojas y formato
  5. Imprime resumen ejecutivo en consola

Uso:
  python reporte_tesoreria.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# ── 0. Configuración ────────────────────────────────────────
RUTA_MOVIMIENTOS = "data/movimientos.csv"
RUTA_PRODUCTOS   = "data/productos.csv"
FECHA_HOY        = datetime.today().strftime("%Y-%m-%d")
NOMBRE_REPORTE   = f"reporte_tesoreria_{FECHA_HOY}.xlsx"


# ── 1. Carga de datos ────────────────────────────────────────
def cargar_datos():
    print("📂 Cargando datos...")
    df = pd.read_csv(RUTA_MOVIMIENTOS, parse_dates=["fecha"])
    productos = pd.read_csv(RUTA_PRODUCTOS)
    df = df.merge(productos, on="producto_id", how="left")
    print(f"   ✔ {len(df)} movimientos cargados")
    return df


# ── 2. Limpieza y validación ─────────────────────────────────
def limpiar_datos(df):
    print("🧹 Limpiando datos...")
    registros_antes = len(df)

    # Eliminar duplicados
    df = df.drop_duplicates(subset="id_movimiento")

    # Eliminar nulos en columnas críticas
    df = df.dropna(subset=["fecha", "monto", "tipo_operacion", "moneda"])

    # Asegurar tipos correctos
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.dropna(subset=["monto"])

    # Estandarizar texto
    df["tipo_operacion"] = df["tipo_operacion"].str.lower().str.strip()
    df["moneda"]         = df["moneda"].str.upper().str.strip()

    # Columna auxiliar: monto con signo (ingresos +, egresos -)
    df["monto_neto"] = df.apply(
        lambda r: r["monto"] if r["tipo_operacion"] == "ingreso" else -r["monto"],
        axis=1
    )

    registros_despues = len(df)
    eliminados = registros_antes - registros_despues
    print(f"   ✔ Limpieza completa. Registros eliminados: {eliminados}")
    return df


# ── 3. Cálculo de KPIs ───────────────────────────────────────
def calcular_kpis(df):
    print("📊 Calculando KPIs...")

    # 3.1 Flujo neto diario por moneda
    flujo_diario = (
        df.groupby(["fecha", "moneda"])
        .agg(
            total_ingresos=("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "ingreso"].sum()),
            total_egresos =("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "egreso"].sum()),
            flujo_neto    =("monto_neto", "sum"),
            n_operaciones =("id_movimiento", "count")
        )
        .reset_index()
        .sort_values(["fecha", "moneda"])
    )

    # 3.2 Saldo acumulado por moneda
    flujo_diario["saldo_acumulado"] = flujo_diario.groupby("moneda")["flujo_neto"].cumsum()

    # 3.3 Resumen por producto
    por_producto = (
        df.groupby(["nombre_producto", "moneda"])
        .agg(
            n_operaciones  =("id_movimiento", "count"),
            total_ingresos =("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "ingreso"].sum()),
            total_egresos  =("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "egreso"].sum()),
            monto_promedio =("monto", "mean")
        )
        .reset_index()
        .sort_values("total_ingresos", ascending=False)
    )
    por_producto["monto_promedio"] = por_producto["monto_promedio"].round(2)

    # 3.4 Top 10 contrapartes
    top_contrapartes = (
        df.groupby("contraparte")
        .agg(
            n_operaciones=("id_movimiento", "count"),
            volumen_total=("monto", "sum"),
            monto_promedio=("monto", "mean")
        )
        .reset_index()
        .sort_values("volumen_total", ascending=False)
        .head(10)
    )
    top_contrapartes["monto_promedio"] = top_contrapartes["monto_promedio"].round(2)

    # 3.5 Alertas de liquidez (días con flujo neto PEN negativo)
    flujo_pen = flujo_diario[flujo_diario["moneda"] == "PEN"].copy()
    alertas = flujo_pen[flujo_pen["flujo_neto"] < 0][["fecha", "flujo_neto", "saldo_acumulado"]].copy()
    alertas["estado"] = "⚠ FLUJO NEGATIVO"
    alertas = alertas.sort_values("flujo_neto")

    # 3.6 Resumen mensual
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    resumen_mensual = (
        df.groupby(["mes", "moneda"])
        .agg(
            total_ingresos=("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "ingreso"].sum()),
            total_egresos =("monto", lambda x: x[df.loc[x.index, "tipo_operacion"] == "egreso"].sum()),
            flujo_neto    =("monto_neto", "sum")
        )
        .reset_index()
    )

    print("   ✔ KPIs calculados")
    return flujo_diario, por_producto, top_contrapartes, alertas, resumen_mensual


# ── 4. Exportar a Excel ──────────────────────────────────────
def exportar_excel(df_raw, flujo_diario, por_producto, top_contrapartes, alertas, resumen_mensual):
    print(f"📤 Exportando reporte: {NOMBRE_REPORTE}")

    with pd.ExcelWriter(NOMBRE_REPORTE, engine="openpyxl") as writer:

        # Hoja 1: Flujo Diario
        flujo_diario.to_excel(writer, sheet_name="Flujo Diario", index=False)

        # Hoja 2: Resumen Mensual
        resumen_mensual.to_excel(writer, sheet_name="Resumen Mensual", index=False)

        # Hoja 3: Por Producto
        por_producto.to_excel(writer, sheet_name="Por Producto", index=False)

        # Hoja 4: Top Contrapartes
        top_contrapartes.to_excel(writer, sheet_name="Top Contrapartes", index=False)

        # Hoja 5: Alertas
        if len(alertas) > 0:
            alertas.to_excel(writer, sheet_name="Alertas Liquidez", index=False)
        else:
            pd.DataFrame({"mensaje": ["Sin alertas en el período"]}).to_excel(
                writer, sheet_name="Alertas Liquidez", index=False
            )

        # Hoja 6: Data completa
        df_raw.drop(columns=["monto_neto", "mes"], errors="ignore").to_excel(
            writer, sheet_name="Data Completa", index=False
        )

    print(f"   ✔ Reporte exportado correctamente")


# ── 5. Resumen ejecutivo en consola ─────────────────────────
def imprimir_resumen(df, flujo_diario, alertas):
    pen = flujo_diario[flujo_diario["moneda"] == "PEN"]
    usd = flujo_diario[flujo_diario["moneda"] == "USD"]

    print("\n" + "="*55)
    print("  RESUMEN EJECUTIVO DE TESORERÍA")
    print(f"  Período: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    print("="*55)
    print(f"  Total operaciones  : {len(df):,}")
    print(f"  Días operativos    : {df['fecha'].nunique()}")
    print()
    print(f"  [PEN] Ingresos     : S/ {pen['total_ingresos'].sum():>18,.2f}")
    print(f"  [PEN] Egresos      : S/ {pen['total_egresos'].sum():>18,.2f}")
    print(f"  [PEN] Flujo neto   : S/ {pen['flujo_neto'].sum():>18,.2f}")
    print()
    print(f"  [USD] Ingresos     : $  {usd['total_ingresos'].sum():>18,.2f}")
    print(f"  [USD] Egresos      : $  {usd['total_egresos'].sum():>18,.2f}")
    print(f"  [USD] Flujo neto   : $  {usd['flujo_neto'].sum():>18,.2f}")
    print()
    print(f"  Alertas liquidez   : {len(alertas)} día(s) con flujo PEN negativo")
    print("="*55)
    print(f"  Reporte generado   : {NOMBRE_REPORTE}")
    print("="*55 + "\n")


# ── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    inicio = datetime.now()

    df                  = cargar_datos()
    df                  = limpiar_datos(df)
    flujo_diario, por_producto, top_contrapartes, alertas, resumen_mensual = calcular_kpis(df)
    exportar_excel(df, flujo_diario, por_producto, top_contrapartes, alertas, resumen_mensual)
    imprimir_resumen(df, flujo_diario, alertas)

    segundos = (datetime.now() - inicio).total_seconds()
    print(f"⏱  Tiempo de ejecución: {segundos:.2f} segundos")
    print("✅ Proceso completado exitosamente.\n")
