import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Asistente de Trading Deportivo",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado con CSS
# CORRECCIÓN: El parámetro correcto es unsafe_allow_html=True
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1.1rem; color: #4B5563; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚽ Asistente de Trading Deportivo</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Estrategia de Cobertura Asimétrica y Dutching para Minimizar Riesgos</div>', unsafe_allow_html=True)

# Barra lateral - Gestión de Banca
st.sidebar.header("💰 Gestión de Banca")
banca_total = st.sidebar.number_input("Banca Total ($)", min_value=10.0, value=1000.0, step=50.0)
pct_stake = st.sidebar.slider("Porcentaje de Stake Sugerido (%)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)

stake_calculado = banca_total * (pct_stake / 100.0)
st.sidebar.info(f"👉 Stake recomendado (base): **${stake_calculado:.2f}**")

# Cuerpo principal - Calculadora
col_inputs, col_strategy = st.columns([1, 1])

with col_inputs:
    st.subheader("📥 Datos de las Apuestas")
    st.markdown("**1ª Apuesta (Pre-partido / No Favorito)**")
    stake_1 = st.number_input("Monto Apostado ($) [S1]", min_value=1.0, value=float(round(stake_calculado, 2)), step=5.0)
    cuota_1 = st.number_input("Cuota de la 1ª Apuesta [O1]", min_value=1.01, value=1.90, step=0.05)
    
    st.markdown("---")
    st.markdown("**2ª Apuesta (En Vivo / Cobertura Favorito)**")
    cuota_2 = st.number_input("Cuota Actual del Favorito en Vivo [O2]", min_value=1.01, value=2.50, step=0.05)
    
    tipo_estrategia = st.radio("Selecciona el Tipo de Cobertura:", ("Riesgo Cero en Cobertura (Tablas)", "Ganancia Igualada (Dutching)"))

# Cálculos Matemáticos
if tipo_estrategia == "Riesgo Cero en Cobertura (Tablas)":
    stake_2 = stake_1 / (cuota_2 - 1) if cuota_2 > 1.0 else 0.0
    inversion_total = stake_1 + stake_2
    retorno_1, beneficio_1 = (stake_1 * cuota_1), (stake_1 * cuota_1) - inversion_total
    retorno_2, beneficio_2 = (stake_2 * cuota_2), 0.0 # Riesgo Cero
else:
    # Dutching
    stake_2 = (stake_1 * cuota_1) / cuota_2
    inversion_total = stake_1 + stake_2
    retorno_1, beneficio_1 = (stake_1 * cuota_1), (stake_1 * cuota_1) - inversion_total
    retorno_2, beneficio_2 = retorno_1, beneficio_1

roi_1 = (beneficio_1 / inversion_total) * 100 if inversion_total > 0 else 0
roi_2 = (beneficio_2 / inversion_total) * 100 if inversion_total > 0 else 0

# Mostrar Resultados
with col_strategy:
    st.subheader("📊 Resultados de la Operación")
    st.markdown(f"### 🎯 Importe a colocar en Cobertura: **${stake_2:.2f}**")
    st.markdown(f"**Inversión Total Combinada:** ${inversion_total:.2f}")
    
    prob_implicita = (1/cuota_1) + (1/cuota_2)
    if prob_implicita < 1.0:
        st.success("🔥 ¡Arbitraje/Surebet detectado! Tienes ganancias garantizadas en cualquier escenario.")
    elif tipo_estrategia == "Ganancia Igualada (Dutching)" and beneficio_1 < 0:
        st.error("⚠️ Alerta: Las cuotas actuales generan pérdidas en este modo. Espera a que suba la cuota en vivo.")

    st.markdown("---")
    st.markdown("#### 🔄 Escenarios de Resultados:")
    col_esc1, col_esc2 = st.columns(2)
    with col_esc1:
        st.markdown("**Si Gana la 1ª Apuesta**")
        st.metric("Beneficio Neto", f"${beneficio_1:.2f}", f"{roi_1:.1f}% ROI", delta_color="normal" if beneficio_1 >= 0 else "inverse")
    with col_esc2:
        st.markdown("**Si Gana la Cobertura**")
        st.metric("Beneficio Neto", f"${beneficio_2:.2f}", f"{roi_2:.1f}% ROI", delta_color="normal" if beneficio_2 >= 0 else "inverse")