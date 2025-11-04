#!/bin/bash
# ==========================================================
# 🐝 Installation propre - Ruches CCA Entremont (Version 2)
# ----------------------------------------------------------
# - Installe dépendances système et Python
# - Crée venv + installe requirements
# - Configure service systemd (PAS de rc.local, PAS de cron)
# ==========================================================

set -e  # Stop script si erreur

echo "==========================================================="
echo "🐝 Installation du projet Ruches Connectées (version PROPRE)"
echo "==========================================================="

# --- 1️⃣ Mise à jour système
echo "🔧 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# --- 2️⃣ Installation dépendances système
echo "📦 Installation des paquets requis..."
sudo apt install -y git python3-venv python3-pip network-manager modemmanager \
                    usb-modeswitch ppp screen python3-smbus i2c-tools

# --- 3️⃣ Activation interfaces GPIO (I2C + 1-Wire)
echo "⚙️ Activation I2C / 1-Wire..."
sudo raspi-config nonint do_onewire 0
sudo raspi-config nonint do_i2c 0

# --- 4️⃣ Création venv Python
cd ~/ruches-connectees
if [ ! -d "venv" ]; then
    echo "🐍 Création environnement virtuel Python..."
    python3 -m venv venv
fi

echo "✅ Activation venv + installation dépendances..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages
pip install -r requirements.txt --break-system-packages
pip uninstall -y RPi.GPIO 2>/dev/null || true
pip install --force-reinstall rpi-lgpio lgpio --break-system-packages

# --- 5️⃣ Installation du service systemd
echo "⚙️ Installation du service systemd..."

sudo tee /etc/systemd/system/ruches.service > /dev/null << 'EOF'
[Unit]
Description=Ruche Connectée CCA - Mesure & Envoi InfluxDB
After=network-online.target

[Service]
User=kilia
WorkingDirectory=/home/kilia/ruches-connectees
ExecStart=/home/kilia/ruches-connectees/venv/bin/python 4gmerged.py
StandardOutput=append:/var/log/ruches.log
StandardError=append:/var/log/ruches.log
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ruches.service
sudo systemctl restart ruches.service

echo "✅ Installation terminée avec succès 🎉"
echo "-----------------------------------------------------------"
echo "📡 Service actif : sudo systemctl status ruches.service --no-pager"
echo "📜 Logs live     : tail -f /var/log/ruches.log"
echo "🚀 Pour exécuter manuellement :"
echo "cd ~/ruches-connectees && venv/bin/python 4gmerged.py"
echo "==========================================================="
