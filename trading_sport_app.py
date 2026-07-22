import streamlit as st
import pandas as pd
import numpy as np
import random
import string
import joblib
from supabase import create_client, Client
import joblib
import os
import pandas as pd
import streamlit as st



# --- CARGADOR DE LOS CEREBROS DE IA EN CACHÉ ---
@st.cache_resource
def cargar_oraculos():
    try:
        m_1x2 = joblib.load('modelo_pre_1x2.pkl')
        m_goles = joblib.load('modelo_pre_goles.pkl')
        m_btts = joblib.load('modelo_pre_btts.pkl')
        return m_1x2, m_goles, m_btts, True
    except:
        return None, None, None, False

@st.cache_data
def cargar_mega_base():
    archivos = ['closing_odds.csv.gz', 'closing_odds.zip', 'closing_odds.csv']
    for arch in archivos:
        if os.path.exists(arch):
            if arch.endswith('.gz'): return pd.read_csv(arch, compression='gzip')
            elif arch.endswith('.zip'): return pd.read_csv(arch, compression='zip')
            else: return pd.read_csv(arch)
    return None

modelo_1x2, modelo_goles, modelo_btts, modelos_cargados = cargar_oraculos()
df_global = cargar_mega_base()

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase: Client = init_connection()
# ---DEFINICION DE ESCENARIOS ---
def detectar_patron_btts_si(min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
                            jerarquia_pre, apm_global_fav, apm_global_deb, apm_global_ganador, apm_global_perdedor,
                            mom_reciente_loc, mom_reciente_vis, mom_combinado, diferencial_mom, 
                            mom_post_gol_fav, mom_post_gol_deb, mom_post_gol_ganador, mom_post_gol_perdedor,
                            tp_fav, tp_deb, tp_ganador, tp_perdedor):
    
    # ---------------------------------------------------------
    # 🐯 PATRÓN SÍ #1: EL TIGRE HERIDO
    # ---------------------------------------------------------
    if (min_corrido <= 45 and 
        estado_goles == True and 
        jerarquia_pre in ["Favorito", "Súper Favorito"] and 
        lider_marcador == "No Favorito" and 
        goles_deb == 1 and 
        mom_post_gol_fav > 1.0 and 
        mom_post_gol_deb < 0.4 and 
        diferencial_mom > 0.7 and
        # -- Bloque de Eficiencia (Filtro de Ruido) --
        tp_fav > 0.40):
        
        return "🟢 EL TIGRE HERIDO: Favorito pierde 0-1 pero asedia brutalmente (Mom > 1.0) y con profundidad (TP > 40%). LUZ VERDE SÍ."

    # ---------------------------------------------------------
    # 🔥 PATRÓN SÍ #2: LA REBELDÍA (Favorito Dormido)
    # ---------------------------------------------------------
    elif (min_corrido <= 45 and 
          estado_goles == True and 
          jerarquia_pre in ["Favorito", "Súper Favorito"] and 
          lider_marcador == "Favorito" and 
          goles_fav == 1 and 
          goles_deb == 0 and 
          apm_global_fav < 0.6 and 
          apm_global_deb > 0.8 and 
          mom_post_gol_fav < 0.4 and 
          mom_post_gol_deb > 0.8 and
          # -- Bloque de Eficiencia (Filtro de Ruido) --
          tp_deb > 0.40):
          
        return "🟢 LA REBELDÍA: Favorito gana 1-0 y se durmió. El Débil asedia con furia (Mom > 0.8) y verticalidad (TP > 40%). LUZ VERDE SÍ."

    # ---------------------------------------------------------
    # 🥊 PATRÓN SÍ #3: LA DEVOLUCIÓN RÁPIDA (Fuerzas Parejas)
    # ---------------------------------------------------------
    elif (min_corrido <= 45 and 
          estado_goles == True and 
          jerarquia_pre == "Fuerzas Parejas" and 
          (goles_ganador == 1 and goles_perdedor == 0) and 
          apm_global_ganador > 0.7 and 
          apm_global_perdedor > 0.8 and 
          mom_combinado >= 1.5 and 
          diferencial_mom < 0.2 and 
          mom_post_gol_perdedor > 0.9 and
          # -- Bloque de Eficiencia (Filtro de Ruido) --
          tp_ganador > 0.35 and 
          tp_perdedor > 0.35):
          
        return "🟢 DEVOLUCIÓN RÁPIDA: Partido parejo 1-0. Intercambio de golpes intenso y ambos llegan con peligro (TP > 35%). LUZ VERDE SÍ."

    # ---------------------------------------------------------
    # 🎭 PATRÓN SÍ #4: EL DESCUENTO POR RELAJACIÓN
    # ---------------------------------------------------------
    elif (min_corrido <= 45 and 
          estado_goles == True and 
          jerarquia_pre in ["Favorito", "Súper Favorito"] and 
          lider_marcador == "Favorito" and 
          goles_fav >= 2 and 
          goles_deb == 0 and 
          apm_global_fav < 0.6 and 
          apm_global_deb > 0.8 and 
          mom_post_gol_deb > 1.0 and
          # -- Bloque de Eficiencia (Filtro de Ruido) --
          tp_deb > 0.45):
          
        return "🟢 DESCUENTO POR RELAJACIÓN: Favorito golea 2-0 y bajó los brazos. El Débil ataca furioso y profundo (TP > 45%). LUZ VERDE SÍ."

    # Si no encaja en ninguno de los patrones dorados:
    else:
        return "⏳ MODO OBSERVACIÓN: El partido no encaja en los patrones perfectos para el Ambos Anotan SÍ."
# ---------------------------------------------------------
    # 🛡️ ESCÁNER DE PATRONES PARA EL BTTS NO (DEFINITIVO)
    # ---------------------------------------------------------
    def detectar_patron_btts_no(min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
                                jerarquia_pre, apm_global_fav, apm_global_deb, 
                                mom_fav, mom_deb, tp_fav, tp_deb):
        
        # 🧱 PATRÓN NO #1: EL MURO INFRANQUEABLE (El Débil no existe)
        if (min_corrido >= 30 and 
            jerarquia_pre in ["Favorito", "Súper Favorito"] and 
            goles_deb == 0 and 
            apm_global_deb < 0.35 and 
            mom_deb < 0.3 and 
            tp_deb < 0.20):
            
            return "🔴 EL MURO: El Débil está asfixiado. Sin momentum (Mom < 0.3) ni profundidad (TP < 20%). LUZ VERDE NO."

        # 💤 PATRÓN NO #2: PACTO DE NO AGRESIÓN (Fuerzas Parejas Bloqueadas)
        elif (min_corrido >= 30 and 
              jerarquia_pre == "Fuerzas Parejas" and 
              apm_global_fav < 0.55 and apm_global_deb < 0.55 and 
              mom_fav < 0.5 and mom_deb < 0.5 and 
              tp_fav < 0.30 and tp_deb < 0.30):
              
            return "🔴 PACTO DE NO AGRESIÓN: Ambos equipos anulados en el medio campo (APM < 0.55). Poca verticalidad. LUZ VERDE NO."

        # 🏥 PATRÓN NO #3: EL DOMINIO ESTÉRIL (Mucho ruido, cero peligro)
        elif (min_corrido >= 35 and 
              estado_goles == False and 
              tp_fav < 0.25 and tp_deb < 0.25):
              
            return "🔴 DOMINIO ESTÉRIL: 0-0 con posesiones largas pero bajísima profundidad en ambos (TP < 25%). LUZ VERDE NO."

        else:
            return "⏳ MODO OBSERVACIÓN: No hay asfixia clara ni bloqueo total. Es riesgoso entrar al NO definitivo aquí."

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
            if estado == "RADAR": continue # <--- NUEVO: Ignora los partidos en seguimiento
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
# El Ancla Contable: Usamos directamente la sumatoria física de las casas de apuestas
df_cajas_reales = obtener_saldos_por_plataforma("REAL")
if not df_cajas_reales.empty:
    saldo_real = df_cajas_reales['Saldo Actual (COP)'].sum()
else:
    saldo_real = obtener_saldo_banca("REAL")

df_cajas_simuladas = obtener_saldos_por_plataforma("SIMULACION")
if not df_cajas_simuladas.empty:
    saldo_simulacion = df_cajas_simuladas['Saldo Actual (COP)'].sum()
else:
    saldo_simulacion = obtener_saldo_banca("SIMULACION")
    # --- CÁLCULO DEL TOPE MÁXIMO POR EVENTO (El 5% de la caja) ---
    tope_maximo_evento = max(0.0, saldo_real * 0.05)

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

st.title("⚖️ Trading Sport Asistido con IA")

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
                monto = st.number_input("Monto a Consignar (COP):", min_value=100, step=100, value=10000, format="%.0f")
                
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
                monto = st.number_input("Monto a Retirar (COP):", min_value=1.0, step=100.0, value=1.0, format="%.2f")
                
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
                monto = st.number_input("Monto a Consignar (COP):", min_value=100, step=100, value=10000)
                
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
                monto = st.number_input("Monto a Retirar (COP):", min_value=1.0, step=100.0, value=1.0)
            
                
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
        capital_total = st.number_input("Inversión Total (Stake COP)", min_value=500, value=min(20000, int(saldo_disponible)) if saldo_disponible > 500 else 500, step=500)
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
        capital_total = st.number_input("Capital Total (COP)", min_value=500, value=min(5000, int(saldo_disponible)) if saldo_disponible > 10000 else 10000, step=5000)
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
        plat_1 = st.selectbox(f"🏦 Plataforma para {str_selec_1 if usar_dutching else str_dc}:", ["1xBet", "BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Otra"], key="plat1")
        if plat_1 == "Otra": plat_1 = st.text_input("Especifica plataforma 1:", key="otra1")
    
    with col_p2:
        if usar_dutching:
            plat_2 = st.selectbox(f"🏦 Plataforma para {str_selec_2}:", ["1xBet", "BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Otra"], key="plat2")
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
    
    capital_inicial = st.number_input("Capital Inicial a Invertir (Stake 1)", min_value=500, value=min(2000, int(saldo_disponible)) if saldo_disponible > 5000 else 10000, step=5000)

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

## =====================================================================
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
                # =====================================================================
                if nombre_estrategia in ["Estrategia 1: eSports Scalping", "Estrategia 3: Binario Personalizado"]:
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
                                key=f"acc_es_{op['codigo']}", horizontal=True
                            )
                            
                            if accion_esports == "📸 Evaluar Asedio y Cazar Cuota":
                                # ------------------------------------------------------------------
                                # 🔄 BOTÓN DE SINCRONIZACIÓN Y LECTURA DE FOTOS 
                                # ------------------------------------------------------------------
                                col_tit1, col_tit2 = st.columns([2, 1])
                                with col_tit1:
                                    st.markdown("#### ⏱️ Auditoría Táctica y Financiera")
                                with col_tit2:
                                    if st.button("🔄 Sincronizar Info", key=f"btn_sync_seg_{op['codigo']}"):
                                        try:
                                            codigo_base = "-".join(str(op['codigo']).split('-')[:2])
                                            res_sync = supabase.table("registro_fotos").select("*").like("codigo_posicion", f"{codigo_base}%").order("minuto_evaluado", desc=True).limit(1).execute()
                                            
                                            if res_sync.data:
                                                foto_reciente = res_sync.data[0]
                                                # AQUÍ ESTÁ LA CORRECCIÓN: Las llaves ahora tienen el '_in_' para que hagan match perfecto con las cajas de texto
                                                st.session_state[f"min_es_in_{op['codigo']}"] = int(foto_reciente['minuto_evaluado'])
                                                st.session_state[f"g_l_es_in_{op['codigo']}"] = int(foto_reciente['goles_local'])
                                                st.session_state[f"g_v_es_in_{op['codigo']}"] = int(foto_reciente['goles_vis'])
                                                st.session_state[f"atqt_l_es_in_{op['codigo']}"] = int(foto_reciente.get('atqt_local', 0))
                                                st.session_state[f"atqt_v_es_in_{op['codigo']}"] = int(foto_reciente.get('atqt_vis', 0))
                                                st.session_state[f"atk_l_es_in_{op['codigo']}"] = int(foto_reciente['atkp_local'])
                                                st.session_state[f"atk_v_es_in_{op['codigo']}"] = int(foto_reciente['atkp_vis'])
                                                
                                                if foto_reciente.get('cuota_si') and float(foto_reciente['cuota_si']) > 1.01:
                                                    st.session_state[f"c_live_es_in_{op['codigo']}"] = float(foto_reciente['cuota_si'])
                                                    
                                                st.success(f"✅ ¡Datos del min {foto_reciente['minuto_evaluado']} importados!")
                                                st.rerun()  # 👈 RECARGA LA PANTALLA
                                            else:
                                                st.warning("⚠️ No hay fotos previas de este partido.")
                                        except Exception as e:
                                            st.error(f"Error sincronizando: {e}")
                                            
                                # NOMBRES DE EQUIPOS
                                partido_str = str(op.get('partido', ''))
                                solo_partido = partido_str.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str else partido_str
                                txt_norm = solo_partido.lower().replace("vs.", "vs").replace("-", "vs")
                                if "vs" in txt_norm:
                                    eq_local = txt_norm.split("vs")[0].strip().title()
                                    eq_vis = txt_norm.split("vs")[1].strip().title()
                                else:
                                    eq_local = solo_partido if len(solo_partido) > 1 else "Equipo Local"
                                    eq_vis = "Equipo Visitante"
                                    
                                if "Ambos Anotan" in eq_local or "[" in eq_local: 
                                    eq_local, eq_vis = "Opción A", "Opción B"

                                # INPUTS DE DATOS FINANCIEROS Y TÁCTICOS
                                c_top1, c_top2, c_top3 = st.columns(3)
                                with c_top1:
                                    minuto_actual = st.number_input("⏱️ Minuto:", min_value=0, max_value=120, step=1, key=f"min_es_in_{op['codigo']}")
                                with c_top2:
                                    cuota_input_es = st.number_input("📉 Cuota Cobertura:", min_value=1.01, step=0.01, key=f"c_live_es_in_{op['codigo']}")
                                    cuota_salida = cuota_input_es if cuota_input_es is not None else 1.01
                                with c_top3:
                                    oferta_cashout = st.number_input("💰 Oferta Cashout ($):", min_value=0.0, step=1000.0, value=0.0, key=f"cash_es_{op['codigo']}")

                                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                                st.markdown("<p style='font-size: 13px; color: #64748B; margin-bottom: 5px;'>Estadísticas Actualizadas en Cancha:</p>", unsafe_allow_html=True)
                                
                                col_t1, col_t2 = st.columns(2)
                                with col_t1:
                                    g_local = st.number_input(f"⚽ Goles de {eq_local}", min_value=0, key=f"g_l_es_in_{op['codigo']}")
                                    atqt_local = st.number_input(f"📊 Atq. Tot. de {eq_local}", min_value=0, key=f"atqt_l_es_in_{op['codigo']}")
                                    atkp_local = st.number_input(f"🔥 Peligro {eq_local}", min_value=0, key=f"atk_l_es_in_{op['codigo']}")
                                with col_t2:
                                    g_vis = st.number_input(f"⚽ Goles de {eq_vis}", min_value=0, key=f"g_v_es_in_{op['codigo']}")
                                    atqt_vis = st.number_input(f"📊 Atq. Tot. de {eq_vis}", min_value=0, key=f"atqt_v_es_in_{op['codigo']}")
                                    atkp_vis = st.number_input(f"🔥 Peligro {eq_vis}", min_value=0, key=f"atk_v_es_in_{op['codigo']}")
                                
                                st.markdown("---")

                                # ====================================================================
                                # ⚡ MOTOR DE MOMENTUM (EXTRAE Y GUARDA AL INSTANTE)
                                # ====================================================================
                                st.markdown("#### ⚡ Motor de Momentum (Aceleración Real)")
                                if st.button("📸 Extraer Ancestro, Calcular y Guardar Foto Actual", key=f"btn_mom_{op['codigo']}", use_container_width=True, type="primary"):
                                    try:
                                        codigo_base = "-".join(str(op['codigo']).split('-')[:2])
                                        res_mom = supabase.table("registro_fotos").select("*").like("codigo_posicion", f"{codigo_base}%").lt("minuto_evaluado", minuto_actual).order("minuto_evaluado", desc=True).limit(1).execute()
                                        
                                        if res_mom.data:
                                            foto_ant = res_mom.data[0]
                                            min_ant = int(foto_ant['minuto_evaluado'])
                                            delta_min = int(minuto_actual) - min_ant
                                            if delta_min >= 2:
                                                atk_l_ant = int(foto_ant['atkp_local'])
                                                atk_v_ant = int(foto_ant['atkp_vis'])
                                                st.session_state[f"apm_l_din_{op['codigo']}"] = max(0.0, (float(atkp_local) - atk_l_ant) / delta_min)
                                                st.session_state[f"apm_v_din_{op['codigo']}"] = max(0.0, (float(atkp_vis) - atk_v_ant) / delta_min)
                                                st.session_state[f"mom_txt_{op['codigo']}"] = f"Últimos {delta_min} min (Desde el {min_ant}')"
                                            else:
                                                st.warning(f"⚠️ La última foto es del min {min_ant}. Deben pasar al menos 2 minutos para medir aceleración.")
                                        else:
                                            st.warning("⚠️ No hay fotos anteriores. Esta se guardará como la base.")

                                        nueva_foto = {
                                            "codigo_posicion": str(op['codigo']),
                                            "minuto_evaluado": int(minuto_actual),
                                            "goles_local": int(g_local),
                                            "goles_vis": int(g_vis),
                                            "atqt_local": int(atqt_local),
                                            "atqt_vis": int(atqt_vis),
                                            "atkp_local": int(atkp_local),
                                            "atkp_vis": int(atkp_vis),
                                            "cuota_si": float(cuota_salida),
                                            "cuota_no": float(op.get('cuota_inicial', 2.0))
                                        }
                                        res_insert = supabase.table("registro_fotos").insert(nueva_foto).execute()
                                        if res_insert.data:
                                            st.success(f"✅ ¡Foto del min {minuto_actual} anclada a la BD con éxito!")
                                            import time
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ Supabase no devolvió confirmación.")
                                    except Exception as e:
                                        st.error(f"❌ Error al guardar la foto táctica: {str(e)}")

                                # =====================================================================
                                # IA Y LECTURA DE MERCADO (LÓGICA LIMPIA)
                                # =====================================================================
                                apm_global_loc = atkp_local / max(1, minuto_actual) if minuto_actual > 0 else 0
                                apm_global_vis = atkp_vis / max(1, minuto_actual) if minuto_actual > 0 else 0
                                
                                if f"apm_l_din_{op['codigo']}" in st.session_state:
                                    apm_local = st.session_state[f"apm_l_din_{op['codigo']}"]
                                    apm_vis = st.session_state[f"apm_v_din_{op['codigo']}"]
                                    texto_momentum = st.session_state[f"mom_txt_{op['codigo']}"]
                                else:
                                    apm_local = apm_global_loc
                                    apm_vis = apm_global_vis
                                    texto_momentum = "Promedio Global"

                                apm_total = apm_local + apm_vis
                                tiempo_restante = max(0, 90 - minuto_actual)
                                goles_totales = g_local + g_vis
                                ird = min(100.0, ((atkp_local + atkp_vis) / max(1, minuto_actual)) * 45.0)

                                texto_mercado = str(op.get('partido', ''))
                                is_ambos_anotan = "Ambos Anotan" in texto_mercado
                                is_linea_goles = "Línea de Goles" in texto_mercado
                                
                                c_loc_hist = float(op.get('cuota_base_audit', 2.0))
                                c_vis_hist = float(op.get('cuota_amenaza_audit', 2.0))
                                if c_loc_hist <= 1.35: jerarquia = f"👑 Súper Favorito: {eq_local}"
                                elif c_vis_hist <= 1.35: jerarquia = f"👑 Súper Favorito: {eq_vis}"
                                elif c_loc_hist < c_vis_hist and (c_vis_hist - c_loc_hist) > 0.3: jerarquia = f"⚔️ Favorito: {eq_local}"
                                elif c_vis_hist < c_loc_hist and (c_loc_hist - c_vis_hist) > 0.3: jerarquia = f"⚔️ Favorito: {eq_vis}"
                                else: jerarquia = "⚖️ Fuerzas Parejas"

                                is_super_fav_local = "Súper Favorito" in jerarquia and eq_local in jerarquia
                                is_super_fav_vis = "Súper Favorito" in jerarquia and eq_vis in jerarquia
                                is_fav_local = "Favorito" in jerarquia and eq_local in jerarquia and not is_super_fav_local
                                is_fav_vis = "Favorito" in jerarquia and eq_vis in jerarquia and not is_super_fav_vis

                                st.markdown(f"""
                                <div style="background-color: #1E293B; border-bottom: 4px solid #3B82F6; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; margin-bottom: 15px;">
                                    <h4 style="margin:0; color:#94A3B8; font-size: 0.9rem;">ADN DEL PARTIDO (Histórico)</h4>
                                    <h3 style="color:#FFFFFF; margin: 5px 0;">[{jerarquia}]</h3>
                                </div>
                                """, unsafe_allow_html=True)

                                # ------------------------------------------------------------------
                                # BIFURCACIÓN DE MERCADO
                                # ------------------------------------------------------------------
                                if is_ambos_anotan:
                                    sel_lower_btts = sel_ini.lower()
                                    palabras_btts = sel_lower_btts.replace(":", " ").replace("-", " ").replace("(", "").replace(")", "").split()
                                    aposto_si = "sí" in palabras_btts or "si" in palabras_btts or "yes" in palabras_btts or ("ambos" in sel_lower_btts and ("sí" in sel_lower_btts or "si" in palabras_btts))
                                    
                                    diferencia_goles_btts = abs(g_local - g_vis)
                                    estado_btts = "⏳ EVALUANDO..."
                                    color_btts = "#64748B"
                                    msj_ia = ""

                                    if aposto_si:
                                        if g_local > 0 and g_vis > 0:
                                            msj_ia = "🎉 **¡OBJETIVO CUMPLIDO!** Ambos marcaron. Ganaste el SÍ. Liquida ya."
                                            ird = 0.0; estado_btts = "✅ GARANTIZADO"; color_btts = "#10B981"
                                        elif goles_totales == 0 and minuto_actual >= 60:
                                            msj_ia = f"⏳ **TIC-TAC MORTAL:** Minuto {minuto_actual} y van 0-0. Pedir 2 goles ahora es un milagro."
                                            estado_btts = "COLAPSO DE TIEMPO"; color_btts = "#EF4444"; ird = 95.0
                                        elif diferencia_goles_btts >= 2:
                                            msj_ia = f"🏔️ **MONTAÑA INALCANZABLE:** Diferencia de {diferencia_goles_btts} goles. El SÍ agoniza."
                                            estado_btts = "MILAGRO REQUERIDO"; color_btts = "#EF4444"; ird = 90.0
                                        else:
                                            if minuto_actual <= 45:
                                                if goles_totales == 0:
                                                    msj_ia = "🟡 **CALIBRACIÓN TÁCTICA:** El SÍ tiene tiempo. Vigila el APM."
                                                    estado_btts = "FASE DE ESTUDIO"; color_btts = "#F59E0B"; ird = 30.0
                                                else:
                                                    msj_ia = "🔥 **EL MARCADOR SE ABRIÓ:** Un gol temprano, excelente escenario para el SÍ."
                                                    estado_btts = "GOL A FAVOR"; color_btts = "#10B981"; ird = 35.0
                                            elif minuto_actual <= 75:
                                                if goles_totales == 0:
                                                    msj_ia = "🔴 **ESTANCAMIENTO CRÍTICO:** Partido en un pozo. Sin goles, SÍ liquidado."
                                                    estado_btts = "AGOTAMIENTO"; color_btts = "#EF4444"; ird = 95.0
                                                else:
                                                    msj_ia = "🟡 **OLLA A PRESIÓN:** Asedio constante. El gol puede caer."
                                                    estado_btts = "GOL INMINENTE"; color_btts = "#F59E0B"; ird = 60.0
                                            else:
                                                msj_ia = "💀 **MUERTE POR RELOJ:** Se acabó el tiempo."
                                                estado_btts = "TIEMPO AGOTADO"; color_btts = "#EF4444"; ird = 100.0
                                    else:
                                        if g_local > 0 and g_vis > 0:
                                            msj_ia = "❌ **SINIESTRO:** Ambos marcaron. Perdiste el NO."
                                            ird = 100.0; estado_btts = "💀 PERDIDO"; color_btts = "#EF4444"
                                        elif goles_totales == 0 and minuto_actual >= 60:
                                            msj_ia = f"✅ **CERO ABSOLUTO:** Minuto {minuto_actual} y van 0-0. Tu NO es casi invencible."
                                            estado_btts = "BLINDAJE DE TIEMPO"; color_btts = "#10B981"; ird = 5.0
                                        elif diferencia_goles_btts >= 2:
                                            msj_ia = f"🛡️ **CANDADO DE PLOMO:** Ventaja de {diferencia_goles_btts}. El ganador hará control total."
                                            estado_btts = "CONTROL TOTAL"; color_btts = "#10B981"; ird = 10.0
                                        else:
                                            if minuto_actual <= 45:
                                                msj_ia = "🟢 **TENDENCIA SEGURA:** Partido controlado, buen inicio para el NO."
                                                estado_btts = "PACIENCIA"; color_btts = "#10B981"; ird = 20.0
                                            else:
                                                msj_ia = "🟡 **ASALTO FINAL:** Riesgo de que el perdedor descuente. Vigila."
                                                estado_btts = "PRESIÓN"; color_btts = "#F59E0B"; ird = 60.0

                                    st.markdown(f"""
                                    <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                                        <h3 style="margin-top:0; color:#0F172A;">📊 ESTADO DEL BTTS (Ambos Anotan)</h3>
                                        <h1 style="color:{color_btts}; font-size: 2.5rem; margin: 10px 0;">{estado_btts}</h1>
                                        <p style="margin:0; font-size: 1.1rem; color:#475569;">{msj_ia}</p>
                                        <p style="margin:10px 0 0 0; font-size: 0.85rem; color:#64748B;">Dinámica actual: {apm_total:.2f} APM ({texto_momentum})</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                elif is_linea_goles:
                                    import re
                                    match_linea = re.search(r'\d+\.\d+|\d+', sel_ini)
                                    linea_obj = float(match_linea.group()) if match_linea else 2.5
                                    aposto_mas = "Más" in sel_ini or "Mas" in sel_ini
                                    diferencia_goles = linea_obj - goles_totales
                                    
                                    if aposto_mas:
                                        if diferencia_goles < 0:
                                            msj_ia = f"🎉 **¡OBJETIVO CUMPLIDO!** Ya superaste la línea."
                                            ird = 0.0; estado_goles = "✅ GARANTIZADO"; color_goles = "#10B981"
                                        else:
                                            msj_ia = f"🚨 **FALTAN GOLES:** Necesitas acción rápida."
                                            ird = 80.0; estado_goles = "🔴 BUSCANDO GOLES"; color_goles = "#EF4444"
                                    else:
                                        if diferencia_goles < 0:
                                            msj_ia = f"❌ **SINIESTRO:** Superaron la línea. Perdiste."
                                            ird = 100.0; estado_goles = "💀 PERDIDO"; color_goles = "#000000"
                                        else:
                                            msj_ia = f"✅ **CONTROL:** La línea de under resiste."
                                            ird = 20.0; estado_goles = "🟢 SEGURO"; color_goles = "#10B981"

                                    st.markdown(f"""
                                    <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                                        <h3 style="margin-top:0; color:#0F172A;">📊 ESTADO LÍNEA DE GOLES ({linea_obj})</h3>
                                        <h1 style="color:{color_goles}; font-size: 2.5rem; margin: 10px 0;">{estado_goles}</h1>
                                        <p style="margin:0; font-size: 1.1rem; color:#475569;">{msj_ia}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                else:
                                    dom_vivo = "Local" if apm_local > apm_vis and (atkp_local - atkp_vis) > 10 else ("Visita" if apm_vis > apm_local and (atkp_vis - atkp_local) > 10 else "Asedio Dividido")
                                    color_1x2 = "#10B981" if ((dom_vivo == "Local" and "Local" in sel_ini) or (dom_vivo == "Visita" and "Visita" in sel_ini)) else "#EF4444"
                                    
                                    st.markdown(f"""
                                    <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                                        <h3 style="margin-top:0; color:#0F172A;">🎯 TÁCTICA 1X2</h3>
                                        <h1 style="color:{color_1x2}; font-size: 2.5rem; margin: 10px 0;">DOMINA: {dom_vivo.upper()}</h1>
                                    </div>
                                    """, unsafe_allow_html=True)

                                # =====================================================================
                                # 🛡️ MATRIZ FINANCIERA (OPCIONES A, B Y CASHOUT)
                                # =====================================================================
                                st.markdown("#### 🔍 Matriz Financiera de la Operación")
                                
                                st1 = op['stake_1']
                                c_ini = op['cuota_inicial']
                                ret_bruto = st1 * c_ini
                                
                                # OPCIÓN A (Seguro Total)
                                monto_inyectar_a = ret_bruto / cuota_salida if cuota_salida > 0 else 0
                                util_si_gana_a = ret_bruto - st1 - monto_inyectar_a
                                
                                # OPCIÓN B (Dejar Correr)
                                util_si_gana_b = ret_bruto - st1
                                util_si_pierde_b = -st1
                                
                                # CASHOUT
                                utilidad_cashout = oferta_cashout - st1
                                diferencia_cashout = util_si_gana_a - utilidad_cashout 
                                
                                col_sc1, col_sc2 = st.columns(2)
                                with col_sc1:
                                    st.markdown(f"""
                                    <div style="background-color: #F8FAFC; padding: 15px; border-radius: 6px; border: 1px solid #CBD5E1; height: 100%;">
                                        <b style="color: #1E293B; font-size: 0.9rem;">OPCIÓN A: Seguro Matemático</b><br>
                                        • Pagar Seguro a Cuota {cuota_salida:.2f}: <b>${monto_inyectar_a:,.0f}</b><br>
                                        • Ganancia Garantizada: <span style="color:{'#10B981' if util_si_gana_a >= 0 else '#EF4444'}; font-weight:bold;">${util_si_gana_a:,.0f}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                with col_sc2:
                                    st.markdown(f"""
                                    <div style="background-color: #FFFBEB; padding: 15px; border-radius: 6px; border: 1px solid #FDE68A; height: 100%;">
                                        <b style="color: #78350F; font-size: 0.9rem;">OPCIÓN B: Modo Suicida (Dejar Correr)</b><br>
                                        • Ganancia si Acertamos: <span style="color:#10B981; font-weight:bold;">${util_si_gana_b:,.0f}</span><br>
                                        • Pérdida si Fallamos: <span style="color:#EF4444; font-weight:bold;">${util_si_pierde_b:,.0f}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                                
                                # LIQUIDACIÓN 
                                es_mejor_cashout = False
                                if oferta_cashout > 0 and diferencia_cashout < 0:
                                    es_mejor_cashout = True
                                    st.markdown(f"""
                                    <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px; border-radius: 4px; margin-bottom: 15px;">
                                        <span style="font-size: 1.05em; color: #991B1B;">🚨 <b>¡CASHOUT DETECTADO COMO LA MEJOR OPCIÓN!</b></span><br>
                                        <span style="font-size: 0.95em; color: #B91C1C;">El botón de la casa es más generoso que la cobertura manual. ¡Tómalo ya!</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                if es_mejor_cashout:
                                    if st.button("✅ LIQUIDAR POR CASHOUT", key=f"btn_cash_{op['codigo']}", use_container_width=True):
                                        hora_actual = datetime.datetime.now().strftime("%H:%M")
                                        supabase.table("historial_trading").update({
                                            "estado": "CERRADA",
                                            "resultado_final": "Cashout (Cierre Anticipado)",
                                            "utilidad_neta_real": float(utilidad_cashout),
                                            "roi_real": float((utilidad_cashout / op['stake_1']) * 100),
                                            "hora_cobertura": hora_actual,
                                            "plataforma_cobertura": "Misma (Cashout)"
                                        }).eq("codigo", op['codigo']).execute()
                                        st.success(f"¡Cashout registrado! Has cerrado la operación con balance de ${utilidad_cashout:,.0f}.")
                                        st.rerun()
                                else:
                                    todas_las_plataformas = ["1xBet", "BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Yajuego", "Zamba", "Rivalo", "MegApuesta", "Sportium", "Stake", "Otra"]
                                    plataforma_cob_sel = st.selectbox("Plataforma donde cazaste la cobertura:", todas_las_plataformas, key=f"plat_es_{op['codigo']}")
                                    plataforma_cob = st.text_input("Especifica la plataforma:", key=f"otra_plat_es_{op['codigo']}") if plataforma_cob_sel == "Otra" else plataforma_cob_sel
                                    
                                    if st.button("⚡ REGISTRAR SEGURO TOTAL (CERRAR POSICIÓN)", key=f"btn_cob_a_{op['codigo']}", use_container_width=True):
                                        hora_actual = datetime.datetime.now().strftime("%H:%M")
                                        supabase.table("historial_trading").update({
                                            "estado": "CUBIERTA",
                                            "cuota_cazada_real": float(cuota_salida),
                                            "hora_cobertura": hora_actual,
                                            "plataforma_cobertura": plataforma_cob,
                                            "reserva_stake_2": float(monto_inyectar_a) 
                                        }).eq("codigo", op['codigo']).execute()
                                        st.success(f"¡Cobertura TOTAL fijada a cuota {cuota_salida}! Pasa a liquidación.")
                                        st.rerun()
                            else:
                                # LIQUIDACIÓN DIRECTA FASE 1
                                with st.form(f"get_dir_es_{op['codigo']}"):
                                    st.markdown("#### 🏁 Conciliación Directa (Sin Cobertura)")
                                    resultado_directo = st.radio(
                                        "Resolución de tu Apuesta:", 
                                        [f"✅ Ganó {sel_ini} (Cobro completo)", f"❌ Perdió {sel_ini} (Pérdida Stake 1)"],
                                        key=f"rad_dir_es_{op['codigo']}"
                                    )
                                    st.markdown("---")
                                    
                                    # --- EXTRACTOR DE NOMBRES DE EQUIPOS (Corrección del NameError) ---
                                    partido_str = str(op.get('partido', ''))
                                    solo_partido = partido_str.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str else partido_str
                                    txt_norm = solo_partido.lower().replace("vs.", "vs").replace("-", "vs")
                                    if "vs" in txt_norm:
                                        eq_local = txt_norm.split("vs")[0].strip().title()
                                        eq_vis = txt_norm.split("vs")[1].strip().title()
                                    else:
                                        eq_local = solo_partido if len(solo_partido) > 1 else "Equipo Local"
                                        eq_vis = "Equipo Visitante"
                                        
                                    if "Ambos Anotan" in eq_local or "[" in eq_local: 
                                        eq_local, eq_vis = "Opción A", "Opción B"
                                    # ------------------------------------------------------------------

                                    goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_dir_es_{op['codigo']}")
                                    goles_finales_rival = st.number_input(f"🚀 Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_dir_es_{op['codigo']}")
                                    
                                    if st.form_submit_button("Registrar Liquidación Directa"):
                                        utilidad = utilidad_original_maxima if "Ganó" in resultado_directo else -op['stake_1']
                                        texto_cierre = f"Cierre Directo: Ganó Inicial" if "Ganó" in resultado_directo else f"Cierre Directo: Perdió Inicial"
                                            
                                        supabase.table("historial_trading").update({
                                            "estado": "CERRADA",
                                            "resultado_final": texto_cierre,
                                            "utilidad_neta_real": float(utilidad),
                                            "roi_real": float((utilidad / op['capital_total']) * 100),
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
                                    [f"✅ Inicial Acertado: Ganó {sel_ini}", f"🛡️ Seguro Acertado: Ganó {sel_cob}", "❌ Déficit Total (Siniestro)"],
                                    key=f"rad_fin_es_{op['codigo']}"
                                )
                                st.markdown("---")
                                goles_finales_seleccion = st.number_input(f"⚽ Goles Equipo A:", min_value=0, step=1, value=0, key=f"gf_sel_es_{op['codigo']}")
                                goles_finales_rival = st.number_input(f"⚽ Goles Equipo B:", min_value=0, step=1, value=0, key=f"gf_riv_es_{op['codigo']}")
                                
                                if st.form_submit_button(f"🏁 Cerrar Libro Mayor"):
                                    retorno_bruto_esperado = op['stake_1'] * op['cuota_inicial']
                                    monto_cobertura = float(op.get('reserva_stake_2', 0))
                                    total_capital = op['stake_1'] + monto_cobertura
                                    
                                    if "Déficit" in resultado_final_ui:
                                        utilidad = -total_capital
                                        texto_db = f"Pérdida Total del Capital"
                                    else:
                                        if "Inicial" in resultado_final_ui:
                                            utilidad = retorno_bruto_esperado - total_capital
                                            texto_db = "Cobro de Apuesta Inicial"
                                        else:
                                            retorno_seguro = monto_cobertura * float(op.get('cuota_cazada_real', 1.01))
                                            utilidad = retorno_seguro - total_capital
                                            texto_db = "Cobro de Fondo de Cobertura"
                                        
                                    supabase.table("historial_trading").update({
                                        "estado": "CERRADA",
                                        "resultado_final": texto_db,
                                        "utilidad_neta_real": float(utilidad),
                                        "roi_real": float((utilidad / op['capital_total']) * 100),
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
                                # --- INICIO BOTÓN DE SINCRONIZACIÓN ---
                                    col_tit1, col_tit2 = st.columns([2, 1])
                                    with col_tit1:
                                        st.markdown("#### ⏱️ Auditoría Táctica por Ritmo de Juego")
                                    with col_tit2:
                                        if st.button("🔄 Sincronizar Info", key=f"btn_sync_ft_{op['codigo']}"):
                                            try:
                                                codigo_base = "-".join(str(op['codigo']).split('-')[:2])
                                                res_sync = supabase.table("registro_fotos").select("*").like("codigo_posicion", f"{codigo_base}%").order("minuto_evaluado", desc=True).limit(1).execute()
                                                if res_sync.data:
                                                    foto_reciente = res_sync.data[0]
                                                    st.session_state[f"min_{op['codigo']}"] = int(foto_reciente['minuto_evaluado'])
                                                    st.session_state[f"g_l_{op['codigo']}"] = int(foto_reciente['goles_local'])
                                                    st.session_state[f"g_v_{op['codigo']}"] = int(foto_reciente['goles_vis'])
                                                    st.session_state[f"atk_l_{op['codigo']}"] = int(foto_reciente['atkp_local'])
                                                    st.session_state[f"atk_v_{op['codigo']}"] = int(foto_reciente['atkp_vis'])
                                                    if foto_reciente.get('cuota_si') and float(foto_reciente['cuota_si']) > 1.01:
                                                        st.session_state[f"cuota_live_{op['codigo']}"] = float(foto_reciente['cuota_si'])
                                                    st.success(f"✅ ¡Datos del min {foto_reciente['minuto_evaluado']} importados!")
                                                    st.rerun()
                                                else:
                                                    st.warning("⚠️ No hay fotos previas de este partido.")
                                            except Exception as e:
                                                st.error(f"Error sincronizando: {e}")
                                    # --- FIN BOTÓN DE SINCRONIZACIÓN ---    
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

                                    tiempo_restante = max(0, 95 - minuto_actual)
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
                                        
                                    st.progress(int(ird) / 100)
                                    st.markdown(f"<h5 style='text-align: center; color: {color};'>Nivel de Amenaza IRD: {ird:.1f}% | {estado}</h5>", unsafe_allow_html=True)
                                    
                                    val_cuota_obj = float(op.get('cuota_objetivo') or 1.01)
                                    if val_cuota_obj < 1.01:
                                        val_cuota_obj = 1.01

                                    cuota_input_ft = st.number_input("Tasa de cobertura fijada (Cuota en Vivo Actual):", min_value=1.01, step=0.01, value=val_cuota_obj, key=f"cuota_live_{op['codigo']}")
                                    cuota_ingresada = cuota_input_ft if cuota_input_ft is not None else 1.01
                                    
                                    oferta_cashout_ft = st.number_input("💰 Oferta Cashout ($):", min_value=0.0, step=1000.0, value=0.0, key=f"cash_ft_{op['codigo']}")
                                    
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
                                            st.success(f"✅ Registro de auditoría completado para el min {minuto_actual}.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error al guardar en Supabase: {str(e)}")
                                            
                                    st.markdown("---")
                                    
                                    todas_las_plataformas = ["1xBet", "BetPlay", "Wplay", "Rushbet", "Bwin", "Codere", "Yajuego", "Zamba", "Rivalo", "MegApuesta", "Sportium", "Stake", "Otra"]
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

                                    # =====================================================================
                                    # 4. ORÁCULO TRI-FACTOR (IA + HISTORIA + RIESGO PATRIMONIAL)
                                    # =====================================================================
                                    import joblib
                                    import pandas as pd
                                    
                                    # A. CEREBRO FÍSICO (IA)
                                    try:
                                        X_liq = pd.DataFrame([{'minuto_evaluado': minuto_actual, 'goles_local': g_local, 'goles_vis': g_vis, 'atkp_local': atkp_local, 'atkp_vis': atkp_vis, 'ird_calculado': ird, 'cuota_base_audit': float(op.get('cuota_base_audit', 2.0)), 'cuota_amenaza_audit': float(op.get('cuota_amenaza_audit', 2.0))}])
                                        m1x2_liq = joblib.load('modelo_1x2.pkl')
                                        pred_1x2 = m1x2_liq.predict(X_liq)[0]
                                        dom_vivo = "Local" if pred_1x2 == 2 else ("Visita" if pred_1x2 == 3 else "Empate/Asedio Dividido")
                                    except:
                                        dom_vivo = "Local" if apm_nuestros > apm_rival and (atkp_nuestros - atkp_rival) > 10 else ("Visita" if apm_rival > apm_nuestros and (atkp_rival - atkp_nuestros) > 10 else "Empate/Asedio Dividido")

                                    # B. CEREBRO HISTÓRICO (Vinculado a los Nombres y Oráculo Inicial)
                                    c_loc_hist_final = float(op.get('cuota_base_audit', 2.0))
                                    c_vis_hist_final = float(op.get('cuota_amenaza_audit', 2.0))
                                    
                                    if c_loc_hist_final < c_vis_hist_final and (c_vis_hist_final - c_loc_hist_final) > 0.3: fav_global = eq_local_seg
                                    elif c_vis_hist_final < c_loc_hist_final and (c_loc_hist_final - c_vis_hist_final) > 0.3: fav_global = eq_vis_seg
                                    else: fav_global = "Fuerzas Parejas"

                                    # C. CEREBRO PATRIMONIAL (Cálculos de Riesgo)
                                    saldo_banca_actual = obtener_saldo_banca(tipo_banca_operacion)
                                    umbral_permitido = max_riesgo_real if banca_op == 'REAL' else max_riesgo_simulacion
                                    pct_rescate_banca = (oferta_cashout_ft / saldo_banca_actual) * 100 if saldo_banca_actual > 0 and oferta_cashout_ft > 0 else 0
                                    exposicion_pct = (cap_total_seguro / saldo_banca_actual) * 100 if saldo_banca_actual > 0 else 0
                                    
                                    # D. ¿VAMOS GANANDO O PERDIENDO? (La clave del tiempo)
                                    ganando_actualmente = True if diferencia_goles > 0 else False
                                    
                                    dictamen_html = ""
                                    
                                    # === JERARQUÍA ESTRICTA DE REGLAS DE ORO ===
                                    
                                    # 1. QUEMAR LA CUENTA (Violación de Gestión de Riesgo)
                                    if exposicion_pct > umbral_permitido and not ganando_actualmente:
                                        dictamen_html = f"""
                                        <div style='background-color: #FEF2F2; border-left: 6px solid #991B1B; padding: 15px; margin-top: 15px; border-radius: 4px; color: #7F1D1D;'>
                                            <h5 style='margin-top:0; color:#991B1B;'>🔥 QUEMA DE CUENTA INMINENTE (Exposición Crítica)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>Has comprometido el <b>{exposicion_pct:.1f}%</b> de tu capital real, superando tu umbral máximo del <b>{umbral_permitido:.1f}%</b>. No estás ganando. ¡LIQUIDA O INYECTA COBERTURA AHORA MISMO para proteger el patrimonio!</p>
                                        </div>
                                        """
                                    # 2. STOP LOSS (Precio)
                                    elif cuota_sl > 0.0 and cuota_ingresada <= cuota_sl:
                                        dictamen_html = f"""
                                        <div style='background-color: #FEF2F2; border-left: 6px solid #B91C1C; padding: 15px; margin-top: 15px; border-radius: 4px; color: #7F1D1D;'>
                                            <h5 style='margin-top:0; color:#991B1B;'>🛑 DICTAMEN: STOP LOSS ESTRUCTURAL ALCANZADO</h5>
                                            <p style='margin:0; font-size:0.95rem;'>La cuota del mercado (<b>{cuota_ingresada:.2f}</b>) ha perforado tu límite. Ejecuta el botón de salida.</p>
                                        </div>
                                        """
                                    # 3. MUERTE POR RELOJ (Tiempo) - CORREGIDO
                                    elif tiempo_restante <= 10 and not ganando_actualmente:
                                        if oferta_cashout_ft > 0:
                                            texto_rescate = f"Toma el rescate de ${oferta_cashout_ft:,.0f} de inmediato antes de que caiga a $0."
                                        else:
                                            texto_rescate = "Ejecuta la cobertura o cierra la operación de inmediato asumiendo la pérdida."
                                        dictamen_html = f"""
                                        <div style='background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 15px; margin-top: 15px; border-radius: 4px; color: #991B1B;'>
                                            <h5 style='margin-top:0; color:#991B1B;'>⏳ MUERTE TÁCTICA POR RELOJ</h5>
                                            <p style='margin:0; font-size:0.95rem;'>Faltan {tiempo_restante} minutos. No importa si los ataques están en {apm_total:.1f} APM, el tiempo se acabó y vas perdiendo. {texto_rescate}</p>
                                        </div>
                                        """
                                    # 4. RELOJ A FAVOR (Tiempo)
                                    elif tiempo_restante <= 10 and ganando_actualmente:
                                        dictamen_html = f"""
                                        <div style='background-color: #F0FDF4; border-left: 6px solid #10B981; padding: 15px; margin-top: 15px; border-radius: 4px; color: #064E3B;'>
                                            <h5 style='margin-top:0; color:#047857;'>🛡️ RELOJ A FAVOR (Blindaje Temporal)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>Quedan solo {tiempo_restante} minutos y llevas la ventaja. El tiempo es tu aliado, aguanta la posición.</p>
                                        </div>
                                        """
                                    # 5. RIESGO CERO
                                    elif pct_rescate_banca < 0.5 and oferta_cashout_ft > 0:
                                        dictamen_html = f"""
                                        <div style='background-color: #F1F5F9; border-left: 6px solid #64748B; padding: 15px; margin-top: 15px; border-radius: 4px; color: #334155;'>
                                            <h5 style='margin-top:0; color:#475569;'>🛡️ DICTAMEN: RIESGO CERO (Marginalidad Absoluta)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>La casa te ofrece migajas (${oferta_cashout_ft:,.0f}). No salves centavos. Deja correr la posición.</p>
                                        </div>
                                        """
                                    # 6. ESTADO FÍSICO VS HISTÓRICO
                                    elif diferencia_goles >= 2:
                                        dictamen_html = f"""
                                        <div style='background-color: #F8FAFC; border-left: 6px solid #8B5CF6; padding: 15px; margin-top: 15px; border-radius: 4px; color: #4C1D95;'>
                                            <h5 style='margin-top:0; color:#5B21B6;'>🔮 DICTAMEN: REVOCAR COBERTURA (VENTAJA CONCLUYENTE)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>Tienes ventaja de 2+ goles. Retén tu reserva intacta y maximiza el rendimiento.</p>
                                        </div>
                                        """
                                    elif (diferencia_goles <= 0) and (share_nuestro > 50.0) and (ird < 85.0):
                                        dictamen_html = f"""
                                        <div style='background-color: #F0FDF4; border-left: 6px solid #059669; padding: 15px; margin-top: 15px; border-radius: 4px; color: #064E3B;'>
                                            <h5 style='margin-top:0; color:#047857;'>🔍 DICTAMEN: PACIENCIA TÁCTICA (MOMENTUM A FAVOR)</h5>
                                            <p style='margin:0; font-size:0.95rem;'>La tendencia estadística te ampara (IRD: {ird:.1f}%). Tienes {tiempo_restante} min de vida, mantén la posición.</p>
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
                                        va_empatado = (diferencia_goles == 0)
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
                                            • <b>Exposición de esta operación:</b> {exposicion_pct:.1f}% (Límite Global: {umbral_permitido:.1f}%)<br>
                                            • <b>Peso del Capital Rescatado:</b> Si ejecutas el seguro, estás rescatando el <b>{pct_rescate_banca:.2f}%</b> de tu patrimonio total.<br><br>
                                            <b>Veredicto de Rescate:</b> {impacto_str}
                                        </div>
                                    </div>
                                    """
                                    
                                    st.markdown(dictamen_html + alerta_patrimonial_html, unsafe_allow_html=True)
                                    
                                    # =====================================================================
                                    # ALERTA DE ROBO CASHOUT VS COBERTURA MANUAL
                                    # =====================================================================
                                    if oferta_cashout_ft > 0:
                                        utilidad_cashout = oferta_cashout_ft - op['stake_1']
                                        diferencia_cashout = util_cobertura_con_cob - utilidad_cashout
                                        
                                        if diferencia_cashout > 0:
                                            st.markdown(f"""
                                            <div style="background-color: #F0FDF4; border-left: 5px solid #22C55E; padding: 12px; border-radius: 4px; margin-top: 10px;">
                                                <span style="font-size: 1.05em; color: #166534;">🛡️ <b>¡NO USES EL BOTÓN DE LA CASA!</b></span><br>
                                                <span style="font-size: 0.95em; color: #15803D;">El botón te deja un balance de <b>${utilidad_cashout:,.0f}</b>. Cubrir matemáticamente la cuota te deja en <b>${util_cobertura_con_cob:,.0f}</b>.</span><br>
                                                <span style="font-weight: bold; color: #16A34A;">👉 Cazar la cuota tú mismo te salva ${diferencia_cashout:,.0f} COP adicionales.</span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        elif diferencia_cashout < 0:
                                            st.markdown(f"""
                                            <div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 12px; border-radius: 4px; margin-top: 10px;">
                                                <span style="font-size: 1.05em; color: #991B1B;">🚨 <b>¡TOMA EL CASHOUT DE LA CASA INMEDIATAMENTE!</b></span><br>
                                                <span style="font-size: 0.95em; color: #B91C1C;">Cubrir matemáticamente te deja en <b>${util_cobertura_con_cob:,.0f}</b>. El botón de la casa es más generoso y te deja en <b>${utilidad_cashout:,.0f}</b>.</span><br>
                                                <span style="font-weight: bold; color: #DC2626;">👉 Usar el botón de la casa te salva ${abs(diferencia_cashout):,.0f} COP. ¡Tómalo ya!</span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                        es_mejor_cashout = True if (util_cobertura_con_cob - utilidad_cashout) < 0 else False
                                        
                                        if es_mejor_cashout:
                                            if st.button("✅ LIQUIDAR POR CASHOUT", key=f"btn_cash_ft_{op['codigo']}", use_container_width=True):
                                                hora_actual = datetime.datetime.now().strftime("%H:%M")
                                                supabase.table("historial_trading").update({
                                                    "estado": "CERRADA",
                                                    "resultado_final": "Cashout (Cierre Anticipado)",
                                                    "utilidad_neta_real": float(utilidad_cashout),
                                                    "roi_real": float((utilidad_cashout / op['stake_1']) * 100),
                                                    "hora_cobertura": hora_actual,
                                                    "plataforma_cobertura": "Misma (Cashout)"
                                                }).eq("codigo", op['codigo']).execute()
                                                st.success(f"¡Cashout registrado! Has cerrado la operación con retorno de ${oferta_cashout_ft:,.0f}.")
                                                st.rerun()
                                    
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
                                goles_finales_seleccion = st.number_input(f"⚽ Goles finales de {eq_local}:", min_value=0, step=1, value=0, key=f"gf_sel_es_{op['codigo']}")
                                goles_finales_rival = st.number_input(f"🚀 Goles finales de {eq_vis}:", min_value=0, step=1, value=0, key=f"gf_riv_es_{op['codigo']}")
                                
                                if st.form_submit_button("Cerrar Libro Mayor"):
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
                                    else: 
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
    
    # 🛡️ BLINDAJE CONTABLE: Calculamos el tope aquí mismo antes de abrir las pestañas
    try:
        tope_maximo_evento = max(0.0, saldo_real * 0.05)
    except NameError:
        tope_maximo_evento = 5000.0  # Valor de rescate en caso de que el saldo aún no haya cargado

    st.markdown("## 🔮 Oráculo Predictivo")
    st.write("Planifica tu entrada al mercado y déjala en el Radar para ejecutarla en vivo basándote en la táctica real.")

    # 🚨 LAS TRES PESTAÑAS DEL ORÁCULO
    tab_pre, tab_radar, tab_vivo = st.tabs(["📋 Escáner Pre-Partido", "📡 Radar En Vivo (Watchlist)", "⏱️ Laboratorio Táctico (Libre)"])

    # ---------------------------------------------------------
    # PESTAÑA 1: PRE-PARTIDO (Oráculo Machine Learning + Contexto)
    # ---------------------------------------------------------
    with tab_pre:
        st.markdown("<h3 style='color: #1E3A8A;'>🧠 Oráculo Predictivo (Escáner & Auditoría)</h3>", unsafe_allow_html=True)
        st.info("Ingresa las cuotas 1X2 para buscar gemelos históricos. Luego analiza el panorama y audita a profundidad el mercado que elijas.")

        # --- ESCUDO ANTI-FANTASMA: Memoria para que la interfaz no se recoja ---
        if 'ia_pre_activa' not in st.session_state:
            st.session_state.ia_pre_activa = False

        if not modelos_cargados or df_global is None:
            st.error("🚨 Modelos o datos no encontrados. Por favor, asegúrate de que se cargaron correctamente.")
        else:
            st.markdown("#### 1️⃣ Define el Contexto del Partido (Cuotas 1X2)")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                c_loc_pre = st.number_input("Cuota Local:", min_value=1.01, value=2.10, step=0.05, key="pre_c_loc")
            with col_p2:
                c_emp_pre = st.number_input("Cuota Empate:", min_value=1.01, value=3.20, step=0.05, key="pre_c_emp")
            with col_p3:
                c_vis_pre = st.number_input("Cuota Visita:", min_value=1.01, value=3.50, step=0.05, key="pre_c_vis")
            
            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                margen = st.slider("🎯 Margen de Búsqueda de Gemelos (±):", min_value=0.05, max_value=0.50, value=0.10, step=0.05)
            with col_m2:
                # 🧮 EL SISTEMA CALCULA TU TECHO MÁXIMO SEGÚN LA BARRA LATERAL
                limite_riesgo_dinero = saldo_real * (max_riesgo_real / 100.0)
                tope_estricto = float(max(100.0, limite_riesgo_dinero)) 
                
                # ✍️ TÚ ESCRIBES LA PLATA, EL SISTEMA TE FRENA SI TE PASAS
                stake_pre = st.number_input(
                    f"Stake Planeado (Max {max_riesgo_real}% = ${tope_estricto:,.0f}):", 
                    min_value=100.0, 
                    max_value=tope_estricto, 
                    value=float(min(5000.0, tope_estricto)), # Empieza en 5000, pero lo borras y pones lo que quieras
                    step=500.0, 
                    format="%.0f"
                )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 Buscar Gemelos y Ejecutar Red Neuronal", use_container_width=True, type="primary"):
                st.session_state.ia_pre_activa = True

            if st.session_state.ia_pre_activa:
                df_clean = df_global.dropna(subset=['avg_odds_home_win', 'avg_odds_draw', 'avg_odds_away_win'])
                
                df_gemelas = df_clean[
                    (df_clean['avg_odds_home_win'] >= c_loc_pre - margen) & (df_clean['avg_odds_home_win'] <= c_loc_pre + margen) &
                    (df_clean['avg_odds_draw'] >= c_emp_pre - margen) & (df_clean['avg_odds_draw'] <= c_emp_pre + margen) &
                    (df_clean['avg_odds_away_win'] >= c_vis_pre - margen) & (df_clean['avg_odds_away_win'] <= c_vis_pre + margen)
                ]
                
                total_gemelas = len(df_gemelas)
                
                if total_gemelas < 10:
                    st.warning(f"🚨 Solo se encontraron {total_gemelas} partidos similares. Sube el 'Margen de Búsqueda'.")
                else:
                    st.success(f"✅ Se encontraron **{total_gemelas} partidos similares** en la base de datos histórica.")
                    
                    # === PROCESAMIENTO IA (UNA SOLA VEZ) ===
                    avg_h = df_gemelas['avg_odds_home_win'].mean()
                    avg_d = df_gemelas['avg_odds_draw'].mean()
                    avg_a = df_gemelas['avg_odds_away_win'].mean()
                    n_odds = df_gemelas['n_odds_home_win'].mean() if 'n_odds_home_win' in df_gemelas.columns else 15
                    
                    inef_h = c_loc_pre - avg_h
                    inef_d = c_emp_pre - avg_d
                    inef_a = c_vis_pre - avg_a
                    
                    input_data = pd.DataFrame([[avg_h, avg_d, avg_a, c_loc_pre, c_emp_pre, c_vis_pre, inef_h, inef_d, inef_a, n_odds, n_odds, n_odds]], 
                        columns=['avg_odds_home_win', 'avg_odds_draw', 'avg_odds_away_win', 'max_odds_home_win', 'max_odds_draw', 'max_odds_away_win', 'ineficiencia_local', 'ineficiencia_empate', 'ineficiencia_visita', 'n_odds_home_win', 'n_odds_draw', 'n_odds_away_win'])
                    
                    prob_1x2 = modelo_1x2.predict_proba(input_data)[0] 
                    prob_empate, prob_local, prob_visita = prob_1x2[0], prob_1x2[1], prob_1x2[2]
                    
                    pred_goles = modelo_goles.predict(input_data)[0]
                    prob_btts_si = modelo_btts.predict_proba(input_data)[0][1] 
                    prob_btts_no = 1.0 - prob_btts_si

                    # ==================================================================
                    # 2️⃣ PANEL GENERAL (MAPA PANORÁMICO)
                    # ==================================================================
                    st.markdown("---")
                    st.markdown(f"<h3 style='text-align: center; color: #1E293B;'>🤖 PANORAMA GLOBAL DEL PARTIDO</h3>", unsafe_allow_html=True)
                    
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.markdown("#### 🏆 Probabilidades 1X2 (IA)")
                        st.metric("Gana Local", f"{prob_local*100:.1f}%")
                        st.metric("Empate", f"{prob_empate*100:.1f}%")
                        st.metric("Gana Visita", f"{prob_visita*100:.1f}%")
                        
                    with col_r2:
                        st.markdown("#### ⚽ Mercado de Goles y BTTS")
                        st.metric("Goles Esperados (IA)", f"{pred_goles:.2f} ⚽")
                        g1, g2 = st.columns(2)
                        g1.metric("BTTS (SÍ)", f"{prob_btts_si*100:.1f}%")
                        g1.metric("BTTS (NO)", f"{prob_btts_no*100:.1f}%")

                    # ==================================================================
                    # 3️⃣ AUDITORÍA A LA CARTA
                    # ==================================================================
                    st.markdown("---")
                    st.markdown("#### 🔎 Auditoría Profunda de Value Betting")
                    mercado_evaluar = st.selectbox("¿Qué mercado decides investigar a fondo?", 
                                                  ["-- Selecciona un mercado --", "Mercado 1X2", "Ambos Anotan (BTTS)", "Línea de Goles"])
                    
                    mercado_display = mercado_evaluar # Para el Radar
                    
                    # ----------------- AUDITORÍA: AMBOS ANOTAN -----------------
                    if mercado_evaluar == "Ambos Anotan (BTTS)":
                        st.markdown("##### ⚖️ Frente a Frente: SÍ vs NO")
                        c_btts1, c_btts2 = st.columns(2)
                        cuota_ofrecida_si = c_btts1.number_input("Cuota Ofrecida por el SÍ:", min_value=1.01, value=1.85, step=0.05)
                        cuota_ofrecida_no = c_btts2.number_input("Cuota Ofrecida por el NO:", min_value=1.01, value=1.85, step=0.05)
                        
                        cuota_minima_si = 1 / prob_btts_si if prob_btts_si > 0 else 99.0
                        cuota_minima_no = 1 / prob_btts_no if prob_btts_no > 0 else 99.0
                        
                        ev_si = (prob_btts_si * (stake_pre * cuota_ofrecida_si - stake_pre)) - (prob_btts_no * stake_pre)
                        ev_no = (prob_btts_no * (stake_pre * cuota_ofrecida_no - stake_pre)) - (prob_btts_si * stake_pre)
                        
                        roi_si = (ev_si / stake_pre) * 100
                        roi_no = (ev_no / stake_pre) * 100

                        col_res_si, col_res_no = st.columns(2)
                        
                        # Panel SÍ
                        with col_res_si:
                            bg_si = "#ECFDF5" if ev_si > 0 else "#FEF2F2"
                            b_color_si = "#10B981" if ev_si > 0 else "#EF4444"
                            st.markdown(f"""
                            <div style="background-color: {bg_si}; border: 2px solid {b_color_si}; padding: 15px; border-radius: 8px;">
                                <h4 style="color:{b_color_si}; text-align:center; margin-top:0;">💥 INVERTIR AL SÍ</h4>
                                <p style="margin:0;"><b>Cuota Mínima Exigida:</b> {cuota_minima_si:.2f}</p>
                                <p style="margin:0;"><b>Casa te Ofrece:</b> {cuota_ofrecida_si:.2f}</p>
                                <hr style="margin:10px 0;">
                                <h5 style="text-align:center; margin:0; color:{b_color_si};">ROI Proyectado: {roi_si:.1f}%</h5>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        # Panel NO
                        with col_res_no:
                            bg_no = "#ECFDF5" if ev_no > 0 else "#FEF2F2"
                            b_color_no = "#10B981" if ev_no > 0 else "#EF4444"
                            st.markdown(f"""
                            <div style="background-color: {bg_no}; border: 2px solid {b_color_no}; padding: 15px; border-radius: 8px;">
                                <h4 style="color:{b_color_no}; text-align:center; margin-top:0;">🛡️ INVERTIR AL NO</h4>
                                <p style="margin:0;"><b>Cuota Mínima Exigida:</b> {cuota_minima_no:.2f}</p>
                                <p style="margin:0;"><b>Casa te Ofrece:</b> {cuota_ofrecida_no:.2f}</p>
                                <hr style="margin:10px 0;">
                                <h5 style="text-align:center; margin:0; color:{b_color_no};">ROI Proyectado: {roi_no:.1f}%</h5>
                            </div>
                            """, unsafe_allow_html=True)

                    # ----------------- AUDITORÍA: 1X2 -----------------
                    elif mercado_evaluar == "Mercado 1X2":
                        opcion_1x2 = st.radio("¿A qué equipo quieres auditar?", ["Gana Local", "Empate", "Gana Visita"], horizontal=True)
                        cuota_ofrecida_1x2 = st.number_input(f"Cuota Ofrecida por {opcion_1x2}:", min_value=1.01, value=2.0, step=0.05)
                        
                        prob_objetivo = prob_local if opcion_1x2 == "Gana Local" else (prob_empate if opcion_1x2 == "Empate" else prob_visita)
                        cuota_minima = 1 / prob_objetivo if prob_objetivo > 0 else 99.0
                        
                        ev_1x2 = (prob_objetivo * (stake_pre * cuota_ofrecida_1x2 - stake_pre)) - ((1 - prob_objetivo) * stake_pre)
                        roi_1x2 = (ev_1x2 / stake_pre) * 100
                        
                        bg_1x2 = "#ECFDF5" if ev_1x2 > 0 else "#FEF2F2"
                        b_color_1x2 = "#10B981" if ev_1x2 > 0 else "#EF4444"
                        mensaje = "✅ VALOR ENCONTRADO" if ev_1x2 > 0 else "🚨 TRAMPA DETECTADA"
                        
                        st.markdown(f"""
                        <div style="background-color: {bg_1x2}; border: 2px solid {b_color_1x2}; padding: 20px; border-radius: 8px; text-align: center;">
                            <h3 style="color:{b_color_1x2}; margin-top:0;">{mensaje}</h3>
                            <p style="font-size:1.1rem; margin:0;">Para <b>{opcion_1x2}</b>, la IA exige una cuota mínima de <b>{cuota_minima:.2f}</b>.</p>
                            <h4 style="color:{b_color_1x2}; margin: 10px 0;">ROI Proyectado: {roi_1x2:.1f}%</h4>
                        </div>
                        """, unsafe_allow_html=True)

                    # ----------------- AUDITORÍA: GOLES -----------------
                    elif mercado_evaluar == "Línea de Goles":
                        linea_g = st.number_input("¿Qué línea de goles quieres auditar?", min_value=0.5, max_value=8.5, value=2.5, step=1.0)
                        mercado_display = f"Goles ({linea_g})"
                        c_gol1, c_gol2 = st.columns(2)
                        cuota_over = c_gol1.number_input(f"Cuota MÁS de {linea_g}:", min_value=1.01, value=1.85, step=0.05)
                        cuota_under = c_gol2.number_input(f"Cuota MENOS de {linea_g}:", min_value=1.01, value=1.85, step=0.05)
                        
                        total_goles_hist = df_gemelas['home_score'] + df_gemelas['away_score']
                        prob_over = len(df_gemelas[total_goles_hist > linea_g]) / total_gemelas if total_gemelas > 0 else 0
                        prob_under = len(df_gemelas[total_goles_hist < linea_g]) / total_gemelas if total_gemelas > 0 else 0
                        
                        cuota_min_over = 1 / prob_over if prob_over > 0 else 99.0
                        cuota_min_under = 1 / prob_under if prob_under > 0 else 99.0
                        
                        ev_o = (prob_over * (stake_pre * cuota_over - stake_pre)) - (prob_under * stake_pre)
                        ev_u = (prob_under * (stake_pre * cuota_under - stake_pre)) - (prob_over * stake_pre)
                        
                        col_go, col_gu = st.columns(2)
                        with col_go:
                            bg_o = "#ECFDF5" if ev_o > 0 else "#FEF2F2"
                            b_c_o = "#10B981" if ev_o > 0 else "#EF4444"
                            st.markdown(f"<div style='background-color:{bg_o}; border:2px solid {b_c_o}; padding:15px; border-radius:8px; text-align:center;'><h4 style='color:{b_c_o}; margin:0;'>⬆️ OVER {linea_g}</h4><p>Prob: {prob_over*100:.1f}%</p><p>Cuota Mínima: {cuota_min_over:.2f}</p><h5 style='color:{b_c_o};'>ROI: {(ev_o/stake_pre)*100:.1f}%</h5></div>", unsafe_allow_html=True)
                        with col_gu:
                            bg_u = "#ECFDF5" if ev_u > 0 else "#FEF2F2"
                            b_c_u = "#10B981" if ev_u > 0 else "#EF4444"
                            st.markdown(f"<div style='background-color:{bg_u}; border:2px solid {b_c_u}; padding:15px; border-radius:8px; text-align:center;'><h4 style='color:{b_c_u}; margin:0;'>⬇️ UNDER {linea_g}</h4><p>Prob: {prob_under*100:.1f}%</p><p>Cuota Mínima: {cuota_min_under:.2f}</p><h5 style='color:{b_c_u};'>ROI: {(ev_u/stake_pre)*100:.1f}%</h5></div>", unsafe_allow_html=True)

                    # ==================================================================
                    # 4️⃣ ZONA DE GUARDADO EN EL RADAR
                    # ==================================================================
                    if mercado_evaluar != "-- Selecciona un mercado --":
                        st.markdown("---")
                        st.markdown("### 📡 Guardar en Radar En Vivo")
                        st.write("¿Encontraste valor? Guárdalo en tu lista de seguimiento.")
                        
                        rp1, rp2 = st.columns(2)
                        with rp1:
                            nombre_partido_radar = st.text_input("Nombre del Partido:", placeholder="Ej: Real Madrid vs Man City")
                        with rp2:
                            plataforma_radar_sel = st.selectbox("Plataforma a usar:", ["1xBet", "BetPlay", "Wplay", "Rushbet", "Codere", "Yajuego", "Zamba", "Sportium", "Megapuesta", "Otra"], key="plat_radar")
                            plataforma_radar = st.text_input("Especifica la plataforma:") if plataforma_radar_sel == "Otra" else plataforma_radar_sel
                        
                        if st.button("📌 Mandar al Radar", use_container_width=True):
                            if not nombre_partido_radar:
                                st.error("Debes ponerle un nombre al partido.")
                            else:
                                if supabase is not None:
                                    import random
                                    nuevo_codigo = f"SCAN-{random.randint(1000,9999)}"
                                    
                                    # Determinamos qué cuota guardar según lo que estaba evaluando
                                    c_guardar = 2.0
                                    if mercado_evaluar == "Ambos Anotan (BTTS)": c_guardar = cuota_ofrecida_si if ev_si > ev_no else cuota_ofrecida_no
                                    elif mercado_evaluar == "Mercado 1X2": c_guardar = cuota_ofrecida_1x2
                                    elif mercado_evaluar == "Línea de Goles": c_guardar = cuota_over if ev_o > ev_u else cuota_under

                                    datos_radar = {
                                        "codigo": nuevo_codigo,
                                        "partido": nombre_partido_radar,
                                        "estrategia": "Escáner Oráculo", 
                                        "seleccion_inicial": mercado_display,
                                        "seleccion_cobertura": "N/A (Radar)", 
                                        "plataforma_inicial": plataforma_radar,
                                        "plataforma_dutch_secundaria": "",
                                        "plataforma_cobertura": "",
                                        "capital_total": float(stake_pre),
                                        "cuota_inicial": float(c_guardar),
                                        "stake_1": float(stake_pre),
                                        "reserva_stake_2": 0.0, 
                                        "cuota_objetivo": 0.0, 
                                        "cuota_stop_loss": 0.0, 
                                        "estado": "RADAR", 
                                        "tipo_banca": "SIMULACION",
                                        "cuota_base_audit": float(c_loc_pre), 
                                        "cuota_empate_audit": float(c_emp_pre),
                                        "cuota_dc_audit": 0.0,
                                        "cuota_amenaza_audit": float(c_vis_pre),
                                        "es_dutching": False,
                                        "stake_dutch_base": 0.0,
                                        "stake_dutch_empate": 0.0
                                    }
                                    
                                    try:
                                        supabase.table("historial_trading").insert(datos_radar).execute()
                                        st.session_state.ia_pre_activa = False 
                                        st.success(f"✅ ¡Partido '{nombre_partido_radar}' guardado con éxito! Ref: {nuevo_codigo}")
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(f"❌ Error al guardar en Radar: {str(db_err)}")
                                else:
                                    st.error("Conecta Supabase primero.")

    # ---------------------------------------------------------
    # PESTAÑA 2: RADAR EN VIVO (Watchlist y Ejecución)
    # ---------------------------------------------------------
    with tab_radar:
        st.subheader("📡 Tu Radar de Seguimiento")
        st.write("Partidos aprobados por el Escáner. Inyecta la foto táctica del partido en curso, configura tus límites de ganancia/pérdida, y ejecuta la posición.")
        
        if supabase is not None:
            res_radar = supabase.table("historial_trading").select("*").eq("estado", "RADAR").execute()
            partidos_radar = res_radar.data
            
            if not partidos_radar:
                st.info("Tu radar está vacío. Escanea partidos en la pestaña 'Escáner Pre-Partido' y mándalos para acá.")
            else:
                for pr in partidos_radar:
                    with st.expander(f"📌 {pr['partido']} | Mdo: {pr['seleccion_inicial']} | Cuota Plan: {pr['cuota_inicial']} | Stake: ${pr['stake_1']:,.0f}"):
                        st.write(f"**Cuotas Base Iniciales:** Local ({pr.get('cuota_base_audit', 'N/A')}) | Empate ({pr.get('cuota_empate_audit', 'N/A')}) | Visita ({pr.get('cuota_amenaza_audit', 'N/A')})")
                        st.markdown("---")
                        
                        # ------------------------------------------------------------------
                        # 🔄 BOTÓN DE SINCRONIZACIÓN Y LECTURA DE FOTOS
                        # ------------------------------------------------------------------
                        col_tit1, col_tit2 = st.columns([2, 1])
                        with col_tit1:
                            st.markdown("#### 📸 Foto Táctica En Vivo")
                        with col_tit2:
                            if st.button("🔄 Sincronizar Info", key=f"btn_sync_{pr['codigo']}"):
                                try:
                                    res_sync = supabase.table("registro_fotos").select("*").like("codigo_posicion", f"{pr['codigo']}%").order("minuto_evaluado", desc=True).limit(1).execute()
                                    if res_sync.data:
                                        foto_reciente = res_sync.data[0]
                                        st.session_state[f"mr_{pr['codigo']}"] = int(foto_reciente['minuto_evaluado'])
                                        st.session_state[f"glr_{pr['codigo']}"] = int(foto_reciente['goles_local'])
                                        st.session_state[f"gvr_{pr['codigo']}"] = int(foto_reciente['goles_vis'])
                                        st.session_state[f"atl_{pr['codigo']}"] = int(foto_reciente.get('atqt_local', 0))
                                        st.session_state[f"atv_{pr['codigo']}"] = int(foto_reciente.get('atqt_vis', 0))
                                        st.session_state[f"alr_{pr['codigo']}"] = int(foto_reciente['atkp_local'])
                                        st.session_state[f"avr_{pr['codigo']}"] = int(foto_reciente['atkp_vis'])
                                        st.success(f"✅ ¡Datos del min {foto_reciente['minuto_evaluado']} importados!")
                                    else:
                                        st.warning("⚠️ No hay fotos previas en el Seguimiento.")
                                except Exception as e:
                                    st.error(f"Error sincronizando: {e}")

                        # ------------------------------------------------------------------
                        # 🏷️ EXTRACCIÓN DE NOMBRES
                        # ------------------------------------------------------------------
                        partido_str_ui = str(pr.get('partido', ''))
                        solo_partido_ui = partido_str_ui.split("|")[0].replace("🏟️", "").strip() if "|" in partido_str_ui else partido_str_ui
                        txt_norm_ui = solo_partido_ui.lower().replace("vs.", "vs").replace("-", "vs")
                        
                        if "vs" in txt_norm_ui:
                            eq_loc_ui = txt_norm_ui.split("vs")[0].strip().title()
                            eq_vis_ui = txt_norm_ui.split("vs")[1].strip().title()
                        else:
                            eq_loc_ui = "Local"
                            eq_vis_ui = "Visita"
                                        
                        # ------------------------------------------------------------------
                        # 🎛️ PANEL DE EVALUACIÓN MULTI-ESTRATEGIA
                        # ------------------------------------------------------------------
                        tab_datos, tab_anti_empate = st.tabs(["⚙️ Carga de Datos (APM)", "💣 Calculadora Anti-Empate"])
                        
                        with tab_datos:
                            # --- ⚡ NUEVO: MÓDULO HÍBRIDO API (AUTO-RELLENADO) ---
                            st.markdown("""
                            <div style='background-color: #F0FDF4; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #16A34A; margin-bottom: 15px;'>
                                <span style='font-size: 0.9rem; color: #166534; font-weight: bold;'>⚡ Auto-Escanear Partido (Opcional)</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_api1, col_api2 = st.columns([2, 1])
                            with col_api1:
                                api_fixture_id = st.text_input("🔗 ID del Partido (API):", key=f"api_id_{pr['codigo']}", placeholder="Ej: 1492290", help="Encuentra este ID en la web de API-Football.")
                            with col_api2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("⚡ Extraer Datos", key=f"btn_api_{pr['codigo']}", use_container_width=True):
                                    if not api_fixture_id.strip():
                                        st.warning("Ingresa el ID del partido primero.")
                                    else:
                                        import requests
                                        
                                        # 🔑 TU LLAVE DE API-FOOTBALL
                                        API_KEY = "26110cee2e79eff8286acec6fd054558" 
                                        
                                        headers = {'x-apisports-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}
                                        
                                        try:
                                            with st.spinner("🛰️ Extrayendo datos en vivo..."):
                                                # Llamada 1: Minutos y Goles
                                                url_fixture = f"https://v3.football.api-sports.io/fixtures?id={api_fixture_id.strip()}"
                                                res_fix = requests.get(url_fixture, headers=headers, timeout=5).json()
                                                
                                                if res_fix.get('response') and len(res_fix['response']) > 0:
                                                    p_data = res_fix['response'][0]
                                                    
                                                    # Inyectamos Minuto y Goles a la memoria de forma segura
                                                    st.session_state[f"mr_{pr['codigo']}"] = int(p_data['fixture']['status']['elapsed'] or 0)
                                                    st.session_state[f"glr_{pr['codigo']}"] = int(p_data['goals']['home'] or 0)
                                                    st.session_state[f"gvr_{pr['codigo']}"] = int(p_data['goals']['away'] or 0)
                                                    
                                                    # Llamada 2: Estadísticas avanzadas
                                                    url_stats = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={api_fixture_id.strip()}"
                                                    res_stats = requests.get(url_stats, headers=headers, timeout=5).json()
                                                    
                                                    encontro_ataques = False
                                                    if len(res_stats.get('response', [])) >= 2:
                                                        stats_loc = res_stats['response'][0]['statistics']
                                                        stats_vis = res_stats['response'][1]['statistics']
                                                        
                                                        # Función interna blindada para limpiar strings como '91%' o 'None'
                                                        def limpiar_valor(val):
                                                            if val is None: return 0
                                                            val_str = str(val).replace('%', '').strip()
                                                            try:
                                                                return int(float(val_str))
                                                            except ValueError:
                                                                return 0

                                                        for stat in stats_loc:
                                                            nombre_stat = str(stat.get('type', '')).lower()
                                                            valor_stat = limpiar_valor(stat.get('value'))
                                                            
                                                            if 'total attack' in nombre_stat or nombre_stat == 'attacks':
                                                                st.session_state[f"atl_{pr['codigo']}"] = valor_stat
                                                                encontro_ataques = True
                                                            elif 'dangerous attack' in nombre_stat:
                                                                st.session_state[f"alr_{pr['codigo']}"] = valor_stat
                                                                encontro_ataques = True
                                                                
                                                        for stat in stats_vis:
                                                            nombre_stat = str(stat.get('type', '')).lower()
                                                            valor_stat = limpiar_valor(stat.get('value'))
                                                            
                                                            if 'total attack' in nombre_stat or nombre_stat == 'attacks':
                                                                st.session_state[f"atv_{pr['codigo']}"] = valor_stat
                                                            elif 'dangerous attack' in nombre_stat:
                                                                st.session_state[f"avr_{pr['codigo']}"] = valor_stat
                                                    
                                                    if encontro_ataques:
                                                        st.success("✅ ¡Datos y ataques extraídos con éxito!")
                                                    else:
                                                        st.warning("⚠️ Minuto y goles actualizados. Esta liga no transmite ataques por API; ponlos a mano.")
                                                    
                                                    st.rerun()
                                                else:
                                                    st.error("❌ No existe un partido con ese ID.")
                                        except Exception as e:
                                            st.error(f"❌ Error de red: {e}")
                            
                            st.markdown("---")
                            # --- FIN MÓDULO HÍBRIDO API ---
                            
                            # TUS CAJAS MANUALES INTACTAS (Ahora leen lo que inyectó la API o lo que tú escribas)
                            cr1, cr2, cr3 = st.columns(3)
                            m_rad = cr1.number_input("⏱️ Minuto:", min_value=0, max_value=120, key=f"mr_{pr['codigo']}", value=st.session_state.get(f"mr_{pr['codigo']}", 0))
                            gl_rad = cr2.number_input(f"⚽ Goles {eq_loc_ui}:", min_value=0, key=f"glr_{pr['codigo']}", value=st.session_state.get(f"glr_{pr['codigo']}", 0))
                            gv_rad = cr3.number_input(f"⚽ Goles {eq_vis_ui}:", min_value=0, key=f"gvr_{pr['codigo']}", value=st.session_state.get(f"gvr_{pr['codigo']}", 0))
                            
                            st.markdown("<p style='font-size: 13px; color: #64748B; margin-bottom: 5px;'>Filtro de Verticalidad (Ataques Totales vs Peligrosos)</p>", unsafe_allow_html=True)
                            cr4, cr5, cr6, cr7 = st.columns(4)
                            # Ataques Totales
                            atq_tot_loc = cr4.number_input(f"Atq. Tot {eq_loc_ui}:", min_value=0, key=f"atl_{pr['codigo']}", value=st.session_state.get(f"atl_{pr['codigo']}", 0))
                            atq_tot_vis = cr5.number_input(f"Atq. Tot {eq_vis_ui}:", min_value=0, key=f"atv_{pr['codigo']}", value=st.session_state.get(f"atv_{pr['codigo']}", 0))
                            # Ataques Peligrosos
                            al_rad = cr6.number_input(f"🔥 Peligro {eq_loc_ui}:", min_value=0, key=f"alr_{pr['codigo']}", value=st.session_state.get(f"alr_{pr['codigo']}", 0))
                            av_rad = cr7.number_input(f"🔥 Peligro {eq_vis_ui}:", min_value=0, key=f"avr_{pr['codigo']}", value=st.session_state.get(f"avr_{pr['codigo']}", 0))

                        with tab_anti_empate:
                            st.markdown("""
                            <div style='background-color: #F8FAFC; border-left: 4px solid #8B5CF6; padding: 10px; border-radius: 4px; margin-bottom: 15px;'>
                                <h4 style='margin:0; color: #4C1D95;'>⚖️ Estrategia Asimétrica (Riesgo al Empate)</h4>
                                <p style='margin:0; font-size:0.85rem; color: #64748B;'>Ideal para usar en Vivo (Min > 45) cuando el Súper Favorito asedia (APM > 1.0) y el marcador va 0-0.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c_ae1, c_ae2, c_ae3 = st.columns(3)
                            cuota_sug_fav = min(float(pr.get('cuota_base_audit', 1.08)), float(pr.get('cuota_amenaza_audit', 1.08)))
                            cuota_sug_deb = max(float(pr.get('cuota_base_audit', 18.20)), float(pr.get('cuota_amenaza_audit', 18.20)))
                            
                            cuota_fav_ae = c_ae1.number_input("👑 Cuota Favorito (En Vivo):", min_value=1.01, step=0.01, value=max(1.01, cuota_sug_fav), key=f"c_fav_ae_{pr['codigo']}")
                            cuota_deb_ae = c_ae2.number_input("🩸 Cuota Débil (En Vivo):", min_value=1.01, step=0.1, value=max(2.0, cuota_sug_deb), key=f"c_deb_ae_{pr['codigo']}")
                            inv_total_ae = c_ae3.number_input("💰 Inversión Total ($):", min_value=1000, step=10000, value=100000, key=f"inv_ae_{pr['codigo']}")
                            
                            if cuota_deb_ae > 0 and cuota_fav_ae > 0:
                                stake_cobertura = inv_total_ae / cuota_deb_ae
                                stake_fuerte = inv_total_ae - stake_cobertura
                                
                                retorno_fav = stake_fuerte * cuota_fav_ae
                                utilidad_fav = retorno_fav - inv_total_ae
                                roi_pct = (utilidad_fav / inv_total_ae) * 100 if inv_total_ae > 0 else 0
                                
                                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                                if stake_fuerte > 0:
                                    st.markdown(f"""
                                    <div style='display: flex; justify-content: space-between; margin-bottom: 10px;'>
                                        <div style='background-color: #ECFDF5; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #A7F3D0;'>
                                            <h5 style='margin:0; color: #065F46;'>🟢 GANA FAVORITO</h5>
                                            <p style='margin:5px 0 0 0; font-size:0.8rem; color: #047857;'>Inyectar: <b>${stake_fuerte:,.0f}</b></p>
                                            <h3 style='margin:10px 0 0 0; color: #10B981;'>+${utilidad_fav:,.0f}</h3>
                                            <span style='font-size:0.75rem; color:#059669; font-weight:bold;'>ROI: {roi_pct:.1f}%</span>
                                        </div>
                                        <div style='background-color: #EFF6FF; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #BFDBFE;'>
                                            <h5 style='margin:0; color: #1E3A8A;'>🔵 GANA DÉBIL</h5>
                                            <p style='margin:5px 0 0 0; font-size:0.8rem; color: #1D4ED8;'>Inyectar: <b>${stake_cobertura:,.0f}</b></p>
                                            <h3 style='margin:10px 0 0 0; color: #3B82F6;'>$0</h3>
                                            <span style='font-size:0.75rem; color:#2563EB;'>Break-Even</span>
                                        </div>
                                        <div style='background-color: #FEF2F2; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #FECACA;'>
                                            <h5 style='margin:0; color: #991B1B;'>🔴 EMPATE</h5>
                                            <p style='margin:5px 0 0 0; font-size:0.8rem; color: #B91C1C;'>El Agujero Negro</p>
                                            <h3 style='margin:10px 0 0 0; color: #EF4444;'>-${inv_total_ae:,.0f}</h3>
                                            <span style='font-size:0.75rem; color:#DC2626;'>Pérdida Total</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning("⚠️ Ajusta la cuota del Débil, no permite cobertura matemática.")

                        # ==================================================================
                        # 💰 LÓGICA DE CONFIGURACIÓN Y CUOTAS 
                        # ==================================================================
                        st.markdown("---")
                        st.markdown("#### ⚙️ Configurar Mercado y Cuotas En Vivo")
                        
                        sel_ini_rad = str(pr.get('seleccion_inicial', ''))
                        mercado_actual = str(pr.get('mercado', ''))
                        
                        if "Ambos Anotan" in mercado_actual or "Ambos" in sel_ini_rad or "Sí" in sel_ini_rad or "No" in sel_ini_rad:
                            mdo_str = "Ambos Anotan"
                            opciones_mercado = ["Sí", "No"]
                            sel_ini_limpia = "Sí" if ("Sí" in sel_ini_rad or "Si" in sel_ini_rad) else "No"
                        elif "Más" in sel_ini_rad or "Menos" in sel_ini_rad or "Goles" in mercado_actual:
                            mdo_str = "Línea de Goles"
                            import re
                            numeros = re.findall(r'\d+\.\d+|\d+', sel_ini_rad)
                            linea = numeros[0] if numeros else "2.5"
                            opciones_mercado = [f"Más de {linea}", f"Menos de {linea}"]
                            sel_ini_limpia = f"Más de {linea}" if "Más" in sel_ini_rad else f"Menos de {linea}"
                        elif "Local" in sel_ini_rad or "Visita" in sel_ini_rad or "Empate" in sel_ini_rad or "1X2" in mercado_actual:
                            mdo_str = "Mercado 1X2"
                            if "Local" in sel_ini_rad:
                                sel_ini_limpia = "Local"; opciones_mercado = ["Local", "Empate / Visita"]
                            elif "Visita" in sel_ini_rad:
                                sel_ini_limpia = "Visita"; opciones_mercado = ["Visita", "Local / Empate"]
                            else:
                                sel_ini_limpia = "Empate"; opciones_mercado = ["Empate", "Cualquiera Gana"]
                        else:
                            mdo_str = mercado_actual if mercado_actual else "Mercado Personalizado"
                            sel_ini_limpia = sel_ini_rad
                            opciones_mercado = [sel_ini_limpia, "Opción Contraria"]

                        st.info(f"💡 **Modo Disciplina:** Operando estrictamente el mercado **[{mdo_str}]** que detectó el escáner.")
                        
                        idx_defecto = 0 if sel_ini_limpia == opciones_mercado[0] else 1 if len(opciones_mercado) > 1 else 0
                        col_nom1, col_nom2 = st.columns(2)
                        with col_nom1:
                            seleccion_final_rad = st.selectbox("Tu Selección:", opciones_mercado, index=idx_defecto, key=f"sel_rad_{pr['codigo']}")
                        with col_nom2:
                            if seleccion_final_rad == opciones_mercado[0]:
                                amenaza_final_rad = opciones_mercado[1] if len(opciones_mercado) > 1 else "Opción Contraria"
                            else:
                                amenaza_final_rad = opciones_mercado[0]
                                
                            st.markdown("<p style='font-size: 14px; margin-bottom: 5px;'>La Amenaza a Cubrir (Automática):</p>", unsafe_allow_html=True)
                            st.markdown(f"""
                            <div style="background-color: #F1F5F9; border: 1px solid #CBD5E1; color: #64748B; padding: 9px 12px; border-radius: 8px; font-family: sans-serif; cursor: not-allowed; min-height: 40px; display: flex; align-items: center;">
                                {amenaza_final_rad}
                            </div>
                            """, unsafe_allow_html=True)

                        # ------------------------------------------------------------------
                        # 🧲 MEMORIA PARA QUE LAS CUOTAS NO SE BORREN AL EVALUAR
                        # ------------------------------------------------------------------
                        c_ent_key = f"c_ent_{pr['codigo']}"
                        if c_ent_key not in st.session_state:
                            st.session_state[c_ent_key] = float(pr.get('cuota_inicial', 2.0))

                        c_am_key = f"c_am_{pr['codigo']}"
                        if c_am_key not in st.session_state:
                            val_am = float(pr.get('cuota_amenaza_audit') or 1.90)
                            st.session_state[c_am_key] = val_am if val_am >= 1.01 else 1.90

                        col_ent1, col_ent2 = st.columns(2)
                        with col_ent1:
                            cuota_ent_rad = st.number_input("Cuota de tu Selección:", min_value=1.01, step=0.05, key=c_ent_key)
                        with col_ent2:
                            cuota_amenaza_rad = st.number_input("Cuota Amenaza a Cubrir:", min_value=1.01, step=0.05, key=c_am_key)

                        # ==================================================================
                        # 📸 BOTÓN DE BITÁCORA (CAPTURAR MOMENTUM + CUOTAS SI/NO)
                        # ==================================================================
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📸 Tomar Foto Táctica y Financiera", key=f"btn_foto_live_{pr['codigo']}", use_container_width=True):
                            if supabase is not None:
                                try:
                                    if seleccion_final_rad == "Sí":
                                        val_cuota_si = float(cuota_ent_rad)
                                        val_cuota_no = float(cuota_amenaza_rad)
                                    elif seleccion_final_rad == "No":
                                        val_cuota_si = float(cuota_amenaza_rad)
                                        val_cuota_no = float(cuota_ent_rad)
                                    else:
                                        val_cuota_si = 0.0
                                        val_cuota_no = 0.0

                                    nueva_foto = {
                                        "codigo_posicion": pr['codigo'],
                                        "minuto_evaluado": m_rad,
                                        "goles_local": gl_rad,
                                        "goles_vis": gv_rad,
                                        "atqt_local": atq_tot_loc, # NUEVA COLUMNA INYECTADA
                                        "atqt_vis": atq_tot_vis,   # NUEVA COLUMNA INYECTADA
                                        "atkp_local": al_rad,
                                        "atkp_vis": av_rad,
                                        "cuota_si": val_cuota_si,
                                        "cuota_no": val_cuota_no
                                    }
                                    
                                    supabase.table("registro_fotos").insert(nueva_foto).execute()
                                    st.success(f"✅ ¡Foto del min {m_rad} anclada con éxito! (SÍ: {val_cuota_si:.2f} | NO: {val_cuota_no:.2f})")
                                except Exception as e:
                                    st.error(f"❌ Error guardando foto en la base de datos: {e}")
                            else:
                                st.error("Supabase no está conectado.")

                        # ==================================================================
                        # 🎛️ SELECTOR DE PERFIL DE RIESGO
                        # ==================================================================
                        st.markdown("---")
                        st.markdown("#### 🎛️ Perfil de Riesgo Operativo")
                        perfil_riesgo = st.selectbox(
                            "Selecciona la rigidez de los candados matemáticos:",
                            ["🛡️ CONSERVADOR (Modo Francotirador)", "⚖️ MODERADO (Modo Táctico)", "🔥 AGRESIVO (Modo Kamikaze)"],
                            index=1,
                            key=f"perfil_{pr['codigo']}"
                        )
                        
                        # Asignación de variables dinámicas
                        if "CONSERVADOR" in perfil_riesgo:
                            umbral_asfixia = 0.8
                            mult_castigo = 0.10
                            umbral_gigante = 0.9
                            ventaja_min_exigida = 0.50  
                            minuto_limite_si = 70       
                        elif "MODERADO" in perfil_riesgo:
                            umbral_asfixia = 0.6
                            mult_castigo = 0.20
                            umbral_gigante = 0.7
                            ventaja_min_exigida = 0.20  
                            minuto_limite_si = 78       
                        else: # AGRESIVO
                            umbral_asfixia = 0.4
                            mult_castigo = 0.50
                            umbral_gigante = 0.5
                            ventaja_min_exigida = 0.0   
                            minuto_limite_si = 85       

                        # ==================================================================
                        # 🧠 BOTÓN DEL ORÁCULO TÁCTICO (EL NÚCLEO)
                        # ==================================================================
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🧠 Validar con Oráculo Táctico", key=f"btn_ev_{pr['codigo']}", use_container_width=True, type="primary"):
                            try:
                                import joblib
                                import pandas as pd
                                m1x2_rad = joblib.load('modelo_1x2.pkl')
                                mgoles_rad = joblib.load('modelo_goles.pkl')
                                mbtts_rad = joblib.load('modelo_btts.pkl')
                                
                                # ------------------------------------------------------------------
                                # ⚡ 1. MOTOR DE MOMENTUM
                                # ------------------------------------------------------------------
                                apm_global_loc = al_rad / max(1, m_rad)
                                apm_global_vis = av_rad / max(1, m_rad)
                                
                                apm_local_dinamico = apm_global_loc
                                apm_vis_dinamico = apm_global_vis
                                texto_momentum = "Promedio Global"
                                tiene_momentum = False
                                
                                if supabase is not None:
                                    try:
                                        res_last = supabase.table("registro_fotos").select("*").eq("codigo_posicion", pr['codigo']).lt("minuto_evaluado", m_rad).order("minuto_evaluado", desc=True).limit(1).execute()
                                        if res_last.data:
                                            foto_ant = res_last.data[0]
                                            min_ant = int(foto_ant['minuto_evaluado'])
                                            delta_min = m_rad - min_ant
                                            if delta_min >= 2:
                                                atk_l_ant = int(foto_ant['atkp_local'])
                                                atk_v_ant = int(foto_ant['atkp_vis'])
                                                apm_local_dinamico = max(0.0, (al_rad - atk_l_ant) / delta_min)
                                                apm_vis_dinamico = max(0.0, (av_rad - atk_v_ant) / delta_min)
                                                texto_momentum = f"Últimos {delta_min} min"
                                                tiene_momentum = True
                                    except:
                                        pass

                                # ------------------------------------------------------------------
                                # ⚖️ 2. MAPEO DE VARIABLES TÁCTICAS
                                # ------------------------------------------------------------------
                                c_loc_hist = float(pr.get('cuota_base_audit', 2.0))
                                c_vis_hist = float(pr.get('cuota_amenaza_audit', 2.0))
                                
                                if c_loc_hist <= 1.35 or c_vis_hist <= 1.35: 
                                    jerarquia_pre = "Súper Favorito"
                                elif (c_loc_hist < c_vis_hist and (c_vis_hist - c_loc_hist) > 0.3) or (c_vis_hist < c_loc_hist and (c_loc_hist - c_vis_hist) > 0.3): 
                                    jerarquia_pre = "Favorito"
                                else: 
                                    jerarquia_pre = "Fuerzas Parejas"

                                fav_es_loc = (c_loc_hist < c_vis_hist and (c_vis_hist - c_loc_hist) > 0.3)
                                fav_es_vis = (c_vis_hist < c_loc_hist and (c_loc_hist - c_vis_hist) > 0.3)

                                min_corrido = m_rad
                                estado_goles = (gl_rad + gv_rad) > 0
                                
                                tp_local = al_rad / atq_tot_loc if atq_tot_loc > 0 else 0.0
                                tp_visita = av_rad / atq_tot_vis if atq_tot_vis > 0 else 0.0

                                if fav_es_loc:
                                    goles_fav, goles_deb = gl_rad, gv_rad
                                    apm_global_fav, apm_global_deb = apm_global_loc, apm_global_vis
                                    mom_fav, mom_deb = apm_local_dinamico, apm_vis_dinamico
                                    tp_fav, tp_deb = tp_local, tp_visita
                                elif fav_es_vis:
                                    goles_fav, goles_deb = gv_rad, gl_rad
                                    apm_global_fav, apm_global_deb = apm_global_vis, apm_global_loc
                                    mom_fav, mom_deb = apm_vis_dinamico, apm_local_dinamico
                                    tp_fav, tp_deb = tp_visita, tp_local
                                else:
                                    goles_fav = goles_deb = apm_global_fav = apm_global_deb = mom_fav = mom_deb = tp_fav = tp_deb = 0

                                if gl_rad > gv_rad:
                                    lider_marcador = "No Favorito" if fav_es_vis else "Favorito"
                                    goles_ganador, goles_perdedor = gl_rad, gv_rad
                                    apm_g_ganador, apm_g_perdedor = apm_global_loc, apm_global_vis
                                    mom_ganador, mom_perdedor = apm_local_dinamico, apm_vis_dinamico
                                    tp_ganador, tp_perdedor = tp_local, tp_visita
                                elif gv_rad > gl_rad:
                                    lider_marcador = "No Favorito" if fav_es_loc else "Favorito"
                                    goles_ganador, goles_perdedor = gv_rad, gl_rad
                                    apm_g_ganador, apm_g_perdedor = apm_global_vis, apm_global_loc
                                    mom_ganador, mom_perdedor = apm_vis_dinamico, apm_local_dinamico
                                    tp_ganador, tp_perdedor = tp_visita, tp_local
                                else:
                                    lider_marcador = "Empate"
                                    goles_ganador = goles_perdedor = apm_g_ganador = apm_g_perdedor = mom_ganador = mom_perdedor = tp_ganador = tp_perdedor = 0

                                mom_combinado = apm_local_dinamico + apm_vis_dinamico
                                diferencial_mom = abs(apm_local_dinamico - apm_vis_dinamico)

                                # ------------------------------------------------------------------
                                # 🔍 3. ESCÁNER DE PATRONES MATEMÁTICOS (SÍ y NO DEFINITIVO)
                                # ------------------------------------------------------------------
                                def detectar_patron_btts_si(mc, eg, lm, gf, gd, jp, agf, agd, agg, agp, m_comb, d_mom, 
                                                            mpg_f, mpg_d, mpg_g, mpg_p, tp_f, tp_d, tp_g, tp_p):
                                    if (mc <= 45 and eg == True and jp in ["Favorito", "Súper Favorito"] and lm == "No Favorito" and gd == 1 and mpg_f > 1.0 and mpg_d < 0.4 and d_mom > 0.7 and tp_f > 0.40):
                                        return "🟢 EL TIGRE HERIDO: Favorito pierde 0-1 pero asedia brutalmente (Mom > 1.0) y con profundidad (TP > 40%). LUZ VERDE SÍ."
                                    elif (mc <= 45 and eg == True and jp in ["Favorito", "Súper Favorito"] and lm == "Favorito" and gf == 1 and gd == 0 and agf < 0.6 and agd > 0.8 and mpg_f < 0.4 and mpg_d > 0.8 and tp_d > 0.40):
                                        return "🟢 LA REBELDÍA: Favorito gana 1-0 y se durmió. El Débil asedia con furia (Mom > 0.8) y verticalidad (TP > 40%). LUZ VERDE SÍ."
                                    elif (mc <= 45 and eg == True and jp == "Fuerzas Parejas" and (goles_ganador == 1 and goles_perdedor == 0) and agg > 0.7 and agp > 0.8 and m_comb >= 1.5 and d_mom < 0.2 and mpg_p > 0.9 and tp_g > 0.35 and tp_p > 0.35):
                                        return "🟢 DEVOLUCIÓN RÁPIDA: Partido parejo 1-0. Intercambio de golpes intenso y ambos llegan con peligro (TP > 35%). LUZ VERDE SÍ."
                                    elif (mc <= 45 and eg == True and jp in ["Favorito", "Súper Favorito"] and lm == "Favorito" and gf >= 2 and gd == 0 and agf < 0.6 and agd > 0.8 and mpg_d > 1.0 and tp_d > 0.45):
                                        return "🟢 DESCUENTO POR RELAJACIÓN: Favorito golea 2-0 y bajó los brazos. El Débil ataca furioso y profundo (TP > 45%). LUZ VERDE SÍ."
                                    return None

                                def detectar_patron_btts_no(mc, eg, jp, gf, gd, agf, agd, mf, md, tf, td):
                                    # 🧱 PATRÓN NO #1: EL MURO INFRANQUEABLE (El Débil no existe)
                                    if (mc >= 30 and jp in ["Favorito", "Súper Favorito"] and gd == 0 and agd < 0.35 and md < 0.3 and td < 0.20):
                                        return "🔴 EL MURO: El Débil está asfixiado. Sin momentum (Mom < 0.3) ni profundidad (TP < 20%). LUZ VERDE NO."
                                    # 💤 PATRÓN NO #2: PACTO DE NO AGRESIÓN (Fuerzas Parejas Bloqueadas)
                                    elif (mc >= 30 and jp == "Fuerzas Parejas" and agf < 0.55 and agd < 0.55 and mf < 0.5 and md < 0.5 and tf < 0.30 and td < 0.30):
                                        return "🔴 PACTO DE NO AGRESIÓN: Ambos equipos anulados en el medio campo (APM < 0.55). Poca verticalidad. LUZ VERDE NO."
                                    # 🏥 PATRÓN NO #3: EL DOMINIO ESTÉRIL (Mucho ruido, cero peligro)
                                    elif (mc >= 35 and eg == False and tf < 0.25 and td < 0.25):
                                        return "🔴 DOMINIO ESTÉRIL: 0-0 con posesiones largas pero bajísima profundidad en ambos (TP < 25%). LUZ VERDE NO."
                                    return None

                                patron_encontrado = None
                                color_patron = "#10B981"
                                bg_patron = "#ECFDF5"
                                titulo_patron = "🏆 PATRÓN MATEMÁTICO DETECTADO (BTTS SÍ)"

                                # Ejecutamos el escáner correcto según la elección del usuario en el Radar
                                if seleccion_final_rad == "Sí":
                                    patron_encontrado = detectar_patron_btts_si(
                                        min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
                                        jerarquia_pre, apm_global_fav, apm_global_deb, apm_g_ganador, apm_g_perdedor,
                                        mom_combinado, diferencial_mom, 
                                        mom_fav, mom_deb, mom_ganador, mom_perdedor, 
                                        tp_fav, tp_deb, tp_ganador, tp_perdedor
                                    )
                                elif seleccion_final_rad == "No":
                                    patron_encontrado = detectar_patron_btts_no(
                                        min_corrido, estado_goles, jerarquia_pre, goles_fav, goles_deb, 
                                        apm_global_fav, apm_global_deb, mom_fav, mom_deb, tp_fav, tp_deb
                                    )
                                    if patron_encontrado:
                                        color_patron = "#EF4444" 
                                        bg_patron = "#FEF2F2"
                                        titulo_patron = "🛡️ PATRÓN DEFENSIVO DETECTADO (BTTS NO)"

                                # RENDERIZAR RESULTADO DEL ESCÁNER (ALERTA GIGANTE)
                                if patron_encontrado:
                                    st.markdown(f"""
                                    <div style="background-color: {bg_patron}; border-left: 6px solid {color_patron}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                                        <h3 style="margin-top:0; color:{color_patron};">{titulo_patron}</h3>
                                        <p style="margin:0; font-size:1.05rem; color:#1F2937;">{patron_encontrado}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                # ------------------------------------------------------------------
                                # 🤖 4. PREDICCIÓN DE MODELOS ML (EL FLUJO ORIGINAL)
                                # ------------------------------------------------------------------
                                apm_rad = apm_local_dinamico + apm_vis_dinamico
                                ird_rad_global = min(100.0, (apm_global_loc + apm_global_vis) * 45.0)
                                
                                X_rad = pd.DataFrame([{
                                    'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad,
                                    'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad_global,
                                    'cuota_base_audit': float(pr.get('cuota_base_audit', 2.0)), 
                                    'cuota_amenaza_audit': float(pr.get('cuota_amenaza_audit', 2.0))
                                }])
                                
                                pred_1x2_rad = m1x2_rad.predict(X_rad)[0]
                                pred_goles_rad = mgoles_rad.predict(X_rad)[0]
                                pred_btts_rad = mbtts_rad.predict(X_rad)[0]
                                
                                probabilidades = mbtts_rad.predict_proba(X_rad)[0]
                                prob_no = probabilidades[0]
                                prob_si = probabilidades[1]

                                # ------------------------------------------------------------------
                                # 🛡️ FILTRO DE SENTIDO COMÚN: SINCRONIZAR PLATA CON FÍSICA
                                # ------------------------------------------------------------------
                                if (apm_local_dinamico < umbral_asfixia and gl_rad == 0) or (apm_vis_dinamico < umbral_asfixia and gv_rad == 0):
                                    prob_si = prob_si * mult_castigo
                                    prob_no = 1.0 - prob_si
                                elif apm_local_dinamico >= 1.0 and apm_vis_dinamico >= 1.0:
                                    prob_si = min(0.95, prob_si * 1.50)
                                    prob_no = 1.0 - prob_si

                                # REFUERZO DE PROBABILIDAD SEGÚN EL PATRÓN ENCONTRADO
                                if patron_encontrado:
                                    if seleccion_final_rad == "Sí":
                                        prob_si = min(0.99, prob_si * 1.5) 
                                        prob_no = 1.0 - prob_si
                                    elif seleccion_final_rad == "No":
                                        prob_no = min(0.99, prob_no * 1.5)
                                        prob_si = 1.0 - prob_no

                                winner_tactico = "Empate" if pred_1x2_rad == 1 else ("Local" if pred_1x2_rad == 2 else "Visita")
                                btts = "SÍ" if pred_btts_rad == 1 else "NO"
                                color_btts = "#10B981" if pred_btts_rad == 1 else "#EF4444"
                                
                                # ------------------------------------------------------------------
                                # ⚖️ 5. RECONSTRUCCIÓN DE JERARQUÍA PARA LA UI
                                # ------------------------------------------------------------------
                                if jerarquia_pre == "Súper Favorito":
                                    jerarquia = f"👑 Súper Favorito: {eq_loc_ui if fav_es_loc else eq_vis_ui}"
                                elif jerarquia_pre == "Favorito":
                                    jerarquia = f"⚔️ Favorito: {eq_loc_ui if fav_es_loc else eq_vis_ui}"
                                else: 
                                    jerarquia = "⚖️ Fuerzas Parejas"

                                if apm_local_dinamico > apm_vis_dinamico and (apm_local_dinamico - apm_vis_dinamico) > 0.4: dom_vivo = eq_loc_ui
                                elif apm_vis_dinamico > apm_local_dinamico and (apm_vis_dinamico - apm_local_dinamico) > 0.4: dom_vivo = eq_vis_ui
                                else: dom_vivo = "Asedio Dividido"

                                # ------------------------------------------------------------------
                                # 🎯 3. SEÑALES TÁCTICAS CLÁSICAS
                                # ------------------------------------------------------------------
                                goles_actuales_totales = gl_rad + gv_rad
                                alerta_señal = ""
                                fav_es_local = "Local" in jerarquia
                                fav_es_visita = "Visita" in jerarquia
                                
                                if tiene_momentum:
                                    if (fav_es_local and gv_rad == 1 and gl_rad == 0 and apm_local_dinamico >= umbral_gigante) or \
                                       (fav_es_visita and gl_rad == 1 and gv_rad == 0 and apm_vis_dinamico >= umbral_gigante):
                                        equipo_atacando = eq_loc_ui if fav_es_local else eq_vis_ui
                                        alerta_señal = f"""
                                        <div style="background-color: #F0FDF4; border-left: 6px solid #16A34A; padding: 15px; border-radius: 4px; margin-bottom: 15px; text-align: left;">
                                            <h4 style="margin-top:0; color:#15803D;">🔥 SEÑAL TÁCTICA: EL GIGANTE HERIDO</h4>
                                            <p style="margin:0; font-size: 0.95rem; color:#14532D;">
                                            El débil anotó, pero el Favorito ({equipo_atacando}) cruzó tu umbral táctico con ({max(apm_local_dinamico, apm_vis_dinamico):.2f} APM recientes). Altísima probabilidad de empate inminente.
                                            </p>
                                        </div>
                                        """
                                    elif (fav_es_local and gl_rad == 1 and gv_rad == 0 and apm_local_dinamico >= umbral_gigante and apm_vis_dinamico <= umbral_asfixia) or \
                                         (fav_es_visita and gv_rad == 1 and gl_rad == 0 and apm_vis_dinamico >= umbral_gigante and apm_local_dinamico <= umbral_asfixia):
                                        equipo_asfixiado = eq_vis_ui if fav_es_local else eq_loc_ui
                                        alerta_señal = f"""
                                        <div style="background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 15px; border-radius: 4px; margin-bottom: 15px; text-align: left;">
                                            <h4 style="margin-top:0; color:#991B1B;">🛡️ SEÑAL TÁCTICA: ASFIXIA TOTAL</h4>
                                            <p style="margin:0; font-size: 0.95rem; color:#7F1D1D;">
                                            El Favorito anotó y no quita el pie del acelerador. El equipo {equipo_asfixiado} está completamente anulado para tu Perfil ({min(apm_local_dinamico, apm_vis_dinamico):.2f} APM). Escenario letal para el SÍ.
                                            </p>
                                        </div>
                                        """
                                    elif m_rad <= 45 and goles_actuales_totales == 0:
                                        if apm_local_dinamico >= 1.0 or apm_vis_dinamico >= 1.0:
                                            atacante_fuerte = eq_loc_ui if apm_local_dinamico > apm_vis_dinamico else eq_vis_ui
                                            es_favorito = True if atacante_fuerte in jerarquia else False
                                            texto_riesgo = "Favorito presionando con furia" if es_favorito else "Peligro de sorpresa del Débil"
                                            
                                            alerta_señal = f"""
                                            <div style="background-color: #FFFBEB; border-left: 6px solid #D97706; padding: 15px; border-radius: 4px; margin-bottom: 15px; text-align: left;">
                                                <h4 style="margin-top:0; color:#B45309;">⚡ SEÑAL DE MOMENTUM: GOL INMINENTE (1T)</h4>
                                                <p style="margin:0; font-size: 0.95rem; color:#92400E;">
                                                El equipo {atacante_fuerte} bombardea el arco ({max(apm_local_dinamico, apm_vis_dinamico):.2f} APM). {texto_riesgo}.
                                                </p>
                                            </div>
                                            """

                                if alerta_señal: st.markdown(alerta_señal, unsafe_allow_html=True)

                                # ------------------------------------------------------------------
                                # 🎯 4. CÁLCULO DE MARCADOR VISUAL
                                # ------------------------------------------------------------------
                                goles_nuevos_esperados = max(0, round(pred_goles_rad) - goles_actuales_totales)
                                calc_loc, calc_vis = gl_rad, gv_rad

                                if pred_1x2_rad == 1: 
                                    if calc_loc > calc_vis: calc_vis = calc_loc 
                                    elif calc_vis > calc_loc: calc_loc = calc_vis 
                                    elif goles_nuevos_esperados >= 2:
                                        calc_loc += (goles_nuevos_esperados // 2)
                                        calc_vis += (goles_nuevos_esperados // 2)
                                elif pred_1x2_rad == 2:
                                    if calc_loc <= calc_vis: calc_loc = calc_vis + max(1, goles_nuevos_esperados)
                                    else: calc_loc += goles_nuevos_esperados
                                else:
                                    if calc_vis <= calc_loc: calc_vis = calc_loc + max(1, goles_nuevos_esperados)
                                    else: calc_vis += goles_nuevos_esperados

                                if apm_global_loc >= 0.6 and apm_global_vis >= 0.6:
                                    calc_loc = max(1, calc_loc)
                                    calc_vis = max(1, calc_vis)
                                    btts = "SÍ (Alta Prob. Física)"
                                    color_btts = "#10B981"
                                elif apm_global_loc < 0.4 or apm_global_vis < 0.4:
                                    btts = "NO (Falta Asedio)"
                                    color_btts = "#EF4444"
                                    if apm_global_loc < 0.4 and gl_rad == 0: calc_loc = 0
                                    if apm_global_vis < 0.4 and gv_rad == 0: calc_vis = 0
                                else:
                                    if pred_btts_rad == 1:
                                        calc_loc = max(1, calc_loc)
                                        calc_vis = max(1, calc_vis)
                                        btts = "SÍ (Proyectado IA)"
                                        color_btts = "#10B981"
                                    else:
                                        btts = "NO (Proyectado IA)"
                                        color_btts = "#EF4444"
                                        
                                marcador_exacto = f"{calc_loc} - {calc_vis}"
                                if calc_loc > 0 and calc_vis > 0:
                                    btts = "SÍ"
                                    color_btts = "#10B981"
                                else:
                                    btts = "NO (Bloqueado por Táctica)" if pred_btts_rad == 1 else "NO"
                                    color_btts = "#EF4444"

                                st.markdown(f"""
                                <div style="background-color: #1E293B; border-bottom: 4px solid #3B82F6; padding: 10px; border-radius: 8px 8px 0 0; text-align: center; margin-bottom: 0px;">
                                    <h4 style="margin:0; color:#94A3B8; font-size: 0.9rem;">ADN DEL PARTIDO</h4>
                                    <h3 style="color:#FFFFFF; margin: 5px 0;">[{jerarquia}]</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                color_winner = "#0EA5E9" if winner_tactico == "Local" else ("#F59E0B" if winner_tactico == "Empate" else "#8B5CF6")
                                st.markdown(f"""
                                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; margin-bottom: 15px;">
                                    <h3 style="margin-top:0; color:#0F172A;">🎯 PROYECCIÓN TÁCTICA</h3>
                                    <h1 style="color:{color_winner}; font-size: 2.5rem; margin: 10px 0;">{marcador_exacto}</h1>
                                    <p style="margin:0; font-size: 1.1rem; color:#475569;">Ganador Físico: <b>{winner_tactico}</b></p>
                                    <p style="margin:5px 0 0 0; font-size: 0.85rem; color:#64748B;">El <b>{dom_vivo}</b> está dominando la cancha (IRD: {ird_rad_global:.1f}%)</p>
                                </div>
                                """, unsafe_allow_html=True)

                                # ------------------------------------------------------------------
                                # 💎 DICTAMEN DE TRADING Y VALUE BETTING
                                # ------------------------------------------------------------------
                                aprueba_key = f"oraculo_aprueba_{pr['codigo']}"
                                perfil_aprobado_key = f"perfil_evaluado_{pr['codigo']}"

                                if mdo_str == "Ambos Anotan":
                                    cuota_justa_si = 1 / prob_si if prob_si > 0.01 else 99.0
                                    cuota_justa_no = 1 / prob_no if prob_no > 0.01 else 99.0
                                    
                                    if seleccion_final_rad == "Sí":
                                        cuota_act_si = st.session_state.get(c_ent_key, cuota_ent_rad)
                                        ventaja = cuota_act_si - cuota_justa_si
                                        prob_mercado = prob_si
                                        cuota_justa = cuota_justa_si
                                        
                                        if m_rad >= minuto_limite_si:
                                            alerta_accion = f"⏳ **BLOQUEO POR RELOJ (LOTERÍA)**"
                                            texto_accion = f"Tu Perfil {perfil_riesgo.split(' ')[1]} prohíbe apostar a goles después del minuto {minuto_limite_si}."
                                            bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
                                        elif ventaja >= ventaja_min_exigida:
                                            alerta_accion = f"🔥 **¡DISPARA AL SÍ AHORA!**"
                                            texto_accion = f"La cuota justa es **{cuota_justa:.2f}** y te ofrecen **{cuota_act_si:.2f}**. Entra ya."
                                            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
                                            # 🟢 LUZ VERDE Y MEMORIA DE RIESGO
                                            st.session_state[aprueba_key] = True 
                                            st.session_state[perfil_aprobado_key] = perfil_riesgo
                                        elif ventaja >= 0:
                                            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
                                            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil {perfil_riesgo.split(' ')[1]} exige ganancia superior."
                                            bg_color = "#F8FAFC"; border_color = "#64748B"; text_color = "#334155"
                                        else:
                                            if (cuota_justa - cuota_act_si) <= 0.40 and m_rad < 75:
                                                alerta_accion = f"⏳ **PACIENCIA (ESPERA A QUE SUBA EL SÍ)**"
                                                texto_accion = f"Pagan muy poco (**{cuota_act_si:.2f}**). La cuota justa es **{cuota_justa:.2f}**. Espera."
                                                bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
                                            else:
                                                alerta_accion = f"🚫 **DESCARTADO (TRAMPA EN EL SÍ)**"
                                                texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_act_si:.2f}**. Aborta."
                                                bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
                                                
                                    else: # Seleccionó "No"
                                        cuota_act_no = st.session_state.get(c_ent_key, cuota_ent_rad)
                                        ventaja = cuota_act_no - cuota_justa_no
                                        prob_mercado = prob_no
                                        cuota_justa = cuota_justa_no
                                        
                                        if ventaja >= ventaja_min_exigida:
                                            alerta_accion = f"🛡️ **¡DISPARA AL NO AHORA!**"
                                            texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_act_no:.2f}**. ¡Mete la plata YA!"
                                            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
                                            # 🟢 LUZ VERDE Y MEMORIA DE RIESGO
                                            st.session_state[aprueba_key] = True 
                                            st.session_state[perfil_aprobado_key] = perfil_riesgo
                                        elif ventaja >= 0:
                                            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
                                            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige mayor margen."
                                            bg_color = "#F8FAFC"; border_color = "#64748B"; text_color = "#334155"
                                        else:
                                            alerta_accion = f"🚫 **LLEGASTE TARDE AL NO**"
                                            texto_accion = f"Cuota justa era **{cuota_justa:.2f}** y ya la tumbaron a **{cuota_act_no:.2f}**. Pérdida matemática."
                                            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
                                            
                                    st.markdown(f"""
                                    <div style="background-color: {bg_color}; border-left: 6px solid {border_color}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                                        <h3 style="margin-top:0; color:{border_color};">{alerta_accion}</h3>
                                        <p style="margin:0; font-size:1.05rem; color:{text_color};">{texto_accion}</p>
                                        <hr style="border-color:{border_color}; opacity:0.3; margin: 10px 0;">
                                        <div style="font-size:0.9rem; color:#475569; display:flex; justify-content:space-between;">
                                            <span><b>Prob. IA {seleccion_final_rad.upper()}:</b> {prob_mercado*100:.1f}%</span>
                                            <span><b>Velocidad:</b> {apm_rad:.2f} APM ({texto_momentum})</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.markdown("---")
                                else:
                                    # Para otros mercados (1X2, Goles), aprobamos directo y guardamos el perfil
                                    st.session_state[aprueba_key] = True
                                    st.session_state[perfil_aprobado_key] = perfil_riesgo

                            except Exception as e:
                                st.error(f"Error procesando IA táctica: {e}")

                        # ==================================================================
                        # 💵 DECISIÓN DE CAPITAL Y AUDITORÍA DE CUPO (POST-ANÁLISIS)
                        # ==================================================================
                        aprueba_key = f"oraculo_aprueba_{pr['codigo']}"
                        
                        # EL ESCUDO MAESTRO: Si no hay luz verde, no se abre la bóveda
                        if not st.session_state.get(aprueba_key, False):
                            st.warning("🛑 BÓVEDA CERRADA: Presiona '🧠 Validar con Oráculo Táctico'. Solo podrás inyectar capital si obtienes LUZ VERDE. 🛡️")
                        else:
                            st.markdown("---")
                            st.markdown("#### 💰 Decisión de Capital a Invertir")
                            
                            # Leemos qué perfil fue el que autorizó la bóveda
                            perfil_evaluado_guardado = st.session_state.get(f"perfil_evaluado_{pr['codigo']}", "MODERADO")
                            es_kamikaze = "AGRESIVO" in perfil_evaluado_guardado
                            es_moderado = "MODERADO" in perfil_evaluado_guardado
                            es_conservador = "CONSERVADOR" in perfil_evaluado_guardado
                            
                            # Extrae el código exacto (Ej: SCAN-9934)
                            partes_codigo = pr['codigo'].split("-")
                            codigo_base_exacto = f"{partes_codigo[0]}-{partes_codigo[1]}" if len(partes_codigo) >= 2 else pr['codigo']
                            
                            capital_ya_investido = 0.0
                            inversiones_previas = []

                            if supabase is not None:
                                try:
                                    res_exp = supabase.table("historial_trading").select("stake_1").like("codigo", f"{codigo_base_exacto}%").in_("estado", ["EN VIVO", "ABIERTA"]).execute()
                                    if res_exp.data:
                                        inversiones_previas = [float(x.get('stake_1', 0.0)) for x in res_exp.data if float(x.get('stake_1', 0.0)) > 0]
                                        capital_ya_investido = sum(inversiones_previas)
                                except Exception:
                                    capital_ya_investido = 0.0

                            # ✅ EL PRESUPUESTO FIJO: Toma exactamente el capital que asignaste tú, no calcula el 5% de nada
                            presupuesto_partido = float(pr.get('capital_total', 5000.0))
                            cupo_disponible_partido = max(0.0, presupuesto_partido - capital_ya_investido)

                            st.markdown(f"""
                            <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 0.85rem; color: #64748B;">Presupuesto Asignado:</span><br>
                                    <b style="color: #1E293B; font-size: 1.05rem;">${presupuesto_partido:,.0f} COP</b>
                                </div>
                                <div>
                                    <span style="font-size: 0.85rem; color: #64748B;">Capital Comprometido:</span><br>
                                    <b style="color: #D97706; font-size: 1.05rem;">${capital_ya_investido:,.0f} COP</b>
                                </div>
                                <div>
                                    <span style="font-size: 0.85rem; color: #64748B;">Cupo Disponible:</span><br>
                                    <b style="color: {'#10B981' if cupo_disponible_partido > 0 else '#EF4444'}; font-size: 1.05rem;">${cupo_disponible_partido:,.0f} COP</b>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            stk_key = f"stk_ent_cap_{pr['codigo']}"

                            modo_gestion = st.radio(
                                "⚙️ Modo de Asignación de Capital:",
                                ["🔓 Libre (Todo el cupo disponible)", "🔒 Control Total (Limitar por nivel de riesgo)"],
                                horizontal=True,
                                key=f"modo_cap_{pr['codigo']}"
                            )
                            
                            bolsas_teoricas = {
                                "kamikaze": presupuesto_partido * 0.20,
                                "moderado": presupuesto_partido * 0.30,
                                "conservador": presupuesto_partido * 0.50
                            }
                            
                            usado_kam, usado_mod, usado_con = False, False, False
                            
                            for inv in inversiones_previas:
                                dist = {}
                                if not usado_kam: dist["kamikaze"] = abs(inv - bolsas_teoricas["kamikaze"])
                                if not usado_mod: dist["moderado"] = abs(inv - bolsas_teoricas["moderado"])
                                if not usado_con: dist["conservador"] = abs(inv - bolsas_teoricas["conservador"])
                                if dist:
                                    mejor = min(dist, key=dist.get)
                                    if mejor == "kamikaze": usado_kam = True
                                    elif mejor == "moderado": usado_mod = True
                                    elif mejor == "conservador": usado_con = True

                            val_kamikaze = 0.0 if usado_kam else bolsas_teoricas["kamikaze"]
                            val_moderado = 0.0 if usado_mod else bolsas_teoricas["moderado"]
                            val_conservador = 0.0 if usado_con else bolsas_teoricas["conservador"]

                            limite_final_inversion = cupo_disponible_partido
                            
                            if "Control Total" in modo_gestion:
                                opciones_permitidas = []
                                if es_kamikaze: opciones_permitidas.append(f"🔥 Kamikaze (Max 20%) {'- AGOTADO' if usado_kam else ''}")
                                if es_moderado: opciones_permitidas.append(f"⚖️ Moderado (Max 30%) {'- AGOTADO' if usado_mod else ''}")
                                if es_conservador: opciones_permitidas.append(f"🛡️ Conservador (Max 50%) {'- AGOTADO' if usado_con else ''}")
                                
                                tipo_entrada = st.selectbox(
                                    "Nivel de riesgo AUTORIZADO por el Oráculo:",
                                    opciones_permitidas,
                                    key=f"tipo_ent_{pr['codigo']}"
                                )
                                if "Kamikaze" in tipo_entrada: limite_final_inversion = min(cupo_disponible_partido, val_kamikaze)
                                elif "Moderado" in tipo_entrada: limite_final_inversion = min(cupo_disponible_partido, val_moderado)
                                else: limite_final_inversion = min(cupo_disponible_partido, val_conservador)

                            col_btn_k1, col_btn_k2, col_btn_k3 = st.columns(3)
                            with col_btn_k1:
                                if st.button(f"🔥 Kamikaze\n${bolsas_teoricas['kamikaze']:,.0f}", key=f"btn_kam_{pr['codigo']}", use_container_width=True, disabled=usado_kam or cupo_disponible_partido <= 0 or not es_kamikaze):
                                    st.session_state[stk_key] = float(min(val_kamikaze, cupo_disponible_partido))
                            with col_btn_k2:
                                if st.button(f"⚖️ Moderado\n${bolsas_teoricas['moderado']:,.0f}", key=f"btn_mod_{pr['codigo']}", use_container_width=True, disabled=usado_mod or cupo_disponible_partido <= 0 or not es_moderado):
                                    st.session_state[stk_key] = float(min(val_moderado, cupo_disponible_partido))
                            with col_btn_k3:
                                if st.button(f"🛡️ Conservador\n${bolsas_teoricas['conservador']:,.0f}", key=f"btn_cons_{pr['codigo']}", use_container_width=True, disabled=usado_con or cupo_disponible_partido <= 0 or not es_conservador):
                                    st.session_state[stk_key] = float(min(val_conservador, cupo_disponible_partido))

                            if stk_key not in st.session_state:
                                st.session_state[stk_key] = float(min(pr.get('stake_1', 1000.0), max(1.0, limite_final_inversion)))

                            if st.session_state[stk_key] > limite_final_inversion:
                                st.session_state[stk_key] = float(limite_final_inversion)

                            if limite_final_inversion <= 0:
                                st.error("🚨 Cupo agotado para el modo seleccionado. Estás protegido.")
                                stake_ent_rad = 0.0
                            else:
                                stake_ent_rad = st.number_input(
                                    f"Capital a Invertir (Max ${limite_final_inversion:,.0f}):",
                                    min_value=100.0,
                                    max_value=float(limite_final_inversion),
                                    step=500.0,
                                    key=stk_key,
                                    format="%.2f"
                                )
                                    
                            # ==================================================================
                            # ⚙️ MÓDULO FINAL DE RIESGO Y DISPARO
                            # ==================================================================
                            lista_casas = ["BetPlay", "Wplay", "Rushbet", "Codere", "Yajuego", "Zamba", "Sportium", "Megapuesta", "Bwin Colombia", "Bet365", "1xBet", "Betfair", "Pinnacle", "Stake", "Otra"]
                            plat_previa = pr.get('plataforma_inicial', 'BetPlay')
                            idx_plat = lista_casas.index(plat_previa) if plat_previa in lista_casas else 0
                            
                            col_plat1, col_plat2 = st.columns(2)
                            with col_plat1:
                                plat_rad_sel = st.selectbox("Casa de Apuestas (Entrada):", lista_casas, index=idx_plat, key=f"plat_{pr['codigo']}")
                            with col_plat2:
                                if plat_rad_sel == "Otra":
                                    plat_rad_final = st.text_input("Especifica la plataforma:", key=f"otra_{pr['codigo']}")
                                else:
                                    plat_rad_final = plat_rad_sel
                                    st.write("")

                            retorno_bruto_esperado = stake_ent_rad * cuota_ent_rad
                            utilidad_max_posible = retorno_bruto_esperado - stake_ent_rad
                            max_roi_pct = (utilidad_max_posible / stake_ent_rad) * 100 if stake_ent_rad > 0 else 0
                            
                            if max_roi_pct > 0:
                                col_lim1, col_lim2 = st.columns(2)
                                with col_lim1:
                                    tp_rad = st.slider("Utilidad Deseada (Take Profit):", min_value=1.0, max_value=max(1.0, float(max_roi_pct - 0.5)), value=min(5.0, max(1.0, float(max_roi_pct / 2))), step=0.5, format="%.1f%%", key=f"tp_{pr['codigo']}")
                                with col_lim2:
                                    sl_rad = st.slider("Pérdida Máxima (Stop Loss):", min_value=1.0, max_value=100.0, value=20.0, step=1.0, format="%.1f%%", key=f"sl_{pr['codigo']}")
                                
                                utilidad_objetivo_dinero = stake_ent_rad * (tp_rad / 100.0)
                                inyeccion_necesaria_tp = utilidad_max_posible - utilidad_objetivo_dinero
                                cuota_cazar_rad = retorno_bruto_esperado / inyeccion_necesaria_tp if inyeccion_necesaria_tp > 0 else 0
                                
                                perdida_maxima = stake_ent_rad * (sl_rad / 100.0)
                                inyeccion_necesaria_sl = utilidad_max_posible + perdida_maxima
                                cuota_sl_rad = retorno_bruto_esperado / inyeccion_necesaria_sl
                                
                                st.markdown(f"""
                                <div style="display:flex; justify-content:space-around; background-color: #F8FAFC; padding: 10px; border-radius: 5px;">
                                    <span style="color:#15803D;">🟢 <b>Take Profit:</b> Cuota {cuota_cazar_rad:.2f}</span>
                                    <span style="color:#B91C1C;">🔴 <b>Stop Loss:</b> Cuota {cuota_sl_rad:.2f}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.warning("La cuota de entrada no permite generar utilidades.")
                                cuota_cazar_rad = 0; cuota_sl_rad = 0
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            banca_ejecutar = st.radio("Entorno de ejecución definitivo:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True, key=f"banca_{pr['codigo']}")
                            banca_activa_rad = "REAL" if "Real" in banca_ejecutar else "SIMULACION"
                            
                            retener_radar = st.checkbox("🔄 Retener partido en el Radar tras disparar", value=True, key=f"chk_retener_{pr['codigo']}")
                            
                            if st.button("🔥 DISPARAR (Confirmar Entrada)", type="primary", key=f"btn_disp_{pr['codigo']}", use_container_width=True):
                                if cuota_cazar_rad > 0 and plat_rad_final:
                                    import datetime
                                    import joblib
                                    import pandas as pd
                                    
                                    try:
                                        m1x2_rad = joblib.load('modelo_1x2.pkl')
                                        mgoles_rad = joblib.load('modelo_goles.pkl')
                                        mbtts_rad = joblib.load('modelo_btts.pkl')
                                        
                                        apm_rad = (al_rad + av_rad) / max(1, m_rad)
                                        ird_rad = min(100.0, apm_rad * 45.0)
                                        
                                        X_rad = pd.DataFrame([{
                                            'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad, 'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad, 'cuota_base_audit': float(pr.get('cuota_base_audit', 2.0)), 'cuota_amenaza_audit': float(pr.get('cuota_amenaza_audit', 2.0))}])
                                        
                                        pred_1x2_testigo = m1x2_rad.predict(X_rad)[0]
                                        pred_goles_testigo = mgoles_rad.predict(X_rad)[0]
                                        pred_btts_testigo = mbtts_rad.predict(X_rad)[0]
                                        
                                        g_totales_actuales = gl_rad + gv_rad
                                        g_nuevos_esp = max(0, round(pred_goles_testigo) - g_totales_actuales)
                                        
                                        c_loc, c_vis = gl_rad, gv_rad
                                        if pred_1x2_testigo == 1: 
                                            if c_loc > c_vis: c_vis = c_loc 
                                            elif c_vis > c_loc: c_loc = c_vis 
                                            elif g_nuevos_esp >= 2: c_loc += 1; c_vis += 1
                                        elif pred_1x2_testigo == 2:
                                            if c_loc <= c_vis: c_loc = c_vis + max(1, g_nuevos_esp)
                                            else: c_loc += g_nuevos_esp
                                        else:
                                            if c_vis <= c_loc: c_vis = c_loc + max(1, g_nuevos_esp)
                                            else: c_vis += g_nuevos_esp

                                        if pred_btts_testigo == 1:
                                            if c_loc == 0: c_loc = 1
                                            if c_vis == 0: c_vis = 1

                                        marcador_ia_testigo = f"{c_loc}-{c_vis}"

                                        partido_limpio_raw = pr['partido'].replace('🏟️ ', '').replace('🏟 ', '').strip()
                                        partido_formateado = f"🏟️ {partido_limpio_raw} | [{mdo_str}] {seleccion_final_rad} vs {amenaza_final_rad}"
                                        hora_actual = datetime.datetime.now().strftime("%H:%M")
                                        
                                        datos_inyeccion = {
                                            "estado": "EN VIVO",
                                            "tipo_banca": banca_activa_rad,
                                            "estrategia": "Estrategia 3: Binario Personalizado", 
                                            "partido": partido_formateado,
                                            "prediccion_ia": marcador_ia_testigo, 
                                            "seleccion_inicial": seleccion_final_rad,
                                            "seleccion_cobertura": amenaza_final_rad,
                                            "plataforma_inicial": plat_rad_final,
                                            "cuota_inicial": float(cuota_ent_rad),
                                            "capital_total": float(stake_ent_rad),
                                            "stake_1": float(stake_ent_rad),
                                            "cuota_objetivo": float(cuota_cazar_rad),
                                            "cuota_stop_loss": float(cuota_sl_rad),
                                            "hora_inicio_partido": hora_actual
                                        }

                                        if retener_radar:
                                            res_hijos = supabase.table("historial_trading").select("codigo").like("codigo", f"{codigo_base_exacto}-%").execute()
                                            numero_hijo = len(res_hijos.data) + 1
                                            codigo_hijo = f"{codigo_base_exacto}-{numero_hijo:02d}"
                                            
                                            registro_clonado = dict(pr)
                                            registro_clonado.update(datos_inyeccion)
                                            registro_clonado['codigo'] = codigo_hijo
                                            if 'id' in registro_clonado: del registro_clonado['id']
                                            
                                            supabase.table("historial_trading").insert(registro_clonado).execute()
                                            
                                            supabase.table("historial_trading").update({"stake_1": 0.0}).eq("codigo", pr['codigo']).execute()
                                            
                                            st.session_state[aprueba_key] = False
                                            st.success(f"✅ ¡Disparo exitoso! Sub-referencia {codigo_hijo}.")
                                        else:
                                            datos_inyeccion['codigo'] = f"{codigo_base_exacto}-01"
                                            supabase.table("historial_trading").update(datos_inyeccion).eq("codigo", pr['codigo']).execute()
                                            st.success("✅ ¡Disparo exitoso! Operación trasladada a Seguimiento.")
                                            
                                        st.rerun()
                                    except Exception as err_db:
                                        st.error(f"❌ Error crítico de Supabase o IA: {str(err_db)}")
                                else:
                                    st.error("Error matemático en las cuotas o plataforma vacía. Ajusta tu entrada.")
                        
                        # ------------------------------------------------------------------
                        # 🗑️ BOTÓN DE ABORTO MAESTRO (SIEMPRE DISPONIBLE FUERA DE LA BÓVEDA)
                        # ------------------------------------------------------------------
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ ABORTAR (Descartar Partido del Radar)", key=f"btn_del_out_{pr['codigo']}", use_container_width=True):
                            if supabase is not None:
                                supabase.table("historial_trading").delete().eq("codigo", pr['codigo']).execute()
                            st.warning("Partido descartado y eliminado del Radar.")
                            st.rerun()
    # ---------------------------------------------------------
    # PESTAÑA 3: LABORATORIO TÁCTICO (Gatillo Rápido en Vivo)
    # ---------------------------------------------------------
    with tab_vivo:
        st.subheader("🧠 Laboratorio Táctico (Gatillo Rápido)")
        st.write("Caza oportunidades en vivo de partidos que no pasaron por el Escáner. Configura la jerarquía inicial y aplica todo el poder del Radar.")
        
        # ==================================================================
        # 1. SETUP DEL PARTIDO LIBRE
        # ==================================================================
        st.markdown("#### 🏗️ 1. Crear Jerarquía del Partido")
        col_eq1, col_eq2 = st.columns(2)
        eq_loc_ui = col_eq1.text_input("Equipo Local:", value="Local", key="lab_eq_loc")
        eq_vis_ui = col_eq2.text_input("Equipo Visitante:", value="Visita", key="lab_eq_vis")
        
        col_c_ini1, col_c_ini2, col_c_ini3 = st.columns(3)
        c_loc_hist = col_c_ini1.number_input("Cuota LOCAL (Pre-partido / Actual):", min_value=1.01, step=0.05, value=2.50, key="lab_c_loc")
        c_emp_hist = col_c_ini2.number_input("Cuota EMPATE:", min_value=1.01, step=0.05, value=3.10, key="lab_c_emp")
        c_vis_hist = col_c_ini3.number_input("Cuota VISITA (Pre-partido / Actual):", min_value=1.01, step=0.05, value=2.80, key="lab_c_vis")
        
        mercado_lab = st.selectbox("Mercado a Operar:", ["Ambos Anotan", "Mercado 1X2", "Línea de Goles (Más/Menos 2.5)"], key="lab_mdo")
        
        # Generamos un código único para Supabase basado en los nombres y el mercado
        codigo_lab = f"LAB-{eq_loc_ui[:3]}-{eq_vis_ui[:3]}".upper()
        
        # Simulamos la variable 'pr' del Radar
        pr = {
            'codigo': codigo_lab,
            'partido': f"🏟️ {eq_loc_ui} vs {eq_vis_ui}",
            'cuota_base_audit': c_loc_hist,
            'cuota_empate_audit': c_emp_hist,
            'cuota_amenaza_audit': c_vis_hist,
            'seleccion_inicial': mercado_lab,
            'mercado': mercado_lab,
            'cuota_inicial': 1.90,
            'stake_1': 500
        }
        
        st.markdown("---")
        st.markdown(f"### 📡 Operando: {pr['partido']} (Código: `{pr['codigo']}`)")

        # ==================================================================
        # 2. EL RADAR EXACTO (Copiado y Adaptado a 'pr')
        # ==================================================================
        # ------------------------------------------------------------------
        # 🔄 BOTÓN DE SINCRONIZACIÓN Y LECTURA DE FOTOS
        # ------------------------------------------------------------------
        col_tit1, col_tit2 = st.columns([2, 1])
        with col_tit1:
            st.markdown("#### 📸 Foto Táctica En Vivo")
        with col_tit2:
            if st.button("🔄 Sincronizar Info", key=f"btn_sync_{pr['codigo']}"):
                try:
                    res_sync = supabase.table("registro_fotos").select("*").like("codigo_posicion", f"{pr['codigo']}%").order("minuto_evaluado", desc=True).limit(1).execute()
                    if res_sync.data:
                        foto_reciente = res_sync.data[0]
                        st.session_state[f"mr_{pr['codigo']}"] = int(foto_reciente['minuto_evaluado'])
                        st.session_state[f"glr_{pr['codigo']}"] = int(foto_reciente['goles_local'])
                        st.session_state[f"gvr_{pr['codigo']}"] = int(foto_reciente['goles_vis'])
                        st.session_state[f"alr_{pr['codigo']}"] = int(foto_reciente['atkp_local'])
                        st.session_state[f"avr_{pr['codigo']}"] = int(foto_reciente['atkp_vis'])
                        st.success(f"✅ ¡Datos del min {foto_reciente['minuto_evaluado']} importados!")
                    else:
                        st.warning("⚠️ No hay fotos previas en el Seguimiento.")
                except Exception as e:
                    st.error(f"Error sincronizando: {e}")

        # ------------------------------------------------------------------
        # 🎛️ PANEL DE EVALUACIÓN MULTI-ESTRATEGIA
        # ------------------------------------------------------------------
        tab_datos, tab_anti_empate = st.tabs(["⚙️ Carga de Datos (APM)", "💣 Calculadora Anti-Empate"])
        
        with tab_datos:
            cr1, cr2, cr3 = st.columns(3)
            m_rad = cr1.number_input("⏱️ Minuto:", min_value=1, max_value=120, key=f"mr_{pr['codigo']}", value=st.session_state.get(f"mr_{pr['codigo']}", 60))
            gl_rad = cr2.number_input(f"⚽ Goles {eq_loc_ui}:", min_value=0, key=f"glr_{pr['codigo']}", value=st.session_state.get(f"glr_{pr['codigo']}", 0))
            gv_rad = cr3.number_input(f"⚽ Goles {eq_vis_ui}:", min_value=0, key=f"gvr_{pr['codigo']}", value=st.session_state.get(f"gvr_{pr['codigo']}", 0))
            
            cr4, cr5 = st.columns(2)
            al_rad = cr4.number_input(f"🔥 Atq. {eq_loc_ui}:", min_value=0, key=f"alr_{pr['codigo']}", value=st.session_state.get(f"alr_{pr['codigo']}", 40))
            av_rad = cr5.number_input(f"🔥 Atq. {eq_vis_ui}:", min_value=0, key=f"avr_{pr['codigo']}", value=st.session_state.get(f"avr_{pr['codigo']}", 25))

        with tab_anti_empate:
            st.markdown("""
            <div style='background-color: #F8FAFC; border-left: 4px solid #8B5CF6; padding: 10px; border-radius: 4px; margin-bottom: 15px;'>
                <h4 style='margin:0; color: #4C1D95;'>⚖️ Estrategia Asimétrica (Riesgo al Empate)</h4>
            </div>
            """, unsafe_allow_html=True)
            
            c_ae1, c_ae2, c_ae3 = st.columns(3)
            cuota_sug_fav = min(float(pr.get('cuota_base_audit', 1.08)), float(pr.get('cuota_amenaza_audit', 1.08)))
            cuota_sug_deb = max(float(pr.get('cuota_base_audit', 18.20)), float(pr.get('cuota_amenaza_audit', 18.20)))
            
            cuota_fav_ae = c_ae1.number_input("👑 Cuota Favorito (En Vivo):", min_value=1.01, step=0.01, value=max(1.01, cuota_sug_fav), key=f"c_fav_ae_{pr['codigo']}")
            cuota_deb_ae = c_ae2.number_input("🩸 Cuota Débil (En Vivo):", min_value=1.01, step=0.1, value=max(2.0, cuota_sug_deb), key=f"c_deb_ae_{pr['codigo']}")
            inv_total_ae = c_ae3.number_input("💰 Inversión Total ($):", min_value=1000, step=10000, value=100000, key=f"inv_ae_{pr['codigo']}")
            
            if cuota_deb_ae > 0 and cuota_fav_ae > 0:
                stake_cobertura = inv_total_ae / cuota_deb_ae
                stake_fuerte = inv_total_ae - stake_cobertura
                retorno_fav = stake_fuerte * cuota_fav_ae
                utilidad_fav = retorno_fav - inv_total_ae
                roi_pct = (utilidad_fav / inv_total_ae) * 100 if inv_total_ae > 0 else 0
                
                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                if stake_fuerte > 0:
                    st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; margin-bottom: 10px;'>
                        <div style='background-color: #ECFDF5; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #A7F3D0;'>
                            <h5 style='margin:0; color: #065F46;'>🟢 GANA FAVORITO</h5>
                            <p style='margin:5px 0 0 0; font-size:0.8rem; color: #047857;'>Inyectar: <b>${stake_fuerte:,.0f}</b></p>
                            <h3 style='margin:10px 0 0 0; color: #10B981;'>+${utilidad_fav:,.0f}</h3>
                        </div>
                        <div style='background-color: #EFF6FF; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #BFDBFE;'>
                            <h5 style='margin:0; color: #1E3A8A;'>🔵 GANA DÉBIL</h5>
                            <p style='margin:5px 0 0 0; font-size:0.8rem; color: #1D4ED8;'>Inyectar: <b>${stake_cobertura:,.0f}</b></p>
                            <h3 style='margin:10px 0 0 0; color: #3B82F6;'>$0</h3>
                        </div>
                        <div style='background-color: #FEF2F2; padding: 15px; border-radius: 8px; width: 32%; text-align: center; border: 1px solid #FECACA;'>
                            <h5 style='margin:0; color: #991B1B;'>🔴 EMPATE</h5>
                            <h3 style='margin:10px 0 0 0; color: #EF4444;'>-${inv_total_ae:,.0f}</h3>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Ajusta la cuota del Débil, no permite cobertura matemática.")

        # ==================================================================
        # 💰 LÓGICA DE CONFIGURACIÓN Y CUOTAS
        # ==================================================================
        st.markdown("---")
        st.markdown("#### ⚙️ Configurar Mercado y Cuotas En Vivo")
        
        sel_ini_rad = str(pr.get('seleccion_inicial', ''))
        
        if "Ambos Anotan" in sel_ini_rad:
            mdo_str = "Ambos Anotan"
            opciones_mercado = ["Sí", "No"]
        elif "Línea de Goles" in sel_ini_rad:
            mdo_str = "Línea de Goles"
            opciones_mercado = ["Más de 2.5", "Menos de 2.5"]
        else:
            mdo_str = "Mercado 1X2"
            opciones_mercado = [f"Local ({eq_loc_ui})", "Empate", f"Visita ({eq_vis_ui})"]

        col_nom1, col_nom2 = st.columns(2)
        with col_nom1:
            seleccion_final_rad = st.selectbox("Tu Selección:", opciones_mercado, key=f"sel_rad_{pr['codigo']}")
        with col_nom2:
            if mdo_str == "Ambos Anotan" or mdo_str == "Línea de Goles":
                amenaza_final_rad = opciones_mercado[1] if seleccion_final_rad == opciones_mercado[0] else opciones_mercado[0]
            else:
                amenaza_final_rad = "Opción Contraria"
                
            st.markdown("<p style='font-size: 14px; margin-bottom: 5px;'>La Amenaza a Cubrir:</p>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color: #F1F5F9; border: 1px solid #CBD5E1; color: #64748B; padding: 9px 12px; border-radius: 8px; font-family: sans-serif; cursor: not-allowed; min-height: 40px; display: flex; align-items: center;">
                {amenaza_final_rad}
            </div>
            """, unsafe_allow_html=True)

        c_ent_key = f"c_ent_{pr['codigo']}"
        if c_ent_key not in st.session_state:
            st.session_state[c_ent_key] = float(pr.get('cuota_inicial', 2.0))

        c_am_key = f"c_am_{pr['codigo']}"
        if c_am_key not in st.session_state:
            st.session_state[c_am_key] = 1.90

        stk_key = f"stk_ent_{pr['codigo']}"
        if stk_key not in st.session_state:
            st.session_state[stk_key] = int(max(5000, int(pr.get('stake_1', 500))))

        col_ent1, col_ent2, col_ent3 = st.columns(3)
        with col_ent1:
            cuota_ent_rad = st.number_input("Cuota de tu Selección:", min_value=1.01, step=0.05, key=c_ent_key)
        with col_ent2:
            cuota_amenaza_rad = st.number_input("Cuota Amenaza a Cubrir:", min_value=1.01, step=0.05, key=c_am_key)
        with col_ent3:
            stake_ent_rad = st.number_input("Capital Invertido:", min_value=500, step=500, key=stk_key)

        # ==================================================================
        # 📸 BOTÓN DE BITÁCORA (CAPTURAR MOMENTUM)
        # ==================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📸 Tomar Foto Táctica y Financiera", key=f"btn_foto_live_{pr['codigo']}", use_container_width=True):
            if supabase is not None:
                try:
                    nueva_foto = {
                        "codigo_posicion": pr['codigo'], "minuto_evaluado": m_rad,
                        "goles_local": gl_rad, "goles_vis": gv_rad,
                        "atkp_local": al_rad, "atkp_vis": av_rad,
                        "cuota_si": cuota_ent_rad, "cuota_no": cuota_amenaza_rad
                    }
                    supabase.table("registro_fotos").insert(nueva_foto).execute()
                    st.success(f"✅ ¡Foto del min {m_rad} anclada al código {pr['codigo']}!")
                except Exception as e:
                    st.error(f"❌ Error guardando foto: {e}")

        # ==================================================================
        # 🎛️ SELECTOR DE PERFIL DE RIESGO
        # ==================================================================
        st.markdown("---")
        st.markdown("#### 🎛️ Perfil de Riesgo Operativo")
        perfil_riesgo = st.selectbox(
            "Selecciona la rigidez de los candados matemáticos:",
            ["🛡️ CONSERVADOR (Modo Francotirador)", "⚖️ MODERADO (Modo Táctico)", "🔥 AGRESIVO (Modo Kamikaze)"],
            index=1,
            key=f"perfil_{pr['codigo']}"
        )
        
        if "CONSERVADOR" in perfil_riesgo:
            umbral_asfixia = 0.8; mult_castigo = 0.10; umbral_gigante = 0.9; ventaja_min_exigida = 0.50; minuto_limite_si = 70
        elif "MODERADO" in perfil_riesgo:
            umbral_asfixia = 0.6; mult_castigo = 0.20; umbral_gigante = 0.7; ventaja_min_exigida = 0.20; minuto_limite_si = 78
        else: 
            umbral_asfixia = 0.4; mult_castigo = 0.50; umbral_gigante = 0.5; ventaja_min_exigida = 0.0; minuto_limite_si = 85

        # ==================================================================
        # 🧠 BOTÓN DEL ORÁCULO TÁCTICO (EL NÚCLEO)
        # ==================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧠 Validar con Oráculo Táctico", key=f"btn_ev_{pr['codigo']}", use_container_width=True, type="primary"):
            try:
                import joblib
                import pandas as pd
                m1x2_rad = joblib.load('modelo_1x2.pkl')
                mgoles_rad = joblib.load('modelo_goles.pkl')
                mbtts_rad = joblib.load('modelo_btts.pkl')
                
                apm_global_loc = al_rad / max(1, m_rad)
                apm_global_vis = av_rad / max(1, m_rad)
                
                apm_local_dinamico = apm_global_loc
                apm_vis_dinamico = apm_global_vis
                texto_momentum = "Promedio Global"
                tiene_momentum = False
                
                if supabase is not None:
                    try:
                        res_last = supabase.table("registro_fotos").select("*").eq("codigo_posicion", pr['codigo']).lt("minuto_evaluado", m_rad).order("minuto_evaluado", desc=True).limit(1).execute()
                        if res_last.data:
                            foto_ant = res_last.data[0]
                            delta_min = m_rad - int(foto_ant['minuto_evaluado'])
                            if delta_min >= 2:
                                apm_local_dinamico = max(0.0, (al_rad - int(foto_ant['atkp_local'])) / delta_min)
                                apm_vis_dinamico = max(0.0, (av_rad - int(foto_ant['atkp_vis'])) / delta_min)
                                texto_momentum = f"Últimos {delta_min} min"
                                tiene_momentum = True
                    except:
                        pass

                apm_rad = apm_local_dinamico + apm_vis_dinamico
                ird_rad_global = min(100.0, (apm_global_loc + apm_global_vis) * 45.0)
                
                X_rad = pd.DataFrame([{
                    'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad,
                    'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad_global,
                    'cuota_base_audit': float(pr.get('cuota_base_audit', 2.0)), 
                    'cuota_amenaza_audit': float(pr.get('cuota_amenaza_audit', 2.0))
                }])
                
                pred_1x2_rad = m1x2_rad.predict(X_rad)[0]
                pred_goles_rad = mgoles_rad.predict(X_rad)[0]
                pred_btts_rad = mbtts_rad.predict(X_rad)[0]
                
                probabilidades = mbtts_rad.predict_proba(X_rad)[0]
                prob_no = probabilidades[0]
                prob_si = probabilidades[1]

                if (apm_local_dinamico < umbral_asfixia and gl_rad == 0) or (apm_vis_dinamico < umbral_asfixia and gv_rad == 0):
                    prob_si = prob_si * mult_castigo
                    prob_no = 1.0 - prob_si
                elif apm_local_dinamico >= 1.0 and apm_vis_dinamico >= 1.0:
                    prob_si = min(0.95, prob_si * 1.50)
                    prob_no = 1.0 - prob_si

                winner_tactico = "Empate" if pred_1x2_rad == 1 else ("Local" if pred_1x2_rad == 2 else "Visita")
                
                if c_loc_hist <= 1.35: jerarquia = f"👑 Súper Favorito: {eq_loc_ui}"
                elif c_vis_hist <= 1.35: jerarquia = f"👑 Súper Favorito: {eq_vis_ui}"
                elif c_loc_hist < c_vis_hist and (c_vis_hist - c_loc_hist) > 0.3: jerarquia = f"⚔️ Favorito: {eq_loc_ui}"
                elif c_vis_hist < c_loc_hist and (c_loc_hist - c_vis_hist) > 0.3: jerarquia = f"⚔️ Favorito: {eq_vis_ui}"
                else: jerarquia = "⚖️ Fuerzas Parejas"

                if apm_local_dinamico > apm_vis_dinamico and (apm_local_dinamico - apm_vis_dinamico) >= 0.3: dom_vivo = eq_loc_ui
                elif apm_vis_dinamico > apm_local_dinamico and (apm_vis_dinamico - apm_local_dinamico) >= 0.3: dom_vivo = eq_vis_ui
                else: dom_vivo = "Asedio Dividido"

                if mdo_str == "Ambos Anotan":
                    cuota_justa_si = 1 / prob_si if prob_si > 0.01 else 99.0
                    cuota_justa_no = 1 / prob_no if prob_no > 0.01 else 99.0
                    
                    if seleccion_final_rad == "Sí":
                        ventaja = cuota_ent_rad - cuota_justa_si
                        prob_mercado = prob_si
                        cuota_justa = cuota_justa_si
                        
                        if m_rad >= minuto_limite_si:
                            alerta_accion = f"⏳ **BLOQUEO POR RELOJ (LOTERÍA)**"
                            texto_accion = f"Tu Perfil {perfil_riesgo.split(' ')[1]} prohíbe apostar a goles después del minuto {minuto_limite_si}. No entres a ruletas de última hora."
                            bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
                        elif ventaja >= ventaja_min_exigida:
                            alerta_accion = f"🔥 **¡DISPARA AL SÍ AHORA!**"
                            texto_accion = f"El mercado es tuyo. La cuota justa es **{cuota_justa:.2f}** y te ofrecen **{cuota_ent_rad:.2f}**. Entra ya."
                            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
                        elif ventaja >= 0:
                            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
                            texto_accion = f"Hay valor matemático (Justa: **{cuota_justa:.2f}**), pero tu Perfil {perfil_riesgo.split(' ')[1]} exige una ganancia superior. Mantente al margen."
                            bg_color = "#F8FAFC"; border_color = "#64748B"; text_color = "#334155"
                        else:
                            if (cuota_justa - cuota_ent_rad) <= 0.40 and m_rad < 75:
                                alerta_accion = f"⏳ **PACIENCIA (ESPERA A QUE SUBA EL SÍ)**"
                                texto_accion = f"Pagan muy poco (**{cuota_ent_rad:.2f}**). La cuota justa es **{cuota_justa:.2f}**. Espera a que alcance ese valor."
                                bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
                            else:
                                alerta_accion = f"🚫 **DESCARTADO (TRAMPA EN EL SÍ)**"
                                texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_ent_rad:.2f}**. La brecha es muy grande. Aborta."
                                bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
                                
                    else: # Seleccionó "No"
                        ventaja = cuota_ent_rad - cuota_justa_no
                        prob_mercado = prob_no
                        cuota_justa = cuota_justa_no
                        
                        if ventaja >= ventaja_min_exigida:
                            alerta_accion = f"🛡️ **¡DISPARA AL NO AHORA!**"
                            texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_ent_rad:.2f}**. ¡Mete la plata YA!"
                            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
                        elif ventaja >= 0:
                            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
                            texto_accion = f"Hay valor matemático (Justa: **{cuota_justa:.2f}**), pero tu Perfil {perfil_riesgo.split(' ')[1]} exige mayor margen. No dispares."
                            bg_color = "#F8FAFC"; border_color = "#64748B"; text_color = "#334155"
                        else:
                            alerta_accion = f"🚫 **LLEGASTE TARDE AL NO**"
                            texto_accion = f"Cuota justa era **{cuota_justa:.2f}** y ya la tumbaron a **{cuota_ent_rad:.2f}**. Operar aquí es pérdida matemática."
                            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
                            
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; border-left: 6px solid {border_color}; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h3 style="margin-top:0; color:{border_color};">{alerta_accion}</h3>
                        <p style="margin:0; font-size:1.05rem; color:{text_color};">{texto_accion}</p>
                        <hr style="border-color:{border_color}; opacity:0.3; margin: 10px 0;">
                        <div style="font-size:0.9rem; color:#475569; display:flex; justify-content:space-between;">
                            <span><b>Prob. IA {seleccion_final_rad.upper()}:</b> {prob_mercado*100:.1f}%</span>
                            <span><b>Velocidad:</b> {apm_rad:.2f} APM ({texto_momentum})</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("---")

                # ==================================================================
                # SEÑALES TÁCTICAS
                # ==================================================================
                fav_es_local = "Local" in jerarquia
                fav_es_visita = "Visita" in jerarquia
                alerta_señal = ""
                goles_actuales_totales = gl_rad + gv_rad
                
                if tiene_momentum:
                    if (fav_es_local and gv_rad == 1 and gl_rad == 0 and apm_local_dinamico >= umbral_gigante) or \
                       (fav_es_visita and gl_rad == 1 and gv_rad == 0 and apm_vis_dinamico >= umbral_gigante):
                        alerta_señal = f"<div style='background-color: #F0FDF4; border-left: 6px solid #16A34A; padding: 15px; border-radius: 4px; margin-bottom: 15px;'><h4 style='margin-top:0; color:#15803D;'>🔥 SEÑAL TÁCTICA: EL GIGANTE HERIDO</h4></div>"
                    
                    elif (fav_es_local and gl_rad == 1 and gv_rad == 0 and apm_local_dinamico >= umbral_gigante and apm_vis_dinamico <= umbral_asfixia) or \
                         (fav_es_visita and gv_rad == 1 and gl_rad == 0 and apm_vis_dinamico >= umbral_gigante and apm_local_dinamico <= umbral_asfixia):
                        alerta_señal = f"<div style='background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 15px; border-radius: 4px; margin-bottom: 15px;'><h4 style='margin-top:0; color:#991B1B;'>🛡️ SEÑAL TÁCTICA: ASFIXIA TOTAL</h4></div>"
                
                if alerta_señal: st.markdown(alerta_señal, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background-color: #1E293B; border-bottom: 4px solid #3B82F6; padding: 10px; border-radius: 8px 8px 0 0; text-align: center;">
                    <h4 style="margin:0; color:#94A3B8; font-size: 0.9rem;">ADN DEL PARTIDO</h4>
                    <h3 style="color:#FFFFFF; margin: 5px 0;">[{jerarquia}]</h3>
                </div>
                <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; margin-bottom: 15px;">
                    <h3 style="margin-top:0; color:#0F172A;">🎯 PROYECCIÓN TÁCTICA</h3>
                    <p style="margin:0; font-size: 1.1rem; color:#475569;">Ganador Físico: <b>{winner_tactico}</b></p>
                    <p style="margin:5px 0 0 0; font-size: 0.85rem; color:#64748B;">El <b>{dom_vivo}</b> está dominando la cancha (IRD: {ird_rad_global:.1f}%)</p>
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error procesando IA táctica: {e}")

        # ==================================================================
        # ⚙️ MÓDULO DE DISPARO (INYECCIÓN A BASE DE DATOS)
        # ==================================================================
        st.markdown("#### 🚀 Ejecutar Posición Manual")
        lista_casas = ["1xBet", "BetPlay", "Wplay", "Rushbet", "Codere", "Yajuego", "Zamba", "Sportium", "Megapuesta", "Otra"]
        plat_rad_sel = st.selectbox("Casa de Apuestas:", lista_casas, key=f"plat_{pr['codigo']}")
        
        banca_ejecutar = st.radio("Entorno de ejecución definitivo:", ["🟢 Dinero Real", "🟡 Simulación (Paper Trading)"], horizontal=True, key=f"banca_{pr['codigo']}")
        
        if st.button("🔥 DISPARAR (Confirmar Entrada Libre)", type="primary", key=f"btn_disp_{pr['codigo']}", use_container_width=True):
            if cuota_ent_rad > 0:
                import datetime
                try:
                    datos_inyeccion = {
                        "codigo": pr['codigo'] + "-" + datetime.datetime.now().strftime("%M%S"),
                        "estado": "EN VIVO",
                        "tipo_banca": "REAL" if "Real" in banca_ejecutar else "SIMULACION",
                        "estrategia": "Estrategia 3: Gatillo Rápido (Lab)", 
                        "partido": pr['partido'],
                        "seleccion_inicial": seleccion_final_rad,
                        "seleccion_cobertura": amenaza_final_rad,
                        "plataforma_inicial": plat_rad_sel,
                        "cuota_inicial": float(cuota_ent_rad),
                        "capital_total": float(stake_ent_rad),
                        "stake_1": float(stake_ent_rad),
                        "hora_inicio_partido": datetime.datetime.now().strftime("%H:%M")
                    }
                    supabase.table("historial_trading").insert(datos_inyeccion).execute()
                    st.success("✅ ¡Operación Libre inyectada a la base de datos con éxito!")
                except Exception as e:
                    st.error(f"❌ Error al disparar: {e}")