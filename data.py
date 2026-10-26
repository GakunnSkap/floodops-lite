"""Escenario educativo sintético: no contiene datos operativos reales."""

from math import isfinite


def get_scenario():
    """Devuelve una copia nueva del escenario y comprueba su consistencia."""
    scenario = {
        "simulated": True,
        "zones": [
            {"id": "Z1", "name": "Zona simulada A", "priority": 3, "penalty": 300},
            {"id": "Z2", "name": "Zona simulada B", "priority": 2, "penalty": 200},
            {"id": "Z3", "name": "Zona simulada C", "priority": 1, "penalty": 100},
            {"id": "Z4", "name": "Zona simulada D", "priority": 3, "penalty": 300},
        ],
        "teams": [
            {"id": "E1", "name": "Equipo simulado 1", "available": True},
            {"id": "E2", "name": "Equipo simulado 2", "available": True},
        ],
        "costs": [[8, 4, 2, None], [6, 5, None, 12]],
    }
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario):
    """Rechaza entradas inconsistentes con ValueError; no calcula asignaciones."""
    if not isinstance(scenario, dict) or scenario.get("simulated") is not True:
        raise ValueError("El escenario debe identificarse como simulado.")

    for key in ("zones", "teams"):
        records = scenario.get(key)
        if not isinstance(records, list) or not records:
            raise ValueError(f"{key} debe ser una lista no vacía.")
        identifiers = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Cada elemento de {key} debe ser un diccionario.")
            identifier = record.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError(f"Identificador inválido en {key}.")
            if identifier in identifiers:
                raise ValueError(f"Identificador duplicado en {key}: {identifier}.")
            identifiers.add(identifier)
            name = record.get("name")
            if not isinstance(name, str) or "simulad" not in name.lower():
                raise ValueError("Cada nombre debe identificar su carácter simulado.")

    zones = scenario["zones"]
    teams = scenario["teams"]
    for zone in zones:
        priority = zone.get("priority")
        penalty = zone.get("penalty")
        if type(priority) is not int or priority not in (1, 2, 3):
            raise ValueError("La prioridad debe ser un entero entre 1 y 3.")
        if type(penalty) not in (int, float) or penalty != 100 * priority:
            raise ValueError("La penalización debe ser 100 por la prioridad.")
    for team in teams:
        if type(team.get("available")) is not bool:
            raise ValueError("La disponibilidad debe ser booleana.")

    costs = scenario.get("costs")
    if not isinstance(costs, list) or len(costs) != len(teams):
        raise ValueError("Debe existir una fila de costos por equipo.")
    for row in costs:
        if not isinstance(row, list) or len(row) != len(zones):
            raise ValueError("Debe existir una columna de costos por zona.")
        for cost in row:
            if cost is None:
                continue
            if type(cost) not in (int, float) or not isfinite(cost) or cost < 0:
                raise ValueError("Cada costo debe ser finito y no negativo, o None.")
