# Modelo compartido para web y Power BI

Los CSV de `data/estrella/` y `data/modelo_web.json` se generan juntos. El catálogo completo disponible se conserva; la proyección web selecciona menciones de Tacna. `data/manifest.json` informa alcance, cobertura y versión de reglas.

## Web

La web valida claves y puentes y reconstruye una fila por hecho. Universidad, año, madurez y búsqueda filtran esa selección. Los resúmenes completos siguen disponibles. El sitio nuevo utiliza JSON, no el CSV antiguo.

Los navegadores con DecompressionStream descargan `modelo_web.json.gz`; el resto usa JSON sin compresión. La estrella y los resúmenes son idénticos en ambas variantes. La compresión reduce transferencia sin eliminar búsqueda en el resumen.

En desarrollo: `python -m http.server 8765 --bind 127.0.0.1`, abrir `/docs/`. El metadato `datos-base` apunta a `../data/`. En el repositorio público, `docs/` contiene el sitio y ese metadato apunta al origen Raw público.

## Importar la estrella en Power BI Desktop

1. Crear una consulta en blanco `ModeloEstrella`, pegar `powerquery/ModeloEstrella.pq` y deshabilitar su carga.
2. Crear las consultas de referencia de `powerquery/dim_*.pq`, `fact_registro.pq` y los puentes cuando se necesiten. Usar los nombres de archivo como nombres de consulta.
3. Relacionar `dim_universidad[universidad_id]`, `dim_anio[anio_id]` y `dim_madurez[madurez_id]` con las columnas homónimas de `fact_registro`. Cardinalidad uno a varios; filtro desde dimensión hacia hecho.
4. Para detalle, relacionar `dim_registro[registro_id]` con `fact_registro[registro_id]`, ambos únicos.
5. Incorporar `dax/medidas_estrella.dax`. Usar `Registros_Tacna` para comparar universidades. El total histórico UNJBG filtrado no equivale a su catálogo completo.
6. Autores y materias se relacionan por ID con sus puentes, y los puentes con `dim_registro`. El filtro debe alcanzar el hecho mediante una relación bidireccional controlada por puente, o una medida con TREATAS. No activar ambas direcciones en todas las relaciones. Seleccionar dos autores del mismo estudio debe contar un registro.
7. `repositorio` describe procedencia. Evitar un segundo camino de filtros de universidad hacia el hecho a través de esa tabla.

Autores son menciones sin identidad ORCID verificada: un nombre igual no prueba que sea la misma persona. El año `0` indica desconocido; `dim_anio` no es un calendario diario. Las fechas originales y su precisión están en `dim_registro`.

El PBIX binario anterior no se reescribe automáticamente. Puede seguir leyendo `Investigaciones_web.pq` y medidas antiguas; la etiqueta heredada `Teorico` representa ausencia de señales. Para usar la estrella hay que incorporar las consultas y relaciones anteriores en Desktop y guardar el PBIX.

## Actualizar y reproducir

- En vivo: `python etl/main_oaipmh.py`. Un fallo de fuente impide el commit de nuevos datos.
- Sin red: `python etl/main_oaipmh.py --desde-json data/origen.json`.
- Pruebas: `python -m unittest discover -s tests -v` y `node tests/test_web.cjs`.
- Documentación: `python documentos/actualizar_modelo.py`, renderizar PlantUML, `python documentos/generar.py` y `python documentos/verificar.py`.

`Generar documentacion` ejecuta el proceso en el repositorio académico. En pull requests adjunta artefactos; en main versiona los documentos. `Validar modelo compartido` reproduce el modelo sin depender de las universidades y adjunta SQLite como artefacto; el binario SQLite no se versiona.
