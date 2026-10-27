"""Schema validation: Primary Key uniqueness, Foreign Key integrity, Enum domains, and format contracts."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class SchemaValidationError:
    def __init__(self, entity: str, record_id: str, field: str, error_type: str, message: str):
        self.entity = entity
        self.record_id = record_id
        self.field = field
        self.error_type = error_type
        self.message = message

    def to_dict(self) -> Dict[str, str]:
        return {
            "entity": self.entity,
            "record_id": self.record_id,
            "field": self.field,
            "error_type": self.error_type,
            "message": self.message,
        }


def validate_pk_uniqueness(
    data: List[Dict[str, str]],
    pk_field: str,
    entity_name: str,
    pattern: str = None,
) -> List[SchemaValidationError]:
    """Validates that primary keys are non-empty, unique, and follow the expected ID format."""
    errors: List[SchemaValidationError] = []
    seen_pks: Set[str] = set()

    for idx, row in enumerate(data):
        pk_val = row.get(pk_field, "").strip()
        record_id = pk_val or f"row-{idx+1}"

        if not pk_val:
            errors.append(
                SchemaValidationError(
                    entity=entity_name,
                    record_id=record_id,
                    field=pk_field,
                    error_type="PK_NULL_OR_EMPTY",
                    message=f"Primary key field '{pk_field}' is missing or empty.",
                )
            )
            continue

        if pk_val in seen_pks:
            errors.append(
                SchemaValidationError(
                    entity=entity_name,
                    record_id=record_id,
                    field=pk_field,
                    error_type="PK_DUPLICATE",
                    message=f"Duplicate primary key value '{pk_val}' detected.",
                )
            )
        else:
            seen_pks.add(pk_val)

        if pattern and not re.match(pattern, pk_val):
            errors.append(
                SchemaValidationError(
                    entity=entity_name,
                    record_id=record_id,
                    field=pk_field,
                    error_type="PK_FORMAT_INVALID",
                    message=f"Primary key '{pk_val}' does not conform to regex '{pattern}'.",
                )
            )

    return errors


def validate_fk_integrity(
    child_data: List[Dict[str, str]],
    fk_field: str,
    child_entity: str,
    parent_pks: Set[str],
    parent_entity: str,
) -> List[SchemaValidationError]:
    """Validates that every foreign key reference points to an existing primary key in the parent table."""
    errors: List[SchemaValidationError] = []

    for idx, row in enumerate(child_data):
        fk_val = row.get(fk_field, "").strip()
        pk_val = list(row.values())[0] if row else f"row-{idx+1}"

        if not fk_val:
            errors.append(
                SchemaValidationError(
                    entity=child_entity,
                    record_id=pk_val,
                    field=fk_field,
                    error_type="FK_NULL_OR_EMPTY",
                    message=f"Foreign key '{fk_field}' is empty.",
                )
            )
        elif fk_val not in parent_pks:
            errors.append(
                SchemaValidationError(
                    entity=child_entity,
                    record_id=pk_val,
                    field=fk_field,
                    error_type="FK_ORPHAN",
                    message=f"Foreign key '{fk_field}' value '{fk_val}' not found in parent entity '{parent_entity}'.",
                )
            )

    return errors


def validate_enum_field(
    data: List[Dict[str, str]],
    field_name: str,
    entity_name: str,
    allowed_values: List[str],
) -> List[SchemaValidationError]:
    """Validates that categorical fields contain only values from the permitted domain."""
    errors: List[SchemaValidationError] = []
    allowed_set = set(allowed_values)

    for idx, row in enumerate(data):
        val = row.get(field_name, "").strip()
        pk_val = list(row.values())[0] if row else f"row-{idx+1}"

        if val not in allowed_set:
            errors.append(
                SchemaValidationError(
                    entity=entity_name,
                    record_id=pk_val,
                    field=field_name,
                    error_type="ENUM_INVALID_VALUE",
                    message=f"Value '{val}' in field '{field_name}' not in allowed set {allowed_values}.",
                )
            )

    return errors


def validate_unique_field(
    data: List[Dict[str, str]],
    field_name: str,
    entity_name: str,
) -> List[SchemaValidationError]:
    """Validates that values in a column with a uniqueness constraint are distinct."""
    errors: List[SchemaValidationError] = []
    seen: Set[str] = set()

    for idx, row in enumerate(data):
        val = row.get(field_name, "").strip()
        pk_val = list(row.values())[0] if row else f"row-{idx+1}"

        if val:
            if val in seen:
                errors.append(
                    SchemaValidationError(
                        entity=entity_name,
                        record_id=pk_val,
                        field=field_name,
                        error_type="UNIQUE_FIELD_DUPLICATE",
                        message=f"Duplicate value '{val}' found for unique field '{field_name}'.",
                    )
                )
            else:
                seen.add(val)

    return errors


def validate_unique_composite_key(
    data: List[Dict[str, str]],
    fields: List[str],
    entity_name: str,
) -> List[SchemaValidationError]:
    """Validates that composite tuples across multiple fields are unique."""
    errors: List[SchemaValidationError] = []
    seen_tuples: Set[Tuple[str, ...]] = set()

    for idx, row in enumerate(data):
        key_tuple = tuple(row.get(f, "").strip() for f in fields)
        pk_val = list(row.values())[0] if row else f"row-{idx+1}"

        if key_tuple in seen_tuples:
            errors.append(
                SchemaValidationError(
                    entity=entity_name,
                    record_id=pk_val,
                    field="+".join(fields),
                    error_type="COMPOSITE_KEY_DUPLICATE",
                    message=f"Duplicate composite key {key_tuple} detected on {entity_name}.",
                )
            )
        else:
            seen_tuples.add(key_tuple)

    return errors
