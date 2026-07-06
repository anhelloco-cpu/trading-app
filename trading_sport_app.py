import streamlit as st
import requests

st.set_page_config(page_title="Sistema de Trading y Auditoría COP", page_icon="⚖️", layout="wide")

# --- INICIALIZAR LA MEMORIA (SESSION STATE) ---
# Esto guarda la cuota si la importas desde el Live Tracker
if 'cuota_importada' not in st.session_state:
    st.session_state.cuota_importada = 1.25

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .paso-caja { background-color: #F8FAFC; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px;}
    .caja-librar { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px;}
    .caja-utilidad { background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 15px; border-radius: 5px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    .caja-inversion { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px;}
    .caja-objetivo { background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 20px; border-radius: 8px;}
    .caja-conservadora { background-color: #EFF6FF; border-left: 6px solid #3B82F6; padding: 20px; border-radius: 8px;}
    .partido-tarjeta { background-color: #FFFFFF; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);}
    </style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (SELECTOR DE MÓDULOS) ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Selecciona la estrategia a conciliar:",
    [
        "2️⃣ Estrategia 2: Paz Mental (Inversión Proyectada)",
        "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)",
        "📡 Módulo 3: Live Tracker (Cuotas Reales)"
    ]
)

st.title("⚖️ Sistema de Trading y Cuadre de Caja")

# =====================================================================
# MÓDULO: ESTRATEGIA 2 (PAZ MENTAL + PROYECCIÓN DE UTILIDAD Y RIESGO)
# =====================================================================
if estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Inversión Proyectada)":
    
    st.markdown("### 📝 Definición del Módulo")
    st.info("**Lógica:** Proyectamos la rentabilidad. Define tu % de utilidad y tu nivel de riesgo. El sistema dividirá el capital automáticamente.")
    
    st.subheader("1️⃣ Parámetros de la Inversión")
    col1, col2, col3 = st.columns(3)

    with col1:
        capital_total = st.number_input("Capital Total a Invertir (COP)", min_value=10000, value=50000, step=5000)
    with col2:
        # Aquí la app lee la memoria por si trajiste una cuota del Live Tracker
        cuota_1 = st.number_input("Cuota Inicial (Favorito o Empate)", min_value=1.01, value=st.session_state.cuota_importada, step=0.05)
    with col3:
        max_utilidad_teorica = (cuota_1 - 1.0) * 100.0
        if max_utilidad_teorica <= 1.0: max_utilidad_teorica = 1.1 
        
        utilidad_esperada = st.slider(
            f"Utilidad Deseada (%) [Máx Teórico: {max_utilidad_teorica:.1f}%]", 
            min_value=1.0, 
            max_value=float(max_utilidad_teorica - 0.1), 
            value=min(10.0, float(max_utilidad_teorica - 0.1)), 
            step=0.5
        )

    st.markdown("---")
    st.subheader("2️⃣ Perfil de Riesgo para la Cobertura (En Vivo)")
    riesgo = st.slider(
        "Nivel de Exigencia en la Cobertura:",
        min_value=0, max_value=100, value=50, step=10
    )

    col_r1, col_r2, col_r3 = st.columns([1,1,1])
    col_r1.write("📉 **0%** (Librar Inversión)")
    col_r2.write("⚖️ **50%** (Utilidad Parcial)")
    col_r3.write("📈 **100%** (Utilidad Total)")

    # Cálculos
    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total
    stake_1 = retorno_objetivo_1 / cuota_1
    stake_2 = capital_total - stake_1

    st.markdown("---")
    st.subheader("📋 DICTAMEN DE AUDITORÍA Y PLAN DE CAZA")

    if stake_2 < 5000:
        st.markdown(f"""
        <div class="error-caja">
            <b>🚨 RESTRICCIÓN DE LIQUIDEZ:</b> Tu reserva calculada (${stake_2:,.0f} COP) es menor al mínimo de $5,000 COP exigido por la casa.<br>
            <b>Solución:</b> Sube tu Capital Total o baja el % de Utilidad Deseada.
        </div>
        """, unsafe_allow_html=True)
    else:
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        utilidad_cobertura_plata = retorno_exigido_cobertura - capital_total

        col_plan1, col_plan2 = st.columns(2)
        with col_plan1:
            st.markdown(f"""
            <div class="caja-inversion">
                <h4 style="color: #0F172A; margin-top:0;">Fase 1: Pre-partido</h4>
                <p>Ingresa exactamente:</p>
                <h2 style="color: #334155;">${stake_1:,.0f} COP</h2>
                <p>A la cuota de <b>{cuota_1:.2f}</b>.</p>
                <hr><p style="margin-bottom:0;"><i>Conserva <b>${stake_2:,.0f} COP</b> de provisión en tu caja.</i></p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_plan2:
            color_caja = "caja-conservadora" if riesgo == 0 else "caja-objetivo" if riesgo == 100 else "caja-inversion"
            color_texto = "#1E3A8A" if riesgo == 0 else "#15803D" if riesgo == 100 else "#0F172A"
            titulo = "🛡️ Caza Conservadora" if riesgo == 0 else "💰 Caza Agresiva" if riesgo == 100 else "⚖️ Caza Dinámica"

            st.markdown(f"""
            <div class="{color_caja}">
                <h4 style="color: {color_texto}; margin-top:0;">{titulo}</h4>
                <p>Cuando el rival suba, inyecta los <b>${stake_2:,.0f} COP</b> a esta cuota exacta:</p>
                <h1 style="color: {color_texto}; font-size: 3.5rem; margin:0;">{cuota_a_cazar:.2f}</h1>
            </div>
            """, unsafe_allow_html=True)


# =====================================================================
# MÓDULO 3: LIVE TRACKER CONECTADO A API
# =====================================================================
elif estrategia_activa == "📡 Módulo 3: Live Tracker (Cuotas Reales)":
    st.markdown("### 📡 Rastreador de Cuotas (The Odds API)")
    st.write("Conecta tu app a los mercados mundiales. Obtén una clave gratis en [the-odds-api.com](https://the-odds-api.com/) y pégala aquí.")
    
    api_key = st.text_input("🔑 Tu API Key:", type="password", help="Pega aquí tu clave gratuita de 32 caracteres.")
    
    # Ligas más populares
    ligas_opciones = {
        "Fútbol Colombiano (Primera A)": "soccer_colombia_primera_a",
        "Próximos Partidos (General)": "upcoming",
        "Champions League": "soccer_uefa_champs_league",
        "Premier League": "soccer_epl",
        "La Liga (España)": "soccer_spain_la_liga",
        "Copa Libertadores": "soccer_conmebol_copa_libertadores"
    }
    
    liga_seleccionada = st.selectbox("⚽ Selecciona la Liga a rastrear:", list(ligas_opciones.keys()))
    
    if st.button("🔄 Actualizar Cuotas Ahora"):
        if not api_key:
            st.error("Por favor, ingresa tu API Key primero.")
        else:
            sport_key = ligas_opciones[liga_seleccionada]
            # Endpoint para cuotas
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,us&markets=h2h&oddsFormat=decimal"
            
            with st.spinner("Descargando datos del mercado..."):
                try:
                    respuesta = requests.get(url)
                    if respuesta.status_code == 200:
                        datos = respuesta.json()
                        
                        if len(datos) == 0:
                            st.warning("No hay partidos disponibles para esta liga en este momento.")
                        else:
                            st.success(f"¡{len(datos)} partidos encontrados!")
                            
                            for partido in datos:
                                home = partido.get("home_team", "Local")
                                away = partido.get("away_team", "Visitante")
                                
                                # Buscar la primera casa de apuestas disponible
                                bookmakers = partido.get("bookmakers", [])
                                if bookmakers:
                                    # Extraer cuotas del primer bookmaker
                                    mercados = bookmakers[0].get("markets", [])
                                    cuotas_h2h = []
                                    for mercado in mercados:
                                        if mercado["key"] == "h2h":
                                            cuotas_h2h = mercado["outcomes"]
                                            break
                                    
                                    # Mostrar los datos si hay cuotas
                                    if cuotas_h2h:
                                        st.markdown(f"""
                                        <div class="partido-tarjeta">
                                            <h3 style="margin:0; color:#1E3A8A;">⚽ {home} vs {away}</h3>
                                            <p style="margin-top:0; color:#64748B;">Casa de apuestas fuente: {bookmakers[0]['title']}</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        # Mostrar botones con las cuotas
                                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                                        for outcome in cuotas_h2h:
                                            nombre_equipo = outcome['name']
                                            precio = outcome['price']
                                            
                                            if nombre_equipo == home:
                                                with col_btn1:
                                                    if st.button(f"🏠 Local ({precio})", key=f"{partido['id']}_home"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota de {precio} guardada! Ve a la Estrategia 2 para usarla.")
                                            elif nombre_equipo == away:
                                                with col_btn3:
                                                    if st.button(f"✈️ Visitante ({precio})", key=f"{partido['id']}_away"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota de {precio} guardada! Ve a la Estrategia 2 para usarla.")
                                            else:
                                                with col_btn2:
                                                    if st.button(f"🤝 Empate ({precio})", key=f"{partido['id']}_draw"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota de {precio} guardada! Ve a la Estrategia 2 para usarla.")
                                else:
                                    st.info(f"{home} vs {away} - Sin cuotas reportadas aún.")
                                    
                    elif respuesta.status_code == 401:
                        st.error("❌ API Key inválida. Revisa que la hayas copiado bien.")
                    else:
                        st.error(f"Error en el servidor de datos (Código {respuesta.status_code}).")
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")


# =====================================================================
# MÓDULO: ESTRATEGIA 1 (MANTENIDA INTACTA)
# =====================================================================
elif estrategia_activa == "1️⃣ Estrategia 1: A favor de la lógica (Back to Lay)":
    st.info("**Lógica:** Ingresamos apoyando estadísticamente al Favorito con nuestra apuesta base.")
    capital_total = st.number_input("Capital total para este evento", min_value=10000, value=20000, step=1000)
    
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