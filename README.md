# Investigaciones que mencionan Tacna

Dataset publico de investigaciones de la UNJBG cuyo titulo, resumen o materias contienen la palabra Tacna (sin distinguir mayusculas). El filtro identifica menciones; no certifica el lugar de ejecucion del estudio. Solo se incluyen registros con anio de publicacion valido.

Fuente academica: https://repositorio.unjbg.edu.pe/server/oai/request

## CSV para Power BI

https://raw.githubusercontent.com/Durdenxito/investigaciones-tacna-data/main/data/investigaciones_tacna.csv

CSV UTF-8 con ocho columnas: titulo, autores, anio, abstract, enlace, materias, universidad y nivel_madurez. `anio` es entero; las demas columnas son texto.

`nivel_madurez` se estima con palabras del resumen. Las categorias Teorico, Prototipo / Piloto y En Produccion no acreditan implementaciones reales. Revisar el documento original para confirmar los resultados. Los metadatos provienen del repositorio academico; su publicacion aqui no cambia los derechos de los documentos originales.

## Actualizacion automatica

GitHub Actions ejecuta las pruebas y el ETL cada domingo a las 00:17 de Peru (05:17 UTC), al cambiar el codigo del ETL en main, o manualmente desde Actions > Actualizar Investigaciones Tacna > Run workflow.

Si falla la descarga o no hay investigaciones validas, no se publica un reemplazo del CSV. Si los datos no cambian, no se crea un commit. El horario de Actions puede sufrir demoras y la actualizacion requiere que la fuente academica este disponible. En repositorios publicos GitHub puede desactivar el cron tras 60 dias sin actividad; si ocurre, reactivarlo desde Actions.

El cron actualiza el CSV. El modelo de Power BI debe configurarse por separado para leer esta URL y refrescar despues del ETL, por ejemplo los lunes a las 12:00 de Peru. No se necesita un token de GitHub para consumir el CSV publico.

## Ejecucion local

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python etl/main_oaipmh.py
```

El CSV se guarda en data/investigaciones_tacna.csv.

## Dashboard publico

https://durdenxito.github.io/investigaciones-tacna-data/

Dos paginas interactivas, filtros compartidos y enlaces a los estudios. El sitio lee el CSV publico al abrirse; para ver nuevos datos, volver a cargar la pagina. No requiere Power BI ni mantener un equipo encendido. Fuente del sitio: docs/. Pruebas web: node tests/test_web.cjs.

