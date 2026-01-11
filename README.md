# Otimizador de Viagens

![Logo](images/logo1.png)

Uma plataforma para otimização de itinerários de viagem, focada em busca e comparação de voos aéreos utilizando dados coletados de fontes online.

## 📋 Descrição

O Otimizador de Viagens é um sistema que ajuda usuários a planejar viagens de forma inteligente, integrando um crawler para coleta de dados de voos do Kayak e uma interface web para visualização e otimização de rotas. O projeto combina técnicas de web scraping, APIs REST e uma interface interativa para fornecer uma experiência completa de planejamento de viagem.

## ✨ Funcionalidades

- **Busca de Voos**: Coleta automática de opções de voos através de web scraping no Kayak
- **Interface Web**: Aplicação Streamlit para entrada de dados e visualização de resultados
- **API Backend**: Serviço FastAPI para processamento de solicitações de otimização
- **Suporte a Múltiplos Destinos**: Possibilidade de planejar rotas complexas
- **Visualização de Mapas**: Integração com Folium para mapas interativos
- **Dados de Aeroportos**: Base de dados com códigos IATA e coordenadas

## 🛠️ Instalação

### Pré-requisitos
- Python 3.8 ou superior
- Pip (gerenciador de pacotes Python)

### Passos de Instalação

1. **Clone o repositório** (se aplicável) ou navegue até o diretório do projeto

2. **Crie um ambiente virtual**:
   ```bash
   python3 -m venv venv
   # ou
   python -m venv venv
   ```

3. **Ative o ambiente virtual**:
   ```bash
   source venv/bin/activate
   # No Windows: .\venv\Scripts\activate
   ```

4. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Instale o navegador Chromium para o Playwright**:
   ```bash
   playwright install chromium
   ```

## 🚀 Uso

### Executando o Sistema

O sistema é composto por três componentes principais que podem ser executados separadamente:

1. **Backend API (FastAPI)**:
   ```bash
   uvicorn main:app --reload
   ```
   A API estará disponível em `http://localhost:8000`

2. **Interface Web (Streamlit)**:
   ```bash
   streamlit run app.py
   ```
   A interface estará disponível em `http://localhost:8501`

3. **Crawler (opcional - para testes manuais)**:
   ```bash
   python crawler_kayak.py
   ```

### Como Usar

1. Abra a interface Streamlit no navegador
2. Insira os detalhes da viagem (origem, destino, datas, passageiros)
3. Clique em "Buscar Voos" para obter opções otimizadas
4. Visualize os resultados em formato de tabela e mapa

## 📁 Estrutura do Projeto

```
otimizador-de-viagens/
├── app.py                 # Interface web Streamlit
├── main.py                # API backend FastAPI
├── crawler_kayak.py       # Crawler para coleta de dados do Kayak
├── requirements.txt       # Dependências Python
├── airports.csv          # Base de dados de aeroportos
├── coord.csv             # Coordenadas geográficas
├── resultados_voos.json  # Cache de resultados (opcional)
├── LICENSE               # Licença do projeto
└── README.md             # Este arquivo
```

## 👥 Equipe

Este projeto foi desenvolvido por:

- **Eduardo Braga**
- **Israel Magalhães**
- **Marcelo Carvalho**

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🔧 Tecnologias Utilizadas

- **Backend**: FastAPI, Python
- **Frontend**: Streamlit, Folium, Plotly
- **Web Scraping**: Playwright, BeautifulSoup
- **Dados**: Pandas, CSV
- **APIs**: RESTful design

## 📞 Suporte

Para dúvidas ou sugestões, entre em contato com a equipe de desenvolvimento.
