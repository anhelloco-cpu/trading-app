import streamlit as st

st.set_page_config(page_title="Sistema de Trading y Auditoría COP", page_icon="⚖️", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .paso-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;}
    .caja-librar { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px;}
    .caja-utilidad { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 5px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    </style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (SELECTOR DE MÓDULOS) ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Selecciona la estrategia a conciliar:",
    [
        "2️⃣ Estrategia 2: Paz Mental (Favorito o Empate)",
        "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)",
        "➕ Nuevos Módulos (Próximamente)"
    ]
)

st.title("⚖️ Sistema de Trading y Cuadre de Caja")

# =====================================================================
# MÓDULO: ESTRATEGIA 2 (LA QUE PREFIERES)
# =====================================================================
if estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Favorito o Empate)":
    
    st.markdown("### 📝 Definición del Módulo")
    st.info("**Lógica:** Compramos tiempo y baja varianza. Ingresamos a la Doble Oportunidad (Favorito o Empate). Mientras el No Favorito no anote, su cuota de victoria subirá constantemente, dándonos el margen para ejecutar la reserva con calma.")
    
    st.subheader("1️⃣ Presupuesto Asignado")
    capital_total = st.number_input("Capital total para este evento (Mínimo $10,000 COP)", min_value=10000, value=20000, step=1000)

    st.markdown("---")
    st.subheader("2️⃣ Ejecución Inicial y Repartición de Fondos")
    col1, col2 = st.columns(2)

    with col1:
        st.write("Datos de la Opción: **Favorito o Empate**")
        cuota_1 = st.number_input("Cuota Pre-partido (Suele ser baja, ej. 1.25)", min_value=1.01, value=1.25, step=0.05)

    with col2:
        max_apuesta_1 = capital_total - 5000
        st.write("Distribución del capital:")
        stake_1 = st.slider(
            "Monto al Favorito o Empate (El resto quedará en reserva):", 
            min_value=5000, 
            max_value=max_apuesta_1, 
            value=max_apuesta_1, 
            step=1000
        )

    stake_2 = capital_total - stake_1
    retorno_1 = stake_1 * cuota_1
    utilidad_neta_1 = retorno_1 - capital_total

    st.markdown("---")
    st.subheader("📋 DICTAMEN Y PLAN DE CAZA EN VIVO")

    if utilidad_neta_1 <= 0:
        st.markdown(f"""
        <div class="error-caja">
            <b>🚨 DÉFICIT OPERATIVO:</b><br>
            Como la cuota de Doble Oportunidad es baja ({cuota_1}), asignar ${stake_1:,.0f} COP genera un retorno de solo ${retorno_1:,.0f} COP.<br>
            Esto no cubre tu presupuesto total de ${capital_total:,.0f} COP. <br>
            <i>Acción requerida: Para esta estrategia, el grueso de tu liquidez debe ir a la primera apuesta. Mueve el control deslizante a la derecha o busca una cuota ligeramente mayor.</i>
        </div>
        """, unsafe_allow_html=True)
    else:
        cuota_para_librar = capital_total / stake_2
        cuota_para_utilidad = retorno_1 / stake_2

        st.markdown(f"""
        <div class="paso-caja">
            <h4 style="color: #0F172A;">Fase 1: Pre-partido (Posicionamiento)</h4>
            <p>Ejecuta un ingreso de <b>${stake_1:,.0f} COP</b> a la opción <b>Favorito o Empate (1X)</b> a cuota <b>{cuota_1:.2f}</b>.</p>
            <p>Conserva los <b>${stake_2:,.0f} COP</b> restantes en el saldo de tu cuenta.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Fase 2: Ejecución de Reserva en Vivo")
        st.write(f"Sigue trabajando con tranquilidad. Revisa el partido periódicamente; el reloj está inflando la cuota de la **Victoria del No Favorito**. Usa tus **${stake_2:,.0f} COP** de reserva SOLO si esa cuota cruza uno de estos umbrales:")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"""
            <div class="caja-librar">
                <h4 style="color: #1E3A8A; margin-top: 0;">🛡️ Objetivo A: Salvar Capital</h4>
                <p>Para recuperar tu presupuesto completo (${capital_total:,.0f}) si hay sorpresa total:</p>
                <h1 style="color: #1E3A8A; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_librar:.2f}</h1>
                <p style="font-size: 0.9rem; margin-top: 10px;">Si el No Favorito gana, recuperas el 100%. Si ocurre lo lógico (Empate o Favorito), consolidas ${utilidad_neta_1:,.0f} COP limpios.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_res2:
            st.markdown(f"""
            <div class="caja-utilidad">
                <h4 style="color: #15803D; margin-top: 0;">💰 Objetivo B: Consolidar Utilidad</h4>
                <p>Para garantizar exactamente la misma utilidad (${utilidad_neta_1:,.0f}) en cualquier escenario:</p>
                <h1 style="color: #15803D; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_utilidad:.2f}</h1>
                <p style="font-size: 0.9rem; margin-top: 10px;">Balance perfecto. Gane quien gane o empaten, los libros cerrarán en verde.</p>
            </div>
            """, unsafe_allow_html=True)


# =====================================================================
# MÓDULO: ESTRATEGIA 1 (MANTENIDA POR SI ACASO)
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