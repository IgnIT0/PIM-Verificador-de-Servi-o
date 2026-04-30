import urllib.request
import urllib.error
import datetime
import csv
import os
import json

class Service:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.is_online = False
        self.latency = 0
        self.last_status = None

    def check_status(self):
        try:
            inicio = datetime.datetime.now()
            req = urllib.request.Request(self.url, headers={'User-Agent': 'UptimeMonitor/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                status_code = response.getcode()
                fim = datetime.datetime.now()
                self.latency = int((fim - inicio).total_seconds() * 1000)
                self.is_online = (status_code == 200)
                return self.is_online, self.latency
        except Exception:
            self.is_online = False
            self.latency = 0
            return False, 0

class Notifier:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)

    def notify(self, service_name, status, message=""):
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        tipo = "[INFO]" if status else "[ALERTA]"
        estado = "ONLINE" if status else "OFFLINE"
        msg = f"{tipo} {timestamp} - {service_name} está {estado}. {message}"
        with open("logs/uptime_history.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        return msg

class Storage:
    def __init__(self, filename="data/uptime_data.csv", config_file="data/config.json"):
        self.filename = filename
        self.config_file = config_file
        self._prepare_storage()

    def _prepare_storage(self):
        folder = os.path.dirname(self.filename)
        if folder: os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "service_name", "status", "latency_ms"])

    def save_result(self, service_name, status, latency=0):
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        status_str = "ONLINE" if status else "OFFLINE"
        with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, service_name, status_str, latency])

    # --- AS FUNÇÕES QUE ESTAVAM FALTANDO ---
    def save_services_config(self, services):
        """Salva a lista de objetos Service no arquivo JSON."""
        data = [{"name": s.name, "url": s.url} for s in services]
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_services_config(self):
        """Lê o arquivo JSON e retorna a lista de serviços."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []
