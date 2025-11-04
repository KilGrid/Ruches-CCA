#!/bin/bash
# ==========================================================
# 🐝 Installation Auto - Ruche Connectée CCA Entremont
# ==========================================================
set -e

REPO_DIR="$HOME/ruches-connectees"
SERVICE_NAME="ruches.service"

echo "🐝 Installation du projet Ruches Connectées"

# 1️⃣ Clone ou mise à jour du dépôt
if [ ! -d "$REPO_DIR" ]; then
    echo "📦 Clonage du dépôt..."
    git clone https://github.com/KilGrid/Ruches-CCA.git "$REPO_DIR"
else
    echo "🔄 Dépôt existant, mise à jour..."
    cd "$REPO_DIR"
    git pull
fi

cd "$REPO_DIR"

# 2️⃣ Création environnement Python
if [ ! -d "venv" ]; then
    echo "🐍 Création du venv..."
    python3 -m venv venv
fi

echo "📦 Installation dépendances..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel --break-system-packages
pip install -r requirements.txt --break-system-packages

# 3️⃣ Installation service systemd
echo "⚙️ Configuration du service systemd..."
sudo tee /etc/systemd/system/$SERVICE_NAME > /dev/null <<EOF
[Unit]
Description=Ruche Connectée CCA - Mesure & Envoi InfluxDB
After=network-online.target

[Service]
User=$USER
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/python 4gmerged.py
StandardOutput=append:/var/log/ruches.log
StandardError=append:/var/log/ruches.log
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "✅ Installation terminée !"
echo "📜 Logs :  tail -f /var/log/ruches.log"
echo "📡 Status : sudo systemctl status $SERVICE_NAME"
