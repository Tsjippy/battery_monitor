#!/usr/bin/env python3
from struct import *
import paho.mqtt.client as mqtt
import json
from mqtt_secrets import *
import logger

#from paho.mqtt.enums import MQTTProtocolVersion
#from paho.mqtt.enums import CallbackAPIVersion
import time
import importlib.metadata

class MqqtToHa:
    def __init__(self, device, sensors):
        self.device         = device
        self.sensors        = sensors

        self.logger         = logger.Logger('info')

        #Store send commands till they are received
        self.sent           = {}
        self.queue          = {}

        # https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html
        # note that with version1, mqttv3 is used and no other migration is made
        # if paho-mqtt v1.6.x gets removed, a full code migration must be made
        if importlib.metadata.version("paho-mqtt")[0] == '1':
            # for paho 1.x clients
            self.client = mqtt.Client(client_id=mqtt_client_id)
        else:
            # for paho 2.x clients
            # note that a deprecation warning gets logged 
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=mqtt_client_id)

        self.connected      = False

        self.device_name    = self.device['name'].lower().replace(" ", "_")

        self.main()

    def __str__(self):
        return f"{self.device.name}"

    def create_sensors(self):
        self.logger.log_message('Creating Sensors')
        
        device_id       = self.device['identifiers'][0]
        

        for index,sensor in self.sensors.items():
            if 'sensortype' in sensor:
                sensortype = sensor['sensortype']
            else:
                sensortype  = 'sensor'

            sensor_name                         = sensor['name'].replace(' ', '_').lower()
            self.sensors[index]['base_topic']   = f"homeassistant/{sensortype}/{device_id}/{sensor_name}"
            unique_id                           = f"{self.device_name}_{sensor_name}"

            self.logger.log_message(f"Creating sensor '{sensor_name}' with unique id {unique_id}")

            config_payload  = {
                "name": sensor['name'],
                "state_topic": sensor['base_topic'] + "/state",
                "unique_id": unique_id,
                "device": self.device,
                "platform": "mqtt"
            }

            if 'state' in sensor:
                config_payload["state_class"]           = sensor['state']
            
            if 'unit' in sensor:
                config_payload["unit_of_measurement"]   = sensor['unit']

            if 'type' in sensor:
                config_payload["device_class"]          = sensor['type']

            if 'icon' in sensor:
                config_payload["icon"]                  = sensor['icon']

            payload                                     = json.dumps(config_payload)

            # Send
            result  = self.client.publish(topic=self.sensors[index]['base_topic'] + "/config", payload=payload, qos=1, retain=False)

            # Store
            self.sent[result.mid]    = payload

            if('init' in sensor):
                self.send_value(sensor['name'], sensor['init'])

    def on_connect(self, client, userdata, flags, reason_code):
        if reason_code == 0:
            self.logger.log_message(f"Succesfuly connected")
        else:
            self.logger.log_message(f"Connected with result code {reason_code}", 'error')

        self.connected  = True

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("$SYS/#")

        client.subscribe("homeassistant/status")

        self.create_sensors()

        self.logger.log_message('Sensors created')

    def on_disconnect(self, client, userdata, rc):
        while True:
            # loop until client.reconnect()
            # returns 0, which means the
            # client is connected
            try:
                if not client.reconnect():
                    break
            except ConnectionRefusedError:
                # if the server is not running,
                # then the host rejects the connection
                # and a ConnectionRefusedError is thrown
                # getting this error > continue trying to
                # connect
                pass
            # if the reconnect was not successful,
            # wait one second
            time.sleep(1)

    def on_message(self, client, userdata, message):
        if( '$SYS/' not in message.topic):
            self.logger.log_message(str(message.topic) + " " + str(message.payload.decode()) + str(userdata))

    def on_log(self, client, userdata, paho_log_level, message):
        if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
            self.logger.log_message(message)

    # Called when the server received our publish succesfully
    def on_publish(self, client, userdata, mid, reason_code='', properties=''):
        #self.logger.log_message(send[mid] )

        #Remove from send dict
        del self.sent[mid]

    # Sends a sensor value
    def send_value(self, name, value, send_json=True):
        topic                   = "homeassistant/sensor/" + self.device['identifiers'][0] + '/' + name.replace(' ', '_').lower() + "/state"

        if send_json:
            payload                 = json.dumps(value)
        else:
            payload                 = value

        # add current messgae to the queue
        self.queue[topic]   = payload

        if not self.connected:
            self.logger.log_message('Not connected, adding to queue', 'warning')
        else:
            # post queued messages
            for topic, payload in self.queue.items():
                result                  = self.client.publish(topic=topic, payload=payload, qos=1, retain=False)
                self.sent[result.mid]   = payload

    def main(self):
        self.logger.log_message('Starting application')

        #client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(mqtt_username, mqtt_password)
        self.client.on_connect   = self.on_connect
        self.client.on_message   = self.on_message
        self.client.on_log       = self.on_log
        self.client.on_publish   = self.on_publish
        self.client.will_set(f'system-sensors/sensor/{self.device_name}/availability', 'offline', retain=True)

        self.logger.log_message('Connecting to Home Assistant')

        while True:
            try:
                self.client.connect(mqtt_host, mqtt_port)
                break
            except ConnectionRefusedError:
                # sleep for 2 minutes if broker is unavailable and retry.
                # Make this value configurable?
                # this feels like a dirty hack. Is there some other way to do this?
                time.sleep(120)
            except OSError:
                # sleep for 10 minutes if broker is not reachable, i.e. network is down
                # Make this value configurable?
                # this feels like a dirty hack. Is there some other way to do this?
                time.sleep(600)
        
        self.client.loop_start()
