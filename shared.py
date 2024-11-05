#!/usr/bin/env python3
from struct import *
import paho.mqtt.client as mqtt
import json
#from paho.mqtt.enums import MQTTProtocolVersion
#from paho.mqtt.enums import CallbackAPIVersion

mqtt_username   = "ewaldharmsen"
mqtt_password   = "3e9mKWoP10ZRw05jfugK"
mqtt_host       = "192.168.0.200"
mqtt_port       = 1883

class MqqtToHa:
    def __init__(self, device, sensors):
        self.device         = device
        self.sensors        = sensors

        #Store send commands till they are received
        self.sent           = {}
        self.queue          = {}
        self.client         = mqtt.Client()
        self.connected      = False

        self.main()

    def __str__(self):
        return f"{self.device.name}"

    def create_sensors(self):
        print('Creating Sensors')

        for sensor in self.sensors.values():
            print(sensor)

            base_topic      = "homeassistant/sensor/" + self.device['identifiers'][0] + '/' + sensor['name'].replace(' ', '_').lower()
            unique_id       = (self.device['name'] + '_' + sensor['name']).lower().replace(" ", "_")

            print("Creating sensor '" + sensor['name'] + "' with unique id " + unique_id)

            config_payload  = {
                "name": sensor['name'],
                "state_topic": base_topic + "/state",
                "state_class": sensor['state'],
                "unit_of_measurement": sensor['unit'],
                "device_class": sensor['type'],
                "unique_id": unique_id,
                "device": self.device,
                #"icon": sensor['icon'],
                "platform": "mqtt"
            }

            payload = json.dumps(config_payload)

            # Send
            result  = self.client.publish(topic=base_topic + "/config", payload=payload, qos=1, retain=False)

            # Store
            self.sent[result.mid]    = payload

            if('init' in sensor):
                self.send_value(sensor['name'], sensor['init'])

    def on_connect(self, client, userdata, flags, reason_code):
        print(f"Connected with result code {reason_code}")

        self.connected  = True

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("$SYS/#")

        client.subscribe("homeassistant/status")

        self.create_sensors()

        print('Sensors created')

    def on_message(self, client, userdata, message):
        if( '$SYS/' not in message.topic):
            print(message.topic+" "+str(message.payload.decode()) + userdata)

    def on_log(self, client, userdata, paho_log_level, message):
        if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
            print(message)

    # Called when the server received our publish succesfully
    def on_publish(self, client, userdata, mid, reason_code='', properties=''):
        #print(send[mid] )

        #Remove from send dict
        del self.sent[mid]

    # Sends a sensor value
    def send_value(self, name, value):
        topic                   = "homeassistant/sensor/" + self.device['identifiers'][0] + '/' + name.replace(' ', '_').lower() + "/state"
        payload                 = json.dumps(value)

        # add current messgae to the queue
        self.queue[topic]   = payload

        if not self.connected:
            print('Not connected, adding to queue')
        else:
            # post queued messages
            for topic, payload in self.queue.items():
                result                  = self.client.publish(topic=topic, payload=payload, qos=1, retain=False)
                self.sent[result.mid]   = payload

    def main(self):
        print('Starting application')
        #client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(mqtt_username, mqtt_password)
        self.client.on_connect   = self.on_connect
        self.client.on_message   = self.on_message
        self.client.on_log       = self.on_log
        self.client.on_publish   = self.on_publish

        
        print('Connecting to Home Assistant')
        self.client.connect(mqtt_host, mqtt_port)

        self.client.loop_start()
