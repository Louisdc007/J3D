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
        print(f"[DEBUG-CLIENT] Ecoute des annonces de serveur. PIN cherche: {pin}")
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if hasattr(socket, 'SO_REUSEPORT'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('', 55666))
            listener.settimeout(1.0)

            print("[DEBUG-CLIENT] En attente des broadcasts du serveur pendant 10s...")
            start_time = time.time()
            
            while time.time() - start_time < 10.0:
                try:
                    data, addr = listener.recvfrom(1024)
                    resp = data.decode().strip()
                    
                    if resp.startswith("J3D_ANNOUNCE:"):
                        parts = resp.split(':')
                        if len(parts) >= 3:
                            announce_pin = parts[1].strip()
                            port = int(parts[2])
                            if announce_pin == str(pin).strip() or pin is None:
                                host = addr[0]
                                listener.close()
                                print(f"[DEBUG-CLIENT] Serveur valide annonce a {host}:{port}")
                                return (host, port)
                except socket.timeout:
                    print(f"[DEBUG-CLIENT] Toujours en ecoute... ({(time.time()-start_time):.1f}s écoulées)")
                except Exception as e:
                    print(f"[DEBUG-CLIENT] Erreur pendant l'ecoute : {e}")
            
            print("[DEBUG-CLIENT] Aucun serveur annonce trouve apres toutes les tentatives.")
            listener.close()
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