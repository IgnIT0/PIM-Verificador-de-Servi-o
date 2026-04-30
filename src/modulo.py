import urllib.request
import urllib.error
import datetime
import csv
import os
import json
import subprocess
import platform
import ipaddress

class Service:
    def __init__(self, name, target, protocol="HTTP"):
        self.name = name
        # Limpamos espaços extras que podem vir ao colar
        self.target = target.strip() 
        self.protocol = protocol.upper()
        self.is_online = False
        self.latency = 0
        self.last_status = None
        
        # Detecta automaticamente se é IPv4, IPv6 ou Domínio
        self.ip_version = self._detect_ip_version()

    def _detect_ip_version(self):
        """Identifica a versão do IP ou se é um domínio."""
        # Remove temporariamente o protocolo para validar o host puro
        clean_host = self.target.replace("https://", "").replace("http://", "").split('/')[0].split(':')[0]
        try:
            ip = ipaddress.ip_address(clean_host)
            return "IPv4" if isinstance(ip, ipaddress.IPv4Address) else "IPv6"
        except ValueError:
            return "Domínio/URL"

    def check_status(self):
        """Executa a checagem baseada no protocolo escolhido."""
        if self.protocol == "HTTP":
            # Garante que a URL tenha o prefixo para o urllib funcionar
            url = self.target if self.target.startswith("http") else f"https://{self.target}"
            return self._check_http(url)
        elif self.protocol == "ICMP":
            return self._check_icmp()
        return False, 0

    def _check_http(self, url):
        try:
            inicio = datetime.datetime.now()
            req = urllib.request.Request(url, headers={'User-Agent': 'UptimeMonitor/1.0'})
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

    def _check_icmp(self):
        """Executa o comando de Ping no sistema operacional."""
        try:
            inicio = datetime.datetime.now()
            # Limpa o IP/Domínio para o comando ping não falhar com prefixos
            host = self.target.replace("https://", "").replace("http://", "").split('/')[0]
            
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            comando = ['ping', param, '1', host]
            
            startupinfo = None
            if platform.system().lower() == 'windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            processo = subprocess.run(
                comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo
            )
            
            fim = datetime.datetime.now()
            self.is_online = (processo.returncode == 0)
            self.latency = int((fim - inicio).total_seconds() * 1000) if self.is_online else 0
            return self.is_online, self.latency
        except Exception:
            return False, 0

class Notifier:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)

    def notify(self, service_name, status, message=""):
        # Aplicação da data no padrão brasileiro D/M/Y
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
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
                # Adicionada coluna de versão do IP no CSV
                writer.writerow(["data_hora", "servico", "status", "latencia_ms", "versao_ip"])

    def save_result(self, service, status, latency=0):
        # Data formatada para o CSV no padrão D/M/Y
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        status_str = "ONLINE" if status else "OFFLINE"
        
        with open(self.filename, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, service.name, status_str, latency, service.ip_version])

    def save_services_config(self, services):
        data = [{"name": s.name, "target": s.target, "protocol": s.protocol} for s in services]
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_services_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []
