#!/usr/bin/python3
#
#   Pi PIR Motion with Home Assistant MQTT Discovery
#
#   Version:    0.1
#   Status:     Development
#   Github:     https://github.com/Chreece/pi_motion_home_assistant
#   Credits:    https://github.com/R4scal/mhz19-mqtt-daemon and https://github.com/robmarkoski/pi-motion-mqtt-sensor

import os
import logging
from gpiozero import MotionSensor
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import socket
import ssl
import sys
import re
import json
import os.path
import argparse
from time import time, sleep, localtime, strftime
from configparser import ConfigParser
from unidecode import unidecode
from colorama import init as colorama_init
from colorama import Fore, Back, Style
from unidecode import unidecode
import sdnotify

project_name = 'Pi PIR Motion with Home Assistant MQTT Discovery'
project_url = 'https://github.com/Chreece/pi_motion_home_assistant'

if False:
    # will be caught by python 2.7 to be illegal syntax
    print('Sorry, this script requires a python3 runtime environemt.', file=sys.stderr)


# Argparse
parser = argparse.ArgumentParser(description=project_name, epilog='For further details see: ' + project_url)
parser.add_argument('--config_dir', help='set directory where config.ini is located', default=sys.path[0])
parse_args = parser.parse_args()

# Intro
colorama_init()
print(Fore.GREEN + Style.BRIGHT)
print(project_name)
print('Source:', project_url)
print(Style.RESET_ALL)

# Systemd Service Notifications - https://github.com/bb4242/sdnotify
sd_notifier = sdnotify.SystemdNotifier()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print_line('MQTT connection established', console=True, sd_notify=True)
        print()
    else:
        print_line('Connection error with result code {} - {}'.format(str(rc), mqtt.connack_string(rc)), error=True)
        #kill main thread
        os._exit(1)

def on_publish(client, userdata, mid):
    #print_line('Data successfully published.')
    pass

def print_line(text, error = False, warning=False, sd_notify=False, console=True):
    timestamp = strftime('%Y-%m-%d %H:%M:%S', localtime())
    if console:
        if error:
            print(Fore.RED + Style.BRIGHT + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL, file=sys.stderr)
        elif warning:
            print(Fore.YELLOW + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL)
        else:
            print(Fore.GREEN + '[{}] '.format(timestamp) + Style.RESET_ALL + '{}'.format(text) + Style.RESET_ALL)
    timestamp_sd = strftime('%b %d %H:%M:%S', localtime())
    if sd_notify:
        sd_notifier.notify('STATUS={} - {}.'.format(timestamp_sd, unidecode(text)))

config_dir = parse_args.config_dir
config = ConfigParser(delimiters=('=', ))
config.optionxform = str
config.read([os.path.join(config_dir, 'config.ini.dist'), os.path.join(config_dir, 'config.ini')])

base_topic = 'homeassistant'

pir = MotionSensor(config['PIR'].getint('gpio', 7),  threshold=config['PIR'].getfloat('threshold', 0.5))

print_line('Connecting to MQTT broker ...')
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish

if config['MQTT'].getboolean('tls', False):
# According to the docs, setting PROTOCOL_SSLv23 "Selects the highest protocol version
# that both the client and server support. Despite the name, this option can select
# “TLS” protocols as well as “SSL”" - so this seems like a resonable default
        mqtt_client.tls_set(
            ca_certs=config['MQTT'].get('tls_ca_cert', None),
            keyfile=config['MQTT'].get('tls_keyfile', None),
            certfile=config['MQTT'].get('tls_certfile', None),
            tls_version=ssl.PROTOCOL_SSLv23
        )

if config['MQTT'].get('username'):
     mqtt_client.username_pw_set(config['MQTT'].get('username'), config['MQTT'].get('password', None))
try:
  mqtt_client.connect(config['MQTT'].get('hostname', 'localhost'),
                      port=config['MQTT'].getint('port', 1883),
                      keepalive=config['MQTT'].getint('keepalive', 60))
except:
  print_line('MQTT connection error. Please check your settings in the configuration file "config.ini"', error=True, sd_notify=True)
  sys.exit(1)
else:
   mqtt_client.loop_start()
   sleep(1.0) # some slack to establish the connection

# Set the sensor name based on the hostname
sensor_name = '{}_pir'.format(socket.gethostname()).replace("-", "_")

print_line('Current sensor name is "{}"'.format(sensor_name).lower())
print_line('Announcing PIR to MQTT broker for auto-discovery ...')

# Set MQTT topic path to be homeassistant/binary_sensor/<sensor name>
topic_path = '{}/binary_sensor/{}'.format(base_topic, sensor_name)

base_payload = {
        "state_topic": "{}/state".format(topic_path).lower()
}

payload = dict(base_payload.items())
# The entity name will be the sensor name from above
payload['name'] = "{}".format(sensor_name)
# Device class set to motion. Home assistant knows which icon to choose
payload['device_class'] = 'motion'
# The motion entity will be on when we will send the "on" state
payload['payload_on'] = 'on'
# The motion entity will be off when we will send the "off" state
payload['payload_off'] = 'off'
# To give the ability to change name, entity_id etc. in ha, a unique_id must be set. Here we give the name from the sensor
payload['unique_id'] = sensor_name
mqtt_client.publish('{}/{}/config'.format(topic_path, sensor_name).lower(), json.dumps(payload), 1, True)

try:
    # Wait the motion sensor to cool_down and then go to a loop
    pir.wait_for_no_motion()
    while True:
        pir.wait_for_motion()
        print_line('Motion detected...')
        try:
          mqtt_client.publish('{}/binary_sensor/{}/state'.format(base_topic, sensor_name).lower(), "on")
          sleep(0.5)
          print()
          print_line('Status messages published', console=False, sd_notify=True)
        except:
          print_line('MQTT error!', console=False, sd_notify=True)
        pir.wait_for_no_motion()
        print_line('No more motion detected...')
        try:
          mqtt_client.publish('{}/binary_sensor/{}/state'.format(base_topic, sensor_name).lower(), "off")
          sleep(0.5)
          print()
          print_line('Status messages published', console=False, sd_notify=True)
        except:
          print_line('MQTT error!', console=False, sd_notify=True)
except KeyboardInterrupt:
    logging.info("KEY INTERRUPT - STOPPING SERVER")
except:
    logging.exception("PIR SENSOR ERROR")
