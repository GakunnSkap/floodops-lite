# FloodOps Lite

Prototipo educativo de IEEE-HKN Hack2Impact 2026 sobre asignación de recursos
ante inundaciones en Guayaquil. Incluye un escenario sintético, una heurística
de referencia y un optimizador que se comparan en una aplicación Streamlit.
No es una herramienta validada para responder a emergencias.

## Ejecución

Desde la carpeta del repositorio, con Python 3.13 y el entorno preparado:

```bash
source "$HOME/.venvs/hackathon-tools-py313/bin/activate"
python -m streamlit run app.py
```

Abrir la dirección indicada, normalmente http://localhost:8501. Detener con Ctrl+C.
En la barra lateral se cambia la disponibilidad de equipos y la prioridad de cada
zona. La penalización sigue siendo `100 × prioridad`. Ambos métodos se recalculan
con las mismas entradas sin modificar los datos originales. La comparación muestra
asignaciones, zonas pendientes, costos y reducción del objetivo; un empate se
identifica expresamente y la reducción porcentual aparece como N/A si la referencia
cuesta cero. La interfaz está en inglés; los nombres conservan su etiqueta simulada.

La vista ilustrativa usa Vega-Lite nativo de Streamlit: cuadrados para equipos,
círculos para zonas y enlaces discontinuos para asignaciones. Un selector alterna
los métodos manteniendo las mismas posiciones. El color indica el estado y los
detalles aparecen al pasar el cursor. Es un esquema sin coordenadas geográficas,
rutas ni ubicaciones reales; evita asociar la simulación a barrios concretos.
No requiere Folium, teselas ni servicios cartográficos externos. Si no carga,
las tablas conservan toda la información de asignación.

En otra computadora, preparar el entorno antes de ejecutar Streamlit:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Datos y modelo

`data.get_scenario()` devuelve un diccionario nuevo con `simulated: True`,
`zones`, `teams` y `costs`. `validate_scenario()` rechaza datos inválidos con
`ValueError`. La etiqueta de simulación es obligatoria; los nombres solo deben
ser textos no vacíos.

Las cuatro zonas y los dos equipos son ficticios: no hay coordenadas ni datos
operativos reales. Las zonas tienen `id`, `name`, `priority` y `penalty`; los
equipos tienen `id`, `name` y `available`. La prioridad va de 1 (baja) a 3 (alta),
y la penalización por dejar una zona pendiente es `100 × prioridad`.
El contrato exige listas no vacías y no admite penalizaciones cero ni cambiar
la penalización sin mantener esa relación con la prioridad.

Las filas de `costs` siguen el orden de los equipos y las columnas el de las zonas.
Los números representan esfuerzo sintético, no minutos, distancias ni dinero.
`None` prohíbe una combinación; la disponibilidad se indica por separado.
Cada equipo puede atender como máximo una zona por ronda y cada zona recibir
como máximo un equipo.

El objetivo compartido es sumar costos de asignación y penalizaciones de zonas
pendientes. La escala es un supuesto educativo: priorizar mediante penalizaciones
no garantiza atender siempre las zonas de mayor prioridad.

## Referencia y pruebas

`baseline.greedy_assignment(scenario)` recorre zonas por penalización descendente
(desempate por identificador) y elige el equipo libre, disponible y compatible
más barato (desempate por identificador de equipo). Si no hay candidato, deja
la zona pendiente. Asigna incluso si el costo supera la penalización; es una
heurística y no garantiza el óptimo.

Sin modificar la entrada, devuelve `assignments` (pares `team_id` y `zone_id`),
`pending_zones`, `assignment_cost`, `pending_penalty` y `total_cost`.
El escenario inicial produce E2→Z1 y E1→Z2, con Z4 y Z3 pendientes:
**10 de asignación + 400 de penalización = 410**.

Desde el entorno activado, ejecutar todas las pruebas:

```bash
python -m unittest -v
```

## Optimización

`optimizer.optimal_assignment(scenario)` devuelve la misma estructura que la
referencia, sin modificar la entrada. Usa `scipy.optimize.linear_sum_assignment`
con una fila por zona y columnas para equipos disponibles y tantas opciones
ficticias como zonas. Una columna real cuesta el costo de asignación; una
ficticia cuesta la penalización de esa zona. Las incompatibilidades usan infinito,
no un costo grande arbitrario. Siempre existe una solución finita dejando todas
las zonas pendientes. Las columnas se usan como máximo una vez, por lo que los
equipos pueden quedar libres y las zonas reciben como máximo un equipo.

El óptimo inicial es E1→Z1 y E2→Z4, con Z2 y Z3 pendientes:
**20 + 300 = 320**. Frente a 410, reduce el costo objetivo un **21,95 %**;
no representa una reducción real de tiempos, daños o víctimas. Los empates pueden
tener varias soluciones óptimas. Las pruebas contrastan el valor con una
enumeración independiente, incluida una muestra reproducible de 100 escenarios
pequeños. La enumeración no forma parte del algoritmo de producción.

## Asistencia de IA y terceros

Los participantes definen la idea y el alcance, toman las decisiones y revisan
los resultados. Codex apoyó la investigación y preparación del entorno antes del
evento y la programación durante el hackathon. Se utilizan Streamlit y SciPy y no se
incluyen datasets de terceros.
