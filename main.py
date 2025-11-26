import streamlit as st
import time
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Sensores",
    layout="wide",
    initial_sidebar_state="expanded" # Expandido para mostrar os controles
)

# --- CONFIGURAÇÕES GLOBAIS ---
DB_NAME = 'sensores.db'
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')

# Cores específicas para cada sensor
DEFAULT_SENSORS_INFO = {
    "M040": {
        "type": "motion", "label": "Movimento", "unit": "", "icon": "🚶‍♂️", 
        "min_val": 0, "max_val": 1, "format": "{:.0f}", 
        "color": "#4FD1C5" # Teal (Verde Azulado)
    }, 
    "T010": {
        "type": "temperature", "label": "Temperatura", "unit": "°C", "icon": "🌡️", 
        "min_val": 18, "max_val": 35, "format": "{:.1f}",
        "color": "#F6AD55" # Laranja Suave
    },
    "H020": {
        "type": "humidity", "label": "Umidade", "unit": "%", "icon": "💧", 
        "min_val": 30, "max_val": 90, "format": "{:.0f}",
        "color": "#63B3ED" # Azul Claro
    },
    "L030": {
        "type": "light", "label": "Luminosidade", "unit": "lux", "icon": "💡", 
        "min_val": 0, "max_val": 1000, "format": "{:.0f}",
        "color": "#F6E05E" # Amarelo
    }
}

# --- FUNÇÕES DE DADOS ---

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=5, check_same_thread=False) 
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

@st.cache_data(ttl=1) 
def fetch_data_history_from_db(limit):
    """Busca o histórico e a última leitura de cada sensor."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame(), {}

    latest_readings = {}
    
    # Busca-se uma quantidade maior de dados (limit * 3) para garantir 
    # que haja informações suficientes para todos os sensores, considerando 
    # que a tabela contém dados misturados.
    query = f"""
    SELECT sensorId, value, timestamp 
    FROM sensor_data 
    ORDER BY timestamp DESC 
    LIMIT {limit * 4}; 
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        conn.close() 

        if df.empty:
            return df, {}
        
        df['type'] = df['sensorId'].apply(lambda x: DEFAULT_SENSORS_INFO.get(x, {}).get("type", "unknown"))
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert(TIMEZONE_BR)
        
        df_latest = df.sort_values(by='timestamp', ascending=False).drop_duplicates(subset=['sensorId'])
        
        for index, row in df_latest.iterrows():
            latest_readings[row["sensorId"]] = {
                "sensorId": row["sensorId"],
                "type": row["type"],
                "value": row["value"],
                "timestamp": row["timestamp"].isoformat() 
            }
        
        return df, latest_readings
        
    except pd.io.sql.DatabaseError:
        st.warning(f"Tabela 'sensor_data' não encontrada. Execute o 'data_writer_sqlite.py'.")
        return pd.DataFrame(columns=['sensorId', 'value', 'timestamp', 'type']), {}
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return pd.DataFrame(columns=['sensorId', 'value', 'timestamp', 'type']), {}

def format_timestamp(timestamp_obj):
    if isinstance(timestamp_obj, str):
        try:
            timestamp_obj = datetime.fromisoformat(timestamp_obj)
        except:
            return str(timestamp_obj)
    
    if pd.isnull(timestamp_obj):
        return "--"
        
    return timestamp_obj.strftime("%d/%m/%Y %H:%M:%S")

def format_value(value, sensor_id):
    config = DEFAULT_SENSORS_INFO.get(sensor_id)
    if not config or value == "N/A":
        return str(value)
    
    if sensor_id == "M040":
        return "Detectado" if (value is not None and float(value) >= 0.5) else "Ausente"

    try:
        return config["format"].format(float(value))
    except (ValueError, TypeError):
        return str(value)

# --- FUNÇÕES DE UI ---
def create_sensor_chart(df_history, sensor_id):
    """Cria um gráfico Plotly estilizado."""
    config = DEFAULT_SENSORS_INFO.get(sensor_id)
    if df_history.empty or not config:
        return None

    df_sensor = df_history[df_history['sensorId'] == sensor_id].copy()
    if df_sensor.empty:
        return None
        
    df_sensor = df_sensor.sort_values(by='timestamp', ascending=True)

    # Cores e Estilo
    # Pega a cor específica do sensor ou usa fallback
    primary_color = config.get("color", "#4FD1C5") 
    secondary_background_color = config.get("secondaryBackgroundColor", "#2D3748")
    text_color = '#E2E8F0'    # Cinza claro
    
    # Título formatado com a cor do sensor
    chart_title = f"<span style='color:{primary_color}'><b>{config['icon']} {config['label']}</b></span>"
    if config['unit']:
        chart_title += f" <span style='font-size: 0.8em; color: #A0AEC0;'>({config['unit']})</span>"

    if sensor_id == "M040":
        # --- LÓGICA DE MOVIMENTO (AREA STEP) ---
        fig = go.Figure()
        
        # Converte hex para rgba com opacidade para o preenchimento
        # Truque simples para converter hex #RRGGBB para rgba
        hex_color = primary_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        fill_color = f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.2)'

        fig.add_trace(go.Scatter(
            x=df_sensor['timestamp'],
            y=df_sensor['value'],
            mode='lines', # No step chart, markers podem poluir, melhor só linha
            name='Movimento',
            line_shape='hv',     
            fill='tozeroy',      
            line=dict(color=primary_color, width=2),
            fillcolor=fill_color
        ))
        
        fig.update_yaxes(
            tickmode='array', 
            tickvals=[0, 1], 
            ticktext=['Ausente', 'Detectado'], 
            range=[-0.1, 1.2],
            gridcolor='rgba(255,255,255,0.05)'
        )
    else:
        # --- LÓGICA PADRÃO (LINHA + MARKERS) ---
        fig = px.line(df_sensor, x='timestamp', y='value')
        
        # Atualiza para ter linha E pontos (markers)
        fig.update_traces(
            mode='lines+markers',
            line=dict(color=primary_color, width=2),
            marker=dict(
                size=6,
                color=primary_color,
                symbol='circle',
                line=dict(width=1, color=secondary_background_color)
                )
        )
        fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')

    # --- ESTILIZAÇÃO GERAL DO LAYOUT ---
    fig.update_layout(
        title=dict(
            text=chart_title,
            font=dict(size=18),
            x=0.02, 
            y=0.93  
        ),
        # Fundo transparente no Plotly para evitar conflito com o CSS do Streamlit
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        
        font=dict(color=text_color),
        
        margin=dict(l=40, r=40, t=80, b=40),
        
        xaxis=dict(
            tickformat="%H:%M:%S",
            title=None,
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title=None,
            zeroline=False
        ),
        height=300
    )

    # Separador
    fig.add_shape(
        type="line",
        xref="paper", yref="paper",
        x0=0, y0=1.05, x1=1, y1=1.05, 
        line=dict(color="#4A5568", width=1)
    )

    return fig

# --- SIDEBAR DE CONTROLES ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    col_btn, col_check = st.columns([1, 1])
        
    auto_refresh = st.toggle("Auto-Refresh", value=True)
    
    refresh_interval = st.slider(
        "Atualização (segundos)", 
        min_value=1, max_value=30, value=10
    )

    st.markdown("---")
    
    # === NOVO SLIDER PARA LIMITAR DADOS ===
    history_limit = st.slider(
        "Pontos no Gráfico",
        min_value=20, 
        max_value=500, 
        value=100, 
        step=20,
        help="Controla a quantidade de dados passados mostrados nos gráficos."
    )

# --- LÓGICA PRINCIPAL ---
# 1. Carregar Dados (Usando o valor do slider history_limit)
history_df, latest_readings = fetch_data_history_from_db(history_limit)

# CSS AVANÇADO: Cards, Gráficos com Bordas Arredondadas
st.markdown(
    """
    <style>
    p { /* Targets st.subheader elements */
        margin-bottom: 0.5rem; /* Reduce space below subheader */
    }

    /* Estilo dos Cards KPI */
    .metric-card { 
        background-color: #2D3748; 
        border-radius: 12px; 
        padding: 20px; 
        border-left: 6px solid #4FD1C5; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }
    .metric-label { color: #A0AEC0; font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { color: #F7FAFC; font-size: 2.2em; font-weight: 700; margin: 5px 0; }
    .metric-unit { color: #4FD1C5; font-size: 0.5em; vertical-align: super; }
    .metric-time { color: #718096; font-size: 0.75em; display: flex; align-items: center; gap: 5px; }
    
    /* Arredondar bordas dos Gráficos Plotly */
    .stPlotlyChart {
        background-color: #2D3748;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        padding: 10px; /* Gap externo */
        border: 1px solid #4A5568; /* Borda sutil */
    }
    
    /* Ajuste Geral */
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎛️ Dashboard de Monitoramento")

# 2. Renderizar KPI Cards
if latest_readings:
    cols = st.columns(len(DEFAULT_SENSORS_INFO))
    sorted_sensors = sorted(DEFAULT_SENSORS_INFO.keys())
    
    for idx, sensor_id in enumerate(sorted_sensors):
        sensor_data = latest_readings.get(sensor_id, {})
        config = DEFAULT_SENSORS_INFO[sensor_id]
        
        val = sensor_data.get("value", "N/A")
        ts = sensor_data.get("timestamp", None)
        formatted_val = format_value(val, sensor_id)
        ts_display = format_timestamp(ts)
        
        # Pega a cor específica para a borda do card
        border_color = config.get("color", "#4FD1C5")

        with cols[idx]:
            # Injeta a cor específica na borda e na unidade
            st.markdown(f"""
            <div class="metric-card" style="border-left: 6px solid {border_color};">
                <div class="metric-label">{config['icon']} {config['label']}</div>
                <div class="metric-value">
                    {formatted_val} <span class="metric-unit" style="color: {border_color};">{config['unit']}</span>
                </div>
                <div class="metric-time">🕒 {ts_display}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.warning("Aguardando dados dos sensores...")

st.markdown("---")

# 3. Abas de Conteúdo
tab_graficos, tab_dados = st.tabs(["📈 Gráficos Visuais", "📋 Dados Brutos & Download"])

# ABA 1: GRÁFICOS
with tab_graficos:
    if not history_df.empty:
        st.caption(f"Visualizando os últimos {len(history_df)} registros (Aprox. {history_limit} por sensor).")
        
        chart_grid = st.columns(2)
        sensors_list = sorted(DEFAULT_SENSORS_INFO.keys())
        
        for i, sensor_id in enumerate(sensors_list):
            fig = create_sensor_chart(history_df, sensor_id)
            if fig:
                chart_grid[i % 2].plotly_chart(
                    fig, 
                    use_container_width=True, 
                    key=f"chart_{sensor_id}_{len(history_df)}"
                )
    else:
        st.info("Sem dados históricos para exibir.")

# ABA 2: DADOS BRUTOS & DOWNLOAD
with tab_dados:
    st.subheader("Filtragem e Exportação")
    
    col_filter, col_dwn = st.columns([3, 1], vertical_alignment="bottom")
    
    with col_filter:
        selected_sensors = st.multiselect(
            "Filtrar por Sensores:",
            options=DEFAULT_SENSORS_INFO.keys(),
            default=DEFAULT_SENSORS_INFO.keys(),
            format_func=lambda x: f"{x} - {DEFAULT_SENSORS_INFO[x]['label']}"
        )
    
    if not history_df.empty:
        filtered_df = history_df[history_df['sensorId'].isin(selected_sensors)].copy()
        filtered_df = filtered_df.sort_values(by='timestamp', ascending=False)
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Horário", format="DD/MM/YYYY HH:mm:ss"),
                "value": "Valor Lido",
                "sensorId": "ID Sensor"
            },
            height=400
        )
        
        with col_dwn:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            st.caption(f"Total de linhas: {len(filtered_df)}")
            st.download_button(
                label="📥 Baixar CSV (Filtrado)",
                data=csv,
                file_name=f'sensores_dados_{timestamp_str}.csv',
                mime='text/csv',
                type="primary"
            )
    else:
        st.info("Nenhum dado disponível para exportação.")

# CONTROLE DE AUTO-REFRESH
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()