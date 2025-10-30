#!/bin/bash
# ==========================================================
# 🐝 Script d'installation automatique - Ruches CCA Entremont
# ==========================================================

echo "==========================================================="
echo "🐝 Installation du projet Ruches Connectées"
echo "==========================================================="

# --- 1️⃣ Mise à jour du système
echo "🔧 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# --- 2️⃣ Installation des dépendances
echo "📦 Installation des paquets requis..."
sudo apt install -y git python3-venv python3-pip network-manager modemmanager usb-modeswitch ppp screen

# --- 3️⃣ Configuration des interfaces (I²C / 1-Wire)
echo "⚙️ Activation des interfaces GPIO / 1-Wire..."
sudo raspi-config nonint do_onewire 0
sudo raspi-config nonint do_i2c 0

# --- 4️⃣ Environnement Python
if [ ! -d "venv" ]; then
    echo "🐍 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

echo "✅ Activation du venv et installation des dépendances..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages
pip install -r requirements.txt --break-system-packages

# --- 5️⃣ Configuration 4G Sunrise (RNDIS)
echo "📶 Configuration et activation de la 4G..."
bash connect_4g.sh

# --- 6️⃣ Démarrage automatique au boot
if ! grep -q "ruches-connectees" /etc/rc.local; then
    echo "🪄 Configuration du démarrage automatique..."
    echo "(sleep 20 && bash -c 'cd /home/$USER/ruches-connectees && source venv/bin/activate && bash connect_4g.sh && python 4gmerged.py >> /var/log/ruches.log 2>&1') &" | sudo tee -a /etc/rc.local
fi

echo "✅ Installation terminée avec succès."
echo "-----------------------------------------------------------"
echo "📡 La ruche se connectera automatiquement à la 4G et à InfluxDB au démarrage."
echo "🚀 Pour lancer manuellement :"
echo "cd ~/ruches-connectees && source venv/bin/activate && python 4gmerged.py"
