import streamlit as st
import requests
import pandas as pd
import random
import string
from supabase import create_client, Client

st.set_page_config(page_title="Sistema de Trading y Auditoría COP", page_icon="⚖️", layout="wide")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase: Client = init_connection()

# --- FUNCIONES AUXILIARES ---
def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

if 'cuota_importada' not in st.session_state:
    st.session_state.cuota_importada = 1.25

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .caja-inversion { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px;}
    .caja-objetivo { background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 20px; border-radius: 8px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    .caja-codigo { background-color: #FFFBEB; border: 2px dashed #F59E0B; padding: 15px; border-radius: 8px; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Navegación:",
    [
        "2️⃣ Estrategia 2: Paz Mental (Crear Operación)",
        "🔒 Seguimiento y Cierre de Operaciones",
        "📡 Módulo 3: Live Tracker (Cuotas)",
        "1️⃣ Estrategia 1: Back to Lay (Básica)"
    ]
)

st.title("⚖️ Sistema de Trading Automático")

# =====================================================================
# MÓDULO 1: PAZ MENTAL + GUARDADO DIRECTO
# =====================================================================
if estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Crear Operación)":
    st.info("**Lógica:** Haz la simulación y si los números cuadran, inicia la operación para obtener tu código de seguimiento.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        capital_total = st.number_input("Capital Total a Invertir (COP)", min_value=10000, value=50000, step=5000)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial (Favorito o Empate)", min_value=1.01, value=st.session_state.cuota_importada, step=0.05)
    with col3:
        max_utilidad_teorica = (cuota_1 - 1.0) * 100.0 if cuota_1 > 1.0 else 1.1
        if max_utilidad_teorica <= 1.0: max_utilidad_teorica = 1.1 
        utilidad_esperada = st.slider(f"Utilidad Deseada (%) [Máx: {max_utilidad_teorica:.1f}%]", min_value=1.0, max_value=float(max_utilidad_teorica - 0.1), value=min(10.0, float(max_utilidad_teorica - 0.1)), step=0.5)

    riesgo = st.slider("Nivel de Exigencia en la Cobertura (0% = Librar, 100% = Ganancia Igualada):", min_value=0, max_value=100, value=50, step=10)

    # Cálculos
    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total
    stake_1 = retorno_objetivo_1 / cuota_1
    stake_2 = capital_total - stake_1

    st.markdown("---")

    if stake_2 < 5000:
        st.markdown(f'<div class="error-caja"><b>🚨 RESTRICCIÓN DE LIQUIDEZ:</b> Tu reserva (${stake_2:,.0f} COP) es menor a $5,000. Ajusta el capital o utilidad.</div>', unsafe_allow_html=True)
    else:
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        
        col_plan1, col_plan2 = st.columns(2)
        with col_plan1:
            st.markdown(f'<div class="caja-inversion"><h4 style="margin-top:0;">Fase 1: Pre-partido</h4><p>Ingresa: <b>${stake_1:,.0f} COP</b> a cuota <b>{cuota_1:.2f}</b>.</p><hr><p>Reserva: <b>${stake_2:,.0f} COP</b></p></div>', unsafe_allow_html=True)
        with col_plan2:
            st.markdown(f'<div class="caja-objetivo"><h4 style="color:#15803D; margin-top:0;">Fase 2: En Vivo</h4><p>Caza esta cuota con la reserva:</p><h1 style="color:#15803D; font-size:3rem; margin:0;">{cuota_a_cazar:.2f}</h1></div>', unsafe_allow_html=True)

        # --- BOTÓN PARA INICIAR LA OPERACIÓN ---
        st.markdown("### 💾 Iniciar Operación Real")
        if supabase is None:
            st.warning("Configura los Secrets de Supabase para guardar operaciones.")
        else:
            with st.form("guardar_operacion"):
                nombre_partido = st.text_input("¿Qué partido es? (Ej: Millonarios vs Santa Fe)")
                submit_iniciar = st.form_submit_button("Generar Código e Iniciar Operación")
                
                if submit_iniciar:
                    if not nombre_partido:
                        st.error("Debes poner el nombre del partido.")
                    else:
                        nuevo_codigo = generar_codigo()
                        datos = {
                            "codigo": nuevo_codigo,
                            "partido": nombre_partido,
                            "capital_total": capital_total,
                            "cuota_inicial": cuota_1,
                            "stake_1": stake_1,
                            "reserva_stake_2": stake_2,
                            "cuota_objetivo": cuota_a_cazar,
                            "estado": "EN VIVO"
                        }
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f"""
                        <div class="caja-codigo">
                            <h3 style="margin:0; color:#B45309;">¡Operación Iniciada!</h3>
                            <p style="margin:0;">Tu código de seguimiento es:</p>
                            <h1 style="margin:0; font-size:4rem; letter-spacing: 5px; color:#D97706;">{nuevo_codigo}</h1>
                            <p><i>Ve al módulo "Seguimiento y Cierre" cuando el partido acabe.</i></p>
                        </div>
                        """, unsafe_allow_html=True)

# =====================================================================
# MÓDULO 2: SEGUIMIENTO Y CIERRE
# =====================================================================
elif estrategia_activa == "🔒 Seguimiento y Cierre de Operaciones":
    st.markdown("### 📝 Operaciones Activas")
    
    if supabase is None:
        st.error("Conecta Supabase primero.")
    else:
        # Obtener operaciones EN VIVO
        res_activas = supabase.table("historial_trading").select("*").eq("estado", "EN VIVO").execute()
        ops_activas = res_activas.data
        
        if not ops_activas:
            st.info("No tienes operaciones pendientes de cierre.")
        else:
            for op in ops_activas:
                with st.expander(f"🟢 Partido: {op['partido']} | Código: {op['codigo']}"):
                    st.write(f"**Capital:** ${op['capital_total']:,.0f} | **Reserva que debías cazar:** ${op['reserva_stake_2']:,.0f} a cuota **{op['cuota_objetivo']:.2f}**")
                    
                    with st.form(f"cierre_{op['codigo']}"):
                        resultado = st.radio("¿Qué sucedió finalmente?", [
                            "Ganó Primera Apuesta (Favorito/Empate)",
                            "Ganó Cobertura (Sorpresa del Rival)",
                            "Pérdida Total (No dio tiempo a cubrir)"
                        ])
                        
                        cuota_real = 0.0
                        if resultado == "Ganó Cobertura (Sorpresa del Rival)":
                            cuota_real = st.number_input("¿A qué cuota exacta lograste meter la cobertura en vivo?", min_value=1.01, step=0.01)
                            
                        if st.form_submit_button("Cerrar Operación"):
                            # El programa calcula la utilidad real automáticamente
                            if resultado == "Ganó Primera Apuesta (Favorito/Empate)":
                                utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                            elif resultado == "Ganó Cobertura (Sorpresa del Rival)":
                                utilidad = (op['reserva_stake_2'] * cuota_real) - op['capital_total']
                            else:
                                utilidad = -op['capital_total']
                                
                            roi = (utilidad / op['capital_total']) * 100
                            
                            # Actualizar Supabase
                            upd_data = {
                                "estado": "CERRADA",
                                "resultado_final": resultado,
                                "cuota_cazada_real": cuota_real,
                                "utilidad_neta_real": utilidad,
                                "roi_real": roi
                            }
                            supabase.table("historial_trading").update(upd_data).eq("codigo", op['codigo']).execute()
                            st.success(f"Operación {op['codigo']} cerrada. Utilidad Real: ${utilidad:,.0f} COP.")
                            st.rerun()

        st.markdown("---")
        st.subheader("📊 Tu Libro Mayor (Resultados)")
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        
        if not df.empty:
            ganadas = len(df[df['utilidad_neta_real'] >= 0])
            total = len(df)
            utilidad_total = df['utilidad_neta_real'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Operaciones Cerradas", total)
            c2.metric("Tasa de No Pérdida", f"{(ganadas/total)*100:.1f}%")
            c3.metric("Utilidad Acumulada", f"${utilidad_total:,.0f} COP")
            
            df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d')
            st.dataframe(df[['fecha', 'codigo', 'partido', 'resultado_final', 'utilidad_neta_real', 'roi_real']], use_container_width=True)


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

# =====================================================================
# MÓDULO 3: LIVE TRACKER CONECTADO A THE ODDS API
# =====================================================================
elif estrategia_activa == "📡 Módulo 3: Live Tracker (Cuotas Reales)":
    st.markdown("### 📡 Rastreador de Cuotas (The Odds API)")
    st.write("Conecta tu app a los mercados mundiales. Obtén una clave gratis en [the-odds-api.com](https://the-odds-api.com/) y pégala aquí.")
    
    # 1. Cajón para la contraseña de la API
    api_key = st.text_input("🔑 Tu API Key:", type="password", help="Pega aquí tu clave de 32 caracteres.")
    
    # 2. Diccionario con las ligas soportadas
    ligas_opciones = {
        "Fútbol Colombiano (Primera A)": "soccer_colombia_primera_a",
        "Próximos Partidos (General)": "upcoming",
        "Champions League": "soccer_uefa_champs_league",
        "Premier League": "soccer_epl",
        "La Liga (España)": "soccer_spain_la_liga",
        "Copa Libertadores": "soccer_conmebol_copa_libertadores"
    }
    
    liga_seleccionada = st.selectbox("⚽ Selecciona la Liga a rastrear:", list(ligas_opciones.keys()))
    
    # 3. El botón que activa la descarga
    if st.button("🔄 Actualizar Cuotas Ahora"):
        if not api_key:
            st.error("Por favor, ingresa tu API Key primero.")
        else:
            sport_key = ligas_opciones[liga_seleccionada]
            
            # La URL exacta que The Odds API necesita para devolvernos los datos en formato decimal
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
                            
                            # 4. Procesar cada partido que nos envía la API
                            for partido in datos:
                                home = partido.get("home_team", "Local")
                                away = partido.get("away_team", "Visitante")
                                
                                bookmakers = partido.get("bookmakers", [])
                                if bookmakers:
                                    mercados = bookmakers[0].get("markets", [])
                                    cuotas_h2h = []
                                    for mercado in mercados:
                                        if mercado["key"] == "h2h":
                                            cuotas_h2h = mercado["outcomes"]
                                            break
                                    
                                    # 5. Imprimir las tarjetas de los partidos en pantalla
                                    if cuotas_h2h:
                                        st.markdown(f"""
                                        <div style="background-color: #FFFFFF; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                                            <h3 style="margin:0; color:#1E3A8A;">⚽ {home} vs {away}</h3>
                                            <p style="margin-top:0; color:#64748B;">Fuente: {bookmakers[0]['title']}</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                                        for outcome in cuotas_h2h:
                                            nombre_equipo = outcome['name']
                                            precio = outcome['price']
                                            
                                            # 6. Guardar en memoria (session_state) si el usuario hace clic
                                            if nombre_equipo == home:
                                                with col_btn1:
                                                    if st.button(f"🏠 Local ({precio})", key=f"{partido['id']}_home"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota guardada! Ve a la Estrategia 2 para usarla.")
                                            elif nombre_equipo == away:
                                                with col_btn3:
                                                    if st.button(f"✈️ Visitante ({precio})", key=f"{partido['id']}_away"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota guardada! Ve a la Estrategia 2 para usarla.")
                                            else:
                                                with col_btn2:
                                                    if st.button(f"🤝 Empate ({precio})", key=f"{partido['id']}_draw"):
                                                        st.session_state.cuota_importada = float(precio)
                                                        st.success(f"¡Cuota guardada! Ve a la Estrategia 2 para usarla.")
                                else:
                                    st.info(f"{home} vs {away} - Sin cuotas reportadas aún.")
                                    
                    elif respuesta.status_code == 401:
                        st.error("❌ API Key inválida. Revisa que la hayas copiado bien (sin espacios al final).")
                    else:
                        st.error(f"Error en el servidor de The Odds API (Código {respuesta.status_code}).")
                except Exception as e:
                    st.error(f"Error de conexión a internet: {str(e)}")