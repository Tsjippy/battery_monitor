#!/usr/bin/env python3
from struct import *
from datetime import datetime
import time
import subprocess
import paho.mqtt.client as mqtt
import json

mqtt_username = "ewaldharmsen"
mqtt_password =  "3e9mKWoP10ZRw05jfugK"
mqtt_host = "192.168.0.216"
mqtt_port = 1883

#******************************************
# Callback function when the client successfully connects to the MQTT broker
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Publish config??
    config_payload = {
        "name": "Power Use General",
        "state_topic": "homeassistant/sensor/house/power_use1/state",
        "state_class": "measurement",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "value_template": "{{ value }}",
        "unique_id": "power_use",
        "device": {
            "identifiers": [
                "thesensor"
            ],
            "name": "Power Use Sensors",
            "model": "None",
            "manufacturer": "None"
        },
        "icon": "mdi:home-lightning-bolt-outline",
        "platform": "mqtt"
    }
    result  = client.publish(topic="homeassistant/sensor/house/power_use1/config", payload=json.dumps(config_payload), qos=0, retain=False)
    print(result)
    print('Created device')
    
    
    item1 = 1000
    item2 = 2000

    # Publish State1
    topic1 = "homeassistant/sensor/house/power_use1/state"
    client.publish(topic=topic1, payload=json.dumps(item1), qos=0, retain=False)

    # Publish State2
    topic2 = "homeassistant/sensor/house/power_use2/state"
    client.publish(topic=topic2, payload=json.dumps(item2), qos=0, retain=False)
    print("Published    '{0}' to '{1}'          Published '{2}' to '{3}'".format(str(item1), topic1, str(item2), topic2))

    time.sleep(6)
#******************************************

#-------------------------------------------------------------------------------------------------------
# main function
def main():
    client = mqtt.Client()
    client.username_pw_set(mqtt_username, mqtt_password)
    client.on_connect = on_connect
    client.connect(mqtt_host, mqtt_port)
    client.loop_forever()

#---------------------------------------------------------------------------------------------------------------------------------
if __name__=="__main__":
    main()
#---------------------------------------------------------------------------------------------------------------------------------
