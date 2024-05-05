import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import time

MQTT_BROKER_HOST = "mqtt"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "datos"

INFLUXDB_HOST = "influxdb"
INFLUXDB_PORT = 8086
INFLUXDB_USER = "myuser"
INFLUXDB_PASSWORD = "mypassword"
INFLUXDB_DATABASE = "mydb"

def on_message(client, userdata, msg):
    # Procesar el mensaje MQTT
    data = msg.payload.decode("utf-8")
    # Almacenar los datos en InfluxDB
    client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, username=INFLUXDB_USER, password=INFLUXDB_PASSWORD, database=INFLUXDB_DATABASE)
    json_body = [
        {
            "measurement": "datos",
            "fields": {
                "valor": float(data)
            }
        }
    ]
    client.write_points(json_body)

client = mqtt.Client()
client.on_message = on_message

# Esperar hasta que el broker MQTT esté disponible
while True:
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        break
    except ConnectionRefusedError:
        print("Broker MQTT no disponible, esperando...")
        time.sleep(1)  # Esperar 1 segundo antes de intentar nuevamente

client.subscribe(MQTT_TOPIC)
client.loop_forever()

