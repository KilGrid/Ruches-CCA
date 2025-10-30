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
