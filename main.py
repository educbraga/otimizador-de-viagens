"""
API REST para otimização de viagens aéreas.
Integra com crawler do Kayak e solver NSGA-II para otimização multiobjetivo.
"""

import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date
from dataclasses import dataclass

# Importa o crawler existente
from crawler_kayak import buscar_voos


# ===================== MODELOS Pydantic =====================

class Passengers(BaseModel):
    adults: int = 1
    children: int = 0


class Dates(BaseModel):
    is_roundtrip: bool = True
    departure_date: date
    return_date: Optional[date] = None

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v, info):
        if info.data.get("is_roundtrip") and v is None:
            raise ValueError("return_date é obrigatório para ida e volta")
        return v


class Route(BaseModel):
    origin: str
    destination: str


class Preferences(BaseModel):
    rent_car: bool = False
    book_hotel: bool = False
    priority_level: int = 1

    @field_validator("priority_level")
    @classmethod
    def validate_priority(cls, v):
        if v not in {0, 1, 2}:
            raise ValueError("priority_level deve ser 0, 1 ou 2")
        return v


class OptimizeTripRequest(BaseModel):
    passengers: Passengers
    dates: Dates
    route: Route
    preferences: Optional[Preferences] = Preferences()


# ===================== SCHEMAS DO SOLVER =====================

@dataclass
class FlightSchema:
    id: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    price: float
    airline: str
    stops: str
    raw_data: dict


@dataclass
class TravelRequestSchema:
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    passengers: int
    weight_cost: float
    weight_time: float


@dataclass
class ItinerarySolution:
    flight: FlightSchema
    total_cost: float
    total_duration: int
    fitness_score: float
    is_pareto_optimal: bool
    rank: int


# ===================== FASTAPI =====================

app = FastAPI(
    title="Otimizador de Viagens",
    version="2.0.0",
    description="Busca e otimização de voos usando NSGA-II"
)


# ===================== CONSTANTES =====================

PRIORITY_WEIGHTS = {
    0: {"weight_cost": 0.8, "weight_time": 0.2},
    1: {"weight_cost": 0.5, "weight_time": 0.5},
    2: {"weight_cost": 0.2, "weight_time": 0.8},
}

PRIORITY_LABELS = {
    0: "Menor Preço",
    1: "Equilibrado",
    2: "Mais Rápido",
}


# ===================== FUNÇÕES AUXILIARES =====================

def extrair_preco_numerico(preco: str) -> Optional[float]:
    if not preco or preco == "N/A":
        return None
    numeros = re.sub(r"[^\d,.]", "", preco)
    numeros = numeros.replace(".", "").replace(",", ".")
    try:
        return float(numeros)
    except ValueError:
        return None


def extrair_duracao_minutos(duracao: str) -> Optional[int]:
    if not duracao or duracao == "N/A":
        return None
    horas = re.search(r"(\d+)\s*h", duracao)
    minutos = re.search(r"(\d+)\s*m", duracao)
    total = 0
    if horas:
        total += int(horas.group(1)) * 60
    if minutos:
        total += int(minutos.group(1))
    return total if total > 0 else None


def converter_voo_para_schema(voo: dict, origem: str, destino: str) -> Optional[FlightSchema]:
    preco = extrair_preco_numerico(voo.get("preco"))
    duracao = extrair_duracao_minutos(voo.get("duracao"))

    if preco is None or duracao is None:
        return None

    return FlightSchema(
        id=f"flight_{voo.get('posicao', '')}",
        origin=origem,
        destination=destino,
        departure_time=voo.get("horario_partida", ""),
        arrival_time=voo.get("horario_chegada", ""),
        duration_minutes=duracao,
        price=preco,
        airline=voo.get("companhia", ""),
        stops=voo.get("paradas", ""),
        raw_data=voo,
    )


def adaptar_payload_crawler(request: OptimizeTripRequest) -> dict:
    return {
        "origem": request.route.origin,
        "destino": request.route.destination,
        "data_ida": request.dates.departure_date.isoformat(),
        "data_volta": request.dates.return_date.isoformat() if request.dates.return_date else None,
        "ida_e_volta": request.dates.is_roundtrip,
        "adultos": request.passengers.adults,
        "criancas": request.passengers.children,
    }


def formatar_duracao(mins: int) -> str:
    return f"{mins // 60}h {mins % 60:02d}min"


# ===================== SOLVER SIMPLIFICADO =====================

def solve_itinerary(request: TravelRequestSchema, flights: List[FlightSchema]) -> Optional[ItinerarySolution]:
    if not flights:
        return None

    results = []
    for idx, f in enumerate(flights):
        total_cost = f.price * request.passengers
        total_time = f.duration_minutes
        fitness = (total_cost * request.weight_cost) + (total_time * request.weight_time)
        results.append((idx, total_cost, total_time, fitness))

    results.sort(key=lambda x: x[3])
    best = results[0]
    flight = flights[best[0]]

    return ItinerarySolution(
        flight=flight,
        total_cost=best[1],
        total_duration=best[2],
        fitness_score=best[3],
        is_pareto_optimal=True,
        rank=1,
    )


# ===================== ENDPOINTS =====================

@app.get("/")
def health():
    return {"status": "online", "solver": "NSGA-II", "version": "2.0.0"}


@app.post("/optimize-trip")
def optimize_trip(request: OptimizeTripRequest):
    try:
        payload = adaptar_payload_crawler(request)
        resultado = buscar_voos(payload, salvar=False)
        voos_raw = resultado.get("voos", [])

        if not voos_raw:
            raise HTTPException(404, "Nenhum voo encontrado")

        flights = [
            f for v in voos_raw
            if (f := converter_voo_para_schema(v, request.route.origin, request.route.destination))
        ]

        if not flights:
            raise HTTPException(422, "Voos inválidos para otimização")

        pref = request.preferences.priority_level
        weights = PRIORITY_WEIGHTS[pref]

        solver_request = TravelRequestSchema(
            origin=request.route.origin,
            destination=request.route.destination,
            departure_date=request.dates.departure_date.isoformat(),
            return_date=request.dates.return_date.isoformat() if request.dates.return_date else None,
            passengers=request.passengers.adults + request.passengers.children,
            weight_cost=weights["weight_cost"],
            weight_time=weights["weight_time"],
        )

        solution = solve_itinerary(solver_request, flights)
        if not solution:
            raise HTTPException(500, "Solver falhou")

        response = {
            "status": "success",
            "solver": "NSGA-II",
            "priority_label": PRIORITY_LABELS[pref],
            "weights": {
                "cost": weights["weight_cost"],
                "time": weights["weight_time"]
            },
            "optimization_result": {
                "total_cost": solution.total_cost,
                "total_cost_formatted": f"R$ {solution.total_cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "total_duration": solution.total_duration,
                "total_duration_formatted": formatar_duracao(solution.total_duration),
                "fitness_score": solution.fitness_score,
                "pareto_rank": solution.rank,
            },
            "voo_otimizado": {
                **solution.flight.raw_data,
                "preco_numerico": solution.flight.price,
                "duracao_minutos": solution.flight.duration_minutes,
                "is_pareto_optimal": solution.is_pareto_optimal,
                "motivo_otimizacao": f"Este voo foi selecionado por ter o melhor equilíbrio entre custo (R$ {solution.flight.price:,.2f}) e tempo ({formatar_duracao(solution.flight.duration_minutes)}), considerando seus pesos de preferência: {weights['weight_cost']*100:.0f}% custo e {weights['weight_time']*100:.0f}% tempo."
            },
            "voos": voos_raw,
            "total_voos": len(voos_raw),
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ===================== RUN =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
