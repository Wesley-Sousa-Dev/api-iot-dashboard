import sqlite3
import json
from flask import Flask, request, jsonify
from datetime import datetime

# --- CONFIGURAÇÕES ---
DB_NAME = 'sensores.db'
API_PORT = 8080

app = Flask(__name__)

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def init_db():
    """Inicializa o banco de dados e a tabela se não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Cria a tabela e mantem 'type' para facilitar no dashboard
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensorId TEXT NOT NULL,
            type TEXT,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"--- Banco de dados '{DB_NAME}' inicializado/verificado com sucesso ---")

@app.route('/api/sensor/data', methods=['POST'])
def receive_sensor_data():
    """
    Endpoint que recebe os dados do simulador Java.
    Espera um JSON no formato:
    {
        "sensorId": "T010",
        "type": "temperature",
        "value": 23.5,
        "timestamp": "2025-01-18T14:32:55Z"
    }
    """
    try:
        data = request.json
        
        # Validação básica
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        sensor_id = data.get('sensorId')
        sensor_type = data.get('type')
        value = data.get('value')
        timestamp = data.get('timestamp')

        # Conecta e salva no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sensor_data (sensorId, type, value, timestamp)
            VALUES (?, ?, ?, ?)
        """, (sensor_id, sensor_type, value, timestamp))
        
        conn.commit()
        conn.close()
        
        # Log no terminal dos dados recebidos
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Recebido: {sensor_id} ({sensor_type}) = {value}")
        
        return jsonify({"status": "success", "message": "Data saved"}), 201

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    """Rota raiz apenas para verificar se a API está online."""
    return "API IoT Online. Aguardando dados em /api/sensor/data", 200

if __name__ == '__main__':
    # Inicializa o banco antes de subir o servidor
    init_db()
    
    print(f"🚀 Servidor API rodando na porta {API_PORT}...")
    print(f"📡 Endpoint esperado: http://localhost:{API_PORT}/api/sensor/data")
    
    # Roda o servidor Flask
    app.run(host='0.0.0.0', port=API_PORT, debug=False)