from bleak import BleakScanner, BleakClient, BleakError
import asyncio
import logger
import sys
import json
import mqtt
import sensors
from datetime import datetime
import signal
import os

class DeviceNotFoundError(Exception):
    pass

class JunctekMonitor:
    def __init__(self):
        self.should_quit        = False
        self.found              = []
        self.charging           = False
        file_path		        = '/data/options.json'
        self.local		        = False
        self.device             = None

        signal.signal(signal.SIGTERM, self.signal_handler)

        self.params = {
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

        self.params_keys         = list(self.params.keys())
        self.params_values       = list(self.params.values())

        if not os.path.exists(file_path):
            self.local	= True
            file_path	= os.path.dirname(os.path.realpath(__file__))+file_path
					
        # Get Options
        with open(file_path, mode="r") as data_file:
            config = json.load(data_file)
            self.log_level           = config.get('log_level')
            self.mac_address         = config.get('macaddress').upper()
            self.battery_capacity    = int(config.get('battery capacity'))
            self.battery_voltage     = int(config.get('voltage'))

        self.logger                  = logger.Logger(self)

        if self.log_level == 'debug':
            self.debug              = True
        else:
            self.debug              = False

        self.MqqtToHa               = mqtt.MqqtToHa(self)

        self.stop_event             = asyncio.Event()
        self.disconnect_event       = asyncio.Event()
        

    def signal_handler(self, sig, frame):
        self.logger.warning(f'Received signal {sig}')
        self.logger.warning('Cleaning up...')
        
        # Set the shutdown flag
        self.should_quit    = True

    async def discover(self):
        try:
            devices    = await BleakScanner.discover()

            self.logger.debug("Found Devices")
            for device in devices:
                self.logger.info(f"BT Device found:\nName: {device.name}\nAddress: {device.address}")
                self.logger.debug(device)

            self.logger.debug("Finished discovery")
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def process_data(self, _, value):       
        try:
            data = str(value.hex())

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
                if bs_list_rev[i] in self.params_values:
                    value_str = ''
                    j = i + 1
                    while j < len(bs_list_rev) and bs_list_rev[j].isdigit():
                        value_str = bs_list_rev[j] + value_str
                        j += 1

                    position    = self.params_values.index(bs_list_rev[i])

                    key         = self.params_keys[position]
                    
                    values[key] = value_str
                    
            if self.debug:
                if not values: 
                    self.logger.warning(f"Nothing found for {data}")
                else:
                    self.logger.debug(f"Raw values: {values}")

            # now format to the correct decimal place, or perform other formatting
            for key, value in list(values.items()):
                if not value.isdigit():
                    del values[key]

                val_int = int(value)                
                if key == "voltage":
                    voltage   = val_int / 100 

                    # Only keep valid values leave out unrealistically values
                    if voltage > ( self.battery_voltage - (self.battery_voltage * 0.2)):
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

                    if temp > 10:
                        values[key] = temp
                elif key == "accum_charge_cap":
                    values[key] = val_int / 1000    

            # Calculate percentage
            if "ah_remaining" in values:
                values["soc"] = values["ah_remaining"] / self.battery_capacity * 100

            # Now it should be formatted corrected, in a dictionary
            if self.debug:
                self.logger.debug(f"Final values: {values}")

            await self.send_to_ha(values)

        except Exception as e:
            self.logger.error(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def send_to_ha(self, values):
        try:           
            for key, value in values.items():
                if not key in sensors.sensors:
                    continue

                if key == "ah_remaining" or key == "cap" or key == "accum_charge_cap" or key == "discharge" or key == "charge":
                    val   = round(value *  self.battery_voltage, 2)
                elif key == "mins_remaining":
                    val   = round(value , 0)
                else:
                    val   = round(value , 1)

                if val > -99:
                    self.MqqtToHa.send_value(key, val)
                    
            # https://www.home-assistant.io/docs/configuration/templating/#time
            # 2023-07-30T20:03:49.253717+00:00
            timestring  = str(datetime.now(datetime.now().astimezone().tzinfo).isoformat())
            if self.debug:
                self.logger.debug(f"Sending time: {timestring}") 

            self.MqqtToHa.send_value('last_message', timestring, False)
        except Exception as e:
            self.logger.error(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    def scanner_callback(self, device, advertisement_data):
        try:
            name    = advertisement_data.local_name

            if device.address.upper() == self.mac_address:
                self.logger.info(f"Found device\nAddress: {device.address}\nName: {name}\nRssi: {advertisement_data.rssi}")
                self.device = device
                self.stop_event.set()
            elif not device.address in self.found:
                self.found.append(device.address)

                if name == None:
                    self.logger.info(f"Found '{device.address}'")
                else:
                    self.logger.info(f"Found '{name}' with address '{device.address}'")
            else:
                if name == None:
                    self.logger.debug(f"'{device.address}' is not: {self.mac_address}")
                else:
                    self.logger.debug(f"{name} with address '{device.address}' is not: {self.mac_address}")
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    def disconnected_callback(self, client):
        try:
            self.logger.debug(f"Disconnected {client}")
            self.disconnect_event.set()
            self.stop_event.clear()
            self.device = None
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def connect(self):
        try:
            # Do not run if already connected
            if self.device != None:
                return
            
            async with BleakScanner(self.scanner_callback) as scanner:
                # Important! Wait for an event to trigger stop, otherwise scanner
                # will stop immediately.
                await self.stop_event.wait()
                self.logger.info(f"Connected to {self.device}")
        
            # scanner stops when block exits
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def main(self):
        while not self.should_quit:
            await  self.connect()

            self.logger.info("Starting Listener")
            try:
                while self.device == None:
                    self.logger.debug("Waiting for device conection")
                    await asyncio.sleep(5)

                async with BleakClient(self.device, disconnected_callback=self.disconnected_callback) as client:
                    self.logger.info(f"Connected to {self.device.name}")
                    
                    read_characteristic_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"
                    
                    self.logger.debug(f"read_characteristic_uuid is {read_characteristic_uuid}")
                    
                    await client.start_notify(read_characteristic_uuid, self.process_data)

                    # Wait till disconnected
                    await self.disconnect_event.wait()

                    await asyncio.sleep(5)

                    # Now run again to connect again
                    self.disconnect_event.clear()
            except BleakError as e:
                self.logger.error(f"Error: {e}")
                #continue  # continue in error case 
            except TimeoutError as e:
                self.logger.debug(f"Timeout {e}")
            except Exception as e:
                if str(e) != '':
                    self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        junctekMonitor  = JunctekMonitor()

        if junctekMonitor.mac_address == '':
            junctekMonitor.logger.debug("Starting discovery")
            asyncio.run(junctekMonitor.discover())
        else:
            junctekMonitor.logger.debug("Starting connection")
            asyncio.run(junctekMonitor.main())

            junctekMonitor.logger.info("Finished")
    except KeyboardInterrupt:
        junctekMonitor.logger.debug("ctrl+c pressed")
    except Exception as e:
        junctekMonitor.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")
        """         async with BleakClient(device) as client:
            self.logger.debug("connected")
            await client.stop_notify(read_characteristic_uuid) """
