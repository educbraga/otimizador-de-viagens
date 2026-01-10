"""
Crawler simples para buscar voos no Kayak
Usa Playwright para renderizar a página e BeautifulSoup para extrair dados.
"""

import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def gerar_url_kayak(dados):
    """
    Gera a URL de busca direta para o Kayak.
    
    Esperado 'dados':
    {
        "origem": "GRU",
        "destino": "MIA",
        "data_ida": "2026-02-05",  # String YYYY-MM-DD
        "data_volta": "2026-02-13", # String YYYY-MM-DD
        "ida_e_volta": True,
        "adultos": 1,
        "criancas": 0
    }
    """
    base_url = "https://www.kayak.com.br/flights"
    
    # 1. Monta a Rota
    rota = f"{dados['origem']}-{dados['destino']}"
    
    # 2. Monta as Datas
    datas = f"{dados['data_ida']}"
    if dados.get('ida_e_volta', True):
        datas += f"/{dados['data_volta']}"
        
    # 3. Monta Passageiros
    passageiros = ""
    if dados.get('adultos', 1) > 1:
        passageiros += f"/{dados['adultos']}adults"
    if dados.get('criancas', 0) > 0:
        passageiros += f"/{dados['criancas']}children"
        
    # URL Final com ordenação por menor preço
    url_final = f"{base_url}/{rota}/{datas}{passageiros}?sort=price_a"
    
    return url_final


def raspar_kayak(url, headless=False):
    """
    Acessa o Kayak e extrai os resultados de voos.
    
    Args:
        url: URL de busca do Kayak
        headless: Se True, roda sem abrir o navegador (pode ser bloqueado mais fácil)
    
    Returns:
        Lista de dicionários com os voos encontrados
    """
    html_content = None
    voos = []
    
    with sync_playwright() as p:
        print("🚀 Iniciando navegador...")
        
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Sao_Paulo'
        )
        
        page = context.new_page()
        
        print(f"🔗 Acessando: {url}")
        page.goto(url)
        
        # Delay para parecer humano
        time.sleep(random.uniform(3, 5))
        
        try:
            # Tenta fechar modal/popup se aparecer
            try:
                page.click('[aria-label="Fechar"]', timeout=3000)
            except:
                pass
            
            try:
                page.click('[aria-label="Close"]', timeout=2000)
            except:
                pass
            
            print("⏳ Aguardando resultados carregarem...")
            
            # Espera pelos resultados - tenta múltiplos seletores
            seletores = ['.nrc6-inner', '.resultWrapper', '[data-resultid]', '.Flights-Results-FlightResultItem']
            resultado_encontrado = False
            
            for sel in seletores:
                try:
                    page.wait_for_selector(sel, timeout=15000)
                    print(f"✅ Resultados encontrados com seletor: {sel}")
                    resultado_encontrado = True
                    break
                except:
                    continue
            
            if not resultado_encontrado:
                print("⚠️ Nenhum seletor padrão encontrado, tentando esperar mais...")
                time.sleep(5)
            
            # Scroll gradual para carregar lazy loading
            print("📜 Rolando página para carregar mais resultados...")
            for i in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(random.uniform(1, 2))
            
            # Espera final
            time.sleep(3)
            
            # Captura o HTML
            html_content = page.content()
            print("📄 HTML capturado!")
            
            # Faz o parsing
            voos = extrair_voos(html_content)
            print(f"✈️ {len(voos)} voos encontrados!")
            
        except Exception as e:
            print(f"❌ Erro ao carregar resultados: {e}")
        
        finally:
            browser.close()
            print("🔒 Navegador fechado.")
    
    return voos


def extrair_voos(html_content):
    """
    Extrai informações dos voos do HTML do Kayak.
    
    Returns:
        Lista de dicionários com dados dos voos
    """
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    voos = []
    
    # Tenta diferentes seletores que o Kayak usa
    resultados = soup.select('.nrc6-inner')
    
    if not resultados:
        resultados = soup.select('.resultWrapper')
    
    if not resultados:
        resultados = soup.select('[data-resultid]')
    
    for i, resultado in enumerate(resultados[:10]):  # Limita a 10 resultados
        try:
            # Preço
            preco_el = resultado.select_one('.f8F1-price-text, .price-text, .multibook-price-per-person')
            preco = preco_el.get_text(strip=True) if preco_el else "N/A"
            
            # Companhia aérea
            cia_el = resultado.select_one('.c_cgF-carrier, .codeshares-airline-names, .leg-carrier')
            companhia = cia_el.get_text(strip=True) if cia_el else "N/A"
            
            # Horários
            horarios_el = resultado.select('.vmXl-mod-variant-large, .departure-time, .depart-time')
            horarios = [h.get_text(strip=True) for h in horarios_el[:2]] if horarios_el else ["N/A", "N/A"]
            
            # Duração
            duracao_el = resultado.select_one('.xdW8, .duration, .segment-duration')
            duracao = duracao_el.get_text(strip=True) if duracao_el else "N/A"
            
            # Paradas
            paradas_el = resultado.select_one('.JWEO-stops-text, .stops-text')
            paradas = paradas_el.get_text(strip=True) if paradas_el else "N/A"
            
            voo = {
                'posicao': i + 1,
                'preco': preco,
                'companhia': companhia,
                'horario_partida': horarios[0] if len(horarios) > 0 else "N/A",
                'horario_chegada': horarios[1] if len(horarios) > 1 else "N/A",
                'duracao': duracao,
                'paradas': paradas
            }
            
            voos.append(voo)
            
        except Exception as e:
            print(f"Erro ao extrair voo {i}: {e}")
            continue
    
    return voos


def exibir_resultados(voos):
    """Exibe os resultados de forma formatada no terminal."""
    if not voos:
        print("\n😕 Nenhum voo encontrado.")
        return
    
    print("\n" + "="*60)
    print("✈️  RESULTADOS DA BUSCA")
    print("="*60)
    
    for voo in voos:
        print(f"""
#{voo['posicao']} - {voo['companhia']}
   💰 Preço: {voo['preco']}
   🕐 {voo['horario_partida']} → {voo['horario_chegada']}
   ⏱️  Duração: {voo['duracao']}
   🔄 Paradas: {voo['paradas']}
   {'-'*40}""")


# Execução direta para teste
if __name__ == "__main__":
    # Exemplo de uso
    dados_busca = {
        "origem": "GRU",
        "destino": "MIA",
        "data_ida": "2026-02-05",
        "data_volta": "2026-02-13",
        "ida_e_volta": True,
        "adultos": 1,
        "criancas": 0
    }
    
    print("🔍 Iniciando busca de voos...")
    print(f"   Rota: {dados_busca['origem']} → {dados_busca['destino']}")
    print(f"   Datas: {dados_busca['data_ida']} a {dados_busca['data_volta']}")
    print(f"   Passageiros: {dados_busca['adultos']} adulto(s), {dados_busca['criancas']} criança(s)")
    
    url = gerar_url_kayak(dados_busca)
    print(f"\n🔗 URL gerada: {url}\n")
    
    voos = raspar_kayak(url, headless=False)
    exibir_resultados(voos)
