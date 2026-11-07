# Greed

<a href="https://anatis-studio.github.io/greed-game/" target="_blank">Site web</a>

**Greed** est un jeu de rôle (RPG), de simulation et de bac-à-sable développé en Python avec Pygame. Il s'agit d'un projet de fin d'année pour notre première année à **Epita**.

Le jeu se déroule dans un monde de *dark fantasy* médiéval, en 2D isométrique (style "Pokémon Gameboy"), après qu'une catastrophe ait ravagé le monde.

## 📖 Concept

Vous incarnez un survivant qui doit explorer ce nouveau monde. Pour survivre, vous devrez :

* Braver des **donjons** pour récupérer de précieuses ressources.

* **Construire et gérer un village** qui servira de refuge.

* **Recruter des PNJ** pour occuper différents postes (forgeron, fermier, garde...).

* **Fabriquer et améliorer** vos armes et compétences pour faire face aux dangers.

## 🚀 Fonctionnalités Clés

* **Système de Donjons** : Aventurez-vous dans des zones instanciées pour des défis et du butin.

* **Artisanat & Progression** : Améliorez votre équipement et débloquez de nouvelles compétences.

* **Gestion de Village** : Bâtissez des structures et assignez des rôles à vos PNJ.

* **Cycle Jour/Nuit** : le village vit au rythme du soleil, les donjons s'ouvrent à la nuit tombée.

* **Boss & Artefacts** : quatre Gardiens à vaincre pour libérer le royaume.

## 📸 Galerie

<img width="756" height="485" alt="Screenshot 2026-02-04 at 10-50-11 Rapport de Soutenance 1 - Cahier technique pdf" src="https://github.com/user-attachments/assets/0fa809e4-0452-4f98-8cc8-727e36a11aea" />

<img width="757" height="491" alt="Screenshot 2026-02-04 at 10-51-39 Rapport de Soutenance 1 - Cahier technique pdf" src="https://github.com/user-attachments/assets/a954b7ae-f53b-4d0d-8d64-769c376c04a3" />

## ✨ Édition Abysses (v1.0) — Nouveautés

### Combat repensé
* **Combo à 3 coups** (clic gauche) : le 3ᵉ coup est un coup final plus large et plus puissant ; un clic pendant un coup enchaîne le suivant.
* **Coups critiques**, nombres de dégâts flottants, **hit-stop**, tremblements d'écran, gerbes de sang et d'étincelles, arcs d'épée visibles.
* **Tourbillon** (clic droit / Maj) : attaque circulaire avec recharge.
* **Esquive** (Espace) : invulnérable pendant la ruée, laisse une traînée spectrale et peut annuler la fin d'un coup.
* **Potions** (R / F) : achetées au Marché (5 max), elles soignent 45 % des PV.

### Monstres plus intelligents
* Les monstres **arment leurs attaques** (ils rougeoient avant de frapper) : on peut les esquiver ou les interrompre.
* Les **Mouches** gardent leurs distances et crachent de l'acide.
* **Élites** dorés (plus résistants, plus de butin) et **coffres** (touche E)… dont certains sont des **mimiques** !

### Contenu des donjons
* **Tonneaux et jarres** destructibles (or, fer, soins), **pièges à pointes** qui blessent aussi les monstres.
* **Autels** de bénédiction temporaire : Rage (+50 % dégâts), Célérité, Vitalité (régénération), Fortune (butin x2).
* Les **squelettes** parent les coups de face (le 3ᵉ coup du combo brise leur garde), les **gobelins** chargent,
  les **champignons** libèrent un nuage toxique en mourant, l'acide des mouches **empoisonne**.
* **Séries de victimes** (Triplé, Massacre, Carnage...) qui rapportent de l'XP bonus.

### Boss
* Chaque **donjon majeur** se termine dans une arène face à un **Gardien de l'Artefact** : charges, ondes de choc, salves de projectiles, invocations, phase **enragée** à 50 % de vie.
* Le 4ᵉ artefact est gardé par **le Seigneur de la Cupidité** et sa **pluie d'or**, avec une troisième phase.
* Écran de **victoire** avec statistiques et crédits.

### Village
* **Tableau des primes** : 3 contrats à la fois (éliminer des monstres, ouvrir des coffres, abattre des élites,
  rapporter du fer, vaincre un Gardien...) avec des primes à réclamer.
* **Forge** : en plus des dégâts, améliorez votre **armure** (-8 % de dégâts subis par niveau) et l'**affûtage** (+5 % de critique).
* Nouvelles illustrations pour l'auberge, les arbres et les fleurs, et un **fantôme de placement** qui montre le vrai bâtiment
  (vert si on peut construire, rouge avec la raison sinon).
* Les **villageois parlent** : cliquez sur eux pour des conseils et des bribes d'histoire.

### Progression
* **Bénédictions** : à chaque niveau, choisissez 1 bonus parmi 3 (12 bénédictions de 4 raretés : vol de vie, épines, seconde chance…).
* **Extraction** : rentrez quand vous voulez en appuyant sur E sur le portail ; à l'aube, ceux qui ne l'ont pas rejoint perdent leur butin.
* Statistiques de partie (monstres, coffres, gardiens, morts…).

### Atmosphère
* **Éclairage dynamique** : torche du joueur, flambeaux muraux, portail, projectiles lumineux ; l'aube éclaircit le donjon.
* **Minimap** avec brouillard de guerre (Tab / M pour la grande carte) et boussole vers le portail.
* Village avec **cycle jour/nuit**, feu de camp animé, lucioles, villageois redessinés.
* **Sons synthétisés procéduralement** (aucun fichier requis) : coups, butin, boss, ambiance de donjon et musique de boss.
* Menus refaits, HUD complet, écran de mort avec bilan.

### Technique
* Les collisions passent par un **index spatial** et seuls les murs utiles sont créés : 60 FPS stables là où le jeu tournait à ~35 FPS.
* Le multijoueur garde le même protocole ; le serveur envoie environ 5 fois moins de murs.

## 🎮 Commandes

| Action | Touche |
| --- | --- |
| Se déplacer | ZQSD / WASD / Flèches |
| Attaquer (combo) | Clic gauche |
| Tourbillon | Clic droit / Maj |
| Esquive | Espace |
| Potion | R / F |
| Coffre, autel, rentrer par le portail | E |
| Carte du donjon | Tab / M |
| Pause | Échap |

## 🛠️ Installation et Lancement

1. **Clonez le dépôt :**

   ```
   git clone https://github.com/Louisdc007/J3D.git
   cd J3D
   ```

2. **Créez un environnement virtuel (recommandé) :**

   ```
   python -m venv venv
   source venv/bin/activate  # Sur Windows: .\venv\Scripts\activate
   ```

3. **Installez les dépendances :**

   ```
   pip install -r sourceCode/requirements.txt
   ```

   > Le jeu utilise **pygame-ce** (fork maintenu de pygame, même API), qui fournit des
   > versions précompilées pour les Python récents. Si `pygame` classique est déjà installé,
   > désinstallez-le d'abord (`pip uninstall pygame`) : les deux paquets entrent en conflit.

4. **Lancez le jeu :**

   ```
   cd sourceCode/src
   python main.py
   ```

## 🧪 Tests

```
python sourceCode/tests/test_game.py
```

Les tests tournent sans fenêtre : collisions avec les murs, mécaniques (contrats, autels, parade, pièges,
poison, armure), sauvegarde, et démarrage de la vraie boucle de jeu.

## 👨‍💻 L'Équipe

* **\[Louis Da Costa\]** - \[Lead Technique\]
* **\[Ghita Abelaoui\]** - \[Network Programmer\]
* **\[Adam Sellam\]** - \[Art & UI/UX\]
* **\[Amine Aaddi\]** - \[Narration et histoire\]

*Projet réalisé dans le cadre de la première année de prépa à Epita (2024-2025).*
