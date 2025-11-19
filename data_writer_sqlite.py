import sqlite3
import time
import random
from datetime import datetime, timezone

# --- CONFIGURAÇÕES DO ESCRITOR ---
DB_NAME = 'sensores.db'
WRITE_INTERVAL = 1  # Frequência com que o simulador envia/escreve dados (1 segundo)

# Informações fixas sobre os sensores
DEFAULT_SENSORS_INFO = {
    "M040": {"type": "motion", "min_val": 0, "max_val": 1, "format": "{:.0f}"}, 
    "T010": {"type": "temperature", "min_val": 18, "max_val": 35, "format": "{:.1f}"},
    "H020": {"type": "humidity", "min_val": 30, "max_val": 90, "format": "{:.0f}"},
    "L030": {"type": "light", "min_val": 0, "max_val": 1000, "format": "{:.0f}"}
}

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def setup_database(conn):
    """Garante que a tabela de dados dos sensores exista."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensorId TEXT NOT NULL,
            type TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    print("Banco de dados SQLite configurado. Tabela 'sensor_data' pronta.")

def generate_random_value(sensor_id):
    """Gera um valor aleatório dentro de uma faixa específica."""
    config = DEFAULT_SENSORS_INFO.get(sensor_id)
    if not config:
        return random.uniform(0, 100)

    min_val, max_val = config["min_val"], config["max_val"]
    
    if sensor_id == "M040":
        return random.choice([0, 1])
    
    if config["format"] == "{:.0f}":
        return round(random.uniform(min_val, max_val), 0)
    else:
        return round(random.uniform(min_val, max_val), 1)

def write_reading_to_db(conn, reading):
    """Insere uma única leitura na tabela sensor_data."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_data (sensorId, type, value, timestamp)
        VALUES (?, ?, ?, ?)
    """, (reading["sensorId"], reading["type"], reading["value"], reading["timestamp"]))
    conn.commit()

def simulate_data_flow():
    """Simula o simulador lendo dados e escrevendo no DB."""
    conn = get_db_connection()
    setup_database(conn)
    
    print(f"\n--- INICIANDO ESCRITA DE DADOS NO {DB_NAME} ---")
    print(f"Intervalo de escrita: {WRITE_INTERVAL} segundo(s).")
    
    while True:
        # 1. Simula a escolha de uma leitura (como se fosse recebida da API)
        random_sensor_id = random.choice(list(DEFAULT_SENSORS_INFO.keys()))
        sensor_type = DEFAULT_SENSORS_INFO[random_sensor_id]["type"]

        reading = {
            "sensorId": random_sensor_id,
            "type": sensor_type,
            "value": generate_random_value(random_sensor_id),
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

        # 2. Escreve a leitura no banco de dados
        try:
            write_reading_to_db(conn, reading)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Escrito: {reading['sensorId']} = {reading['value']}")
        except Exception as e:
            print(f"Erro ao escrever no DB: {e}")
            # Tenta reconectar em caso de erro
            conn = get_db_connection()
            setup_database(conn) 

        # 3. Pausa para simular o intervalo de escrita
        time.sleep(WRITE_INTERVAL)

if __name__ == "__main__":
    try:
        simulate_data_flow()
    except KeyboardInterrupt:
        print("\nEscrita de dados interrompida pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro no simulador de escrita: {e}")