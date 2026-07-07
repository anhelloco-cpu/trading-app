import streamlit as st
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
    ["2️⃣ Estrategia 2: Paz Mental (Crear Operación)", "🔒 Seguimiento y Liquidación de Posiciones"]
)

st.title("⚖️ Sistema de Trading Automático")

# =====================================================================
# MÓDULO 1: PAZ MENTAL + GUARDADO
# =====================================================================
if estrategia_activa == "2️⃣ Estrategia 2: Paz Mental (Crear Operación)":
    st.info("**Lógica:** Configura tu inversión. Si los números cuadran, inicia la operación y obtén tu código.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        capital_total = st.number_input("Capital Total (COP)", min_value=10000, value=50000, step=5000)
    with col2:
        cuota_1 = st.number_input("Cuota Inicial (Favorito o Empate)", min_value=1.01, value=1.25, step=0.05)
    with col3:
        utilidad_esperada = st.slider("Utilidad Deseada (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)

    riesgo = st.slider("Exigencia en Cobertura (0% = Librar, 100% = Ganancia Igualada):", min_value=0, max_value=100, value=50, step=10)

    # Cálculos
    retorno_objetivo_1 = capital_total * (1 + (utilidad_esperada / 100.0))
    utilidad_neta_plata = retorno_objetivo_1 - capital_total
    stake_1 = retorno_objetivo_1 / cuota_1
    stake_2 = capital_total - stake_1

    st.markdown("---")

    if stake_2 < 5000:
        st.markdown(f'<div class="error-caja"><b>🚨 RESTRICCIÓN:</b> Reserva menor a $5,000. Ajusta el capital o utilidad.</div>', unsafe_allow_html=True)
    else:
        retorno_exigido_cobertura = capital_total + (utilidad_neta_plata * (riesgo / 100.0))
        cuota_a_cazar = retorno_exigido_cobertura / stake_2
        
        col_plan1, col_plan2 = st.columns(2)
        with col_plan1:
            st.markdown(f'<div class="caja-inversion"><h4>Fase 1: Pre-partido</h4><p>Ingresa: <b>${stake_1:,.0f} COP</b> a cuota <b>{cuota_1:.2f}</b>.</p><hr><p>Reserva: <b>${stake_2:,.0f} COP</b></p></div>', unsafe_allow_html=True)
        with col_plan2:
            st.markdown(f'<div class="caja-objetivo"><h4>Fase 2: En Vivo</h4><p>Caza esta cuota:</p><h1 style="color:#15803D; font-size:3rem; margin:0;">{cuota_a_cazar:.2f}</h1></div>', unsafe_allow_html=True)

        st.markdown("### 💾 Iniciar Operación")
        with st.form("guardar_operacion"):
            nombre_partido = st.text_input("Partido (Ej: Nacional vs Santa Fe)")
            if st.form_submit_button("Generar Código e Iniciar"):
                if not nombre_partido:
                    st.error("Nombre del partido es obligatorio.")
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
                    try:
                        supabase.table("historial_trading").insert(datos).execute()
                        st.markdown(f'<div class="caja-codigo"><h3>Código: {nuevo_codigo}</h3></div>', unsafe_allow_html=True)
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
        # Extraer operaciones pendientes de liquidación
        res = supabase.table("historial_trading").select("*").in_("estado", ["EN VIVO", "CUBIERTA"]).execute()
        ops = res.data
        
        if not ops:
            st.info("Libro mayor al día. No hay posiciones abiertas en este momento.")
        else:
            for op in ops:
                with st.expander(f"⚽ {op['partido']} | Ref: {op['codigo']} | Estado: {op['estado']}"):
                    st.write(f"**Capital Comprometido:** ${op['capital_total']:,.0f} | **Fondo de Cobertura:** ${op['reserva_stake_2']:,.0f} | **Target:** {op['cuota_objetivo']:.2f}")
                    
                    # ---------------------------------------------------------
                    # ESTADO A: POSICIÓN ABIERTA (EN VIVO, SIN COBERTURA)
                    # ---------------------------------------------------------
                    if op['estado'] == "EN VIVO":
                        st.info("POSICIÓN ABIERTA: Seleccione la gestión de riesgo a aplicar.")
                        
                        with st.form(f"gestion_{op['codigo']}"):
                            accion = st.radio(
                                "Acción a ejecutar:", 
                                ["Ejecutar Cobertura en Mercado (Hedge)", "Liquidar Posición Directa (Sin Cobertura)"]
                            )
                            
                            # Campos dinámicos según la acción
                            cuota_ingresada = 0.0
                            resultado_directo = ""
                            
                            if accion == "Ejecutar Cobertura en Mercado (Hedge)":
                                cuota_ingresada = st.number_input("Tasa de cobertura fijada (Cuota):", min_value=1.01, step=0.01, value=float(op['cuota_objetivo']))
                            else:
                                resultado_directo = st.radio(
                                    "Confirmación de evento pre-partido:", 
                                    ["Efectividad de Apuesta Pre-Partido", "Déficit Operativo (Pérdida de Inversión Inicial)"]
                                )

                            if st.form_submit_button("Registrar Movimiento"):
                                if accion == "Ejecutar Cobertura en Mercado (Hedge)":
                                    # Registro de la cobertura, la posición sigue abierta (CUBIERTA)
                                    supabase.table("historial_trading").update({
                                        "estado": "CUBIERTA",
                                        "cuota_cazada_real": cuota_ingresada
                                    }).eq("codigo", op['codigo']).execute()
                                    st.success("Cobertura registrada en el libro. La posición permanece abierta a la espera de liquidación final.")
                                else:
                                    # Liquidación directa inmediata
                                    if "Efectividad" in resultado_directo:
                                        utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                    else:
                                        # Solo se pierde el stake_1 porque la reserva nunca entró al mercado
                                        utilidad = -op['stake_1'] 
                                        
                                    supabase.table("historial_trading").update({
                                        "estado": "CERRADA",
                                        "resultado_final": f"Cierre Directo: {resultado_directo}",
                                        "utilidad_neta_real": utilidad,
                                        "roi_real": (utilidad / op['capital_total']) * 100
                                    }).eq("codigo", op['codigo']).execute()
                                    st.success(f"Posición liquidada. Utilidad neta registrada: ${utilidad:,.0f} COP.")
                                st.rerun()

                    # ---------------------------------------------------------
                    # ESTADO B: POSICIÓN CUBIERTA (ESPERANDO LIQUIDACIÓN FINAL)
                    # ---------------------------------------------------------
                    elif op['estado'] == "CUBIERTA":
                        st.success(f"🛡️ Posición con cobertura asegurada a tasa de {op['cuota_cazada_real']:.2f}. Pendiente de liquidación.")
                        
                        with st.form(f"liq_{op['codigo']}"):
                            resultado_final = st.radio(
                                "Resolución del evento para conciliación:", 
                                [
                                    "Efectividad de Apuesta Pre-Partido", 
                                    "Efectividad de Cobertura Ejecutada", 
                                    "Déficit Operativo General (Pérdida Total)"
                                ]
                            )
                            
                            if st.form_submit_button("Liquidar Posición Cubierta"):
                                if "Pre-Partido" in resultado_final:
                                    utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                elif "Cobertura" in resultado_final:
                                    utilidad = (op['reserva_stake_2'] * op['cuota_cazada_real']) - op['capital_total']
                                else:
                                    utilidad = -op['capital_total']
                                    
                                supabase.table("historial_trading").update({
                                    "estado": "CERRADA",
                                    "resultado_final": resultado_final,
                                    "utilidad_neta_real": utilidad,
                                    "roi_real": (utilidad / op['capital_total']) * 100
                                }).eq("codigo", op['codigo']).execute()
                                st.success(f"Conciliación exitosa. Utilidad neta registrada: ${utilidad:,.0f} COP.")
                                st.rerun()

        # Resumen del Libro Mayor
        st.markdown("---")
        st.subheader("📊 Libro Mayor Contable (Posiciones Liquidadas)")
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        
        if not df.empty:
            st.dataframe(df[['fecha', 'codigo', 'partido', 'resultado_final', 'utilidad_neta_real', 'roi_real']], use_container_width=True)