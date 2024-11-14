#https://github.com/chriskomus/ble-sniffer-walkthrough

import gatt
import time
from datetime import datetime, timezone
import sys

import sensors
import logger

updateInterval      = 10 #in seconds
debug               = False
NOTIFY_CHAR_UUID    = '0000ffe1-0000-1000-8000-00805f9b34fb'
MAC_ADDRESS         = '38:3b:26:79:6f:c5'
battery_capacity_ah = 400 # Ah      

class AnyDeviceManager(gatt.DeviceManager):
    def device_discovered(self, device):
        self.logger.log_message("Discovered [%s] %s" % (device.mac_address, device.alias()))

class AnyDevice(gatt.Device):
    def __init__(self, mac_address, manager):
        super().__init__(mac_address, manager)

        self.charging           = False
        self.last_dom_update    = int(time.time())  
        self.updating           = False 
        self.avg_values         = {}
        self.logger             = logger.Logger('info')
    
    def connect_succeeded(self):
        super().connect_succeeded()
        self.logger.log_message("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        self.logger.log_message("[%s] Connection failed: %s" % (self.mac_address, str(error)), 'error')
        # Try to connect again
        #connect()

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        self.logger.log_message("[%s] Disconnected" % (self.mac_address), 'warning')
        self.logger.log_message("[%s] Reconnecting in 10 seconds" % (self.mac_address), 'warning')
        time.sleep(10)
        self.connect()

    def services_resolved(self):
        super().services_resolved()

        self.logger.log_message("[%s] Resolved services" % (self.mac_address))
        for service in self.services:
            self.logger.log_message("[%s]  Service [%s]" % (self.mac_address, service.uuid))
            for characteristic in service.characteristics:
                if not NOTIFY_CHAR_UUID:
                    self.logger.log_message("[%s]    Characteristic [%s]" % (self.mac_address, characteristic.uuid))
                elif characteristic.uuid == NOTIFY_CHAR_UUID:
                    self.logger.log_message("[%s]    Enabling Notifications for Characteristic [%s]" % (self.mac_address, characteristic.uuid))
                    characteristic.enable_notifications()

    def characteristic_enable_notifications_succeeded(self, characteristic):
        self.logger.log_message('characteristic_enable_notifications_succeeded')

    def characteristic_enable_notifications_failed(self, characteristic, error):
        self.logger.log_message('characteristic_enable_notifications_failed', 'error')

    def characteristic_value_updated(self, characteristic, value):
        super().characteristic_value_updated(characteristic, value)
        self.on_data_received(value)

    def on_data_received(self, value):
        if debug:
            self.logger.log_message(f"Got packet of len(value)={len(value)}: {value.hex()}")
        self.process_data(value.hex())
        
    def add_to_average(self, key, value):
        # add to the values to be averaged
        if key not in self.avg_values:
            self.avg_values[key] = [value]
        else:
            self.avg_values[key].append(value)
            
    def average(self, lst, decimals=1): 
        if debug:
            self.logger.log_message(lst)
            
        if len(lst)  == 0:
            return -99
            
        return round((sum(lst) / len(lst)) , decimals)
        
    def send_to_ha(self):
        try:
            if debug:
                self.logger.log_message("Time to ha update: "+ str(updateInterval - (int( time.time()) - self.last_dom_update)))
                
            if((int( time.time()) - self.last_dom_update) > updateInterval and not self.updating):
                # set to True to prevent it to run a new update before the previous one is finished
                self.updating        = True

                self.last_dom_update = int(time.time())
                
                if debug:
                    self.logger.log_message(self.avg_values) 
                
                for key, value in self.avg_values.items():
                    if not key in sensors.sensors:
                        continue
                    
                    name    = sensors.sensors[key]['name']

                    if key == "ah_remaining" or key == "cap" or key == "accum_charge_cap" or key == "discharge" or key == "charge":
                        val   = self.average(value * 48 , 2)
                    elif key == "mins_remaining":
                        val   = self.average(value, 0)
                    else:
                        val   = self.average(value, 1)

                    if val > -99:
                        sensors.MqqtToHa.send_value(name, val)
                    
                    # reset the values  
                    self.avg_values[key] = []  

                # https://www.home-assistant.io/docs/configuration/templating/#time
                # 2023-07-30T20:03:49.253717+00:00
                timestring  = str(datetime.now(datetime.now().astimezone().tzinfo).isoformat())
                if debug:
                    self.logger.log_message(f"Sending time: {timestring}") 

                sensors.MqqtToHa.send_value('last_message', timestring, False)

                self.updating        = False
        except Exception as e:
            self.logger.log_message(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")
                
    def process_data(self, data):
        try:
            params = {
                "voltage":          "c0",       
                "current":          "c1",       # Amps
                "cur_soc":          "d0",       # %
                "dir_of_current":   "d1",   
                "ah_remaining":     "d2",
                "discharge":        "d3",		# todays total in kWh
                "charge":           "d4",       # todays total in kWh
                "accum_charge_cap": "d5",       # accumulated charging capacity Ah (/1000)
                "mins_remaining":   "d6",
                "power":            "d8",       # Watt
                "temp":             "d9",       # C
                "full_charge_volt": "e6",
                "zero_charge_volt": "e7",
            }

            params_keys         = list(params.keys())
            params_values       = list(params.values())

            # split bs into a list of all values and hex keys
            bs_list             = [data[i:i+2] for i in range(0, len(data), 2)]

            # reverse the list so that values come after hex params
            bs_list_rev         = list(reversed(bs_list))

            values      = {}
            # iterate through the list and if a param is found,
            # add it as a key to the dict. The value for that key is a
            # concatenation of all following elements in the list
            # until a non-numeric element appears. This would either
            # be the next param or the beginning hex value.
            for i in range(len(bs_list_rev)-1):
                if bs_list_rev[i] in params_values:
                    value_str = ''
                    j = i + 1
                    while j < len(bs_list_rev) and bs_list_rev[j].isdigit():
                        value_str = bs_list_rev[j] + value_str
                        j += 1

                    position    = params_values.index(bs_list_rev[i])

                    key         = params_keys[position]
                    
                    values[key] = value_str
                    
            if debug:
                if not values: 
                    self.logger.log_message(f"Nothing found for {data}")
                else:
                    self.logger.log_message(values)

            # now format to the correct decimal place, or perform other formatting
            for key,value in list(values.items()):
                if not value.isdigit():
                    del values[key]

                val_int = int(value)                
                if key == "voltage":
                    voltage   = val_int / 100 
                    if voltage > 40:
                        values[key] = voltage               
                elif key == "current":
                    values[key] = val_int / 100
                    
                    if self.charging == False:
                        values["current"] *= -1
                elif key == "discharge":
                    values[key] = val_int / 100000
                    self.charging = False
                elif key == "charge":
                    values[key] = val_int / 100000
                    self.charging = True
                elif key == "dir_of_current":
                    if value == "01":
                        self.charging = True
                    else:
                        self.charging = False
                elif key == "ah_remaining":
                    values[key] = val_int / 1000
                elif key == "mins_remaining":
                    values[key] = val_int
                elif key == "power":
                    values[key] = val_int / 100
                    
                    if self.charging == False:
                        values["power"] *= -1
                elif key == "temp":
                    temp    = val_int - 100
                    self.logger.log_message(f"Temp = {temp}")

                    if temp > 10:
                        values[key] = temp
                elif key == "accum_charge_cap":
                    values[key] = val_int / 1000    
                    
                # add to the values to be averaged
                self.add_to_average(key, values[key])

            # Calculate percentage
            if "ah_remaining" in values:
                values["soc"] = values["ah_remaining"] / battery_capacity_ah * 100
                self.add_to_average("soc", values["soc"])

            # Now it should be formatted corrected, in a dictionary
            if debug:
                self.logger.log_message(values) 
            
            # send to home assistant every minute            
            self.send_to_ha()  
        except Exception as e:
            self.logger.log_message(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

manager = gatt.DeviceManager(adapter_name='hci0')

lgr = logger.Logger()

# Run discovery
manager.update_devices()
lgr.log_message("Starting discovery...")
# scan all the advertisements from the services list
manager.start_discovery()
discovering = True
wait = 15
found = []
# delay / sleep for 10 ~ 15 sec to complete the scanning
while discovering:
    time.sleep(1)
    f = len(manager.devices())
    lgr.log_message("Found {} BLE-devices so far".format(f))
    found.append(f)
    if len(found) > 5:
        if found[len(found) - 5] == f:
            # We did not find any new devices the last 5 seconds
            discovering = False
    wait = wait - 1
    if wait == 0:
        discovering = False

manager.stop_discovery()
lgr.log_message("Found {} BLE-devices".format(len(manager.devices())))

def connect():
    for dev in manager.devices():
        lgr.log_message("Processing device {} {}".format(dev.mac_address, dev.alias()))
        if MAC_ADDRESS:
            mac = MAC_ADDRESS.lower()
            if dev.mac_address.lower() == mac:
                lgr.log_message("Trying to connect to {}...".format(dev.mac_address))

                try:
                    device = AnyDevice(mac_address=mac, manager=manager)
                    lgr.log_message("Connected!")
                except Exception as e:
                    lgr.log_message(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")
                    
                    lgr.log_message("Trying again, terminate with Ctrl+C")
                    connect()

                device.connect()
        
connect()

if MAC_ADDRESS:
    lgr.log_message("Terminate with Ctrl+C")

    try:
        manager.run()
    except KeyboardInterrupt:
        lgr.log_message("Terminating")
        sensors.MqqtToHa.logger.log_message('Program killed: running cleanup code')
        sensors.MqqtToHa.client.publish(f'system-sensors/sensor/{sensors.MqqtToHa.device_name}/availability', 'offline', retain=True)
        sensors.MqqtToHa.client.disconnect()
        sensors.MqqtToHa.client.loop_stop()
        sys.stdout.flush()
        lgr.log_message("Succesfully terminated")
    except Exception as e:
        lgr.log_message(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    for dev in manager.devices():
        dev.disconnect()
else:
    lgr.log_message("Choose a mac address from the list and enter it into ble_config.ini")
            