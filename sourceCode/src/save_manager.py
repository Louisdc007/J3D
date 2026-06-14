import json
import os
import sys

def get_save_dir():
    """Retourne le dossier de sauvegarde dans les données utilisateur du système."""
    app_name = "Greed"
    if sys.platform == "win32":
        # %APPDATA%\Greed\ sur Windows
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        save_dir = os.path.join(base, app_name)
    elif sys.platform == "darwin":
        # ~/Library/Application Support/Greed/ sur macOS
        save_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", app_name)
    else:
        # ~/.local/share/Greed/ sur Linux
        save_dir = os.path.join(os.path.expanduser("~"), ".local", "share", app_name)
    
    os.makedirs(save_dir, exist_ok=True)
    return save_dir

class SaveManager:
    def __init__(self, filename="save.json"):
        save_dir = get_save_dir()
        self.filename = os.path.join(save_dir, filename)
        print(f"[SaveManager] Fichier de sauvegarde : {self.filename}")

    def load_game(self):
        if not os.path.exists(self.filename):
            return None
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            print("Sauvegarde chargée avec succès !")
            return data
        except Exception as e:
            print(f"Erreur chargement: {e}")
            return None

    def save_game(self, game_data):
        try:
            with open(self.filename, 'w') as f:
                json.dump(game_data, f, indent=4)
            print("Partie sauvegardée !")
        except Exception as e:
            print(f"Erreur sauvegarde: {e}")

    def delete_save(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
            print("Fichier de sauvegarde supprimé.")