from influxdb_client_3 import InfluxDBClient3, Point
import paho.mqtt.client as mqtt

class mqtt2influx2b():
    def __init__(self,mqtt_ip:str, mqtt_port:str, ifdb_tok:str, ifdb_ipport:str, ifdb_org:str, ifdb_db:str):
        '''
        params:
            - mqtt broker ip
            - mqtt broker port
            - influxdb token
            - influxdb ip:port
            - influxdb org
            - influxdb database
        '''
        #connect to influxdb 
        self.ifdb_client = InfluxDBClient3(token=ifdb_tok,
                            host=ifdb_ipport,
                            org=ifdb_org,
                            database=ifdb_db)

        #create mqtt client object and assign on connect and on message functions
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.on_connect = self.mqtt_on_connect
        self.mqttc.on_message = self.on_message

        self.mqtt_ip = mqtt_ip
        self.mqtt_port = mqtt_port

        
    #Connect function
    def mqtt_on_connect(self, mqtt_client, userdata, flags, reason_code, properties):
        ''' 
        Here we subscribe to the sensors (topics) we want
        '''
        
        #subscribing
        mqtt_client.subscribe('/Player1/Piezo1'),
        mqtt_client.subscribe('/Player1/Piezo2'),
        mqtt_client.subscribe('/Player1/Piezo3'),
        mqtt_client.subscribe('/Player1/Piezo4'),
        mqtt_client.subscribe('/Player2/Piezo1'),
        mqtt_client.subscribe('/Player2/Piezo2'),
        mqtt_client.subscribe('/Player2/Piezo3'),
        mqtt_client.subscribe('/Player2/Piezo4')

        print(f"Connected with result code {reason_code}")

    #function called every time we receive a message
    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))
        player = msg.topic[1:7]
        piezo = msg.topic[8:]
        
        #create influxdb point and send
        point = Point("PiezoSignal").tag(player).field(piezo,float(msg.payload))
        self.ifdb_client.write(point)
    
    def start(self):
        ''' 
        Starts listening to incoming mqtt messages.
        Runs on_message every time.
        '''
        #quizas poner esto en una funcion
        self.mqttc.connect(self.mqtt_ip, self.mqtt_port, 60) #connect mqtt to client (el 60 que es?)
        self.mqttc.loop_forever()

######
######
######
##MAIN
######
######
######

params = {
    "mqtt_ip":'192.168.164.88',
    "mqtt_port":1883, 
    "ifdb_tok":"ygYcYy950HBz1C1oj2oD6LUBfOyl-WiwkC47xiUPDfmJby3dv1DPlldTACZ1SXrJXjSoH97TZxNUcGKY5-XFdw==", 
    "ifdb_ipport":"http://localhost:8086", 
    "ifdb_org":"slapslap_organization", 
    "ifdb_db":"slapslap_bucket"
}

mqtt_to_influxdb_object = mqtt2influx2b(*params.values())
mqtt_to_influxdb_object.start()