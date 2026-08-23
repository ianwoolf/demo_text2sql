from __future__ import annotations
from sqlglot import exp, parse
from sqlglot.errors import ParseError
from app.models import Catalog
from .models import SparkSQLValidation, TransformationRequestData, TransformationSQLGenerateRequest


def validate_spark_sql(sql: str, request: TransformationSQLGenerateRequest, catalog: Catalog) -> SparkSQLValidation:
    errors, warnings = [], []
    try:
        statements = parse(sql, read="spark")
    except ParseError as exc:
        return SparkSQLValidation(status="failed", errors=[f"Invalid Spark SQL syntax: {exc}."])
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        return SparkSQLValidation(status="failed", errors=["Spark SQL must be one SELECT or WITH ... SELECT query."])
    tree = statements[0]
    selected = {source.dataset_id.split(".")[-1].lower() for source in request.source}
    catalog_tables = {table.name.lower(): table for table in catalog.tables}
    ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    tables = sorted({table.name.lower() for table in tree.find_all(exp.Table) if table.name.lower() not in ctes})
    for table in tables:
        if table not in selected:
            errors.append(f"Spark SQL references unselected source dataset: {table}.")
    aliases = {(table.alias_or_name or table.name).lower(): table.name.lower() for table in tree.find_all(exp.Table) if table.name.lower() not in ctes}
    all_columns = {column.name.lower() for name in selected if name in catalog_tables for column in catalog_tables[name].columns}
    for column in tree.find_all(exp.Column):
        name, qualifier = column.name.lower(), (column.table or "").lower()
        if qualifier in ctes:
            continue
        if qualifier in aliases:
            table = catalog_tables.get(aliases[qualifier])
            if table and name not in {item.name.lower() for item in table.columns}:
                errors.append(f"Unknown selected source column: {qualifier}.{column.name}.")
        elif not qualifier and name not in all_columns:
            errors.append(f"Unknown selected source column: {column.name}.")
    outer = tree if isinstance(tree, exp.Select) else tree.args.get("this")
    if not isinstance(outer, exp.Select):
        outer = tree.find(exp.Select)
    outputs = [item.alias_or_name for item in outer.expressions if item.alias_or_name] if outer else []
    if len([name.lower() for name in outputs]) != len(set(name.lower() for name in outputs)):
        errors.append("Spark SQL output column names must be unique.")
    for partition in request.sink.partition_columns:
        if partition.lower() not in {name.lower() for name in outputs}:
            errors.append(f"Sink partition column is not present in Spark SQL output: {partition}.")
    joins = [f"{relation.left} = {relation.right}" for relation in catalog.relations if relation.left.split(".")[0] in selected and relation.right.split(".")[0] in selected]
    if len(selected) > 1 and not joins:
        warnings.append("No known metadata relation connects the selected datasets.")
    return SparkSQLValidation(status="failed" if errors else "passed", referenced_tables=tables, output_columns=outputs, joins=joins, warnings=warnings, errors=list(dict.fromkeys(errors)))


def validate_transformation(data: TransformationRequestData, catalog: Catalog) -> SparkSQLValidation:
    request = TransformationSQLGenerateRequest(mode="mock", requirement_text=data.requirement_text, source=data.source, sink=data.sink)
    return validate_spark_sql(data.spark_sql.content, request, catalog)
