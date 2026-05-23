import paho.mqtt.client as mqtt
import time

BROKER = "localhost"  
TOPICO = "/smartgrid/prueba"
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conexión al BROKER exitosa")
    else:
        print("Error al conectar al BROKER, código de error:", rc)

client = mqtt.Client()
client.on_connect = on_connect

print(f"Conectando a {BROKER}...")
client.connect(BROKER, 1883, 60)

client.loop_start()
time.sleep(2)  # Espera para asegurar la conexión

mensaje = "Hola desde MQTT"
client.publish(TOPICO, mensaje)
print(f"Mensaje publicado en el tópico '{TOPICO}': {mensaje}")

time.sleep(2)  # Espera para asegurar que el mensaje se publique
client.loop_stop()
client.disconnect()
print("Desconectado del BROKER")