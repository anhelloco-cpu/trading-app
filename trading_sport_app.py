import streamlit as st

st.set_page_config(page_title="Asistente de Trading (COP)", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .instruccion-final { background-color: #D1FAE5; padding: 20px; border-radius: 10px; border-left: 8px solid #10B981; font-size: 1.1rem; }
    .metric-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; height: 100%; }
    .alerta-roja { background-color: #FEE2E2; padding: 20px; border-radius: 10px; border-left: 8px solid #EF4444; font-size: 1.1rem; }
    .main-title { font-size: 2.2rem; color: #0F172A; font-weight: bold; margin-bottom: 0.2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 Asistente de Trading Deportivo (COP)</div>', unsafe_allow_html=True)

# Pestañas para tener ambas herramientas en la misma aplicación
tab1, tab2 = st.tabs(["🎯 Buscador de Cuota (En Vivo)", "📊 Análisis Estadístico (EV)"])

with tab1:
    st.write("Calcula la cuota que debes exigirle al mercado en vivo tras el primer gol para asegurar tu balance.")
    
    # --- SECCIÓN 1: INVERSIÓN BASE ---
    st.subheader("1️⃣ Tu Inversión Base (Al Favorito)")
    col1, col2 = st.columns(2)
    with col1:
        stake_1 = st.number_input("Capital Invertido (Mín. $5,000 COP) [S1]", min_value=5000, value=10000, step=1000)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial del Favorito [O1]", min_value=1.01, value=1.60, step=0.05)

    # --- SECCIÓN 2: PRESUPUESTO DE COBERTURA ---
    st.markdown("---")
    st.subheader("2️⃣ Tu Presupuesto de Cobertura")
    st.write("¿Cuánto capital estás dispuesto a inyectar al 'Empate o Visitante' para cubrirte cuando el favorito anote?")
    stake_2 = st.number_input("Capital de Cobertura (Mín. $5,000 COP) [S2]", min_value=5000, value=5000, step=1000)

    # --- MATEMÁTICA INVERSA (Cálculo de Cuotas) ---
    inversion_total = stake_1 + stake_2
    retorno_favorito = stake_1 * cuota_1
    beneficio_bruto_favorito = retorno_favorito - inversion_total

    # Prevención de división por cero
    if stake_2 > 0:
        cuota_objetivo_cero = inversion_total / stake_2
        cuota_objetivo_igualada = retorno_favorito / stake_2
    else:
        cuota_objetivo_cero = 0
        cuota_objetivo_igualada = 0

    # --- DICTAMEN FINAL ---
    st.markdown("---")
    st.subheader("📋 DICTAMEN DE OPERACIÓN Y CUOTAS A CAZAR")

    # Validación: Si la inversión supera el pago del favorito, es pérdida segura.
    if beneficio_bruto_favorito < 0:
        st.markdown(f"""
        <div class="alerta-roja">
            <b>🚨 ALERTA DE DÉFICIT:</b> Invertirías ${inversion_total:,.0f} COP en total, pero si el Favorito gana solo cobrarías ${retorno_favorito:,.0f} COP.<br>
            <i>Solución: Necesitas subir tu inversión al Favorito (S1) o elegir una cuota inicial más alta.</i>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**Capital Total Comprometido:** ${inversion_total:,.0f} COP")
        
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            st.markdown(f"""
            <div class="metric-caja">
                <h4 style="color: #475569;">Opción A: Riesgo Cero (Salvar Capital)</h4>
                <p>Para recuperar exactamente tus ${inversion_total:,.0f} COP si ocurre una sorpresa, la cuota debe llegar mínimo a:</p>
                <h1 style="color: #0F172A; font-size: 3rem; margin: 0;">{cuota_objetivo_cero:.2f}</h1>
                <hr>
                <p style="margin-bottom: 0;"><b>Si Favorito Gana:</b> Utilidad de ${beneficio_bruto_favorito:,.0f} COP</p>
                <p style="margin-top: 0;"><b>Si Visitante Empata/Gana:</b> Tablas ($0 COP)</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_res2:
            st.markdown(f"""
            <div class="metric-caja">
                <h4 style="color: #059669;">Opción B: Ganancia Igualada (Ideal)</h4>
                <p>Para ganar la misma utilidad sin importar el equipo que gane, la cuota debe llegar mínimo a:</p>
                <h1 style="color: #059669; font-size: 3rem; margin: 0;">{cuota_objetivo_igualada:.2f}</h1>
                <hr>
                <p style="margin-bottom: 0;"><b>Si Favorito Gana:</b> Utilidad de ${beneficio_bruto_favorito:,.0f} COP</p>
                <p style="margin-top: 0;"><b>Si Visitante Empata/Gana:</b> Utilidad de ${beneficio_bruto_favorito:,.0f} COP</p>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("Análisis Probabilístico y Valor Esperado (EV)")
    st.write("Audita las cuotas de la casa de apuestas frente a tu propia estimación estadística para saber si hay valor real.")
    
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.markdown("#### Datos de la Casa de Apuestas")
        cuota_evaluar = st.number_input("Cuota a evaluar", min_value=1.01, value=2.00, step=0.05)
        prob_implicita = (1 / cuota_evaluar) * 100
        st.info(f"📊 **Probabilidad Implícita:** La casa de apuestas estima que este evento tiene un **{prob_implicita:.2f}%** de probabilidad de ocurrir.")
        
    with col_stat2:
        st.markdown("#### Tu Análisis (Realidad)")
        prob_real = st.number_input("Probabilidad Real Estimada (%)", min_value=1.0, max_value=99.9, value=55.0, step=1.0)
        
        prob_ganar_dec = prob_real / 100.0
        prob_perder_dec = 1.0 - prob_ganar_dec
        ganancia_neta_unidad = cuota_evaluar - 1.0
        
        ev = (prob_ganar_dec * ganancia_neta_unidad) - prob_perder_dec
        ev_porcentaje = ev * 100
        
        if ev > 0:
            st.success(f"📈 **Valor Esperado (EV+): {ev_porcentaje:.2f}%** \n\nA largo plazo, por cada $100 apostados ganarás ${ev_porcentaje:.2f}. Esta es una operación matemáticamente rentable.")
        else:
            st.error(f"📉 **Valor Esperado (EV-): {ev_porcentaje:.2f}%** \n\nA largo plazo, perderás dinero con esta operación. La cuota es demasiado baja para el riesgo.")