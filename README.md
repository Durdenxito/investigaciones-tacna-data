# Investigaciones sobre Tacna: UNJBG y UPT

El sitio de GitHub Pages consume una estrella JSON validada y muestra una fila por registro, con filtros de universidad, año y señales textuales. Los metadatos originales son de los repositorios universitarios; no se descargan PDF.

- Sitio: https://durdenxito.github.io/investigaciones-tacna-data/
- Web: docs/.
- JSON compartido: data/modelo_web.json.
- Tablas relacionadas para Power BI: data/estrella/.
- Catálogo capturado antes del filtro: data/origen.json.
- Esquema, conteos y cobertura: data/manifest.json.
- Diccionario: [docs/modelo_datos.md](docs/modelo_datos.md).
- Consultas y relaciones Power BI: [docs/guia_estrella.md](docs/guia_estrella.md).

## Cobertura y límites

La captura integrada conserva 4016 registros de la selección histórica UNJBG y 5296 del catálogo UPT. De UPT, 3667 mencionan Tacna. El manifiesto conserva el alcance por fuente: los dos catálogos totales no son directamente comparables. La web compara selecciones bajo la misma regla de mención de Tacna, con fechas de captura distintas.

El modelo no fusiona autores por nombre ni registros por título. La ausencia de patrones se denomina Sin evidencia textual detectada. Los indicios de prototipo o producción no acreditan implementación real.

## Actualización

GitHub Actions intenta actualizar ambas fuentes los domingos a las 05:17 UTC, ante cambios de código en main y manualmente. Se exige completar ambas fuentes; cualquier fallo impide publicar datos parciales. UPT usa OAI-PMH y completa los identificadores faltantes mediante su listado y fichas HTML públicas, con pausas y reintentos limitados.

Las pruebas de pull request y de rama reconstruyen la captura guardada sin depender de las universidades. SQLite se genera localmente y se adjunta como artefacto de CI; no se versiona su binario.

## Reproducir

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python etl/main_oaipmh.py --desde-json data/origen.json
node tests/test_web.cjs
```

Para recolectar en vivo: python etl/main_oaipmh.py.

El CSV antiguo data/investigaciones_tacna.csv conserva ocho columnas y las etiquetas heredadas para el PBIX anterior. El sitio nuevo consume JSON y los modelos nuevos de Power BI deben usar la estrella y dax/medidas_estrella.dax. El PBIX binario y la documentación académica se mantienen en el repositorio académico; no se publica aquí información de portadas.
