import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
import ast
import requests

# 1. Configurações de Estética da Página
st.set_page_config(
    page_title="Viagem Otimizada AI",
    page_icon="✈️",
    layout="wide"
)

# Inicialização de Session State para campos dinâmicos
if "qtde_origens" not in st.session_state:
    st.session_state["qtde_origens"] = 1
if "qtde_destinos" not in st.session_state:
    st.session_state["qtde_destinos"] = 1

# Carregamento dos dados de aeroportos para autocomplete
@st.cache_data
def load_airports():
    try:
        # Carrega o CSV assumindo que ele está no mesmo diretório
        df = pd.read_csv("airports.csv")
        
        # Remove entradas que não tenham código IATA ou Cidade definidos
        df = df.dropna(subset=['IATA', 'City', 'Airport name'])
        
        # Cria uma string formatada para facilitar a busca: "Cidade (IATA) - Aeroporto"
        df['Display'] = df.apply(
            lambda x: f"{str(x['City']).strip()} ({str(x['IATA']).strip()}) - {str(x['Airport name']).strip()}", 
            axis=1
        )
        
        # Retorna a lista ordenada para o selectbox
        return sorted(df['Display'].unique().tolist())
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de aeroportos (airports.csv): {e}")
        return []

# Carregamento do banco de dados de coordenadas
@st.cache_data
def load_coordinates():
    try:
        with open("coord.csv", "r") as f:
            content = f.read()
            if "coords =" in content:
                content = content.replace("coords =", "").strip()
            return ast.literal_eval(content)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo de coordenadas (coord.csv): {e}")
        return {}

# Carrega a lista uma única vez
airport_options = load_airports()

def extrair_iata(texto_aeroporto: str) -> str:
    """Extrai o código IATA de uma string."""
    if not texto_aeroporto:
        return ""
    try:
        inicio = texto_aeroporto.index("(") + 1
        fim = texto_aeroporto.index(")")
        return texto_aeroporto[inicio:fim]
    except ValueError:
        return texto_aeroporto[:3].upper()

def mapear_prioridade(peso: str) -> int:
    """Converte o texto de prioridade para o valor numérico."""
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
    adultos = col_a.number_input("Adultos", 1, 6, 1)
    criancas = col_c.number_input("Crianças", 0, 5, 0)
    
    st.markdown("### 📅 Datas")
    data_inicio = st.date_input("Data Início", value=date(2026, 2, 5), format="DD/MM/YYYY")
    
    ida_e_volta = st.toggle("Ida e Volta", value=True)
    
    data_volta = data_inicio + timedelta(days=7)
    
    alugar_carro = False
    buscar_hoteis_toggle = False

    if ida_e_volta:
        data_volta = st.date_input("Data de Volta", value=data_inicio + timedelta(days=7), format="DD/MM/YYYY")
        alugar_carro = st.toggle("Alugar Carro", value=False)
        buscar_hoteis_toggle = st.toggle("Buscar Hotéis", value=True)
    
    st.markdown("---")
    st.markdown("### 📍 Roteiro")
    
    # --- MODIFICAÇÃO 1: Origens Dinâmicas ---
    lista_origens_selecionadas = []
    
    st.markdown("**Origem(ns)**")
    for i in range(st.session_state["qtde_origens"]):
        # Tenta definir um padrão apenas para o primeiro
        idx_padrao = None
        if i == 0 and airport_options:
            for idx, opt in enumerate(airport_options):
                if "GRU" in opt and "São Paulo" in opt:
                    idx_padrao = idx
                    break
        
        origem = st.selectbox(
            f"Origem {i+1}", 
            options=airport_options, 
            index=idx_padrao if i == 0 else None,
            key=f"origem_{i}",
            label_visibility="collapsed"
        )
        if origem:
            lista_origens_selecionadas.append(origem)

    # Botões de Adicionar/Remover Origem
    col_add_org, col_rem_org = st.columns(2)
    with col_add_org:
        if st.button("➕ Adicionar Origem"):
            st.session_state["qtde_origens"] += 1
            st.rerun()
    with col_rem_org:
        if st.session_state["qtde_origens"] > 1:
            if st.button("➖ Remover Origem"):
                st.session_state["qtde_origens"] -= 1
                st.rerun()

    st.markdown("") # Espaçamento

    # --- MODIFICAÇÃO 2: Destinos Dinâmicos ---
    lista_destinos_selecionados = []
    
    st.markdown("**Destino(s)**")
    for i in range(st.session_state["qtde_destinos"]):
        # Tenta definir um padrão apenas para o primeiro
        idx_padrao_dest = None
        if i == 0 and airport_options:
            for idx, opt in enumerate(airport_options):
                if "MIA" in opt and "Miami" in opt:
                    idx_padrao_dest = idx
                    break

        destino = st.selectbox(
            f"Destino {i+1}", 
            options=airport_options, 
            index=idx_padrao_dest if i == 0 else None,
            key=f"destino_{i}",
            label_visibility="collapsed"
        )
        if destino:
            lista_destinos_selecionados.append(destino)

    # Botões de Adicionar/Remover Destino
    col_add_dest, col_rem_dest = st.columns(2)
    with col_add_dest:
        if st.button("➕ Adicionar Destino"):
            st.session_state["qtde_destinos"] += 1
            st.rerun()
    with col_rem_dest:
        if st.session_state["qtde_destinos"] > 1:
            if st.button("➖ Remover Destino"):
                st.session_state["qtde_destinos"] -= 1
                st.rerun()
    
    # --- MODIFICAÇÃO 7: Campo Cidades Obrigatórias removido ---
    
    st.markdown("---")
    st.markdown("### ⚖️ Prioridade")
    peso = st.select_slider(
        "Prioridade",
        options=["Menor Preço", "Equilibrado", "Mais Rápido"],
        value="Equilibrado"
    )
    
    btn_otimizar = st.button("✨ OTIMIZAR VIAGEM", use_container_width=True, type="primary")

# Variáveis principais para uso no restante do código (usando o primeiro selecionado como referência principal)
origens = lista_origens_selecionadas[0] if lista_origens_selecionadas else None
destinos = lista_destinos_selecionados[0] if lista_destinos_selecionados else None

# Lógica de integração com o backend
if btn_otimizar:
    if not origens or not destinos:
        st.error("⚠️ Selecione pelo menos uma origem e um destino antes de otimizar.")
    else:
        iata_origem = extrair_iata(origens)
        iata_destino = extrair_iata(destinos)
        
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
        
        with st.spinner("🔍 Buscando voos... Isso pode levar alguns segundos."):
            try:
                resultado = chamar_backend(payload)
                st.session_state["resultado_busca"] = resultado
                st.session_state["busca_realizada"] = True
                st.success(f"✅ Encontrados {resultado.get('total_voos', 0)} voos!")
            except requests.exceptions.ConnectionError:
                # Fallback para demonstração se a API não estiver rodando
                st.session_state["busca_realizada"] = True
                st.warning("⚠️ Modo de demonstração (API offline)")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
                # Fallback
                st.session_state["busca_realizada"] = True

# 4. PAINEL PRINCIPAL
st.title("🚀 Roteiro Inteligente")
st.caption(f"Exibindo melhor rota para {origens} ➔ {destinos} com foco em {peso}")

# Métricas
m1, m2, m3, m4 = st.columns(4)

if "busca_realizada" in st.session_state:
    resultado = st.session_state.get("resultado_busca", {})
    opt_result = resultado.get("optimization_result", {})
    
    preco_formatado = opt_result.get("total_cost_formatted", "R$ 3.250,00")
    duracao_formatada = opt_result.get("total_duration_formatted", "11h 08min")
    total_voos = resultado.get("total_voos", len(resultado.get("voos", [])))
    
    m1.metric("💰 Melhor Preço", preco_formatado)
    m2.metric("✈️ Total de Opções", total_voos if total_voos else "4")
    m3.metric("⏱️ Menor Duração", duracao_formatada)
    m4.metric("📊 Status", "✅ Otimizado")
    
    # Exibir card de resultado da otimização
    if resultado and resultado.get("status") == "success":
        st.markdown("---")
        st.subheader("🎯 Resultado da Otimização")
        
        voo_otimizado = resultado.get("voo_otimizado", {})
        weights = resultado.get("weights", {})
        
        # Card principal do voo otimizado
        with st.container():
            col_opt1, col_opt2, col_opt3 = st.columns([2, 2, 1])
            
            with col_opt1:
                st.markdown("##### 🏆 Voo Recomendado")
                st.markdown(f"**Companhia:** {voo_otimizado.get('companhia', 'N/A')}")
                st.markdown(f"**Preço:** {voo_otimizado.get('preco', 'N/A')}")
                
                if voo_otimizado.get("is_pareto_optimal"):
                    st.success("✨ Solução Pareto-Ótima")
            
            with col_opt2:
                st.markdown("##### 📈 Métricas do Solver")
                st.markdown(f"**Algoritmo:** `{resultado.get('solver', 'NSGA-II')}`")
                st.markdown(f"**Prioridade:** {resultado.get('priority_label', 'Equilibrado')}")
                
                # Barra de pesos
                peso_custo = weights.get("cost", 0.5)
                peso_tempo = weights.get("time", 0.5)
                st.markdown(f"**Pesos:** 💵 Custo: `{peso_custo:.0%}` | ⏱️ Tempo: `{peso_tempo:.0%}`")
            
            with col_opt3:
                st.markdown("##### 🎲 Fitness")
                fitness = opt_result.get("fitness_score", 0)
                pareto_rank = opt_result.get("pareto_rank", 1)
                st.metric("Score", f"{fitness:.4f}")
                st.metric("Rank Pareto", f"#{pareto_rank}")
        
        # Motivo da otimização em expander
        motivo = voo_otimizado.get("motivo_otimizacao", "")
        if motivo:
            with st.expander("ℹ️ Por que esta opção foi selecionada?"):
                st.info(motivo)

else:
    m1.metric("💰 Preço Otimizado", "R$ --", "Aguardando busca")
    m2.metric("✈️ Total de Voos", "--")
    m3.metric("⏱️ Duração", "--")
    m4.metric("📊 Status", "⏳ Pendente")

st.markdown("---")

# --- MODIFICAÇÃO 4, 5 e 6: Controle Dinâmico das Abas ---
lista_abas = ["📋 Itinerários"]
if buscar_hoteis_toggle:
    lista_abas.append("🏨 Hotéis Encontrados")
if alugar_carro:
    lista_abas.append("🚗 Aluguel de Carros")

abas_criadas = st.tabs(lista_abas)

# Mapeamento das abas para variáveis para fácil acesso
tab_rota = abas_criadas[0]
tab_hoteis = None
tab_carros = None

# Identifica qual aba é qual baseado na ordem de criação
idx_atual = 1
if buscar_hoteis_toggle:
    tab_hoteis = abas_criadas[idx_atual]
    idx_atual += 1
if alugar_carro:
    tab_carros = abas_criadas[idx_atual]


with tab_rota:
    coords = load_coordinates()

    # --- MODIFICAÇÃO 3: Lógica de Pares (Ida e Volta) ---
    if st.session_state.get("busca_realizada"):
        iata_o = extrair_iata(origens)
        iata_d = extrair_iata(destinos)
        
        if ida_e_volta:
            # Criação de dados em PARES (Linha N: Ida, Linha N+1: Volta)
            data_voos = {
                "Tipo": ["IDA", "VOLTA", "IDA", "VOLTA"],
                "Cia Aérea": ["Copa Airlines", "Copa Airlines", "LATAM", "LATAM"],
                "Rota": [
                    f"{iata_o} ➔ {iata_d}", 
                    f"{iata_d} ➔ {iata_o}",
                    f"{iata_o} ➔ {iata_d}",
                    f"{iata_d} ➔ {iata_o}"
                ],
                "Partida": [
                    f"01:30 ({data_inicio.strftime('%d/%m')})",
                    f"15:00 ({data_volta.strftime('%d/%m')})",
                    f"19:40 ({data_inicio.strftime('%d/%m')})",
                    f"08:20 ({data_volta.strftime('%d/%m')})"
                ],
                "Chegada": [
                    f"10:38 ({data_inicio.strftime('%d/%m')})",
                    f"00:15 ({(data_volta + timedelta(days=1)).strftime('%d/%m')})",
                    f"05:15 ({(data_inicio + timedelta(days=1)).strftime('%d/%m')})",
                    f"18:40 ({data_volta.strftime('%d/%m')})"
                ],
                "Duração": ["11h 08min", "11h 15min", "12h 35min", "12h 20min"],
                "Detalhes": ["1 parada", "1 parada", "1 parada", "1 parada"],
                "Conexões": [
                    "Panamá (PTY)", 
                    "Panamá (PTY)", 
                    "Lima (LIM)", 
                    "Lima (LIM)"
                ],
                "Preço Total": ["R$ 3.250,00 (Par)", "", "R$ 3.540,00 (Par)", ""]
            }
        else:
            # Apenas Ida
            data_voos = {
                "Tipo": ["IDA", "IDA", "IDA", "IDA"],
                "Cia Aérea": ["Copa Airlines", "Avianca", "LATAM", "Delta"],
                "Rota": [f"{iata_o} ➔ {iata_d}"] * 4,
                "Partida": [
                    f"01:30 ({data_inicio.strftime('%d/%m')})",
                    f"06:05 ({data_inicio.strftime('%d/%m')})",
                    f"19:40 ({data_inicio.strftime('%d/%m')})",
                    f"22:50 ({data_inicio.strftime('%d/%m')})"
                ],
                "Chegada": ["10:38", "17:20", "05:15 (+1)", "09:30 (+1)"],
                "Duração": ["11h 08m", "13h 15m", "12h 35m", "14h 40m"],
                "Detalhes": ["1 parada", "1 parada", "1 parada", "1 parada"],
                "Conexões": ["Panamá (PTY)", "Bogotá (BOG)", "Lima (LIM)", "Atlanta (ATL)"],
                "Preço Total": ["R$ 1.800", "R$ 1.950", "R$ 2.100", "R$ 2.400"]
            }

        df_rota = pd.DataFrame(data_voos)

        st.info("👇 Clique na tabela para visualizar a rota. Em caso de Ida/Volta, os voos são exibidos em pares sequenciais.")

        event = st.dataframe(
            df_rota,
            use_container_width=True,
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-row"
        )

        rows = event.selection.rows
        selected_index = rows[0] if rows else 0
        
        rota_selecionada = df_rota.iloc[selected_index]
        conexao_texto = rota_selecionada["Conexões"]
        cia_selecionada = rota_selecionada["Cia Aérea"]
        rota_str = rota_selecionada["Rota"]

        # Mapa Dinâmico
        st.subheader(f"Visualização: {cia_selecionada} ({rota_str})")
        
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

        ponto_conexao = None
        if "PTY" in conexao_texto and "PTY" in coords: ponto_conexao = coords["PTY"]
        elif "BOG" in conexao_texto and "BOG" in coords: ponto_conexao = coords["BOG"]
        elif "LIM" in conexao_texto and "LIM" in coords: ponto_conexao = coords["LIM"]
        elif "ATL" in conexao_texto and "ATL" in coords: ponto_conexao = coords["ATL"]

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
    else:
        st.info("Realize uma busca para ver os itinerários.")


if tab_hoteis:
    with tab_hoteis:
        st.subheader(f"Melhores opções em {destinos}")
        hoteis_fake = [
            {
                "nome": "Miami Beach Grand Resort",
                "preco": "R$ 1.250",
                "nota": "4.8",
                "img": "https://images.unsplash.com/photo-1561501900-3701fa6a0864?w=600",
                "desc": "Vista para o mar, café da manhã incluso."
            },
            {
                "nome": "Downtown Modern Suite",
                "preco": "R$ 890",
                "nota": "4.5",
                "img": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400",
                "desc": "Localizado no centro financeiro."
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
                    st.write(f"Preço: {hotel['preco']}/noite")
                    st.button(f"Reservar {hotel['nome']}", key=hotel['nome'])
                st.divider()

# --- MODIFICAÇÃO 5: Conteúdo da Aba Carros ---
if tab_carros:
    with tab_carros:
        st.subheader(f"Opções de Veículos em {destinos}")
        carros_fake = [
            {"modelo": "Tesla Model 3", "cat": "Premium", "preco": "R$ 450/dia", "img": "https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=400"},
            {"modelo": "Toyota RAV4", "cat": "SUV", "preco": "R$ 320/dia", "img": "https://images.unsplash.com/photo-1706509234538-9831b1b33d66?q=80&w=1742&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"},
            {"modelo": "Ford Mustang Convertible", "cat": "Esportivo", "preco": "R$ 580/dia", "img": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400"},
        ]
        
        cols = st.columns(3)
        for idx, carro in enumerate(carros_fake):
            with cols[idx]:
                st.image(carro["img"], use_container_width=True)
                st.markdown(f"**{carro['modelo']}**")
                st.caption(carro['cat'])
                st.write(f"💰 {carro['preco']}")
                st.button("Alugar", key=f"car_{idx}")

st.markdown('<div class="footer">Gerado por Smart Travel AI © 2026</div>', unsafe_allow_html=True)