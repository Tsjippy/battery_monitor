from requests import post
import json
from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo
from paho.mqtt.client import Client, MQTTMessage

host        = '192.168.0.216'
base_url    = 'http://' + host + ':8123/api'
token       = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhYTEzZDI5ZjNjNTA0MmE5YjgwMzZkZWNhZjg1OGFjMiIsImlhdCI6MTcyOTY4MjY3NywiZXhwIjoyMDQ1MDQyNjc3fQ.BxHG5_Zwwg-sJpYouFzIBNSO5vo9cfb_8xB9Hw4vRxY'

headers = {
    'Authorization': 'Bearer ' + token,
    'content-type': 'application/json'
}

def my_callback(client: Client, user_data, message: MQTTMessage):
    print(message.payload.decode())

# Configure the required parameters for the MQTT broker
mqtt_settings = Settings.MQTT(host=host, username='ewaldharmsen', password='3e9mKWoP10ZRw05jfugK')

# Define the device. At least one of `identifiers` or `connections` must be supplied
device_info = DeviceInfo(name="Batteries", identifiers="unique_battery_id")

# Associate the sensor with the device via the `device` parameter
# `unique_id` must also be set, otherwise Home Assistant will not display the device in the UI
voltage_sensor_info = BinarySensorInfo(name="Voltage", device_class="voltage", unique_id="battery_voltage_1", device=device_info)

voltage_settings = Settings(mqtt=mqtt_settings, entity=voltage_sensor_info)

# Instantiate the sensor
voltage_sensor = BinarySensor(voltage_settings, my_callback)

print(voltage_sensor)

# Change the state of the sensor, publishing an MQTT message that gets picked up by HA
print(voltage_sensor.update_state('49.3'))
