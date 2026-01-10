"""
Crawler simples para buscar voos no Kayak
Usa Playwright para renderizar a página e BeautifulSoup para extrair dados.
"""

import json
import random
import time
from datetime import datetime
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


def salvar_json(voos, dados_busca, arquivo="resultados_voos.json"):
    """
    Salva os resultados em um arquivo JSON.
    
    Args:
        voos: Lista de voos encontrados
        dados_busca: Dados da busca original
        arquivo: Nome do arquivo de saída
    
    Returns:
        Caminho do arquivo salvo
    """
    resultado = {
        "busca": dados_busca,
        "data_execucao": datetime.now().isoformat(),
        "total_voos": len(voos),
        "voos": voos
    }
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Resultados salvos em: {arquivo}")
    return arquivo


def buscar_voos(dados_busca, salvar=True, arquivo="resultados_voos.json"):
    """
    Função principal para o backend consumir.
    
    Args:
        dados_busca: Dicionário com origem, destino, datas, etc.
        salvar: Se True, salva em arquivo JSON
        arquivo: Nome do arquivo de saída (se salvar=True)
    
    Returns:
        Dicionário com os resultados da busca
    
    Exemplo de uso:
        from crawler_kayak import buscar_voos
        
        dados = {
            "origem": "GRU",
            "destino": "MIA",
            "data_ida": "2026-02-05",
            "data_volta": "2026-02-13",
            "ida_e_volta": True,
            "adultos": 1,
            "criancas": 0
        }
        
        resultado = buscar_voos(dados, salvar=True)
        print(resultado['voos'])  # Lista de voos
    """
    url = gerar_url_kayak(dados_busca)
    voos = raspar_kayak(url, headless=False)
    
    resultado = {
        "busca": dados_busca,
        "url": url,
        "data_execucao": datetime.now().isoformat(),
        "total_voos": len(voos),
        "voos": voos
    }
    
    if salvar:
        salvar_json(voos, dados_busca, arquivo)
    
    return resultado


def carregar_json(arquivo="resultados_voos.json"):
    """
    Carrega resultados de um arquivo JSON salvo anteriormente.
    
    Args:
        arquivo: Caminho do arquivo JSON
    
    Returns:
        Dicionário com os dados salvos
    
    Exemplo de uso:
        from crawler_kayak import carregar_json
        
        dados = carregar_json('resultados_voos.json')
        for voo in dados['voos']:
            print(f"{voo['companhia']} - {voo['preco']}")
    """
    with open(arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    
    # Usa a função principal que retorna JSON
    resultado = buscar_voos(dados_busca, salvar=True)
    
    # Exibe no terminal
    exibir_resultados(resultado['voos'])
    
    # Mostra o JSON no terminal também
    print("\n📋 JSON gerado:")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
