"""
MINI SMART GRID — Dashboard
Redes Inteligentes 2026
=======================================
Tópicos sincronizados con el repo v1.0.0:
  smartGrid.py    → /smartgrid/nodo1/consumo  /smartgrid/nodo2/consumo
  ia_predictiva.py→ /smartgrid/control  (publica ON/OFF)

NOTA: ia_predictiva.py no publica la predicción en MQTT.
      Este dashboard la calcula localmente con el mismo modelo
      usando los datos que llegan del nodo1.

pip install dash plotly paho-mqtt pandas dash-bootstrap-components joblib scikit-learn
python dashboard.py  →  http://localhost:8050
"""

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import paho.mqtt.client as mqtt
import threading
import json
import joblib
import os
import numpy as np
import pandas as pd
from collections import deque
from datetime import datetime

# ─────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
#MQTT_BROKER    = "localhost"             # ← IP del broker 
MQTT_BROKER = "broker.hivemq.com"         # Conexion desde diferentes laptops
MQTT_PORT      = 1883
TOPICO_NODO1   = "/smartgrid/nodo1/consumo"   # smartGrid.py
TOPICO_NODO2   = "/smartgrid/nodo2/consumo"   # smartGrid.py
TOPICO_CTRL    = "/smartgrid/control"         # ia_predictiva.py publica ON/OFF
TOPICO_PRED    = "/smartgrid/prediccion"      
MAX_PUNTOS     = 120
UMBRAL_ALERTA  = 320    # 80 % de 400 W → línea amarilla
UMBRAL_MAX     = 400    # igual que smartGrid.py → línea roja

# Ruta al modelo entrenado 
MODELO_PATH = "modelo_regresion_smartgrid.pkl"

# ─────────────────────────────────────────────────────────────
#  CARGAR MODELO (para calcular predicción localmente)
# ─────────────────────────────────────────────────────────────
modelo_ia = None
if os.path.exists(MODELO_PATH):
    try:
        modelo_ia = joblib.load(MODELO_PATH)
        print(f"[IA] Modelo cargado desde {MODELO_PATH}")
    except Exception as e:
        print(f"[IA] No se pudo cargar el modelo: {e}")
else:
    print(f"[IA] {MODELO_PATH} no encontrado — predicción desactivada")
    print(f"     Copia modelo_regresion_smartgrid.pkl junto a dashboard.py")

def predecir_local(hora, minuto, watts):
    """
    Replica exactamente la lógica de ia_predictiva.py para calcular
    la predicción sin un tópico extra.
    """
    if modelo_ia is None:
        return None
    try:
        ct1 = watts * 0.98
        ct2 = watts * 0.95
        ct3 = watts * 0.90
        X = pd.DataFrame([[hora, minuto, ct1, ct2, ct3]],
                         columns=['hora', 'minuto', 'consumo_t_1',
                                  'consumo_t_2', 'consumo_t_3'])
        return round(float(modelo_ia.predict(X)[0]), 2)
    except Exception as e:
        print(f"[IA] Error en predicción: {e}")
        return None

# ─────────────────────────────────────────────────────────────
#  BUFFER DE DATOS
# ─────────────────────────────────────────────────────────────
datos = {
    "tiempo":     deque(maxlen=MAX_PUNTOS),
    "nodo1":      deque(maxlen=MAX_PUNTOS),
    "nodo2":      deque(maxlen=MAX_PUNTOS),
    "prediccion": deque(maxlen=MAX_PUNTOS),
    "control":    "ON",
    "conectado":  False,
    "ultimo_msg": "—",
    "total_msgs": 0,
}

# ─────────────────────────────────────────────────────────────
#  CLIENTE MQTT
# ─────────────────────────────────────────────────────────────
def extraer_watts(payload: str) -> float:
    try:
        return float(json.loads(payload).get("watts", 0))
    except Exception:
        return float(payload.strip())

def on_connect(client, userdata, flags, rc):
    datos["conectado"] = (rc == 0)
    if rc == 0:
        for t in [TOPICO_NODO1, TOPICO_NODO2, TOPICO_CTRL, TOPICO_PRED]:
            client.subscribe(t)
        print(f"[MQTT] Conectado a {MQTT_BROKER}")
    else:
        print(f"[MQTT] Error rc={rc}")

def on_disconnect(client, userdata, rc):
    datos["conectado"] = False

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        ahora   = datetime.now().strftime("%H:%M:%S")
        datos["ultimo_msg"] = f"{ahora} · {msg.topic}"
        datos["total_msgs"] += 1

        if msg.topic == TOPICO_NODO1:
            w = extraer_watts(payload)
            datos["nodo1"].append(w)
            datos["tiempo"].append(ahora)
            # Predicción local usando el mismo modelo que ia_predictiva.py
            try:
                j   = json.loads(payload)
                pred = predecir_local(j["hora"], j["minuto"], w)
                if pred is not None:
                    datos["prediccion"].append(pred)
            except Exception:
                pass

        elif msg.topic == TOPICO_NODO2:
            datos["nodo2"].append(extraer_watts(payload))

        elif msg.topic == TOPICO_PRED:
            datos["prediccion"].append(extraer_watts(payload))

        elif msg.topic == TOPICO_CTRL:
            datos["control"] = payload.strip().upper()

    except Exception as e:
        print(f"[MQTT] Error: {e}")

def iniciar_mqtt():
    client = mqtt.Client()
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] No se pudo conectar a {MQTT_BROKER}:{MQTT_PORT} — {e}")

threading.Thread(target=iniciar_mqtt, daemon=True).start()

# ─────────────────────────────────────────────────────────────
#  APP DASH
# ─────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;600;800&display=swap",
    ],
    title="Smart Grid · Dashboard",
)

C_BG     = "#060b14"
C_PANEL  = "#0d1826"
C_BORDE  = "#0e4a6e"
C_CYAN   = "#00d4ff"
C_VERDE  = "#00ff9d"
C_AMAR   = "#ffc400"
C_ROJO   = "#ff4060"
C_TEXTO  = "#c8e6f7"

S_CARD = {
    "background": C_PANEL, "border": f"1px solid {C_BORDE}",
    "borderRadius": "4px", "padding": "18px 22px", "marginBottom": "16px",
    "boxShadow": "0 0 18px rgba(0,212,255,0.07)",
    "fontFamily": "'Exo 2', sans-serif", "color": C_TEXTO,
}
S_LABEL = {
    "fontFamily": "'Share Tech Mono', monospace", "fontSize": "11px",
    "color": C_CYAN, "letterSpacing": "3px", "textTransform": "uppercase",
    "marginBottom": "10px", "borderBottom": f"1px solid {C_BORDE}",
    "paddingBottom": "8px",
}
S_MONO_BIG = {
    "fontFamily": "'Share Tech Mono', monospace",
    "fontSize": "2.6rem", "fontWeight": "800", "lineHeight": "1",
}
S_UNIT = {
    "fontFamily": "'Share Tech Mono', monospace",
    "fontSize": "0.85rem", "color": "#6a9bb5", "marginLeft": "4px",
}

def kpi(titulo, val_id, unidad, color=C_CYAN):
    return html.Div([
        html.Div(titulo, style=S_LABEL),
        html.Div([
            html.Span("—", id=val_id, style={**S_MONO_BIG, "color": color}),
            html.Span(unidad, style=S_UNIT),
        ]),
    ], style={**S_CARD, "minHeight": "100px"})

def alerta_row(icono, texto, color):
    return html.Div([
        html.Span(icono + " ", style={"color": color}),
        html.Span(texto, style={"color": C_TEXTO, "fontSize": "12px"}),
    ], style={
        "fontFamily": "'Share Tech Mono', monospace", "marginBottom": "9px",
        "padding": "7px 10px", "background": "rgba(0,212,255,0.04)",
        "borderLeft": f"2px solid {color}", "borderRadius": "2px",
    })

LAYOUT_G = dict(
    plot_bgcolor=C_BG, paper_bgcolor=C_PANEL,
    font=dict(family="Share Tech Mono, monospace", color=C_TEXTO, size=11),
    margin=dict(l=40, r=20, t=10, b=40),
    xaxis=dict(gridcolor=C_BORDE, gridwidth=0.5, showgrid=True,
               linecolor=C_BORDE, zeroline=False, tickfont=dict(size=10)),
    yaxis=dict(gridcolor=C_BORDE, gridwidth=0.5, showgrid=True,
               linecolor=C_BORDE, zeroline=False, tickfont=dict(size=10)),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C_BORDE,
                borderwidth=1, font=dict(size=10)),
    hovermode="x unified",
)

app.layout = html.Div(style={"backgroundColor": C_BG, "minHeight": "100vh",
                              "padding": "24px 28px",
                              "fontFamily": "'Exo 2', sans-serif"}, children=[
    # ── HEADER ──
    html.Div([
        html.Div([
            html.Div("◈", style={"color": C_CYAN, "fontSize": "1.8rem", "marginRight": "12px"}),
            html.Div([
                html.H1("MINI SMART GRID", style={
                    "fontFamily": "'Share Tech Mono', monospace", "color": C_CYAN,
                    "fontSize": "1.5rem", "margin": "0", "letterSpacing": "6px",
                }),
                html.Div("Redes Inteligentes · Dashboard de Monitoreo en Tiempo Real", style={
                    "color": "#4a7a99", "fontSize": "0.75rem",
                    "letterSpacing": "2px", "fontFamily": "'Share Tech Mono', monospace",
                }),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div([
            html.Div(id="conn-status"),
            html.Div(id="reloj", style={
                "fontFamily": "'Share Tech Mono', monospace", "fontSize": "0.75rem",
                "color": "#4a7a99", "marginTop": "4px", "textAlign": "right",
            }),
        ], style={"textAlign": "right"}),
    ], style={
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
        "marginBottom": "24px", "borderBottom": f"1px solid {C_BORDE}", "paddingBottom": "16px",
    }),

    # ── KPIs ──
    dbc.Row([
        dbc.Col(kpi("CONSUMO NODO 1", "kpi-n1", "W", C_CYAN),  md=3),
        dbc.Col(kpi("CONSUMO NODO 2", "kpi-n2", "W", C_VERDE), md=3),
        dbc.Col(kpi("PREDICCIÓN IA",  "kpi-pr", "W", C_AMAR),  md=3),
        dbc.Col(html.Div([
            html.Div("CONTROL DE CARGA", style=S_LABEL),
            html.Span("ON", id="ctrl-badge", style={**S_MONO_BIG, "color": C_VERDE}),
            html.Div(id="ctrl-desc", style={
                "fontSize": "0.7rem", "color": "#4a7a99",
                "fontFamily": "'Share Tech Mono', monospace", "marginTop": "6px",
            }),
        ], style={**S_CARD, "minHeight": "100px"}), md=3),
    ], className="g-3"),

    # ── GRÁFICA PRINCIPAL ──
    html.Div([
        html.Div("CONSUMO REAL vs PREDICCIÓN DEL MODELO", style=S_LABEL),
        dcc.Graph(id="graf-main", config={"displayModeBar": False}, style={"height": "320px"}),
    ], style=S_CARD),

    # ── FILA INFERIOR ──
    dbc.Row([
        dbc.Col(html.Div([
            html.Div("COMPARATIVO NODOS (últimos 20 puntos)", style=S_LABEL),
            dcc.Graph(id="graf-nodos", config={"displayModeBar": False}, style={"height": "220px"}),
        ], style=S_CARD), md=8),
        dbc.Col(html.Div([
            html.Div("ESTADO DEL SISTEMA", style=S_LABEL),
            html.Div(id="panel-estado"),
        ], style={**S_CARD, "minHeight": "280px"}), md=4),
    ], className="g-3"),

    # ── BARRA INFERIOR ──
    html.Div([
        html.Span(id="last-msg", style={
            "fontFamily": "'Share Tech Mono', monospace", "fontSize": "11px", "color": "#2a5a75",
        }),
        html.Span(id="tot-msg", style={
            "fontFamily": "'Share Tech Mono', monospace", "fontSize": "11px",
            "color": "#2a5a75", "float": "right",
        }),
    ], style={"borderTop": f"1px solid {C_BORDE}", "paddingTop": "10px", "marginTop": "8px"}),

    dcc.Interval(id="tick", interval=2000, n_intervals=0, disabled=True),
])

# ─────────────────────────────────────────────────────────────
#  CALLBACK PRINCIPAL
# ─────────────────────────────────────────────────────────────
@app.callback(
    Output("graf-main",    "figure"),
    Output("graf-nodos",   "figure"),
    Output("kpi-n1",       "children"),
    Output("kpi-n2",       "children"),
    Output("kpi-pr",       "children"),
    Output("ctrl-badge",   "children"),
    Output("ctrl-badge",   "style"),
    Output("ctrl-desc",    "children"),
    Output("conn-status",  "children"),
    Output("reloj",        "children"),
    Output("last-msg",     "children"),
    Output("tot-msg",      "children"),
    Output("panel-estado", "children"),
    Input("tick", "n_intervals"),
)
def tick(_):
    t  = list(datos["tiempo"])
    n1 = list(datos["nodo1"])
    n2 = list(datos["nodo2"])
    pr = list(datos["prediccion"])
    ct = datos["control"]
    ahora = datetime.now().strftime("%H:%M:%S")

    # KPIs
    v_n1 = f"{n1[-1]:.1f}" if n1 else "—"
    v_n2 = f"{n2[-1]:.1f}" if n2 else "—"
    v_pr = f"{pr[-1]:.1f}" if pr else "—"

    # Control badge
    if ct == "ON":
        badge_style = {**S_MONO_BIG, "color": C_VERDE}
        ctrl_desc   = "Carga activa · Sistema normal"
    else:
        badge_style = {**S_MONO_BIG, "color": C_ROJO}
        ctrl_desc   = "⚠ Carga desactivada · Umbral superado"

    # Conexión
    color_conn = C_VERDE if datos["conectado"] else C_ROJO
    texto_conn = f"MQTT CONECTADO · {MQTT_BROKER}" if datos["conectado"] else f"SIN CONEXIÓN · {MQTT_BROKER}"
    conn_children = [
        html.Span("● ", style={"color": color_conn}),
        html.Span(texto_conn, style={
            "fontFamily": "'Share Tech Mono', monospace", "fontSize": "11px",
            "letterSpacing": "2px", "color": color_conn,
        }),
    ]

    # ── Gráfica principal ──
    trazas = []
    if t and n1:
        trazas.append(go.Scatter(x=t, y=n1, name="Nodo 1 (real)",
            line=dict(color=C_CYAN, width=2), fill="tozeroy",
            fillcolor="rgba(0,212,255,0.05)", mode="lines"))
    if t and n2:
        trazas.append(go.Scatter(x=t, y=n2, name="Nodo 2 (real)",
            line=dict(color=C_VERDE, width=1.5, dash="dot"), mode="lines"))
    if t and pr:
        n = min(len(t), len(pr))
        trazas.append(go.Scatter(x=t[-n:], y=pr[-n:], name="Predicción IA",
            line=dict(color=C_AMAR, width=2, dash="dash"), mode="lines"))

    shapes = annotations = []
    if t:
        x0, x1 = t[0], t[-1]
        shapes = [
            dict(type="line", x0=x0, x1=x1, y0=UMBRAL_ALERTA, y1=UMBRAL_ALERTA,
                 line=dict(color=C_AMAR, width=1, dash="dot")),
            dict(type="line", x0=x0, x1=x1, y0=UMBRAL_MAX, y1=UMBRAL_MAX,
                 line=dict(color=C_ROJO, width=1, dash="dot")),
        ]
        annotations = [
            dict(x=x1, y=UMBRAL_ALERTA, text="Alerta 320W", showarrow=False,
                 font=dict(color=C_AMAR, size=9), xanchor="right"),
            dict(x=x1, y=UMBRAL_MAX, text="Máx 400W", showarrow=False,
                 font=dict(color=C_ROJO, size=9), xanchor="right"),
        ]

    fig_main = go.Figure(data=trazas,
        layout=go.Layout(**{**LAYOUT_G, "shapes": shapes, "annotations": annotations}))

    # ── Gráfica barras ──
    bar_t  = t[-20:]
    bar_n1 = n1[-20:] if n1 else []
    bar_n2 = n2[-20:] if n2 else []
    bars = []
    if bar_t and bar_n1:
        bars.append(go.Bar(x=bar_t, y=bar_n1, name="Nodo 1",
                           marker_color=C_CYAN, opacity=0.8))
    if bar_t and bar_n2:
        bars.append(go.Bar(x=bar_t, y=bar_n2, name="Nodo 2",
                           marker_color=C_VERDE, opacity=0.8))
    fig_bars = go.Figure(data=bars,
        layout=go.Layout(**{**LAYOUT_G, "barmode": "group"}))

    # ── Panel estado ──
    estado = []
    if not datos["conectado"]:
        estado.append(alerta_row("◌", f"Conectando a {MQTT_BROKER}:{MQTT_PORT}...", C_AMAR))
    else:
        estado.append(alerta_row("◉", "Broker MQTT activo", C_VERDE))

    if modelo_ia is not None:
        estado.append(alerta_row("◈", "Modelo IA cargado · Predicción activa", C_CYAN))
    else:
        estado.append(alerta_row("◇", "Sin modelo .pkl · Predicción inactiva", C_AMAR))

    for nodo, vals in [("Nodo1", n1), ("Nodo2", n2)]:
        if vals:
            v = vals[-1]
            if v >= UMBRAL_MAX:
                estado.append(alerta_row("▲", f"{nodo}: {v:.0f}W — UMBRAL MÁXIMO", C_ROJO))
            elif v >= UMBRAL_ALERTA:
                estado.append(alerta_row("△", f"{nodo}: {v:.0f}W — Consumo alto", C_AMAR))
            else:
                estado.append(alerta_row("◆", f"{nodo}: {v:.0f}W — Normal", C_VERDE))

    if pr and n1:
        estado.append(alerta_row("◈",
            f"IA: desviación {abs(pr[-1]-n1[-1]):.1f}W vs real", C_CYAN))

    estado.append(alerta_row("◇", f"Mensajes recibidos: {datos['total_msgs']}", "#4a7a99"))

    if not estado:
        estado = [html.Div("Esperando datos MQTT...", style={
            "color": "#4a7a99", "fontFamily": "'Share Tech Mono', monospace", "fontSize": "12px",
        })]

    return (
        fig_main, fig_bars,
        v_n1, v_n2, v_pr,
        ct, badge_style, ctrl_desc,
        conn_children, ahora,
        f"Último mensaje: {datos['ultimo_msg']}",
        f"Total mensajes: {datos['total_msgs']}",
        estado,
    )


if __name__ == "__main__":
    print("=" * 55)
    print("  MINI SMART GRID — Dashboard")
    print(f"  Broker  : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Modelo  : {'CARGADO ✓' if modelo_ia else 'NO encontrado — copia el .pkl'}")
    print("  Abre    : http://localhost:8050")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=8050)
