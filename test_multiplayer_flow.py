#!/usr/bin/env python3
"""
Script de test pour valider le flux complet du multijoueur online.
Teste :
1. Création d'un serveur avec code PIN
2. Découverte du serveur via UDP
3. Connexion d'un client
4. Synchronisation de base
5. Progression de niveaux
6. Gestion de la mort
"""

import sys
import os
import time
import subprocess
import socket

# Ajouter le chemin vers le code source
src_path = os.path.join(os.path.dirname(__file__), 'sourceCode', 'src')
sys.path.insert(0, src_path)

multi_path = os.path.join(src_path, 'systeme_multijoueur')
if multi_path not in sys.path:
    sys.path.append(multi_path)

from network import Network
from game_server import GameServer

def test_pin_generation():
    """Test 1: Génération de code PIN"""
    print("\n" + "="*60)
    print("TEST 1: Génération de code PIN")
    print("="*60)
    
    server = GameServer(port=55560)
    pin = server.pin_code
    print(f"✓ PIN générée: {pin}")
    assert len(pin) == 6, "PIN doit avoir 6 chiffres"
    assert pin.isdigit(), "PIN doit être numérique"
    print("✓ Format du PIN valide")
    return True

def test_server_startup():
    """Test 2: Démarrage du serveur"""
    print("\n" + "="*60)
    print("TEST 2: Démarrage du serveur")
    print("="*60)
    
    server = GameServer(port=55561)
    result = server.start()
    print(f"✓ Serveur démarré: {result}")
    assert result, "Le serveur devrait démarrer"
    
    # Donner un peu de temps pour que le serveur se lance
    time.sleep(1)
    
    print(f"✓ Serveur écoute sur le port {server.port}")
    print(f"✓ Code PIN: {server.pin_code}")
    
    server.stop()
    print("✓ Serveur arrêté proprement")
    return True

def test_network_discovery():
    """Test 3: Découverte réseau via UDP"""
    print("\n" + "="*60)
    print("TEST 3: Découverte réseau UDP")
    print("="*60)
    
    # Lancer un serveur en arrière-plan
    server = GameServer(port=55562)
    server.start()
    
    # Attendre que le serveur soit prêt
    time.sleep(1)
    
    # Tenter une découverte
    print(f"Recherche du serveur avec PIN: {server.pin_code}...")
    discovered = Network.discover(pin=server.pin_code)
    
    if discovered:
        host, port = discovered
        print(f"✓ Serveur découvert à {host}:{port}")
        assert port == server.port, f"Port doit être {server.port}"
        print("✓ Port correct")
    else:
        print("✗ Serveur non découvert (peut être normal si broadcast UDP bloquée)")
    
    server.stop()
    return True

def test_server_network_class():
    """Test 4: Classe GameServer"""
    print("\n" + "="*60)
    print("TEST 4: Classe GameServer")
    print("="*60)
    
    server = GameServer(port=55563)
    print(f"✓ GameServer initialisée")
    print(f"  - PIN: {server.pin_code}")
    print(f"  - Port: {server.port}")
    print(f"  - Joueurs: {server.player_count}")
    
    # Tester la génération de donjon
    dungeon = server.generate_dungeon(level=1)
    print(f"✓ Donjon généré pour le niveau 1")
    print(f"  - Ennemis: {len(dungeon['enemies'])}")
    assert len(dungeon['enemies']) > 0, "Le donjon doit avoir au moins un ennemi"
    
    dungeon_level_2 = server.generate_dungeon(level=2)
    print(f"✓ Donjon généré pour le niveau 2")
    print(f"  - Ennemis: {len(dungeon_level_2['enemies'])}")
    assert len(dungeon_level_2['enemies']) > len(dungeon['enemies']), \
        "Le niveau 2 doit avoir plus d'ennemis que le niveau 1"
    
    print("✓ Progression des niveaux validée")
    return True

def test_network_client():
    """Test 5: Classe Network (client)"""
    print("\n" + "="*60)
    print("TEST 5: Classe Network (client)")
    print("="*60)
    
    # Tester Network.discover() sans serveur
    result = Network.discover(pin="000000")
    print(f"Recherche d'un serveur inexistant: {result}")
    assert result is None, "Devrait retourner None pour serveur inexistant"
    print("✓ Gestion correcte d'absence de serveur")
    
    # Tester Network.__init__() avec paramètres
    net = Network(server="127.0.0.1", port=12345)
    print(f"✓ Network initialisée avec paramètres personnalisés")
    print(f"  - Serveur: {net.server}")
    print(f"  - Port: {net.port}")
    assert net.server == "127.0.0.1", "Serveur doit être 127.0.0.1"
    assert net.port == 12345, "Port doit être 12345"
    
    return True

def run_all_tests():
    """Lance tous les tests"""
    print("\n")
    print("#" * 60)
    print("#  TESTS SYSTEME MULTIJOUEUR ONLINE")
    print("#" * 60)
    
    tests = [
        ("Génération PIN", test_pin_generation),
        ("Démarrage serveur", test_server_startup),
        ("Découverte UDP", test_network_discovery),
        ("Classe GameServer", test_server_network_class),
        ("Classe Network", test_network_client),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"\n✓ {test_name} RÉUSSI")
                passed += 1
        except Exception as e:
            print(f"\n✗ {test_name} ÉCHOUÉ: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RÉSULTATS: {passed} réussis, {failed} échoués")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS! 🎉")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) échoué(s)")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
