# 🎮 J3D Multijoueur Online - Mode d'emploi

## ✨ Quoi de Neuf?

Vous pouvez maintenant **jouer à J3D en coopération avec vos amis sur votre réseau WiFi!**

- ✅ **Système simple** : Code PIN 6 chiffres (ex: 421311)
- ✅ **Pas d'IP complexe** : Découverte automatique via USB/WiFi
- ✅ **Donjons progressifs** : Niveaux 1, 2, 3... avec ennemis plus difficiles
- ✅ **Améliorations** : 20 secondes au spawn pour upgrader (HP, DPS, SPD)
- ✅ **Multijoueur vrai** : Synchronisation en temps réel

---

## 🚀 Pour Démarrer le Multijoueur

### Option 1: Script de Lancement (Recommandé)
```bash
cd /Users/louisdacosta/J3D
./launch_multiplayer.sh
```

### Option 2: Lancement Direct
```bash
cd /Users/louisdacosta/J3D/sourceCode/src
python3 main.py
```

---

## 👥 Scénario Typique: Vous + Votre Ami

### **Joueur 1 (Créateur/Serveur)**

1. Lance le jeu → Menu
2. Clique **MULTIJOUEUR**
3. Clique **SERVEUR**
4. ✅ Apparaît: Code PIN: `421311`
5. 📢 **Dit à votre ami: "Rejoins avec ce code: 421311"**
6. Clique **COMMENCER**
7. 🎮 Vous voilà dans le donjon ensemble!

### **Joueur 2 (Client/Rejoignant)**

1. Lance le jeu → Menu
2. Clique **MULTIJOUEUR**
3. Clique **CLIENT**
4. Saisit le PIN: `421311` (chiffres seulement)
5. Clique **RECHERCHER**
6. ✅ "Serveur trouvé!"
7. 🎮 Connecté! Vous jouez ensemble!

---

## 🎮 Pendant le Jeu

### Controls
- **Déplacement**: Z/S/Q/D ou Flèches
- **Attaque**: Espace
- **Pause**: Échap

### Progression
1. **Eliminez tous les ennemis** du donjon
2. **Fenêtre d'amélioration** (20 secondes):
   - Choisissez une amélioration:
     - 🩹 **SANTÉ +50**: Vous soigne
     - ⚔️ **DÉGÂTS +10**: Coup plus fort  
     - 🏃 **VITESSE +5%**: Vous courez plus vite
3. **Vers le niveau suivant!**
   - Niveau 2 = Plus d'ennemis + Plus forts
   - Niveau 3 = Encore plus difficile!
   - ... continuez jusqu'à vos limites!

### Si vous Mourez
- ❌ Vous mourez
- 🚪 Déconnexion automatique
- ↩️ Retour au menu
- 🎮 Recommencez avec vos amis!

---

## 🧪 Tester le Système

Pour vérifier que tout fonctionne:

```bash
cd /Users/louisdacosta/J3D
python3 test_multiplayer_flow.py
```

Vous verrez:
```
✓ PIN générée: 421311
✓ Format du PIN valide
✓ Serveur démarré
✓ Donjon niveau 1: 7 ennemis
✓ Donjon niveau 2: 9 ennemis
✓ Progression des niveaux validée

🎉 TOUS LES TESTS SONT PASSÉS!
```

---

## 📡 Fonctionnement Technique

### Pour les Curieux (Architecture)

1. **Créateur (Serveur)**
   - Lance `GameServer` sur port `55555`
   - Génère un PIN aléatoire `421311`
   - Écoute les clients qui se connectent
   - Maître de l'IA des monstres
   - Envoie l'état du jeu chaque seconde

2. **Rejoignant (Client)**
   - Demande "Où est le serveur du PIN 421311?"
   - Broadcast UDP sur port `55556`
   - Reçoit réponse: "Je suis à 192.168.1.5:55555"
   - Se connecte en TCP
   - Reçoit les monstres et positions

3. **Pendant le Jeu**
   - Serveur = "Maître"
     - Contrôle l'IA des ennemis
     - Détecte qui est mort
     - Génère le nouveau donjon
   - Clients = "Téléspectateurs" + "Acteurs"
     - Envoient leurs inputs
     - Reçoivent positions ennemis
     - Affichent les autres joueurs

---

## 🐛 Dépannage

### Q: "Le serveur n'est pas trouvé"
**R:** 
- Vérifiez que vous êtes sur le MÊME réseau WiFi
- Le port UDP 55556 peut être bloqué par le firewall
- Attendez 5 secondes et réessayez
- Vérifiez que le créateur a cliqué "COMMENCER"

### Q: "La découverte dit Code incorrect"
**R:**
- Vérifiez que vous avez entré exactement les 6 chiffres
- Sans espaces ni caractères spéciaux

### Q: "Les ennemis ne bougent pas"
**R:**
- C'est normal au début du niveau
- Attendez 2 secondes, ils commencent à se rapprocher

### Q: "Mon ami me voit pas bouger"
**R:**
- Vérifiez votre lag (peut prendre 0.5s)
- Si c'est très lent, le réseau est saturé

---

## 📊 Informations de Port

| Port | Protocole | Usage |
|------|-----------|-------|
| 55556 | UDP | 🔍 Découverte serveur (broadcast) |
| 55555+ | TCP | 🎮 Jeu en temps réel |

---

## 📚 Documentation Complète

Pour plus de détails techniques, voir: **MULTIPLAYER_SUMMARY.md**

---

## ✅ Checklist Avant de Jouer

- [ ] Python3 installé (`python3 --version`)
- [ ] Pygame installé (`python3 -c "import pygame"`)
- [ ] Connecté au même réseau WiFi que votre ami
- [ ] Port UDP 55556 (peut être ouvert par le VPN)
- [ ] Tests passent (`python3 test_multiplayer_flow.py`)

---

## 🎉 C'est Prêt!

Invitez vos amis et **jouez ensemble dans les donjons de J3D!** 🎮

```
Step 1: Créateur → SERVEUR → COMMENCER
Step 2: Ami      → CLIENT  → RECHERCHER
Step 3: GG        → Coopérez ensemble!
```

**Bon jeu!** 🚀
