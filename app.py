import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
import ast

# Importação da ferramenta de busca (Google Hotels)
try:
    import plotly.express as px
except ImportError:
    px = None

# 1. Configurações de Estética da Página
st.set_page_config(
    page_title="Viagem Otimizada AI",
    page_icon="✈️",
    layout="wide"
)

# Carregamento dos dados de aeroportos para autocomplete
@st.cache_data
def load_airports():
    try:
        # Carrega o CSV assumindo que ele está no mesmo diretório
        df = pd.read_csv("airports.csv")
        
        # Remove entradas que não tenham código IATA ou Cidade definidos
        df = df.dropna(subset=['IATA', 'City', 'Airport name'])
        
        # Cria uma string formatada para facilitar a busca: "Cidade (IATA) - Aeroporto"
        # Ex: "São Paulo (GRU) - Guarulhos..."
        df['Display'] = df.apply(
            lambda x: f"{str(x['City']).strip()} ({str(x['IATA']).strip()}) - {str(x['Airport name']).strip()}", 
            axis=1
        )
        
        # Retorna a lista ordenada para o selectbox
        return sorted(df['Display'].unique().tolist())
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de aeroportos (airports.csv): {e}")
        return []

# Carregamento do banco de dados de coordenadas (substituindo o hardcoded)
@st.cache_data
def load_coordinates():
    try:
        # O arquivo coord.csv contém uma estrutura de dicionário Python 'coords = {...}'
        # e não um formato CSV padrão. Usamos ast.literal_eval para processá-lo.
        with open("coord.csv", "r") as f:
            content = f.read()
            # Remove a atribuição da variável para parsear apenas o dicionário
            if "coords =" in content:
                content = content.replace("coords =", "").strip()
            return ast.literal_eval(content)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de coordenadas (coord.csv): {e}")
        return {}

# Carrega a lista uma única vez
airport_options = load_airports()

# 2. Estilização CSS Minimalista
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .footer { position: fixed; bottom: 10px; right: 10px; color: gray; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 3. BARRA LATERAL (Entrada de Dados)
with st.sidebar:
    st.title("Configuração")
    
    st.markdown("### 👥 Passageiros")
    col_a, col_c = st.columns(2)
    adultos = col_a.number_input("Adultos", 1, 6, 1) # Limite de 6 para a API
    criancas = col_c.number_input("Crianças", 0, 5, 0)
    
    st.markdown("### 📅 Datas")
    data_inicio = st.date_input(
        "Data Início", 
        value=date(2026, 2, 5), 
        format="DD/MM/YYYY"
    )
    
    ida_e_volta = st.toggle("Ida e Volta", value=True)
    
    data_volta = data_inicio + timedelta(days=7)
    
    # Inicializa variáveis como False por padrão para evitar erros se 'ida_e_volta' for False
    alugar_carro = False
    buscar_hoteis_toggle = False

    if ida_e_volta:
        data_volta = st.date_input(
            "Data de Volta", 
            value=data_inicio + timedelta(days=7),
             format="DD/MM/YYYY"
        )
        
        # Opções exibidas apenas se Ida e Volta estiver ativo
        alugar_carro = st.toggle("Alugar Carro", value=False)
        buscar_hoteis_toggle = st.toggle("Buscar Hotéis", value=True)
    
    st.markdown("---")
    st.markdown("### 📍 Roteiro")
    
    # Lógica para definir índices padrão (Tenta achar GRU e MIA, senão usa o primeiro da lista)
    default_idx_origem = 0
    default_idx_destino = 0
    
    if airport_options:
        # Procura índice para São Paulo (GRU)
        for i, opt in enumerate(airport_options):
            if "GRU" in opt and "São Paulo" in opt:
                default_idx_origem = i
                break
        
        # Procura índice para Miami (MIA)
        for i, opt in enumerate(airport_options):
            if "MIA" in opt and "Miami" in opt:
                default_idx_destino = i
                break

    # Implementação dos campos com Selectbox (Autocomplete)
    origens = st.selectbox(
        "Origem", 
        options=airport_options, 
        index=None,
        help="Digite o nome da cidade ou código IATA para buscar"
    )
    
    destinos = st.selectbox(
        "Destino", 
        options=airport_options, 
        index=None,
        help="Digite o nome da cidade ou código IATA para buscar"
    )
    
    cidades_extra = st.text_area("Cidades Obrigatórias", placeholder="Ex: Londres, Paris...")
    
    st.markdown("---")
    st.markdown("### ⚖️ Prioridade")
    peso = st.select_slider(
        "Prioridade",
        options=["Menor Preço", "Equilibrado", "Mais Rápido"],
        value="Equilibrado"
    )
    
    btn_otimizar = st.button("✨ OTIMIZAR VIAGEM", use_container_width=True, type="primary")

# 4. PAINEL PRINCIPAL
st.title("🚀 Roteiro Inteligente")
st.caption(f"Exibindo melhor rota para {origens} ➔ {destinos} com foco em {peso}")

# Métricas
m1, m2, m3, m4 = st.columns(4)
m1.metric("Preço Otimizado", "R$ 1.540", "-22%")
m2.metric("Tempo Total", "10.8h", "+2h conex.")
m3.metric("Hospedagem", "R$ 450/dia", "Média")
m4.metric("Economia Real", "R$ 1.100", "🔥")

st.markdown("---")

tab_rota, tab_hoteis, tab_tendencia = st.tabs(["📋 Itinerários", "🏨 Hotéis Encontrados", "📈 Tendência de Preço"])

with tab_rota:
    # 1. Banco de dados de coordenadas (Hubs) - Lendo do arquivo coord.csv
    coords = load_coordinates()

    # 2. Criação do DataFrame das Rotas
    df_rota = pd.DataFrame({
        "Cia Aérea": ["Copa Airlines", "Avianca", "LATAM", "Delta Airlines"],
        "Rota": ["São Paulo (GRU) ➔ Miami (MIA)"] * 4,
        "Partida": [
            f"01:30 ({data_inicio.strftime('%d/%m')})",
            f"06:05 ({data_inicio.strftime('%d/%m')})",
            f"19:40 ({data_inicio.strftime('%d/%m')})",
            f"22:50 ({data_inicio.strftime('%d/%m')})"
        ],
        "Chegada": [
            f"10:38 ({(data_inicio).strftime('%d/%m')})", 
            f"17:20 ({(data_inicio).strftime('%d/%m')})", 
            f"05:15 ({(data_inicio + timedelta(days=1)).strftime('%d/%m')})", 
            f"09:30 ({(data_inicio + timedelta(days=1)).strftime('%d/%m')})"  
        ],
        "Duração": ["11h 08min", "13h 15min", "12h 35min", "14h 40min"],
        "Detalhes": ["1 parada", "1 parada", "1 parada", "1 parada"],
        "Conexões": [
            "Panamá (PTY) - 1h 20m espera", 
            "Bogotá (BOG) - 3h 10m espera", 
            "Lima (LIM) - 2h 05m espera", 
            "Atlanta (ATL) - 2h 45m espera"
        ],
        "Preço": ["R$ 3.250,00", "R$ 2.980,00", "R$ 3.540,00", "R$ 4.100,00"],
    })

    st.info("👇 **Clique em uma linha** da tabela para visualizar a rota no mapa.")

    # 3. Tabela Interativa (Substitui st.table)
    # on_select="rerun" faz o app recarregar quando clica
    event = st.dataframe(
        df_rota,
        use_container_width=True,
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row"
    )

    # 4. Lógica de Captura da Seleção
    # Se houver seleção, pega o índice. Se não, usa 0 (primeira rota).
    rows = event.selection.rows
    selected_index = rows[0] if rows else 0
    
    # Extrai os dados da linha selecionada
    rota_selecionada = df_rota.iloc[selected_index]
    conexao_texto = rota_selecionada["Conexões"]
    cia_selecionada = rota_selecionada["Cia Aérea"]

    # 5. Lógica do Mapa Dinâmico
    st.subheader(f"Visualização: {cia_selecionada}")
    
    mapa = folium.Map(location=[5.0, -65.0], zoom_start=3, tiles="CartoDB positron")
    
    # Define pontos fixos (Mock)
    # Nota: Em produção, você buscaria dinamicamente do input do usuário
    # Se as chaves não existirem no novo arquivo coord.csv, adicione tratamento de erro
    try:
        ponto_origem = coords.get("GRU", [-23.4356, -46.4731])
        ponto_destino = coords.get("MIA", [25.7959, -80.2870])
    except AttributeError:
        # Fallback caso coords não tenha carregado corretamente
        ponto_origem = [-23.4356, -46.4731]
        ponto_destino = [25.7959, -80.2870]

    # Marcadores Origem/Destino
    folium.Marker(ponto_origem, popup="GRU", icon=folium.Icon(color="green", icon="plane")).add_to(mapa)
    folium.Marker(ponto_destino, popup="MIA", icon=folium.Icon(color="red", icon="flag")).add_to(mapa)

    # Identifica coordenada da conexão baseado na string da linha selecionada
    ponto_conexao = None
    # Verifica se a chave existe no dicionário carregado antes de acessar
    if "PTY" in conexao_texto and "PTY" in coords: ponto_conexao = coords["PTY"]
    elif "BOG" in conexao_texto and "BOG" in coords: ponto_conexao = coords["BOG"]
    elif "LIM" in conexao_texto and "LIM" in coords: ponto_conexao = coords["LIM"]
    elif "ATL" in conexao_texto and "ATL" in coords: ponto_conexao = coords["ATL"]

    # Desenha rota
    if ponto_conexao:
        folium.PolyLine([ponto_origem, ponto_conexao, ponto_destino], color="#0066FF", weight=4, opacity=0.8).add_to(mapa)
        folium.CircleMarker(ponto_conexao, radius=6, color="orange", fill=True, fill_color="orange", popup=conexao_texto).add_to(mapa)
    else:
        folium.PolyLine([ponto_origem, ponto_destino], color="#0066FF", weight=4).add_to(mapa)

    st_folium(mapa, width="100%", height=400, key="mapa_rota")

    

with tab_hoteis:
    st.subheader(f"Melhores opções em {destinos}")
    
    if buscar_hoteis_toggle:
        # Simulando uma busca de dados reais
        # Em um projeto real, aqui você usaria 'requests' para chamar uma API de hotéis
        hoteis_fake = [
            {
                "nome": "Miami Beach Grand Resort",
                "preco": "R$ 1.250",
                "nota": "4.8",
                "img": "https://images.unsplash.com/photo-1561501900-3701fa6a0864?w=600",
                "desc": "Vista para o mar, café da manhã incluso e piscina infinita."
            },
            {
                "nome": "Downtown Modern Suite",
                "preco": "R$ 890",
                "nota": "4.5",
                "img": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400",
                "desc": "Localizado no centro financeiro, ideal para quem busca mobilidade."
            },
            {
                "nome": "Ocean Drive Boutique Hotel",
                "preco": "R$ 1.540",
                "nota": "4.9",
                "img": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400",
                "desc": "Estilo Art Déco com acesso direto à praia privativa."
            }
        ]

        for hotel in hoteis_fake:
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(hotel["img"], use_container_width=True)
                with col2:
                    st.subheader(hotel["nome"])
                    st.write(f"⭐ **Avaliação:** {hotel['nota']}")
                    st.write(f"📅 **Período:** {data_inicio.strftime('%d/%m')} a {data_volta.strftime('%d/%m')}")
                    st.markdown(f"### Preço: {hotel['preco']}/noite")
                    st.button(f"Reservar no {hotel['nome']}", key=hotel['nome'])
                st.divider()
    else:
        st.info("Ative 'Buscar Hotéis' na barra lateral para ver as opções.")

with tab_tendencia:
    st.subheader("Melhores dias para embarcar")
    if px:
        df_precos = pd.DataFrame({
            "Data": ["01/02", "02/02", "03/02", "04/02", "05/02", "06/02", "07/02"],
            "Preço": [1900, 1850, 1540, 1600, 2100, 1950, 1700]
        })
        fig = px.area(df_precos, x="Data", y="Preço", title="Variação de Preço (R$)")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Instale o Plotly (`pip install plotly`)")

st.markdown('<div class="footer">Gerado por Smart Travel AI © 2026</div>', unsafe_allow_html=True)