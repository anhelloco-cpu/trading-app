import streamlit as st

st.set_page_config(page_title="Calculadora de Presupuesto Cerrado", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .paso-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;}
    .caja-librar { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px;}
    .caja-utilidad { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 5px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    </style>
""", unsafe_allow_html=True)

st.title("💰 Calculadora de Presupuesto Cerrado (COP)")
st.write("Asigna tu presupuesto total y la app te dirá cómo dividirlo y qué cuotas exactas debes cazar.")

# --- 1. CONFIGURACIÓN DEL CAPITAL TOTAL ---
st.subheader("1️⃣ Tu Presupuesto Total")
capital_total = st.number_input("¿Cuánto dinero en total vas a invertir en este partido? (Mínimo $10,000 COP)", 
                                min_value=10000, value=20000, step=1000)

# --- 2. LA PRIMERA APUESTA Y REPARTICIÓN ---
st.markdown("---")
st.subheader("2️⃣ La Cuota y Repartición del Dinero")
col1, col2 = st.columns(2)

with col1:
    cuota_1 = st.number_input("Cuota de tu Primera Apuesta", min_value=1.01, value=1.60, step=0.05)

with col2:
    max_apuesta_1 = capital_total - 5000
    st.write("¿Cómo quieres dividir el dinero?")
    stake_1 = st.slider(
        "Monto para la Primera Apuesta (El resto será tu reserva para cazar):", 
        min_value=5000, 
        max_value=max_apuesta_1, 
        value=max_apuesta_1, # Sugerimos enviar el máximo posible a la apuesta 1
        step=1000
    )

stake_2 = capital_total - stake_1

# --- 3. AUDITORÍA MATEMÁTICA ---
retorno_1 = stake_1 * cuota_1
utilidad_neta_1 = retorno_1 - capital_total

st.markdown("---")
st.subheader("📋 TU PLAN DE EJECUCIÓN")

if utilidad_neta_1 <= 0:
    st.markdown(f"""
    <div class="error-caja">
        <b>🚨 LOS NÚMEROS NO CUADRAN:</b><br>
        Si destinas ${stake_1:,.0f} a la primera apuesta (cuota {cuota_1}), tu pago sería de ${retorno_1:,.0f} COP.<br>
        Esto no alcanza a cubrir tu Presupuesto Total de ${capital_total:,.0f} COP.<br>
        <i>Ajusta el slider para ponerle más dinero a la Primera Apuesta o busca una cuota inicial más alta.</i>
    </div>
    """, unsafe_allow_html=True)
else:
    # Fórmulas de las cuotas a cazar
    cuota_para_librar = capital_total / stake_2
    cuota_para_utilidad = retorno_1 / stake_2

    st.markdown(f"""
    <div class="paso-caja">
        <h4 style="color: #0F172A;">Paso 1: Antes del partido (El Ingreso)</h4>
        <p>Ve a tu casa de apuestas e ingresa <b>${stake_1:,.0f} COP</b> a la cuota de <b>{cuota_1:.2f}</b>.</p>
        <p>Mantén tus otros <b>${stake_2:,.0f} COP</b> guardados en la cuenta como reserva.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Paso 2: En Vivo (La Caza)")
    st.write(f"Con los **${stake_2:,.0f} COP** que dejaste en reserva, abre el partido en vivo. Debes apostarlos SOLO si el equipo contrario llega a una de estas dos cuotas:")

    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown(f"""
        <div class="caja-librar">
            <h4 style="color: #1E3A8A; margin-top: 0;">🛡️ Escenario A: Solo para Librar</h4>
            <p>Para recuperar tu presupuesto completo (${capital_total:,.0f}) y salir sin pérdidas:</p>
            <h1 style="color: #1E3A8A; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_librar:.2f}</h1>
            <p style="font-size: 0.9rem; margin-top: 10px;">Si haces esto y el rival gana, recuperas tu plata. Si tu 1ra apuesta gana, te llevas ${utilidad_neta_1:,.0f} de ganancia limpia.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_res2:
        st.markdown(f"""
        <div class="caja-utilidad">
            <h4 style="color: #15803D; margin-top: 0;">💰 Escenario B: Para tener Utilidad</h4>
            <p>Para ganar equitativamente (${utilidad_neta_1:,.0f} limpios) gane quien gane:</p>
            <h1 style="color: #15803D; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_utilidad:.2f}</h1>
            <p style="font-size: 0.9rem; margin-top: 10px;">Matemáticamente perfecto. Si logras apostar tus ${stake_2:,.0f} COP a esta cuota, tu balance de caja cerrará en verde sí o sí.</p>
        </div>
        """, unsafe_allow_html=True)