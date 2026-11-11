# Modelo compartido para web y Power BI

Los CSV de `data/estrella/` y `data/modelo_web.json` se generan juntos. El catálogo completo disponible se conserva; la proyección web selecciona menciones de Tacna. `data/manifest.json` informa alcance, cobertura y versión de reglas.

## Web

La web valida claves y puentes y reconstruye una fila por hecho. Contiene seis reportes: panorama, evolución temporal, universidades, madurez, temas y catálogo. Universidad, año, mes, día, madurez y búsqueda filtran la misma selección en todos los reportes. Los resúmenes completos siguen disponibles. El sitio nuevo utiliza JSON, no el CSV antiguo.

Seleccionar un año habilita los meses con datos; seleccionar un mes habilita sus días conocidos. Cambiar el año borra mes/día y cambiar el mes borra el día. Un registro que solo tiene año participa en ese año, pero no en un mes o día inventado. La interfaz informa precisión y exclusiones. La captura histórica UNJBG solo conserva año; la selección web actual tiene 2515 fechas completas, una con precisión de mes y 5167 con solo año.

Evolución temporal agrupa por año, mes o día: el gráfico muestra hasta los últimos 60 periodos observados y la tabla todos los periodos. Temas cuenta una investigación por palabra clave, conserva las asociaciones originales y excluye URI OCDE; muestra un top 10 en el gráfico y top 20 en la tabla. El catálogo pagina de 25 en 25 y muestra la precisión real de la fecha. Los conteos y porcentajes se calculan sobre la selección filtrada; varias materias no multiplican los registros.

Los navegadores con DecompressionStream descargan `modelo_web.json.gz`; el resto usa JSON sin compresión. La estrella y los resúmenes son idénticos en ambas variantes. La compresión reduce transferencia sin eliminar búsqueda en el resumen.

En desarrollo: `python -m http.server 8765 --bind 127.0.0.1` desde la raíz del proyecto, abrir `/docs/`. En localhost se consulta `/data/`. En producción se usa la URL Raw pública fija. No se aceptan orígenes de datos proporcionados por formularios ni por metadatos del documento. En el repositorio público, `docs/` contiene el sitio.

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

CI instala las versiones de `requirements.lock.txt` y `documentos/requirements.lock.txt`, comprueba SHA256 y admite solo wheels. Al cambiar dependencias, actualizar también sus versiones y hashes en esos archivos.

Sonar puede señalar las constantes XML de `etl/extract_oaipmh.py` con S5332. Son identificadores de namespace, no conexiones de red: [la especificación OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html) exige esos URI con `http://`. Sustituirlos por HTTPS impediría reconocer los documentos. Esa observación requiere revisión como falso positivo en Sonar; no se desactiva la regla global.
