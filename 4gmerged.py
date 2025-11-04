#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruches Connectées CCA Entremont
---------------------------------
Mesure de température, poids, tension batterie
et envoi vers InfluxDB Cloud via 4G (Air780E)

Compatible Raspberry Pi 5 + HAT FIT0992
"""

import time
import json
import glob
import requests
import subprocess
import statistics
import smbus2
import RPi.GPIO as GPIO
from hx711 import HX711
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
logging.getLogger().setLevel(logging.ERROR)



# --- CHARGEMENT CONFIGURATION ---
with open("config.json", "r") as f:
    CONFIG = json.load(f)

DEVICE = CONFIG["device"]
SITE = CONFIG["site"]
INTERVAL = CONFIG["interval"]

INFLUX_URL = CONFIG["influx_url"].rstrip("/")
INFLUX_ORG = CONFIG["influx_org"]
INFLUX_BUCKET = CONFIG["influx_bucket"]
INFLUX_TOKEN = CONFIG["influx_token"]

# --- INFLUXDB SETUP ---
WRITE_ENDPOINT = f"{INFLUX_URL}/api/v2/write"
PARAMS = {"org": INFLUX_ORG, "bucket": INFLUX_BUCKET, "precision": "s"}
HEADERS = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8"
}

# --- CONFIG CAPTEURS ---
HX711_DT = 5
HX711_SCK = 6
SCALE_FACTOR = 92
OFFSET = 0
I2C_ADDR_BAT = 0x36

# --- HTTP SESSION ROBUSTE ---
session = requests.Session()
retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))


# === CAPTEURS ===
def charger_modules():
    """Active les modules 1-Wire nécessaires au capteur DS18B20"""
    try:
        subprocess.run(['sudo', 'modprobe', 'w1-gpio'], check=True)
        subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)
        print("✅ Modules 1-Wire chargés")
    except subprocess.CalledProcessError:
        print("⚠️ Impossible d’activer le module 1-Wire (déjà actif ?)")


def initialiser_hx711():
    """Initialise la balance HX711"""
    global OFFSET
    GPIO.setmode(GPIO.BCM)
    hx = HX711(dout_pin=HX711_DT, pd_sck_pin=HX711_SCK, channel='A', gain=128)
    hx.reset()
    print("Mise à zéro... Ne pas poser de charge.")
    raw_data = hx.get_raw_data(times=10)
    OFFSET = statistics.mean(raw_data)
    print(f"✅ Balance HX711 initialisée (tare = {OFFSET:.2f})")
    return hx


def lire_temperature():
    """Lecture température (°C) DS18B20"""
    try:
        capteurs = glob.glob('/sys/bus/w1/devices/28-*')
        if not capteurs:
            return None, "Capteur DS18B20 non trouvé"
        with open(f"{capteurs[0]}/w1_slave", "r") as f:
            temp_line = f.readlines()[1]
        temp_c = float(temp_line.split("t=")[1]) / 1000.0
        return temp_c, "OK"
    except Exception as e:
        return None, f"Erreur DS18B20: {e}"


def lire_poids(hx):
    """Lecture poids (g) HX711"""
    try:
        raw_data = hx.get_raw_data(times=5)
        valeur_moyenne = statistics.mean(raw_data)
        poids_grammes = (valeur_moyenne - OFFSET) / SCALE_FACTOR
        return poids_grammes, "OK"
    except Exception as e:
        return None, f"Erreur HX711: {e}"


def lire_batterie():
    """Lecture tension (V) et charge (%) via HAT FIT0992"""
    try:
        bus = smbus2.SMBus(1)
        vcell = bus.read_word_data(I2C_ADDR_BAT, 0x02)
        vcell = ((vcell & 0xFF) << 8) | (vcell >> 8)
        voltage = (vcell >> 4) * 1.25 / 1000.0
        soc = bus.read_word_data(I2C_ADDR_BAT, 0x04)
        soc = ((soc & 0xFF) << 8) | (soc >> 8)
        percent = soc / 256.0
        return voltage, percent, "OK"
    except Exception as e:
        return None, None, f"Erreur batterie: {e}"


# === ENVOI INFLUX ===
def send_point(temp, poids, batt_v, batt_pct):
    """Format et envoie les données vers InfluxDB"""
    try:
        ts = int(time.time())
        line = (
            f"ruches,device={DEVICE},site={SITE} "
            f"temperature={temp:.1f},poids={poids:.2f},"
            f"battery={batt_v:.3f},battery_pct={batt_pct:.1f} {ts}"
        )
        print(f"DEBUG → {line}")   # ✅ AJOUT ICI
        r = session.post(WRITE_ENDPOINT, params=PARAMS, headers=HEADERS,
                         data=line.encode("utf-8"), timeout=10)
        r.raise_for_status()
        print(f"✅ Données envoyées ({time.strftime('%H:%M:%S')})")
    except Exception as e:
        print(f"❌ Erreur envoi InfluxDB: {e}")



# === MAIN LOOP ===
def main():
    print("🌡️⚖️🔋 Ruche connectée CCA — démarrage")
    print("=" * 60)

    charger_modules()
    hx = initialiser_hx711()

    compteur = 1
    while True:
        print(f"\n📊 Mesure #{compteur}")
        temp, msg_t = lire_temperature()
        poids, msg_p = lire_poids(hx)
        batt_v, batt_pct, msg_b = lire_batterie()

        if all(v is not None for v in [temp, poids, batt_v]):
            print(f"🌡️ {temp:.1f} °C | ⚖️ {poids:.2f} g | 🔋 {batt_v:.3f} V ({batt_pct:.1f}%)")
            send_point(temp, poids, batt_v, batt_pct)
        else:
            print(f"⚠️ Lecture incomplète: {msg_t}, {msg_p}, {msg_b}")

        compteur += 1
        print(f"⏳ Attente {INTERVAL} s avant la prochaine mesure...")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("\n👋 Arrêt manuel, GPIO libérés.")
