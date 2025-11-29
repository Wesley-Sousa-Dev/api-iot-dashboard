# API REST IoT
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![SQLite](https://img.shields.io/badge/Database-SQLite3-green)
![Status](https://img.shields.io/badge/Status-Concluído-green)


## 📝 Visão geral
O "API REST IoT" é um sistema distribuído projetado para a ingestão, persistência e monitoramento de telemetria em tempo real. O projeto estabelece uma infraestrutura de comunicação onde dispositivos de borda (edge devices) reportam estados ambientais e de ocupação para um nó central de processamento.

A arquitetura da solução baseia-se no desacoplamento entre a camada de produção de dados e a camada de visualização, utilizando uma API REST como ponto de entrada unificado. Simuladores externos (em Java) atuam como produtores independentes, disparando requisições HTTP contendo cargas JSON padronizadas. O sistema processa esses eventos de forma assíncrona e intercalada, simulando um ambiente real onde múltiplos sensores (Temperatura, Umidade, Luminosidade, Movimento) enviam leituras em momentos distintos e aleatórios.

<div align="center">
<img 
  src="./assets/dashboard_example_01.png"
  alt="Exemplo da página de produto"
  height="500"
  />
</div>

---

## ✨ Principais Funcionalidades
- **Ingestão de Dados via API:** Endpoint dedicado para recepção de requisições POST vindas de sensores simulados;
- **Monitoramento em Tempo Real:** Cards dinâmicos exibindo os dados mais recentes recebidos;
- **Visualização Interativa:** Gráficos de linha e barra desenvolvidos com Plotly, permitindo zoom e seleção de dados;
- **Controle de Atualização:** Intervalo de *refresh* automático customizável (com opção de pausa);
- **Persistência de Dados:** Armazenamento imediato, seguro e leve das leituras (ID, Valor, Timestamp) utilizando o banco de dados SQLite;
- **Filtragem Avançada:** Filtros para selecionar sensores específicos;
- **Exportação de Dados:** Download imediato dos dados filtrados em formato CSV.

---

## 🛠 Tecnologias Utilizadas
Este projeto foi desenvolvido utilizando as seguintes tecnologias:

- **Linguagem Principal:** [Python](https://www.python.org/);
- **Frontend / Dashboard:** [Streamlit](https://streamlit.io/);
- **Backend / Ingestão:** [Flask](https://flask.palletsprojects.com/);
- **Banco de Dados:** SQLite3 (Nativo do Python);
- **Manipulação de Dados:** [Pandas](https://pandas.pydata.org/);
- **Gráficos:** [Plotly Express](https://plotly.com/python/);
- **Simulação de Sensores:** Java (arquivos .jar).

---

## 🚀 Passos para execução
### Pré-requisitos
  Antes de começar, certifique-se de ter instalado em sua máquina:
  - [Python 3.8+](https://www.python.org/downloads/);
  - [Java Runtime Environment (JRE)](https://www.java.com/pt-BR/download/) (para rodar os simuladores .jar);
  - [Git](https://git-scm.com/).

  ### Passo 1. Clone o repositório
  ```bash
    git clone Wesley-Sousa-Dev/api-iot-dashboard
  ```

  ### Passo 2. Configuração do Ambiente Virtual
  Crie e ative o ambiente virtual para isolar as dependências do projeto:

  **Linux / macOS:**
  ```bash
    python -m venv .venv
    source .venv/bin/activate
  ```

  **Windows:**
  ```bash
    python -m venv .venv
    .venv/Scripts/activate
  ```


  ### Passo 3. Instalação das Dependências
  Com o ambiente virtual ativo, instale as bibliotecas necessárias:
   ```bash  
    pip install -r requirements.txt
   ```

  ### Passo 4: Inicializar a API de Coleta e Persistência de Dados
  Neste passo, iniciamos o servidor Python que ficará escutando na porta 8080. Ele é responsável por receber os dados dos sensores e salvar no banco de dados SQLite.

  Execute o comando abaixo e **mantenha o terminal aberto**:

  ```bash
  python data_writer_sqlite.py
  ```
  Você verá a mensagem: "🚀 Servidor API rodando na porta 8080..."

  ### Passo 5. Iniciando a Simulação de Dados
  Com a API rodando, agora precisamos ligar os sensores para gerar os dados. Abra um novo terminal e execute o simulador:
  
  ```bash 
    cd utils
    java -jar simulator-sensores-iot.jar
  ```

  OBS.: Não é executado o "server-iot-rest-example.jar", pois nossa API Python "data_writer_sqlite.py" já cumpre o papel de servidor, substituindo o exemplo em Java.

  ### Passo 6. Executando o Dashboard
  Finalmente, inicie a interface visual com o Streamlit em um terceiro terminal:
  ```bash
    streamlit run main.py
  ```
  O navegador abrirá automaticamente no endereço http://localhost:8501.

  
