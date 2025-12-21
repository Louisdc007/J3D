import json
import os

class SaveManager:
    def __init__(self, filename="save.json"):
        self.filename = filename

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