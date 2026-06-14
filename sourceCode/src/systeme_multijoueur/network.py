import socket
import pickle
import struct
import time
import ipaddress

class Network:
    _cached_broadcasts = None
    @classmethod
    def get_local_ips(cls):
        ips = []
        # Simple method: connection attempt
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except:
            pass

        # Robust method: listing all interfaces
        try:
            host_name = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(host_name)
            for ip in ip_list:
                if ip not in ips and not ip.startswith("127."):
                    ips.append(ip)
        except:
            pass

        # Fallback for systems where hostname resolution fails
        if not ips:
            try:
                # This is a bit specific but works on some Unix/Mac
                ips.append(socket.gethostbyname(socket.gethostname()))
            except:
                pass

        if not ips:
            ips.append("127.0.0.1")
        return list(set(ips))

    @classmethod
    def get_primary_ip(cls):
        """Returns the IP address likely used for the local network."""
        ips = cls.get_local_ips()
        # Prefer non-loopback IPs
        real_ips = [ip for ip in ips if not ip.startswith("127.")]
        if real_ips:
            # If multiple, prefer 192. or 10. patterns (common home wifi)
            for ip in real_ips:
                if ip.startswith("192.168.") or ip.startswith("10."):
                    return ip
            return real_ips[0]
        return "127.0.0.1"

    @classmethod
    def get_broadcasts(cls):
        # Kept as utility for other potential uses, but simplified
        return ['<broadcast>', '255.255.255.255']


    def __init__(self, server="127.0.0.1", port=55555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.client.settimeout(10.0) # Augmenté de 2s à 10s pour le WiFi
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
        except Exception as e:
            print(f"[DEBUG-CLIENT] Erreur TCP connect a {self.addr}: {e}")
            return None

    def send(self, data):
        try:
            raw = pickle.dumps(data)
            header = struct.pack('>I', len(raw))
            self.client.sendall(header + raw)
            return self.receive_data()
        except:
            return None