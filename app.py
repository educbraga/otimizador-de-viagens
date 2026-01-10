import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta

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
    data_inicio = st.date_input("Data Início", value=date(2026, 2, 5))
    
    ida_e_volta = st.toggle("Ida e Volta", value=True)
    
    data_volta = data_inicio + timedelta(days=7)
    if ida_e_volta:
        data_volta = st.date_input("Data de Volta", value=data_inicio + timedelta(days=7))
    
    alugar_carro = st.toggle("Alugar Carro", value=False)
    buscar_hoteis_toggle = st.toggle("Buscar Hotéis", value=True)
    
    st.markdown("---")
    st.markdown("### 📍 Roteiro")
    origens = st.text_input("Origem", "São Paulo")
    destinos = st.text_input("Destino", "Miami")
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
    df_rota = pd.DataFrame({
        "Rota": ["São Paulo (GRU) ➔ Miami (MIA)"],
        "Detalhes": ["1 parada - Panamá (PTY)"],
        "Espera":["1h 35m"],
        "Cia Aérea": ["LATAM"],
        "Partida": [f"02:40 ({data_inicio.strftime('%d/%m/%y')})"],
        "Chegada": [f"06:35 ({data_inicio.strftime('%d/%m/%y')})"],
        "Duração": ["10h 35min"],
        "Preço": ["R$ 1.540,00"],
    })
    st.table(df_rota)
    st.info("💡 **Dica:** Esta rota economiza R$ 1.200 em relação ao voo direto.")

    st.subheader("Visualização da Rota")
    mapa = folium.Map(location=[10, -70], zoom_start=3, tiles="CartoDB positron")
    folium.PolyLine([[-23.5, -46.6], [9.0, -79.5], [25.7, -80.1]], color="#0066FF", weight=4).add_to(mapa)
    #folium.Marker([-23.5, -46.6], popup=origens).add_to(mapa)
    #folium.Marker([25.7, -80.1], popup=destinos).add_to(mapa)
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