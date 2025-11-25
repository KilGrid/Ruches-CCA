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
import os
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

# --- Gestion du modem 4g pour économiser de la batterie ---
def modem_off():
    """Coupe proprement la connexion 4G pour éviter les erreurs dhclient."""
    try:
        # Libère totalement la configuration DHCP
        subprocess.run(["sudo", "dhclient", "-r", "eth1"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        time.sleep(1)  # laisse dhclient terminer proprement

        # Désactive l'interface
        subprocess.run(["sudo", "ip", "link", "set", "eth1", "down"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        print("4G éteinte proprement")
    except Exception as e:
        print(f"Erreur extinction 4G: {e}")

def modem_on():
    """Réactive proprement la 4G avec une configuration DHCP propre."""
    try:
        # Active l'interface
        subprocess.run(["sudo", "ip", "link", "set", "eth1", "up"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        time.sleep(1)

        # Libère d'abord tout ancien état DHCP (important !)
        subprocess.run(["sudo", "dhclient", "-r", "eth1"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        # Redemande une IP propre
        subprocess.run(["sudo", "dhclient", "eth1"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        print("4G réactivée proprement")
    except Exception as e:
        print(f"Erreur activation 4G: {e}")



# --- HTTP SESSION ROBUSTE ---
session = requests.Session()
retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

def attendre_connexion(timeout=180, retry_delay=5):
    """Attend que la connexion Internet 4G soit disponible"""
    print("Vérification de la connexion 4G...")
    start = time.time()
    while True:
        try:
            subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,   # important
            )
            print("Connexion 4G opérationnelle")
            return True
        except subprocess.CalledProcessError:
            pass
        if time.time() - start > timeout:
            print("Connexion 4G indisponible après délai, poursuite du programme.")
            return False
        print("En attente de la 4G...")
        time.sleep(retry_delay)


# === CAPTEURS ===
def charger_modules():
    """Active les modules 1-Wire nécessaires au capteur DS18B20"""
    try:
        subprocess.run(['sudo', 'modprobe', 'w1-gpio'], check=True)
        subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)
        print("Modules 1-Wire chargés")
    except subprocess.CalledProcessError:
        print("Impossible d’activer le module 1-Wire (déjà actif ?)")

def lire_hx711_brut(dout, sck, timeout_s=0.2):
    """Lecture non bloquante du HX711."""
    # Attente du front bas (data ready)
    t0 = time.time()
    while GPIO.input(dout) == 1:
        if time.time() - t0 > timeout_s:
            raise TimeoutError("HX711 bloqué (DT HIGH)")
        time.sleep(0.0001)

    # Lecture 24 bits
    value = 0
    for _ in range(24):
        GPIO.output(sck, True)
        time.sleep(0.000001)
        value = (value << 1) | GPIO.input(dout)
        GPIO.output(sck, False)
        time.sleep(0.000001)

    # Bits de gain
    GPIO.output(sck, True)
    time.sleep(0.000001)
    GPIO.output(sck, False)

    # Convertir signed
    if value & (1 << 23):
        value -= 1 << 24

    return value

def initialiser_hx711():
    global OFFSET

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HX711_DT, GPIO.IN)
    GPIO.setup(HX711_SCK, GPIO.OUT)

    print("Initialisation HX711...")

    while True:
        try:
            print("Mise à zéro... Ne pas poser de charge.")

            valeurs = [lire_hx711_brut(HX711_DT, HX711_SCK) for _ in range(10)]
            OFFSET = statistics.mean(valeurs)

            print(f"Balance HX711 initialisée (tare = {OFFSET:.2f})")
            return True

        except Exception as e:
            print(f"⚠️ HX711 non prêt : {e} → nouvelle tentative dans 2 s")
            time.sleep(2)


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


def lire_poids(_):
    try:
        valeurs = [lire_hx711_brut(HX711_DT, HX711_SCK) for _ in range(5)]
        valeur_moyenne = statistics.mean(valeurs)
        poids_grammes = (valeur_moyenne - OFFSET) / SCALE_FACTOR

        if abs(poids_grammes) > 20000:
            return None, f"Poids aberrant: {poids_grammes:.2f} g"

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

# === BUFFER LOCAL (OFFLINE STORAGE) ===
BUFFER_FILE = "buffer.txt"

def enregistrer_dans_buffer(line, max_size_bytes=1_000_000):
    """Ajoute une ligne de mesure dans le buffer local avec limite de taille"""
    try:
        if os.path.exists(BUFFER_FILE) and os.path.getsize(BUFFER_FILE) > max_size_bytes:
            print("Buffer plein, suppression des anciennes données.")
            os.remove(BUFFER_FILE)
        with open(BUFFER_FILE, "a") as f:
            f.write(line + "\n")
        print("Mesure sauvegardée localement (offline)")
    except Exception as e:
        print(f"Erreur écriture buffer: {e}")

def envoyer_buffer():
    """Tente d’envoyer toutes les mesures sauvegardées"""
    if not os.path.exists(BUFFER_FILE):
        return
    try:
        with open(BUFFER_FILE, "r") as f:
            lignes = [l.strip() for l in f.readlines() if l.strip()]
        if not lignes:
            return
        print(f"Tentative d’envoi du buffer ({len(lignes)} mesures)...")

        for line in lignes:
            try:
                r = session.post(WRITE_ENDPOINT, params=PARAMS, headers=HEADERS,
                                 data=line.encode("utf-8"), timeout=10)
                r.raise_for_status()
            except Exception as e:
                print(f"Échec envoi ligne buffer: {e}")
                break
        else:
            print("Buffer vidé avec succès.")
            os.remove(BUFFER_FILE)
    except Exception as e:
        print(f"Erreur lecture/envoi buffer: {e}")

# === ENVOI INFLUX ===
def send_point(temp, poids, batt_v, batt_pct, temp_cpu):
    """Format et envoie les données vers InfluxDB, avec buffer local."""
    ts = int(time.time())
    line = (
        f"ruches,device={DEVICE},site={SITE} "
        f"temperature={temp:.1f},"
        f"poids={poids:.2f},"
        f"battery={batt_v:.3f},"
        f"battery_pct={batt_pct:.1f},"
        f"cpu_temp={temp_cpu:.1f} {ts}"
    )
    print(f"DEBUG → {line}")

    # Activation modem 4G
    modem_on()
    time.sleep(2)  # Laisser le temps au modem d’obtenir une IP

    # Vérifie la connexion
    try:
        subprocess.run(
            ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except subprocess.CalledProcessError:
        print("4G absente — mesure stockée localement.")
        enregistrer_dans_buffer(line)
        return False

    # Envoi en ligne
    try:
        r = session.post(
            WRITE_ENDPOINT,
            params=PARAMS,
            headers=HEADERS,
            data=line.encode("utf-8"),
            timeout=10
        )
        r.raise_for_status()

        print(f"Données envoyées ({time.strftime('%H:%M:%S')})")
        envoyer_buffer()  # tenter de vider le buffer après chaque succès

        # Désactivation modem 4G après succès
        modem_off()

        return True

    except Exception as e:
        print(f"Erreur envoi InfluxDB: {e} → sauvegarde locale.")
        enregistrer_dans_buffer(line)
        return False


def lire_temperature_cpu():
    """Retourne la température CPU en °C"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_millideg = int(f.read().strip())
        return round(temp_millideg / 1000.0, 1)
    except Exception as e:
        print(f"Erreur lecture température CPU: {e}")
        return None


# === MAIN LOOP ===
def main():
    print(" Ruche connectée CCA — démarrage")
    print("=" * 60)

    charger_modules()
    attendre_connexion()
    hx = initialiser_hx711()

    compteur = 1
    while True:
        print(f"\n Mesure #{compteur}")

        # === LECTURES CAPTEURS ===
        temp, msg_t = lire_temperature()
        poids, msg_p = lire_poids(hx)
        batt_v, batt_pct, msg_b = lire_batterie()
        temp_cpu = lire_temperature_cpu()

        # === DONNÉES COHÉRENTES ? ===
        if all(v is not None for v in [temp, poids, batt_v]):
            print(f"{temp:.1f} °C |  {poids:.2f} g | {batt_v:.3f} V ({batt_pct:.1f}%)")

            # === ENVOI DES DONNÉES ===
            send_point(temp, poids, batt_v, batt_pct, temp_cpu)

        else:
            print(f" Lecture incomplète: {msg_t}, {msg_p}, {msg_b}")

        # === PROCHAINE MESURE ===
        compteur += 1
        print(f" Attente {INTERVAL} s avant la prochaine mesure...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("\n Arrêt manuel, GPIO libérés.")
