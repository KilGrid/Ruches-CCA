🐝 README.md — Projet Ruches Connectées CCA
# 🌞🐝 Ruches Connectées – Projet CCA Entremont

Ce projet vise à déployer des **ruches connectées autonomes** capables de mesurer la **température interne** et le **poids de la ruche**, puis d’envoyer ces données en **temps réel vers InfluxDB Cloud** via une **connexion 4G**.  
L’alimentation est assurée par un **HAT solaire UPS DFRobot FIT0992**.

---

## 🧩 Architecture matérielle

**Matériel principal :**
- Raspberry Pi 5 (Bookworm, kernel 6.12.25+rpt-rpi-2712)
- Module HX711 (pesée)
- Capteur de température DS18B20 (1-Wire)
- Module 4G Air780E (communication)
- HAT UPS DFRobot FIT0992 (alimentation solaire)

**Schéma de câblage :**

| Composant | GPIO Raspberry Pi | Broche physique | Détail |
|------------|------------------|------------------|--------|
| HX711 VCC | 5 V | Pin 2 | Alimentation |
| HX711 GND | GND | Pin 6 | Masse commune |
| HX711 DT  | GPIO 5 | Pin 29 | Données |
| HX711 SCK | GPIO 6 | Pin 31 | Horloge |
| DS18B20 VCC | 3.3 V | Pin 1 | Alimentation capteur |
| DS18B20 GND | GND | Pin 9 | Masse |
| DS18B20 DATA | GPIO 4 | Pin 7 | Bus 1-Wire (résistance 4.7kΩ entre DATA et 3.3V) |

---

## 🧠 Fonctionnalités

- Lecture du **poids** via HX711  
- Lecture de la **température** via DS18B20  
- Envoi périodique (60 s) vers **InfluxDB Cloud**
- Gestion automatique de la connexion 4G
- Mode résilient : si la 4G n’est pas disponible, les envois sont reportés
- Code portable via `venv` + `requirements.txt`

---

## ⚙️ Installation (nouveau Raspberry Pi)

### 1️⃣ Cloner le projet
```bash
cd ~
git clone https://github.com/KilGrid/Ruches-CCA.git ruches-connectees
cd ruches-connectees

2️⃣ Créer l’environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages

3️⃣ Installer les dépendances
pip install -r requirements.txt --break-system-packages

4️⃣ Activer 1-Wire
sudo raspi-config
# Interface Options → 1-Wire → Enable

5️⃣ Lancer le script
source venv/bin/activate
python 4gmerged.py

📡 Connexion 4G (Air780E)

Créer le fichier /etc/ppp/peers/air780e :

/dev/ttyUSB2 115200
connect "/usr/sbin/chat -v -f /etc/chatscripts/air780e"
noipdefault
usepeerdns
defaultroute
persist
noauth


Créer /etc/chatscripts/air780e :

ABORT "BUSY"
ABORT "NO CARRIER"
ABORT "ERROR"
"" AT
OK ATE0
OK AT+CGDCONT=1,"IP","your.apn.here"
OK ATD*99#
CONNECT ""


Remplace your.apn.here par l’APN de ton opérateur (ex: gprs.swisscom.ch, internet, etc.)

Démarrer la connexion :

sudo pon air780e


Vérifier :

ifconfig ppp0
ping -c 4 8.8.8.8


Couper la connexion :

sudo poff air780e

🪫 Alimentation solaire (UPS DFRobot FIT0992)

En cours d’intégration :
lecture de la tension batterie et état de charge via I²C (0x36).

🔁 Automatisation (exécution au démarrage)

Ajouter dans /etc/rc.local avant exit 0 :

(sleep 15 && bash -c 'cd /home/kilia/ruches-connectees && source venv/bin/activate && python 4gmerged.py >> /var/log/ruches.log 2>&1') &

🧪 Dépannage rapide
Problème	Diagnostic
Cannot determine SOC peripheral base address	Utiliser rpi-lgpio au lieu de RPi.GPIO
❌ Aucun capteur DS18B20 trouvé	Vérifier GPIO 4 + résistance 4.7kΩ
❌ Erreur envoi InfluxDB	Connexion 4G ou Wi-Fi non active
WARNING:root:setting gain ...	Normal, ignorable (hx711 calibration)
🧰 Environnement logiciel validé
rpi-lgpio==0.6
lgpio==0.2.2.0
hx711==1.1.2.3
requests==2.28.1
smbus2==0.4.2

📊 InfluxDB Cloud (v2)

URL : https://us-east-1-1.aws.cloud2.influxdata.com

Org : CCA Entremont

Bucket : Ruches_Test

🧑‍💻 Auteur

Projet CCA Entremont – Développement par Kilian Léger +41 79 583 77 63
Gestion des ruches connectées, monitoring poids/température via 4G + solaire.
