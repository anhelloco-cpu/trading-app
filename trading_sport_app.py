import streamlit as st

st.set_page_config(page_title="Sistema de Trading Deportivo", page_icon="⚖️", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .paso-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;}
    .caja-librar { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px;}
    .caja-utilidad { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 5px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    </style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (SELECTOR DE ESTRATEGIAS) ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Selecciona la estrategia a ejecutar:",
    [
        "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)",
        "➕ Nueva Estrategia (Próximamente...)"
    ]
)

st.title("⚖️ Sistema de Trading y Cuadre de Caja")

# =====================================================================
# MÓDULO: ESTRATEGIA 1
# =====================================================================
if estrategia_activa == "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)":
    
    st.markdown("### 📝 Definición del Módulo")
    st.info("**Lógica:** Ingresamos apoyando estadísticamente al Favorito con nuestra apuesta base. Cuando anote el primer gol y la cuota de 'Empate o Visitante' se dispare, ejecutamos la reserva para asegurar el balance.")
    
    # --- 1. CONFIGURACIÓN DEL CAPITAL TOTAL ---
    st.subheader("1️⃣ Presupuesto Asignado")
    capital_total = st.number_input("Capital total para este evento (Mínimo $10,000 COP)", 
                                    min_value=10000, value=20000, step=1000)

    # --- 2. LA PRIMERA APUESTA Y REPARTICIÓN ---
    st.markdown("---")
    st.subheader("2️⃣ Ejecución Inicial y Repartición de Fondos")
    col1, col2 = st.columns(2)

    with col1:
        cuota_1 = st.number_input("Cuota Pre-partido del Favorito", min_value=1.01, value=1.60, step=0.05)

    with col2:
        max_apuesta_1 = capital_total - 5000
        st.write("Distribución del capital:")
        stake_1 = st.slider(
            "Monto de ingreso al Favorito (El resto quedará en reserva):", 
            min_value=5000, 
            max_value=max_apuesta_1, 
            value=max_apuesta_1, 
            step=1000
        )

    stake_2 = capital_total - stake_1

    # --- 3. AUDITORÍA MATEMÁTICA ---
    retorno_1 = stake_1 * cuota_1
    utilidad_neta_1 = retorno_1 - capital_total

    st.markdown("---")
    st.subheader("📋 DICTAMEN Y PLAN DE CAZA EN VIVO")

    if utilidad_neta_1 <= 0:
        st.markdown(f"""
        <div class="error-caja">
            <b>🚨 DÉFICIT OPERATIVO:</b><br>
            Si destinas ${stake_1:,.0f} COP al Favorito (cuota {cuota_1}), el retorno bruto sería de ${retorno_1:,.0f} COP.<br>
            Esto te dejaría en saldo rojo frente a tu presupuesto total de ${capital_total:,.0f} COP.<br>
            <i>Acción requerida: Desplaza el slider para asignar más liquidez a la primera apuesta o busca una cuota base superior.</i>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fórmulas de auditoría para hallar la cuota exacta
        cuota_para_librar = capital_total / stake_2
        cuota_para_utilidad = retorno_1 / stake_2

        st.markdown(f"""
        <div class="paso-caja">
            <h4 style="color: #0F172A;">Fase 1: Pre-partido</h4>
            <p>Ejecuta un ingreso de <b>${stake_1:,.0f} COP</b> a favor del Favorito a cuota <b>{cuota_1:.2f}</b>.</p>
            <p>Conserva los <b>${stake_2:,.0f} COP</b> restantes en el saldo de tu cuenta.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Fase 2: Ejecución de Reserva en Vivo")
        st.write(f"Espera el gol del Favorito. Cuando ocurra, vigila la opción **'Doble Oportunidad (Empate o Visitante)'**. Usa tus **${stake_2:,.0f} COP** de reserva SOLO si la cuota cruza uno de estos umbrales:")

        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            st.markdown(f"""
            <div class="caja-librar">
                <h4 style="color: #1E3A8A; margin-top: 0;">🛡️ Objetivo A: Salvar Capital</h4>
                <p>Para recuperar tu presupuesto completo (${capital_total:,.0f}) y salir en tablas (saldo cero):</p>
                <h1 style="color: #1E3A8A; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_librar:.2f}</h1>
                <p style="font-size: 0.9rem; margin-top: 10px;">Balance: Si el rival empata/remonta, recuperas el 100%. Si el Favorito mantiene la victoria, utilidad limpia de ${utilidad_neta_1:,.0f} COP.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_res2:
            st.markdown(f"""
            <div class="caja-utilidad">
                <h4 style="color: #15803D; margin-top: 0;">💰 Objetivo B: Consolidar Utilidad</h4>
                <p>Para garantizar exactamente la misma utilidad neta (${utilidad_neta_1:,.0f}) gane quien gane:</p>
                <h1 style="color: #15803D; margin: 0; font-size: 2.5rem;">Caza la cuota: {cuota_para_utilidad:.2f}</h1>
                <p style="font-size: 0.9rem; margin-top: 10px;">Balance: Matemáticamente infalible. Al ingresar a esta cuota, el libro de operaciones cerrará en verde bajo cualquier escenario final.</p>
            </div>
            """, unsafe_allow_html=True)

# =====================================================================
# MÓDULO: NUEVAS ESTRATEGIAS (PLANTILLA)
# =====================================================================
elif estrategia_activa == "➕ Nueva Estrategia (Próximamente...)":
    st.warning("Este módulo se encuentra en fase de diseño. Aquí configuraremos las próximas lógicas matemáticas para nuevos mercados (ej. mercado de goles, hándicaps).")