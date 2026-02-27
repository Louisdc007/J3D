#!/bin/bash

# 🎮 Script de Lancement Multijoueur J3D
# Ce script lance facilement le mode multijoueur

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          J3D MULTIJOUEUR - Installation Rapide            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Vérifier que Python3 est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 n'est pas installé"
    exit 1
fi

echo "✓ Python3 trouvé"
echo ""

# Chemins
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$PROJECT_DIR/sourceCode/src"
MULTI_DIR="$SRC_DIR/systeme_multijoueur"

echo "🎯 Localisation du projet: $PROJECT_DIR"
echo ""

# Vérifier les fichiers essentiels
echo "🔍 Vérification des fichiers..."

FILES=(
    "$SRC_DIR/game.py"
    "$MULTI_DIR/game_server.py"
    "$MULTI_DIR/network.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $(basename $file)"
    else
        echo "  ❌ Manquant: $file"
        exit 1
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Options de Lancement                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "1) 🎮 Lancer le jeu muliplayer"
echo "2) 🧪 Lancer les tests du système"
echo "3) 📖 Afficher la documentation"
echo "0) ❌ Quitter"
echo ""

read -p "Choisissez une option (0-3): " choice

case $choice in
    1)
        echo ""
        echo "🎮 Lancement du jeu multijoueur..."
        echo ""
        cd "$SRC_DIR"
        python3 main.py
        ;;
    
    2)
        echo ""
        echo "🧪 Lancement des tests..."
        echo ""
        cd "$PROJECT_DIR"
        python3 test_multiplayer_flow.py
        ;;
    
    3)
        echo ""
        echo "📖 Documentation du système multijoueur:"
        echo ""
        if [ -f "$PROJECT_DIR/MULTIPLAYER_SUMMARY.md" ]; then
            cat "$PROJECT_DIR/MULTIPLAYER_SUMMARY.md" | head -100
            echo ""
            echo "... (voir MULTIPLAYER_SUMMARY.md pour la documentation complète)"
        else
            echo "Documentation non trouvée"
        fi
        ;;
    
    0)
        echo "Au revoir! 👋"
        ;;
    
    *)
        echo "Option invalide"
        exit 1
        ;;
esac

echo ""
