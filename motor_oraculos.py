import joblib
import pandas as pd
import math
import re

# ==================================================================
# 1. CARGA DE MODELOS (Se ejecuta una sola vez al importar)
# ==================================================================
try:
    # Modelos EN VIVO (Sin el '_pre_')
    m1x2_rad = joblib.load('modelo_1x2.pkl')
    mgoles_rad = joblib.load('modelo_goles.pkl')
    mbtts_rad = joblib.load('modelo_btts.pkl')
except Exception as e:
    print(f"Error cargando modelos ML en el motor: {e}")

# ==================================================================
# 2. DEFINICIÓN DE ESCENARIOS Y PATRONES TÁCTICOS (INTOCABLE)
# ==================================================================
def detectar_patron_btts_si(min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
                            jerarquia_pre, apm_global_fav, apm_global_deb, apm_global_ganador, apm_global_perdedor,
                            mom_reciente_loc, mom_reciente_vis, mom_combinado, diferencial_mom, 
                            mom_post_gol_fav, mom_post_gol_deb, mom_post_gol_ganador, mom_post_gol_perdedor,
                            tp_fav, tp_deb, tp_ganador, tp_perdedor):
    
    if (min_corrido <= 45 and estado_goles == True and jerarquia_pre in ["Favorito", "Súper Favorito"] and 
        lider_marcador == "No Favorito" and goles_deb == 1 and mom_post_gol_fav > 1.0 and 
        mom_post_gol_deb < 0.4 and diferencial_mom > 0.7 and tp_fav > 0.40):
        return "🟢 EL TIGRE HERIDO: Favorito pierde 0-1 pero asedia brutalmente (Mom > 1.0) y con profundidad (TP > 40%). LUZ VERDE SÍ."

    elif (min_corrido <= 45 and estado_goles == True and jerarquia_pre in ["Favorito", "Súper Favorito"] and 
          lider_marcador == "Favorito" and goles_fav == 1 and goles_deb == 0 and apm_global_fav < 0.6 and 
          apm_global_deb > 0.8 and mom_post_gol_fav < 0.4 and mom_post_gol_deb > 0.8 and tp_deb > 0.40):
        return "🟢 LA REBELDÍA: Favorito gana 1-0 y se durmió. El Débil asedia con furia (Mom > 0.8) y verticalidad (TP > 40%). LUZ VERDE SÍ."

    elif (min_corrido <= 45 and estado_goles == True and jerarquia_pre == "Fuerzas Parejas" and 
          (goles_ganador == 1 and goles_perdedor == 0) and apm_global_ganador > 0.7 and 
          apm_global_perdedor > 0.8 and mom_combinado >= 1.5 and diferencial_mom < 0.2 and 
          mom_post_gol_perdedor > 0.9 and tp_ganador > 0.35 and tp_perdedor > 0.35):
        return "🟢 DEVOLUCIÓN RÁPIDA: Partido parejo 1-0. Intercambio de golpes intenso y ambos llegan con peligro (TP > 35%). LUZ VERDE SÍ."

    elif (min_corrido <= 45 and estado_goles == True and jerarquia_pre in ["Favorito", "Súper Favorito"] and 
          lider_marcador == "Favorito" and goles_fav >= 2 and goles_deb == 0 and apm_global_fav < 0.6 and 
          apm_global_deb > 0.8 and mom_post_gol_deb > 1.0 and tp_deb > 0.45):
        return "🟢 DESCUENTO POR RELAJACIÓN: Favorito golea 2-0 y bajó los brazos. El Débil ataca furioso y profundo (TP > 45%). LUZ VERDE SÍ."

    else:
        return None

def detectar_patron_btts_no(min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
                            jerarquia_pre, apm_global_fav, apm_global_deb, 
                            mom_fav, mom_deb, tp_fav, tp_deb):
    
    if (min_corrido >= 35 and jerarquia_pre in ["Favorito", "Súper Favorito"] and goles_deb == 0 and 
        apm_global_deb < 0.25 and mom_deb < 0.20 and tp_deb < 0.15):
        return "🔴 EL MURO: El Débil está asfixiado. Cero momentum (Mom < 0.20) y nula profundidad (TP < 15%). LUZ VERDE NO."

    elif (min_corrido >= 35 and jerarquia_pre == "Fuerzas Parejas" and estado_goles == False and 
          apm_global_fav < 0.45 and apm_global_deb < 0.45 and mom_fav < 0.4 and mom_deb < 0.4 and 
          tp_fav < 0.20 and tp_deb < 0.20):
        return "🔴 PACTO DE NO AGRESIÓN: 0-0 congelado. Ambos equipos anulados (APM < 0.45, TP < 20%). LUZ VERDE NO."

    elif (min_corrido >= 40 and estado_goles == False and tp_fav < 0.15 and tp_deb < 0.15):
        return "🔴 DOMINIO ESTÉRIL: Minuto 40+. 0-0 con posesiones inútiles. Nadie pisa el área (TP < 15%). LUZ VERDE NO."

    else:
        return None


# ==================================================================
# 3. MOTOR PRINCIPAL: ORÁCULO BTTS Y 1X2
# ==================================================================
def procesar_oraculo_btts(m_rad, gl_rad, gv_rad, al_rad, av_rad, atq_tot_loc, atq_tot_vis,
                          c_loc_hist, c_vis_hist, cuota_act, seleccion_final_rad, 
                          perfil_riesgo, eq_loc_ui, eq_vis_ui, foto_ant=None):

    # 1. LÍMITES POR PERFIL DE RIESGO
    if "CONSERVADOR" in perfil_riesgo:
        umbral_asfixia = 0.8; mult_castigo = 0.10; umbral_gigante = 0.9; ventaja_min_exigida = 0.50; minuto_limite_si = 70
    elif "MODERADO" in perfil_riesgo:
        umbral_asfixia = 0.6; mult_castigo = 0.20; umbral_gigante = 0.7; ventaja_min_exigida = 0.20; minuto_limite_si = 78
    else: 
        umbral_asfixia = 0.4; mult_castigo = 0.50; umbral_gigante = 0.5; ventaja_min_exigida = 0.0; minuto_limite_si = 85

    # 2. CÁLCULO DINÁMICO DE MOMENTUM
    apm_global_loc = al_rad / max(1, m_rad)
    apm_global_vis = av_rad / max(1, m_rad)
    apm_local_dinamico = apm_global_loc
    apm_vis_dinamico = apm_global_vis
    texto_momentum = "Promedio Global"
    tiene_momentum = False
    
    if foto_ant is not None:
        min_ant = int(foto_ant['minuto_evaluado'])
        delta_min = m_rad - min_ant
        if delta_min >= 2:
            atk_l_ant = int(foto_ant['atkp_local'])
            atk_v_ant = int(foto_ant['atkp_vis'])
            apm_local_dinamico = max(0.0, (al_rad - atk_l_ant) / delta_min)
            apm_vis_dinamico = max(0.0, (av_rad - atk_v_ant) / delta_min)
            texto_momentum = f"Últimos {delta_min} min"
            tiene_momentum = True

    # 3. MAPEO TÁCTICO
    es_loc_fav_matematico = c_loc_hist < c_vis_hist
    es_vis_fav_matematico = c_vis_hist < c_loc_hist
    dif_cuotas = abs(c_loc_hist - c_vis_hist)
    
    if c_loc_hist <= 1.35 or c_vis_hist <= 1.35: 
        jerarquia_pre = "Súper Favorito"
        fav_es_loc = es_loc_fav_matematico; fav_es_vis = es_vis_fav_matematico
    elif dif_cuotas > 0.3: 
        jerarquia_pre = "Favorito"
        fav_es_loc = es_loc_fav_matematico; fav_es_vis = es_vis_fav_matematico
    else: 
        jerarquia_pre = "Fuerzas Parejas"
        fav_es_loc = False; fav_es_vis = False

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
        goles_fav, goles_deb = gl_rad, gv_rad
        apm_global_fav, apm_global_deb = apm_global_loc, apm_global_vis
        mom_fav, mom_deb = apm_local_dinamico, apm_vis_dinamico
        tp_fav, tp_deb = tp_local, tp_visita

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

    # 4. EJECUCIÓN DE PATRONES
    patron_encontrado = None
    color_patron = "#10B981"
    bg_patron = "#ECFDF5"
    titulo_patron = "🏆 PATRÓN MATEMÁTICO DETECTADO (BTTS SÍ)"

    if seleccion_final_rad == "Sí":
        patron_encontrado = detectar_patron_btts_si(
            min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
            jerarquia_pre, apm_global_fav, apm_global_deb, apm_g_ganador, apm_g_perdedor,
            mom_combinado, diferencial_mom, mom_fav, mom_deb, mom_ganador, mom_perdedor, 
            tp_fav, tp_deb, tp_ganador, tp_perdedor
        )
    elif seleccion_final_rad == "No":
        patron_encontrado = detectar_patron_btts_no(
            min_corrido, estado_goles, lider_marcador, goles_fav, goles_deb, 
            jerarquia_pre, apm_global_fav, apm_global_deb, 
            mom_fav, mom_deb, tp_fav, tp_deb
        )
        if patron_encontrado:
            color_patron = "#EF4444" 
            bg_patron = "#FEF2F2"
            titulo_patron = "🛡️ PATRÓN DEFENSIVO DETECTADO (BTTS NO)"

    # 5. PREDICCIÓN DE MODELOS ML
    apm_rad = apm_local_dinamico + apm_vis_dinamico
    ird_rad_global = min(100.0, (apm_global_loc + apm_global_vis) * 45.0)
    
    X_rad = pd.DataFrame([{
        'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad,
        'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad_global,
        'cuota_base_audit': float(c_loc_hist), 'cuota_amenaza_audit': float(c_vis_hist)
    }])
    
    pred_1x2_rad = m1x2_rad.predict(X_rad)[0]
    pred_goles_rad = mgoles_rad.predict(X_rad)[0]
    pred_btts_rad = mbtts_rad.predict(X_rad)[0]
    
    probabilidades = mbtts_rad.predict_proba(X_rad)[0]
    prob_no = probabilidades[0]
    prob_si = probabilidades[1]

    # CANDADOS: Modificadores de Asfixia y Fuego Cruzado
    if (apm_local_dinamico < umbral_asfixia and gl_rad == 0) or (apm_vis_dinamico < umbral_asfixia and gv_rad == 0):
        prob_si = prob_si * mult_castigo
        prob_no = 1.0 - prob_si
    elif apm_local_dinamico >= 1.0 and apm_vis_dinamico >= 1.0:
        prob_si = min(0.95, prob_si * 1.50)
        prob_no = 1.0 - prob_si

    if patron_encontrado:
        if seleccion_final_rad == "Sí":
            prob_si = min(0.99, prob_si * 1.5) 
            prob_no = 1.0 - prob_si
        elif seleccion_final_rad == "No":
            prob_no = min(0.99, prob_no * 1.5)
            prob_si = 1.0 - prob_no

    winner_tactico = "Empate" if pred_1x2_rad == 1 else ("Local" if pred_1x2_rad == 2 else "Visita")

    # 6. VARIABLES UI
    if jerarquia_pre == "Súper Favorito":
        jerarquia = f"👑 Súper Favorito: {eq_loc_ui if fav_es_loc else eq_vis_ui}"
    elif jerarquia_pre == "Favorito":
        jerarquia = f"⚔️ Favorito: {eq_loc_ui if fav_es_loc else eq_vis_ui}"
    else: 
        jerarquia = "⚖️ Fuerzas Parejas"

    if apm_global_loc > apm_global_vis and (apm_global_loc - apm_global_vis) > 0.15: 
        dom_vivo = eq_loc_ui
    elif apm_global_vis > apm_global_loc and (apm_global_vis - apm_global_loc) > 0.15: 
        dom_vivo = eq_vis_ui
    else: 
        dom_vivo = "Asedio Dividido"

    # SEÑALES TÁCTICAS CLÁSICAS
    goles_actuales_totales = gl_rad + gv_rad
    alerta_señal = ""
    
    if tiene_momentum:
        if goles_deb == 1 and goles_fav == 0 and mom_fav >= umbral_gigante:
            equipo_atacando = eq_loc_ui if fav_es_loc else eq_vis_ui
            alerta_señal = f"""
            <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 12px; border-radius: 4px; margin-top: 15px;">
                <h5 style="margin-top:0; color:#15803D;">🔥 SEÑAL TÁCTICA: EL GIGANTE HERIDO</h5>
                <p style="margin:0; font-size: 0.9rem; color:#14532D;">
                El débil anotó, pero el Favorito ({equipo_atacando}) cruzó tu umbral táctico reciente con ({mom_fav:.2f} APM). Altísima probabilidad de empate inminente.
                </p>
            </div>
            """
        elif goles_fav == 1 and goles_deb == 0 and mom_fav >= umbral_gigante and mom_deb <= umbral_asfixia and apm_global_deb <= umbral_asfixia:
            equipo_asfixiado = eq_vis_ui if fav_es_loc else eq_loc_ui
            alerta_señal = f"""
            <div style="background-color: #FEF2F2; border-left: 5px solid #DC2626; padding: 12px; border-radius: 4px; margin-top: 15px;">
                <h5 style="margin-top:0; color:#991B1B;">🛡️ SEÑAL TÁCTICA: ASFIXIA TOTAL</h5>
                <p style="margin:0; font-size: 0.9rem; color:#7F1D1D;">
                El Favorito anotó y no quita el pie del acelerador. El equipo {equipo_asfixiado} está completamente anulado (Global: {apm_global_deb:.2f} APM | Reciente: {mom_deb:.2f} APM). Escenario letal para el SÍ.
                </p>
            </div>
            """
        elif m_rad <= 45 and goles_actuales_totales == 0:
            if mom_fav >= 1.0 or mom_deb >= 1.0:
                if mom_fav > mom_deb:
                    atacante_fuerte = eq_loc_ui if fav_es_loc else eq_vis_ui
                    texto_riesgo = "Favorito presionando con furia"
                else:
                    atacante_fuerte = eq_vis_ui if fav_es_loc else eq_loc_ui
                    texto_riesgo = "Peligro de sorpresa del Débil"
                alerta_señal = f"""
                <div style="background-color: #FFFBEB; border-left: 5px solid #D97706; padding: 12px; border-radius: 4px; margin-top: 15px;">
                    <h5 style="margin-top:0; color:#B45309;">⚡ SEÑAL DE MOMENTUM: GOL INMINENTE (1T)</h5>
                    <p style="margin:0; font-size: 0.9rem; color:#92400E;">
                    El equipo {atacante_fuerte} bombardea el arco ({max(mom_fav, mom_deb):.2f} APM reciente). {texto_riesgo}.
                    </p>
                </div>
                """

    # CÁLCULO DE MARCADOR VISUAL
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
    elif apm_global_loc < 0.4 or apm_global_vis < 0.4:
        if apm_global_loc < 0.4 and gl_rad == 0: calc_loc = 0
        if apm_global_vis < 0.4 and gv_rad == 0: calc_vis = 0
    else:
        if pred_btts_rad == 1:
            calc_loc = max(1, calc_loc)
            calc_vis = max(1, calc_vis)

    marcador_exacto = f"{calc_loc} - {calc_vis}"

    # 7. DICTAMEN DE TRADING Y VALUE BETTING
    luz_verde = False
    alerta_accion = ""
    texto_accion = ""
    bg_color = "#F8FAFC"
    border_color = "#64748B"
    text_color = "#334155"

    cuota_justa_si = 1 / prob_si if prob_si > 0.01 else 99.0
    cuota_justa_no = 1 / prob_no if prob_no > 0.01 else 99.0
    
    if seleccion_final_rad == "Sí":
        ventaja = cuota_act - cuota_justa_si
        prob_mercado = prob_si
        cuota_justa = cuota_justa_si
        if m_rad >= minuto_limite_si:
            alerta_accion = f"⏳ **BLOQUEO POR RELOJ (LOTERÍA)**"
            texto_accion = f"Tu Perfil prohíbe apostar a goles después del minuto {minuto_limite_si}."
            bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
        elif ventaja >= ventaja_min_exigida:
            alerta_accion = f"🔥 **¡DISPARA AL SÍ AHORA!**"
            texto_accion = f"La cuota justa es **{cuota_justa:.2f}** y te ofrecen **{cuota_act:.2f}**. Entra ya."
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige ganancia superior."
        else:
            if (cuota_justa - cuota_act) <= 0.40 and m_rad < 75:
                alerta_accion = f"⏳ **PACIENCIA (ESPERA A QUE SUBA EL SÍ)**"
                texto_accion = f"Pagan muy poco (**{cuota_act:.2f}**). La cuota justa es **{cuota_justa:.2f}**. Espera."
                bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
            else:
                alerta_accion = f"🚫 **DESCARTADO (TRAMPA EN EL SÍ)**"
                texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_act:.2f}**. Aborta."
                bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
    else: 
        ventaja = cuota_act - cuota_justa_no
        prob_mercado = prob_no
        cuota_justa = cuota_justa_no
        if ventaja >= ventaja_min_exigida:
            alerta_accion = f"🛡️ **¡DISPARA AL NO AHORA!**"
            texto_accion = f"Cuota justa: **{cuota_justa:.2f}** / Te ofrecen: **{cuota_act:.2f}**. ¡Mete la plata YA!"
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = f"🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige mayor margen."
        else:
            alerta_accion = f"🚫 **LLEGASTE TARDE AL NO**"
            texto_accion = f"Cuota justa era **{cuota_justa:.2f}** y ya la tumbaron a **{cuota_act:.2f}**. Pérdida matemática."
            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"

    color_winner = "#0EA5E9" if winner_tactico == "Local" else ("#F59E0B" if winner_tactico == "Empate" else "#8B5CF6")

    # EMPAQUETADO FINAL HACIA STREAMLIT
    return {
        "luz_verde": luz_verde,
        "jerarquia": jerarquia,
        "dom_vivo": dom_vivo,
        "marcador_exacto": marcador_exacto,
        "winner_tactico": winner_tactico,
        "color_winner": color_winner,
        "tp_local": tp_local,
        "tp_visita": tp_visita,
        "ird_rad_global": ird_rad_global,
        "alerta_señal": alerta_señal,
        "patron_encontrado": patron_encontrado,
        "titulo_patron": titulo_patron,
        "color_patron": color_patron,
        "bg_patron": bg_patron,
        "alerta_accion": alerta_accion,
        "texto_accion": texto_accion,
        "bg_color": bg_color,
        "border_color": border_color,
        "text_color": text_color,
        "prob_mercado": prob_mercado,
        "apm_global_comb": apm_global_loc + apm_global_vis,
        "apm_rad": apm_rad,
        "texto_momentum": texto_momentum
    }

# ==================================================================
# 4. MOTOR PRINCIPAL: ORÁCULO LÍNEA DE GOLES
# ==================================================================
def procesar_oraculo_goles(m_rad, gl_rad, gv_rad, al_rad, av_rad, atq_tot_loc, atq_tot_vis,
                           c_loc_hist, c_vis_hist, cuota_act, linea_seleccionada, 
                           perfil_riesgo_g, foto_ant=None):
    
    # 1. LIMITES POR PERFIL
    if "CONSERVADOR" in perfil_riesgo_g: ventaja_min_g = 0.50; minuto_limite_g = 70
    elif "MODERADO" in perfil_riesgo_g: ventaja_min_g = 0.20; minuto_limite_g = 78
    else: ventaja_min_g = 0.0; minuto_limite_g = 85

    # 2. CALCULO APM DINÁMICO
    apm_global_loc = al_rad / max(1, m_rad)
    apm_global_vis = av_rad / max(1, m_rad)
    apm_local_dinamico = apm_global_loc
    apm_vis_dinamico = apm_global_vis
    texto_momentum_g = "Promedio Global"
    
    if foto_ant is not None:
        min_ant = int(foto_ant['minuto_evaluado'])
        delta_min = m_rad - min_ant
        if delta_min >= 2:
            apm_local_dinamico = max(0.0, (al_rad - int(foto_ant['atkp_local'])) / delta_min)
            apm_vis_dinamico = max(0.0, (av_rad - int(foto_ant['atkp_vis'])) / delta_min)
            texto_momentum_g = f"Últimos {delta_min} min"

    apm_rad_g = apm_local_dinamico + apm_vis_dinamico
    ird_rad_global = min(100.0, (apm_global_loc + apm_global_vis) * 45.0)
    
    X_rad_g = pd.DataFrame([{
        'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad,
        'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad_global,
        'cuota_base_audit': float(c_loc_hist), 'cuota_amenaza_audit': float(c_vis_hist)
    }])
    
    pred_goles_rad = mgoles_rad.predict(X_rad_g)[0]
    
    # MATEMÁTICA DE POISSON
    nums_linea = re.findall(r'\d+\.\d+|\d+', linea_seleccionada)
    linea_operacion = float(nums_linea[0]) if nums_linea else 2.5
    goles_techo_under = int(math.floor(linea_operacion))
    
    lam = max(0.1, float(pred_goles_rad))
    p_under = 0.0
    for k in range(goles_techo_under + 1):
        p_under += (math.exp(-lam) * (lam**k)) / math.factorial(k)
        
    prob_goles_menos = p_under
    prob_goles_mas = 1.0 - p_under
    
    tp_local = al_rad / atq_tot_loc if atq_tot_loc > 0 else 0.0
    tp_visita = av_rad / atq_tot_vis if atq_tot_vis > 0 else 0.0
    
    # APLICACIÓN DE FUEGO CRUZADO Y ASFIXIA A POISSON
    if apm_rad_g >= 1.5 and tp_local > 0.30 and tp_visita > 0.30: 
        prob_goles_mas = min(0.95, prob_goles_mas * 1.30)
        prob_goles_menos = 1.0 - prob_goles_mas
    elif apm_rad_g <= 0.6 and tp_local < 0.20 and tp_visita < 0.20: 
        prob_goles_menos = min(0.95, prob_goles_menos * 1.30)
        prob_goles_mas = 1.0 - prob_goles_menos

    cuota_justa_mas = 1 / prob_goles_mas if prob_goles_mas > 0.01 else 99.0
    cuota_justa_menos = 1 / prob_goles_menos if prob_goles_menos > 0.01 else 99.0
    
    luz_verde = False
    alerta_accion = ""
    texto_accion = ""
    bg_color = "#F8FAFC"
    border_color = "#64748B"
    text_color = "#334155"

    if "Más" in linea_seleccionada:
        ventaja = cuota_act - cuota_justa_mas
        prob_mercado = prob_goles_mas
        cuota_justa = cuota_justa_mas
        if m_rad >= minuto_limite_g:
            alerta_accion = "⏳ **BLOQUEO POR RELOJ**"
            texto_accion = f"Tu Perfil prohíbe apostar a goles tardíos (min > {minuto_limite_g})."
            bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
        elif ventaja >= ventaja_min_g:
            alerta_accion = "🔥 **¡DISPARA AL OVER AHORA!**"
            texto_accion = f"Justa: **{cuota_justa:.2f}** / Ofrecen: **{cuota_act:.2f}**."
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = "🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige más."
        else:
            alerta_accion = "🚫 **DESCARTADO (TRAMPA EN EL OVER)**"
            texto_accion = f"Matemáticamente en contra. Aborta."
            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
    else:
        ventaja = cuota_act - cuota_justa_menos
        prob_mercado = prob_goles_menos
        cuota_justa = cuota_justa_menos
        if ventaja >= ventaja_min_g:
            alerta_accion = "🛡️ **¡DISPARA AL UNDER AHORA!**"
            texto_accion = f"Justa: **{cuota_justa:.2f}** / Ofrecen: **{cuota_act:.2f}**."
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = "🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor, pero tu Perfil exige más."
        else:
            alerta_accion = "🚫 **LLEGASTE TARDE AL UNDER**"
            texto_accion = f"Pérdida matemática."
            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"

    return {
        "luz_verde": luz_verde,
        "alerta_accion": alerta_accion,
        "texto_accion": texto_accion,
        "bg_color": bg_color,
        "border_color": border_color,
        "text_color": text_color,
        "prob_mercado": prob_mercado,
        "apm_rad_g": apm_rad_g,
        "texto_momentum_g": texto_momentum_g
    }

# ==================================================================
# 4. MOTOR PRINCIPAL: ORÁCULO LÍNEA DE GOLES (POISSON + IA)
# ==================================================================
def procesar_oraculo_goles(m_rad, gl_rad, gv_rad, al_rad, av_rad, atq_tot_loc, atq_tot_vis,
                           c_loc_hist, c_vis_hist, cuota_act, linea_seleccionada, 
                           perfil_riesgo_g, foto_ant=None):
    
    import math
    import re
    import pandas as pd
    import joblib

    # Intentamos cargar el modelo de goles
    try:
        mgoles_rad = joblib.load('modelo_goles.pkl')
    except:
        return {"alerta_accion": "Error", "texto_accion": "No se encontró el modelo de goles."}

    # -------------------------------------------------------------
    # 1. LÍMITES DINÁMICOS POR PERFIL DE RIESGO (GOLES)
    # -------------------------------------------------------------
    if "CONSERVADOR" in perfil_riesgo_g: 
        ventaja_min_g = 0.50
        minuto_limite_g = 70
        umbral_fuego = 1.8     # Exige un tiroteo brutal (APM > 1.8) para creerle al Over
        umbral_asfixia = 0.8   # Se asusta rápido: si el APM baja de 0.8, ya apoya el Under
        tp_exigido = 0.40      # Exige muchísima profundidad (40%) para el Over
    elif "MODERADO" in perfil_riesgo_g: 
        ventaja_min_g = 0.20
        minuto_limite_g = 78
        umbral_fuego = 1.5     # Fuego cruzado estándar (APM > 1.5)
        umbral_asfixia = 0.6   # Asfixia estándar
        tp_exigido = 0.30      # Profundidad normal (30%)
    else: # AGRESIVO / KAMIKAZE
        ventaja_min_g = 0.0
        minuto_limite_g = 85
        umbral_fuego = 1.2     # Con un ritmo levemente alto ya se lanza al Over
        umbral_asfixia = 0.4   # Exige que el partido esté muertísimo para apoyar el Under
        tp_exigido = 0.20      # Se conforma con poca profundidad (20%)

    # -------------------------------------------------------------
    # 2. CÁLCULO DE MOMENTUM DINÁMICO (FILTRO ANTI-RUIDO)
    # -------------------------------------------------------------
    apm_global_loc = al_rad / max(1, m_rad)
    apm_global_vis = av_rad / max(1, m_rad)
    apm_local_dinamico = apm_global_loc
    apm_vis_dinamico = apm_global_vis
    texto_momentum_g = "Promedio Global"
    
    if foto_ant is not None:
        min_ant = int(foto_ant['minuto_evaluado'])
        delta_min = m_rad - min_ant
        if delta_min >= 2:
            apm_local_dinamico = max(0.0, (al_rad - int(foto_ant['atkp_local'])) / delta_min)
            apm_vis_dinamico = max(0.0, (av_rad - int(foto_ant['atkp_vis'])) / delta_min)
            texto_momentum_g = f"Últimos {delta_min} min"

    apm_rad_g = apm_local_dinamico + apm_vis_dinamico
    ird_rad_global = min(100.0, (apm_global_loc + apm_global_vis) * 45.0)
    
    # -------------------------------------------------------------
    # 3. PREDICCIÓN IA (BASE PARA POISSON)
    # -------------------------------------------------------------
    X_rad_g = pd.DataFrame([{
        'minuto_evaluado': m_rad, 'goles_local': gl_rad, 'goles_vis': gv_rad,
        'atkp_local': al_rad, 'atkp_vis': av_rad, 'ird_calculado': ird_rad_global,
        'cuota_base_audit': float(c_loc_hist), 'cuota_amenaza_audit': float(c_vis_hist)
    }])
    
    # La IA predice la cantidad de goles esperados para el partido completo
    pred_goles_rad = mgoles_rad.predict(X_rad_g)[0]
    
    # -------------------------------------------------------------
    # 4. LEY DE POISSON
    # -------------------------------------------------------------
    # Extraemos el número de la línea seleccionada (ej. de "Más de 2.5" sacamos 2.5)
    nums_linea = re.findall(r'\d+\.\d+|\d+', linea_seleccionada)
    linea_operacion = float(nums_linea[0]) if nums_linea else 2.5
    
    # El techo para calcular el UNDER (Si es 2.5, el techo es 2 goles)
    goles_techo_under = int(math.floor(linea_operacion))
    
    # Nuestro Lambda (λ) es lo que predijo la IA
    lam = max(0.1, float(pred_goles_rad))
    p_under = 0.0
    
    # Sumatoria de Poisson para 0, 1, ..., hasta el techo
    for k in range(goles_techo_under + 1):
        p_under += (math.exp(-lam) * (lam**k)) / math.factorial(k)
        
    prob_goles_menos = p_under
    prob_goles_mas = 1.0 - p_under
    
    # -------------------------------------------------------------
    # 5. EL SEGURO TÁCTICO (MODIFICADORES DE PROBABILIDAD)
    # -------------------------------------------------------------
    tp_local = al_rad / atq_tot_loc if atq_tot_loc > 0 else 0.0
    tp_visita = av_rad / atq_tot_vis if atq_tot_vis > 0 else 0.0
    
    # Premio al Over si hay Fuego Cruzado y Profundidad (Según tu perfil)
    if apm_rad_g >= umbral_fuego and tp_local > tp_exigido and tp_visita > tp_exigido: 
        prob_goles_mas = min(0.95, prob_goles_mas * 1.30)
        prob_goles_menos = 1.0 - prob_goles_mas
        
    # Premio al Under si hay Asfixia o partido aburrido (Según tu perfil)
    elif apm_rad_g <= umbral_asfixia and tp_local < (tp_exigido - 0.10) and tp_visita < (tp_exigido - 0.10): 
        prob_goles_menos = min(0.95, prob_goles_menos * 1.30)
        prob_goles_mas = 1.0 - prob_goles_menos

    # -------------------------------------------------------------
    # 6. DICTAMEN DE TRADING Y VALUE BETTING
    # -------------------------------------------------------------
    cuota_justa_mas = 1 / prob_goles_mas if prob_goles_mas > 0.01 else 99.0
    cuota_justa_menos = 1 / prob_goles_menos if prob_goles_menos > 0.01 else 99.0
    
    luz_verde = False
    alerta_accion = ""
    texto_accion = ""
    bg_color = "#F8FAFC"
    border_color = "#64748B"
    text_color = "#334155"

    if "Más" in linea_seleccionada:
        ventaja = cuota_act - cuota_justa_mas
        prob_mercado = prob_goles_mas
        cuota_justa = cuota_justa_mas
        
        if m_rad >= minuto_limite_g:
            alerta_accion = "⏳ **BLOQUEO POR RELOJ (LOTERÍA)**"
            texto_accion = f"Tu Perfil prohíbe apostar a goles tardíos (min > {minuto_limite_g})."
            bg_color = "#FFFBEB"; border_color = "#F59E0B"; text_color = "#92400E"
        elif ventaja >= ventaja_min_g:
            alerta_accion = "🔥 **¡DISPARA AL OVER AHORA!**"
            texto_accion = f"Justa: **{cuota_justa:.2f}** / Ofrecen: **{cuota_act:.2f}**."
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = "🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige más ganancia."
        else:
            alerta_accion = "🚫 **DESCARTADO (TRAMPA EN EL OVER)**"
            texto_accion = f"Matemáticamente en contra. Aborta."
            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"
            
    else:
        ventaja = cuota_act - cuota_justa_menos
        prob_mercado = prob_goles_menos
        cuota_justa = cuota_justa_menos
        
        if ventaja >= ventaja_min_g:
            alerta_accion = "🛡️ **¡DISPARA AL UNDER AHORA!**"
            texto_accion = f"Justa: **{cuota_justa:.2f}** / Ofrecen: **{cuota_act:.2f}**."
            bg_color = "#ECFDF5"; border_color = "#10B981"; text_color = "#064E3B"
            luz_verde = True
        elif ventaja >= 0:
            alerta_accion = "🛡️ **BLOQUEO POR PERFIL DE RIESGO**"
            texto_accion = f"Hay valor (Justa: **{cuota_justa:.2f}**), pero tu Perfil exige más."
        else:
            alerta_accion = "🚫 **LLEGASTE TARDE AL UNDER**"
            texto_accion = f"Pérdida matemática."
            bg_color = "#FEF2F2"; border_color = "#EF4444"; text_color = "#991B1B"

    # EMPAQUETADO HACIA STREAMLIT
    return {
        "luz_verde": luz_verde,
        "alerta_accion": alerta_accion,
        "texto_accion": texto_accion,
        "bg_color": bg_color,
        "border_color": border_color,
        "text_color": text_color,
        "prob_mercado": prob_mercado,
        "apm_rad_g": apm_rad_g,
        "texto_momentum_g": texto_momentum_g
    }
