let
    Origen = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com", [RelativePath = "Durdenxito/investigaciones-tacna-data/main/data/investigaciones_tacna.csv"]),
        [Delimiter = ",", Columns = 8, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"titulo", type text}, {"autores", type text}, {"anio", Int64.Type},
        {"abstract", type text}, {"enlace", type text}, {"materias", type text},
        {"universidad", type text}, {"nivel_madurez", type text}
    })
in
    Tipos
