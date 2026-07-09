import streamlit as st
import pandas as pd
import numpy as np
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

def obtener_saldo_banca(tipo_banca: str) -> float:
    if supabase is None:
        return 0.0
    try:
        # 1. Sumar movimientos de caja
        res_movs = supabase.table("movimientos_caja").select("tipo_movimiento", "monto").eq("tipo_banca", tipo_banca).execute()
        total_caja = 0.0
        for mov in res_movs.data:
            if mov['tipo_movimiento'] == "CONSIGNACION":
                total_caja += float(mov['monto'])
            elif mov['tipo_movimiento'] == "RETIRO":
                total_caja -= float(mov['monto'])
        
        # 2. Consolidar utilidades/pérdidas de posiciones CERRADAS
        res_ops_cerradas = supabase.table("historial_trading").select("utilidad_neta_real").eq("tipo_banca", tipo_banca).eq("estado", "CERRADA").execute()
        total_utilidad = sum(float(op['utilidad_neta_real']) for op in res_ops_cerradas.data) if res_ops_cerradas.data else 0.0
        
        # 3. Restar el capital que está COMPROMETIDO en posiciones abiertas
        res_ops_abiertas = supabase.table("historial_trading").select("capital_total").eq("tipo_banca", tipo_banca).in_("estado", ["EN VIVO", "CUBIERTA"]).execute()
        capital_retenido = sum(float(op['capital_total']) for op in res_ops_abiertas.data) if res_ops_abiertas.data else 0.0
        
        return total_caja + total_utilidad - capital_retenido
    except Exception as e:
        return 0.0

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .caja-inversion { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px;}
    .caja-objetivo { background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 20px; border-radius: 8px;}
    .error-caja { background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 5px; color: #991B1B;}
    .caja-codigo { background-color: #FFFBEB; border: 2px dashed #F59E0B; padding: 15px; border-radius: 8px; text-align: center;}
    .kpi-banca { background-color: #F1F5F9; padding: 15px; border-radius: 6px; border: 1px solid #CBD5E1; text-align: center;}
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- CÁLCULO DE SALDOS EN TIEMPO REAL ---
saldo_real = obtener_saldo_banca("REAL")
saldo_simulacion = obtener_saldo_banca("SIMULACION")

# --- LISTADO DE PLATAFORMAS (CASAS DE APUESTAS) ---
plataformas_colombia = ["BetPlay", "Wplay", "Rushbet", "Codere", "Yajuego", "Zamba", "Sportium", "Megapuesta", "Bwin Colombia"]
plataformas_internacionales = ["Bet365", "1xBet", "Betfair", "Pinnacle", "Stake"]
todas_las_plataformas = plataformas_colombia + plataformas_internacionales + ["Otra"]

# --- PANEL LATERAL ---
st.sidebar.title("⚙️ Módulos de Operación")
estrategia_activa = st.sidebar.radio(
    "Navegación:",
    [
        "💰 Gestión de Capital (Caja)",
        "🎯 Estrategia Libre (Apuesta Directa)",
        "2️⃣ Estrategia 2: Paz Mental (Crear Operación)", 
        "🔒 Seguimiento y Liquidación de Posiciones",
        "🔬 Auditoría Cuantitativa (Reporte)"
    ]
)

# Indicadores de saldos fijos en la barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Banca Real:** ${saldo_real:,.0f} COP")
st.sidebar.markdown(f"**Banca Simulación:** ${saldo_simulacion:,.0f} COP")

# Configuración de Riesgo Personalizado
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Umbral de Riesgo")
max_riesgo_permitido = st.sidebar.slider("Alerta de exposición máxima por operación (%):", min_value=5, max_value=100, value=30, step=5)

st.title("⚖️ Sistema de Trading Automático")

# =====================================================================
# MÓDULO: GESTIÓN DE CAPITAL (CONSIGNAR Y RETIRAR)
# =====================================================================
if estrategia_activa == "💰 Gestión de Capital (Caja)":
    st.markdown("### 💰 Control de Flujos de Efectivo y Tesorería")
    st.write("Administre los depósitos y retiros para fondear sus cuentas operativas.")
    
    tab_real, tab_sim = st.tabs(["🟢 BANCA REAL", "🟡 BANCA DE SIMULACIÓN"])
    
    with tab_real:
        st.markdown(f'<div class="kpi-banca"><h5>DISPONIBLE REAL</h5><h2>${saldo_real:,.0f} COP</h2></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("consignar_real"):
                monto = st.number_input("Monto a Consignar (COP):", min_value=5000, step=5000, value=10000)
                if st.form_submit_button("📥 Consignar en Banca Real"):
                    supabase.table("movimientos_caja").insert({"tipo_banca": "REAL", "tipo_movimiento": "CONSIGNACION", "monto": monto}).execute()
                    st.success("Depósito registrado con éxito.")
                    st.rerun()
        with c2:
            with st.form("retirar_real"):
                monto = st.number_input("Monto a Retirar (COP):", min_value=5000, step=5000, value=10000)
                if st.form_submit_button("📤 Retirar de Banca Real"):
                    if monto > saldo_real:
                        st.error("Fondos insuficientes para ejecutar el retiro.")
                    else:
                        supabase.table("movimientos_caja").insert({"tipo_banca": "REAL", "tipo_movimiento": "RETIRO", "monto": monto}).execute()
                        st.success("Retiro registrado con éxito.")
                        st.rerun()
                        
    with tab_sim:
        st.markdown(f'<div class="kpi-banca"><h5>DISPONIBLE SIMULACIÓN</h5><h2>${saldo_simulacion:,.0f} COP</h2></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("consignar_sim"):
                monto = st.number_input("Monto a Consignar Simulado (COP):", min_value=5000, step=5000, value=50000)
                if st.form_submit_button("📥 Consignar en Simulación"):
                    supabase.table("movimientos_caja").insert({"tipo_banca": "SIMULACION", "tipo_movimiento": "CONSIGNACION", "monto": monto}).execute()
                    st.success("Fondeo simulado registrado.")
                    st.rerun()
        with c2:
            with st.form("retirar_sim"):
                monto = st.number_input("Monto a Retirar Simulado (COP):", min_value=5000, step=5000, value=50000)
                if st.form_submit_button("📤 Retirar de Simulación"):
                    if monto > saldo_simulacion:
                        st.error("Fondos simulados insuficientes.")
                    else:
                        supabase.table("movimientos_caja").insert({"tipo_banca": "SIMULACION", "tipo_movimiento": "RETIRO", "monto": monto}).execute()
                        st.success("Retiro simulado registrado.")
                        st.rerun()
# =====================================================================
# MÓDULO 1.5: ESTRATEGIA LIBRE (APUESTA DIRECTA SIN COBERTURA)
# =====================================================================
elif estrategia_activa == "🎯 Estrategia Libre (Apuesta Directa)":
    st.info("**Lógica:** Registro de operaciones direccionales simples. El 100% del capital es el Stake inicial.")
    
    tipo_banca_op = st.radio("Entorno de ejecución:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True)
    banca_activa = "REAL" if "Real" in tipo_banca_op else "SIMULACION"
    saldo_disponible = saldo_real if banca_activa == "REAL" else saldo_simulacion
    
    col1, col2 = st.columns(2)
    with col1:
        capital_total = st.number_input("Inversión Total (Stake COP)", min_value=5000, value=min(20000, int(saldo_disponible)) if saldo_disponible > 5000 else 5000, step=5000)
    with col2:
        cuota_1 = st.number_input("Cuota Fijada", min_value=1.01, value=1.50, step=0.05)

    if saldo_disponible > 0:
        porcentaje_exposicion = (capital_total / saldo_disponible) * 100
        if porcentaje_exposicion > max_riesgo_permitido:
            st.warning(f"⚠️ Alerta de Exposición: Esta operación compromete el {porcentaje_exposicion:.1f}% de la banca disponible, superando el umbral establecido.")

    st.markdown("### 💾 Detalles de la Posición")
    with st.form("guardar_libre"):
        c_eq1, c_eq2 = st.columns(2)
        with c_eq1:
            partido = st.text_input("Evento/Partido", placeholder="Ej: Millonarios vs Cali")
        with c_eq2:
            seleccion = st.text_input("🎯 Selección", placeholder="Ej: Más de 2.5 Goles")
        
        plataforma_ini = st.selectbox("Plataforma de Inversión:", todas_las_plataformas)
        plataforma_otra = ""
        if plataforma_ini == "Otra":
            plataforma_otra = st.text_input("Especifica la plataforma:")

        if st.form_submit_button("Generar Código e Iniciar"):
            if not partido or not seleccion:
                st.error("Debes ingresar el evento y tu selección.")
            elif capital_total > saldo_disponible:
                st.error("Saldo insuficiente en la caja seleccionada.")
            else:
                nuevo_codigo = generar_codigo()
                plataforma_final = plataforma_otra if plataforma_ini == "Otra" else plataforma_ini
                
                # CORRECCIÓN: Etiqueta única para aislar los saldos y evitar embargos de reserva fantasmas
                datos = {
                    "codigo": nuevo_codigo,
                    "partido": partido,
                    "estrategia": "Estrategia Libre Directa", # <--- Cambio contable clave
                    "seleccion_inicial": seleccion,
                    "seleccion_cobertura": "N/A (Apuesta Libre)",
                    "plataforma_inicial": plataforma_final,
                    "capital_total": capital_total,
                    "cuota_inicial": cuota_1,
                    "stake_1": capital_total,
                    "reserva_stake_2": 0,
                    "cuota_objetivo": 0,
                    "estado": "EN VIVO",
                    "tipo_banca": banca_activa
                }
                try:
                    supabase.table("historial_trading").insert(datos).execute()
                    st.markdown(f'<div class="caja-codigo"><h3>Código ({banca_activa}): {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error de Supabase: {str(e)}")
# =====================================================================
# MÓDULO 1: PAZ MENTAL + GUARDADO
# =====================================================================
elif estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Crear Operación)":
    st.info("**Lógica:** Configura tu inversión y registra la plataforma para correcta trazabilidad.")
    
    tipo_banca_op = st.radio("Entorno de ejecución:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True)
    banca_activa = "REAL" if "Real" in tipo_banca_op else "SIMULACION"
    saldo_disponible = saldo_real if banca_activa == "REAL" else saldo_simulacion
    
    # --- SELECTOR DE ENFOQUE (CLÁSICO VS INVERSO) ---
    st.markdown("---")
    enfoque_operativo = st.radio(
        "🎯 Enfoque de Mercado (Determina el libro de auditoría):",
        ["🔵 Clásico (Pre-partido a Favorito/Empate)", "🔴 Inverso (Pre-partido a Sorpresa/Empate)"],
        horizontal=True
    )
    
    # Variables dinámicas solo para la base de datos y la cuota sugerida
    nombre_estrategia_bd = "Estrategia 2: Paz Mental Clásica" if "Clásico" in enfoque_operativo else "Estrategia 2: Paz Mental Inversa"
    val_cuota_def = 1.25 if "Clásico" in enfoque_operativo else 1.80 
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        capital_total = st.number_input("Capital Total (COP)", min_value=10000, value=min(50000, int(saldo_disponible)) if saldo_disponible > 10000 else 10000, step=5000)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial (Apuesta Pre-partido)", min_value=1.01, value=float(val_cuota_def), step=0.05)
    with col3:
        utilidad_esperada = st.slider("Utilidad Deseada (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)

    riesgo = st.slider("Exigencia en Cobertura (0% = Librar, 100% = Ganancia Igualada):", min_value=0, max_value=100, value=50, step=10)

    if saldo_disponible > 0:
        porcentaje_exposicion = (capital_total / saldo_disponible) * 100
        if porcentaje_exposicion > max_riesgo_permitido:
            st.warning(f"⚠️ Alerta de Exposición: Esta operación compromete el {porcentaje_exposicion:.1f}% de la banca disponible, superando el umbral establecido del {max_riesgo_permitido}%.")

    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total
    stake_1 = retorno_objetivo_1 / cuota_1
    stake_2 = capital_total - stake_1

    st.markdown("---")

    if stake_2 < 5000:
        st.markdown(f'<div class="error-caja"><b>🚨 RESTRICCIÓN:</b> Reserva menor a $5,000. Ajusta el capital o utilidad.</div>', unsafe_allow_html=True)
    elif capital_total > saldo_disponible:
        st.markdown(f'<div class="error-caja"><b>🚨 SALDO INSUFICIENTE:</b> El capital configurado supera el saldo disponible.</div>', unsafe_allow_html=True)
    else:
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        
        col_plan1, col_plan2 = st.columns(2)
        with col_plan1:
            st.markdown(f'<div class="caja-inversion"><h4>Fase 1: Pre-partido</h4><p>Ingresa: <b>${stake_1:,.0f} COP</b> a cuota <b>{cuota_1:.2f}</b>.</p><hr><p>Reserva: <b>${stake_2:,.0f} COP</b></p></div>', unsafe_allow_html=True)
        with col_plan2:
            st.markdown(f'<div class="caja-objetivo"><h4>Fase 2: En Vivo</h4><p>Caza esta cuota:</p><h1 style="color:#15803D; font-size:3rem; margin:0;">{cuota_a_cazar:.2f}</h1></div>', unsafe_allow_html=True)

        st.markdown("### 💾 Detalles y Registro de la Operación")
        with st.form("guardar_operacion"):
            
            st.info("💡 **Regla Fija:** Escribe en la Caja 1 el equipo de tu apuesta pre-partido. Escribe en la Caja 2 el equipo que debes cazar en vivo.")
            
            c_eq1, c_eq2 = st.columns(2)
            with c_eq1:
                # Textos fijos, sin inversión dinámica
                eq_apuesta_inicial = st.text_input("⚽ Equipo Apuesta Inicial (Stake 1: Gana/Empata)")
            with c_eq2:
                # Textos fijos, sin inversión dinámica
                eq_cobertura = st.text_input("🎯 Equipo a Cazar en Vivo (Cobertura: Solo Gana)")
            
            # --- INYECCIÓN DEL RELOJ DE AUDITORÍA ---
            hora_inicio = st.time_input("⏱️ Hora de inicio del partido:")
            
            plataforma_ini = st.selectbox("Plataforma de la Apuesta Inicial:", todas_las_plataformas)
            plataforma_otra = ""
            if plataforma_ini == "Otra":
                plataforma_otra = st.text_input("Especifica la otra plataforma:")

            if st.form_submit_button("Generar Código e Iniciar"):
                if not eq_apuesta_inicial or not eq_cobertura:
                    st.error("Debes ingresar los nombres de los equipos en ambas cajas.")
                else:
                    nuevo_codigo = generar_codigo()
                    plataforma_final = plataforma_otra if plataforma_ini == "Otra" else plataforma_ini
                    
                    # Lógica limpia y directa: Lo que escribes, es lo que se guarda.
                    seleccion_ini = f"Gana o Empata {eq_apuesta_inicial}"
                    seleccion_cob = f"Gana {eq_cobertura}"
                    
                    datos = {
                        "codigo": nuevo_codigo,
                        "partido": f"{eq_apuesta_inicial} vs {eq_cobertura}",
                        "estrategia": nombre_estrategia_bd,
                        "seleccion_inicial": seleccion_ini,
                        "seleccion_cobertura": seleccion_cob,
                        "plataforma_inicial": plataforma_final,
                        "capital_total": capital_total,
                        "cuota_inicial": cuota_1,
                        "stake_1": stake_1,
                        "reserva_stake_2": stake_2,
                        "cuota_objetivo": cuota_a_cazar,
                        "estado": "EN VIVO",
                        "tipo_banca": banca_activa,
                        "hora_inicio_partido": hora_inicio.strftime("%H:%M") # --- INYECCIÓN DEL DATO FORMATEADO ---
                    }
                    try:
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f'<div class="caja-codigo"><h3>Código ({banca_activa}): {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"❌ Error de Supabase: {str(e)}")

# =====================================================================
# MÓDULO 2: SEGUIMIENTO Y LIQUIDACIÓN DE POSICIONES
# =====================================================================
elif estrategia_activa == "🔒 Seguimiento y Liquidación de Posiciones":
    st.markdown("### 📝 Panel de Control y Auditoría")
    
    import datetime
    import pandas as pd
    
    if supabase is None:
        st.error("Conecta Supabase primero.")
    else:
        # Consulta organizada por hora de inicio
        res = supabase.table("historial_trading").select("*").in_("estado", ["EN VIVO", "CUBIERTA"]).order("hora_inicio_partido", desc=False).execute()
        ops = res.data
        
        if not ops:
            st.info("Libro mayor al día. No hay posiciones abiertas en este momento.")
        else:
            for op in ops:
                with st.expander(f"⚽ {op['partido']} | Hora: {op.get('hora_inicio_partido', 'N/A')} | Ref: {op['codigo']} | Estado: {op['estado']}"):
                    es_apuesta_libre = op['reserva_stake_2'] == 0
                    
                    sel_ini = op.get('seleccion_inicial', 'Apuesta Inicial')
                    sel_cob = op.get('seleccion_cobertura', 'Cobertura')
                    tipo_estrategia = op.get('estrategia', 'Estrategia 2: Paz Mental Clásica')
                    
                    # --- DESGLOSE AUTOMÁTICO DE NOMBRES DE EQUIPOS ---
                    partido_str = op.get('partido', 'Local vs Visitante')
                    if ' vs ' in partido_str:
                        eq_local = partido_str.split(' vs ')[0].strip()
                        eq_vis = partido_str.split(' vs ')[1].strip()
                    elif ' - ' in partido_str:
                        eq_local = partido_str.split(' - ')[0].strip()
                        eq_vis = partido_str.split(' - ')[1].strip()
                    else:
                        eq_local = "Local"
                        eq_vis = "Visitante"
                    
                    # Identificación automática de bando
                    es_st1_local = (sel_ini.lower() in eq_local.lower()) or (eq_local.lower() in sel_ini.lower())
                    
                    # --- CONCIENCIA DE MERCADO ---
                    if "Inversa" in tipo_estrategia:
                        contexto_mercado = f"El reloj es aliado. Si {sel_ini} aguanta o anota, la cuota de {sel_cob} se disparará."
                    else:
                        contexto_mercado = f"El reloj es enemigo. Necesitas un gol de {sel_ini} o presión temprana para bajar la cuota."
                    
                    if es_apuesta_libre:
                        st.write(f"**Capital Comprometido (Libre):** ${op['capital_total']:,.0f}")
                        st.info(f"🎯 **Selección:** **{sel_ini}** a cuota **{op['cuota_inicial']:.2f}** en **{op.get('plataforma_inicial', 'N/A')}**")
                    else:
                        st.write(f"**Capital Comprometido:** ${op['capital_total']:,.0f} | **Fondo de Cobertura:** ${op['reserva_stake_2']:,.0f}")
                        
                        st.markdown(f"""
                        <div style="background-color: #F8FAFC; padding: 15px; border-left: 4px solid #3B82F6; border-radius: 4px; margin-bottom: 15px;">
                            <p style="margin: 0; font-size: 0.95rem;">🎯 <b>Stake 1:</b> A favor de <b>{sel_ini}</b></p>
                            <p style="margin: 8px 0 8px 0; font-size: 0.95rem;">🛡️ <b>Misión en Vivo:</b> Cazar a <b>{sel_cob}</b> a cuota mínima de <b>{op['cuota_objetivo']:.2f}</b></p>
                            <p style="margin: 0; font-size: 0.85rem; color: #64748B;"><i>💡 {contexto_mercado}</i></p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if op['estado'] == "EN VIVO":
                        if es_apuesta_libre:
                            st.write("Resolución final de la operación:")
                            with st.form(f"gestion_libre_{op['codigo']}"):
                                resultado_libre = st.radio("Resultado:", [f"✅ Ganó {sel_ini} (Cobro Completo)", "❌ Perdida (Pérdida del Capital)"], key=f"rad_lib_{op['codigo']}")
                                if st.form_submit_button("Liquidar Apuesta Libre"):
                                    if "Ganó" in resultado_libre:
                                        utilidad = (op['capital_total'] * op['cuota_inicial']) - op['capital_total']
                                        texto_cierre = "Libre: Ganada"
                                    else:
                                        utilidad = -op['capital_total']
                                        texto_cierre = "Libre: Perdida"
                                        
                                    supabase.table("historial_trading").update({
                                        "estado": "CERRADA",
                                        "resultado_final": texto_cierre,
                                        "utilidad_neta_real": utilidad,
                                        "roi_real": (utilidad / op['capital_total']) * 100
                                    }).eq("codigo", op['codigo']).execute()
                                    st.success(f"Posición liquidada. Utilidad neta: ${utilidad:,.0f} COP.")
                                    st.rerun()
                        else:
                            st.write("### 🛡️ Gestión de Riesgo Dinámico en Vivo")
                            accion = st.radio(
                                "Acción Operativa:", 
                                ["Evaluar Asedio y Cobertura (IRD)", "Liquidar Posición Directa (Sin Cobertura)"],
                                key=f"radio_accion_{op['codigo']}"
                            )
                            
                            if accion == "Evaluar Asedio y Cobertura (IRD)":
                                
                                # --- 1. RECUPERACIÓN DE LA ÚLTIMA FOTO ---
                                res_fotos = supabase.table("registro_fotos").select("*").eq("codigo_posicion", op['codigo']).order("minuto_evaluado", desc=True).limit(1).execute()
                                
                                if res_fotos.data:
                                    ultima_foto = res_fotos.data[0]
                                    min_base = ultima_foto['minuto_evaluado']
                                else:
                                    ultima_foto = {'goles_local': 0, 'goles_vis': 0, 'atkp_local': 0, 'atkp_vis': 0}
                                    min_base = 0

                                st.markdown("#### ⏱️ Auditoría Táctica por Ritmo de Juego")
                                
                                minuto_sugerido = min_base
                                if minuto_sugerido == 0:
                                    hora_ini_str = op.get("hora_inicio_partido", "")
                                    if hora_ini_str:
                                        try:
                                            ahora = datetime.datetime.now()
                                            hora_inicio = datetime.datetime.strptime(hora_ini_str, "%H:%M").replace(year=ahora.year, month=ahora.month, day=ahora.day)
                                            if ahora < hora_inicio: hora_inicio -= datetime.timedelta(days=1)
                                            diff_m = int((ahora - hora_inicio).total_seconds() / 60)
                                            minuto_sugerido = diff_m if diff_m <= 45 else (45 if diff_m < 60 else diff_m - 15)
                                        except Exception: pass
                                
                                minuto_sugerido = max(0, min(95, int(minuto_sugerido)))
                                minuto_actual = st.number_input("⏱️ Minuto del Partido:", min_value=0, max_value=110, value=minuto_sugerido, step=1, key=f"min_{op['codigo']}")
                                
                                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                                col_t1, col_t2 = st.columns(2)
                                
                                # --- FORMULARIO ESPEJO: GOLES Y ATAQUES ABSOLUTOS ---
                                with col_t1:
                                    bg_local = "#F0FDF4" if es_st1_local else "#F8FAFC"
                                    lbl_local = f"🏠 {eq_local} (Tu Equipo)" if es_st1_local else f"🏠 {eq_local}"
                                    st.markdown(f"<div style='background-color:{bg_local}; padding:5px; border-radius:5px; text-align:center; font-weight:bold; color:#334155;'>{lbl_local}</div>", unsafe_allow_html=True)
                                    g_local = st.number_input(f"⚽ Goles", min_value=0, value=int(ultima_foto.get('goles_local', 0)), key=f"g_l_{op['codigo']}")
                                    atkp_local = st.number_input(f"🔥 Atq. Peligrosos", min_value=0, value=int(ultima_foto.get('atkp_local', 0)), key=f"atk_l_{op['codigo']}")
                                
                                with col_t2:
                                    bg_vis = "#F0FDF4" if not es_st1_local else "#FEF2F2"
                                    lbl_vis = f"🚀 {eq_vis} (Tu Equipo)" if not es_st1_local else f"🚀 {eq_vis} (Rival)"
                                    st.markdown(f"<div style='background-color:{bg_vis}; padding:5px; border-radius:5px; text-align:center; font-weight:bold; color:#334155;'>{lbl_vis}</div>", unsafe_allow_html=True)
                                    g_vis = st.number_input(f"⚽ Goles", min_value=0, value=int(ultima_foto.get('goles_vis', 0)), key=f"g_v_{op['codigo']}")
                                    atkp_vis = st.number_input(f"🔥 Atq. Peligrosos", min_value=0, value=int(ultima_foto.get('atkp_vis', 0)), key=f"atk_v_{op['codigo']}")

                                # --- 2. MOTOR MATEMÁTICO REALISTA (APM - Ataques Por Minuto) ---
                                if es_st1_local:
                                    goles_nuestros = g_local
                                    goles_amenaza = g_vis
                                    atkp_nuestros = atkp_local
                                    atkp_amenaza = atkp_vis
                                else:
                                    goles_nuestros = g_vis
                                    goles_amenaza = g_local
                                    atkp_nuestros = atkp_vis
                                    atkp_amenaza = atkp_local

                                # Cálculo de la diferencia de goles
                                diferencia_goles = goles_nuestros - goles_amenaza

                                if diferencia_goles < 0:
                                    ird_base = 100.0  # Perdiendo
                                elif diferencia_goles == 0:
                                    ird_base = 55.0   # Empatados: Alerta severa
                                elif diferencia_goles == 1:
                                    ird_base = 30.0   # Ganando por 1: Riesgo latente
                                else:
                                    ird_base = 0.0    # Ganando por >1: Colchón de seguridad
                                
                                # Cálculo de APM (Ritmo de Asedio)
                                min_divisor = max(1, minuto_actual)
                                apm_rival = atkp_amenaza / min_divisor
                                apm_total = (atkp_nuestros + atkp_amenaza) / min_divisor
                                
                                # Ponderación del Asedio (Acelerador matemático)
                                presion_dominio = apm_rival * 45.0  # 1.0 APM aporta 45 puntos de riesgo
                                
                                # Multiplicador Temporal
                                if minuto_actual <= 60: f_t = 0.8
                                elif minuto_actual <= 75: f_t = 1.0
                                else: f_t = 1.0 + ((minuto_actual - 75) * 0.035) 
                                
                                if ird_base == 100.0:
                                    ird = 100.0
                                else:
                                    ird = min(100.0, ird_base + (presion_dominio * f_t))
                                
                                # --- 3. RENDERIZADO DEL TERMÓMETRO (IRD) ---
                                st.markdown("---")
                                st.markdown("#### 🌡️ Índice de Riesgo Dinámico (IRD)")
                                if min_base == 0:
                                    st.info(f"📌 **Fase de Calibración:** Primera foto registrada. Guarda la línea base para iniciar.")
                                else:
                                    st.info(f"🔎 Auditando ritmo: Rival ataca a **{apm_rival:.2f} veces por minuto**. Partido a {apm_total:.2f} APM total.")
                                
                                if ird < 40:
                                    color = "#10B981"
                                    estado = f"BAJO - Asedio del rival controlado ({apm_rival:.2f} APM)."
                                elif ird < 70:
                                    color = "#F59E0B"
                                    estado = f"MODERADO - El rival empuja la línea ({apm_rival:.2f} APM). Vigilar cuotas."
                                else:
                                    color = "#EF4444"
                                    estado = f"CRÍTICO - ¡Tunda del rival! Bombardeo de {apm_rival:.2f} ataques x minuto."
                                    
                                st.progress(int(ird) / 100)
                                st.markdown(f"<h5 style='text-align: center; color: {color};'>Nivel de Amenaza IRD: {ird:.1f}% | {estado}</h5>", unsafe_allow_html=True)
                                
                                # --- BOTÓN DE ENTRADA A SUPABASE ---
                                if st.button("📸 Guardar Foto y Cerrar Ventana", key=f"btn_foto_{op['codigo']}", use_container_width=True):
                                    try:
                                        nueva_foto = {
                                            "codigo_posicion": str(op['codigo']),
                                            "minuto_evaluado": int(minuto_actual),
                                            "goles_local": int(g_local or 0), 
                                            "goles_vis": int(g_vis or 0),
                                            "atkp_local": int(atkp_local or 0),
                                            "atkp_vis": int(atkp_vis or 0),
                                            "ird_calculado": float(round(ird, 2))
                                        }
                                        supabase.table("registro_fotos").insert(nueva_foto).execute()
                                        st.success(f"✅ Registro completado y respaldado para el minuto {minuto_actual}.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error("❌ Error al guardar en Supabase:")
                                        st.write(f"Detalle del error: {str(e)}")
                                        st.json(nueva_foto)
                                        
                                st.markdown("---")
                                
                                # --- 4. FINANZAS Y DICTAMEN DE EJECUCIÓN ---
                                cuota_ingresada = st.number_input("Tasa de cobertura fijada (Cuota en Vivo Actual):", min_value=1.01, step=0.01, value=float(op['cuota_objetivo']), key=f"cuota_live_{op['codigo']}")
                                plataforma_cob = st.selectbox("Plataforma donde cazaste la cobertura:", todas_las_plataformas, key=f"plat_live_{op['codigo']}")
                                
                                util_inicial_con_cob = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                util_cobertura_con_cob = (op['reserva_stake_2'] * cuota_ingresada) - op['capital_total']
                                util_inicial_sin_cob = (op['stake_1'] * op['cuota_inicial']) - op['stake_1']
                                util_perdida_sin_cob = -op['stake_1']
                                
                                st.markdown("#### 🔍 Matriz Financiera")
                                col_sc1, col_sc2 = st.columns(2)
                                with col_sc1:
                                    st.markdown(f"""
                                    <div style="background-color: #F8FAFC; padding: 15px; border-radius: 6px; border: 1px solid #CBD5E1;">
                                        <b style="color: #1E293B;">OPCIÓN A: Cobertura Activa (Cuota {cuota_ingresada:.2f})</b><br>
                                        • Consolidación Inicial: <b>${util_inicial_con_cob:,.0f} COP</b><br>
                                        • Consolidación Seguro: <span style="color:{'#10B981' if util_cobertura_con_cob >= 0 else '#EF4444'}; font-weight:bold;">${util_cobertura_con_cob:,.0f} COP</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                with col_sc2:
                                    st.markdown(f"""
                                    <div style="background-color: #FFFBEB; padding: 15px; border-radius: 6px; border: 1px solid #FDE68A;">
                                        <b style="color: #78350F;">OPCIÓN B: Abandono de Seguro</b><br>
                                        • Consolidación Inicial: <b>${util_inicial_sin_cob:,.0f} COP</b> (Reserva a salvo)<br>
                                        • Consolidación Pérdida: <span style="color:#EF4444; font-weight:bold;">-${op['stake_1']:,.0f} COP</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                costo_seguro = util_inicial_sin_cob - util_inicial_con_cob
                                mejora_escenario_negativo = util_cobertura_con_cob - util_perdida_sin_cob
                                va_empatado = (goles_nuestros == goles_amenaza)
                                
                                if util_inicial_con_cob >= 0 and util_cobertura_con_cob >= 0:
                                    st.markdown(f"""
                                    <div style="background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 15px; margin-top: 15px; border-radius: 4px; color: #166534;">
                                        <h5 style="margin: 0 0 5px 0; color: #166534;">✅ ARBITRAJE PERFECTO DETECTADO</h5>
                                        <p style="margin: 0; font-size: 0.95rem;">La cuota liquida en verde en ambos escenarios. Asegurar utilidades.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif cuota_ingresada >= op['cuota_objetivo']:
                                    st.markdown(f"""
                                    <div style="background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 15px; margin-top: 15px; border-radius: 4px; color: #166534;">
                                        <h5 style="margin: 0 0 5px 0; color: #166534;">✅ EQUILIBRIO OPERATIVO VIGENTE</h5>
                                        <p style="margin: 0; font-size: 0.95rem;">Cuota objetivo alcanzada, la matemática de diseño se cumple.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                elif mejora_escenario_negativo > costo_seguro:
                                    if va_empatado:
                                        if ird > 70:
                                            st.markdown(f"""
                                            <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                                <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 ALERTA DE QUIEBRE: SALVATAJE DEL EMPATE</h5>
                                                <p style="margin: 0; font-size: 0.95rem;">
                                                    El modelo predictivo arroja <b>{ird:.1f}% de riesgo</b> de destrucción del empate. <b>Fuerza el seguro ahora para proteger patrimonio.</b>
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="background-color: #F8FAFC; border-left: 6px solid #94A3B8; padding: 15px; margin-top: 15px; border-radius: 4px; color: #334155;">
                                                <h5 style="margin: 0 0 5px 0; color: #334155;">💡 PACIENCIA TÁCTICA: EMPATE PROTEGIDO</h5>
                                                <p style="margin: 0; font-size: 0.95rem;">
                                                    El marcador favorece y la aceleración de la amenaza está controlada ({ird:.1f}%). Esperar maduración de cuota.
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                    else:
                                        if ird > 60:
                                            st.markdown(f"""
                                            <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                                <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 MITIGACIÓN TÁCTICA URGENTE</h5>
                                                <p style="margin: 0; font-size: 0.95rem;">
                                                    La presión es asfixiante (Riesgo: {ird:.1f}%). Mitigar golpe y rescatar ${mejora_escenario_negativo:,.0f} COP.
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="background-color: #EFF6FF; border-left: 6px solid #3B82F6; padding: 15px; margin-top: 15px; border-radius: 4px; color: #1E3A8A;">
                                                <h5 style="margin: 0 0 5px 0; color: #1E3A8A;">⚖️ MANTENER POSICIÓN CON CAUTELA</h5>
                                                <p style="margin: 0; font-size: 0.95rem;">
                                                    La cuota es subóptma pero el riesgo es manejable ({ird:.1f}%). No sobrepagar seguro.
                                                </p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                elif mejora_escenario_negativo > 0:
                                    st.markdown(f"""
                                    <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; margin-top: 15px; border-radius: 4px; color: #92400E;">
                                        <h5 style="margin: 0 0 5px 0; color: #B45309;">⚠️ SEGURO INEFICIENTE (INFLACIÓN DE PRECIO)</h5>
                                        <p style="margin: 0; font-size: 0.95rem;">Comprometes demasiada utilidad para blindar una porción ínfima. Preferible soportar.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown(f"""
                                    <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                        <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 EJECUCIÓN INVIABLE</h5>
                                        <p style="margin: 0; font-size: 0.95rem;">El hedge empeora el estado de resultados. Asumir cierre directo.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("🔒 Confirmar y Registrar Cobertura en Libro Mayor", key=f"btn_sub_cob_{op['codigo']}"):
                                    hora_actual = datetime.datetime.now().strftime("%H:%M")
                                    supabase.table("historial_trading").update({
                                        "estado": "CUBIERTA", 
                                        "cuota_cazada_real": cuota_ingresada,
                                        "plataforma_cobertura": plataforma_cob,
                                        "hora_cobertura": hora_actual
                                    }).eq("codigo", op['codigo']).execute()
                                    st.success(f"Operación CUBIERTA registrada a las {hora_actual}.")
                                    st.rerun()
                                    
                            else:
                                with st.form(f"get_dir_{op['codigo']}"):
                                    resultado_directo = st.radio(
                                        "Resolución Post-Partido:", 
                                        [f"✅ Ganó {sel_ini} (Cobro completo)", f"❌ Perdió {sel_ini} (Pérdida Stake 1)"],
                                        key=f"rad_dir_{op['codigo']}"
                                    )
                                    if st.form_submit_button("Registrar Liquidación Directa"):
                                        if "Ganó" in resultado_directo:
                                            utilidad = (op['stake_1'] * op['cuota_inicial']) - op['stake_1']
                                            texto_cierre = "Cierre Directo: Ganó Inicial"
                                        else:
                                            utilidad = -op['stake_1']
                                            texto_cierre = "Cierre Directo: Perdió Inicial"
                                            
                                        supabase.table("historial_trading").update({
                                            "estado": "CERRADA",
                                            "resultado_final": texto_cierre,
                                            "utilidad_neta_real": utilidad,
                                            "roi_real": (utilidad / op['capital_total']) * 100
                                        }).eq("codigo", op['codigo']).execute()
                                        st.success(f"Posición liquidada. Utilidad real transferida: ${utilidad:,.0f} COP.")
                                        st.rerun()

                    elif op['estado'] == "CUBIERTA":
                        st.success(f"🛡️ Cobertura asegurada a tasa de {op.get('cuota_cazada_real', 0):.2f} en {op.get('plataforma_cobertura', 'N/A')}.")
                        with st.form(f"liq_{op['codigo']}"):
                            resultado_final_ui = st.radio(
                                "Conciliación Final del Evento:", 
                                [
                                    f"✅ Inicial Acertado: Ganó {sel_ini}", 
                                    f"🛡️ Seguro Acertado: Ganó {sel_cob}", 
                                    "❌ Déficit Total (Se cayó el Empate)"
                                ],
                                key=f"rad_fin_{op['codigo']}"
                            )
                            if st.form_submit_button("Cerrar Libro Mayor"):
                                if "Inicial" in resultado_final_ui:
                                    utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                    texto_db = "Cobro de Apuesta Inicial"
                                elif "Seguro" in resultado_final_ui:
                                    utilidad = (op['reserva_stake_2'] * op['cuota_cazada_real']) - op['capital_total']
                                    texto_db = "Cobro de Fondo de Cobertura"
                                else:
                                    utilidad = -op['capital_total']
                                    texto_db = "Pérdida Total del Capital"
                                    
                                supabase.table("historial_trading").update({
                                    "estado": "CERRADA",
                                    "resultado_final": texto_db,
                                    "utilidad_neta_real": utilidad,
                                    "roi_real": (utilidad / op['capital_total']) * 100
                                }).eq("codigo", op['codigo']).execute()
                                st.success(f"Libro cerrado. Balance de la operación: ${utilidad:,.0f} COP.")
                                st.rerun()

        st.markdown("---")
        st.subheader("📊 Libro Mayor Contable (Cierres Históricos)")
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        
        if not df.empty:
            # 1. Tabla de datos general (Historial de auditoría)
            st.dataframe(df[['fecha', 'tipo_banca', 'codigo', 'partido', 'seleccion_inicial', 'resultado_final', 'utilidad_neta_real', 'roi_real']], use_container_width=True)
            
            # --- ANCLAJE CRONOLÓGICO DE ZONA HORARIA (Colombia UTC-5) ---
            hoy = (datetime.datetime.utcnow() - datetime.timedelta(hours=5)).date()
            df['fecha_dt'] = pd.to_datetime(df['fecha'], utc=True).dt.tz_convert('America/Bogota')
            df['dia'] = df['fecha_dt'].dt.date
            # Extraer hora de cierre para ordenar la sesión del día
            df['hora_cierre'] = df['fecha_dt'].dt.strftime('%H:%M')
            
            st.markdown("### 📈 Estado de Resultados Desagregado")
            
            # Separación de libros mayores por entorno de ejecución
            df_real_master = df[df['tipo_banca'] == 'REAL'].copy()
            df_sim_master = df[df['tipo_banca'] == 'SIMULACION'].copy()
            
            # Separación en pestañas principales
            tab_real, tab_sim = st.tabs(["🟢 Contabilidad Real", "🟡 Contabilidad Simulación (Paper Trading)"])
            
            # ==========================================
            # PESTAÑA 1: BANCA REAL
            # ==========================================
            with tab_real:
                if not df_real_master.empty:
                    # Selector de alcance temporal
                    filtro_tiempo_r = st.radio("Alcance Temporal (Real):", ["📅 Hoy", "📈 Consolidación Histórica"], horizontal=True, key="filtro_t_real")
                    
                    df_hoy_r = df_real_master[df_real_master['dia'] == hoy]
                    utilidad_hoy_r = df_hoy_r['utilidad_neta_real'].sum()
                    ops_hoy_r = len(df_hoy_r)
                    utilidad_total_r = df_real_master['utilidad_neta_real'].sum()
                    
                    # Despliegue de balances según la selección
                    if filtro_tiempo_r == "📅 Hoy":
                        st.metric(label="💵 Cierre de Caja (Hoy)", value=f"${utilidad_hoy_r:,.0f} COP", delta=f"{ops_hoy_r} operaciones cerradas")
                        
                        if not df_hoy_r.empty:
                            st.markdown("<br><b>Evolución de la Sesión Actual (Operación por Operación)</b>", unsafe_allow_html=True)
                            # Ordenar cronológicamente para ver la curva del día
                            df_hoy_r = df_hoy_r.sort_values(by='fecha_dt')
                            # Crear un identificador visual único para el eje X del gráfico
                            df_hoy_r['operacion'] = df_hoy_r['hora_cierre'] + " - " + df_hoy_r['codigo']
                            df_grafica_hoy_r = df_hoy_r.set_index('operacion')['utilidad_neta_real']
                            st.bar_chart(df_grafica_hoy_r)
                        else:
                            st.info("Sin registros liquidados en la jornada de hoy.")
                    
                    else:  # Consolidación Histórica
                        st.metric(label="💰 Utilidad Neta Acumulada", value=f"${utilidad_total_r:,.0f} COP")
                        
                        st.markdown("<br><b>Tendencia de Resultados Diarios (PNL Consolidado)</b>", unsafe_allow_html=True)
                        df_grafica_cons_r = df_real_master.groupby('dia')['utilidad_neta_real'].sum()
                        st.bar_chart(df_grafica_cons_r)
                else:
                    st.info("No hay transacciones cerradas en Dinero Real.")
            
            # ==========================================
            # PESTAÑA 2: BANCA SIMULADA
            # ==========================================
            with tab_sim:
                if not df_sim_master.empty:
                    # Selector de alcance temporal simulado
                    filtro_tiempo_s = st.radio("Alcance Temporal (Simulación):", ["📅 Hoy", "📈 Consolidación Histórica"], horizontal=True, key="filtro_t_sim")
                    
                    df_hoy_s = df_sim_master[df_sim_master['dia'] == hoy]
                    utilidad_hoy_s = df_hoy_s['utilidad_neta_real'].sum()
                    ops_hoy_s = len(df_hoy_s)
                    utilidad_total_s = df_sim_master['utilidad_neta_real'].sum()
                    
                    if filtro_tiempo_s == "📅 Hoy":
                        st.metric(label="💵 Cierre Virtual (Hoy)", value=f"${utilidad_hoy_s:,.0f} COP", delta=f"{ops_hoy_s} ops virtuales")
                        
                        if not df_hoy_s.empty:
                            st.markdown("<br><b>Evolución de la Sesión Virtual (Operación por Operación)</b>", unsafe_allow_html=True)
                            df_hoy_s = df_sim_master[df_sim_master['dia'] == hoy].sort_values(by='fecha_dt')
                            df_hoy_s['operacion'] = df_hoy_s['hora_cierre'] + " - " + df_hoy_s['codigo']
                            df_grafica_hoy_s = df_hoy_s.set_index('operacion')['utilidad_neta_real']
                            st.bar_chart(df_grafica_hoy_s)
                        else:
                            st.info("Sin registros simulados el día de hoy.")
                    
                    else:  # Consolidación Histórica Simulada
                        st.metric(label="💰 Utilidad Virtual Acumulada", value=f"${utilidad_total_s:,.0f} COP")
                        
                        st.markdown("<br><b>Rendimiento Histórico del Modelo (PNL Consolidado)</b>", unsafe_allow_html=True)
                        df_grafica_cons_s = df_sim_master.groupby('dia')['utilidad_neta_real'].sum()
                        st.bar_chart(df_grafica_cons_s)
                else:
                    st.info("No hay transacciones cerradas en Paper Trading.")

# =====================================================================
# MÓDULO 3: AUDITORÍA CUANTITATIVA (SIMULACIÓN E IA)
# =====================================================================
elif estrategia_activa == "🔬 Auditoría Cuantitativa (Reporte)":
    st.markdown("### 🔬 Laboratorio Cuantitativo de Estrategias")
    st.write("Análisis estadístico basado exclusivamente en la data empírica recopilada durante el período de prueba (Banca Simulación).")
    
    if supabase is None:
        st.error("Conecta Supabase para acceder al motor estadístico.")
    else:
        # Extraer registros cerrados solo de la simulación
        res_sim = supabase.table("historial_trading").select("*").eq("tipo_banca", "SIMULACION").eq("estado", "CERRADA").execute()
        df_sim = pd.DataFrame(res_sim.data)
        
        if df_sim.empty:
            st.info("Aún no hay operaciones de simulación finalizadas para auditar.")
        else:
            # 1. Filtro por Estrategia
            if 'estrategia' not in df_sim.columns:
                df_sim['estrategia'] = "Estrategia 2: Paz Mental Clásica"
                
            estrategias_disponibles = df_sim['estrategia'].dropna().unique().tolist()
            estrategia_seleccionada = st.selectbox("📌 Selecciona la estrategia a auditar:", estrategias_disponibles)
            
            df_est = df_sim[df_sim['estrategia'] == estrategia_seleccionada].copy()
            total_ops = len(df_est)
            
            if total_ops == 0:
                st.info(f"No hay registros cerrados para la estrategia: {estrategia_seleccionada}")
            else:
                if st.button(f"📈 Generar Dictamen Cuantitativo ({total_ops} Simulaciones)"):
                    
                    st.markdown("---")
                    
                    # 3. SELLO DE AUDITORÍA DINÁMICO
                    if total_ops < 5:
                        st.markdown(f"""
                        <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: #991B1B;">
                            <h4 style="margin-top: 0; color: #991B1B;">🚨 DICTAMEN: MUESTRA CRÍTICA (ESTRATEGIA NO PROBADA)</h4>
                            <p style="margin-bottom: 0; font-size: 0.95rem;">
                                Este informe cuenta con una muestra de solo <b>{total_ops} operaciones</b>. Financieramente, este volumen es insignificante. 
                                Los indicadores expuestos abajo están distorsionados por la varianza de corto plazo (suerte). 
                                <b>El modelo matemático carece de sustento probabilístico hasta acumular un volumen mayor.</b>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif total_ops < 100:
                        st.markdown(f"""
                        <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: #92400E;">
                            <h4 style="margin-top: 0; color: #B45309;">⚠️ DICTAMEN PRELIMINAR: MUESTRA EN DESARROLLO (NO PROBADA AÚN)</h4>
                            <p style="margin-bottom: 0; font-size: 0.95rem;">
                                Este dictamen preliminar cuenta con <b>{total_ops} operaciones</b>. Aunque el motor matemático ya proyecta tendencias operativas, 
                                el estándar exige un mínimo de <b>100 eventos continuos</b> para mitigar por completo el factor azar y dar por 'probada' o certificada la viabilidad de la estrategia. Los datos actuales son estrictamente orientativos para control de gestión parcial.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success(f"✅ CERTIFICACIÓN OFICIAL: ESTRATEGIA ESTADÍSTICAMENTE PROBADA. El volumen de {total_ops} operaciones mitiga la desviación estándar. Las métricas describen la ventaja matemática real del modelo.")

                    # 4. Cálculos de Eficiencia Operativa
                    victorias_pre_partido = df_est['resultado_final'].str.contains("Pre-Partido|Ganó Inicial", case=False, na=False).sum()
                    victorias_cobertura = df_est['resultado_final'].str.contains("Cobertura", case=False, na=False).sum()
                    derrotas_totales = df_est['resultado_final'].str.contains("Déficit|Perdid", case=False, na=False).sum()
                    
                    win_rate = (victorias_pre_partido / total_ops) * 100
                    frecuencia_rescate = (victorias_cobertura / total_ops) * 100
                    loss_rate = (derrotas_totales / total_ops) * 100
                    cuota_promedio = df_est['cuota_inicial'].mean()
                    
                    # --- NUEVO: CÁLCULO DE TIEMPO PROMEDIO DE COBERTURA (TIME-TO-HEDGE) ---
                    tiempo_promedio_cob = 0
                    if 'hora_inicio_partido' in df_est.columns and 'hora_cobertura' in df_est.columns:
                        df_tiempos = df_est.dropna(subset=['hora_inicio_partido', 'hora_cobertura']).copy()
                        if not df_tiempos.empty:
                            try:
                                # Convertimos las cadenas "HH:MM" a objetos de tiempo de Pandas para restarlos
                                t_inicio = pd.to_datetime(df_tiempos['hora_inicio_partido'], format='%H:%M')
                                t_cob = pd.to_datetime(df_tiempos['hora_cobertura'], format='%H:%M')
                                
                                # Calculamos la diferencia en minutos
                                diff_minutos = (t_cob - t_inicio).dt.total_seconds() / 60.0
                                
                                # Ajuste por si el partido empezó antes de medianoche y se cubrió después
                                diff_minutos = diff_minutos.apply(lambda x: x + 1440 if x < 0 else x)
                                
                                tiempo_promedio_cob = diff_minutos.mean()
                            except Exception:
                                tiempo_promedio_cob = 0

                    # 5. Cálculos de Riesgo Institucional
                    roi_promedio = df_est['roi_real'].mean()
                    volatilidad_roi = df_est['roi_real'].std() if total_ops > 1 else 0
                    
                    ev = ((win_rate / 100) * (cuota_promedio - 1)) - (loss_rate / 100)
                    sharpe_ratio = (roi_promedio / volatilidad_roi) if volatilidad_roi > 0 else 0
                    
                    df_est = df_est.sort_values(by='fecha')
                    df_est['acumulado_utilidad'] = df_est['utilidad_neta_real'].cumsum()
                    df_est['pico_historico'] = df_est['acumulado_utilidad'].cummax()
                    df_est['drawdown'] = df_est['pico_historico'] - df_est['acumulado_utilidad']
                    max_drawdown_cop = df_est['drawdown'].max() if not df_est['drawdown'].empty else 0
                    
                    # 6. Motor de Decisión (Veredicto)
                    if ev <= 0:
                        veredicto = "🚨 ESTRATEGIA NO VIABLE (EV Negativo)"
                        color_v = "#EF4444"
                        desc_v = "La matemática demuestra que, a largo plazo, esta configuración quemará el capital."
                    elif sharpe_ratio < 0.8:
                        veredicto = "⚠️ ESTRATEGIA DE ALTO RIESGO"
                        color_v = "#F59E0B"
                        desc_v = "Rendimientos erráticos. La volatilidad no justifica el estrés operativo."
                    elif 0.8 <= sharpe_ratio <= 1.5:
                        veredicto = "✅ ESTRATEGIA MODERADA (Viable)"
                        color_v = "#10B981"
                        desc_v = "Configuración sólida. Se recomienda mantener una exposición máxima del 8% al 12% por operación."
                    else:
                        veredicto = "💎 ESTRATEGIA INSTITUCIONAL (Óptima)"
                        color_v = "#3B82F6"
                        desc_v = "Excelente gestión de riesgo y baja volatilidad. Lista para escalado de capital."

                    # --- RENDERIZADO DEL DASHBOARD ---
                    st.markdown(f"""
                        <div style="background-color: {color_v}; padding: 20px; border-radius: 8px; color: white; text-align: center; margin-bottom: 25px;">
                            <h2 style="margin: 0; color: white;">{veredicto}</h2>
                            <p style="margin: 5px 0 0 0;">{desc_v}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("""
                    <style>
                    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center; }
                    .metric-card h4 { margin-top: 0; color: #475569; font-size: 1rem; }
                    .metric-card h2 { margin: 10px 0; font-size: 2rem; }
                    .metric-card p { margin-bottom: 0; color: #64748B; font-size: 0.85rem; }
                    </style>
                    """, unsafe_allow_html=True)

                    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
                    with col_kpi1:
                        st.markdown(f'<div class="metric-card"><h4>Esperanza Matemática (EV)</h4><h2 style="color: {"#10B981" if ev > 0 else "#EF4444"}">{ev:,.3f}</h2><p>Rendimiento estadístico x unidad</p></div>', unsafe_allow_html=True)
                    with col_kpi2:
                        st.markdown(f'<div class="metric-card"><h4>Ratio Sharpe</h4><h2 style="color: {"#3B82F6" if sharpe_ratio >= 1.5 else "#F59E0B"}">{sharpe_ratio:,.2f}</h2><p>Retorno ajustado al riesgo</p></div>', unsafe_allow_html=True)
                    with col_kpi3:
                        st.markdown(f'<div class="metric-card"><h4>Max Drawdown</h4><h2 style="color: #EF4444">${max_drawdown_cop:,.0f}</h2><p>Mayor caída de capital soportada</p></div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.subheader("📊 Eficiencia en la Cancha (Realidad Operativa)")
                    
                    # Añadimos una columna más al renderizado inferior para mostrar el tiempo
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Volumen Analizado", f"{total_ops} Ops")
                    c2.metric("Efectividad Inicial", f"{win_rate:.1f}%")
                    c3.metric("Frecuencia Rescate", f"{frecuencia_rescate:.1f}%")
                    c4.metric("Tasa Fracaso", f"{loss_rate:.1f}%")
                    
                    # Formateo visual del tiempo: Si no hay coberturas mostrar "N/A"
                    texto_tiempo = f"{tiempo_promedio_cob:.0f} min" if tiempo_promedio_cob > 0 else "N/A"
                    c5.metric("Tiempo Promedio a Cobertura", texto_tiempo)