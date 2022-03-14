# PIR2HA: a PIR to Home Assistant script with MQTT Auto-Discovery
My search for a PIR to HA (Home Assistant) work-out-of-the-box solution wasn't a success.

Since I am not having the necessary skills to write my own script, I decided to create my Frankenstein, using the code from two working scripts:
https://github.com/R4scal/mhz19-mqtt-daemon (Most of the code comes from this)
https://github.com/robmarkoski/pi-motion-mqtt-sensor 
Thank you very much @robmarkoski and @R4skal

This python script should work in any Rpi with a PIR connected to a GPIO and will create an entity in HA through MQTT Auto Discovery.

# Installation:
We need some py scripts to install first:
```
pip3 install paho-mqtt sdnotify colorama Unidecode
```
Clone the repository to your home directory
```
git clone https://github.com/Chreece/pir2ha
cd pir2ha
```

Check the values from config are ok with your installment
```
nano config.ini
```
If the values in config.ini aren't right for you, uncomment them and change only what needs to be changed (ctr+x to exit and save any changes).

Check if the service is right:
```
nano pir2ha.service
```
and then copy it to the system folder and start it:
```
sudo cp pir2ha.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable pir2ha
sudo systemctl start pir2ha
```

After that a new binary_sensor entity should arrive in HA with the name from your host + "pir" (i.e. raspberrypi_pir).
Since there is a device_class: motion it should already have the motion icon and you can also make changes in the UI because of the unique_id.

ENJOY!
