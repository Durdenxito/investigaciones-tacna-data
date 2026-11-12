let
    Base = "https://raw.githubusercontent.com",
    Ruta = "Durdenxito/investigaciones-tacna-data/main/data/estrella/",
    Nombres = {"dim_universidad", "repositorio", "dim_anio", "dim_madurez", "dim_registro", "fact_registro", "dim_autor", "dim_materia", "puente_registro_autor", "puente_registro_materia"},
    Leer = (nombre as text) as table =>
        let
            Csv = Csv.Document(Web.Contents(Base, [RelativePath = Ruta & nombre & ".csv"]), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            Tabla = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
            Enteros = List.Intersect({Table.ColumnNames(Tabla), {"anio_id", "orden"}}),
            Tipada = Table.TransformColumnTypes(Tabla, List.Transform(Enteros, each {_, Int64.Type})),
            Booleanos = List.Select(Table.ColumnNames(Tipada), each _ = "menciona_tacna" or Text.StartsWith(_, "coincide_")),
            Resultado = Table.TransformColumns(Tipada, List.Transform(Booleanos, each {_, (valor) => if Text.Lower(Text.From(valor)) = "true" then true else if Text.Lower(Text.From(valor)) = "false" then false else error "Booleano inválido", type logical}))
        in Resultado
in
    Record.FromList(List.Transform(Nombres, each Leer(_)), Nombres)

