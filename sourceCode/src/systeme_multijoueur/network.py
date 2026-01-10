import socket
import pickle

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(10) #10 sec d'attente pour se connecter
        self.server = "127.0.0.1"  #adresse locale
        self.port = 55555
        self.addr = (self.server, self.port)
        self.p = self.connect()

    def connect(self):
        try:
            print(f"Tentative de connexion à {self.server}:{self.port}...")
            self.client.connect(self.addr)
            # recoit l'ID et les obstacles
            data = self.client.recv(32768)
            return pickle.loads(data)
        except socket.timeout:
            print("Erreur : Le serveur n'a pas répondu (Timeout).")
            return None
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            return None

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            #on recoit la position de tous les joueurs
            reply = self.client.recv(32768)
            return pickle.loads(reply)
        except Exception as e:
            print(f"Erreur de communication : {e}")
            return None
