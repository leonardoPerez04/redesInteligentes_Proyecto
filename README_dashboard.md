# Dashboard — Mini Smart Grid
**Redes Inteligentes 2026**

## Archivos necesarios
```
dashboard.py                      ← script principal
requirements.txt                  ← dependencias
modelo_regresion_smartgrid.pkl    ← ya está en el repo (no subir de nuevo)
```

## Instalación
```bash
pip install -r requirements.txt
```

## Configuración (antes de correr)

Abre `dashboard.py` y edita las primeras líneas:

```python
MQTT_BROKER   = "broker.hivemq.com"   # ← broker público, no requiere instalación
MQTT_PORT     = 1883
TOPICO_NODO1  = "/smartgrid/nodo1/consumo"   # sincronizado con smartGrid.py
TOPICO_NODO2  = "/smartgrid/nodo2/consumo"   # sincronizado con smartGrid.py
TOPICO_CTRL   = "/smartgrid/control"          # ia_predictiva.py publica ON/OFF aquí
TOPICO_PRED   = "/smartgrid/prediccion"       # opcional
UMBRAL_ALERTA = 320    # watts — línea amarilla (80% de 400W)
UMBRAL_MAX    = 400    # watts — línea roja, igual que smartGrid.py
```

## Cómo correr
```bash
py dashboard.py
```
Abre en tu navegador: **http://localhost:8050**

---

## Qué muestra el dashboard

| Panel | Descripción |
|-------|-------------|
| KPI Nodo 1 | Último valor de watts del nodo 1 en tiempo real |
| KPI Nodo 2 | Último valor de watts del nodo 2 en tiempo real |
| KPI Predicción IA | Predicción calculada localmente con el modelo `.pkl` |
| Control de Carga | ON verde / OFF rojo según `/smartgrid/control` |
| Gráfica principal | Serie temporal: Nodo 1, Nodo 2 y predicción de IA superpuestos con líneas de umbral |
| Comparativo nodos | Barras de los últimos 20 puntos lado a lado |
| Estado del sistema | Alertas automáticas por nodo + estado del broker y modelo |

---

## Cómo funciona la predicción

El dashboard carga `modelo_regresion_smartgrid.pkl` y calcula la predicción localmente con los mismos datos que llegan por MQTT (hora, minuto, watts). No requiere que `ia_predictiva.py` publique un tópico extra.

---

## Conexión con los demás integrantes

- **simulador:** cambia `BROKER_HOST = "broker.hivemq.com"` en `smartGrid.py` y corre el script
- **IA:** cambia `BROKER_HOST = "broker.hivemq.com"` en `ia_predictiva.py`
- **broker:** no se necesita Mosquitto local, se usa HiveMQ público
- **Conjunto** deben apuntar a `broker.hivemq.com` para que el sistema funcione junto

---

## Presentacion 

1. Todos los integrantes apuntan a `broker.hivemq.com`
2. Corre `py dashboard.py`
3. El dashboard se actualiza **cada 2 segundos** automáticamente
4. El profesor puede ver el dashboard desde su celular entrando a `http://192.168.1.85:8050` en la misma red WiFi