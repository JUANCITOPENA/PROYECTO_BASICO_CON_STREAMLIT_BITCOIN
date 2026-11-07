import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Crypto Executive Dashboard",
    page_icon="📈",
    layout="wide"
)

# ==========================================
# FILTROS EN BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Parámetros de Análisis")

simbolo = st.sidebar.selectbox(
    "Selecciona el Activo:",
    options=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
    index=0
)

intervalo = st.sidebar.selectbox(
    "Temporalidad (Intervalo):",
    options=["1d", "4h", "1h", "1w"],
    index=0
)

limite = st.sidebar.slider(
    "Horizonte temporal (Número de velas):",
    min_value=30,
    max_value=365,
    value=90,
    step=5
)

st.sidebar.subheader("Indicadores Técnicos")
sma_rapida = st.sidebar.number_input("Periodo SMA Rápida", min_value=5, max_value=50, value=20)
sma_lenta = st.sidebar.number_input("Periodo SMA Lenta", min_value=20, max_value=200, value=50)

# ==========================================
# EXTRACCIÓN Y CACHÉ DE DATOS
# ==========================================
@st.cache_data(ttl=300)
def obtener_datos(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    raw = response.json()
    
    cols = ["OpenTime", "Open", "High", "Low", "Close", "Volume"]
    df = pd.DataFrame(raw).iloc[:, :6]
    df.columns = cols
    
    df["Fecha"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df[cols[1:]] = df[cols[1:]].astype(float)
    return df

# Carga de datos con manejo de errores
try:
    with st.spinner("Descargando datos desde Binance API..."):
        df = obtener_datos(simbolo, intervalo, limite)
except Exception as e:
    st.error(f"Error al conectar con la API de Binance: {e}")
    st.stop()

# ==========================================
# PROCESAMIENTO DE MÉTRICAS
# ==========================================
df["SMA_Fast"] = df["Close"].rolling(sma_rapida).mean()
df["SMA_Slow"] = df["Close"].rolling(sma_lenta).mean()
df["Retorno_Acum_%"] = ((df["Close"] / df["Close"].iloc[0]) - 1) * 100

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

# Métricas actuales
p_act = df["Close"].iloc[-1]
p_prev = df["Close"].iloc[-2]
var_dia = ((p_act / p_prev) - 1) * 100
ret_tot = df["Retorno_Acum_%"].iloc[-1]
rsi_act = df["RSI"].iloc[-1]

# ==========================================
# RENDERIZADO EN STREAMLIT
# ==========================================
st.title(f"📊 Dashboard Ejecutivo: {simbolo}")
st.caption(f"Análisis sobre las últimas {limite} velas (Intervalo: {intervalo}) al {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Fila de métricas clave (KPIs)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Precio Actual", f"${p_act:,.2f}", f"{var_dia:+.2f}%")
kpi2.metric("Retorno Acumulado", f"{ret_tot:+.2f}%")
kpi3.metric("Rango del Periodo", f"${df['High'].max():,.0f}", f"Mín: ${df['Low'].min():,.0f}")
kpi4.metric("RSI Actual (14)", f"{rsi_act:.1f}")

# Renderizado de Gráficos (Matplotlib)
fig, ax = plt.subplots(2, 2, figsize=(16, 9))
fig.patch.set_facecolor("#0e1117" if st.get_option("theme.base") == "dark" else "#f8f9fa")

# Panel 1: Estructura de Tendencia
ax[0, 0].fill_between(df["Fecha"], df["Low"], df["High"], color="#3498db", alpha=0.15, label="Rango (H-L)")
ax[0, 0].plot(df["Fecha"], df["Close"], label="Precio Cierre", color="#2c3e50", lw=2)
ax[0, 0].plot(df["Fecha"], df["SMA_Fast"], label=f"SMA {sma_rapida}", color="#e67e22", ls="--")
ax[0, 0].plot(df["Fecha"], df["SMA_Slow"], label=f"SMA {sma_lenta}", color="#27ae60", ls="--")
ax[0, 0].set_title(f"1. Estructura de Tendencia: Precio vs Medias Móviles", fontweight="bold")

# Panel 2: Rendimiento Acumulado
ax[0, 1].fill_between(df["Fecha"], df["Retorno_Acum_%"], 0, where=(df["Retorno_Acum_%"] >= 0), color="#2ecc71", alpha=0.3, label="Ganancia")
ax[0, 1].fill_between(df["Fecha"], df["Retorno_Acum_%"], 0, where=(df["Retorno_Acum_%"] < 0), color="#e74c3c", alpha=0.3, label="Pérdida")
ax[0, 1].plot(df["Fecha"], df["Retorno_Acum_%"], color="#2c3e50", lw=1.8)
ax[0, 1].axhline(0, color="gray", ls=":", lw=1.2)
ax[0, 1].set_title(f"2. Rendimiento Acumulado ({ret_tot:+.2f}%)", fontweight="bold")

# Panel 3: Volumen
colores_vol = ["#2ecc71" if c >= o else "#e74c3c" for c, o in zip(df["Close"], df["Open"])]
ax[1, 0].bar(df["Fecha"], df["Volume"], color=colores_vol, width=0.8, alpha=0.85)
ax[1, 0].plot(df["Fecha"], df["Volume"].rolling(14).mean(), color="#8e44ad", lw=1.8, label="Media Vol 14")
ax[1, 0].set_title("3. Flujo de Volumen: Comprador (Verde) vs Vendedor (Rojo)", fontweight="bold")

# Panel 4: RSI
ax[1, 1].plot(df["Fecha"], df["RSI"], color="#8e44ad", lw=1.8, label="RSI 14")
ax[1, 1].axhline(70, color="#c0392b", ls="--", alpha=0.8, label="Sobrecompra (>70)")
ax[1, 1].axhline(30, color="#27ae60", ls="--", alpha=0.8, label="Sobreventa (<30)")
ax[1, 1].fill_between(df["Fecha"], 70, 30, color="gray", alpha=0.08)
ax[1, 1].set(ylim=(10, 90), title=f"4. Momentum de Mercado (RSI: {rsi_act:.1f})")

# Formateo visual común
for a in ax.flat:
    a.set_facecolor("#ffffff")
    a.grid(alpha=0.25, ls="--")
    a.legend(loc="upper left", fontsize=8, framealpha=0.8)
    a.xaxis.set_major_formatter(mdates.DateFormatter('%d/%b'))
    a.tick_params(axis="x", rotation=25)

plt.tight_layout()
st.pyplot(fig)

# Tabla opcional de datos crudos
with st.expander("🔍 Explorar Datos en Bruto"):
    st.dataframe(
        df[["Fecha", "Open", "High", "Low", "Close", "Volume", "Retorno_Acum_%", "RSI"]].sort_values(by="Fecha", ascending=False),
        use_container_width=True
    )