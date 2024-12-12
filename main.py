import requests
import logging
import sqlite4
from datetime import datetime
from time import sleep

# Configuração do controlador
CONTROLLER_URL = "https://seu-controlador:8443"
USERNAME = "seu_usuario"
PASSWORD = "sua_senha"
VERIFY_SSL = False  # Defina como True se o SSL for válido
DB_PATH = "unifi_logs.db"

# Configuração de logging
logging.basicConfig(
    filename="unifi_reboot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_database():
    """Configura o banco de dados SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        site TEXT,
        device_name TEXT,
        mac_address TEXT,
        status TEXT,
        uptime INTEGER
    )''')
    conn.commit()
    conn.close()

def save_log(site, device_name, mac_address, status, uptime):
    """Salva log no banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (timestamp, site, device_name, mac_address, status, uptime) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now(), site, device_name, mac_address, status, uptime)
    )
    conn.commit()
    conn.close()

def login():
    """Autentica no UniFi Controller."""
    session = requests.Session()
    session.verify = VERIFY_SSL
    response = session.post(
        f"{CONTROLLER_URL}/api/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return session

def get_sites(session):
    """Obtém a lista de locais gerenciados."""
    response = session.get(f"{CONTROLLER_URL}/api/self/sites")
    response.raise_for_status()
    return response.json()["data"]

def reboot_devices(session, site_id, site_name):
    """Reinicia dispositivos do local e registra no banco de dados."""
    response = session.get(f"{CONTROLLER_URL}/api/s/{site_id}/stat/device")
    response.raise_for_status()
    devices = response.json()["data"]
    
    for device in devices:
        device_name = device.get("name", "Desconhecido")
        mac = device["mac"]
        uptime = device.get("uptime", 0)
        
        # Adiciona lógica para reiniciar apenas se uptime > 7 dias
        if uptime > 604800:  # 7 dias em segundos
            reboot_response = session.post(
                f"{CONTROLLER_URL}/api/s/{site_id}/cmd/devmgr",
                json={"cmd": "restart", "mac": mac}
            )
            if reboot_response.status_code == 200:
                status = "Sucesso"
                logging.info(f"Reiniciado: {device_name} (MAC: {mac}) no site {site_name}.")
            else:
                status = "Falha"
                logging.warning(f"Erro ao reiniciar: {device_name} (MAC: {mac}) no site {site_name}.")
        else:
            status = "Ignorado (uptime < 7 dias)"
            logging.info(f"Dispositivo ignorado: {device_name} (MAC: {mac}). Uptime atual: {uptime}s.")
        
        save_log(site_name, device_name, mac, status, uptime)
        sleep(1)

def main():
    """Executa o fluxo principal."""
    setup_database()
    session = login()
    sites = get_sites(session)
    for site in sites:
        site_id = site["name"]
        site_name = site["desc"]
        logging.info(f"Processando local: {site_name} (ID: {site_id})")
        reboot_devices(session, site_id, site_name)

if __name__ == "__main__":
    main()
