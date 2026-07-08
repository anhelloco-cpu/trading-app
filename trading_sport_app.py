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
                
                # Para la apuesta libre, el stake_2 y la cuota objetivo van en 0
                datos = {
                    "codigo": nuevo_codigo,
                    "partido": partido,
                    "estrategia": "Estrategia 2: Paz Mental", # <--- ¡Nueva línea clave!
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
                        "tipo_banca": banca_activa
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
    
    if supabase is None:
        st.error("Conecta Supabase primero.")
    else:
        res = supabase.table("historial_trading").select("*").in_("estado", ["EN VIVO", "CUBIERTA"]).execute()
        ops = res.data
        
        if not ops:
            st.info("Libro mayor al día. No hay posiciones abiertas en este momento.")
        else:
            for op in ops:
                with st.expander(f"⚽ {op['partido']} | Ref: {op['codigo']} | Entorno: {op['tipo_banca']} | Estado: {op['estado']}"):
                    es_apuesta_libre = op['reserva_stake_2'] == 0
                    
                    # Nombres dinámicos extraídos de la base de datos
                    sel_ini = op.get('seleccion_inicial', 'Apuesta Inicial')
                    sel_cob = op.get('seleccion_cobertura', 'Cobertura')
                    
                    if es_apuesta_libre:
                        st.write(f"**Capital Comprometido (Libre):** ${op['capital_total']:,.0f}")
                        st.info(f"🎯 **Selección:** **{sel_ini}** a cuota **{op['cuota_inicial']:.2f}** en **{op.get('plataforma_inicial', 'N/A')}**")
                    else:
                        st.write(f"**Capital Comprometido:** ${op['capital_total']:,.0f} | **Fondo de Cobertura:** ${op['reserva_stake_2']:,.0f}")
                        st.info(f"""
                        🎯 **Stake Inicial:** A favor de **{sel_ini}** en **{op.get('plataforma_inicial', 'N/A')}**
                        🛡️ **Misión en Vivo:** Cazar **{sel_cob}** a cuota mínima de **{op['cuota_objetivo']:.2f}**
                        """)
                    
                    if op['estado'] == "EN VIVO":
                        if es_apuesta_libre:
                            # FORMULARIO SENCILLO PARA APUESTA LIBRE
                            st.write("Resolución final de la operación:")
                            with st.form(f"gestion_libre_{op['codigo']}"):
                                resultado_libre = st.radio("Resultado:", [f"✅ Ganó {sel_ini} (Cobro Completo)", "❌ Perdida (Pérdida del Capital)"])
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
                            # FORMULARIO COMPLEJO ORIGINAL PARA PAZ MENTAL
                            st.write("Seleccione la gestión de riesgo a aplicar:")
                            accion = st.radio(
                                "Acción a ejecutar:", 
                                ["Ejecutar Cobertura en Mercado (Hedge)", "Liquidar Posición Directa (Sin Cobertura)"],
                                key=f"radio_accion_{op['codigo']}"
                            )
                            
                            with st.form(f"gestion_{op['codigo']}"):
                                cuota_ingresada = 0.0
                                plataforma_cob = ""
                                resultado_directo = ""
                                
                                if accion == "Ejecutar Cobertura en Mercado (Hedge)":
                                    cuota_ingresada = st.number_input("Tasa de cobertura fijada (Cuota):", min_value=1.01, step=0.01, value=float(op['cuota_objetivo']))
                                    plataforma_cob = st.selectbox("Plataforma donde cazaste la cobertura:", todas_las_plataformas)
                                else:
                                    # BOTONES DINÁMICOS PARA CIERRE DIRECTO
                                    resultado_directo = st.radio(
                                        "¿Qué pasó con el Stake 1 (ya que no hubo cobertura)?", 
                                        [
                                            f"✅ Ganó {sel_ini} (Cobro completo)", 
                                            f"❌ Perdió {sel_ini} (Pérdida del Stake 1)"
                                        ]
                                    )

                                if st.form_submit_button("Registrar Movimiento"):
                                    if accion == "Ejecutar Cobertura en Mercado (Hedge)":
                                        supabase.table("historial_trading").update({
                                            "estado": "CUBIERTA", 
                                            "cuota_cazada_real": cuota_ingresada,
                                            "plataforma_cobertura": plataforma_cob
                                        }).eq("codigo", op['codigo']).execute()
                                        st.success("Cobertura registrada. Pendiente de liquidación.")
                                    else:
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
                                        st.success(f"Posición liquidada. Utilidad neta: ${utilidad:,.0f} COP.")
                                    st.rerun()

                    elif op['estado'] == "CUBIERTA":
                        st.success(f"🛡️ Cobertura asegurada a tasa de {op.get('cuota_cazada_real', 0):.2f} en {op.get('plataforma_cobertura', 'N/A')}.")
                        with st.form(f"liq_{op['codigo']}"):
                            
                            # BOTONES DINÁMICOS PARA LIQUIDACIÓN FINAL
                            resultado_final_ui = st.radio(
                                "Resolución del evento:", 
                                [
                                    f"✅ Pre-Partido: Ganó {sel_ini}", 
                                    f"🛡️ Cobertura: Ganó {sel_cob}", 
                                    "❌ Déficit Operativo General (Pérdida Total)"
                                ]
                            )
                            
                            if st.form_submit_button("Liquidar Posición Cubierta"):
                                # Mapeo contable (Separa lo que ves de lo que se guarda para no dañar el Módulo 3)
                                if "Pre-Partido" in resultado_final_ui:
                                    utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                    texto_db = "Efectividad de Apuesta Pre-Partido"
                                elif "Cobertura" in resultado_final_ui:
                                    utilidad = (op['reserva_stake_2'] * op['cuota_cazada_real']) - op['capital_total']
                                    texto_db = "Efectividad de Cobertura Ejecutada"
                                else:
                                    utilidad = -op['capital_total']
                                    texto_db = "Déficit Operativo General (Pérdida Total)"
                                    
                                supabase.table("historial_trading").update({
                                    "estado": "CERRADA",
                                    "resultado_final": texto_db,
                                    "utilidad_neta_real": utilidad,
                                    "roi_real": (utilidad / op['capital_total']) * 100
                                }).eq("codigo", op['codigo']).execute()
                                st.success(f"Conciliación registrada: ${utilidad:,.0f} COP.")
                                st.rerun()

        st.markdown("---")
        st.subheader("📊 Libro Mayor Contable (Historial de Cierres)")
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        if not df.empty:
            st.dataframe(df[['fecha', 'tipo_banca', 'codigo', 'partido', 'seleccion_inicial', 'resultado_final', 'utilidad_neta_real', 'roi_real']], use_container_width=True)
            
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
            # 1. Filtro por Estrategia (Asumiendo que guardaste la columna 'estrategia')
            if 'estrategia' not in df_sim.columns:
                df_sim['estrategia'] = "Estrategia 2: Paz Mental" # Fallback por si la columna es nueva
                
            estrategias_disponibles = df_sim['estrategia'].dropna().unique().tolist()
            estrategia_seleccionada = st.selectbox("📌 Selecciona la estrategia a auditar:", estrategias_disponibles)
            
            # Filtramos el dataframe
            df_est = df_sim[df_sim['estrategia'] == estrategia_seleccionada].copy()
            total_ops = len(df_est)
            
            if total_ops < 5:
                st.warning(f"⏳ Muestra Insuficiente. Tienes {total_ops} operaciones. Se requieren al menos 5 para evitar errores de varianza matemática.")
            else:
                # 2. El botón de generación de informe con el contador
                if st.button(f"📈 Generar Dictamen Cuantitativo ({total_ops} Simulaciones)"):
                    
                    st.markdown("---")
                    
                    # 3. Advertencia Profesional de Auditoría
                    if total_ops < 100:
                        st.markdown(f"""
                        <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                            <h4 style="color: #B45309; margin-top: 0;">⚠️ AVISO DE AUDITORÍA: MUESTRA EN DESARROLLO</h4>
                            <p style="color: #92400E; margin-bottom: 0;">
                                Este dictamen preliminar cuenta con <b>{total_ops} operaciones</b>. El estándar exige un mínimo de <b>100 eventos</b> para mitigar la desviación estándar y considerar los datos estadísticamente viables. Las siguientes métricas son orientativas.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success("✅ VALIDACIÓN INSTITUCIONAL: La muestra estadística supera las 100 operaciones. El margen de error se considera aceptable para la toma de decisiones.")

                    # 4. Cálculos de Eficiencia Operativa (Tu motor matemático)
                    victorias_pre_partido = df_est['resultado_final'].str.contains("Pre-Partido", case=False, na=False).sum()
                    victorias_cobertura = df_est['resultado_final'].str.contains("Cobertura Ejecutada", case=False, na=False).sum()
                    derrotas_totales = df_est['resultado_final'].str.contains("Déficit|Perdid", case=False, na=False).sum()
                    
                    win_rate = (victorias_pre_partido / total_ops) * 100
                    frecuencia_rescate = (victorias_cobertura / total_ops) * 100
                    loss_rate = (derrotas_totales / total_ops) * 100
                    cuota_promedio = df_est['cuota_inicial'].mean()
                    
                    # 5. Cálculos de Riesgo Institucional
                    roi_promedio = df_est['roi_real'].mean()
                    volatilidad_roi = df_est['roi_real'].std() if total_ops > 1 else 0
                    
                    ev = ((win_rate / 100) * (cuota_promedio - 1)) - (loss_rate / 100)
                    sharpe_ratio = (roi_promedio / volatilidad_roi) if volatilidad_roi > 0 else 0
                    
                    # Cálculo de Max Drawdown Real
                    df_est = df_est.sort_values(by='fecha')
                    df_est['acumulado_utilidad'] = df_est['utilidad_neta_real'].cumsum()
                    df_est['pico_historico'] = df_est['acumulado_utilidad'].cummax()
                    df_est['drawdown'] = df_est['pico_historico'] - df_est['acumulado_utilidad']
                    max_drawdown_cop = df_est['drawdown'].max()
                    
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
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Volumen Analizado", f"{total_ops} Ops")
                    c2.metric("Efectividad Inicial", f"{win_rate:.1f}%")
                    c3.metric("Frecuencia de Rescate", f"{frecuencia_rescate:.1f}%")
                    c4.metric("Tasa de Fracaso", f"{loss_rate:.1f}%")