import streamlit as st

st.set_page_config(page_title="Calculadora Trading COP", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .instruccion-final { background-color: #D1FAE5; padding: 20px; border-radius: 10px; border-left: 8px solid #10B981; font-size: 1.2rem; }
    .alerta-roja { background-color: #FEE2E2; padding: 20px; border-radius: 10px; border-left: 8px solid #EF4444; font-size: 1.2rem; }
    .metric-caja { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Calculadora de Cobertura a Favor (COP)")
st.write("Estrategia: Entrar a favor de la probabilidad (Favorito) y cubrir utilidades tras el primer gol.")

# --- SECCIÓN 1: EL INGRESO BASE ---
st.subheader("1️⃣ Tu Apuesta Base (Pre-partido)")
st.write("Apuesta a la **Victoria Simple del Favorito** antes de que inicie el partido.")
col1, col2 = st.columns(2)
with col1:
    stake_1 = st.number_input("Capital Invertido (Mín. $5,000 COP) [S1]", min_value=5000, value=10000, step=1000)
with col2:
    cuota_1 = st.number_input("Cuota del Favorito [O1]", min_value=1.01, value=1.60, step=0.05)

# --- SECCIÓN 2: LA COBERTURA EN VIVO ---
st.markdown("---")
st.subheader("2️⃣ Ejecución de Cobertura (En Vivo tras el gol)")
st.write("El favorito hizo gol. Ahora busca la opción **Doble Oportunidad (Empate o Visitante)** e ingresa su nueva cuota.")

cuota_2 = st.number_input("Cuota Actual (Empate o Visitante) [O2]", min_value=1.01, value=3.50, step=0.10)

estrategia = st.radio(
    "Selecciona tu modelo de cuadre:",
    [
        "Ganancia Igualada: Misma utilidad neta sin importar el resultado.",
        "Riesgo Cero (Free Bet): Recuperas la inversión si hay sorpresa, maximizas ganancia si gana el favorito."
    ]
)

# --- MATEMÁTICA Y CONCILIACIÓN ---
if "Ganancia Igualada" in estrategia:
    stake_2 = (stake_1 * cuota_1) / cuota_2
    inversion_total = stake_1 + stake_2
    retorno_1 = stake_1 * cuota_1
    retorno_2 = stake_2 * cuota_2
else:
    stake_2 = stake_1 / (cuota_2 - 1) if cuota_2 > 1.0 else 0
    inversion_total = stake_1 + stake_2
    retorno_1 = stake_1 * cuota_1
    retorno_2 = stake_2 * cuota_2

beneficio_1 = retorno_1 - inversion_total
beneficio_2 = retorno_2 - inversion_total

# --- DICTAMEN FINAL ---
st.markdown("---")
st.subheader("📋 DICTAMEN DE OPERACIÓN")

# Validación de restricciones operativas
if beneficio_1 < 0 and beneficio_2 <= 0:
    st.markdown(f"""
    <div class="alerta-roja">
        <b>🚨 DÉFICIT MATEMÁTICO:</b> Las cuotas no dan margen. Si cubres ahora, la inversión total (${inversion_total:,.0f} COP) superará los retornos.
    </div>
    """, unsafe_allow_html=True)
elif stake_2 > 0 and stake_2 < 5000:
    st.markdown(f"""
    <div class="alerta-roja">
        <b>⚠️ ALERTA DE LÍMITE MÍNIMO:</b> El cálculo exige apostar ${stake_2:,.0f} COP, pero la casa exige $5,000 COP mínimo.<br>
        <i>Solución: Necesitas aumentar tu apuesta base (S1) para que el porcentaje de cobertura supere los $5,000 COP.</i>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="instruccion-final">
        <b>👉 MONTO EXACTO A CUBRIR:</b> ${stake_2:,.0f} COP a la cuota de {cuota_2}.<br>
        <b>💰 CAPITAL TOTAL COMPROMETIDO:</b> ${inversion_total:,.0f} COP.
    </div>
    """, unsafe_allow_html=True)
    
    st.write("### Balance Final Proyectado")
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown(f"""
        <div class="metric-caja">
            <h4>Si el Favorito Gana</h4>
            <p>Ingresos Brutos: ${retorno_1:,.0f} COP</p>
            <p style="color: #059669; font-weight: bold; font-size: 1.1rem;">Utilidad Neta: ${beneficio_1:,.0f} COP</p>
        </div>
        """, unsafe_allow_html=True)
    with col_res2:
        st.markdown(f"""
        <div class="metric-caja">
            <h4>Si el Visitante Empata o Remonta</h4>
            <p>Ingresos Brutos: ${retorno_2:,.0f} COP</p>
            <p style="color: {'#059669' if beneficio_2 > 0 else '#475569'}; font-weight: bold; font-size: 1.1rem;">Utilidad Neta: ${beneficio_2:,.0f} COP</p>
        </div>
        """, unsafe_allow_html=True)