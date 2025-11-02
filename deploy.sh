#!/bin/bash
# ============================================================
# 🚀 Script de déploiement automatique - Ruches CCA Entremont
# ------------------------------------------------------------
# Ce script installe et configure entièrement une ruche :
# - Clone le dépôt GitHub
# - Installe Python + venv + dépendances
# - Configure systemd pour démarrage automatique
# ============================================================

set -e  # stoppe si une erreur survient

echo "🐝 Installation du projet Ruches Connectées CCA..."

# 1️⃣ Nettoyage préalable
sudo systemctl stop ruches.service 2>/dev/null || true
rm -rf ~/ruches-connectees

# 2️⃣ Clonage du dépôt
echo "📦 Clonage du dépôt GitHub..."
cd ~
git clone https://github.com/KilGrid/Ruches-CCA.git ruches-connectees
cd ruches-connectees

# 3️⃣ Création de l'environnement virtuel
echo "🐍 Création du venv Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages

# 4️⃣ Installation des dépendances
echo "📦 Installation des dépendances..."
pip install -r requirements.txt --break-system-packages
pip uninstall -y RPi.GPIO --break-system-packages
pip install --force-reinstall rpi-lgpio lgpio --break-system-packages

# 5️⃣ Vérification rapide
echo "🔎 Vérification des librairies installées..."
pip list | grep -E "hx711|lgpio|rpi-lgpio|requests|smbus2"

# 6️⃣ Création du service systemd
echo "⚙️ Configuration du service systemd..."
sudo tee /etc/systemd/system/ruches.service > /dev/null << 'EOF'
[Unit]
Description=Ruche Connectée CCA - Mesure & Envoi InfluxDB
After=network-online.target

[Service]
ExecStart=/bin/bash -c 'cd /home/kilia/ruches-connectees && source venv/bin/activate && python 4gmerged.py'
WorkingDirectory=/home/kilia/ruches-connectees
StandardOutput=append:/var/log/ruches.log
StandardError=append:/var/log/ruches.log
Restart=always
User=kilia

[Install]
WantedBy=multi-user.target
EOF

# 7️⃣ Activation du service
sudo systemctl daemon-reload
sudo systemctl enable ruches.service
sudo systemctl start ruches.service

echo "✅ Déploiement terminé avec succès !"
echo "🔍 Consulte les logs avec : tail -f /var/log/ruches.log"
