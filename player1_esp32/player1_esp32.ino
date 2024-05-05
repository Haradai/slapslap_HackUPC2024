#include <Wire.h>
#include "Adafruit_MPR121.h"
#include <WiFi.h>
#include <PubSubClient.h>

#ifndef _BV
#define _BV(bit) (1 << (bit)) 
#endif

#define WIFI_SSID "slap_project"
#define WIFI_PASSWORD "slapslap"

//MQTT Broker
#define MQTT_HOST IPAddress(192, 168, 1, 113)

#define MQTT_PORT 1883
#define MQTT_Piezo "/Player1"
#define MQTT_SUB_Output1 "/Turn"
#define MQTT_SUB_Output2 "/Game_state"

#define RED 5
#define GREEN 16
#define YELLOW 18
#define GND1 17

WiFiClient espClient;
PubSubClient client(espClient);

char lastMessage_tourn[256];
char lastMessage_game[256];
int turn = 1;

Adafruit_MPR121 cap = Adafruit_MPR121();

// Keeps track of the last pins touched
// so we know when buttons are 'released'
uint16_t lasttouched = 0;
uint16_t currtouched = 0;

uint8_t b_pads[]= {0,0,0,0,0,0};
uint8_t v_pads[]= {0,0,0,0,0,0};

void callback(char *topic, byte *payload, unsigned int length) {
    Serial.print("Received message on topic: ");
    Serial.println(topic);
    if (strcmp(topic, "/Turn") == 0) {
      if (length < sizeof(lastMessage_tourn)) { // Avoid buffer overflow
          memcpy(lastMessage_tourn, payload, length); // Copy payload to lastMessage
          lastMessage_tourn[length] = '\0'; // Add null-terminator
      } else {
          Serial.println("Message too long, truncated");
          memcpy(lastMessage_tourn, payload, sizeof(lastMessage_tourn) - 1);
          lastMessage_tourn[sizeof(lastMessage_tourn) - 1] = '\0';
      }
    }
    if (strcmp(topic, "/Game_state") == 0) {
      if (length < sizeof(lastMessage_game)) { // Avoid buffer overflow
          memcpy(lastMessage_game, payload, length); // Copy payload to lastMessage
          lastMessage_game[length] = '\0'; // Add null-terminator
      } else {
          Serial.println("Message too long, truncated");
          memcpy(lastMessage_game, payload, sizeof(lastMessage_game) - 1);
          lastMessage_game[sizeof(lastMessage_game) - 1] = '\0';
      }
      Serial.print("Saved message content: ");
      Serial.println(lastMessage_game); // Display the saved message
    }
    if (strcmp(topic, "/Turn") == 0 && strcmp(lastMessage_tourn, "Player2") == 0) {
        turn = 2;
        analogWrite(RED, 0);
        analogWrite(GREEN, 0);
        analogWrite(YELLOW, 255);
    } else if (strcmp(topic, "/Turn") == 0 && strcmp(lastMessage_tourn, "Player1") == 0) {
        turn = 1;
        analogWrite(RED, 0);
        analogWrite(GREEN, 255);
        analogWrite(YELLOW, 0);
    }
    if (strcmp(topic, "/Game_state") == 0 && strcmp(lastMessage_game, "Hit success") == 0 && turn == 2 ){
      for(int i=0; i<10;i++){
        analogWrite(RED, 255);
        analogWrite(GREEN, 0);
        analogWrite(YELLOW, 0);
        delay(100);
        analogWrite(RED, 0);
        delay(100);
      }
      Serial.print("fora");
      memcpy(lastMessage_game, "Waiting users", 14); // Copy payload to lastMessagelastMessage_game="";
      Serial.print(lastMessage_game);
      analogWrite(YELLOW, 255);
    }
}

void setup() {
  
  pinMode(GND1, OUTPUT);
  pinMode(YELLOW, OUTPUT);
  pinMode(RED, OUTPUT);
  pinMode(GREEN, OUTPUT);
  delay(100);
  analogWrite(GND1, 0);
  analogWrite(RED, 255);
  analogWrite(GREEN, 255);
  analogWrite(YELLOW, 255);

  Serial.begin(9600);

  while (!Serial) {
    delay(10);
  }
  Serial.println("Connecting to WiFi..");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Conected to WiFi network");
  client.setServer(MQTT_HOST, MQTT_PORT);

  while (!client.connected()) {
      String client_id = "esp32-client-";
      client_id += String(WiFi.macAddress());
      Serial.printf("The client %s connects to the public MQTT broker\n", client_id.c_str());
      if (client.connect(client_id.c_str())) {
          Serial.println("Public EMQX MQTT broker connected");
      } else {
          Serial.print("failed with state ");
          Serial.print(client.state());
          Serial.print(" ");
          delay(2000);
      }
  }
  client.setCallback(callback);
  boolean r= client.subscribe(MQTT_SUB_Output1);
  if(r){
    Serial.println("Subscribed to /Turn");
  }else{
    Serial.println("Not subscribed to /Turn");
  }

  r= client.subscribe(MQTT_SUB_Output2);
  if(r){
    Serial.println("Subscribed to /Game_state");
  }else{
    Serial.println("Not subscribed to /Game_state");
  }

  Serial.println("Adafruit MPR121 Capacitive Touch sensor test"); 
  
  // Default address is 0x5A, if tied to 3.3V its 0x5B
  // If tied to SDA its 0x5C and if SCL then 0x5D
  if (!cap.begin(0x5A)) {
    Serial.println("MPR121 not found, check wiring?");
    while (1);
  }
  Serial.println("MPR121 found!");
  analogWrite(RED, 0);
  analogWrite(GREEN, 255);
  analogWrite(YELLOW, 0);
}

void loop() {
  client.loop();
  // Get the currently touched pads
  currtouched = cap.touched();
  
  for (uint8_t i=0; i<11; i+=2) {
    // it if *is* touched and *wasnt* touched before, alert!
    v_pads[i/2] = cap.filteredData(i);
    if ((currtouched & _BV(i)) && !(lasttouched & _BV(i)) ) {
      //Serial.print(i/2); Serial.println(" touched");
      b_pads[i/2] = 1;

    }
    // if it *was* touched and now *isnt*, alert!
    if (!(currtouched & _BV(i)) && (lasttouched & _BV(i)) ) {
      //Serial.print(i/2); Serial.println(" released");
      b_pads[i/2] = 0;
    }
  }
  
  char buffer[256];

  sprintf(buffer, "{'Binary' : { 'Pad1' : '%d', 'Pad2' : '%d', 'Pad3' : '%d', 'Pad4' : '%d', 'Pad5' : '%d', 'Pad6' : '%d'}, 'Value'  : { 'Pad1' : '%d', 'Pad2' : '%d', 'Pad3' : '%d', 'Pad4' : '%d', 'Pad5' : '%d', 'Pad6' : '%d'}}", b_pads[0], b_pads[1], b_pads[2], b_pads[3], b_pads[4], b_pads[5], v_pads[0], v_pads[1], v_pads[2], v_pads[3], v_pads[4], v_pads[5]);
  // Serial.println(buffer);
  client.publish(MQTT_Piezo, buffer);

  // reset our state
  lasttouched = currtouched;

  delay(100);
}
