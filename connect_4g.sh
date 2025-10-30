#!/bin/bash
# ==========================================================
# 🚀 Activation automatique de la connexion 4G Air780E (Sunrise)
# ==========================================================
# Ce script configure et active la 4G via l’interface RNDIS (eth1)

echo "🔍 Vérification de l'interface 4G..."
if ip link show eth1 > /dev/null 2>&1; then
    echo "✅ Interface détectée : eth1"
    sudo ip link set eth1 up
    sudo dhclient -r eth1 2>/dev/null
    sudo dhclient eth1
    IP=$(ip -4 addr show eth1 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    echo "🌐 Adresse IP : $IP"
else
    echo "❌ Interface eth1 introuvable. Vérifie que le module Air780E est branché."
    exit 1
fi

# Test Internet
echo "🔎 Test de connectivité..."
if ping -c 2 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ Connexion Internet 4G opérationnelle."
else
    echo "⚠️ Aucune réponse réseau. Vérifie la couverture ou la carte SIM."
fi
