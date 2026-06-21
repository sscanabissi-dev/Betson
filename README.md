# Dashboard de Interacciones Betsson

Dashboard automatizado en Streamlit para monitorear en tiempo casi real la hoja `BBDD_INTERACCIONES`, cruzarla con la base de agentes `BBDD_ARMY` y sumar el plan operativo de `CONTROL_DIARIO` y `PARTIDOS`.

## Que muestra

- Avance diario por persona contra una meta configurable.
- Cruce por numero de contacto entre interacciones y agentes.
- Ranking diario por persona o avance diario por Army mediante selector.
- Cumplimiento oficial de objetivos desde `CONTROL_DIARIO`.
- Calendario de partidos y acciones planeadas desde `PARTIDOS`.
- Agentes activos sin actividad en el periodo filtrado.
- Diagnostico de calidad: contactos sin registro, facturacion incompleta, Army por definir y diferencias de Army entre hojas.
- Total de interacciones, personas con actividad, cobertura de activos y porcentaje de cruce con `BBDD_ARMY`.
- Filtros por fecha, Army, estatus, cruce con agentes, tipo de participacion, evento, persona y numero de contacto.
- Tendencia por hora y desglose alternable por tipo de participacion, Army o eventos.
- Graficos con Apache ECharts embebido.
- Tablas interactivas con AgGrid: busqueda, filtros, ordenamiento, paginacion y descarga.
- KPIs compactos con iconos a color de Iconify.
- Logo y favicon locales en `assets/`.
- Tabla de interacciones cruzadas con link directo a la evidencia en Drive.
- Descarga CSV de los datos filtrados.
- Auto-refresh cada 60 segundos.

## Fuente de datos

La app lee estas hojas publicas:

```text
https://docs.google.com/spreadsheets/d/1bA5QldI-H0S449F2p0T0XJOhDFcLllbV6HuMSEPNk2E/gviz/tq?tqx=out:csv&sheet=BBDD_INTERACCIONES
https://docs.google.com/spreadsheets/d/1bA5QldI-H0S449F2p0T0XJOhDFcLllbV6HuMSEPNk2E/gviz/tq?tqx=out:csv&sheet=BBDD_ARMY
https://docs.google.com/spreadsheets/d/1bA5QldI-H0S449F2p0T0XJOhDFcLllbV6HuMSEPNk2E/gviz/tq?tqx=out:csv&sheet=CONTROL_DIARIO
https://docs.google.com/spreadsheets/d/1bA5QldI-H0S449F2p0T0XJOhDFcLllbV6HuMSEPNk2E/gviz/tq?tqx=out:csv&sheet=PARTIDOS
```

Para que funcione en Streamlit Community Cloud, el Google Sheet debe mantenerse como `Cualquier persona con el enlace: Lector`.

## Ejecutar localmente

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Subir a GitHub

```bash
git init
git add .
git commit -m "Add Betsson interactions dashboard"
git branch -M main
git remote add origin https://github.com/<usuario>/<repositorio>.git
git push -u origin main
```

## Desplegar en Streamlit Community Cloud

1. Entra a https://share.streamlit.io/.
2. Selecciona el repositorio de GitHub.
3. En `Main file path`, usa `app.py`.
4. Despliega. No necesitas configurar secrets mientras la hoja siga publica.

## Configuracion opcional

Si mas adelante cambia la URL de la hoja, puedes agregar este secret en Streamlit Cloud:

```toml
GOOGLE_SHEET_INTERACTIONS_CSV_URL = "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/gviz/tq?tqx=out:csv&sheet=BBDD_INTERACCIONES"
GOOGLE_SHEET_ARMY_CSV_URL = "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/gviz/tq?tqx=out:csv&sheet=BBDD_ARMY"
GOOGLE_SHEET_DAILY_CONTROL_CSV_URL = "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/gviz/tq?tqx=out:csv&sheet=CONTROL_DIARIO"
GOOGLE_SHEET_MATCHES_CSV_URL = "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/gviz/tq?tqx=out:csv&sheet=PARTIDOS"
```

## Assets

El logo y el favicon estan guardados localmente en `assets/` para que el despliegue no dependa de una imagen externa. El SVG proviene de Wikimedia Commons: `File:Betsson AB Logo.svg`.
