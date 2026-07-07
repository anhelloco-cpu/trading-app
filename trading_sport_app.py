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
    ["2️⃣ Estrategia 2: Paz Mental (Crear Operación)", "🔒 Seguimiento y Cierre de Operaciones"]
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
# MÓDULO 2: SEGUIMIENTO Y CIERRE (FLUJO DE TRES ESTADOS)
# =====================================================================
elif estrategia_activa == "🔒 Seguimiento y Cierre de Operaciones":
    st.markdown("### 📝 Panel de Control de Operaciones")
    
    if supabase is None:
        st.error("Conecta Supabase primero.")
    else:
        # Traemos todo lo que no esté CERRADO
        res = supabase.table("historial_trading").select("*").in_("estado", ["EN VIVO", "CUBIERTA"]).execute()
        ops = res.data
        
        if not ops:
            st.info("No tienes operaciones activas en este momento.")
        else:
            for op in ops:
                with st.expander(f"⚽ {op['partido']} | Código: {op['codigo']} | Estado: {op['estado']}"):
                    st.write(f"**Capital Total:** ${op['capital_total']:,.0f} | **Reserva (Stake 2):** ${op['reserva_stake_2']:,.0f}")
                    
                    # --- ESTADO 1: PENDIENTE (AÚN NO SE HA CAZADO LA COBERTURA) ---
                    if op['estado'] == "EN VIVO":
                        st.warning("⚠️ Operación sin cubrir. Esperando cuota objetivo.")
                        
                        with st.form(f"cazar_{op['codigo']}"):
                            cuota_cazada = st.number_input("¿A qué cuota cazaste la cobertura?", min_value=1.01, step=0.01, value=float(op['cuota_objetivo']))
                            if st.form_submit_button("✅ Cazar Cobertura (Marcar como Cubierta)"):
                                supabase.table("historial_trading").update({
                                    "estado": "CUBIERTA",
                                    "cuota_cazada_real": cuota_cazada
                                }).eq("codigo", op['codigo']).execute()
                                st.success("¡Operación marcada como cubierta! Ya puedes esperar al final del partido.")
                                st.rerun()
                                
                    # --- ESTADO 2: CUBIERTA (YA SE CAZÓ, ESPERANDO FINAL) ---
                    elif op['estado'] == "CUBIERTA":
                        st.success(f"🛡️ Operación cubierta exitosamente a cuota {op['cuota_cazada_real']:.2f}")
                        
                        with st.form(f"liquidar_{op['codigo']}"):
                            resultado = st.radio("¿Qué pasó al final?", [
                                "Ganó Apuesta Inicial (Favorito)",
                                "Ganó Cobertura",
                                "Pérdida Total"
                            ])
                            
                            if st.form_submit_button("Liquidar Operación"):
                                # Cálculo contable
                                if "Ganó Apuesta Inicial" in resultado:
                                    utilidad = (op['stake_1'] * op['cuota_inicial']) - op['capital_total']
                                elif "Ganó Cobertura" in resultado:
                                    utilidad = (op['reserva_stake_2'] * op['cuota_cazada_real']) - op['capital_total']
                                else:
                                    utilidad = -op['capital_total']
                                    
                                supabase.table("historial_trading").update({
                                    "estado": "CERRADA",
                                    "resultado_final": resultado,
                                    "utilidad_neta_real": utilidad,
                                    "roi_real": (utilidad / op['capital_total']) * 100
                                }).eq("codigo", op['codigo']).execute()
                                st.success(f"Operación finalizada. Utilidad: ${utilidad:,.0f} COP.")
                                st.rerun()

        # Resumen del Libro Mayor
        st.markdown("---")
        st.subheader("📊 Historial de Auditoría")
        res_cerradas = supabase.table("historial_trading").select("*").eq("estado", "CERRADA").order("fecha", desc=True).execute()
        df = pd.DataFrame(res_cerradas.data)
        
        if not df.empty:
            st.dataframe(df[['fecha', 'codigo', 'partido', 'resultado_final', 'utilidad_neta_real', 'roi_real']], use_container_width=True)