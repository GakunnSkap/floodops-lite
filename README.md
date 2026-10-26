# FloodOps Lite

Prototipo educativo desarrollado para IEEE-HKN Hack2Impact 2026. Su objetivo es
explorar la asignación de recursos limitados ante escenarios de inundación en
Guayaquil, Ecuador.

Esta versión inicial muestra únicamente el nombre y la descripción del proyecto.
Todavía no incluye escenarios, optimización ni mapas. No es un sistema operativo
de emergencias ni una herramienta validada para tomar decisiones de respuesta.

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

## Asistencia de IA y terceros

Se utilizó Codex para investigación y diagnóstico previos al evento, preparación
del entorno y asistencia en la creación de esta base inicial durante el evento.
Las decisiones y los resultados son revisados por el participante humano. El uso
de IA y los componentes incorporados se documentarán conforme a las reglas del
hackathon. Esta versión utiliza Streamlit; no incluye datasets de terceros.
