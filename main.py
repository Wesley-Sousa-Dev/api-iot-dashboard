import streamlit as st
import time
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import pytz

# --- CONFIGURAÇÕES STREAMLIT (DEVE SER A PRIMEIRA CHAMADA) ---
st.set_page_config(
    page_title="Dashboard de Sensores",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONFIGURAÇÕES GLOBAIS ---
DB_NAME = 'sensores.db'
POLLING_INTERVAL = 3
HISTORY_LIMIT = 100
MAIN_SENSOR_ID = "T010"
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')

DEFAULT_SENSORS_INFO = {
    "M040": {"type": "motion", "label": "Movimento", "unit": "", "icon": "🚶‍♂️", "min_val": 0, "max_val": 1, "format": "{:.0f}"}, 
    "T010": {"type": "temperature", "label": "Temperatura", "unit": "°C", "icon": "🌡️", "min_val": 18, "max_val": 35, "format": "{:.1f}"},
    "H020": {"type": "humidity", "label": "Umidade", "unit": "%", "icon": "💧", "min_val": 30, "max_val": 90, "format": "{:.0f}"},
    "L030": {"type": "light", "label": "Luminosidade", "unit": "lux", "icon": "💡", "min_val": 0, "max_val": 1000, "format": "{:.0f}"}
}

# Inicializa o estado da sessão
if 'latest_readings' not in st.session_state:
    st.session_state.latest_readings = {sensor_id: {"value": "N/A", "timestamp": "N/A", "type": DEFAULT_SENSORS_INFO[sensor_id]["type"]} 
                                         for sensor_id in DEFAULT_SENSORS_INFO}
if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(columns=['sensorId', 'value', 'timestamp'])


# --- FUNÇÕES DE DADOS E SQLITE ---

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=1) 
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def fetch_data_history_from_db(limit):
    """Busca o histórico e a última leitura de cada sensor."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame(), {}

    latest_readings = {}
    
    query = f"""
    SELECT sensorId, value, timestamp 
    FROM sensor_data 
    ORDER BY timestamp DESC 
    LIMIT {limit * len(DEFAULT_SENSORS_INFO)};
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        
        # Converte timestamp UTC para o TZ de destino (BR)
        df['type'] = df['sensorId'].apply(lambda x: DEFAULT_SENSORS_INFO.get(x, {}).get("type", "unknown"))
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert(TIMEZONE_BR)
        
        # Filtra a última leitura de cada sensor para os cards
        df_latest = df.sort_values(by='timestamp', ascending=False).drop_duplicates(subset=['sensorId'])
        
        for index, row in df_latest.iterrows():
            latest_readings[row["sensorId"]] = {
                "sensorId": row["sensorId"],
                "type": row["type"],
                "value": row["value"],
                "timestamp": row["timestamp"].isoformat() 
            }
        
    except pd.io.sql.DatabaseError:
        df = pd.DataFrame(columns=['sensorId', 'value', 'timestamp', 'type'])
        st.warning(f"Tabela 'sensor_data' não encontrada no banco. Execute o 'data_writer_sqlite.py'.")
    except Exception as e:
        st.error(f"Erro ao ler dados do SQLite: {e}")
        df = pd.DataFrame(columns=['sensorId', 'value', 'timestamp', 'type'])
    finally:
        conn.close()

    return df, latest_readings

def format_timestamp(timestamp_iso):
    """Formata o timestamp para o formato DD/MM/AAAA HH:MM:SS (TZ de destino)."""
    try:
        dt = datetime.fromisoformat(str(timestamp_iso))
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        return "Timestamp Inválido"

def format_value(value, sensor_id):
    """Formata o valor de acordo com a configuração do sensor."""
    config = DEFAULT_SENSORS_INFO.get(sensor_id)
    if not config:
        return str(value)
    
    if sensor_id == "M040":
        return "Detectado" if (value is not None and float(value) >= 0.5) else "Ausente"

    try:
        return config["format"].format(float(value))
    except (ValueError, TypeError):
        return str(value)

# --- FUNÇÃO DE CRIAÇÃO DE GRÁFICOS PLOTLY ---

def create_sensor_chart(df_history, sensor_id):
    """Cria um gráfico Plotly de linha para um sensor específico."""
    config = DEFAULT_SENSORS_INFO.get(sensor_id)
    if df_history.empty or not config:
        return None

    df_sensor = df_history[df_history['sensorId'] == sensor_id].sort_values(by='timestamp', ascending=True)

    if sensor_id == "M040":
        y_title = "Status (0/1)"
        fig = px.line(df_sensor, x='timestamp', y='value',
                      title=f"{config['icon']} {config['label']} ({config['unit']})", markers=True)
        fig.update_yaxes(
            tickmode='array', tickvals=[0, 1], ticktext=['Ausente', 'Detectado'], range=[-0.1, 1.1])
    else:
        y_title = f"Valor ({config['unit']})"
        fig = px.line(df_sensor, x='timestamp', y='value',
                      title=f"{config['icon']} {config['label']} ({config['unit']})")
    
    # Configurações de fuso horário e estilo do Plotly
    fig.update_xaxes(
        tickformat="%H:%M:%S",
        hoverformat="%d/%m/%Y %H:%M:%S (%Z)"
    )

    fig.update_layout(
        plot_bgcolor='#2D3748', 
        paper_bgcolor='#2D3748',
        font=dict(color='#E2E8F0'),
        title_font_color="#4FD1C5",
        xaxis_title="Tempo",
        yaxis_title=y_title,
        height=300
    )
    return fig

# --- ESTILOS CSS E RENDERIZAÇÃO DE CARDS (HTML/Markdown) ---

st.markdown(
    """
    <style>
    .main-card { background-color: #2D3748; border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .main-card .main-value { font-size: 5rem; font-weight: 800; color: #4FD1C5; line-height: 1; }
    .main-card .main-label { font-size: 1.8rem; color: #E2E8F0; margin-bottom: 0.5rem; }
    .small-card { background-color: #2D3748; border-radius: 0.75rem; padding: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 1rem; display: flex; align-items: center; gap: 1rem; }
    .small-card .icon { font-size: 2rem; color: #A0AEC0; }
    .small-card .value { font-size: 1.5rem; font-weight: 700; color: #E2E8F0; }
    </style>
    """,
    unsafe_allow_html=True
)

def render_main_card(placeholder, sensor_id=MAIN_SENSOR_ID):
    """Renderiza o card principal (Temperatura)."""
    current_reading = st.session_state.latest_readings.get(sensor_id, {})
    value = current_reading.get("value", "N/A")
    timestamp = current_reading.get("timestamp", "N/A")
    
    formatted_value = format_value(value, sensor_id)
    unit = DEFAULT_SENSORS_INFO[sensor_id]["unit"]
    icon = DEFAULT_SENSORS_INFO[sensor_id]["icon"]
    label = DEFAULT_SENSORS_INFO[sensor_id]["label"]
    
    with placeholder.container():
        st.markdown(
            f"""
            <div class="main-card">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                        <span style="font-size: 2.5rem; color: #4FD1C5;">{icon}</span>
                        <p class="main-label">{label}</p>
                    </div>
                    <p class="main-value">{formatted_value}{unit}</p>
                    <p class="main-status">Última leitura: {format_timestamp(timestamp)}</p>
                </div>
                <div class="footer-info">
                    <p>Sensor ID: {sensor_id}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_small_card(placeholder, sensor_id):
    """Renderiza um card menor para outros sensores."""
    current_reading = st.session_state.latest_readings.get(sensor_id, {})
    value = current_reading.get("value", "N/A")
    timestamp = current_reading.get("timestamp", "N/A")
    
    formatted_value = format_value(value, sensor_id)
    unit = DEFAULT_SENSORS_INFO[sensor_id]["unit"]
    icon = DEFAULT_SENSORS_INFO[sensor_id]["icon"]
    label = DEFAULT_SENSORS_INFO[sensor_id]["label"]

    with placeholder.container():
        st.markdown(
            f"""
            <div class="small-card">
                <span class="icon">{icon}</span>
                <div>
                    <div class="label">{label}</div>
                    <div class="value">{formatted_value} {unit}</div>
                    <div style="font-size: 0.75rem; color: #6B7280;">Atualizado: {format_timestamp(timestamp)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# --- ESTRUTURA DE LAYOUT STREAMLIT ---

st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 2rem;">
        <h1 style="margin: 0; font-size: 2.5rem; color: #4FD1C5;">Monitoramento de Sensores</h1>
        <span style="font-size: 1.5rem; color: #E2E8F0;">⚙️</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.write(f'<p style="color:#A0AEC0; margin-bottom: 2rem;">Fonte de Dados: SQLite local ({DB_NAME}). Buscando as últimas {HISTORY_LIMIT} leituras. Atualização a cada {POLLING_INTERVAL} segundos.</p>', unsafe_allow_html=True)
st.write('<p style="color:#F6AD55;">ATENÇÃO: Este dashboard está no modo LEITURA. Execute o script <code>data_writer_sqlite.py</code> em paralelo para alimentar o banco de dados.</p>', unsafe_allow_html=True)


# Layout principal: Cards de Leitura
main_col, other_sensors_col = st.columns([1, 2]) 
main_card_placeholder = main_col.empty()
small_cards_container = other_sensors_col.container()
cols_small = small_cards_container.columns(3) 

other_sensors_placeholders = {
    "M040": cols_small[0].empty(),
    "H020": cols_small[1].empty(),
    "L030": cols_small[2].empty(),
}

# Abas na parte inferior
st.markdown("---")
tab_charts, tab_raw_data = st.tabs(["📊 Gráficos de Evolução", "📋 Dados Brutos Recebidos"])

with tab_charts:
    st.subheader("Evolução Temporal dos Sensores")
    placeholder_charts_col = st.empty()

with tab_raw_data:
    placeholder_raw_data = st.empty()


# --- LOOP DE ATUALIZAÇÃO (POLLING) ---

while True:
    # Captura o timestamp atual para garantir uma chave única nos gráficos Plotly
    current_time = datetime.now().strftime("%Y%m%d%H%M%S") 
    
    # 1. Busca histórico e últimas leituras do SQLite
    history_df, latest_readings = fetch_data_history_from_db(HISTORY_LIMIT)
    
    # Atualiza o estado da sessão
    st.session_state.latest_readings.update(latest_readings)
    st.session_state.history_df = history_df
    
    # 2. Renderiza os cards
    render_main_card(main_card_placeholder, MAIN_SENSOR_ID) 
    
    for sensor_id, placeholder in other_sensors_placeholders.items():
        render_small_card(placeholder, sensor_id)
        
    # 3. Renderiza os gráficos (Tab 1)
    with tab_charts:
        with placeholder_charts_col.container():
            if not history_df.empty:
                
                chart_cols = st.columns(2)
                sensors_to_plot = ["T010", "H020", "L030", "M040"]
                
                for i, sensor_id in enumerate(sensors_to_plot):
                    fig = create_sensor_chart(history_df, sensor_id)
                    if fig:
                        # CORREÇÃO DE ERRO: key única por sensor E por ciclo de loop
                        chart_cols[i % 2].plotly_chart(fig, use_container_width=True, key=f"chart_{sensor_id}_{current_time}")
                        
            else:
                st.info("Aguardando dados históricos no banco de dados para gerar os gráficos.")

    # 4. Renderiza dados brutos (Tab 2)
    with tab_raw_data:
        with placeholder_raw_data.container():
            st.subheader(f"Últimas {len(st.session_state.history_df)} Leituras")
            st.caption("Esta tabela mostra os dados exatamente como foram lidos do banco de dados (SQLite).")
            
            # Exibe o DataFrame brutos
            st.dataframe(
                st.session_state.history_df[['sensorId', 'value', 'timestamp']].sort_values(by='timestamp', ascending=False), 
                use_container_width=True
            )

    # 5. Pausa para o polling
    time.sleep(POLLING_INTERVAL)