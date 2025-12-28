# --- SÉLECTEUR DE MODE ---
ONLINE_MODE = True 
# -------------------------

if __name__ == "__main__":
    if ONLINE_MODE:
        from systeme_multijoueur.client_main import run_multiplayer
        run_multiplayer()
    else:
        # Import du code original de ton ami
        import os, sys
        sys.path.append(os.path.join(os.path.dirname(__file__), 'sourceCode', 'src'))
        # On suppose que son fichier s'appelle main.py et a une fonction principale
        import main 
        main.main() # ou le code direct s'il n'a pas de fonctioN
