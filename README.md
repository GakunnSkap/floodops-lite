# FloodOps Lite

Prototipo educativo desarrollado para IEEE-HKN Hack2Impact 2026. Su objetivo es
explorar la asignación de recursos limitados ante escenarios de inundación en
Guayaquil, Ecuador.

La aplicación muestra únicamente el nombre y la descripción del proyecto.
El repositorio incluye un escenario simulado, todavía sin optimización ni mapas.
No es un sistema operativo de emergencias ni una herramienta validada para tomar
decisiones de respuesta.

## Ejecución local

Requiere Python 3.13 y las dependencias de `requirements.txt`. Desde la carpeta
del repositorio, en la computadora preparada para el evento, utilizar el entorno
existente, sin reinstalar paquetes:

```bash
source "$HOME/.venvs/hackathon-tools-py313/bin/activate"
python -m streamlit run app.py
```

Abrir la dirección local indicada por Streamlit, normalmente
http://localhost:8501. Para detenerlo, pulsar Ctrl+C en la terminal.

En otra computadora con Python 3.13, crear un entorno e instalar dependencias:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Escenario educativo

`data.py` ofrece `get_scenario()`, que devuelve datos nuevos en cada llamada,
y `validate_scenario(scenario)`, que lanza `ValueError` ante datos inválidos.
El diccionario contiene `simulated`, `zones`, `teams` y `costs`.

Las cuatro zonas y los dos equipos son ficticios, sin coordenadas ni información
operativa real. Cada zona tiene `id`, `name`, `priority` y `penalty`; cada equipo
tiene `id`, `name` y `available`. Las prioridades son 1 (baja), 2 (media) y 3
(alta). Dejar una zona pendiente penaliza con 100 veces su prioridad.

La matriz `costs` tiene filas en el orden de `teams` y columnas en el orden de
`zones`. Un número representa esfuerzo de asignación sintético: menor es mejor.
No representa minutos, distancia ni dinero. `None` significa asignación
incompatible y debe tratarse como prohibición, nunca como costo cero.
La disponibilidad del equipo se comprueba por separado.

El modelo previsto tiene una sola ronda: cada equipo atiende como máximo una
zona y cada zona recibe como máximo un equipo. Las zonas pendientes son
explícitas en el objetivo previsto: sumar costos de asignaciones realizadas y
penalizaciones de zonas sin atender. Ambos usan la misma escala artificial;
la prioridad es una preferencia mediante penalización, no una garantía absoluta.
La escala elegida es un supuesto educativo que deberá revisarse antes de modelar.
Todavía no se calcula ninguna asignación ni se comprueban resultados de un solver.

Pruebas del escenario, desde el entorno activado:

```bash
python -m unittest -v test_data
```

## Asistencia de IA y terceros

Los participantes definen la idea y el alcance del proyecto, toman las decisiones
y revisan los resultados. Codex apoyó la investigación y preparación del entorno
antes del evento y la creación de esta base inicial durante el hackathon.
Esta versión utiliza Streamlit y no incluye datasets de terceros.
