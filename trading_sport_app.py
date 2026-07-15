import streamlit as st
import pandas as pd
import numpy as np
import random
import string
import joblib
from supabase import create_client, Client
import streamlit as st
import pandas as pd
import joblib
import os

# --- CARGADOR DE LOS CEREBROS DE IA ---
@st.cache_resource
def cargar_oraculos():
    m_1x2 = joblib.load('modelo_pre_1x2.pkl')
    m_goles = joblib.load('modelo_pre_goles.pkl')
    m_btts = joblib.load('modelo_pre_btts.pkl')
    return m_1x2, m_goles, m_btts

try:
    modelo_1x2, modelo_goles, modelo_btts = cargar_oraculos()
    modelos_cargados = True
except Exception as e:
    modelos_cargados = False

st.set_page_config(page_title="Sistema de Trading y Auditoría COP", page_icon="⚖️", layout="wide")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase: Client = init_connection()

# --- FUNCIONES AUXILIARES BLINDADAS ---
def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def safe_float(val):
    """Aspiradora: Convierte cualquier basura, espacio, coma o nulo en un 0.0 seguro"""
    if val is None: return 0.0
    if isinstance(val, str):
        val = val.replace(',', '').strip()
        if val == '': return 0.0
    try:
        return float(val)
    except:
        return 0.0

def obtener_saldo_banca(tipo_banca: str) -> float:
    if supabase is None: return 0.0
    try:
        # 1. Sumar movimientos de caja (Aspiradora activada)
        res_movs = supabase.table("movimientos_caja").select("tipo_movimiento", "monto").eq("tipo_banca", tipo_banca).execute()
        total_caja = sum(round(safe_float(m.get('monto'))) if str(m.get('tipo_movimiento')) == "CONSIGNACION" else -round(safe_float(m.get('monto'))) for m in res_movs.data)
        
        # 2. Utilidades CERRADAS
        res_ops_cerradas = supabase.table("historial_trading").select("utilidad_neta_real").eq("tipo_banca", tipo_banca).eq("estado", "CERRADA").execute()
        total_utilidad = sum(round(safe_float(op.get('utilidad_neta_real'))) for op in res_ops_cerradas.data)
        
        # 3. Capital retenido en abiertas
        res_ops_abiertas = supabase.table("historial_trading").select("estado", "capital_total", "stake_1", "reserva_stake_2", "estrategia", "cuota_inicial", "cuota_cazada_real", "es_dutching", "stake_dutch_base", "stake_dutch_empate").eq("tipo_banca", tipo_banca).in_("estado", ["EN VIVO", "CUBIERTA"]).execute()
        capital_retenido = 0.0
        
        for op in res_ops_abiertas.data:
            estado = str(op.get('estado') or '')
            es_dutch = op.get('es_dutching', False)
            
            if es_dutch:
                cap_fase1 = round(safe_float(op.get('stake_dutch_base'))) + round(safe_float(op.get('stake_dutch_empate')))
            else:
                cap_fase1 = round(safe_float(op.get('stake_1'))) or round(safe_float(op.get('capital_total')))
            
            capital_retenido += cap_fase1
            
            if estado == "CUBIERTA":
                c_ini = safe_float(op.get('cuota_inicial')) or 1.0
                c_caz = safe_float(op.get('cuota_cazada_real'))
                if "eSports" in str(op.get('estrategia') or '') and c_caz > 0:
                    capital_retenido += round((cap_fase1 * c_ini) / c_caz)
                else:
                    capital_retenido += round(safe_float(op.get('reserva_stake_2')))
                    
        return total_caja + total_utilidad - capital_retenido
    except Exception:
        return 0.0

# 🧠 NUEVO MOTOR: TRAZABILIDAD CRUZADA POR PLATAFORMA (CONTABILIDAD DOBLE ASIENTO)
def obtener_saldos_por_plataforma(tipo_banca: str) -> pd.DataFrame:
    if supabase is None: return pd.DataFrame()
    try:
        saldos = {}
        
        # 1. Movimientos Manuales (Consignaciones y Retiros)
        res_movs = supabase.table("movimientos_caja").select("tipo_movimiento", "monto", "plataforma").eq("tipo_banca", tipo_banca).execute()
        for m in res_movs.data:
            p = str(m.get('plataforma') or 'Sin Especificar').strip()
            if p not in saldos: saldos[p] = 0.0
            if str(m.get('tipo_movimiento')) == "CONSIGNACION":
                saldos[p] += round(safe_float(m.get('monto')))
            else:
                saldos[p] -= round(safe_float(m.get('monto')))
                
        # 2. Operaciones Históricas (Auditoría Unificada de Flujos)
        res_ops = supabase.table("historial_trading").select("*").eq("tipo_banca", tipo_banca).execute()
        for op in res_ops.data:
            p_ini = str(op.get('plataforma_inicial') or 'Sin Especificar').strip()
            p_cob = str(op.get('plataforma_cobertura') or 'Sin Especificar').strip()
            p_dutch = str(op.get('plataforma_dutch_secundaria') or 'Sin Especificar').strip()
            
            if p_ini not in saldos: saldos[p_ini] = 0.0
            if p_cob not in saldos and p_cob != 'Sin Especificar': saldos[p_cob] = 0.0
            if p_dutch not in saldos and p_dutch != 'Sin Especificar': saldos[p_dutch] = 0.0
            
            estado = str(op.get('estado') or '')
            res_fin = str(op.get('resultado_final') or '')
            estrategia = str(op.get('estrategia') or '')
            es_dutching = op.get('es_dutching', False)
            
            # Recaudación de Stakes vía Aspiradora
            util_neta = round(safe_float(op.get('utilidad_neta_real')))
            stake_base = round(safe_float(op.get('stake_dutch_base')))
            stake_emp = round(safe_float(op.get('stake_dutch_empate')))
            stake_1 = round(safe_float(op.get('stake_1'))) or round(safe_float(op.get('capital_total')))
            
            c_ini = safe_float(op.get('cuota_inicial')) or 1.0
            c_caz = safe_float(op.get('cuota_cazada_real'))
            
            monto_cob = round(safe_float(op.get('reserva_stake_2')))
            if ("eSports" in estrategia or "Binario" in estrategia) and c_caz > 0:
                monto_cob = round((stake_1 * c_ini) / c_caz)

            # -------------------------------------------------------------
            # PASO A: REGISTRO DEL EGRESO (Aplica a Abiertas, Cubiertas y Cerradas)
            # -------------------------------------------------------------
            if es_dutching:
                saldos[p_ini] -= stake_base
                if p_dutch != 'Sin Especificar': saldos[p_dutch] -= stake_emp
            else:
                saldos[p_ini] -= stake_1
                
            # Si la operación requirió cobertura (en curso o ejecutada históricamente)
            if estado == "CUBIERTA" or (estado == "CERRADA" and p_cob != 'Sin Especificar' and monto_cob > 0 and "Directo" not in res_fin and "Libre" not in res_fin):
                if p_cob != 'Sin Especificar':
                    saldos[p_cob] -= monto_cob

            # -------------------------------------------------------------
            # PASO B: REGISTRO DEL INGRESO (Sólo aplica a Cerradas que generaron retorno)
            # -------------------------------------------------------------
            if estado == "CERRADA":
                # Determinación de la masa de capital total indexada a la operación
                capital_total_operacion = (stake_base + stake_emp) if es_dutching else stake_1
                if p_cob != 'Sin Especificar' and monto_cob > 0 and "Directo" not in res_fin and "Libre" not in res_fin:
                    capital_total_operacion += monto_cob
                
                # Ecuación Contable de Retorno Bruto (Inflows)
                retorno_bruto = util_neta + capital_total_operacion
                
                # CONDICIÓN 1: Pérdida Total (Siniestro Absoluto) -> Retorno es $0
                if any(k in res_fin for k in ["Déficit", "Pérdida Total", "Perdió Inicial", "Libre Perdida", "Pérdida de Stake"]):
                    pass # No hay ingresos que retornar a ninguna cuenta
                    
                # CONDICIÓN 2: Ganó el Seguro / Cobertura
                elif any(k in res_fin for k in ["Fondo de Cobertura", "Seguro Acertado", "Utilidad Seguro en"]):
                    if p_cob != 'Sin Especificar':
                        saldos[p_cob] += retorno_bruto
                        
                # CONDICIÓN 3: Ganó la selección de la Fase 1
                else:
                    if es_dutching and p_dutch != 'Sin Especificar' and f"[{p_dutch}]" in res_fin:
                        saldos[p_dutch] += retorno_bruto
                    else:
                        saldos[p_ini] += retorno_bruto

        df = pd.DataFrame(list(saldos.items()), columns=['Casa de Apuestas', 'Saldo Actual (COP)'])
        if df.empty: return df
        df = df[df['Saldo Actual (COP)'].abs() > 0.1]
        return df.sort_values(by='Saldo Actual (COP)', ascending=False)
        
    except Exception as e:
        st.error(f"🚨 Error matemático en Caja ({tipo_banca}): {str(e)}")
        return pd.DataFrame()

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
        "⚡ Estrategia 1: eSports (Scalping)", 
        "2️⃣ Estrategia 2: Paz Mental (Fútbol)", 
        "3️⃣ Estrategia 3: Binario Personalizado",
        "🔒 Seguimiento y Liquidación de Posiciones",
        "🔬 Auditoría Cuantitativa (Reporte)",
        "🔮 Oráculo Predictivo (Machine Learning)" # <--- EL ORÁCULO AÑADIDO
    ]
)

# Indicadores de saldos fijos en la barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Banca Real:** ${saldo_real:,.0f} COP")
st.sidebar.markdown(f"**Banca Simulación:** ${saldo_simulacion:,.0f} COP")

# Configuración de Riesgo Personalizado Independiente
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Umbrales de Riesgo")
max_riesgo_real = st.sidebar.slider("Exposición máxima Dinero Real (%):", min_value=5, max_value=100, value=10, step=5)
max_riesgo_simulacion = st.sidebar.slider("Exposición máxima Simulación (%):", min_value=5, max_value=100, value=30, step=5)

st.title("⚖️ Sistema de Trading Automático")

# =====================================================================
# MÓDULO: GESTIÓN DE CAPITAL (CONSIGNAR Y RETIRAR)
# =====================================================================
if estrategia_activa == "💰 Gestión de Capital (Caja)":
    st.markdown("### 💰 Control de Flujos y Patrimonio por Plataforma")
    st.write("El sistema deduce automáticamente cuánto dinero tienes en cada casa cruzando fondeos con los resultados de tus coberturas.")
    
    tab_real, tab_sim = st.tabs(["🟢 BANCA REAL", "🟡 BANCA DE SIMULACIÓN"])
    
    with tab_real:
        col_kpi, col_table = st.columns([1, 1.5])
        with col_kpi:
            st.markdown(f'<div class="kpi-banca" style="height: 100%;"><h5>DISPONIBLE GLOBAL REAL</h5><h2 style="color:#10B981;">${saldo_real:,.0f} COP</h2><p style="font-size:0.8rem; color:#64748B;">Patrimonio Neto Total</p></div>', unsafe_allow_html=True)
        with col_table:
            df_plat_real = obtener_saldos_por_plataforma("REAL")
            if not df_plat_real.empty:
                st.write("**Distribución actual del dinero por casa:**")
                df_real_fmt = df_plat_real.copy()
                # Formateamos a dinero y aseguramos que no explote
                df_real_fmt['Saldo Actual (COP)'] = df_real_fmt['Saldo Actual (COP)'].apply(lambda x: f"${float(x):,.0f}")
                # Hacemos que la casa sea el índice para ocultar los números laterales
                df_real_fmt = df_real_fmt.set_index('Casa de Apuestas')
                # 🛑 ESCUDO ANTI-CRASH: Usamos HTML puro estático, evadimos PyArrow
                st.table(df_real_fmt)
            else:
                st.info("No hay dinero distribuido en plataformas.")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("consignar_real"):
                st.markdown("#### 📥 Registrar Depósito en Casa")
                plat_in = st.selectbox("¿En qué casa vas a fondear?", todas_las_plataformas)
                plat_in_otra = st.text_input("Especificar plataforma:") if plat_in == "Otra" else ""
                monto = st.number_input("Monto a Consignar (COP):", min_value=5000, step=5000, value=10000)
                
                if st.form_submit_button("Fijar Depósito (Banca Real)"):
                    plataforma_final = plat_in_otra if plat_in == "Otra" else plat_in
                    if not plataforma_final:
                        st.error("Debes especificar la plataforma.")
                    else:
                        supabase.table("movimientos_caja").insert({
                            "tipo_banca": "REAL", 
                            "tipo_movimiento": "CONSIGNACION", 
                            "monto": monto,
                            "plataforma": plataforma_final
                        }).execute()
                        st.success(f"Depósito de ${monto:,.0f} en {plataforma_final} registrado.")
                        st.rerun()
                        
        with c2:
            with st.form("retirar_real"):
                st.markdown("#### 📤 Registrar Retiro de Ganancias")
                plat_out = st.selectbox("¿De qué casa retiras dinero?", todas_las_plataformas)
                plat_out_otra = st.text_input("Especificar plataforma:") if plat_out == "Otra" else ""
                monto = st.number_input("Monto a Retirar (COP):", min_value=5000, step=5000, value=10000)
                
                if st.form_submit_button("Fijar Retiro (Banca Real)"):
                    plataforma_final = plat_out_otra if plat_out == "Otra" else plat_out
                    if not plataforma_final:
                        st.error("Debes especificar la plataforma.")
                    elif monto > saldo_real:
                        st.error("El monto supera el patrimonio global disponible.")
                    else:
                        supabase.table("movimientos_caja").insert({
                            "tipo_banca": "REAL", 
                            "tipo_movimiento": "RETIRO", 
                            "monto": monto,
                            "plataforma": plataforma_final
                        }).execute()
                        st.success(f"Retiro de ${monto:,.0f} desde {plataforma_final} registrado.")
                        st.rerun()
                        
    with tab_sim:
        col_kpi_s, col_table_s = st.columns([1, 1.5])
        with col_kpi_s:
            st.markdown(f'<div class="kpi-banca" style="height: 100%;"><h5>DISPONIBLE SIMULACIÓN</h5><h2 style="color:#F59E0B;">${saldo_simulacion:,.0f} COP</h2><p style="font-size:0.8rem; color:#64748B;">Patrimonio Virtual</p></div>', unsafe_allow_html=True)
        with col_table_s:
            df_plat_sim = obtener_saldos_por_plataforma("SIMULACION")
            if not df_plat_sim.empty:
                st.write("**Distribución virtual por casa:**")
                df_sim_fmt = df_plat_sim.copy()
                df_sim_fmt['Saldo Actual (COP)'] = df_sim_fmt['Saldo Actual (COP)'].apply(lambda x: f"${float(x):,.0f}")
                df_sim_fmt = df_sim_fmt.set_index('Casa de Apuestas')
                # 🛑 ESCUDO ANTI-CRASH: Usamos HTML puro estático
                st.table(df_sim_fmt)
            else:
                st.info("No hay dinero distribuido en simulación.")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("consignar_sim"):
                st.markdown("#### 📥 Fondeo Virtual")
                plat_in = st.selectbox("Plataforma simulada:", todas_las_plataformas)
                plat_in_otra = st.text_input("Especificar plataforma:") if plat_in == "Otra" else ""
                monto = st.number_input("Monto a Consignar (COP):", min_value=5000, step=5000, value=50000)
                
                if st.form_submit_button("Fijar Fondeo Virtual"):
                    plataforma_final = plat_in_otra if plat_in == "Otra" else plat_in
                    supabase.table("movimientos_caja").insert({
                        "tipo_banca": "SIMULACION", 
                        "tipo_movimiento": "CONSIGNACION", 
                        "monto": monto,
                        "plataforma": plataforma_final
                    }).execute()
                    st.success(f"Fondeo de ${monto:,.0f} a {plataforma_final} exitoso.")
                    st.rerun()
                    
        with c2:
            with st.form("retirar_sim"):
                st.markdown("#### 📤 Retiro Virtual")
                plat_out = st.selectbox("Plataforma simulada:", todas_las_plataformas)
                plat_out_otra = st.text_input("Especificar plataforma:") if plat_out == "Otra" else ""
                monto = st.number_input("Monto a Retirar (COP):", min_value=5000, step=5000, value=50000)
                
                if st.form_submit_button("Fijar Retiro Virtual"):
                    plataforma_final = plat_out_otra if plat_out == "Otra" else plat_out
                    if monto > saldo_simulacion:
                        st.error("Fondos simulados globales insuficientes.")
                    else:
                        supabase.table("movimientos_caja").insert({
                            "tipo_banca": "SIMULACION", 
                            "tipo_movimiento": "RETIRO", 
                            "monto": monto,
                            "plataforma": plataforma_final
                        }).execute()
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

    # Definir cuál umbral respetar según la banca
    umbral_riesgo_actual = max_riesgo_real if banca_activa == "REAL" else max_riesgo_simulacion

    if saldo_disponible > 0:
        porcentaje_exposicion = (capital_total / saldo_disponible) * 100
        if porcentaje_exposicion > umbral_riesgo_actual:
            st.warning(f"⚠️ Alerta de Exposición: Esta operación compromete el {porcentaje_exposicion:.1f}% de la banca disponible, superando el umbral de {umbral_riesgo_actual}%.")

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
# MÓDULO 1.0: PAZ MENTAL + GUARDADO (MOTOR DE ARBITRAJE INTEGRADO)
# =====================================================================
elif estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Fútbol)":
    st.info("**Lógica:** Auditoría financiera previa, configuración de capital y trazabilidad operativa con control de Stop Loss.")
    
    tipo_banca_op = st.radio("Entorno de ejecución:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True)
    banca_activa = "REAL" if "Real" in tipo_banca_op else "SIMULACION"
    saldo_disponible = saldo_real if banca_activa == "REAL" else saldo_simulacion
    
    # --- SELECTOR DE ENFOQUE (TRES VARIANTES - CERO ESPORTS) ---
    st.markdown("---")
    enfoque_operativo = st.radio(
        "🎯 Enfoque de Mercado (Determina el libro de auditoría):",
        [
            "🔵 Clásico (Pre-partido a Favorito/Empate)", 
            "🔴 Inverso (Pre-partido a Sorpresa/Empate)",
            "🔥 Fuego Cruzado (Cualquiera Gana - Cazar Empate)"
        ],
        horizontal=False
    )
    
    # Asignación del nombre para la base de datos
    if "Fuego" in enfoque_operativo:
        nombre_estrategia_bd = "Estrategia 2: Fuego Cruzado"
    elif "Clásico" in enfoque_operativo:
        nombre_estrategia_bd = "Estrategia 2: Clásica"
    else:
        nombre_estrategia_bd = "Estrategia 2: Inversa"
    
    # Cambio dinámico de etiquetas según la estrategia
    if "Fuego" in enfoque_operativo:
        lab_gana = "1. Gana Local"
        lab_empate = "2. Gana Visitante"
        lab_dc = "3. Doble Oportunidad (12)"
        lab_rival = "4. Empate (Amenaza)"
    else:
        lab_gana = "1. Gana Tu Equipo"
        lab_empate = "2. Empate (X)"
        lab_dc = "3. Doble Oportunidad"
        lab_rival = "4. Gana Rival (Amenaza)"

    # Variables de texto maestras para la UI
    str_selec_1 = "Gana Local" if "Fuego" in enfoque_operativo else "Gana tu Equipo"
    str_selec_2 = "Gana Visitante" if "Fuego" in enfoque_operativo else "Empate"
    str_amenaza = "Empate" if "Fuego" in enfoque_operativo else "Rival"
    str_dc = "12 (Local/Visita)" if "Fuego" in enfoque_operativo else "Gana/Empata"

    # =================================================================
    # ⚖️ MOTOR DE ARBITRAJE (DUTCHING CALCULATOR)
    # =================================================================
    st.markdown("---")
    st.markdown("### ⚖️ 1. Motor de Arbitraje (Auditoría de Cuotas)")
    
    col_odd1, col_odd2, col_odd3, col_odd4 = st.columns(4)
    with col_odd1:
        cuota_gana = st.number_input(lab_gana, min_value=1.01, value=2.00, step=0.05)
    with col_odd2:
        cuota_empate = st.number_input(lab_empate, min_value=1.01, value=2.80 if "Fuego" in enfoque_operativo else 3.65, step=0.05)
    with col_odd3:
        cuota_dc_casa = st.number_input(lab_dc, min_value=1.01, value=1.35 if "Fuego" in enfoque_operativo else 1.26, step=0.01)
    with col_odd4:
        cuota_rival = st.number_input(lab_rival, min_value=1.01, value=3.20 if "Fuego" in enfoque_operativo else 4.00, step=0.05)

    prob_gana = 1.0 / cuota_gana
    prob_empate = 1.0 / cuota_empate
    prob_total = prob_gana + prob_empate
    cuota_sintetica = 1.0 / prob_total

    diferencia_cuotas = cuota_sintetica - cuota_dc_casa

    if diferencia_cuotas > 0.01:
        usar_dutching = True
        cuota_efectiva = cuota_sintetica
        st.success(f"🚨 **INEFICIENCIA DETECTADA:** La cuota sintética es **{cuota_sintetica:.3f}**. Le ganas {diferencia_cuotas:.3f} de ventaja a la casa. **El sistema dividirá tu apuesta por separado.**")
    else:
        usar_dutching = False
        cuota_efectiva = cuota_dc_casa
        if diferencia_cuotas < -0.01:
            st.info(f"✅ **CUOTA JUSTA:** La casa te está pagando mejor (**{cuota_dc_casa:.2f}**) que apostar por separado ({cuota_sintetica:.3f}). **Doble Oportunidad en 1 sola casa.**")
        else:
            st.info(f"⚖️ **MERCADO BALANCEADO:** No hay ventaja matemática en separar la apuesta. **Doble Oportunidad en 1 sola casa.**")

    # =================================================================
    # 💰 CONFIGURACIÓN DE CAPITAL Y GESTIÓN DE RIESGO
    # =================================================================
    st.markdown("---")
    st.markdown("### 💰 2. Asignación de Capital y Riesgo")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        capital_total = st.number_input("Capital Total (COP)", min_value=10000, value=min(50000, int(saldo_disponible)) if saldo_disponible > 10000 else 10000, step=5000)
    with col2:
        utilidad_esperada = st.slider("Utilidad Deseada (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)
    with col3:
        porcentaje_perdida = st.slider("Stop Loss Máximo (% de pérdida):", min_value=1.0, max_value=50.0, value=20.0, step=1.0)

    riesgo = st.slider("Exigencia en Cobertura (0% = Librar, 100% = Ganancia Igualada):", min_value=0, max_value=100, value=50, step=10)

    # Definir cuál umbral respetar según la banca
    umbral_riesgo_actual = max_riesgo_real if banca_activa == "REAL" else max_riesgo_simulacion

    if saldo_disponible > 0:
        porcentaje_exposicion = (capital_total / saldo_disponible) * 100
        
        if porcentaje_exposicion > umbral_riesgo_actual: 
            st.warning(f"⚠️ Alerta de Exposición: Comprometes el {porcentaje_exposicion:.1f}% de tu banca. Superas el umbral de {umbral_riesgo_actual}%.")
            
    # Matemática Financiera Base
    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total
    stake_1 = retorno_objetivo_1 / cuota_efectiva
    stake_2 = capital_total - stake_1

    # Cálculos de partición (Dutching)
    if usar_dutching:
        stake_base = stake_1 * (cuota_empate / (cuota_gana + cuota_empate))
        stake_emp_dutch = stake_1 * (cuota_gana / (cuota_gana + cuota_empate))
    else:
        stake_base = stake_1
        stake_emp_dutch = 0

    # =================================================================
    # 🏢 ENRUTAMIENTO DE CAPITAL (NUEVO MÓDULO)
    # =================================================================
    st.markdown("---")
    st.markdown("### 🏢 3. Enrutamiento de Capital (Plataformas)")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        plat_1 = st.selectbox(f"🏦 Plataforma para {str_selec_1 if usar_dutching else str_dc}:", ["BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Otra"], key="plat1")
        if plat_1 == "Otra": plat_1 = st.text_input("Especifica plataforma 1:", key="otra1")
    
    with col_p2:
        if usar_dutching:
            plat_2 = st.selectbox(f"🏦 Plataforma para {str_selec_2}:", ["BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Otra"], key="plat2")
            if plat_2 == "Otra": plat_2 = st.text_input("Especifica plataforma 2:", key="otra2")
        else:
            st.info("🔒 Al usar Doble Oportunidad, todo el Ticket de Fase 1 pertenece a la misma plataforma.")
            plat_2 = plat_1

    st.markdown("---")

    if stake_2 < 5000:
        st.markdown(f'<div class="error-caja"><b>🚨 RESTRICCIÓN:</b> Reserva menor a $5,000. Ajusta el capital o utilidad.</div>', unsafe_allow_html=True)
    elif capital_total > saldo_disponible:
        st.markdown(f'<div class="error-caja"><b>🚨 SALDO INSUFICIENTE:</b> El capital configurado supera el saldo disponible.</div>', unsafe_allow_html=True)
    else:
        # CÁLCULOS TÁCTICOS: Take Profit, Break-Even y Stop Loss
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        
        cuota_break_even = capital_total / stake_2
        
        salvavidas_requerido = capital_total * (1 - (porcentaje_perdida / 100.0))
        cuota_stop_loss = salvavidas_requerido / stake_2

        st.markdown(f"""
        <div style="background-color: #EFF6FF; border-left: 4px solid #3B82F6; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 0.95rem; color: #1E3A8A;">⚖️ <b>Punto de Equilibrio (Break-Even):</b> Si cazas a {str_amenaza} a una cuota exacta de <b>{cuota_break_even:.2f}</b>, recuperas el 100% de tu capital (${capital_total:,.0f} COP) saliendo sin ganancias ni pérdidas.</p>
        </div>
        """, unsafe_allow_html=True)

        cols_plan = st.columns(3)
        
        with cols_plan[0]:
            if usar_dutching:
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px;">
                    <h4 style="margin-top:0;">Fase 1: Pre-partido</h4>
                    <p style="margin:0;">Stake 1 Total (<b>${stake_1:,.0f} COP</b>):</p>
                    <ul style="margin-top: 5px; margin-bottom: 5px; font-size:0.9rem;">
                        <li><b>${stake_base:,.0f}</b> ➔ {str_selec_1} <span style="color:#2563EB;">[{plat_1}]</span></li>
                        <li><b>${stake_emp_dutch:,.0f}</b> ➔ {str_selec_2} <span style="color:#2563EB;">[{plat_2}]</span></li>
                    </ul>
                    <hr style="margin: 10px 0;">
                    <p style="margin:0; font-size:0.85rem; color:#475569;">Cajón Reserva: <b>${stake_2:,.0f} COP</b></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px;">
                    <h4 style="margin-top:0;">Fase 1: Pre-partido</h4>
                    <p style="margin:0;">Ticket Directo:</p>
                    <ul style="margin-top: 5px; margin-bottom: 5px; font-size:0.9rem;">
                        <li><b>${stake_1:,.0f}</b> ➔ {str_dc} a cuota {cuota_efectiva:.2f} <span style="color:#2563EB;">[{plat_1}]</span></li>
                    </ul>
                    <hr style="margin: 10px 0;">
                    <p style="margin:0; font-size:0.85rem; color:#475569;">Cajón Reserva: <b>${stake_2:,.0f} COP</b></p>
                </div>
                """, unsafe_allow_html=True)
                
        with cols_plan[1]:
            st.markdown(f"""
            <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 15px; border-radius: 4px; text-align: center;">
                <h4 style="margin-top:0; color:#15803D;">Take Profit (Ganancia)</h4>
                <p style="margin:0; font-size:0.85rem;">Si la cuota de {str_amenaza} <b>SUBE</b> a:</p>
                <h1 style="color:#15803D; font-size:2.2rem; margin:10px 0;">{cuota_a_cazar:.2f}</h1>
                <p style="margin:0; font-size: 0.75rem; color:#475569;">Cazas con tu Reserva Completa</p>
            </div>
            """, unsafe_allow_html=True)

        with cols_plan[2]:
            st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 4px; text-align: center;">
                <h4 style="margin-top:0; color:#B91C1C;">Stop Loss (Pánico)</h4>
                <p style="margin:0; font-size:0.85rem;">Si la cuota de {str_amenaza} <b>BAJA</b> a:</p>
                <h1 style="color:#B91C1C; font-size:2.2rem; margin:10px 0;">{cuota_stop_loss:.2f}</h1>
                <p style="margin:0; font-size: 0.75rem; color:#475569;">Salvas el {100-porcentaje_perdida:.0f}% de tu caja</p>
            </div>
            """, unsafe_allow_html=True)

        # =================================================================
        # 💾 REGISTRO CONTABLE 
        # =================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💾 4. Detalles del Partido y Registro")
        with st.form("guardar_operacion"):
            
            if "Fuego" in enfoque_operativo:
                st.info("💡 **Fuego Cruzado:** Escribe en la Caja 1 el Local y en la Caja 2 el Visitante.")
            else:
                st.info("💡 **Regla Fija:** Escribe en la Caja 1 tu selección base. Escribe en la Caja 2 el equipo rival (la amenaza).")
            
            c_eq1, c_eq2 = st.columns(2)
            with c_eq1:
                eq_apuesta_inicial = st.text_input("⚽ Equipo Local" if "Fuego" in enfoque_operativo else "⚽ Equipo Apuesta Inicial")
            with c_eq2:
                eq_cobertura = st.text_input("🚀 Equipo Visitante" if "Fuego" in enfoque_operativo else "🎯 Equipo Amenaza")
            
            hora_inicio = st.time_input("⏱️ Hora de inicio del partido:")

            if st.form_submit_button("Generar Código e Iniciar Auditoría"):
                if not eq_apuesta_inicial or not eq_cobertura:
                    st.error("Debes ingresar los nombres de los equipos en ambas cajas.")
                else:
                    import random, string
                    nuevo_codigo = f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(100, 999)}"
                    
                    # Textos para la Base de Datos con trazabilidad de plataformas
                    if "Fuego" in enfoque_operativo:
                        if usar_dutching:
                            seleccion_ini = f"Dutching: Gana {eq_apuesta_inicial} [{plat_1}] + Gana {eq_cobertura} [{plat_2}]"
                        else:
                            seleccion_ini = f"Doble Oportunidad (12): {eq_apuesta_inicial}/{eq_cobertura} [{plat_1}]"
                        seleccion_cob = "Empate (X)"
                    else:
                        if usar_dutching:
                            seleccion_ini = f"Dutching: {eq_apuesta_inicial} [{plat_1}] + Empate [{plat_2}]"
                        else:
                            seleccion_ini = f"Doble Oportunidad: {eq_apuesta_inicial} [{plat_1}]"
                        seleccion_cob = f"Gana {eq_cobertura}"
                    
                    audit_empate = cuota_rival if "Fuego" in enfoque_operativo else cuota_empate
                    audit_amenaza = cuota_empate if "Fuego" in enfoque_operativo else cuota_rival

                    datos = {
                        "codigo": nuevo_codigo,
                        "partido": f"{eq_apuesta_inicial} vs {eq_cobertura}",
                        "estrategia": nombre_estrategia_bd,
                        "seleccion_inicial": seleccion_ini,
                        "seleccion_cobertura": seleccion_cob,
                        "plataforma_inicial": plat_1,
                        "plataforma_dutch_secundaria": plat_2 if usar_dutching else "",
                        "capital_total": capital_total,
                        "cuota_inicial": round(cuota_efectiva, 3),
                        "stake_1": stake_1,
                        "reserva_stake_2": stake_2,
                        "cuota_objetivo": cuota_a_cazar,
                        "cuota_stop_loss": cuota_stop_loss,
                        "estado": "EN VIVO",
                        "tipo_banca": banca_activa,
                        "hora_inicio_partido": hora_inicio.strftime("%H:%M"),
                        "cuota_base_audit": cuota_gana,
                        "cuota_empate_audit": audit_empate, 
                        "cuota_dc_audit": cuota_dc_casa,
                        "cuota_amenaza_audit": audit_amenaza, 
                        "es_dutching": usar_dutching,
                        "stake_dutch_base": round(stake_base, 2),
                        "stake_dutch_empate": round(stake_emp_dutch, 2)
                    }
                    try:
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f'<div class="caja-codigo"><h3>Código ({banca_activa}): {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error de Supabase: {str(e)}")

# =====================================================================
# MÓDULO 1: ESPORTS SCALPING (PLANEACIÓN Y AUDITORÍA PREVIA)
# =====================================================================
elif estrategia_activa == "⚡ Estrategia 1: eSports (Scalping)":
    st.info("**Lógica:** Inversión inicial definida. La inyección de cobertura se calculará dinámicamente en vivo.")
    
    tipo_banca_op = st.radio("Entorno de ejecución:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True)
    banca_activa = "REAL" if "Real" in tipo_banca_op else "SIMULACION"
    saldo_disponible = saldo_real if banca_activa == "REAL" else saldo_simulacion
    
    # --- SELECTOR DE ENFOQUE (LAS 4 CAUSALES) ---
    st.markdown("---")
    enfoque_operativo = st.radio(
        "🎯 Enfoque de Mercado (Determina el libro de auditoría):",
        [
            "🔵 Gana Favorito (Pre-partido a Favorito/Empate)", 
            "🔴 Gana No Favorito (Pre-partido a Sorpresa/Empate)",
            "🔥 Ninguno Gana (Fuego Cruzado - Cazar Empate)",
            "⚽ Mercado de Goles (Menos de X vs Más de X)"
        ],
        horizontal=False
    )
    
    nombre_estrategia_bd = "Estrategia 1: eSports Scalping"
    
    # Cambio dinámico de etiquetas
    if "Goles" in enfoque_operativo:
        periodo_goles = st.radio("⏱️ Periodo del Mercado:", ["Primer Tiempo (PT)", "Partido Completo (FT)"], horizontal=True)
        linea_goles = st.number_input(f"Línea de Goles (X) para {periodo_goles}:", value=1.5, step=0.5)
        lab_gana = f"1. Menos de {linea_goles} Goles (Inicial)"
        lab_rival = f"2. Más de {linea_goles} Goles (Amenaza)"
        lab_empate = "" # No aplica
    elif "Ninguno" in enfoque_operativo:
        lab_gana = "1. Gana Local"
        lab_empate = "2. Gana Visitante"
        lab_rival = "3. Empate (Amenaza)"
    else:
        lab_gana = "1. Gana Tu Equipo"
        lab_empate = "2. Empate (X)"
        lab_rival = "3. Gana Rival (Amenaza)"

    # =================================================================
    # ⚖️ 1. CONSTRUCCIÓN DE CUOTA
    # =================================================================
    st.markdown("---")
    st.markdown("### ⚖️ 1. Construcción de Cuota")
    
    if "Goles" in enfoque_operativo:
        col_odd1, col_odd2 = st.columns(2)
        with col_odd1:
            cuota_gana = st.number_input(lab_gana, min_value=1.01, value=1.85, step=0.05)
        with col_odd2:
            cuota_rival = st.number_input(lab_rival, min_value=1.01, value=2.10, step=0.05)
            
        cuota_efectiva = cuota_gana
        cuota_empate = 0.0
        usar_dutching = False
        st.success(f"⚙️ **CUOTA DIRECTA:** Tu cuota de entrada es **{cuota_efectiva:.3f}**. Mercado de 2 vías sin Dutching.")
    else:
        col_odd1, col_odd2, col_odd3 = st.columns(3)
        with col_odd1:
            cuota_gana = st.number_input(lab_gana, min_value=1.01, value=2.00, step=0.05)
        with col_odd2:
            cuota_empate = st.number_input(lab_empate, min_value=1.01, value=2.80 if "Ninguno" in enfoque_operativo else 3.65, step=0.05)
        with col_odd3:
            cuota_rival = st.number_input(lab_rival, min_value=1.01, value=3.20 if "Ninguno" in enfoque_operativo else 4.00, step=0.05)

        prob_gana = 1.0 / cuota_gana
        prob_empate = 1.0 / cuota_empate
        prob_total = prob_gana + prob_empate
        cuota_efectiva = 1.0 / prob_total
        usar_dutching = True
        st.success(f"⚙️ **CUOTA SINTÉTICA:** Tu cuota efectiva de entrada es **{cuota_efectiva:.3f}**. El sistema dividirá el capital automáticamente.")

    # =================================================================
    # 💰 2. ASIGNACIÓN DE CAPITAL Y CÁLCULO DE LÍMITES
    # =================================================================
    st.markdown("---")
    st.markdown("### 💰 2. Asignación de Capital y Riesgo")
    
    capital_inicial = st.number_input("Capital Inicial a Invertir (Stake 1)", min_value=5000, value=min(20000, int(saldo_disponible)) if saldo_disponible > 5000 else 10000, step=5000)

    # 🧮 MATEMÁTICA DE LÍMITES DINÁMICOS
    retorno_bruto_esperado = capital_inicial * cuota_efectiva
    utilidad_max_posible = retorno_bruto_esperado - capital_inicial
    max_roi_pct = (utilidad_max_posible / capital_inicial) * 100 if capital_inicial > 0 else 0
    
    if max_roi_pct <= 0:
        st.error("⚠️ La cuota es demasiado baja para generar utilidad. Imposible cubrir.")
        st.stop()
        
    st.markdown(f"<p style='font-size:0.9rem; color:#475569;'><i>(Nota: Tu utilidad máxima posible si no usas cobertura es de <b>${utilidad_max_posible:,.0f}</b> o <b>{max_roi_pct:.1f}%</b>)</i></p>", unsafe_allow_html=True)
        
    col1, col2 = st.columns(2)
    with col1:
        # El slider se adapta al ROI máximo posible para que JAMÁS dé valores negativos
        utilidad_esperada = st.slider(
            "Utilidad Deseada con Seguro (Take Profit):", 
            min_value=1.0, 
            max_value=max(1.0, float(max_roi_pct - 0.5)), 
            value=min(5.0, max(1.0, float(max_roi_pct / 2))), 
            step=0.5,
            format="%.1f%%"
        )
    with col2:
        porcentaje_perdida = st.slider(
            "Stop Loss Máximo (% de pérdida permitida):", 
            min_value=1.0, max_value=100.0, value=20.0, step=1.0, format="%.1f%%"
        )

    # 🧮 CÁLCULO EXACTO DE CUOTAS A CAZAR
    utilidad_objetivo_dinero = capital_inicial * (utilidad_esperada / 100.0)
    inyeccion_necesaria_tp = utilidad_max_posible - utilidad_objetivo_dinero
    cuota_a_cazar = retorno_bruto_esperado / inyeccion_necesaria_tp if inyeccion_necesaria_tp > 0 else 0
    
    perdida_maxima = capital_inicial * (porcentaje_perdida / 100.0)
    inyeccion_necesaria_sl = utilidad_max_posible + perdida_maxima
    cuota_stop_loss = retorno_bruto_esperado / inyeccion_necesaria_sl

    # Auditoría de Riesgo Pre-Partido
    umbral_riesgo_actual = max_riesgo_real if banca_activa == "REAL" else max_riesgo_simulacion
    if saldo_disponible > 0:
        porcentaje_exposicion = (capital_inicial / saldo_disponible) * 100
        if porcentaje_exposicion > umbral_riesgo_actual: 
            st.warning(f"⚠️ Alerta de Exposición: Comprometes el {porcentaje_exposicion:.1f}% de tu banca. Superas el umbral de {umbral_riesgo_actual}%.")

    # Cálculos de partición obligatoria (Dutching vs Directa)
    if usar_dutching:
        stake_base = capital_inicial * (cuota_empate / (cuota_gana + cuota_empate))
        stake_emp_dutch = capital_inicial * (cuota_gana / (cuota_gana + cuota_empate))
    else:
        stake_base = capital_inicial
        stake_emp_dutch = 0.0

    st.markdown("---")

    if capital_inicial > saldo_disponible:
        st.markdown(f'<div class="error-caja"><b>🚨 SALDO INSUFICIENTE:</b> El capital inicial supera el saldo disponible.</div>', unsafe_allow_html=True)
    else:
        if "Goles" in enfoque_operativo:
            sufijo_ui = "PT" if "Primer" in periodo_goles else "FT"
            str_selec_1 = f"Menos de {linea_goles} {sufijo_ui}"
            str_amenaza = f"Más de {linea_goles} {sufijo_ui}"
            items_html = f"<li><b>${stake_base:,.0f}</b> ➔ {str_selec_1}</li>"
        else:
            str_selec_1 = "Gana Local" if "Ninguno" in enfoque_operativo else "Gana tu Equipo"
            str_selec_2 = "Gana Visitante" if "Ninguno" in enfoque_operativo else "Empate"
            str_amenaza = "Empate" if "Ninguno" in enfoque_operativo else "Rival"
            items_html = f"<li><b>${stake_base:,.0f}</b> ➔ {str_selec_1}</li><li><b>${stake_emp_dutch:,.0f}</b> ➔ {str_selec_2}</li>"

        cols_plan = st.columns(3)
        with cols_plan[0]:
            st.markdown(f"""
            <div style="background-color: #F8FAFC; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px;">
                <h4 style="margin-top:0;">Fase 1: Pre-partido</h4>
                <p style="margin:0;">Stake 1 (<b>${capital_inicial:,.0f} COP</b>):</p>
                <ul style="margin-top: 5px; margin-bottom: 5px; font-size:0.9rem;">
                    {items_html}
                </ul>
            </div>
            """, unsafe_allow_html=True)
                
        with cols_plan[1]:
            st.markdown(f"""
            <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 15px; border-radius: 4px; text-align: center;">
                <h4 style="margin-top:0; color:#15803D;">Take Profit (Ganancia)</h4>
                <p style="margin:0; font-size:0.85rem;">Si la cuota de {str_amenaza} <b>SUBE</b> a:</p>
                <h1 style="color:#15803D; font-size:2.2rem; margin:10px 0;">{cuota_a_cazar:.2f}</h1>
                <p style="margin:0; font-size: 0.75rem; color:#475569;">Aseguras {utilidad_esperada}% de utilidad</p>
            </div>
            """, unsafe_allow_html=True)
            
        with cols_plan[2]:
            st.markdown(f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 4px; text-align: center;">
                <h4 style="margin-top:0; color:#B91C1C;">Stop Loss (Pánico)</h4>
                <p style="margin:0; font-size:0.85rem;">Si la cuota de {str_amenaza} <b>BAJA</b> a:</p>
                <h1 style="color:#B91C1C; font-size:2.2rem; margin:10px 0;">{cuota_stop_loss:.2f}</h1>
                <p style="margin:0; font-size: 0.75rem; color:#475569;">Salvas el {100-porcentaje_perdida:.0f}% de tu inversión</p>
            </div>
            """, unsafe_allow_html=True)

        # =================================================================
        # 💾 3. REGISTRO CONTABLE 
        # =================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💾 3. Detalles y Registro de la Operación")
        with st.form("guardar_operacion_esports"):
            
            c_eq1, c_eq2 = st.columns(2)
            with c_eq1:
                if "Goles" in enfoque_operativo:
                    st.info("💡 **Mercado de Goles:** Escribe el nombre del partido.")
                    eq_apuesta_inicial = st.text_input("⚽ Partido (Ej: Equipo A vs Equipo B)")
                elif "Ninguno" in enfoque_operativo:
                    st.info("💡 **Fuego Cruzado:** Escribe en la Caja 1 el Local y en la Caja 2 el Visitante.")
                    eq_apuesta_inicial = st.text_input("🎮 Jugador/Equipo Local")
                else:
                    st.info("💡 **Regla Fija:** Escribe en la Caja 1 tu selección base. Escribe en la Caja 2 el equipo rival (la amenaza).")
                    eq_apuesta_inicial = st.text_input("🎮 Jugador Apuesta Inicial")
                    
            with c_eq2:
                if "Goles" in enfoque_operativo:
                    st.info(f"💡 **Línea Actual:** {linea_goles} Goles ({periodo_goles})")
                    eq_cobertura = st.text_input("Línea seleccionada", value=f"Under/Over {linea_goles}", disabled=True)
                elif "Ninguno" in enfoque_operativo:
                    st.info("💡 **El Empate es tu amenaza.**")
                    eq_cobertura = st.text_input("🚀 Jugador/Equipo Visitante")
                else:
                    st.info("💡 **Este es tu seguro/amenaza.**")
                    eq_cobertura = st.text_input("🎯 Jugador Amenaza")
            
            hora_inicio = st.time_input("⏱️ Hora de inicio del evento:")
            plataforma_ini = st.selectbox("Plataforma de la Apuesta Inicial:", todas_las_plataformas)
            plataforma_otra = st.text_input("Especifica la otra plataforma:") if plataforma_ini == "Otra" else ""

            if st.form_submit_button("Generar Código e Iniciar Auditoría Scalping"):
                if not eq_apuesta_inicial:
                    st.error("Debes ingresar el nombre de los jugadores o el partido.")
                elif not "Goles" in enfoque_operativo and not eq_cobertura:
                    st.error("Debes ingresar los nombres de los jugadores en ambas cajas.")
                else:
                    import random, string
                    nuevo_codigo = f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(100, 999)}"
                    plataforma_final = plataforma_otra if plataforma_ini == "Otra" else plataforma_ini
                    
                    if "Goles" in enfoque_operativo:
                        partido_str = eq_apuesta_inicial
                        sufijo_bd = "PT" if "Primer" in periodo_goles else "FT"
                        seleccion_ini = f"Menos de {linea_goles} Goles {sufijo_bd}"
                        seleccion_cob = f"Más de {linea_goles} Goles {sufijo_bd}"
                        audit_empate = 0.0
                        audit_amenaza = cuota_rival
                    elif "Ninguno" in enfoque_operativo:
                        partido_str = f"{eq_apuesta_inicial} vs {eq_cobertura}"
                        seleccion_ini = f"Dutching: Gana {eq_apuesta_inicial} + Gana {eq_cobertura}"
                        seleccion_cob = "Empate (X)"
                        audit_empate = cuota_rival
                        audit_amenaza = cuota_empate
                    else:
                        partido_str = f"{eq_apuesta_inicial} vs {eq_cobertura}"
                        seleccion_ini = f"Dutching: {eq_apuesta_inicial} + Empate"
                        seleccion_cob = f"Gana {eq_cobertura}"
                        audit_empate = cuota_empate
                        audit_amenaza = cuota_rival

                    datos = {
                        "codigo": nuevo_codigo,
                        "partido": partido_str,
                        "estrategia": nombre_estrategia_bd,
                        "seleccion_inicial": seleccion_ini,
                        "seleccion_cobertura": seleccion_cob,
                        "plataforma_inicial": plataforma_final,
                        "capital_total": capital_inicial, # Adaptado al dinamismo
                        "cuota_inicial": round(cuota_efectiva, 3),
                        "stake_1": capital_inicial, # Stake 1 es el capital inicial completo
                        "reserva_stake_2": 0, # Ya no se usa reserva estática
                        "cuota_objetivo": cuota_a_cazar,
                        "cuota_stop_loss": cuota_stop_loss,
                        "estado": "EN VIVO",
                        "tipo_banca": banca_activa,
                        "hora_inicio_partido": hora_inicio.strftime("%H:%M"),
                        "cuota_base_audit": cuota_gana,
                        "cuota_empate_audit": audit_empate, 
                        "cuota_dc_audit": 0.0, 
                        "cuota_amenaza_audit": audit_amenaza, 
                        "es_dutching": usar_dutching,
                        "stake_dutch_base": round(stake_base, 2),
                        "stake_dutch_empate": round(stake_emp_dutch, 2)
                    }
                    try:
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f'<div class="caja-codigo"><h3>Código ({banca_activa}): {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error de Supabase: {str(e)}")

# =====================================================================
# MÓDULO 3: ESTRATEGIA BINARIA DINÁMICA (CREADOR DE MERCADOS)
# =====================================================================
elif estrategia_activa == "3️⃣ Estrategia 3: Binario Personalizado":
    st.info("**Lógica:** Constructor de mercados de 2 vías (Sí/No, A/B). Utiliza el motor de **Reserva Elástica** para darte libertad de cobertura en vivo sin asfixia de Stop Loss inicial.")
    
    tipo_banca_op = st.radio("Entorno de ejecución:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True)
    banca_activa = "REAL" if "Real" in tipo_banca_op else "SIMULACION"
    saldo_disponible = saldo_real if banca_activa == "REAL" else saldo_simulacion
    
    st.markdown("---")
    st.markdown("### 🏷️ 1. Bautizar el Evento y el Mercado")
    
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        partido_base = st.text_input("⚽ Evento Principal:", placeholder="Ej: Real Madrid vs City")
    with col_n2:
        tipo_mercado = st.selectbox("🎯 Selecciona el Mercado:", ["🔥 Ambos Anotan (BTTS)", "⚽ Línea de Goles (Más/Menos)", "✍️ Otro Mercado Personalizado..."])
        
    if tipo_mercado == "🔥 Ambos Anotan (BTTS)":
        nombre_mercado = "Ambos Anotan"
        opcion_a = "Sí"
        opcion_b = "No"
        st.info("💡 **Mercado Automático:** Las opciones 'Sí' y 'No' han sido preconfiguradas. El Motor IA táctico se activará para este evento.")
        
    elif tipo_mercado == "⚽ Línea de Goles (Más/Menos)":
        linea_goles = st.number_input("🎯 Ingresa la Línea de Goles (Ej: 2.5, 3.5):", min_value=0.5, step=0.5, value=2.5)
        nombre_mercado = f"Línea de Goles {linea_goles}"
        opcion_a = f"Más de {linea_goles}"
        opcion_b = f"Menos de {linea_goles}"
        st.info(f"💡 **Mercado Automático:** Opciones configuradas como '{opcion_a}' y '{opcion_b}'.")
        
    else:
        nombre_mercado = st.text_input("🎯 Nombre del Mercado:", placeholder="Ej: Más de 10 Córners")
        st.markdown("**Define las dos únicas opciones posibles:**")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            opcion_a = st.text_input("Opción A:", placeholder="Ej: Sí")
        with col_opt2:
            opcion_b = st.text_input("Opción B:", placeholder="Ej: No")

    if not opcion_a or not opcion_b or not nombre_mercado:
        st.warning("☝️ Bautiza el mercado y las dos opciones para habilitar el motor matemático.")
    else:
        # =================================================================
        # ⚖️ 2. SELECCIÓN Y CUOTAS (ENTRADA DIRECTA)
        # =================================================================
        st.markdown("---")
        st.markdown("### ⚖️ 2. Selección Operativa")
        
        seleccion_objetivo = st.radio("¿A cuál de las dos opciones le vas a apostar tu capital inicial?", [opcion_a, opcion_b], horizontal=True)
        opcion_amenaza = opcion_b if seleccion_objetivo == opcion_a else opcion_a
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cuota_inicial = st.number_input(f"Cuota para tu apuesta ({seleccion_objetivo}):", min_value=1.01, value=1.90, step=0.05)
        with col_c2:
            cuota_amenaza_pre = st.number_input(f"Cuota actual de la amenaza ({opcion_amenaza}):", min_value=1.01, value=1.90, step=0.05)
            
        st.success(f"⚙️ **ENTRADA FIJADA:** Tu cuota de entrada es **{cuota_inicial:.3f}**. La cobertura se calculará dinámicamente en vivo.")

        # =================================================================
        # 💰 3. ASIGNACIÓN DE CAPITAL (RESERVA ELÁSTICA)
        # =================================================================
        st.markdown("---")
        st.markdown("### 💰 3. Asignación de Capital Inicial")
        
        capital_inicial = st.number_input("Capital Inicial a Invertir (Stake 1)", min_value=5000, value=min(20000, int(saldo_disponible)) if saldo_disponible > 5000 else 10000, step=5000)

        # 🧮 MATEMÁTICA DE LÍMITES DINÁMICOS
        retorno_bruto_esperado = capital_inicial * cuota_inicial
        utilidad_max_posible = retorno_bruto_esperado - capital_inicial
        max_roi_pct = (utilidad_max_posible / capital_inicial) * 100 if capital_inicial > 0 else 0
        
        if max_roi_pct <= 0:
            st.error("⚠️ La cuota es demasiado baja para generar utilidad. Imposible cubrir en el futuro.")
            st.stop()
            
        st.markdown(f"<p style='font-size:0.9rem; color:#475569;'><i>(Tu utilidad máxima posible si no usas cobertura será de <b>${utilidad_max_posible:,.0f}</b> o <b>{max_roi_pct:.1f}%</b>)</i></p>", unsafe_allow_html=True)
            
        col1, col2 = st.columns(2)
        with col1:
            utilidad_esperada = st.slider(
                "Utilidad Deseada si decides cubrir (Take Profit):", 
                min_value=1.0, 
                max_value=max(1.0, float(max_roi_pct - 0.5)), 
                value=min(5.0, max(1.0, float(max_roi_pct / 2))), 
                step=0.5,
                format="%.1f%%"
            )
        with col2:
            porcentaje_perdida = st.slider(
                "Pérdida permitida si decides abortar (Stop Loss):", 
                min_value=1.0, max_value=100.0, value=20.0, step=1.0, format="%.1f%%"
            )

        # 🧮 CÁLCULO DE OBJETIVOS
        utilidad_objetivo_dinero = capital_inicial * (utilidad_esperada / 100.0)
        inyeccion_necesaria_tp = utilidad_max_posible - utilidad_objetivo_dinero
        cuota_a_cazar = retorno_bruto_esperado / inyeccion_necesaria_tp if inyeccion_necesaria_tp > 0 else 0
        
        perdida_maxima = capital_inicial * (porcentaje_perdida / 100.0)
        inyeccion_necesaria_sl = utilidad_max_posible + perdida_maxima
        cuota_stop_loss = retorno_bruto_esperado / inyeccion_necesaria_sl

        # Auditoría de Riesgo Pre-Partido
        umbral_riesgo_actual = max_riesgo_real if banca_activa == "REAL" else max_riesgo_simulacion
        if saldo_disponible > 0:
            porcentaje_exposicion = (capital_inicial / saldo_disponible) * 100
            if porcentaje_exposicion > umbral_riesgo_actual: 
                st.warning(f"⚠️ Alerta de Exposición: Iniciar esta operación compromete el {porcentaje_exposicion:.1f}% de tu banca. Límite: {umbral_riesgo_actual}%.")

        st.markdown("---")

        if capital_inicial > saldo_disponible:
            st.markdown(f'<div class="error-caja"><b>🚨 SALDO INSUFICIENTE:</b> El capital inicial supera el saldo disponible.</div>', unsafe_allow_html=True)
        else:
            cols_plan = st.columns(3)
            with cols_plan[0]:
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 4px;">
                    <h4 style="margin-top:0;">Fase 1: Pre-partido</h4>
                    <p style="margin:0;">Stake 1 (<b>${capital_inicial:,.0f} COP</b>):</p>
                    <ul style="margin-top: 5px; margin-bottom: 5px; font-size:0.9rem;">
                        <li><b>${capital_inicial:,.0f}</b> ➔ {seleccion_objetivo}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                    
            with cols_plan[1]:
                st.markdown(f"""
                <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 15px; border-radius: 4px; text-align: center;">
                    <h4 style="margin-top:0; color:#15803D;">Take Profit (Ganancia)</h4>
                    <p style="margin:0; font-size:0.85rem;">Si '{opcion_amenaza}' <b>SUBE</b> a:</p>
                    <h1 style="color:#15803D; font-size:2.2rem; margin:10px 0;">{cuota_a_cazar:.2f}</h1>
                    <p style="margin:0; font-size: 0.75rem; color:#475569;">Aseguras {utilidad_esperada}% de utilidad inyectando en vivo</p>
                </div>
                """, unsafe_allow_html=True)
                
            with cols_plan[2]:
                st.markdown(f"""
                <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 4px; text-align: center;">
                    <h4 style="margin-top:0; color:#B91C1C;">Stop Loss (Pánico)</h4>
                    <p style="margin:0; font-size:0.85rem;">Si '{opcion_amenaza}' <b>BAJA</b> a:</p>
                    <h1 style="color:#B91C1C; font-size:2.2rem; margin:10px 0;">{cuota_stop_loss:.2f}</h1>
                    <p style="margin:0; font-size: 0.75rem; color:#475569;">Te retiras perdiendo max. {porcentaje_perdida}% del Stake 1</p>
                </div>
                """, unsafe_allow_html=True)

            # =================================================================
            # 💾 REGISTRO CONTABLE 
            # =================================================================
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 💾 4. Plataformas y Registro")
            with st.form("guardar_binario_dinamico"):
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    plat_1 = st.selectbox("Plataforma de Inversión:", todas_las_plataformas, key="pb1")
                    if plat_1 == "Otra": plat_1 = st.text_input("Especificar plataforma:")
                with col_p2:
                    hora_inicio = st.time_input("⏱️ Hora de inicio del evento:")

                if st.form_submit_button("Generar Código e Iniciar Auditoría"):
                    import random, string
                    nuevo_codigo = f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(100, 999)}"
                    
                    # Truco maestro de nomenclatura
                    partido_str = f"🏟️ {partido_base} | [{nombre_mercado}] {opcion_a} vs {opcion_b}"
                    
                    # Le inyectamos la "Estrategia 1" en la base de datos para que el Seguimiento active la terminal dinámica
                    datos = {
                        "codigo": nuevo_codigo,
                        "partido": partido_str,
                        "estrategia": "Estrategia 3: Binario Personalizado", # Engaño legal para usar la terminal dinámica
                        "seleccion_inicial": seleccion_objetivo,
                        "seleccion_cobertura": opcion_amenaza,
                        "plataforma_inicial": plat_1,
                        "capital_total": capital_inicial, 
                        "cuota_inicial": round(cuota_inicial, 3),
                        "stake_1": capital_inicial, 
                        "reserva_stake_2": 0, 
                        "cuota_objetivo": cuota_a_cazar,
                        "cuota_stop_loss": cuota_stop_loss,
                        "estado": "EN VIVO",
                        "tipo_banca": banca_activa,
                        "hora_inicio_partido": hora_inicio.strftime("%H:%M"),
                        "cuota_base_audit": cuota_inicial,
                        "cuota_amenaza_audit": cuota_amenaza_pre, 
                        "es_dutching": False,
                        "stake_dutch_base": 0,
                        "stake_dutch_empate": 0
                    }
                    try:
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f'<div class="caja-codigo"><h3>Código ({banca_activa}): {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
                        st.rerun()
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
                tipo_banca_operacion = op.get('tipo_banca', 'SIMULACION')
                nombre_estrategia = op.get('estrategia', '')
                
                # =====================================================================
                # ⚡ COCKPIT DINÁMICO (eSPORTS Y BINARIO PERSONALIZADO)
                # Comparten el motor de "Reserva Elástica"
                # =====================================================================
                if nombre_estrategia in ["Estrategia 1: eSports Scalping", "Estrategia 3: Binario Personalizado"]:
                    # Identificador visual limpio según estrategia
                    icono_est = "🎯" if "Binario" in nombre_estrategia else "🎮"
                    etiqueta_db = "Binario" if "Binario" in nombre_estrategia else "eSports"
                    
                    with st.expander(f"{icono_est} {op['partido']} | Ref: {op['codigo']} | Estado: {op['estado']}"):
                        
                        sel_ini = op.get('seleccion_inicial', 'Apuesta Inicial')
                        sel_cob = op.get('seleccion_cobertura', 'Cobertura')
                        saldo_banca_actual = obtener_saldo_banca(tipo_banca_operacion)
                        umbral_permitido = max_riesgo_real if tipo_banca_operacion == 'REAL' else max_riesgo_simulacion
                        
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <span style="background:#3B82F6; color:white; padding:4px 8px; border-radius:4px; font-size:0.8rem; font-weight:bold;">{tipo_banca_operacion}</span>
                            <span style="color:#64748B; font-size:0.8rem; font-weight:bold;">{nombre_estrategia}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # BLOQUE INFORMATIVO FIJO
                        st.markdown(f"""
                        <div style="background-color: #F8FAFC; padding: 15px; border-left: 5px solid #F59E0B; border-radius: 4px; margin-bottom: 15px;">
                            <p style="margin: 0; font-size: 0.95rem;">🎯 <b>Posición Inicial:</b> {sel_ini} (Stake 1: <b>${op['stake_1']:,.0f} COP</b> a cuota {op['cuota_inicial']:.2f})</p>
                            <p style="margin: 5px 0 0 0; font-size: 0.95rem;">🚀 <b>Amenaza a cubrir en vivo:</b> <span style="color:#D97706; font-weight:bold; font-size:1.05rem;">{sel_cob}</span></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c_info1, c_info2, c_info3 = st.columns(3)
                        c_info1.metric("Punto de Entrada", f"{op['cuota_inicial']:.2f}")
                        c_info2.metric("🟢 Take Profit", f"{op['cuota_objetivo']:.2f}")
                        c_info3.metric("🔴 Stop Loss", f"{op.get('cuota_stop_loss', 0.0):.2f}")
                        
                        st.markdown("---")
                        
                        # -------------------------------------------------------------
                        # FASE 1: EN VIVO (HEDGING DINÁMICO)
                        # -------------------------------------------------------------
                        if op['estado'] == "EN VIVO":
                            
                            # CÁLCULO DE BREAK-EVEN Y UTILIDAD MÁXIMA
                            retorno_bruto_esperado = op['stake_1'] * op['cuota_inicial']
                            utilidad_original_maxima = retorno_bruto_esperado - op['stake_1']
                            inyeccion_maxima_breakeven = utilidad_original_maxima
                            cuota_minima_rentable = retorno_bruto_esperado / inyeccion_maxima_breakeven if inyeccion_maxima_breakeven > 0 else 0
                            
                            st.markdown(f"""
                            <div style="background-color: #EFF6FF; padding: 15px; border-left: 4px solid #3B82F6; border-radius: 4px; margin-bottom: 20px;">
                                <p style="margin: 0; font-size: 0.95rem; color: #1E3A8A;">📈 <b>Escenario SIN COBERTURA:</b> Si dejas correr y gana {sel_ini}, tu utilidad máxima será <b>${utilidad_original_maxima:,.0f} COP</b>.</p>
                                <hr style="margin: 8px 0; border-color: #3B82F6; opacity: 0.2;">
                                <p style="margin: 0; font-size: 0.95rem; color: #1E3A8A;">⚖️ <b>Punto de Equilibrio:</b> Para ganar asegurando con cobertura, necesitas cazar a <b>cuota mínima de {cuota_minima_rentable:.2f}</b>.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            accion_esports = st.radio(
                                f"Acción Operativa ({etiqueta_db}):", 
                                ["📸 Evaluar Asedio y Cazar Cuota", "🏁 Liquidar Posición Directa (Sin Cobertura)"],
                                key=f"acc_es_{op['codigo']}",
                                horizontal=True
                            )
                            
                            if accion_esports == "📸 Evaluar Asedio y Cazar Cuota":
                                st.markdown("#### ⏱️ Auditoría Táctica y Financiera")
                                
                                # 1. Extracción inteligente de equipos para las cajas de goles
                                partido_str = str(op.get('partido', ''))
                                solo_partido = partido_str.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str else partido_str
                                
                                # Filtro blindado: busca 'vs', 'vs.', o '-' sin importar mayúsculas
                                txt_norm = solo_partido.lower().replace("vs.", "vs").replace("-", "vs")
                                
                                if "vs" in txt_norm:
                                    partes = txt_norm.split("vs")
                                    eq_local = partes[0].strip().title()
                                    eq_vis = partes[1].strip().title()
                                else:
                                    # Si solo escribió un nombre sin 'vs', usamos ese
                                    eq_local = solo_partido if len(solo_partido) > 1 else "Equipo Local"
                                    eq_vis = "Equipo Visitante"
                                    
                                # Parche retroactivo: Si la apuesta era vieja y el sistema guardó el nombre del mercado
                                if "Ambos Anotan" in eq_local or "[" in eq_local:
                                    eq_local, eq_vis = "Equipo A", "Equipo B"

                                # Recuperar última foto
                                res_fotos = supabase.table("registro_fotos").select("*").eq("codigo_posicion", op['codigo']).order("minuto_evaluado", desc=True).limit(1).execute()
                                ultima_foto = res_fotos.data[0] if res_fotos.data else {'goles_local': 0, 'goles_vis': 0, 'atkp_local': 0, 'atkp_vis': 0}
                                min_base = ultima_foto.get('minuto_evaluado', 0) if res_fotos.data else 0

                                # Calcular minuto sugerido
                                minuto_sugerido = min_base
                                if minuto_sugerido == 0 and op.get("hora_inicio_partido"):
                                    try:
                                        ahora = datetime.datetime.now()
                                        h_ini = datetime.datetime.strptime(op["hora_inicio_partido"], "%H:%M").replace(year=ahora.year, month=ahora.month, day=ahora.day)
                                        if ahora < h_ini: h_ini -= datetime.timedelta(days=1)
                                        diff = int((ahora - h_ini).total_seconds() / 60)
                                        minuto_sugerido = diff if diff <= 45 else (45 if diff < 60 else diff - 15)
                                    except Exception: pass
                                
                                # 2. PANELES DE INPUT (Táctica, Cuota y Cashout)
                                c_top1, c_top2, c_top3 = st.columns(3)
                                with c_top1:
                                    minuto_actual = st.number_input("⏱️ Minuto:", min_value=0, max_value=120, value=max(0, min(95, int(minuto_sugerido))), step=1, key=f"min_es_{op['codigo']}")
                                with c_top2:
                                    val_cuota_obj = float(op.get('cuota_objetivo') or 1.01)
                                    if val_cuota_obj < 1.01: val_cuota_obj = 1.01
                                    cuota_input_es = st.number_input("📉 Cuota Cobertura:", min_value=1.01, step=0.01, value=val_cuota_obj, key=f"c_live_es_{op['codigo']}")
                                    cuota_salida = cuota_input_es if cuota_input_es is not None else 1.01
                                with c_top3:
                                    oferta_cashout = st.number_input("💰 Oferta Cashout ($):", min_value=0.0, step=1000.0, value=0.0, key=f"cash_es_{op['codigo']}", help="Escribe lo que te ofrece la casa en el botón de Cerrar Apuesta")

                                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                                col_t1, col_t2 = st.columns(2)
                                
                                with col_t1:
                                    g_local = st.number_input(f"⚽ Goles de {eq_local}", min_value=0, value=int(ultima_foto.get('goles_local', 0)), key=f"g_l_es_{op['codigo']}")
                                    atkp_local = st.number_input(f"🔥 Atq. de {eq_local}", min_value=0, value=int(ultima_foto.get('atkp_local', 0)), key=f"atk_l_es_{op['codigo']}")
                                
                                with col_t2:
                                    g_vis = st.number_input(f"⚽ Goles de {eq_vis}", min_value=0, value=int(ultima_foto.get('goles_vis', 0)), key=f"g_v_es_{op['codigo']}")
                                    atkp_vis = st.number_input(f"🔥 Atq. de {eq_vis}", min_value=0, value=int(ultima_foto.get('atkp_vis', 0)), key=f"atk_v_es_{op['codigo']}")
                                
                                st.markdown("---")
                                
                                # 3. CÁLCULOS MATEMÁTICOS DE IA
                                # Buscamos el mercado en AMBOS campos para que no se quede ciego
                                texto_mercado = str(op.get('mercado', '')) + " " + str(op.get('partido', ''))
                                is_ambos_anotan = "Ambos Anotan" in texto_mercado
                                is_linea_goles = "Línea de Goles" in texto_mercado
                                
                                # Velocímetros Reales (APM)
                                apm_local = atkp_local / max(1, minuto_actual)
                                apm_vis = atkp_vis / max(1, minuto_actual)
                                apm_total = apm_local + apm_vis
                                tiempo_restante = 90 - minuto_actual
                                goles_totales = g_local + g_vis
                                
                                retorno_bruto_esperado = op['stake_1'] * op['cuota_inicial']
                                utilidad_original_maxima = retorno_bruto_esperado - op['stake_1']
                                cuota_minima_rentable = retorno_bruto_esperado / utilidad_original_maxima if utilidad_original_maxima > 0 else 0
                                cuota_sl = float(op.get('cuota_stop_loss') or 0.0)
                                
                                # Pre-calculamos la utilidad exacta para que el Dictamen nos hable con dinero real
                                monto_a_inyectar = retorno_bruto_esperado / cuota_salida
                                utilidad_proyectada = retorno_bruto_esperado - op['stake_1'] - monto_a_inyectar
                                
                                ird = 0.0
                                msj_ia = ""
                                
                                if is_ambos_anotan:
                                    st.markdown("#### 🧠 Asesoría Táctica IA (Mercado 'Ambos Anotan')")
                                    aposto_si = (sel_ini.strip().lower() in ["sí", "si", "yes"])
                                    
                                    if aposto_si:
                                        if g_local > 0 and g_vis > 0:
                                            msj_ia = "🎉 **¡OBJETIVO CUMPLIDO!** Ambos marcaron. Ganaste el SÍ. Liquida ya."
                                            ird = 0.0
                                        elif g_local == 0 and g_vis == 0:
                                            if minuto_actual < 20:
                                                msj_ia = f"⏳ **Fase de Estudio:** Minuto {minuto_actual}. APM Total: {apm_total:.1f}. Es temprano, deja correr."
                                                ird = 20.0
                                            else:
                                                if apm_total >= 1.3 and apm_local >= 0.5 and apm_vis >= 0.5:
                                                    msj_ia = f"🔥 **Ida y Vuelta (Frenético):** Velocímetro en {apm_total:.1f} APM. Ambos atacan, excelente escenario."
                                                    ird = 25.0
                                                elif apm_total < 0.9:
                                                    msj_ia = f"📉 **Partido Trabado:** Velocidad muy lenta ({apm_total:.1f} APM). Considera salir."
                                                    ird = 85.0
                                                else:
                                                    msj_ia = f"⚠️ **Ritmo Lento/Inclinado:** Velocidad en {apm_total:.1f} APM. Precaución."
                                                    ird = 60.0
                                        else:
                                            if g_local == 0: 
                                                eq_necesitado = eq_local; apm_necesitado = apm_local; eq_dominante = eq_vis; apm_dominante = apm_vis
                                            else: 
                                                eq_necesitado = eq_vis; apm_necesitado = apm_vis; eq_dominante = eq_local; apm_dominante = apm_local
                                                
                                            total_atkp_actual = (apm_necesitado + apm_dominante) * minuto_actual
                                            share_necesitado = ((apm_necesitado * minuto_actual) / total_atkp_actual) * 100 if total_atkp_actual > 0 else 0
                                            
                                            st.write(f"🔍 **Auditoría:** {eq_necesitado} ataca a **{apm_necesitado:.1f} APM** ({share_necesitado:.0f}% del control).")
                                            
                                            if apm_necesitado >= 0.7 and share_necesitado >= 55:
                                                msj_ia = f"⚔️ **ASEDIO TOTAL:** {eq_necesitado} domina al rival. ¡Aguanta!"
                                                ird = 35.0 if tiempo_restante > 20 else 60.0
                                            elif apm_necesitado >= 0.7 and share_necesitado < 50:
                                                msj_ia = f"⚠️ **GOLPE A GOLPE:** No hay dominio claro. Alerta encendida."
                                                ird = 70.0
                                            elif apm_necesitado < 0.5:
                                                msj_ia = f"🚨 **ASFIXIA TÁCTICA:** {eq_necesitado} no tiene velocidad. ¡Sal de ahí!"
                                                ird = 95.0
                                            else:
                                                msj_ia = f"🛡️ **INTENTO TÍMIDO:** Prepara cobertura."
                                                ird = 80.0
                                                
                                            if tiempo_restante <= 12 and (g_local == 0 or g_vis == 0):
                                                msj_ia += " ⏳ **¡TIEMPO CRÍTICO!**"
                                                ird = max(ird, 90.0)
                                    else:
                                        if g_local > 0 and g_vis > 0:
                                            msj_ia = "❌ **SINIESTRO:** Ambos marcaron. Perdiste el NO."
                                            ird = 100.0
                                        else:
                                            msj_ia = f"✅ **Auditoría del NO:** Velocidad de {apm_total:.1f} APM. Evalúa si el que pierde ataca mucho."
                                            ird = 50.0 
                                    st.info(msj_ia)

                                elif is_linea_goles:
                                    st.markdown("#### 🧠 Asesoría Táctica IA (Mercado 'Línea de Goles')")
                                    import re
                                    match_linea = re.search(r'\d+\.\d+|\d+', sel_ini)
                                    linea_obj = float(match_linea.group()) if match_linea else 2.5
                                    aposto_mas = "Más" in sel_ini or "Mas" in sel_ini
                                    
                                    diferencia_goles = linea_obj - goles_totales
                                    st.write(f"📊 **Métrica Global:** Velocidad del partido en **{apm_total:.1f} APM**.")
                                    st.write(f"⏱️ **Contexto Espacio-Tiempo:** Faltan **{tiempo_restante} min** y tienes un margen de **{abs(diferencia_goles)} goles** respecto al límite.")
                                    
                                    if aposto_mas:
                                        if diferencia_goles < 0:
                                            msj_ia = f"🎉 **¡OBJETIVO CUMPLIDO!** Ya superaste la línea de {linea_obj} goles."
                                            ird = 0.0
                                        # FILTRO DE ESPACIO TIEMPO EXTREMO (Apostó Más)
                                        elif diferencia_goles >= 1.5 and tiempo_restante <= 25:
                                            msj_ia = f"🚨 **RELOJ EN CONTRA:** Te faltan {int(diferencia_goles + 0.5)} goles y solo quedan {tiempo_restante} minutos. El asedio no importa si ya no hay tiempo. ¡HUYE YA!"
                                            ird = 95.0
                                        else:
                                            if apm_total >= 1.3:
                                                msj_ia = f"🔥 **PARTIDO ROTO:** Excelente volumen ofensivo ({apm_total:.1f} APM). Faltan {int(diferencia_goles + 0.5)} goles en {tiempo_restante} min. ¡Mantén la posición!"
                                                ird = 30.0 if tiempo_restante > 20 else 65.0
                                            elif apm_total >= 0.9:
                                                msj_ia = f"⚖️ **RITMO ESTÁNDAR:** Velocidad normal. Tienes {tiempo_restante} min para buscar los goles que necesitas."
                                                ird = 55.0 if tiempo_restante > 20 else 80.0
                                            else:
                                                msj_ia = f"📉 **PARTIDO MUERTO:** Ritmo muy lento ({apm_total:.1f} APM) y el tiempo avanza. Huye y caza cuota."
                                                ird = 90.0
                                                
                                            if diferencia_goles <= 0.5 and tiempo_restante <= 15:
                                                msj_ia += f" ⏳ Estás a UN SOLO GOL, máxima tensión en los últimos {tiempo_restante} min."
                                                
                                    else: # Apostó MENOS
                                        if diferencia_goles < 0:
                                            msj_ia = f"❌ **SINIESTRO:** Superaron la línea. Perdiste el 'Menos de'."
                                            ird = 100.0
                                        # FILTROS DE ESPACIO TIEMPO (BLINDAJES ESCALONADOS)
                                        elif diferencia_goles >= 3.5:
                                            msj_ia = f"✅ **BLINDAJE DE ACERO:** Tienes un colchón gigante de {diferencia_goles} goles. Tendrían que hacer un gol cada {tiempo_restante/max(1, diferencia_goles):.1f} minutos. Apuesta extremadamente segura, no importa el ritmo."
                                            ird = 5.0
                                        elif diferencia_goles >= 2.5 and tiempo_restante <= 45:
                                            msj_ia = f"✅ **BLINDAJE DE SEGUNDO TIEMPO:** Colchón de {diferencia_goles} goles y ya pasamos la mitad del partido. Matemáticamente casi imposible que te remonten."
                                            ird = 10.0
                                        elif diferencia_goles >= 1.5 and tiempo_restante <= 20:
                                            msj_ia = f"✅ **BLINDAJE DE CIERRE:** Colchón de {diferencia_goles} goles y quedan {tiempo_restante} min. El reloj ya mató el partido."
                                            ird = 15.0
                                        else:
                                            if diferencia_goles <= 1.0: 
                                                if apm_total >= 1.2:
                                                    msj_ia = f"🚨 **¡PÁNICO OFENSIVO!** A UN GOL de perder y el partido está FRENÉTICO ({apm_total:.1f} APM). ¡HUYE INMEDIATAMENTE!"
                                                    ird = 95.0
                                                elif tiempo_restante <= 15:
                                                    msj_ia = f"⏳ **RELOJ SALVADOR:** A 1 gol de perder, pero el ritmo es normal y solo faltan {tiempo_restante} min. El reloj es tu amigo."
                                                    ird = 55.0
                                                else:
                                                    msj_ia = f"⚠️ **Alerta:** A un gol de perder y quedan {tiempo_restante} min de riesgo. Vigila de cerca."
                                                    ird = 75.0
                                            else:
                                                if apm_total >= 1.2:
                                                    msj_ia = f"⚠️ **RITMO PELIGROSO:** Tienes colchón de {int(diferencia_goles)} goles, pero atacan a ritmo frenético ({apm_total:.1f} APM) con {tiempo_restante} min por delante. Gran riesgo."
                                                    ird = 70.0
                                                elif apm_total >= 0.9:
                                                    msj_ia = f"⚖️ **RITMO MODERADO:** Velocidad normal ({apm_total:.1f} APM). Faltan {tiempo_restante} min. Atento a cambios."
                                                    ird = 55.0
                                                else:
                                                    msj_ia = f"✅ **CONTROL TOTAL:** Partido aburrido ({apm_total:.1f} APM). Faltan {tiempo_restante} min y tienes margen. Apuesta segura."
                                                    ird = 15.0
                                    st.info(msj_ia)

                                else:
                                    st.markdown("#### 🌡️ Termómetro del Evento (IRD General)")
                                    ird = min(100.0, apm_total * 45.0) 
                                    st.info(f"🔎 El evento fluye a **{apm_total:.2f} Ataques Peligrosos por Minuto** totales.")
                                
                                # Escala de 3 colores para mayor precisión
                                color_barra = "#10B981" if ird < 45 else "#F59E0B" if ird < 75 else "#EF4444"
                                st.progress(int(ird) / 100)
                                st.markdown(f"<h5 style='text-align: center; color: {color_barra};'>Alerta Táctica (IRD): {ird:.1f}%</h5>", unsafe_allow_html=True)

                                # =====================================================================
                                # 4. DICTAMEN INTEGRAL CON 3 NIVELES DE ALERTA
                                # =====================================================================
                                dictamen_fin = ""
                                if cuota_sl > 0 and cuota_salida <= cuota_sl:
                                    dictamen_fin = f"🛑 **¡STOP LOSS ROTO!** La cuota actual ({cuota_salida:.2f}) ha tocado tu límite. **EVACUACIÓN OBLIGATORIA AHORA**."
                                    c_dict = "#FEF2F2"; b_dict = "#B91C1C"
                                elif cuota_salida >= cuota_minima_rentable:
                                    if ird >= 75:
                                        dictamen_fin = f"⚖️ **TOMA DE BENEFICIOS:** El riesgo es rojo (IRD {ird:.1f}%), PERO tienes **${utilidad_proyectada:,.0f} COP** de ganancia. **Caza la cuota y asegura.**"
                                        c_dict = "#FFFBEB"; b_dict = "#D97706"
                                    elif ird >= 45: # La alerta amarilla dinámica
                                        dictamen_fin = f"⚠️ **ALERTA AMARILLA (VIGILANCIA):** El partido está movido (Ritmo Peligroso). Tienes una utilidad temporal de **${utilidad_proyectada:,.0f} COP**. No te confíes; si el asedio no baja, toma esos **${utilidad_proyectada:,.0f} COP** y sal antes de que se complique."
                                        c_dict = "#FEFCE8"; b_dict = "#CA8A04"
                                    else:
                                        dictamen_fin = f"🛡️ **ZONA DE CONFORT:** El partido está tranquilo a tu favor. Estás ganando **${utilidad_proyectada:,.0f} COP**. Puedes dejar correr."
                                        c_dict = "#F0FDF4"; b_dict = "#15803D"
                                else:
                                    if ird >= 75:
                                        dictamen_fin = f"🚨 **AMPUTACIÓN TÁCTICA:** Colapso en la cancha. Cubrir implica pérdida de **${utilidad_proyectada:,.0f} COP**, pero la IA sugiere amputar antes de perderlo todo."
                                        c_dict = "#FEF2F2"; b_dict = "#DC2626"
                                    elif ird >= 45:
                                        dictamen_fin = f"⚠️ **INCERTIDUMBRE:** El partido tiene riesgo medio y vas perdiendo **${utilidad_proyectada:,.0f} COP**. Aguanta un poco, pero no quites los ojos de la pantalla."
                                        c_dict = "#FFFBEB"; b_dict = "#D97706"
                                    else:
                                        dictamen_fin = f"⏳ **PACIENCIA ESTRATÉGICA:** Vas perdiendo **${utilidad_proyectada:,.0f} COP**, pero la lectura táctica dice que la situación está bajo control. Mantén la calma."
                                        c_dict = "#EFF6FF"; b_dict = "#1D4ED8"
                                        
                                st.markdown(f"""
                                <div style="background-color: {c_dict}; border-left: 5px solid {b_dict}; padding: 15px; border-radius: 4px; margin-top: 15px; margin-bottom: 15px;">
                                    <p style="margin: 0; font-size: 0.95rem; color: {b_dict};">{dictamen_fin}</p>
                                </div>
                                """, unsafe_allow_html=True)

                                st.markdown(f"**Inversión para cazar a {cuota_salida:.2f}:** ${monto_a_inyectar:,.0f} COP ➡️ **Balance Consolidado:** ${utilidad_proyectada:,.0f} COP")

                                # =====================================================================
                                # ⚖️ RADAR DE EFICIENCIA CASHOUT VS. COBERTURA MANUAL
                                # =====================================================================
                                if oferta_cashout > 0:
                                    utilidad_cashout = oferta_cashout - op['stake_1']
                                    diferencia_cashout = utilidad_proyectada - utilidad_cashout
                                    
                                    if diferencia_cashout > 0:
                                        # Te están robando en el Cashout
                                        st.markdown(f"""
                                        <div style="background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 12px; border-radius: 4px; margin-top: 10px;">
                                            <span style="font-size: 1.05em; color: #166534;">🛡️ <b>¡NO USES EL BOTÓN DE LA CASA!</b></span><br>
                                            <span style="font-size: 0.95em; color: #15803D;">El botón te deja un balance de <b>${utilidad_cashout:,.0f}</b>. Cubrir matemáticamente la cuota te deja en <b>${utilidad_proyectada:,.0f}</b>.</span><br>
                                            <span style="font-weight: bold; color: #16A34A;">👉 Cazar la cuota tú mismo te salva ${diferencia_cashout:,.0f} COP adicionales.</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    elif diferencia_cashout < 0:
                                        # El Cashout es sorprendentemente mejor
                                        st.markdown(f"""
                                        <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px; border-radius: 4px; margin-top: 10px;">
                                            <span style="font-size: 1.05em; color: #991B1B;">🚨 <b>¡TOMA EL CASHOUT DE LA CASA INMEDIATAMENTE!</b></span><br>
                                            <span style="font-size: 0.95em; color: #B91C1C;">Cubrir matemáticamente te deja en <b>${utilidad_proyectada:,.0f}</b>. El botón de la casa es más generoso y te deja en <b>${utilidad_cashout:,.0f}</b>.</span><br>
                                            <span style="font-weight: bold; color: #DC2626;">👉 Usar el botón de la casa te salva ${abs(diferencia_cashout):,.0f} COP. ¡Tómalo ya!</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.info("⚖️ Ambas opciones (Cobertura Manual o Cashout) te dejan exactamente con el mismo margen de dinero.")

                                st.markdown("---")
                                
                                # Lógica para saber si el botón de Cashout domina
                                es_mejor_cashout = False
                                if oferta_cashout > 0:
                                    utilidad_cashout = oferta_cashout - op['stake_1']
                                    if (utilidad_proyectada - utilidad_cashout) < 0:
                                        es_mejor_cashout = True

                                if es_mejor_cashout:
                                    st.info(f"💡 **Retorno Directo:** Como el Cashout es la mejor opción, el dinero regresa a tu banco original ({op.get('plataforma_inicial', 'tu plataforma')}). La operación se cerrará inmediatamente.")
                                    col_btn1, col_btn2 = st.columns(2)
                                    with col_btn1:
                                        if st.button("📸 Guardar Foto Táctica (Entrenar IA)", key=f"btn_foto_es_{op['codigo']}", use_container_width=True):
                                            try:
                                                supabase.table("registro_fotos").insert({
                                                    "codigo_posicion": str(op['codigo']), "minuto_evaluado": int(minuto_actual),
                                                    "goles_local": int(g_local), "goles_vis": int(g_vis),
                                                    "atkp_local": int(atkp_local), "atkp_vis": int(atkp_vis),
                                                    "ird_calculado": float(round(ird, 2)), "cuota_ofrecida": float(cuota_salida)
                                                }).execute()
                                                st.success("✅ Foto inyectada a la IA.")
                                                st.rerun()
                                            except Exception as e: st.error(f"❌ Error al guardar foto: {str(e)}")
                                    with col_btn2:
                                        if st.button("✅ LIQUIDAR POR CASHOUT", key=f"btn_cash_{op['codigo']}", use_container_width=True):
                                            hora_actual = datetime.datetime.now().strftime("%H:%M")
                                            supabase.table("historial_trading").update({
                                                "estado": "CERRADA", # Pasa directamente a cerrada, no a cubierta
                                                "resultado_final": "Cashout (Cierre Anticipado)",
                                                "utilidad_neta_real": float(utilidad_cashout),
                                                "roi_real": float((utilidad_cashout / op['stake_1']) * 100),
                                                "hora_cobertura": hora_actual,
                                                "plataforma_cobertura": "Misma (Cashout)"
                                            }).eq("codigo", op['codigo']).execute()
                                            st.success(f"¡Cashout registrado! Has cerrado la operación con retorno de ${oferta_cashout:,.0f}.")
                                            st.rerun()
                                else:
                                    todas_las_plataformas = ["BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Yajuego", "Zamba", "Rivalo", "MegApuesta", "Sportium", "Stake", "1xBet", "Otra"]
                                    plataforma_cob_sel = st.selectbox("Plataforma donde cazaste la cobertura:", todas_las_plataformas, key=f"plat_es_{op['codigo']}")
                                    plataforma_cob = st.text_input("Especifica la plataforma:", key=f"otra_plat_es_{op['codigo']}") if plataforma_cob_sel == "Otra" else plataforma_cob_sel
                                    
                                    col_btn1, col_btn2 = st.columns(2)
                                    with col_btn1:
                                        if st.button("📸 Guardar Foto Táctica (Entrenar IA)", key=f"btn_foto_es_{op['codigo']}", use_container_width=True):
                                            try:
                                                supabase.table("registro_fotos").insert({
                                                    "codigo_posicion": str(op['codigo']), "minuto_evaluado": int(minuto_actual),
                                                    "goles_local": int(g_local), "goles_vis": int(g_vis),
                                                    "atkp_local": int(atkp_local), "atkp_vis": int(atkp_vis),
                                                    "ird_calculado": float(round(ird, 2)), "cuota_ofrecida": float(cuota_salida)
                                                }).execute()
                                                st.success(f"✅ Foto capturada min {minuto_actual}. Datos inyectados.")
                                                st.rerun()
                                            except Exception as e: st.error(f"❌ Error al guardar foto: {str(e)}")
                                    with col_btn2:
                                        if st.button("⚡ REGISTRAR COBERTURA CONTABLE", key=f"btn_cob_es_{op['codigo']}", use_container_width=True):
                                            hora_actual = datetime.datetime.now().strftime("%H:%M")
                                            supabase.table("historial_trading").update({
                                                "estado": "CUBIERTA",
                                                "cuota_cazada_real": float(cuota_salida),
                                                "hora_cobertura": hora_actual,
                                                "plataforma_cobertura": plataforma_cob
                                            }).eq("codigo", op['codigo']).execute()
                                            st.success(f"¡Cobertura fijada a cuota {cuota_salida} en {plataforma_cob}! Pasa a liquidación.")
                                            st.rerun()
                                    
                            else:
                                with st.form(f"get_dir_es_{op['codigo']}"):
                                    st.markdown("#### 🏁 Conciliación Directa (Sin Cobertura)")
                                    resultado_directo = st.radio(
                                        "Resolución de tu Apuesta:", 
                                        [f"✅ Ganó {sel_ini} (Cobro completo)", f"❌ Perdió {sel_ini} (Pérdida Stake 1)"],
                                        key=f"rad_dir_es_{op['codigo']}"
                                    )
                                    st.markdown("---")
                                    
                                    # Extractor de equipos para Liquidación
                                    partido_str = str(op.get('partido', ''))
                                    solo_partido = partido_str.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str else partido_str
                                    txt_norm = solo_partido.lower().replace("vs.", "vs").replace("-", "vs")
                                    if "vs" in txt_norm:
                                        eq_local = txt_norm.split("vs")[0].strip().title()
                                        eq_vis = txt_norm.split("vs")[1].strip().title()
                                    else:
                                        eq_local = solo_partido if len(solo_partido) > 1 else "Equipo Local"
                                        eq_vis = "Equipo Visitante"
                                    if "Ambos Anotan" in eq_local or "[" in eq_local: eq_local, eq_vis = "Equipo A", "Equipo B"

                                    st.info(f"🏟️ **Evento:** {partido_str}")
                                    st.markdown("🤖 **Marcador / Puntos Finales para Entrenamiento IA**")
                                    goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_dir_es_{op['codigo']}")
                                    goles_finales_rival = st.number_input(f"⚽ Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_dir_es_{op['codigo']}")
                                    
                                    if st.form_submit_button("Registrar Liquidación Directa"):
                                        utilidad = utilidad_original_maxima if "Ganó" in resultado_directo else -op['stake_1']
                                        
                                        # Textos limpios para la IA según la estrategia
                                        if "Ganó" in resultado_directo:
                                            texto_cierre = f"Cierre Directo {etiqueta_db}: Ganó Inicial"
                                        else:
                                            texto_cierre = f"Cierre Directo {etiqueta_db}: Perdió Inicial"
                                            
                                        supabase.table("historial_trading").update({
                                            "estado": "CERRADA",
                                            "resultado_final": texto_cierre,
                                            "utilidad_neta_real": utilidad,
                                            "roi_real": (utilidad / op['capital_total']) * 100,
                                            "goles_finales_seleccion": goles_finales_seleccion, 
                                            "goles_finales_rival": goles_finales_rival         
                                        }).eq("codigo", op['codigo']).execute()
                                        st.success(f"Posición liquidada directamente. Balance: ${utilidad:,.0f} COP.")
                                        st.rerun()

                        # -------------------------------------------------------------
                        # FASE 2: CUBIERTA (ASENTAMIENTO FINAL)
                        # -------------------------------------------------------------
                        elif op['estado'] == "CUBIERTA":
                            st.success(f"🛡️ Cobertura asegurada a tasa de {op.get('cuota_cazada_real', 0.0):.2f}.")
                            
                            with st.form(f"liq_esports_{op['codigo']}"):
                                st.markdown("#### 🏁 Conciliación Final de la Cobertura")
                                resultado_final_ui = st.radio(
                                    "Resolución Final del Evento:", 
                                    [
                                        f"✅ Inicial Acertado: Ganó {sel_ini}", 
                                        f"🛡️ Seguro Acertado: Ganó {sel_cob}", 
                                        "❌ Déficit Total (Siniestro)"
                                    ],
                                    key=f"rad_fin_es_{op['codigo']}"
                                )
                                st.markdown("---")
                                
                                # Extractor de equipos para Liquidación
                                partido_str = str(op.get('partido', ''))
                                solo_partido = partido_str.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str else partido_str
                                txt_norm = solo_partido.lower().replace("vs.", "vs").replace("-", "vs")
                                if "vs" in txt_norm:
                                    eq_local = txt_norm.split("vs")[0].strip().title()
                                    eq_vis = txt_norm.split("vs")[1].strip().title()
                                else:
                                    eq_local = solo_partido if len(solo_partido) > 1 else "Equipo Local"
                                    eq_vis = "Equipo Visitante"
                                if "Ambos Anotan" in eq_local or "[" in eq_local: eq_local, eq_vis = "Equipo A", "Equipo B"

                                st.info(f"🏟️ **Evento:** {partido_str}")
                                st.markdown("🤖 **Marcador / Puntos Finales para Entrenamiento IA**")
                                goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_es_{op['codigo']}")
                                goles_finales_rival = st.number_input(f"⚽ Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_es_{op['codigo']}")
                                
                                if st.form_submit_button(f"🏁 Cerrar Libro Mayor {etiqueta_db}"):
                                    retorno_bruto_esperado = op['stake_1'] * op['cuota_inicial']
                                    monto_cobertura_efectivo = retorno_bruto_esperado / float(op.get('cuota_cazada_real', 1.01))
                                    total_capital_operacion = op['stake_1'] + monto_cobertura_efectivo
                                    
                                    if "Déficit" in resultado_final_ui:
                                        utilidad = -total_capital_operacion
                                        texto_db = f"Pérdida Total del Capital ({etiqueta_db})"
                                    else:
                                        utilidad = retorno_bruto_esperado - total_capital_operacion
                                        texto_db = f"Cobro de Apuesta Inicial ({etiqueta_db})" if "Inicial" in resultado_final_ui else f"Cobro de Fondo de Cobertura ({etiqueta_db})"
                                        
                                    supabase.table("historial_trading").update({
                                        "estado": "CERRADA",
                                        "resultado_final": texto_db,
                                        "utilidad_neta_real": utilidad,
                                        "roi_real": (utilidad / op['capital_total']) * 100,
                                        "goles_finales_seleccion": goles_finales_seleccion, 
                                        "goles_finales_rival": goles_finales_rival          
                                    }).eq("codigo", op['codigo']).execute()
                                    
                                    st.success(f"Libro cerrado. Balance neto transferido a PNL: ${utilidad:,.0f} COP.")
                                    st.rerun()

                # =====================================================================
                # ⚽ INTERFAZ TÁCTICA PARA FÚTBOL (PAZ MENTAL Y LIBRE)
                # =====================================================================
                else:
                    with st.expander(f"⚽ {op.get('partido', 'N/A')} | Hora: {op.get('hora_inicio_partido', 'N/A')} | Ref: {op.get('codigo', 'N/A')} | Estado: {op.get('estado', 'N/A')}"):
                        
                        cuota_sl = float(op.get('cuota_stop_loss') or 0.0)
                        cuota_obj_segura = float(op.get('cuota_objetivo') or 0.0)
                        reserva_actual = float(op.get('reserva_stake_2') or 0.0)
                        capital_actual = float(op.get('capital_total') or 0.0)
                        cuota_be = float(capital_actual / reserva_actual) if reserva_actual > 0 else 0.0
                        
                        cap_total_seguro = capital_actual
                        reserva_segura = reserva_actual
                        st1_seguro = float(op.get('stake_1') or cap_total_seguro)
                        cuota_ini_segura = float(op.get('cuota_inicial') or 1.0)
                        
                        banca_op = str(op.get('tipo_banca') or 'N/A')
                        es_apuesta_libre = (reserva_segura == 0)
                        
                        sel_ini = str(op.get('seleccion_inicial') or 'Apuesta Inicial')
                        sel_cob = str(op.get('seleccion_cobertura') or 'Cobertura')
                        tipo_estrategia = str(op.get('estrategia') or 'Estrategia 2: Paz Mental Clásica')
                        
                        partido_str = str(op.get('partido') or 'Local vs Visitante')
                        if ' vs ' in partido_str:
                            eq_local = partido_str.split(' vs ')[0].strip()
                            eq_vis = partido_str.split(' vs ')[1].strip()
                        elif ' - ' in partido_str:
                            eq_local = partido_str.split(' - ')[0].strip()
                            eq_vis = partido_str.split(' - ')[1].strip()
                        else:
                            eq_local = "Local"
                            eq_vis = "Visitante"
                        
                        es_st1_local = (sel_ini.lower() in eq_local.lower()) or (eq_local.lower() in sel_ini.lower())
                        
                        if "Inversa" in tipo_estrategia:
                            contexto_mercado = f"El reloj es aliado. Si {sel_ini} aguanta o anota, la cuota de {sel_cob} se disparará."
                        else:
                            contexto_mercado = f"El reloj es enemigo. Necesitas un gol de {sel_ini} o presión temprana para bajar la cuota."
                        
                        if es_apuesta_libre:
                            st.write(f"**Capital Comprometido (Libre) [{banca_op}]:** ${cap_total_seguro:,.0f}")
                            st.info(f"🎯 **Selección:** **{sel_ini}** a cuota **{cuota_ini_segura:.2f}** en **{op.get('plataforma_inicial', 'N/A')}**")
                        else:
                            st.write(f"**Capital Comprometido [{banca_op}]:** ${cap_total_seguro:,.0f} | **Fondo de Cobertura:** ${reserva_segura:,.0f}")
                            
                            st.markdown(f"""
                            <div style="background-color: #F8FAFC; padding: 15px; border-left: 4px solid #3B82F6; border-radius: 4px; margin-bottom: 15px;">
                                <p style="margin: 0; font-size: 0.95rem;">🎯 <b>Stake 1:</b> A favor de <b>{sel_ini}</b></p>
                                <p style="margin: 8px 0 0 0; font-size: 0.95rem; color: #15803D;">🟢 <b>Take Profit:</b> Cazar a <b>{sel_cob}</b> a cuota <b>{cuota_obj_segura:.2f}</b> o más.</p>
                                <p style="margin: 8px 0 0 0; font-size: 0.95rem; color: #1E3A8A;">⚖️ <b>Break-Even:</b> Cuota <b>{cuota_be:.2f}</b> (Recuperas todo el capital).</p>
                                <p style="margin: 8px 0 8px 0; font-size: 0.95rem; color: #B91C1C;">🔴 <b>Stop Loss:</b> Cuota <b>{cuota_sl:.2f}</b> (Paracaídas de emergencia).</p>
                                <hr style="margin: 10px 0; border-color: #CBD5E1;">
                                <p style="margin: 0; font-size: 0.85rem; color: #64748B;"><i>💡 {contexto_mercado}</i></p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        es_dutching_op = op.get('es_dutching', False)
                        p_ini = op.get('plataforma_inicial', 'N/A')
                        p_dutch = op.get('plataforma_dutch_secundaria', 'N/A')
                        p_cob = op.get('plataforma_cobertura', 'N/A')
                        es_fuego = "Fuego" in tipo_estrategia
                        
                        opciones_resultados = [f"🏠 Ganó {eq_local}", "🤝 Empató", f"🚀 Ganó {eq_vis}"]

                        if op['estado'] == "EN VIVO":
                            if es_apuesta_libre:
                                st.write("### 🏁 Resolución de Apuesta Directa")
                                with st.form(f"gestion_libre_{op['codigo']}"):
                                    # 🛑 CORRECCIÓN: Opciones binarias reales para Apuesta Libre
                                    resultado_libre = st.radio(
                                        "¿Se cumplió tu pronóstico?", 
                                        ["✅ Apuesta Acertada (Cobrar Ganancia)", "❌ Apuesta Fallada (Pérdida de Stake)"], 
                                        key=f"rad_lib_{op['codigo']}"
                                    )
                                    
                                    if st.form_submit_button("Liquidar Apuesta Libre"):
                                        if "Acertada" in resultado_libre:
                                            utilidad = (cap_total_seguro * cuota_ini_segura) - cap_total_seguro
                                            texto_cierre = f"Libre Ganada [{p_ini}]"
                                        else:
                                            utilidad = -cap_total_seguro
                                            texto_cierre = f"Libre Perdida [{p_ini}]"
                                            
                                        supabase.table("historial_trading").update({
                                            "estado": "CERRADA",
                                            "resultado_final": texto_cierre,
                                            "utilidad_neta_real": utilidad,
                                            "roi_real": (utilidad / cap_total_seguro) * 100 if cap_total_seguro > 0 else 0
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

                                    diferencia_goles = goles_nuestros - goles_amenaza

                                    tiempo_restante = max(1, 95 - minuto_actual)
                                    min_divisor = max(1, minuto_actual)
                                    
                                    apm_nuestros = atkp_nuestros / min_divisor
                                    apm_rival = atkp_amenaza / min_divisor
                                    apm_total = apm_nuestros + apm_rival
                                    
                                    atkp_totales = atkp_nuestros + atkp_amenaza
                                    share_nuestro = (atkp_nuestros / atkp_totales * 100) if atkp_totales > 0 else 50.0
                                    
                                    ataques_futuros_nuestros = tiempo_restante * apm_nuestros
                                    ataques_futuros_rival = tiempo_restante * apm_rival
                                    
                                    letalidad_nuestra = (goles_nuestros + 1) / (atkp_nuestros + 10)
                                    letalidad_rival = (goles_amenaza + 1) / (atkp_amenaza + 10)
                                    
                                    exp_goles_nuestros = ataques_futuros_nuestros * letalidad_nuestra
                                    exp_goles_rival = ataques_futuros_rival * letalidad_rival

                                    if diferencia_goles < 0:
                                        if diferencia_goles == -1: 
                                            if minuto_actual <= 45: ird_base = 65.0
                                            elif minuto_actual <= 75: ird_base = 80.0
                                            else: ird_base = 95.0
                                        else: 
                                            ird_base = 100.0
                                    elif diferencia_goles == 0: ird_base = 55.0
                                    elif diferencia_goles == 1: ird_base = 30.0
                                    else: ird_base = 0.0 
                                    
                                    presion_dominio = apm_rival * 45.0
                                    
                                    if diferencia_goles > 0:
                                        f_t = tiempo_restante / 95.0
                                    else:
                                        if minuto_actual <= 60: f_t = 0.8
                                        elif minuto_actual <= 75: f_t = 1.0
                                        else: f_t = 1.0 + ((minuto_actual - 75) * 0.035) 
                                    
                                    if share_nuestro > 50.0:
                                        escudo_dominio_base = (share_nuestro - 50.0) * 1.5
                                        factor_decaimiento = 1.0 if diferencia_goles > 0 else (tiempo_restante / 95.0)
                                        escudo_dominio = escudo_dominio_base * factor_decaimiento
                                    else:
                                        escudo_dominio = 0.0

                                    ird_crudo = ird_base + (presion_dominio * f_t) - escudo_dominio
                                    ird = max(0.0, min(100.0, ird_crudo))
                                    
                                    st.markdown("---")
                                    st.markdown("#### 🌡️ Índice de Riesgo Dinámico (IRD)")
                                    if min_base == 0:
                                        st.info(f"📌 **Fase de Calibración:** Primera foto registrada.")
                                    else:
                                        st.info(f"🔎 Auditando ritmo: Rival ataca a **{apm_rival:.2f} APM**. Partido a {apm_total:.2f} APM total. (Tú dominas el **{share_nuestro:.1f}%**).")
                                    
                                    if ird < 40:
                                        color = "#10B981"
                                        estado = f"BAJO - Escenario controlado por marcador o tiempo."
                                    elif ird < 70:
                                        color = "#F59E0B"
                                        estado = f"MODERADO - Riesgo mitigado por posesión/tiempo."
                                    else:
                                        color = "#EF4444"
                                        estado = f"CRÍTICO - ¡Alerta de Siniestro en Posición!"
                                        
                                    st.progress(int(ird))
                                    st.markdown(f"<h5 style='text-align: center; color: {color};'>Nivel de Amenaza IRD: {ird:.1f}% | {estado}</h5>", unsafe_allow_html=True)
                                    
                                    val_cuota_obj = float(op.get('cuota_objetivo') or 1.01)
                                    if val_cuota_obj < 1.01:
                                        val_cuota_obj = 1.01

                                    cuota_input_ft = st.number_input("Tasa de cobertura fijada (Cuota en Vivo Actual):", min_value=1.01, step=0.01, value=val_cuota_obj, key=f"cuota_live_{op['codigo']}")
                                    cuota_ingresada = cuota_input_ft if cuota_input_ft is not None else 1.01
                                    
                                    if st.button("📸 Guardar Foto y Cerrar Ventana", key=f"btn_foto_{op['codigo']}", use_container_width=True):
                                        try:
                                            nueva_foto = {
                                                "codigo_posicion": str(op['codigo']),
                                                "minuto_evaluado": int(minuto_actual),
                                                "goles_local": int(g_local or 0), 
                                                "goles_vis": int(g_vis or 0),
                                                "atkp_local": int(atkp_local or 0),
                                                "atkp_vis": int(atkp_vis or 0),
                                                "ird_calculado": float(round(ird, 2)),
                                                "cuota_ofrecida": float(cuota_ingresada)
                                            }
                                            supabase.table("registro_fotos").insert(nueva_foto).execute()
                                            st.success(f"✅ Registro de auditoría (Táctica + Precio) completado para el min {minuto_actual}.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error al guardar en Supabase: {str(e)}")
                                            
                                    st.markdown("---")
                                    
                                    todas_las_plataformas = ["BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Yajuego", "Zamba", "Rivalo", "MegApuesta", "Sportium", "Stake", "1xBet", "Otra"]
                                    plataforma_cob_sel = st.selectbox("Plataforma donde cazaste la cobertura:", todas_las_plataformas, key=f"plat_live_{op['codigo']}")
                                    
                                    if plataforma_cob_sel == "Otra":
                                        plataforma_cob = st.text_input("Especifica la plataforma de cobertura:", key=f"otra_plat_live_{op['codigo']}")
                                    else:
                                        plataforma_cob = plataforma_cob_sel
                                        
                                    st1_seguro = float(op.get('stake_1') or cap_total_seguro)
                                    c_ini_segura = float(op.get('cuota_inicial') or 1.0)
                                    res_segura = float(op.get('reserva_stake_2') or 0.0)
                                    
                                    util_inicial_con_cob = (st1_seguro * c_ini_segura) - cap_total_seguro
                                    util_cobertura_con_cob = (res_segura * cuota_ingresada) - cap_total_seguro
                                    util_inicial_sin_cob = (st1_seguro * c_ini_segura) - st1_seguro
                                    util_perdida_sin_cob = -st1_seguro
                                    
                                    st.markdown("#### 🔍 Matriz Financiera de la Operación")
                                    
                                    if cuota_be > 0:
                                        if cuota_ingresada >= cuota_be:
                                            st.markdown(f"<div style='background-color: #F0FDF4; padding: 10px; border-left: 4px solid #16A34A; border-radius: 4px; margin-bottom: 10px; color: #166534; font-size: 0.9rem;'>⚖️ <b>Estado Break-Even:</b> La cuota actual ({cuota_ingresada:.2f}) ya superó tu Punto de Equilibrio ({cuota_be:.2f}). Estás operando en zona libre de pérdida de capital.</div>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"<div style='background-color: #FEF2F2; padding: 10px; border-left: 4px solid #EF4444; border-radius: 4px; margin-bottom: 10px; color: #991B1B; font-size: 0.9rem;'>⚖️ <b>Estado Break-Even:</b> La cuota actual ({cuota_ingresada:.2f}) está por debajo del Punto de Equilibrio ({cuota_be:.2f}). Cubrir ahora consolidará una pérdida matemática.</div>", unsafe_allow_html=True)
                                    
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
                                    capital_rescatado = util_cobertura_con_cob - util_perdida_sin_cob
                                    
                                    if costo_seguro > 0:
                                        ratio_eficiencia = capital_rescatado / costo_seguro
                                    else:
                                        ratio_eficiencia = 999.0 
                                    
                                    color_ratio = "#10B981" if ratio_eficiencia >= 1.0 else "#EF4444"
                                    estado_ratio = "SEGURO EFICIENTE" if ratio_eficiencia >= 1.0 else "SEGURO EXTORSIVO (Pagas más de lo que salvas)"
                                    
                                    st.markdown(f"""
                                    <div style="background-color: #F1F5F9; padding: 15px; border-radius: 6px; border-left: 5px solid {color_ratio}; margin-top: 15px;">
                                        <h5 style="margin-top: 0; color: #334155;">⚖️ Auditoría de Costo-Beneficio (La Póliza)</h5>
                                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                            <span>📉 <b>Costo de la Prima (Sacrificio si ganas):</b></span>
                                            <span style="color: #EF4444; font-weight: bold;">${costo_seguro:,.0f} COP</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                            <span>🛡️ <b>Capital Rescatado (Salvamento si pierdes):</b></span>
                                            <span style="color: #10B981; font-weight: bold;">${capital_rescatado:,.0f} COP</span>
                                        </div>
                                        <hr style="margin: 10px 0; border-top: 1px solid #CBD5E1;">
                                        <div style="display: flex; justify-content: space-between;">
                                            <span>📊 <b>Veredicto Financiero:</b></span>
                                            <span style="color: {color_ratio}; font-weight: bold;">{estado_ratio} (Ratio: {ratio_eficiencia:.2f}x)</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    dictamen_html = ""
                                    va_empatado = (diferencia_goles == 0)
                                    
                                    if cuota_sl > 0.0 and cuota_ingresada <= cuota_sl:
                                        dictamen_html = f"""
                                        <div style='background-color: #FEF2F2; border-left: 6px solid #B91C1C; padding: 15px; margin-top: 15px; border-radius: 4px; color: #7F1D1D;'>
                                            <h5 style='margin-top:0; color:#991B1B;'>🛑 DICTAMEN: STOP LOSS ESTRUCTURAL ALCANZADO</h5>
                                            <p style='margin:0; font-size:0.95rem;'>La cuota del mercado (<b>{cuota_ingresada:.2f}</b>) ha perforado tu límite. Quema la reserva ahora mismo.</p>
                                        </div>
                                        """
                                    elif ird >= 85.0:
                                        if ratio_eficiencia < 1.0:
                                            dictamen_html = f"""
                                            <div style='background-color: #FEF2F2; border-left: 6px solid #B91C1C; padding: 15px; margin-top: 15px; border-radius: 4px; color: #7F1D1D;'>
                                                <h5 style='margin-top:0; color:#991B1B;'>🚨 DICTAMEN: RIESGO CRÍTICO + SEGURO EXTORSIVO</h5>
                                                <p style='margin:0; font-size:0.95rem;'>Colapso inminente (IRD: {ird:.1f}%), pero la cuota es usurera. Decisión a discreción del Trader.</p>
                                            </div>
                                            """
                                        else:
                                            dictamen_html = f"""
                                            <div style='background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;'>
                                                <h5 style='margin-top:0; color:#991B1B;'>🚨 DICTAMEN: ORDEN DE EVACUACIÓN INMEDIATA</h5>
                                                <p style='margin:0; font-size:0.95rem;'>Ejecuta la cobertura de inmediato para salvaguardar el capital residual.</p>
                                            </div>
                                            """
                                    elif diferencia_goles >= 2 or (diferencia_goles == 1 and tiempo_restante <= 10 and ird < 60.0):
                                        dictamen_html = f"""
                                        <div style='background-color: #F8FAFC; border-left: 6px solid #8B5CF6; padding: 15px; margin-top: 15px; border-radius: 4px; color: #4C1D95;'>
                                            <h5 style='margin-top:0; color:#5B21B6;'>🔮 DICTAMEN: REVOCAR COBERTURA (VENTAJA CONCLUYENTE)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>Retén tu reserva intacta y maximiza el rendimiento.</p>
                                        </div>
                                        """
                                    elif (diferencia_goles <= 0) and (share_nuestro > 50.0) and (ird < 85.0):
                                        dictamen_html = f"""
                                        <div style='background-color: #F0FDF4; border-left: 6px solid #059669; padding: 15px; margin-top: 15px; border-radius: 4px; color: #064E3B;'>
                                            <h5 style='margin-top:0; color:#047857;'>🔍 DICTAMEN: PACIENCIA TÁCTICA (MOMENTUM A FAVOR)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>La tendencia estadística te ampara (IRD: {ird:.1f}%). Mantén la posición.</p>
                                        </div>
                                        """
                                    elif util_inicial_con_cob >= 0 and util_cobertura_con_cob >= 0:
                                        dictamen_html = """
                                        <div style="background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 15px; margin-top: 15px; border-radius: 4px; color: #166534;">
                                            <h5 style="margin: 0 0 5px 0; color: #166534;">✅ DICTAMEN: ARBITRAJE PERFECTO DETECTADO</h5>
                                            <p style="margin: 0; font-size: 0.95rem;">La cuota liquida en verde en ambos escenarios. Asegura utilidades.</p>
                                        </div>
                                        """
                                    elif cuota_ingresada >= op.get('cuota_objetivo', 0):
                                        dictamen_html = """
                                        <div style="background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 15px; margin-top: 15px; border-radius: 4px; color: #166534;">
                                            <h5 style="margin: 0 0 5px 0; color: #166534;">✅ DICTAMEN: EQUILIBRIO OPERATIVO VIGENTE</h5>
                                        </div>
                                        """
                                    elif ratio_eficiencia >= 1.0:
                                        if va_empatado:
                                            if ird > 70:
                                                dictamen_html = f"""
                                                <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                                    <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 DICTAMEN: ALERTA DE QUIEBRE (SALVATAJE DEL EMPATE)</h5>
                                                </div>
                                                """
                                            else:
                                                dictamen_html = f"""
                                                <div style="background-color: #F8FAFC; border-left: 6px solid #94A3B8; padding: 15px; margin-top: 15px; border-radius: 4px; color: #334155;">
                                                    <h5 style="margin: 0 0 5px 0; color: #334155;">💡 DICTAMEN: PACIENCIA TÁCTICA (EMPATE BAJO CONTROL)</h5>
                                                </div>
                                                """
                                        else:
                                            if ird > 60:
                                                dictamen_html = f"""
                                                <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                                    <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 DICTAMEN: MITIGACIÓN URGENTE</h5>
                                                </div>
                                                """
                                            else:
                                                dictamen_html = f"""
                                                <div style="background-color: #EFF6FF; border-left: 6px solid #3B82F6; padding: 15px; margin-top: 15px; border-radius: 4px; color: #1E3A8A;">
                                                    <h5 style="margin: 0 0 5px 0; color: #1E3A8A;">⚖️ DICTAMEN: MANTENER POSICIÓN CON CAUTELA</h5>
                                                </div>
                                                """
                                    elif ratio_eficiencia > 0:
                                        dictamen_html = f"""
                                        <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; margin-top: 15px; border-radius: 4px; color: #92400E;">
                                            <h5 style="margin: 0 0 5px 0; color: #B45309;">⚠️ DICTAMEN: SEGURO INEFICIENTE (INFLACIÓN DE PRECIO)</h5>
                                        </div>
                                        """
                                    else:
                                        dictamen_html = """
                                        <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;">
                                            <h5 style="margin: 0 0 5px 0; color: #991B1B;">🚨 DICTAMEN: EJECUCIÓN INVIABLE</h5>
                                        </div>
                                        """
                                    
                                    saldo_banca_actual = saldo_real if banca_op == "REAL" else saldo_simulacion
                                    exposicion_pct = (cap_total_seguro / saldo_banca_actual) * 100 if saldo_banca_actual > 0 else 0
                                    pct_rescate_banca = (capital_rescatado / saldo_banca_actual) * 100 if saldo_banca_actual > 0 and capital_rescatado > 0 else 0
                                    
                                    if pct_rescate_banca >= 5.0:
                                        impacto_str = "🛑 ALTAMENTE CONSIDERABLE (Vital para la supervivencia de la banca)"
                                        color_impacto = "#BE123C"; bg_impacto = "#FFF1F2"
                                    elif pct_rescate_banca >= 2.0:
                                        impacto_str = "⚠️ CONSIDERABLE (Protege liquidez operativa importante)"
                                        color_impacto = "#B45309"; bg_impacto = "#FFFBEB"
                                    else:
                                        impacto_str = "ℹ️ MARGINAL (Impacto mínimo en la caja general)"
                                        color_impacto = "#334155"; bg_impacto = "#F8FAFC"
                                        
                                    alerta_patrimonial_html = f"""
                                    <div style="background-color: {bg_impacto}; border-left: 5px solid {color_impacto}; padding: 15px; margin-top: 15px; border-radius: 4px; color: #0F172A;">
                                        <h5 style="margin-top: 0; color: {color_impacto};">💼 Contexto de Portafolio ({banca_op})</h5>
                                        <div style="font-size: 0.95rem;">
                                            • <b>Exposición de esta operación:</b> {exposicion_pct:.1f}% de tu cuenta.<br>
                                            • <b>Peso del Capital Rescatado:</b> Si ejecutas el seguro, estás rescatando el <b>{pct_rescate_banca:.2f}%</b> de tu patrimonio total.<br><br>
                                            <b>Veredicto de Rescate:</b> {impacto_str}
                                        </div>
                                    </div>
                                    """
                                    
                                    st.markdown(dictamen_html + alerta_patrimonial_html, unsafe_allow_html=True)
                                    
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
                                        st.markdown("#### 🏁 Conciliación Final del Evento (Cierre Directo / Sin Cobertura)")
                                        resultado_directo = st.radio("Realidad del Partido:", opciones_resultados, key=f"rad_dir_{op['codigo']}")
                                        
                                        st.markdown("---")
                                        st.markdown("🤖 **Datos para Entrenamiento de IA (Obligatorio)**")
                                        goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_{op['codigo']}")
                                        goles_finales_rival = st.number_input(f"🚀 Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_{op['codigo']}")
                                        
                                        if st.form_submit_button("Registrar Liquidación Directa"):
                                            # Inteligencia Contable
                                            gano_fase1 = False
                                            plat_win = ""
                                            
                                            if "Local" in resultado_directo:
                                                gano_fase1 = True
                                                plat_win = p_ini
                                            elif "Empató" in resultado_directo:
                                                if not es_fuego:
                                                    gano_fase1 = True
                                                    plat_win = p_dutch if es_dutching_op else p_ini
                                            elif "Visitante" in resultado_directo:
                                                if es_fuego:
                                                    gano_fase1 = True
                                                    plat_win = p_dutch if es_dutching_op else p_ini
                                            
                                            if gano_fase1:
                                                # Gana la inversión base, pero la reserva no se tocó, por lo que el ROI se hace sobre el Stake 1 gastado
                                                utilidad = (op['stake_1'] * op['cuota_inicial']) - op['stake_1']
                                                texto_cierre = f"Directo: ✅ Ganancia en [{plat_win}] ({resultado_directo})"
                                            else:
                                                utilidad = -op['stake_1']
                                                texto_cierre = f"Directo: ❌ Pérdida de Stake ({resultado_directo})"
                                                
                                            supabase.table("historial_trading").update({
                                                "estado": "CERRADA",
                                                "resultado_final": texto_cierre,
                                                "utilidad_neta_real": utilidad,
                                                "roi_real": (utilidad / cap_total_seguro) * 100 if cap_total_seguro > 0 else 0,
                                                "goles_finales_seleccion": goles_finales_seleccion, 
                                                "goles_finales_rival": goles_finales_rival         
                                            }).eq("codigo", op['codigo']).execute()
                                            st.success(f"Posición liquidada y datos guardados para la IA. Utilidad real transferida: ${utilidad:,.0f} COP.")
                                            st.rerun()

                        elif op['estado'] == "CUBIERTA":
                            st.success(f"🛡️ Cobertura asegurada a tasa de {op.get('cuota_cazada_real', 0):.2f} en {op.get('plataforma_cobertura', 'N/A')}.")
                            with st.form(f"liq_{op['codigo']}"):
                                st.markdown("#### 🏁 Conciliación Final del Evento (Operación Cubierta)")
                                resultado_final_ui = st.radio("Realidad del Partido:", opciones_resultados, key=f"rad_fin_{op['codigo']}")
                                
                                st.markdown("---")
                                st.markdown("🤖 **Datos para Entrenamiento de IA (Obligatorio)**")
                                goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_cob_{op['codigo']}")
                                goles_finales_rival = st.number_input(f"🚀 Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_cob_{op['codigo']}")
                                
                                if st.form_submit_button("Cerrar Libro Mayor"):
                                    # Inteligencia Contable para CUBIERTA
                                    gano_fase1 = False
                                    gano_cobertura = False
                                    plat_win = ""
                                    
                                    if "Local" in resultado_final_ui:
                                        gano_fase1 = True
                                        plat_win = p_ini
                                    elif "Empató" in resultado_final_ui:
                                        if es_fuego:
                                            gano_cobertura = True
                                            plat_win = p_cob
                                        else:
                                            gano_fase1 = True
                                            plat_win = p_dutch if es_dutching_op else p_ini
                                    elif "Visitante" in resultado_final_ui:
                                        if es_fuego:
                                            gano_fase1 = True
                                            plat_win = p_dutch if es_dutching_op else p_ini
                                        else:
                                            gano_cobertura = True
                                            plat_win = p_cob
                                            
                                    if gano_fase1:
                                        utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                        texto_db = f"✅ Utilidad Base en [{plat_win}] ({resultado_final_ui})"
                                    else: # Por fuerza matemática, si no ganó Fase 1, ganó la Cobertura (porque cubriste todo el mercado)
                                        utilidad = (op['reserva_stake_2'] * op['cuota_cazada_real']) - op['capital_total']
                                        texto_db = f"🛡️ Utilidad Seguro en [{plat_win}] ({resultado_final_ui})"
                                        
                                    supabase.table("historial_trading").update({
                                        "estado": "CERRADA",
                                        "resultado_final": texto_db,
                                        "utilidad_neta_real": utilidad,
                                        "roi_real": (utilidad / cap_total_seguro) * 100 if cap_total_seguro > 0 else 0,
                                        "goles_finales_seleccion": goles_finales_seleccion, 
                                        "goles_finales_rival": goles_finales_rival         
                                    }).eq("codigo", op['codigo']).execute()
                                    st.success(f"Libro cerrado y datos guardados para la IA. Balance de la operación: ${utilidad:,.0f} COP.")
                                    st.rerun()

        
# =====================================================================
# MÓDULO 4: AUDITORÍA CUANTITATIVA Y LIBRO MAYOR
# =====================================================================
elif estrategia_activa == "🔬 Auditoría Cuantitativa (Reporte)":
    st.markdown("## 📊 Libro Mayor Contable (Cierres Históricos)")
    st.write("Historial completo de transacciones liquidadas y estado de resultados.")
    
    import datetime
    import pandas as pd
    
    # 🛑 EL BOTÓN QUE FRENA LA CARGA PESADA DE MEMORIA
    mostrar_informe = st.checkbox("🚀 Generar Informe Contable y Gráficas (Haz clic aquí para cargar)")
    
    if supabase is not None and mostrar_informe:
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        
        if not df.empty:
            df_mostrar = df[['fecha', 'tipo_banca', 'codigo', 'partido', 'seleccion_inicial', 'resultado_final', 'utilidad_neta_real', 'roi_real']].copy()
            df_mostrar['fecha'] = df_mostrar['fecha'].astype(str)
            df_mostrar['utilidad_neta_real'] = pd.to_numeric(df_mostrar['utilidad_neta_real'], errors='coerce').fillna(0.0)
            df_mostrar['roi_real'] = pd.to_numeric(df_mostrar['roi_real'], errors='coerce').fillna(0.0)
            
            df_mostrar_html = df_mostrar.copy()
            df_mostrar_html['utilidad_neta_real'] = df_mostrar_html['utilidad_neta_real'].apply(lambda x: f"${x:,.0f}")
            df_mostrar_html['roi_real'] = df_mostrar_html['roi_real'].apply(lambda x: f"{x:.1f}%")
            
            # --- PAGINACIÓN DE LA TABLA (Para no colgar el navegador) ---
            filas_por_pagina = 15
            total_paginas = max(1, len(df_mostrar_html) // filas_por_pagina + (1 if len(df_mostrar_html) % filas_por_pagina > 0 else 0))
            
            col_pag1, col_pag2 = st.columns([1, 4])
            with col_pag1:
                pagina_actual = st.number_input("Página:", min_value=1, max_value=total_paginas, value=1, step=1)
            
            inicio_idx = (pagina_actual - 1) * filas_por_pagina
            fin_idx = inicio_idx + filas_por_pagina
            
            st.write(f"Mostrando operaciones de la {inicio_idx + 1} a la {min(fin_idx, len(df_mostrar_html))} de un total de {len(df_mostrar_html)}")
            st.dataframe(df_mostrar_html.iloc[inicio_idx:fin_idx], use_container_width=True, height=550)
            
            hoy = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date()
            df['fecha_dt'] = pd.to_datetime(df['fecha'], utc=True) - pd.Timedelta(hours=5)
            df['dia'] = df['fecha_dt'].dt.date
            df['hora_cierre'] = df['fecha_dt'].dt.strftime('%H:%M')
            
            st.markdown("---")
            st.markdown("### 📈 Estado de Resultados Desagregado")
            
            df_real_master = df[df['tipo_banca'] == 'REAL'].copy()
            df_sim_master = df[df['tipo_banca'] == 'SIMULACION'].copy()
            
            tab_real, tab_sim = st.tabs(["🟢 Contabilidad Real", "🟡 Contabilidad Simulación (Paper Trading)"])
            
            with tab_real:
                if not df_real_master.empty:
                    filtro_tiempo_r = st.radio("Alcance Temporal (Real):", ["📅 Hoy", "📈 Consolidación Histórica"], horizontal=True, key="filtro_t_real")
                    df_hoy_r = df_real_master[df_real_master['dia'] == hoy]
                    utilidad_hoy_r = df_hoy_r['utilidad_neta_real'].sum()
                    ops_hoy_r = len(df_hoy_r)
                    utilidad_total_r = df_real_master['utilidad_neta_real'].sum()
                    
                    if filtro_tiempo_r == "📅 Hoy":
                        st.metric(label="💵 Cierre de Caja (Hoy)", value=f"${utilidad_hoy_r:,.0f} COP", delta=f"{ops_hoy_r} operaciones cerradas")
                        if not df_hoy_r.empty:
                            df_hoy_r = df_hoy_r.sort_values(by='fecha_dt')
                            df_hoy_r['operacion'] = df_hoy_r['hora_cierre'] + " - " + df_hoy_r['codigo']
                            st.bar_chart(df_hoy_r.set_index('operacion')['utilidad_neta_real'])
                    else: 
                        st.metric(label="💰 Utilidad Neta Acumulada", value=f"${utilidad_total_r:,.0f} COP")
                        # Gráfica ligera (Últimos 30 días para no saturar memoria)
                        st.bar_chart(df_real_master.groupby('dia')['utilidad_neta_real'].sum().tail(30))
                else:
                    st.info("No hay transacciones cerradas en Dinero Real.")
            
            with tab_sim:
                if not df_sim_master.empty:
                    filtro_tiempo_s = st.radio("Alcance Temporal (Simulación):", ["📅 Hoy", "📈 Consolidación Histórica"], horizontal=True, key="filtro_t_sim")
                    df_hoy_s = df_sim_master[df_sim_master['dia'] == hoy]
                    utilidad_hoy_s = df_hoy_s['utilidad_neta_real'].sum()
                    ops_hoy_s = len(df_hoy_s)
                    utilidad_total_s = df_sim_master['utilidad_neta_real'].sum()
                    
                    if filtro_tiempo_s == "📅 Hoy":
                        st.metric(label="💵 Cierre Virtual (Hoy)", value=f"${utilidad_hoy_s:,.0f} COP", delta=f"{ops_hoy_s} ops virtuales")
                        if not df_hoy_s.empty:
                            df_hoy_s = df_hoy_s.sort_values(by='fecha_dt')
                            df_hoy_s['operacion'] = df_hoy_s['hora_cierre'] + " - " + df_hoy_s['codigo']
                            st.bar_chart(df_hoy_s.set_index('operacion')['utilidad_neta_real'])
                    else: 
                        st.metric(label="💰 Utilidad Virtual Acumulada", value=f"${utilidad_total_s:,.0f} COP")
                        # Gráfica ligera (Últimos 30 días)
                        st.bar_chart(df_sim_master.groupby('dia')['utilidad_neta_real'].sum().tail(30))
                else:
                    st.info("No hay transacciones cerradas en Paper Trading.")
        else:
            st.info("La base de datos está limpia. No hay operaciones registradas aún.")
            
    elif supabase is None:
        st.error("Conecta Supabase primero.")
    else:
        st.info("👆 Activa la casilla de arriba para procesar los datos y cargar el Libro Mayor Contable de forma segura.")

    st.markdown("---")

    st.markdown("### 🔬 Auditoría por Frecuencia y Utilidad Neta")
    st.write("Evalúa la viabilidad del modelo midiendo **cuántas veces aciertas** (Frecuencia) y la **plata real que queda** (Utilidad), aislando el ruido del tamaño de la apuesta.")
    
    if supabase is None:
        st.error("Conecta Supabase para acceder al motor estadístico.")
    else:
        # Extraer TODOS los registros cerrados (Simulación + Real) para maximizar la muestra estadística
        res_audit = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").execute()
        df_sim = pd.DataFrame(res_audit.data) # Mantenemos la variable df_sim interna para no afectar el resto de tu código
        
        if df_sim.empty:
            st.info("Aún no hay operaciones finalizadas para auditar.")
        else:
            # ---------------------------------------------------------
            # 1. CLASIFICADOR DINÁMICO DE SUB-ESTRATEGIAS
            # ---------------------------------------------------------
            def clasificar_estrategia(row):
                est_original = str(row.get('estrategia', ''))
                sel_ini = str(row.get('seleccion_inicial', ''))
                
                # Si es eSports, el algoritmo entra a desglosarla según lo que operaste
                if "eSports" in est_original:
                    if "Menos de" in sel_ini or "Más de" in sel_ini or "Goles" in sel_ini:
                        return "⚡ eSports: Mercado de Goles"
                    elif "+ Gana" in sel_ini:
                        return "⚡ eSports: Fuego Cruzado (Empate Amenaza)"
                    else:
                        # Deducimos si es favorito evaluando quién tenía la cuota más baja
                        try:
                            c_base = float(row.get('cuota_base_audit', 0))
                            c_amenaza = float(row.get('cuota_amenaza_audit', 0))
                            if c_base > 0 and c_amenaza > 0:
                                if c_base < c_amenaza:
                                    return "⚡ eSports: Gana Favorito"
                                else:
                                    return "⚡ eSports: Gana No Favorito (Sorpresa)"
                            else:
                                return "⚡ eSports: Histórico (Sin datos de cuota)"
                        except:
                            return "⚡ eSports: Histórico (Sin datos de cuota)"
                elif "Binario" in est_original:
                    # Pasamos todo el texto a minúsculas para que no hayan errores de lectura
                    texto_mercado = str(row.get('partido', '')).lower()
                    
                    if "ambos anotan" in texto_mercado:
                        return "🔥 Binario: Ambos Anotan"
                    elif "línea de goles" in texto_mercado or "linea de goles" in texto_mercado:
                        return "⚽ Binario: Línea de Goles"
                    else:
                        return "✍️ Binario: Otros Mercados Personalizados"
                elif not est_original or str(est_original) == 'nan':
                    return "⚽ Estrategia 2: Paz Mental Clásica"
                else:
                    return est_original

            # Aplicamos el clasificador al DataFrame
            df_sim['estrategia_desglosada'] = df_sim.apply(clasificar_estrategia, axis=1)
            
            # Llenamos el menú desplegable con las sub-estrategias encontradas
            estrategias_disponibles = sorted(df_sim['estrategia_desglosada'].dropna().unique().tolist())
            estrategia_seleccionada = st.selectbox("📌 Selecciona la rama específica a auditar:", estrategias_disponibles)
            
            # EL FILTRO MAESTRO: Aísla los datos para que no se mezcle dinero ni frecuencias
            df_est = df_sim[df_sim['estrategia_desglosada'] == estrategia_seleccionada].copy()
            total_ops = len(df_est)
            
            if total_ops == 0:
                st.info(f"No hay registros cerrados para la estrategia: {estrategia_seleccionada}")
            else:
                if st.button(f"📈 Generar Dictamen Cuantitativo ({total_ops} Operaciones)"):
                    
                    st.markdown("---")
                    
                    # 2. SELLO DE AUDITORÍA DINÁMICO
                    if total_ops < 5:
                        st.markdown(f"""
                        <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: #991B1B;">
                            <h4 style="margin-top: 0; color: #991B1B;">🚨 DICTAMEN: MUESTRA CRÍTICA (POCO VOLUMEN)</h4>
                            <p style="margin-bottom: 0; font-size: 0.95rem;">
                                Tienes solo <b>{total_ops} operaciones</b> en esta rama. Es imposible saber si la estrategia es buena o mala porque el azar influye demasiado.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif total_ops < 100:
                        st.markdown(f"""
                        <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; border-radius: 5px; margin-bottom: 20px; color: #92400E;">
                            <h4 style="margin-top: 0; color: #B45309;">⚠️ DICTAMEN PRELIMINAR (EN DESARROLLO)</h4>
                            <p style="margin-bottom: 0; font-size: 0.95rem;">
                                Con <b>{total_ops} operaciones</b> ya se nota una tendencia, pero para que un modelo se declare "probado" requieres mínimo 100 eventos continuos.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success(f"✅ CERTIFICACIÓN OFICIAL: ESTRATEGIA ESTADÍSTICAMENTE PROBADA ({total_ops} ops).")

                    # ---------------------------------------------------------
                    # 3. CÁLCULOS POR FRECUENCIA Y DINERO EXCLUSIVO
                    # ---------------------------------------------------------
                    victorias_pre_partido = df_est['resultado_final'].str.contains("Pre-Partido|Ganó Inicial|Apuesta Inicial", case=False, na=False).sum()
                    victorias_cobertura = df_est['resultado_final'].str.contains("Cobertura|Profit|Seguro", case=False, na=False).sum()
                    derrotas_totales = df_est['resultado_final'].str.contains("Déficit|Perdió|Pérdida|Loss", case=False, na=False).sum()
                    
                    total_ganadas = victorias_pre_partido + victorias_cobertura
                    efectividad_global = (total_ganadas / total_ops) * 100 if total_ops > 0 else 0
                    
                    win_rate = (victorias_pre_partido / total_ops) * 100
                    loss_rate = (derrotas_totales / total_ops) * 100
                    
                    try:
                        cuota_promedio = df_est['cuota_inicial'].astype(float).mean()
                    except:
                        cuota_promedio = 1.0
                    
                    # Cálculo exclusivo de dinero para la estrategia seleccionada
                    try:
                        utilidad_neta_total = df_est['utilidad_neta_real'].astype(float).sum()
                        capital_total_movilizado = df_est['capital_total'].astype(float).sum()
                        roi_historico_estrategia = (utilidad_neta_total / capital_total_movilizado) * 100 if capital_total_movilizado > 0 else 0
                    except:
                        utilidad_neta_total = 0
                        capital_total_movilizado = 0
                        roi_historico_estrategia = 0

                    # CÁLCULO DE TIEMPO PROMEDIO DE COBERTURA
                    tiempo_promedio_cob = 0
                    if 'hora_inicio_partido' in df_est.columns and 'hora_cobertura' in df_est.columns:
                        df_tiempos = df_est.dropna(subset=['hora_inicio_partido', 'hora_cobertura']).copy()
                        if not df_tiempos.empty:
                            try:
                                t_inicio = pd.to_datetime(df_tiempos['hora_inicio_partido'], format='%H:%M')
                                t_cob = pd.to_datetime(df_tiempos['hora_cobertura'], format='%H:%M')
                                diff_minutos = (t_cob - t_inicio).dt.total_seconds() / 60.0
                                diff_minutos = diff_minutos.apply(lambda x: x + 1440 if x < 0 else x)
                                tiempo_promedio_cob = diff_minutos.mean()
                            except Exception:
                                tiempo_promedio_cob = 0

                    ev = ((efectividad_global / 100) * (cuota_promedio - 1)) - (loss_rate / 100)
                    
                    # ---------------------------------------------------------
                    # 4. MOTOR DE DECISIÓN AUDITADO (DINERO + FRECUENCIA)
                    # ---------------------------------------------------------
                    if utilidad_neta_total < 0:
                        if efectividad_global >= 50:
                            veredicto = "⚠️ ILUSIÓN DE RENTABILIDAD (Falsa Seguridad)"
                            color_v = "#F59E0B"
                            desc_v = "Ganas frecuentemente, pero las pérdidas son tan grandes que destruyen tu capital. El ROI es negativo. Revisa tu Stop Loss en esta rama específica."
                        else:
                            veredicto = "🚨 SISTEMA EN QUIEBRA (Modelo Deficiente)"
                            color_v = "#EF4444"
                            desc_v = "Matemática y financieramente en rojo. Baja tasa de aciertos y pérdida de patrimonio evidente. Detener ejecución."
                    else:
                        if efectividad_global >= 70 and ev > 0:
                            veredicto = "💎 SISTEMA DE ALTO RENDIMIENTO (>70% Acierto)"
                            color_v = "#3B82F6"
                            desc_v = "Caja en verde y frecuencia de éxito altísima. Modelo altamente consistente y listo para escalado."
                        elif efectividad_global >= 50:
                            veredicto = "✅ ESTRATEGIA ESTABLE Y RENTABLE"
                            color_v = "#10B981"
                            desc_v = "El balance contable es positivo y la tasa de aciertos es saludable. Mantén el rigor disciplinario."
                        else:
                            veredicto = "⚠️ RENTABILIDAD POR SUERTE (Alta Varianza)"
                            color_v = "#8B5CF6"
                            desc_v = "Tienes utilidad positiva, pero aciertas menos del 50% de las veces. Tu rentabilidad depende de cazar cuotas muy altas. Cuidado con las rachas perdedoras."

                    # --- RENDERIZADO DEL DASHBOARD FINANCIERO ---
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
                    .metric-card h2 { margin: 10px 0; font-size: 2.2rem; font-weight: bold; }
                    .metric-card p { margin-bottom: 0; color: #64748B; font-size: 0.9rem; font-weight: 500; }
                    </style>
                    """, unsafe_allow_html=True)

                    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
                    with col_kpi1:
                        st.markdown(f'<div class="metric-card"><h4>🎯 Tasa de Éxito (Hit Rate)</h4><h2 style="color: {"#10B981" if efectividad_global >= 50 else "#EF4444"}">{efectividad_global:.1f}%</h2><p>{total_ganadas} operaciones en verde</p></div>', unsafe_allow_html=True)
                    with col_kpi2:
                        st.markdown(f'<div class="metric-card"><h4>💵 Utilidad Neta Real</h4><h2 style="color: {"#10B981" if utilidad_neta_total >= 0 else "#EF4444"}">${utilidad_neta_total:,.0f}</h2><p>Balance exclusivo de esta rama</p></div>', unsafe_allow_html=True)
                    with col_kpi3:
                        st.markdown(f'<div class="metric-card"><h4>📈 ROI de la Estrategia</h4><h2 style="color: {"#3B82F6" if roi_historico_estrategia > 0 else "#EF4444"}">{roi_historico_estrategia:,.1f}%</h2><p>Sobre ${capital_total_movilizado:,.0f} invertidos aquí</p></div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.subheader("📊 Radiografía Operativa (Conteo de Veces)")
                    
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Volumen Auditado", f"{total_ops} ops")
                    c2.metric("Acertó Inicial", f"{victorias_pre_partido} veces")
                    c3.metric("Entró Seguro", f"{victorias_cobertura} veces")
                    c4.metric("Siniestros (Rojo)", f"{derrotas_totales} veces")
                    
                    texto_tiempo = f"{tiempo_promedio_cob:.0f} min" if tiempo_promedio_cob > 0 else "N/A"
                    c5.metric("Tiempo a Cobertura", texto_tiempo)

                    # =====================================================================
                    # 🧠 MAPA DE EFECTIVIDAD DE CAZA (POR VECES)
                    # =====================================================================
                    st.markdown("---")
                    st.subheader("🎯 Efectividad Atrapando el Seguro (Mapa de Calor)")
                    st.write("Mide la **frecuencia de captura**: ¿En qué nivel de cuota eres mejor asegurando ganancias?")
                    
                    # Filtramos operaciones que intentaron usar esquema de cobertura
                    df_cob_data = df_est[df_est['cuota_objetivo'] > 0].copy()
                    
                    if not df_cob_data.empty:
                        df_cob_data['seguro_cazado'] = df_cob_data['cuota_cazada_real'] > 0
                        
                        # 1. Crear los tramos contables
                        bins = [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 1000.0]
                        labels = [
                            '🛡️ Conservador (1.01 a 1.99)', 
                            '⚖️ Moderado (2.00 a 2.99)', 
                            '🔥 Agresivo (3.00 a 4.99)', 
                            '🚀 Extremo (5.00 a 7.99)',
                            '⚡ Riesgo Alto (8.00 a 11.99)',
                            '🌪️ Kamikaze (12.00 a 19.99)',
                            '🌌 Astronómico (20.00+)'
                        ]
                        
                        df_cob_data['tramo'] = pd.cut(df_cob_data['cuota_objetivo'].astype(float), bins=bins, labels=labels, right=False)
                        
                        # 2. Agrupar la estadística por cada tramo (Por Frecuencia de Veces)
                        resumen = df_cob_data.groupby('tramo', observed=False).agg(
                            Intentos=('cuota_objetivo', 'count'),
                            Exitos=('seguro_cazado', 'sum')
                        ).reset_index()
                        
                        # 3. Limpiar los tramos vacíos
                        resumen = resumen[resumen['Intentos'] > 0].copy()
                        
                        # 4. Calcular los porcentajes reales de acierto
                        resumen['Tasa de Éxito'] = (resumen['Exitos'] / resumen['Intentos']) * 100
                        
                        # Renombrar columnas
                        resumen.columns = ['Nivel de Riesgo (Cuota Objetivo)', 'Intentos (Veces)', 'Atrapadas (Veces)', '% Efectividad Bruta']
                        
                        # Renderizar tabla
                        resumen_show = resumen.copy()
                        resumen_show['% Efectividad Bruta'] = resumen_show['% Efectividad Bruta'].apply(lambda x: f"{x:.1f}%")
                        st.dataframe(resumen_show, use_container_width=True, hide_index=True)
                        
                        # 5. El Dictamen Táctico
                        if len(resumen) > 1:
                            mejor_tramo = resumen.loc[resumen['% Efectividad Bruta'].idxmax()]
                            peor_tramo = resumen.loc[resumen['% Efectividad Bruta'].idxmin()]
                            
                            if mejor_tramo['% Efectividad Bruta'] == peor_tramo['% Efectividad Bruta']:
                                st.info("💡 Tienes la misma efectividad de caza en todos los tramos. Cierra más operaciones de prueba para generar un patrón estadístico.")
                            else:
                                st.success(f"💡 **Dictamen:** Tu zona más sólida de captura es el rango **{mejor_tramo['Nivel de Riesgo (Cuota Objetivo)']}**, logras atrapar la cobertura el **{mejor_tramo['% Efectividad Bruta']:.1f}%** de las veces. Evita el nivel **{peor_tramo['Nivel de Riesgo (Cuota Objetivo)']}**, donde tu acierto cae al **{peor_tramo['% Efectividad Bruta']:.1f}%**.")
                        else:
                            st.info("💡 Solo has operado en un único rango de riesgo. Intenta variar tus cuotas en las próximas simulaciones para construir este mapa.")
                    else:
                        st.info("Muestra insuficiente de coberturas para generar el mapa de efectividad.")

# =====================================================================
# MÓDULO 5: ORÁCULO PREDICTIVO (MACHINE LEARNING BÁSICO)
# =====================================================================
elif estrategia_activa == "🔮 Oráculo Predictivo (Machine Learning)":
    st.markdown("## 🔮 Oráculo Predictivo")
    st.write("Planifica tu entrada al mercado basándote en la estadística dura de tu base de datos, no en intuición.")

    tab_pre, tab_vivo = st.tabs(["📋 Planificación Pre-Partido", "⏱️ Oráculo En Vivo (Foto Táctica)"])

    # ---------------------------------------------------------
    # PESTAÑA 1: PRE-PARTIDO (Oráculo Machine Learning)
    # ---------------------------------------------------------
    with tab_pre:
        st.subheader("🧠 Oráculo Predictivo (Machine Learning)")
        st.info("El Oráculo ya no busca coincidencias manuales. Ahora usa 3 Redes Neuronales entrenadas con casi 500,000 partidos para detectar las ineficiencias del mercado.")

        if not modelos_cargados:
            st.error("🚨 Modelos no encontrados. Por favor, ejecuta 'entrenar_global.py' primero.")
        else:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("**📊 Promedio del Mercado Mundial**")
                avg_h = st.number_input("Promedio Local:", min_value=1.01, value=2.10, step=0.05)
                avg_d = st.number_input("Promedio Empate:", min_value=1.01, value=3.20, step=0.05)
                avg_a = st.number_input("Promedio Visita:", min_value=1.01, value=3.50, step=0.05)
            with col_m2:
                st.markdown("**💰 Cuotas en tu Casa de Apuestas**")
                max_h = st.number_input("Tu Cuota Local:", min_value=1.01, value=2.25, step=0.05)
                max_d = st.number_input("Tu Cuota Empate:", min_value=1.01, value=3.30, step=0.05)
                max_a = st.number_input("Tu Cuota Visita:", min_value=1.01, value=3.60, step=0.05)
            
            st.markdown("---")
            col_ev1, col_ev2 = st.columns(2)
            with col_ev1:
                mercado_evaluar = st.selectbox("¿Qué mercado vas a auditar?", ["Gana Local", "Empate", "Gana Visita"])
            with col_ev2:
                stake_pre = st.number_input("Stake ($ COP):", min_value=5000, value=20000, step=5000)

            if st.button("🚀 Ejecutar Red Neuronal", use_container_width=True):
                with st.spinner("Decodificando ineficiencias matemáticas..."):
                    # 1. Calcular las "trampas" (ineficiencias)
                    inef_h = max_h - avg_h
                    inef_d = max_d - avg_d
                    inef_a = max_a - avg_a
                    n_odds = 15 # Valor estándar de liquidez
                    
                    # 2. Empaquetar para la IA
                    input_data = pd.DataFrame([[
                        avg_h, avg_d, avg_a, max_h, max_d, max_a,
                        inef_h, inef_d, inef_a, n_odds, n_odds, n_odds
                    ]], columns=[
                        'avg_odds_home_win', 'avg_odds_draw', 'avg_odds_away_win',
                        'max_odds_home_win', 'max_odds_draw', 'max_odds_away_win',
                        'ineficiencia_local', 'ineficiencia_empate', 'ineficiencia_visita',
                        'n_odds_home_win', 'n_odds_draw', 'n_odds_away_win'
                    ])
                    
                    # 3. La IA hace sus predicciones instantáneas
                    prob_1x2 = modelo_1x2.predict_proba(input_data)[0] 
                    prob_empate = prob_1x2[0]
                    prob_local = prob_1x2[1]
                    prob_visita = prob_1x2[2]
                    
                    pred_goles = modelo_goles.predict(input_data)[0]
                    prob_btts = modelo_btts.predict_proba(input_data)[0][1] 
                    
                    # 4. Cálculos de Valor Esperado (EV) para el mercado seleccionado
                    if mercado_evaluar == "Gana Local":
                        prob_real = prob_local
                        cuota_mercado = max_h
                    elif mercado_evaluar == "Gana Visita":
                        prob_real = prob_visita
                        cuota_mercado = max_a
                    else:
                        prob_real = prob_empate
                        cuota_mercado = max_d
                        
                    prob_perder = 1.0 - prob_real
                    ganancia_neta = (stake_pre * cuota_mercado) - stake_pre
                    ev = (prob_real * ganancia_neta) - (prob_perder * stake_pre)
                    roi_ev = (ev / stake_pre) * 100 if stake_pre > 0 else 0
                    
                    # 5. Imprimir Resultados
                    st.markdown("---")
                    st.markdown("### 🏆 Probabilidades Reales (IA)")
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Local", f"{prob_local*100:.1f}%")
                    r2.metric("Empate", f"{prob_empate*100:.1f}%")
                    r3.metric("Visita", f"{prob_visita*100:.1f}%")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### ⚽ Radar de Goles")
                    g1, g2 = st.columns(2)
                    g1.metric("Goles Esperados", f"{pred_goles:.2f} goles")
                    g2.metric("Ambos Anotan (Sí)", f"{prob_btts*100:.1f}%")
                    
                    st.markdown("---")
                    st.markdown(f"### ⚖️ Veredicto de Valor: {mercado_evaluar}")
                    if ev > 0:
                        st.markdown(f"""
                        <div style="background-color: #F0FDF4; border-left: 6px solid #22C55E; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top:0; color: #166534;">✅ ERROR DE LA CASA (EV+)</h3>
                            <h1 style="color: #15803D; margin: 10px 0;">+${ev:,.0f} COP <span style="font-size: 1rem;">de valor puro</span></h1>
                            <p style="margin:0; color: #166534;">La probabilidad real global es <b>{prob_real*100:.1f}%</b>. A cuota <b>{cuota_mercado}</b>, tienes ventaja matemática. <b>(ROI Proyectado: +{roi_ev:.1f}%)</b>.</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: #FEF2F2; border-left: 6px solid #EF4444; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top:0; color: #991B1B;">🚨 TRAMPA DE LA CASA (EV-)</h3>
                            <h1 style="color: #B91C1C; margin: 10px 0;">-${abs(ev):,.0f} COP <span style="font-size: 1rem;">de pérdida esperada</span></h1>
                            <p style="margin:0; color: #991B1B;">A largo plazo perderás dinero. La probabilidad real es solo <b>{prob_real*100:.1f}%</b>. Aléjate. <b>(ROI: {roi_ev:.1f}%)</b>.</p>
                        </div>
                        """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: EN VIVO (Oráculo Táctico Puro)
    # ---------------------------------------------------------
    with tab_vivo:
        st.subheader("🧠 El Cerebro Táctico (Machine Learning)")
        st.write("Ingresa tu Foto Táctica actual. La IA, operando como un analista puro (ciega a las cuotas de la casa), cruzará el asedio en cancha para darte una predicción integral al instante.")
        
        st.markdown("#### 📸 Foto Táctica En Vivo")
        c_vivo1, c_vivo2, c_vivo3 = st.columns(3)
        minuto_sim = c_vivo1.number_input("⏱️ Minuto Actual:", min_value=1, max_value=120, value=60)
        g_loc_sim = c_vivo2.number_input("⚽ Goles Local:", min_value=0, value=0)
        g_vis_sim = c_vivo3.number_input("⚽ Goles Visitante:", min_value=0, value=0)
        
        c_vivo4, c_vivo5, c_vivo6 = st.columns(3)
        atq_loc_sim = c_vivo4.number_input("🔥 Atq. Pel. Local:", min_value=0, value=40)
        atq_vis_sim = c_vivo5.number_input("🔥 Atq. Pel. Visitante:", min_value=0, value=25)
        # La caja de "Cuota Ofrecida" ha sido eliminada por completo.
        
        if st.button("🧠 Despertar Oráculo (Proyectar Escenario)", use_container_width=True):
            import joblib
            import pandas as pd
            import os
            
            # Verificamos que los cerebros existan en la carpeta
            if not os.path.exists('modelo_1x2.pkl'):
                st.error("🚨 Falta el archivo 'modelo_1x2.pkl'. Asegúrate de que los 3 cerebros estén en la misma carpeta.")
            else:
                with st.spinner("Procesando redes neuronales tácticas..."):
                    try:
                        # 1. Cargar los cerebros congelados
                        modelo_1x2 = joblib.load('modelo_1x2.pkl')
                        modelo_goles = joblib.load('modelo_goles.pkl')
                        modelo_btts = joblib.load('modelo_btts.pkl')
                        
                        # 2. Calcular el IRD para la IA
                        apm_total = (atq_loc_sim + atq_vis_sim) / max(1, minuto_sim)
                        ird_sim = min(100.0, apm_total * 45.0)
                        
                        # 3. Empaquetar las 6 variables tácticas EXACTAS
                        X_input = pd.DataFrame([{
                            'minuto_evaluado': minuto_sim,
                            'goles_local': g_loc_sim,
                            'goles_vis': g_vis_sim,
                            'atkp_local': atq_loc_sim,
                            'atkp_vis': atq_vis_sim,
                            'ird_calculado': ird_sim
                        }])
                        
                        # 4. Extraer las Predicciones
                        pred_1x2 = modelo_1x2.predict(X_input)[0]
                        pred_goles = modelo_goles.predict(X_input)[0]
                        pred_btts = modelo_btts.predict(X_input)[0]
                        
                        # 5. Traducción de resultados de máquina a humano
                        ganador_str = "Empate" if pred_1x2 == 1 else "Equipo Local" if pred_1x2 == 2 else "Equipo Visitante"
                        btts_str = "SÍ" if pred_btts == 1 else "NO"
                        color_btts = "#10B981" if pred_btts == 1 else "#EF4444"
                        # -------------------------------------------------------------
                        # 🎯 MOTOR DE TRIANGULACIÓN (MARCADOR EXACTO REALISTA)
                        # -------------------------------------------------------------
                        goles_actuales_totales = g_loc_sim + g_vis_sim
                        goles_nuevos_esperados = max(0, round(pred_goles) - goles_actuales_totales)
                        
                        calc_loc = g_loc_sim
                        calc_vis = g_vis_sim

                        if pred_1x2 == 1: 
                            if calc_loc > calc_vis: calc_vis = calc_loc 
                            elif calc_vis > calc_loc: calc_loc = calc_vis 
                            elif goles_nuevos_esperados >= 2:
                                calc_loc += 1
                                calc_vis += 1
                        elif pred_1x2 == 2:
                            if calc_loc <= calc_vis: calc_loc = calc_vis + max(1, goles_nuevos_esperados)
                            else: calc_loc += goles_nuevos_esperados
                        else:
                            if calc_vis <= calc_loc: calc_vis = calc_loc + max(1, goles_nuevos_esperados)
                            else: calc_vis += goles_nuevos_esperados

                        if pred_btts == 1:
                            if calc_loc == 0: calc_loc = 1
                            if calc_vis == 0: calc_vis = 1

                        marcador_exacto = f"{calc_loc} - {calc_vis}"

                        # -------------------------------------------------------------
                        # ⏱️ ÁRBITRO DE TIEMPO (FILTRO ANTI-REMONTADAS IMPOSIBLES)
                        # -------------------------------------------------------------
                        minutos_restantes = 90 - minuto_sim
                        diferencia_goles_real = abs(g_loc_sim - g_vis_sim) # <--- AHORA SÍ MIRA LA REALIDAD
                        
                        # Definimos quién va ganando en la vida real (1=Empate, 2=Local, 3=Visita)
                        lider_real = 1 if g_loc_sim == g_vis_sim else (2 if g_loc_sim > g_vis_sim else 3)
                        
                        # El Árbitro SOLO interviene si alguien ya va ganando y la IA predice que lo van a empatar o remontar
                        if lider_real != 1 and pred_1x2 != lider_real:
                            # Regla física: 1 gol requiere en promedio 10 minutos de asedio
                            if (diferencia_goles_real * 10) > minutos_restantes:
                                # ¡Físicamente imposible! Restauramos el marcador a favor del líder real.
                                if lider_real == 2:
                                    calc_loc = g_loc_sim
                                    calc_vis = g_vis_sim + (1 if pred_btts == 1 and g_vis_sim == 0 and minutos_restantes >= 5 else 0)
                                    marcador_exacto = f"{calc_loc} - {calc_vis}"
                                    ganador_str = "Equipo Local (Corregido por Reloj)"
                                else:
                                    calc_loc = g_loc_sim + (1 if pred_btts == 1 and g_loc_sim == 0 and minutos_restantes >= 5 else 0)
                                    calc_vis = g_vis_sim
                                    marcador_exacto = f"{calc_loc} - {calc_vis}"
                                    ganador_str = "Equipo Visitante (Corregido por Reloj)"
                                    
                                st.markdown(f"""
                                <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
                                    <h4 style="margin-top:0; color:#B45309;">⏱️ ALERTA DEL ÁRBITRO DE TIEMPO</h4>
                                    <p style="margin:0; color:#92400E;">La IA proyectó un Empate/Remontada por la alta presión ofensiva, pero la diferencia es de <b>{diferencia_goles_real} goles</b> y solo quedan <b>{minutos_restantes} minutos</b>. El Risk Manager ha bloqueado la predicción por ser físicamente imposible.</p>
                                </div>
                                """, unsafe_allow_html=True)
                        # -------------------------------------------------------------
                        # ---> ¡ESTAS DOS LÍNEAS SON VITALES! <---
                        apm_loc = atq_loc_sim / max(1, minuto_sim)
                        apm_vis = atq_vis_sim / max(1, minuto_sim)
                        
                        # Si la IA predice que "Ambos Anotan" (SÍ)
                        if pred_btts == 1:
                            if apm_loc < 0.5 or apm_vis < 0.5:
                                st.markdown("""
                                <div style="background-color: #FFFBEB; border-left: 6px solid #F59E0B; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
                                    <h4 style="margin-top:0; color:#B45309;">⚠️ ADVERTENCIA DE SENTIDO COMÚN</h4>
                                    <p style="margin:0; color:#92400E;">La IA proyecta <b>SÍ (Ambos Anotan)</b> basándose en estadística, pero el volumen ofensivo actual es de <b>menos de 0.5 APM</b>.<br>
                                    El Oráculo tiene autonomía, pero el Risk Manager sugiere extrema cautela en esta entrada.</p>
                                </div>
                                """, unsafe_allow_html=True)
                                # AQUÍ QUITAMOS LA SOBREESCRITURA. La IA mantiene su respuesta original. 
                        st.markdown("---")
                        st.markdown("### 🔮 Veredicto del Oráculo (Análisis Físico)")
                        # Tarjeta Gigante del Marcador
                        st.markdown(f"""
                        <div style="background-color: #1E293B; border: 2px solid #3B82F6; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                            <h4 style="margin-top:0; color:#94A3B8;">🎯 MARCADOR EXACTO PROYECTADO</h4>
                            <h1 style="color:#FFFFFF; font-size: 3.5rem; margin: 10px 0; font-family: monospace;">{marcador_exacto}</h1>
                            <p style="margin:0; font-size: 0.9rem; color:#64748B;">Triangulación matemática de los 3 modelos predictivos</p>
                        </div>
                        """, unsafe_allow_html=True)
                        col_r1, col_r2, col_r3 = st.columns(3)
                        with col_r1:
                            st.markdown(f"""
                            <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; text-align: center;">
                                <h4 style="margin-top:0; color:#475569;">🏆 Ganador Proyectado</h4>
                                <h2 style="color:#0F172A; margin: 10px 0;">{ganador_str}</h2>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col_r2:
                            st.markdown(f"""
                            <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; text-align: center;">
                                <h4 style="margin-top:0; color:#475569;">⚽ Goles Totales (Al final)</h4>
                                <h2 style="color:#0EA5E9; margin: 10px 0;">{pred_goles:.1f} Goles</h2>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col_r3:
                            st.markdown(f"""
                            <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 15px; border-radius: 8px; text-align: center;">
                                <h4 style="margin-top:0; color:#475569;">🔥 ¿Ambos Anotan?</h4>
                                <h2 style="color:{color_btts}; margin: 10px 0;">{btts_str}</h2>
                            </div>
                            """, unsafe_allow_html=True)
                            
                    except Exception as e:
                        st.error(f"❌ Error al procesar la predicción: {str(e)}")