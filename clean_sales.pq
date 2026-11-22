// In Excel or Power BI, create a blank query and paste this into Advanced Editor.
// Set Root to the extracted sample folder (which contains dealers.csv and sales).
let
    Root = "C:\replace-me\consumer-durables-mis\sample",
    ReadCsv = (bytes as binary) as table =>
        Table.PromoteHeaders(Csv.Document(bytes, [Delimiter=",", Encoding=65001]), [PromoteAllScalars=true]),
    Normalize = (value as nullable text) as nullable text => Text.Upper(Text.Trim(value)),
    Files = Table.SelectRows(Folder.Contents(Root & "\sales"), each [Extension] = ".csv"),
    Inputs = Table.Combine(List.Transform(Files[Content], ReadCsv)),
    Typed = Table.TransformColumnTypes(Inputs, {
        {"sale_date", type date}, {"sell_in", Int64.Type}, {"sell_out", Int64.Type}
    }, "en-US"),
    Normalized = Table.TransformColumns(Typed, {
        {"record_id", Text.Trim, type text}, {"dealer", Normalize, type text}, {"sku", Normalize, type text}
    }),
    Dealers = ReadCsv(File.Contents(Root & "\dealers.csv")),
    Skus = ReadCsv(File.Contents(Root & "\skus.csv")),
    DealerJoin = Table.NestedJoin(Normalized, {"dealer"}, Dealers, {"dealer"}, "dealer_map"),
    SkuJoin = Table.NestedJoin(DealerJoin, {"sku"}, Skus, {"sku"}, "sku_map"),
    Mapped = Table.SelectRows(SkuJoin, each Table.RowCount([dealer_map]) = 1 and Table.RowCount([sku_map]) = 1),
    Unique = Table.Distinct(Table.Buffer(Mapped), {"record_id"}),
    Regions = Table.ExpandTableColumn(Unique, "dealer_map", {"region"}, {"region"}),
    Result = Table.SelectColumns(Regions, {"record_id", "sale_date", "dealer", "sku", "region", "sell_in", "sell_out"})
in
    Result
