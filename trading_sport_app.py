import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Asistente de Trading Cuantitativo", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; color: #0F172A; font-weight: bold; margin-bottom: 0.2rem; }
    .subtitle { font-size: 1.1rem; color: #475569; margin-bottom: 2rem; }
    .highlight { background-color: #E2E8F0; padding: 15px; border-radius: 8px; border-left: 5px solid #3B82F6; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 Asistente de Trading Cuantitativo</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Cálculo de Cuota Objetivo, Análisis Estadístico y Valor Esperado (EV)</div>', unsafe_allow_html=True)

# Tabs para dividir la herramienta
tab1, tab2 = st.tabs(["🎯 Cazador de Cuota Objetivo", "📊 Análisis Estadístico (EV)"])

with tab1:
    st.markdown("### 1. Planificación de la Cobertura Pre-Partido")
    st.write("Ingresa los datos de tu apuesta inicial para conciliar los escenarios y determinar qué cuota necesitas cazar en vivo.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        stake_1 = st.number_input("Monto Apuesta Inicial ($) [S1]", min_value=1.0, value=50.0, step=5.0)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial (No Favorito) [O1]", min_value=1.01, value=1.90, step=0.05)
    with col3:
        # Qué porcentaje del beneficio potencial estás dispuesto a usar para cubrirte
        riesgo_cobertura = st.slider("Sacrificio de Beneficio para Cobertura (%)", 50, 100, 100, 
                                     help="100% significa que usarás toda tu ganancia potencial para cubrir el riesgo a cero.")

    # Matemáticas del Cazador de Cuotas
    beneficio_bruto = stake_1 * cuota_1
    ganancia_neta_potencial = beneficio_bruto - stake_1
    
    # Presupuesto máximo para la segunda apuesta (S2)
    presupuesto_cobertura = ganancia_neta_potencial * (riesgo_cobertura / 100.0)
    
    # Cálculo de la cuota mínima necesaria para no tener pérdidas
    if presupuesto_cobertura > 0:
        cuota_objetivo = (stake_1 + presupuesto_cobertura) / presupuesto_cobertura
    else:
        cuota_objetivo = 0.0

    st.markdown("---")
    st.markdown("### 2. Tu Plan de Ejecución en Vivo")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown(f"""
        <div class="highlight">
            <h4>💰 Presupuesto de Cobertura Exacto</h4>
            <p>Si tu primera apuesta acierta, tu ganancia neta sería de <b>${ganancia_neta_potencial:.2f}</b>.</p>
            <p>El monto máximo que puedes apostar al Favorito en vivo (S2) sin generar pérdidas globales es: <br>
            <span style="font-size: 24px; font-weight: bold; color: #DC2626;">${presupuesto_cobertura:.2f}</span></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_res2:
        st.markdown(f"""
        <div class="highlight">
            <h4>🎯 Cuota Mínima a Cazar (Target Odds)</h4>
            <p>Para recuperar toda tu inversión (${stake_1:.2f} + ${presupuesto_cobertura:.2f}), la cuota del Favorito en vivo DEBE subir hasta llegar como mínimo a:</p>
            <span style="font-size: 32px; font-weight: bold; color: #059669;">{cuota_objetivo:.2f}</span>
            <p><small><i>Si la cuota no llega a este valor, NO debes ejecutar la cobertura porque matemáticamente perderás dinero.</i></small></p>
        </div>
        """, unsafe_allow_html=True)


with tab2:
    st.markdown("### Análisis Probabilístico y Valor Esperado (EV)")
    st.write("Audita las cuotas de la casa de apuestas frente a tu propia estimación estadística para saber si hay valor real en el mercado.")
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.markdown("#### Datos de la Casa de Apuestas")
        cuota_evaluar = st.number_input("Cuota a evaluar", min_value=1.01, value=2.00, step=0.05)
        prob_implicita = (1 / cuota_evaluar) * 100
        st.info(f"📊 **Probabilidad Implícita:** La casa de apuestas estima que este evento tiene un **{prob_implicita:.2f}%** de probabilidad de ocurrir.")
        
    with col_stat2:
        st.markdown("#### Tu Análisis (Realidad)")
        prob_real = st.number_input("Probabilidad Real Estimada (%)", min_value=1.0, max_value=99.9, value=55.0, step=1.0)
        
        # Fórmula de Valor Esperado (EV) = (Probabilidad de Ganar * Ganancia Neta) - (Probabilidad de Perder * Stake)
        # Asumimos stake de 1 unidad para simplificar
        prob_ganar_dec = prob_real / 100.0
        prob_perder_dec = 1.0 - prob_ganar_dec
        ganancia_neta_unidad = cuota_evaluar - 1.0
        
        ev = (prob_ganar_dec * ganancia_neta_unidad) - prob_perder_dec
        ev_porcentaje = ev * 100
        
        if ev > 0:
            st.success(f"📈 **Valor Esperado (EV+): {ev_porcentaje:.2f}%** \n\nA largo plazo, por cada $100 apostados ganarás ${ev_porcentaje:.2f}. Esta es una operación matemáticamente rentable.")
        else:
            st.error(f"📉 **Valor Esperado (EV-): {ev_porcentaje:.2f}%** \n\nA largo plazo, perderás dinero con esta operación. La cuota es demasiado baja para el riesgo.")