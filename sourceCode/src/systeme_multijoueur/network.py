import socket
import pickle
import struct
import time
import ipaddress

class Network:
    @classmethod
    def get_local_ips(cls):
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
            s.close()
        except:
            pass
        try:
            host_name = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(host_name)
            for ip in ip_list:
                if ip not in ips and not ip.startswith("127."):
                    ips.append(ip)
        except:
            pass
        if not ips:
            ips.append("127.0.0.1")
        return ips

    @classmethod
    def get_broadcasts(cls):
        bcasts = ['<broadcast>', '255.255.255.255']
        for ip in cls.get_local_ips():
            if ip != "127.0.0.1":
                parts = ip.split('.')
                if len(parts) == 4:
                    bcasts.append(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
        return list(set(bcasts))

    @classmethod
    def discover(cls, pin=None):
        print(f"[DEBUG-CLIENT] Demarrage de la decouverte. PIN cherche: {pin}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.5)
            
            msg = f"J3D_DISCOVER:{pin}" if pin else "J3D_DISCOVER"
            encoded = msg.encode()
            targets = cls.get_broadcasts()
            
            print(f"[DEBUG-CLIENT] IPs cibles pour le broadcast: {targets}")

            for attempt in range(5):
                print(f"[DEBUG-CLIENT] Tentative {attempt + 1}/5")
                for target in targets:
                    try:
                        # Changement du port de découverte ici
                        sock.sendto(encoded, (target, 55666))
                        print(f"[DEBUG-CLIENT] Paquet envoye a {target}:55666")
                    except Exception as e:
                        print(f"[DEBUG-CLIENT] Echec de l'envoi a {target} : {e}")
                
                start = time.time()
                while time.time() - start < 0.5:
                    try:
                        data, addr = sock.recvfrom(1024)
                        resp = data.decode().strip()
                        print(f"[DEBUG-CLIENT] Message recu de {addr} : {resp}")
                        
                        if resp.startswith("J3D_SERVER:"):
                            parts = resp.split(':')
                            if len(parts) >= 3:
                                host = addr[0]
                                port = int(parts[2])
                                sock.close()
                                print(f"[DEBUG-CLIENT] Serveur valide trouve a {host}:{port}")
                                return (host, port)
                    except socket.timeout:
                        pass
                    except Exception as e:
                        print(f"[DEBUG-CLIENT] Erreur pendant l'ecoute : {e}")
            
            print("[DEBUG-CLIENT] Aucun serveur trouve apres toutes les tentatives.")
            sock.close()
            return None
        except Exception as e:
            print(f"[DEBUG-CLIENT] Erreur critique dans discover : {e}")
            return None

    def __init__(self, server="127.0.0.1", port=55555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(2)
        self.server = server
        self.port = port
        self.addr = (self.server, self.port)
        self.p = self.connect()

    def _recv_exact(self, n):
        """Read exactly n bytes from the socket."""
        data = b""
        while len(data) < n:
            try:
                packet = self.client.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                return None
            except:
                return None
        return data

    def receive_data(self):
        """Receive a length-prefixed pickled message."""
        try:
            raw_len = self._recv_exact(4)
            if raw_len is None:
                return None
            msg_len = struct.unpack('>I', raw_len)[0]
            if msg_len > 10_000_000:  # Safety: reject messages > 10MB
                return None
            data = self._recv_exact(msg_len)
            if data is None:
                return None
            return pickle.loads(data)
        except:
            return None

    def connect(self):
        try:
            self.client.connect(self.addr)
            return self.receive_data()
        except:
            return None

    def send(self, data):
        try:
            raw = pickle.dumps(data)
            header = struct.pack('>I', len(raw))
            self.client.sendall(header + raw)
            return self.receive_data()
        except:
            return None