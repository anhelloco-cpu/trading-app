import streamlit as st

st.set_page_config(page_title="Sistema de Trading y Auditoría COP", page_icon="⚖️", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .paso-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;}
    .caja-librar { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px;}
    .caja-utilidad { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 5px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    
    /* Nuevos estilos para el proyector de inversión */
    .caja-inversion { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px;}
    .caja-objetivo { background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 20px; border-radius: 8px;}
    .caja-conservadora { background-color: #EFF6FF; border-left: 6px solid #3B82F6; padding: 20px; border-radius: 8px;}
    </style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (SELECTOR DE MÓDULOS) ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Selecciona la estrategia a conciliar:",
    [
        "2️⃣ Estrategia 2: Paz Mental (Inversión Proyectada)",
        "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)",
        "➕ Nuevos Módulos (Próximamente)"
    ]
)

st.title("⚖️ Sistema de Trading y Cuadre de Caja")

# =====================================================================
# MÓDULO: ESTRATEGIA 2 (PAZ MENTAL + PROYECCIÓN DE UTILIDAD Y RIESGO)
# =====================================================================
if estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Inversión Proyectada)":
    
    st.markdown("### 📝 Definición del Módulo")
    st.info("**Lógica:** Proyectamos la rentabilidad. Define tu % de utilidad y tu nivel de riesgo. El sistema dividirá el capital automáticamente y te dirá qué cuota exacta cazar mientras trabajas con tranquilidad (ingresando primero a Favorito o Empate).")
    
    # --- 1. CONFIGURACIÓN DE LA INVERSIÓN ---
    st.subheader("1️⃣ Parámetros de la Inversión")
    col1, col2, col3 = st.columns(3)

    with col1:
        capital_total = st.number_input("Capital Total a Invertir (COP)", min_value=10000, value=50000, step=5000)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial (Favorito o Empate)", min_value=1.05, value=1.25, step=0.05)
    with col3:
        max_utilidad_teorica = (cuota_1 - 1.0) * 100.0
        # Evitar errores si la cuota es muy baja
        if max_utilidad_teorica <= 1.0: max_utilidad_teorica = 1.1 
        
        utilidad_esperada = st.slider(
            f"Utilidad Deseada (%) [Máx Teórico: {max_utilidad_teorica:.1f}%]", 
            min_value=1.0, 
            max_value=float(max_utilidad_teorica - 0.1), 
            value=min(10.0, float(max_utilidad_teorica - 0.1)), 
            step=0.5
        )

    # --- 2. CONFIGURACIÓN DEL RIESGO ---
    st.markdown("---")
    st.subheader("2️⃣ Perfil de Riesgo para la Cobertura (En Vivo)")
    st.write("¿Qué rendimiento exiges si la operación se voltea y gana el No Favorito? (Esto define tu cuota de entrada)")

    riesgo = st.slider(
        "Nivel de Exigencia en la Cobertura:",
        min_value=0, max_value=100, value=50, step=10,
        help="0% = Conservador (Solo salvar capital). 100% = Agresivo (Exigir la misma utilidad del escenario principal)."
    )

    col_r1, col_r2, col_r3 = st.columns([1,1,1])
    col_r1.write("📉 **0%** (Librar Inversión)")
    col_r2.write("⚖️ **50%** (Utilidad Parcial)")
    col_r3.write("📈 **100%** (Utilidad Total)", anchor="right")

    # --- 3. INGENIERÍA INVERSA Y CÁLCULOS ---
    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total

    # El algoritmo calcula exactamente cuánto apostar para lograr esa utilidad
    stake_1 = retorno_objetivo_1 / cuota_1
    stake_2 = capital_total - stake_1

    st.markdown("---")
    st.subheader("📋 DICTAMEN DE AUDITORÍA Y PLAN DE CAZA")

    if stake_2 < 5000:
        st.markdown(f"""
        <div class="error-caja">
            <b>🚨 RESTRICCIÓN DE LIQUIDEZ (LÍMITE DE LA CASA):</b><br>
            Para lograr un {utilidad_esperada}% de utilidad con esta cuota, el algoritmo determina que tu reserva debe ser de ${stake_2:,.0f} COP.<br>
            <i>Sin embargo, la casa de apuestas exige un mínimo de $5,000 COP.</i><br><br>
            <b>Solución:</b> Necesitas aumentar tu Capital Total o disminuir tu expectativa de Utilidad Deseada (%).
        </div>
        """, unsafe_allow_html=True)
    else:
        # Cálculo de la cuota exacta según el riesgo
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        utilidad_cobertura_plata = retorno_exigido_cobertura - capital_total

        col_plan1, col_plan2 = st.columns(2)
        
        with col_plan1:
            st.markdown(f"""
            <div class="caja-inversion">
                <h4 style="color: #0F172A; margin-top:0;">Fase 1: Pre-partido</h4>
                <p>Ve a tu casa de apuestas e ingresa exactamente:</p>
                <h2 style="color: #334155;">${stake_1:,.0f} COP</h2>
                <p>A la cuota de <b>{cuota_1:.2f}</b> (Favorito o Empate).</p>
                <hr>
                <p style="margin-bottom:0;"><i>Conserva <b>${stake_2:,.0f} COP</b> de provisión en tu caja.</i></p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_plan2:
            if riesgo == 0:
                color_caja = "caja-conservadora"
                titulo = "🛡️ Fase 2: Caza Conservadora"
                color_texto = "#1E3A8A"
            elif riesgo == 100:
                color_caja = "caja-objetivo"
                titulo = "💰 Fase 2: Caza Agresiva"
                color_texto = "#15803D"
            else:
                color_caja = "caja-inversion"
                titulo = "⚖️ Fase 2: Caza Dinámica"
                color_texto = "#0F172A"

            st.markdown(f"""
            <div class="{color_caja}">
                <h4 style="color: {color_texto}; margin-top:0;">{titulo}</h4>
                <p>Sigue trabajando. Cuando la victoria del rival suba, busca inyectar tus <b>${stake_2:,.0f} COP</b> a esta cuota exacta:</p>
                <h1 style="color: {color_texto}; font-size: 3.5rem; margin:0;">{cuota_a_cazar:.2f}</h1>
                <p style="font-size:0.9rem;"><i>Esta cuota incluye tu exigencia de riesgo del {riesgo}%.</i></p>
            </div>
            """, unsafe_allow_html=True)

        # --- BALANCE FINAL PROYECTADO ---
        st.write("### 💵 Proyección del Cierre de Caja")
        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            st.success(f"**Si tu Apuesta 1 gana (Favorito/Empate):**\n\nEl libro cierra con **${utilidad_neta_plata:,.0f} COP** de utilidad neta (+{utilidad_esperada:.1f}% ROI).")
            
        with col_b2:
            if riesgo == 0:
                st.info(f"**Si la Cobertura gana (Sorpresa del Rival):**\n\nEl libro cierra en tablas. Utilidad: **$0 COP** (Recuperaste el 100% del capital).")
            else:
                roi_cobertura = (utilidad_cobertura_plata/capital_total)*100
                st.success(f"**Si la Cobertura gana (Sorpresa del Rival):**\n\nEl libro cierra con **${utilidad_cobertura_plata:,.0f} COP** de utilidad neta (+{roi_cobertura:.1f}% ROI).")


# =====================================================================
# MÓDULO: ESTRATEGIA 1 (MANTENIDA INTACTA)
# =====================================================================
elif estrategia_activa == "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)":
    st.markdown("### 📝 Definición del Módulo")
    st.info("**Lógica:** Ingresamos apoyando estadísticamente al Favorito con nuestra apuesta base. Cuando anote el primer gol y la cuota de 'Empate o Visitante' se dispare, ejecutamos la reserva.")
    
    st.subheader("1️⃣ Presupuesto Asignado")
    capital_total = st.number_input("Capital total para este evento (Mínimo $10,000 COP)", min_value=10000, value=20000, step=1000)

    st.markdown("---")
    st.subheader("2️⃣ Ejecución Inicial y Repartición de Fondos")
    col1, col2 = st.columns(2)

    with col1:
        cuota_1 = st.number_input("Cuota Pre-partido del Favorito", min_value=1.01, value=1.60, step=0.05)

    with col2:
        max_apuesta_1 = capital_total - 5000
        stake_1 = st.slider("Monto de ingreso al Favorito:", min_value=5000, max_value=max_apuesta_1, value=max_apuesta_1, step=1000)

    stake_2 = capital_total - stake_1
    retorno_1 = stake_1 * cuota_1
    utilidad_neta_1 = retorno_1 - capital_total

    st.markdown("---")
    st.subheader("📋 DICTAMEN Y PLAN DE CAZA EN VIVO")

    if utilidad_neta_1 <= 0:
        st.markdown(f"""
        <div class="error-caja"><b>🚨 DÉFICIT OPERATIVO:</b> Verifica los montos y cuotas, el retorno no supera el capital total invertido.</div>
        """, unsafe_allow_html=True)
    else:
        cuota_para_librar = capital_total / stake_2
        cuota_para_utilidad = retorno_1 / stake_2

        st.markdown(f"""
        <div class="paso-caja">
            <h4 style="color: #0F172A;">Fase 1: Pre-partido</h4>
            <p>Ejecuta un ingreso de <b>${stake_1:,.0f} COP</b> a favor del Favorito a cuota <b>{cuota_1:.2f}</b>.</p>
            <p>Conserva los <b>${stake_2:,.0f} COP</b> restantes.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Fase 2: Ejecución de Reserva en Vivo")
        st.write("Espera el gol del Favorito. Luego, caza estas cuotas en la opción **Empate o Visitante**:")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"""<div class="caja-librar"><h4 style="color: #1E3A8A; margin-top: 0;">🛡️ Salvar Capital</h4><h1 style="color: #1E3A8A; margin: 0;">{cuota_para_librar:.2f}</h1></div>""", unsafe_allow_html=True)
        with col_res2:
            st.markdown(f"""<div class="caja-utilidad"><h4 style="color: #15803D; margin-top: 0;">💰 Consolidar Utilidad</h4><h1 style="color: #15803D; margin: 0;">{cuota_para_utilidad:.2f}</h1></div>""", unsafe_allow_html=True)

# =====================================================================
# PLANTILLA NUEVOS MÓDULOS
# =====================================================================
elif estrategia_activa == "➕ Nuevos Módulos (Próximamente)":
    st.warning("Ecosistema modular listo. Aquí podemos desplegar las próximas integraciones matemáticas que diseñes para la plataforma.")