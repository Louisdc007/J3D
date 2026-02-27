import socket
import pickle

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(10)
        self.server = "127.0.0.1"
        self.port = 55555
        self.addr = (self.server, self.port)
        self.p = self.connect()

    def receive_data(self):
        """
        Écoute le réseau et recolle les morceaux du paquet 
        jusqu'à ce que l'objet complet (comme la carte du donjon) soit reconstitué.
        """
        data = b""
        while True:
            try:
                packet = self.client.recv(32768)
                if not packet:
                    return None
                
                # On ajoute le nouveau morceau reçu
                data += packet
                
                try:
                    # On essaie de lire les données. 
                    # Si ça marche, c'est qu'on a tout reçu !
                    return pickle.loads(data)
                except (pickle.UnpicklingError, EOFError):
                    # Si ça plante, c'est qu'il manque encore des morceaux. 
                    # La boucle continue et attend la suite.
                    continue
                    
            except socket.timeout:
                print("Erreur : Temps d'attente réseau dépassé.")
                return None
            except Exception as e:
                print(f"Erreur de réception réseau : {e}")
                return None

    def connect(self):
        try:
            print(f"Tentative de connexion à {self.server}:{self.port}...")
            self.client.connect(self.addr)
            # On utilise notre nouvelle fonction robuste pour recevoir l'immense carte
            return self.receive_data()
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            return None

    def send(self, data):
        try:
            self.client.sendall(pickle.dumps(data))
            # On utilise la même fonction pour recevoir la position des joueurs
            return self.receive_data()
        except Exception as e:
            print(f"Erreur de communication : {e}")
            return None
