# Script que entrena el modelo 

# import pandas as pd
# from sklearn.linear_model import LinearRegression
# import paho.mqtt.client as mqtt
# import json

# print("Entrenando modelo de IA...")
# # El modelo oficial exige variables como: hora, minuto, consumo_t-1


# datos_entrenamiento = pd.DataFrame({
#     'hora': [7, 8, 13, 14, 20, 21],
#     'consumo_previo': [300, 200, 350, 150, 280, 100],
#     'watts_futuros': [350, 180, 380, 140, 300, 90] # Lo que queremos predecir
# })

# X_train = datos_entrenamiento[['hora', 'consumo_previo']]
# y_train = datos_entrenamiento['watts_futuros']

# modelo = LinearRegression()
# modelo.fit(X_train, y_train)
# print(f"Modelo entrenado. Score R2: {modelo.score(X_train, y_train)}")


# BROKER = "localhost"
# TOPICO_ESCUCHA = "/smartgrid/nodo1/consumo" # Escuchamos al nodo 1
# TOPICO_CONTROL = "/smartgrid/control"
# UMBRAL_MAX = 400 # Watts [cite: 88, 90]

# def on_message(client, userdata, msg):
#     # 1. Llega el dato en tiempo real
#     datos_actuales = json.loads(msg.payload.decode())
#     hora_actual = datos_actuales['hora']
#     consumo_actual = datos_actuales['watts']
    
#     # 2. Hacemos la predicción
#     X_nuevo = pd.DataFrame([[hora_actual, consumo_actual]], columns=['hora', 'consumo_previo'])
#     prediccion_watts = modelo.predict(X_nuevo)[0]
    
#     print(f"[{hora_actual}:{datos_actuales['minuto']}] Consumo Real: {consumo_actual:.1f}W | Predicción a 5 min: {prediccion_watts:.1f}W")
    
#     # 3. Lógica de control automático
#     if prediccion_watts > UMBRAL_MAX:
#         print(">>> ¡ALERTA PREDICTIVA! Apagando circuito preventivamente <<<")
#         client.publish(TOPICO_CONTROL, 'OFF')

# # Configurar red MQTT
# cliente = mqtt.Client()
# cliente.on_message = on_message
# cliente.connect(BROKER, 1883, 60)
# cliente.subscribe(TOPICO_ESCUCHA)

# print("Activo. Escuchando flujo de datos...")
# cliente.loop_forever()


# Modelo ya entrenado, por lo que se genera el siguiente script para usarlo.

import pandas as pd
import paho.mqtt.client as mqtt
import json
import joblib

# 1. CARGAR EL CEREBRO ENTRENADO
print("Cargando el modelo de IA desde el archivo local...")
modelo = joblib.load('modelo_regresion_smartgrid.pkl')
print("¡Modelo cargado exitosamente! Listo para operar.")

# 2. CONFIGURACIÓN DE RED LOCAL
BROKER = "localhost"
TOPICO_ESCUCHA = "/smartgrid/nodo1/consumo"
TOPICO_CONTROL = "/smartgrid/control"
UMBRAL_MAX = 400 # Watts

# 3. LÓGICA DE PREDICCIÓN Y CONTROL
def on_message(client, userdata, msg):
    datos_actuales = json.loads(msg.payload.decode())
    hora_actual = datos_actuales['hora']
    minuto_actual = datos_actuales['minuto']
    consumo_actual = datos_actuales['watts']
    
    
    consumo_t_1 = consumo_actual * 0.98
    consumo_t_2 = consumo_actual * 0.95
    consumo_t_3 = consumo_actual * 0.90
    
    
    X_nuevo = pd.DataFrame([[hora_actual, minuto_actual, consumo_t_1, consumo_t_2, consumo_t_3]], 
                           columns=['hora', 'minuto', 'consumo_t_1', 'consumo_t_2', 'consumo_t_3'])
    
    # Hacemos la predicción
    prediccion_watts = modelo.predict(X_nuevo)[0]
    
    print(f"[{hora_actual}:{minuto_actual}] Medido: {consumo_actual:.1f}W | Proyectado (5 min): {prediccion_watts:.1f}W")
    
    
    if prediccion_watts > UMBRAL_MAX:
        print(">>> ¡ALERTA PREDICTIVA! Límite superado. Enviando comando OFF a la carga <<<")
        client.publish(TOPICO_CONTROL, 'OFF')


cliente = mqtt.Client()
cliente.on_message = on_message
cliente.connect(BROKER, 1883, 60)
cliente.subscribe(TOPICO_ESCUCHA)

print("Servicio de IA activo y escuchando...")
cliente.loop_forever()