let
    RutaCsv = "C:\Users\grimm\OneDrive\Documentos\Proyectito de Inteligencia\dashboard-produccion-github-epis\data\investigaciones_tacna.csv",
    Origen = Csv.Document(File.Contents(RutaCsv), [Delimiter = ",", Columns = 8, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"titulo", type text}, {"autores", type text}, {"anio", Int64.Type},
        {"abstract", type text}, {"enlace", type text}, {"materias", type text},
        {"universidad", type text}, {"nivel_madurez", type text}
    })
in
    Tipos
