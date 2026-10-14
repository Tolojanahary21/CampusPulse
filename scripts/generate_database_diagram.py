"""Génère le diagramme depuis le code des modèles, sans charger de .env ni DB.

Usage depuis la racine : python scripts/generate_database_diagram.py
Le générateur couvre les déclarations mapped_column et contraintes explicites.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def name(node: ast.AST) -> str:
    return node.id if isinstance(node, ast.Name) else ""


def columns(node: ast.ClassDef) -> list[dict]:
    result = []
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if name(call.func) != "mapped_column":
            continue
        foreign = None
        data_type = "VARCHAR(36)"
        for argument in call.args:
            if isinstance(argument, ast.Call):
                kind = name(argument.func)
                if kind == "ForeignKey":
                    foreign = ast.literal_eval(argument.args[0])
                elif kind == "String":
                    data_type = f"VARCHAR({ast.literal_eval(argument.args[0])})"
                elif kind == "DateTime":
                    data_type = "TIMESTAMPTZ"
                else:
                    data_type = kind.upper()
            elif isinstance(argument, ast.Name):
                data_type = {"Integer": "INTEGER", "Text": "TEXT", "Boolean": "BOOLEAN", "Float": "FLOAT", "JSON": "JSON", "Date": "DATE"}.get(argument.id, argument.id.upper())
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        primary = "primary_key" in keywords and ast.literal_eval(keywords["primary_key"])
        unique = "unique" in keywords and ast.literal_eval(keywords["unique"])
        nullable = "None" in ast.unparse(statement.annotation)
        if "nullable" in keywords:
            nullable = ast.literal_eval(keywords["nullable"])
        result.append({"name": statement.target.id, "type": data_type, "foreign": foreign, "primary": primary, "unique": unique, "nullable": nullable})
    return result


def main() -> None:
    nodes = []
    model_files = list((ROOT / "backend/app/models").glob("*.py"))
    model_files += [ROOT / "backend/app/services/mail.py", ROOT / "backend/app/core/rate_limit.py"]
    for model_file in sorted(model_files):
        tree = ast.parse(model_file.read_text(encoding="utf-8"))
        nodes.extend(item for item in tree.body if isinstance(item, ast.ClassDef))
    entity = next(item for item in nodes if item.name == "Entity")
    shared = columns(entity)
    lines = ["@startuml", "' Généré par scripts/generate_database_diagram.py ; ne charge aucune configuration.", "hide circle", "skinparam linetype ortho", "skinparam shadowing false", "title CampusPulse — schéma relationnel de la V1", ""]
    links = []
    count = 0
    for model in nodes:
        table = None
        constraints = []
        for statement in model.body:
            if not isinstance(statement, ast.Assign):
                continue
            if any(name(target) == "__tablename__" for target in statement.targets):
                table = ast.literal_eval(statement.value)
            if any(name(target) == "__table_args__" for target in statement.targets):
                for constraint in ast.walk(statement.value):
                    if not isinstance(constraint, ast.Call):
                        continue
                    if name(constraint.func) == "UniqueConstraint":
                        constraints.append("UQ(" + ", ".join(ast.literal_eval(value) for value in constraint.args) + ")")
                    elif name(constraint.func) == "CheckConstraint":
                        label = next((ast.literal_eval(kw.value) for kw in constraint.keywords if kw.arg == "name"), "validation")
                        constraints.append("CHECK " + label)
                    elif name(constraint.func) == "ForeignKeyConstraint":
                        fields = ", ".join(ast.literal_eval(constraint.args[0]))
                        targets = ", ".join(ast.literal_eval(constraint.args[1]))
                        constraints.append(f"FK({fields}) vers {targets}")
                    elif name(constraint.func) == "Index":
                        unique = any(kw.arg == "unique" and ast.literal_eval(kw.value) for kw in constraint.keywords)
                        if unique:
                            constraints.append("INDEX UQ " + ast.literal_eval(constraint.args[0]))
        if table is None:
            continue
        count += 1
        values = (shared if any(name(base) == "Entity" for base in model.bases) else []) + columns(model)
        lines.append(f'entity "{table}" as {table} {{')
        for value in values:
            flags = [flag for flag, present in (("PK", value["primary"]), ("FK", value["foreign"]), ("UQ", value["unique"])) if present]
            flags_text = " <<" + ",".join(flags) + ">>" if flags else ""
            lines.append(f'  {" " if value["nullable"] else "*"} {value["name"]} : {value["type"]}{flags_text}')
            if value["foreign"]:
                parent, _ = value["foreign"].split(".", 1)
                cardinality = '"0..1"' if value["nullable"] else '"1"'
                child_cardinality = '"0..1"' if value["unique"] else '"0..*"'
                links.append(f'{parent} {cardinality} -- {child_cardinality} {table} : {value["name"]}')
        if constraints:
            lines.append("  --")
            lines.extend("  " + constraint for constraint in constraints)
        lines.extend(["}", ""])
    lines.extend(links)
    lines.extend(["", "legend bottom", f"  {count} tables déclarées ; * champ obligatoire ; PK clé primaire ; FK clé étrangère ; UQ unicité.", "  Les UUID sont des VARCHAR(36). Cibles : clés primaires composées.", "  Les compatibilités entre établissements sont aussi vérifiées dans les transactions API.", "  Les contraintes CHECK sont nommées ici ; leurs expressions figurent dans les modèles et migrations.", "endlegend", "@enduml", ""])
    destination = ROOT / "docs/database-schema.puml"
    destination.write_text("\n".join(lines), encoding="utf-8")
    print(f"Diagramme généré : {count} tables.")


if __name__ == "__main__":
    main()
