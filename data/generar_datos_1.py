"""
generar_datos.py
Genera un dataset simulado de movimientos de tesorería bancaria.
Exporta: movimientos.csv y productos.csv
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import random

random.seed(42)
np.random.seed(42)

# --- Parámetros ---
FECHA_INICIO = date(2024, 1, 1)
FECHA_FIN    = date(2024, 12, 31)
N_REGISTROS  = 500

# --- Catálogos ---
PRODUCTOS = {
    1: "Depósito a Plazo",
    2: "Overnight",
    3: "Cuenta Corriente",
    4: "Repo",
    5: "Línea de Crédito"
}

MONEDAS = ["PEN", "USD"]

TIPOS_OP = ["ingreso", "egreso"]

CONTRAPARTES = [
    "BCP", "BBVA", "Interbank", "Scotiabank",
    "Citibank", "BCRP", "Cliente A", "Cliente B", "Cliente C"
]

# --- Generar fechas (solo días hábiles lunes-viernes) ---
fechas_habiles = []
d = FECHA_INICIO
while d <= FECHA_FIN:
    if d.weekday() < 5:  # 0=lun ... 4=vie
        fechas_habiles.append(d)
    d += timedelta(days=1)

# --- Construir registros ---
registros = []
for i in range(1, N_REGISTROS + 1):
    fecha      = random.choice(fechas_habiles)
    producto_id = random.choice(list(PRODUCTOS.keys()))
    tipo_op    = random.choice(TIPOS_OP)
    moneda     = random.choices(MONEDAS, weights=[0.6, 0.4])[0]

    # Montos realistas por producto
    if producto_id == 2:   # Overnight → montos grandes
        monto = round(random.uniform(500_000, 5_000_000), 2)
    elif producto_id == 4: # Repo
        monto = round(random.uniform(200_000, 2_000_000), 2)
    elif producto_id == 1: # Depósito a Plazo
        monto = round(random.uniform(50_000, 1_000_000), 2)
    else:
        monto = round(random.uniform(5_000, 300_000), 2)

    contraparte = random.choice(CONTRAPARTES)

    registros.append({
        "id_movimiento" : i,
        "fecha"         : fecha,
        "producto_id"   : producto_id,
        "tipo_operacion": tipo_op,
        "monto"         : monto,
        "moneda"        : moneda,
        "contraparte"   : contraparte,
        "descripcion"   : f"{PRODUCTOS[producto_id]} - {contraparte}"
    })

df = pd.DataFrame(registros).sort_values("fecha").reset_index(drop=True)

# --- Tabla de productos (para el JOIN en SQL) ---
df_productos = pd.DataFrame([
    {"producto_id": k, "nombre_producto": v}
    for k, v in PRODUCTOS.items()
])

# --- Exportar ---
df.to_csv("data/movimientos.csv", index=False)
df_productos.to_csv("data/productos.csv", index=False)

print(f"✅ movimientos.csv  → {len(df)} registros")
print(f"✅ productos.csv    → {len(df_productos)} registros")
print("\nPrimeras filas:")
print(df.head())
