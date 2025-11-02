# 🐝 Ruches Connectées – Projet CCA Entremont

Ce projet vise à déployer des **ruches connectées autonomes** capables de mesurer la **température interne**, le **poids de la ruche**, et le **niveau de charge batterie**, puis d’envoyer ces données en **temps réel vers InfluxDB Cloud via une connexion 4G**.  
L’alimentation est assurée par un **HAT solaire UPS DFRobot FIT0992**.

---

## 🧩 Architecture matérielle

### Matériel principal
- Raspberry Pi 5 (Bookworm, kernel 6.12.25+rpt-rpi-2712)
- Module HX711 (pesée)
- Capteur de température DS18B20 (1-Wire)
- Module 4G Air780E (communication)
- HAT UPS DFRobot FIT0992 (alimentation solaire)

### Schéma de câblage

| Composant     | GPIO Raspberry Pi | Broche physique | Détail |
|----------------|-------------------|------------------|--------|
| HX711 VCC      | 5 V               | Pin 2            | Alimentation |
| HX711 GND      | GND               | Pin 6            | Masse commune |
| HX711 DT       | GPIO 5            | Pin 29           | Données |
| HX711 SCK      | GPIO 6            | Pin 31           | Horloge |
| DS18B20 VCC    | 3.3 V             | Pin 1            | Alimentation capteur |
| DS18B20 GND    | GND               | Pin 9            | Masse |
| DS18B20 DATA   | GPIO 4            | Pin 7            | Bus 1-Wire *(résistance 4.7kΩ entre DATA et 3.3V)* |

---

## 🧠 Fonctionnalités

- Lecture du **poids** via HX711  
- Lecture de la **température** via DS18B20  
- Lecture de la **tension batterie** via FIT0992 (I²C 0x36)  
- Envoi périodique (60 s) vers **InfluxDB Cloud**  
- Gestion automatique de la **connexion 4G**  
- **Redémarrage automatique** après coupure ou plantage via `systemd`  
- Code **configurable** via `config.json`

---

## ⚙️ Installation manuelle (si non automatisée)

### 1️⃣ Cloner le dépôt
```bash
cd ~
git clone https://github.com/KilGrid/Ruches-CCA.git ruches-connectees
cd ruches-connectees
2️⃣ Créer l’environnement virtuel Python
bash
Copier le code
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages
3️⃣ Installer les dépendances
bash
Copier le code
pip install -r requirements.txt --break-system-packages
pip uninstall -y RPi.GPIO --break-system-packages
pip install --force-reinstall rpi-lgpio lgpio --break-system-packages
4️⃣ Activer 1-Wire et I²C
bash
Copier le code
sudo raspi-config
# Interface Options → 1-Wire → Enable
# Interface Options → I2C → Enable
5️⃣ Activer la connexion 4G (Air780E – Sunrise)
L’Air780E se connecte automatiquement via son interface RNDIS (eth1).

Pour activer manuellement :

bash
Copier le code
sudo ip link set eth1 up
sudo dhclient eth1
ip a show eth1
Tu dois voir :

sql
Copier le code
inet 192.168.10.2/24 brd 192.168.10.255 scope global dynamic noprefixroute eth1
➡️ La connexion 4G Sunrise est active 🎉

Teste :

bash
Copier le code
ping -c 4 8.8.8.8
6️⃣ Lancer le script principal
bash
Copier le code
source venv/bin/activate
python 4gmerged.py
Les capteurs DS18B20, HX711 et la batterie FIT0992 enverront leurs données vers InfluxDB Cloud.

🚀 Déploiement automatique (recommandé)
Pour configurer automatiquement une nouvelle ruche (clone, venv, dépendances, service auto-démarrage) :

bash
Copier le code
curl -fsSL https://raw.githubusercontent.com/KilGrid/Ruches-CCA/main/deploy.sh | bash
➡️ En quelques minutes, la ruche est prête à fonctionner.
Les logs sont enregistrés dans :

bash
Copier le code
tail -f /var/log/ruches.log
🔁 Lancement automatique au démarrage
Le service ruches.service démarre ton script à chaque mise sous tension.

Démarrer manuellement :

bash
Copier le code
sudo systemctl start ruches.service
Arrêter :

bash
Copier le code
sudo systemctl stop ruches.service
Vérifier :

bash
Copier le code
sudo systemctl status ruches.service
Voir les logs :

bash
Copier le code
tail -f /var/log/ruches.log
🧪 Dépannage rapide
Problème	Diagnostic
Cannot determine SOC peripheral base address	Utiliser rpi-lgpio au lieu de RPi.GPIO
❌ Aucun capteur DS18B20 trouvé	Vérifier câblage GPIO 4 + résistance 4.7kΩ
❌ Erreur envoi InfluxDB	Vérifier la connexion 4G (eth1)
WARNING:root:setting gain...	Normal, sans impact (HX711 calibration)

🧰 Environnement logiciel validé
bash
Copier le code
rpi-lgpio==0.6
lgpio==0.2.2.0
hx711==1.1.2.3
requests==2.32.5
smbus2==0.5.0
📊 InfluxDB Cloud (v2)
URL : https://us-east-1-1.aws.cloud2.influxdata.com

Organisation : CCA Entremont

Bucket : Ruches_Test

🧑‍💻 Auteur
Projet CCA Entremont
Développement : Kilian Léger
Gestion des ruches connectées – monitoring poids, température et batterie via 4G + solaire.

📞 +41 79 583 77 63
📡 Air780E – Sunrise LTE
🌞 Alimentation : FIT0992 + panneau solaire
