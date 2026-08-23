from pydantic import BaseModel, Field
from app.models import Catalog, Table
from .models import SourceDataset, TransformationSQLGenerateRequest


class MetadataPreflightError(ValueError):
    code = "metadata_invalid"
    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__("; ".join(item["message"] for item in details))


class GenerationContext(BaseModel):
    primary_source: str
    datasets: list[Table]
    sources: list[SourceDataset]
    relations: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_generation_context(request: TransformationSQLGenerateRequest, catalog: Catalog) -> GenerationContext:
    errors: list[dict[str, str]] = []
    names = [source.dataset_id.split(".")[-1] for source in request.source]
    if len(names) != len(set(names)):
        errors.append({"code": "duplicate_source", "message": "Source datasets must be unique."})
    primaries = [source for source in request.source if source.role == "primary"]
    if len(primaries) != 1:
        errors.append({"code": "primary_source", "message": "Exactly one primary source dataset is required."})
    table_map = {table.name: table for table in catalog.tables}
    datasets: list[Table] = []
    for source, name in zip(request.source, names):
        table = table_map.get(name)
        if not table:
            errors.append({"code": "unknown_dataset", "message": f"Unknown source dataset: {source.dataset_id}."})
            continue
        known_columns = {column.name for column in table.columns}
        for column in source.selected_columns:
            if column not in known_columns:
                errors.append({"code": "unknown_column", "message": f"Unknown column {name}.{column}."})
        datasets.append(table)
    source_ids = {source.dataset_id.lower() for source in request.source}
    if request.sink.qualified_name.lower() in source_ids:
        errors.append({"code": "sink_is_source", "message": "Sink dataset cannot be the same as a source dataset."})
    if errors:
        raise MetadataPreflightError(errors)
    selected = set(names)
    relations = [relation.model_dump() for relation in catalog.relations if relation.left.split(".")[0] in selected and relation.right.split(".")[0] in selected]
    warnings = ["No known metadata relation connects the selected datasets."] if len(selected) > 1 and not relations else []
    return GenerationContext(primary_source=primaries[0].dataset_id, datasets=datasets, sources=request.source, relations=relations, warnings=warnings)
