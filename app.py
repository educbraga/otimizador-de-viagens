import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
import ast
import requests  # Adicionar esta linha

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

def extrair_iata(texto_aeroporto: str) -> str:
    """
    Extrai o código IATA de uma string como 'São Paulo (GRU) - Guarulhos...'
    Retorna o código entre parênteses.
    """
    if not texto_aeroporto:
        return ""
    try:
        inicio = texto_aeroporto.index("(") + 1
        fim = texto_aeroporto.index(")")
        return texto_aeroporto[inicio:fim]
    except ValueError:
        return texto_aeroporto[:3].upper()


def mapear_prioridade(peso: str) -> int:
    """Converte o texto de prioridade para o valor numérico esperado pela API."""
    mapa = {
        "Menor Preço": 0,
        "Equilibrado": 1,
        "Mais Rápido": 2
    }
    return mapa.get(peso, 1)


def chamar_backend(payload: dict) -> dict:
    """Envia requisição POST para o backend e retorna a resposta."""
    url = "http://localhost:8000/optimize-trip"
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()

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

# Lógica de integração com o backend
if btn_otimizar:
    # Validação básica
    if not origens or not destinos:
        st.error("⚠️ Selecione origem e destino antes de otimizar.")
    else:
        # Extrai códigos IATA
        iata_origem = extrair_iata(origens)
        iata_destino = extrair_iata(destinos)
        
        # Monta o payload
        payload = {
            "passengers": {
                "adults": adultos,
                "children": criancas
            },
            "dates": {
                "is_roundtrip": ida_e_volta,
                "departure_date": data_inicio.isoformat(),
                "return_date": data_volta.isoformat() if ida_e_volta else None
            },
            "preferences": {
                "priority_level": mapear_prioridade(peso)
            },
            "route": {
                "origin": iata_origem,
                "destination": iata_destino
            }
        }
        
        # Chama o backend com spinner
        with st.spinner("🔍 Buscando voos... Isso pode levar alguns segundos."):
            try:
                resultado = chamar_backend(payload)
                st.session_state["resultado_busca"] = resultado
                st.session_state["busca_realizada"] = True
                st.success(f"✅ Encontrados {resultado.get('total_voos', 0)} voos!")
            except requests.exceptions.ConnectionError:
                st.error("❌ Não foi possível conectar ao backend. Verifique se a API está rodando em http://localhost:8000")
            except requests.exceptions.Timeout:
                st.error("❌ A busca demorou muito. Tente novamente.")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ Erro na API: {e}")
            except Exception as e:
                st.error(f"❌ Erro inesperado: {e}")

# 4. PAINEL PRINCIPAL
st.title("🚀 Roteiro Inteligente")
st.caption(f"Exibindo melhor rota para {origens} ➔ {destinos} com foco em {peso}")

# Métricas - Usa dados reais se disponível
m1, m2, m3, m4 = st.columns(4)

if "resultado_busca" in st.session_state and st.session_state.get("busca_realizada"):
    resultado = st.session_state["resultado_busca"]
    voos = resultado.get("voos", [])
    
    # Extrai o menor preço (tenta parsear o valor)
    if voos:
        # Pega o primeiro voo (geralmente já ordenado por preço)
        menor_preco = voos[0].get("preco", "N/A")
        total_voos = resultado.get("total_voos", 0)
        
        # Tenta extrair a menor duração
        duracao_menor = voos[0].get("duracao", "N/A") if voos else "N/A"
    else:
        menor_preco = "N/A"
        total_voos = 0
        duracao_menor = "N/A"
    
    m1.metric("Melhor Preço", menor_preco)
    m2.metric("Total de Voos", total_voos)
    m3.metric("Menor Duração", duracao_menor)
    m4.metric("Busca em", resultado.get("data_execucao", "")[:10])
else:
    # Dados mockados quando não há busca
    m1.metric("Preço Otimizado", "R$ --", "Aguardando busca")
    m2.metric("Total de Voos", "--")
    m3.metric("Duração", "--")
    m4.metric("Status", "⏳ Pendente")

st.markdown("---")

tab_rota, tab_hoteis, tab_tendencia = st.tabs(["📋 Itinerários", "🏨 Hotéis Encontrados", "📈 Tendência de Preço"])

with tab_rota:
    # 1. Banco de dados de coordenadas (Hubs) - Lendo do arquivo coord.csv
    coords = load_coordinates()

    # 2. Criação do DataFrame das Rotas - Usa dados reais se disponível
    if "resultado_busca" in st.session_state and st.session_state.get("busca_realizada"):
        resultado = st.session_state["resultado_busca"]
        voos = resultado.get("voos", [])
        
        if voos:
            # Mapeia os dados do backend para o formato da tabela
            df_rota = pd.DataFrame({
                "Cia Aérea": [v.get("companhia", "N/A") for v in voos],
                "Rota": [f"{extrair_iata(origens) if origens else 'N/A'} ➔ {extrair_iata(destinos) if destinos else 'N/A'}"] * len(voos),
                "Partida": [v.get("horario_partida", "N/A") for v in voos],
                "Chegada": [v.get("horario_chegada", "N/A") for v in voos],
                "Duração": [v.get("duracao", "N/A") for v in voos],
                "Detalhes": [v.get("paradas", "N/A") for v in voos],
                "Preço": [v.get("preco", "N/A") for v in voos],
            })
        else:
            st.warning("Nenhum voo encontrado para esta rota.")
            df_rota = pd.DataFrame()
    else:
        # Dados mockados (mantém comportamento original)
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
            "Preço": ["R$ 3.250,00", "R$ 2.980,00", "R$ 3.540,00", "R$ 4.100,00"],
        })

    if not df_rota.empty:
        st.info("👇 **Clique em uma linha** da tabela para visualizar a rota no mapa.")

        # 3. Tabela Interativa
        event = st.dataframe(
            df_rota,
            use_container_width=True,
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-row"
        )

        # 4. Lógica de Captura da Seleção
        rows = event.selection.rows
        selected_index = rows[0] if rows else 0
        
        # Extrai os dados da linha selecionada
        rota_selecionada = df_rota.iloc[selected_index]
        conexao_texto = rota_selecionada["Detalhes"]
        cia_selecionada = rota_selecionada["Cia Aérea"]

        # 5. Lógica do Mapa Dinâmico
        st.subheader(f"Visualização: {cia_selecionada}")
        
        iata_origem = extrair_iata(origens)
        iata_destino = extrair_iata(destinos)

        ponto_origem = coords.get(iata_origem)
        ponto_destino = coords.get(iata_destino)

        if not ponto_origem or not ponto_destino:
            st.warning("⚠️ Coordenadas não encontradas para origem ou destino.")
            st.stop()

        # Centraliza o mapa entre origem e destino
        center_lat = (ponto_origem[0] + ponto_destino[0]) / 2
        center_lon = (ponto_origem[1] + ponto_destino[1]) / 2

        mapa = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=4,
            tiles="CartoDB positron"
        )
    

        # Marcadores Origem/Destino
        folium.Marker(
            ponto_origem,
            popup=f"Origem: {iata_origem}",
            icon=folium.Icon(color="green", icon="plane")
        ).add_to(mapa)

        folium.Marker(
            ponto_destino,
            popup=f"Destino: {iata_destino}",
            icon=folium.Icon(color="red", icon="flag")
        ).add_to(mapa)

        # Identifica coordenada da conexão baseado na string da linha selecionada
        ponto_conexao = None
        # Verifica se a chave existe no dicionário carregado antes de acessar
        if "PTY" in conexao_texto and "PTY" in coords: ponto_conexao = coords["PTY"]
        elif "BOG" in conexao_texto and "BOG" in coords: ponto_conexao = coords["BOG"]
        elif "LIM" in conexao_texto and "LIM" in coords: ponto_conexao = coords["LIM"]
        elif "ATL" in conexao_texto and "ATL" in coords: ponto_conexao = coords["ATL"]

        # Desenha rota
        if ponto_conexao:
            folium.PolyLine(
                [ponto_origem, ponto_destino],
                color="#0066FF",
                weight=4,
                opacity=0.8
            ).add_to(mapa)
            folium.CircleMarker(ponto_conexao, radius=6, color="orange", fill=True, fill_color="orange", popup=conexao_texto).add_to(mapa)
        else:
            folium.PolyLine(
                [ponto_origem, ponto_destino],
                color="#0066FF",
                weight=4,
                opacity=0.8
            ).add_to(mapa)

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