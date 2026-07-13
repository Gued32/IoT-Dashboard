import network
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print("Suche WLAN-Netzwerke...")
time.sleep(2)

networks = wlan.scan()

for net in networks:
    ssid = net[0].decode()
    rssi = net[3]
    authmode = net[4]
    print("SSID:", ssid, "| Signal:", rssi, "| Auth:", authmode)