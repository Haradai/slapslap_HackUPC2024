from influxdb_client_3 import InfluxDBClient3, Point
import paho.mqtt.client as mqtt
import numpy as np
import ast
from datetime import datetime
from datetime import timedelta
import time

class slap_game_service():
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

        #CONFIG VARIABLES
        self.N_SENSORS_PER_GLOVE = 6
        self.BUFFER_N_SAMPLES = 2
        self.ATTEMPT_TIMEOUT_SEC = 2

        #SENSING VARIABLES
        self.cap_values = {
            "Player1": np.zeros(shape=(self.N_SENSORS_PER_GLOVE, self.BUFFER_N_SAMPLES)),
            "Player2": np.zeros(shape=(self.N_SENSORS_PER_GLOVE, self.BUFFER_N_SAMPLES))
        } 
    
        #hit values buffer
        self.hits_buffer = {
            "Player1": np.zeros(shape=(self.N_SENSORS_PER_GLOVE, self.BUFFER_N_SAMPLES)),
            "Player2": np.zeros(shape=(self.N_SENSORS_PER_GLOVE, self.BUFFER_N_SAMPLES))
        }

        #GAME VARIABLES
        self._turns = ["Init", "Player1", "Player2"]
        self.old_turn = ""
        self.turn = "Init" #Always player A starts
        self.log_turn()

        self._game_states = ["Waiting users", "Ready","Attemting hit","Hit success", "Hit failure","Anomaly"]
        self.old_game_state = ""
        self.game_state = "Waiting users" #Always start with rest
        self.log_game_state()
        

        self.attempt_hit_start = datetime.now()

    #Connect function
    def mqtt_on_connect(self, mqtt_client, userdata, flags, reason_code, properties):
        ''' 
        Here we subscribe to the sensors (topics) we want
        '''
        
        #subscribing
        mqtt_client.subscribe('/Player1'),
        mqtt_client.subscribe('/Player2'),
        print(f"Connected with result code {reason_code}")

    #function called every time we receive a message
    def on_message(self, client, userdata, msg):
        ''' 
        this is the live loop that is alive thanks to the 
        constant incoming values from mqtt sent by the esp32's
        '''
        #player sending message
        player = msg.topic[1:]

        #conert to dict the message
        sensor_load = ast.literal_eval(str(msg.payload)[2:-1])

        sensor_values = sensor_load["Value"]
        sensor_hits = sensor_load["Binary"]

        #convert values to ints , they com in as strings
        for key in sensor_values:
            sensor_values[key] = int(sensor_values[key])
        
        for key in sensor_hits:
            sensor_hits[key] = int(sensor_hits[key])
        
        #save values to influxdb
        self.log_cap_vals(sensor_values, player)
        
        #if any hit log into influxdb
        if np.any(sensor_hits):
            self.log_cap_vals(sensor_hits, player, is_binary=True)

        self.update_hits_buffer(sensor_hits, player)
        
        #get hits sensing on both players
        hits_player1 = np.any(self.hits_buffer["Player1"],axis=1)
        hits_player2 = np.any(self.hits_buffer["Player2"],axis=1)     
        
        #Init each turn case:
        if self.game_state == "Waiting users":
            #check for both that last sensor (inside hand) is hit
            if hits_player1[0] and hits_player2[0] :
                print("Starting turn!")
                #if first time playing
                if self.turn == "Init":
                    self.turn = "Player1"
                    self.log_turn()

                self.game_state = "Ready"
                self.log_game_state()

                #send to esp32 for comoddity purposes
                self.mqttc.publish("/Turn",self.turn)  

        #actual game run (execissevely explicit for debugging purposes)
        else:
            if self.turn == "Player1":
                if hits_player1[0]: #all sensors except last(inner hand sensor)
                    pass
                    #still ready
                else:
                    #started going for a hit! or already going for a hit. If rest change to going for a hit
                    if self.game_state == "Ready":
                        self.game_state = "Attempting hit"
                        self.log_game_state()
                        self.attempt_hit_start = datetime.now()

                    #if already attempting a hit check for contrary player hit or separate or attempt timeout
                    elif self.game_state == "Attempting hit":
                        #check adversary hit (all sensors minus last one)
                        if np.any(hits_player2[1:]):
                            self.game_state  = "Hit success"
                            self.log_game_state()

                        else:
                            #if time elapsed is greater than timeout change to failure
                            elapsed = datetime.now() - self.attempt_hit_start
                            if elapsed > timedelta(seconds = self.ATTEMPT_TIMEOUT_SEC):
                                self.game_state = "Hit failure"
                                self.log_game_state()
                
            if self.turn == "Player2":
                if hits_player2[0]: #all sensors except last(inner hand sensor)
                    pass
                    #still resting
                else:
                    #started going for a hit! or already going for a hit. If rest change to going for a hit
                    if self.game_state == "Ready":
                        self.game_state = "Attempting hit"
                        self.log_game_state()
                        self.attempt_hit_start = datetime.now()

                    #if already attempting a hit check for contrary player hit or separate or attempt timeout
                    elif self.game_state == "Attempting hit":
                        #check adversary hit (all sensors minus last one)
                        if np.any(hits_player1[1:]):
                            self.game_state  = "Hit success"
                            self.log_game_state()
                            print("Hit success!!!!")

                        else:
                            #if time elapsed is greater than timeout change to failure
                            elapsed = datetime.now() - self.attempt_hit_start
                            if elapsed > timedelta(seconds = self.ATTEMPT_TIMEOUT_SEC):
                                self.game_state = "Hit failure"
                                self.log_game_state()
                                print("Hit failure")

            #get other player id
            other_player = "Player1" if self.turn == "Player2" else "Player2"
            print(f"The other player is: {other_player}")

            #handle if hit success or failure
            if self.game_state == "Hit success":
                self.log_point(self.turn) #log 1 point to turn player
                self.game_state = "Waiting users"
                self.log_game_state()


            if self.game_state == "Hit failure":
                self.log_esquivos(other_player)
                self.turn = other_player
                self.log_turn()
                self.game_state = "Waiting users"
                self.log_game_state()

        #debug
        print(f"Game state: {self.game_state}")
        print(f"Turn: {self.turn}")
        Player1_holding = np.any(self.hits_buffer["Player1"][0,:])
        Player2_holding = np.any(self.hits_buffer["Player2"][0,:])
        print(f"Inner_pads: Player1:{Player1_holding}  Player2:{Player2_holding}")

    def log_turn(self):
        ''' 
        Logs turn to influxdb

        TODO: log value to mqtt so that gloves can read it and change led color
        '''
        point = Point("Turn").field("Turn",self.turn)
        self.ifdb_client.write(point)
        self.mqttc.publish("/Turn",self.turn)  
    
    def log_game_state(self):
        ''' 
        Logs game_state to influxdb
        '''
        point = Point("Game state").field("Game state",self.game_state)
        self.ifdb_client.write(point)
        self.mqttc.publish("/Game_state",self.game_state)  
    
    def log_point(self,player):
        ''' 
        Logs game_state to influxdb
        '''
        point = Point("Point").tag("player",player).field("Value",1)
        self.ifdb_client.write(point)
    
    def log_esquivos(self,player):
        ''' 
        Logs game_state to influxdb
        '''
        point = Point("Esquivo").tag("player",player).field("Value",1)
        self.ifdb_client.write(point)

    def log_cap_vals(self, sensor_values:dict, player:str, is_binary:bool=False):
        
        ##Save point to influxdb
        #create point for this timestamp and player
        if is_binary:
            point = Point("CapacitiveHits").tag("player",player)
        else:
            point = Point("CapacitiveSignal").tag("player",player)

        #iterate over all sensors and add value to point as different fields.
        for sensor_id, value in zip(sensor_values.keys(),sensor_values.values()):
            point.field(sensor_id,value)
    
        #write point to influxdb
        self.ifdb_client.write(point)

    def update_hits_buffer(self, sensor_values:dict, player:str):
        ##Update new values to piezo values
        #Are saved as ordered in the json in the numpy array
        sample = np.expand_dims(np.array(list(sensor_values.values())),axis=1)
        self.hits_buffer[player] = np.concatenate( [self.hits_buffer[player][:,1:], sample] ,axis=1)

    def start(self):
        ''' 
        Starts listening to incoming mqtt messages.
        Runs on_message every time.
        '''
        #quizas poner esto en una funcion
        self.mqttc.connect(self.mqtt_ip, self.mqtt_port, 60) #connect mqtt to client (el 60 que es?)
        self.mqttc.loop_forever()
    
    #def check_states_legality(sensors_array_playerA):
        
        #check if any


######
######
######
##MAIN
######
######
######

params = {
    "mqtt_ip":'192.168.1.113',
    "mqtt_port":1883, 
    "ifdb_tok":"XR0mXDy_ejp9yFOHy85jJBPtOILcYtd4wcf_FtLww3EOudxI6FxWPlQMuGLk-W794AphD1NO355_Lwsi9TwwHQ==", 
    "ifdb_ipport":"http://localhost:8086", 
    "ifdb_org":"slap", 
    "ifdb_db":"bucket"
}

mqtt_to_influxdb_object = slap_game_service(*params.values())
mqtt_to_influxdb_object.start()