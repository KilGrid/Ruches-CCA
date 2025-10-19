#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4g_capteurs.py — Lecture des capteurs (température, poids) et envoi vers InfluxDB v2 via 4G
Basé sur le code LoRa existant, adapté pour envoi 4G
"""

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import subprocess
import glob
import RPi.GPIO as GPIO
from hx711 import HX711
import statistics

# --- CONFIG INFLUXDB ---
INFLUX_URL   = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_ORG   = "CCA Entremont"
INFLUX_BUCKET= "Ruches_Test"
INFLUX_TOKEN = "EuA5d0tQQw_Doo_ZJYmh02xZ4rkGVaebAp9SCD08YO_Ry2kdBVucAPw_CvZumOxPKN7un_zSWzUUo6QvRBaY2Q=="

DEVICE = "ruche-01"
SITE   = "cabane_xyz"
INTERVAL = 60   # secondes entre deux envois

# --- CONFIG CAPTEURS ---
# Configuration des broches pour HX711
HX711_DT = 5    # Pin DT (données, GPIO 5)
HX711_SCK = 6   # Pin SCK (horloge, GPIO 6)
scale_factor = 92  # Facteur de calibration
offset = 0         # Valeur de tare initiale

# --- SETUP INFLUXDB ---
WRITE_ENDPOINT = INFLUX_URL.rstrip("/") + "/api/v2/write"
PARAMS = {"org": INFLUX_ORG, "bucket": INFLUX_BUCKET, "precision": "s"}
HEADERS = {
    "Authorization": f"Token {INFLUX_TOKEN}",
    "Content-Type": "text/plain; charset=utf-8",
}

# Session avec retries (robuste 4G)
session = requests.Session()
retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

def charger_modules():
    """Charge les modules 1-Wire pour la température"""
    try:
        subprocess.run(['sudo', 'modprobe', 'w1-gpio'], check=True)
        subprocess.run(['sudo', 'modprobe', 'w1-therm'], check=True)
        print("✅ Modules 1-Wire chargés")
        return True
    except Exception as e:
        print(f"❌ Erreur chargement modules: {str(e)}")
        return False

def initialiser_hx711():
    """Initialise la balance HX711"""
    try:
        GPIO.setmode(GPIO.BCM)
        hx = HX711(dout_pin=HX711_DT, pd_sck_pin=HX711_SCK, channel='A', gain=128)
        hx.reset()
        print("Mise à zéro en cours... Ne placez aucun poids sur la balance.")
        raw_data = hx.get_raw_data(times=10)
        if raw_data:
            global offset
            offset = statistics.mean(raw_data)
            print(f"✅ Balance HX711 initialisée - Valeur de tare: {offset:.2f}")
            return hx
        else:
            print("❌ Erreur : Impossible de lire les données brutes.")
            return None
    except Exception as e:
        print(f"❌ Erreur initialisation HX711: {str(e)}")
        return None

def lire_temperature():
    """Lit la température depuis un capteur DS18B20"""
    try:
        capteurs = glob.glob('/sys/bus/w1/devices/28-*')
        if not capteurs:
            print("❌ Aucun capteur DS18B20 trouvé")
            return None, "Aucun capteur trouvé"
        
        capteur = capteurs[0]
        with open(f"{capteur}/w1_slave", 'r') as f:
            data = f.read()
        
        temp_line = data.split('\n')[1]
        temp_c = float(temp_line.split('t=')[1]) / 1000.0
        return temp_c, "OK"
    except Exception as e:
        return None, f"Erreur lecture température: {str(e)}"

def lire_poids(hx):
    """Lit le poids depuis la balance HX711"""
    try:
        raw_data = hx.get_raw_data(times=5)
        if raw_data:
            valeur_moyenne = statistics.mean(raw_data)
            poids_grammes = (valeur_moyenne - offset) / scale_factor
            return poids_grammes, "OK"
        else:
            return None, "Erreur lecture données brutes"
    except Exception as e:
        return None, f"Erreur balance: {str(e)}"

def send_point(temp, poids, rssi=-72, snr=9.5):
    """Envoie un point de données vers InfluxDB"""
    try:
        ts = int(time.time())
        # Calcul d'une valeur de batterie simulée (vous pouvez l'adapter selon vos besoins)
        batt = 3.92  # Valeur fixe ou à adapter selon votre système
        
        # Format InfluxDB Line Protocol
        line = f"air780e,device={DEVICE},site={SITE} temperature={temp:.1f},poids={poids:.2f},battery={batt},rssi={rssi}i,snr={snr} {ts}"
        
        r = session.post(WRITE_ENDPOINT, params=PARAMS, headers=HEADERS, data=line.encode("utf-8"), timeout=10)
        r.raise_for_status()
        print(f"✅ envoyé à {time.strftime('%Y-%m-%d %H:%M:%S')} : {line}")
        return True
    except Exception as e:
        print(f"❌ Erreur envoi InfluxDB: {e}")
        return False

def main():
    """Fonction principale"""
    print("🌡️⚖️ Mesure et envoi 4G vers InfluxDB - Raspberry Pi 5")
    print("=" * 60)
    
    # Initialisation des capteurs
    print("🔧 Initialisation des capteurs...")
    if not charger_modules():
        return
    
    hx = initialiser_hx711()
    if not hx:
        return
    
    print("\n" + "=" * 60)
    print("🚀 Démarrage des mesures et envois 4G...")
    print("-" * 60)
    print("⏳ Démarrage envoi périodique vers InfluxDB… (CTRL+C pour arrêter)")
    
    try:
        compteur = 1
        while True:
            print(f"\n📊 Mesure #{compteur}")
            
            # Lecture des capteurs
            temp, temp_message = lire_temperature()
            poids, poids_message = lire_poids(hx)
            
            if temp is not None and poids is not None:
                print(f"🌡️ Température: {temp:.1f}°C")
                print(f"⚖️ Poids: {poids:.2f} g")
                
                # Envoi vers InfluxDB
                succes = send_point(temp=temp, poids=poids)
                if not succes:
                    print("⚠️ Échec d'envoi, attente avant réessai...")
                    time.sleep(10)
            else:
                print(f"❌ Erreur capteurs - Temp: {temp_message}, Poids: {poids_message}")
                # En cas d'erreur capteurs, on peut envoyer des valeurs par défaut ou passer
                print("📡 Pas d'envoi à cause des erreurs capteurs")
            
            print(f"\n⏱️ Attente {INTERVAL} secondes avant prochaine mesure...")
            print("-" * 60)
            
            compteur += 1
            time.sleep(INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Programme arrêté par l'utilisateur")
    finally:
        GPIO.cleanup()
        print("✅ Nettoyage GPIO effectué")

if __name__ == "__main__":
    main()