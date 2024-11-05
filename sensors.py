import shared

# The main device that contains the sensors
device              = {
    "identifiers": [
        "solar_batteries_ble"
    ],
    "name": "Battery Status Monitor",
    "model": "Junctec",
    "manufacturer": "Ewald Harmsen"
}

# Sensor definition
sensors = {
    'voltage': {
        "name": "Voltage",
        "state": "measurement",
        "unit": "V",
        "type": "VOLTAGE",
        "icon": "mdi:flash-triangle"
    },
    'current': {
        "name": "Current",
        "state": "measurement",
        "unit": "A",
        "type": "CURRENT",
        "icon": "mdi:current-ac"
    },
    'power': {
        "name": "Power",
        "state": "measurement",
        "unit": "W",
        "type": "POWER",
        "icon": "mdi:home-lightning-bolt-outline"
    },
    'temp': {
        "name": "Temperature",
        "state": "measurement",
        "unit": "°C",
        "type": "TEMPERATURE",
        "icon": "mdi:thermometer"
    },
    'soc': {
        "name": "Socket",
        "state": "measurement",
        "unit": "%",
        "type": "BATTERY",
        #"icon": "mdi:thermometer"
    },
    'ah_remaining': {
        "name": "Remaining Energy",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        #"icon": "mdi:thermometer"
    },
    'mins_remaining': {
        "name": "Remaining Time",
        "state": "measurement",
        "unit": "min",
        "type": "DURATION",
        #"icon": "mdi:thermometer"
    },
    'max_capacity': {
        "name": "Capacity",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        #"icon": "mdi:thermometer",
        "init": 400 * 48
    },
    'accum_charge_cap': {
        "name": "Accumulated Charged Load",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        #"icon": "mdi:thermometer"
    },
    'discharge': {
        "name": "Discharged Today",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        #"icon": "mdi:thermometer"
    },
    'charge': {
        "name": "Charged Today",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        #"icon": "mdi:thermometer"
    }
}

MqqtToHa    = shared.MqqtToHa(device, sensors)
