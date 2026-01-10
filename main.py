"""
API REST simples para otimização de viagens aéreas.
Integra com o crawler existente do Kayak.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date

# Importa a função do crawler existente
from crawler_kayak import buscar_voos


# ============== Modelos Pydantic ==============

class Passengers(BaseModel):
    adults: int = 1
    children: int = 0


class Dates(BaseModel):
    is_roundtrip: bool = True
    departure_date: date
    return_date: Optional[date] = None

    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v, info):
        """Valida que return_date existe se is_roundtrip=True"""
        if info.data.get('is_roundtrip') and v is None:
            raise ValueError('return_date é obrigatório para viagens de ida e volta')
        return v


class Route(BaseModel):
    origin: str
    destination: str


class Preferences(BaseModel):
    rent_car: bool = False
    book_hotel: bool = False
    priority_level: int = 1

    @field_validator('priority_level')
    @classmethod
    def validate_priority(cls, v):
        """Valida que priority_level está em {0, 1, 2}"""
        if v not in {0, 1, 2}:
            raise ValueError('priority_level deve ser 0, 1 ou 2')
        return v


class OptimizeTripRequest(BaseModel):
    passengers: Passengers
    dates: Dates
    route: Route
    preferences: Optional[Preferences] = None


# ============== Aplicação FastAPI ==============

app = FastAPI(
    title="Otimizador de Viagens",
    description="API para busca otimizada de voos aéreos",
    version="1.0.0"
)


# ============== Funções Auxiliares ==============

def adaptar_payload(request: OptimizeTripRequest) -> dict:
    """
    Converte o payload da API para o formato esperado pelo crawler.
    
    API format -> Crawler format
    """
    return {
        "origem": request.route.origin,
        "destino": request.route.destination,
        "data_ida": request.dates.departure_date.isoformat(),
        "data_volta": request.dates.return_date.isoformat() if request.dates.return_date else None,
        "ida_e_volta": request.dates.is_roundtrip,
        "adultos": request.passengers.adults,
        "criancas": request.passengers.children
    }


# Mapeamento de cidades para IATA (preparado para expansão futura)
CIDADE_PARA_IATA = {
    "são paulo": "GRU",
    "sao paulo": "GRU",
    "miami": "MIA",
    "nova york": "JFK",
    "new york": "JFK",
    "orlando": "MCO",
    "los angeles": "LAX",
    "rio de janeiro": "GIG",
    "brasilia": "BSB",
}


def converter_cidade_para_iata(cidade: str) -> str:
    """
    Converte nome de cidade para código IATA.
    Se já for um código IATA (3 letras), retorna como está.
    """
    # Se já é código IATA (3 letras maiúsculas)
    if len(cidade) == 3 and cidade.isalpha():
        return cidade.upper()
    
    # Tenta converter de nome para IATA
    cidade_lower = cidade.lower().strip()
    return CIDADE_PARA_IATA.get(cidade_lower, cidade.upper())


# ============== Endpoints ==============

@app.get("/")
def root():
    """Endpoint de health check"""
    return {"status": "online", "service": "Otimizador de Viagens API"}


@app.post("/optimize-trip")
def optimize_trip(request: OptimizeTripRequest):
    """
    Busca voos otimizados com base nos parâmetros fornecidos.
    
    Recebe os dados da viagem, adapta para o formato do crawler,
    executa a busca e retorna os resultados.
    """
    try:
        # Adapta o payload para o formato do crawler
        dados_busca = adaptar_payload(request)
        
        # Chama o crawler (sem salvar arquivo)
        resultado = buscar_voos(dados_busca, salvar=False)
        
        return resultado
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar voos: {str(e)}"
        )


# ============== Para rodar diretamente ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)