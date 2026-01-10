# Otimizador de viagens

# 1. Criar ambiente virtual Python

python -m venv venv

# 2. Ativar o ambiente virtual

source venv/bin/activate

Se Windows: .\venv\Scripts\activate

# 3. Instalar as dependências

pip install -r requirements.txt

# 4. Instalar o navegador Chromium do Playwright

playwright install chromium

# 5. Rodar o crawler (opcional)

python crawler_kayak.py

# 6. Rodar o Frontend com Streamlit

streamlit run app.py

# 7. Iniciar o Backend

uvicorn main:app --reload

## 📄 Licença

Este projeto está sob a licença MIT
