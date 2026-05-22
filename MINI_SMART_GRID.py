"""
=============================================================
  MINI SMART GRID — Simulador de Nodo IoT
=============================================================

REQUISITOS:
  pip install paho-mqtt
"""

import paho.mqtt.client as mqtt
import time
import math
import random
import json
from datetime import datetime

# ── CONFIGURACIÓN ─────────────────────────────────────────────
BROKER_HOST = "localhost"   # Cambia si el broker está en otra PC
BROKER_PORT = 1883
INTERVALO   = 5             # Segundos entre cada publicación

# Tópicos MQTT (uno por nodo)
TOPICO_NODO1 = "/smartgrid/nodo1/consumo"
TOPICO_NODO2 = "/smartgrid/nodo2/consumo"

# Límite máximo de consumo en watts (para las alertas)
UMBRAL_MAX = 400  # watts

# ── FUNCIÓN: Genera watts realistas según la hora ─────────────
def generar_consumo(hora, minuto, ruido=True):
    """
    Simula el consumo eléctrico típico de un espacio universitario.
    Tiene picos a las 7am, 1pm y 8pm (horarios de mayor actividad).

    Parámetros:
        hora   (int): hora del día (0-23)
        minuto (int): minuto actual (0-59)
        ruido  (bool): agrega variación aleatoria realista

    Retorna:
        float: consumo en watts
    """
    t = hora + minuto / 60.0  # hora decimal (ej: 7.5 = 7:30am)

    # Patrón base con tres picos usando funciones seno
    pico_manana  = 180 * math.exp(-0.5 * ((t - 7.0) / 1.2) ** 2)   # Pico 7am
    pico_mediodia = 200 * math.exp(-0.5 * ((t - 13.0) / 1.5) ** 2) # Pico 1pm
    pico_noche   = 160 * math.exp(-0.5 * ((t - 20.0) / 1.0) ** 2)  # Pico 8pm

    # Consumo base que nunca baja de ~50W (equipos en standby)
    base = 50

    consumo = base + pico_manana + pico_mediodia + pico_noche

    # Ruido gaussiano para simular variaciones reales (±10%)
    if ruido:
        consumo += random.gauss(0, consumo * 0.08)

    # Garantiza que no baje de 30W ni suba de 500W
    return round(max(30.0, min(500.0, consumo)), 2)


# ── CALLBACKS MQTT ────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado al broker MQTT correctamente")
    else:
        print(f"Error de conexión. Código: {rc}")
        print("    Verifica que Mosquitto esté corriendo (Integrante 2)")

def on_publish(client, userdata, mid):
    pass  # Confirmación silenciosa de publicación exitosa


# ── PROGRAMA PRINCIPAL ────────────────────────────────────────
def main():
    print("=" * 55)
    print("  SIMULADOR DE NODO IoT — Mini Smart Grid")
    print("=" * 55)
    print(f"  Broker : {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Tópicos: {TOPICO_NODO1}")
    print(f"           {TOPICO_NODO2}")
    print(f"  Intervalo: cada {INTERVALO} segundos")
    print(f"  Umbral máximo: {UMBRAL_MAX}W")
    print("=" * 55)
    print("  Presiona Ctrl+C para detener\n")

    # Crear cliente MQTT
    cliente = mqtt.Client(client_id="nodo_simulado_integrante1")
    cliente.on_connect = on_connect
    cliente.on_publish = on_publish

    # Conectar al broker
    try:
        cliente.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except ConnectionRefusedError:
        print("No se pudo conectar al broker.")
        print("Asegúrate de que Mosquitto esté instalado y corriendo.")
        print("Comando para iniciar: mosquitto -v")
        return

    # Iniciar loop de red en segundo plano
    cliente.loop_start()
    time.sleep(1)  # Espera breve para que se establezca la conexión

    # ── LOOP PRINCIPAL: publica datos indefinidamente ──────────
    try:
        while True:
            ahora   = datetime.now()
            hora    = ahora.hour
            minuto  = ahora.minute

            # Generar consumo para cada nodo (con variación entre ellos)
            watts_nodo1 = generar_consumo(hora, minuto)
            watts_nodo2 = generar_consumo(hora, minuto) * random.uniform(0.7, 1.1)
            watts_nodo2 = round(max(30.0, min(500.0, watts_nodo2)), 2)

            # Construir mensaje JSON con metadatos
            mensaje_nodo1 = {
                "nodo":      "nodo1",
                "timestamp": ahora.isoformat(),
                "hora":      hora,
                "minuto":    minuto,
                "watts":     watts_nodo1,
                "alerta":    watts_nodo1 > UMBRAL_MAX
            }
            mensaje_nodo2 = {
                "nodo":      "nodo2",
                "timestamp": ahora.isoformat(),
                "hora":      hora,
                "minuto":    minuto,
                "watts":     watts_nodo2,
                "alerta":    watts_nodo2 > UMBRAL_MAX
            }

            # Publicar en MQTT
            cliente.publish(TOPICO_NODO1, json.dumps(mensaje_nodo1), qos=1)
            cliente.publish(TOPICO_NODO2, json.dumps(mensaje_nodo2), qos=1)

            # Mostrar en consola con indicador de alerta
            alerta1 = "ALERTA" if mensaje_nodo1["alerta"] else "OK"
            alerta2 = "ALERTA" if mensaje_nodo2["alerta"] else "OK"

            print(f"[{ahora.strftime('%H:%M:%S')}] "
                  f"Nodo1: {watts_nodo1:6.1f}W {alerta1} | "
                  f"Nodo2: {watts_nodo2:6.1f}W {alerta2}")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print("\n\n  Simulador detenido por el usuario.")
        print("  Desconectando del broker...")
        cliente.loop_stop()
        cliente.disconnect()
        print("¡Hasta luego!")


if __name__ == "__main__":
    main()
