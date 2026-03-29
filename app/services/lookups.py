from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.db import assets as assets_db
from app.db import lookups as lookups_db


def _serialize_lookup_row(row: dict | None, *uuid_fields: str):
    if row is None:
        return None

    item = dict(row)
    for field_name in uuid_fields:
        if field_name in item and item[field_name] is not None:
            item[field_name] = str(item[field_name])

    return item


def _serialize_lookup_rows(rows: list[dict], *uuid_fields: str):
    return [_serialize_lookup_row(row, *uuid_fields) for row in rows]


def _normalize_name(value: str | None, field_name: str = "name") -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_uuid(value, *, field_name: str, required: bool = False) -> str | None:
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"Missing required field: {field_name}")
        return None

    try:
        return str(UUID(str(value).strip()))
    except ValueError:
        raise ValueError(f"Invalid {field_name}, must be a UUID string")


def list_asset_statuses():
    return _serialize_lookup_rows(assets_db.list_asset_status_rows(), "id")


def get_asset_status(status_id):
    normalized_status_id = _normalize_uuid(
        status_id,
        field_name="status_id",
        required=True,
    )
    return _serialize_lookup_row(
        assets_db.get_asset_status_row(normalized_status_id),
        "id",
    )


def validate_asset_status_id(status_id, *, required: bool = False, field_name: str = "status_id") -> str | None:
    normalized_status_id = _normalize_uuid(
        status_id,
        field_name=field_name,
        required=required,
    )
    if normalized_status_id is None:
        return None

    if get_asset_status(normalized_status_id) is None:
        raise ValueError(f"Unknown {field_name}")

    return normalized_status_id


def list_asset_categories():
    return _serialize_lookup_rows(lookups_db.list_category_rows(), "id")


def list_categories():
    return list_asset_categories()


def get_category(category_id):
    normalized_category_id = _normalize_uuid(
        category_id,
        field_name="category_id",
        required=True,
    )
    return _serialize_lookup_row(
        lookups_db.get_category_row(normalized_category_id),
        "id",
    )


def validate_category_id(category_id, *, required: bool = False, field_name: str = "category_id") -> str | None:
    normalized_category_id = _normalize_uuid(
        category_id,
        field_name=field_name,
        required=required,
    )
    if normalized_category_id is None:
        return None

    if get_category(normalized_category_id) is None:
        raise ValueError(f"Unknown {field_name}")

    return normalized_category_id


def create_category(*, name: str) -> dict:
    normalized_name = _normalize_name(name, "Category name")

    if lookups_db.category_name_exists(normalized_name):
        raise ValueError("Category already exists")

    try:
        row = lookups_db.create_category_row(
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Category already exists") from exc

    return _serialize_lookup_row(row, "id")


def update_category(*, category_id, name: str) -> dict:
    normalized_category_id = validate_category_id(
        category_id,
        required=True,
        field_name="category_id",
    )
    normalized_name = _normalize_name(name, "Category name")

    if lookups_db.category_name_exists(normalized_name, exclude_id=normalized_category_id):
        raise ValueError("Category already exists")

    try:
        row = lookups_db.update_category_row(
            normalized_category_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Category already exists") from exc

    if row is None:
        raise ValueError("Unknown category_id")

    return _serialize_lookup_row(row, "id")


def delete_category(category_id) -> bool:
    normalized_category_id = validate_category_id(
        category_id,
        required=True,
        field_name="category_id",
    )
    try:
        return lookups_db.delete_category_row(normalized_category_id)
    except IntegrityError as exc:
        raise ValueError("Category cannot be deleted because it is in use") from exc


def list_makes(category_id=None):
    normalized_category_id = None
    if category_id is not None and str(category_id).strip():
        normalized_category_id = _normalize_uuid(
            category_id,
            field_name="category_id",
            required=True,
        )

    return _serialize_lookup_rows(
        lookups_db.list_makes(category_id=normalized_category_id),
        "id",
        "category_id",
    )


def get_make(make_id):
    normalized_make_id = _normalize_uuid(make_id, field_name="make_id", required=True)
    return _serialize_lookup_row(
        lookups_db.get_make_row(normalized_make_id),
        "id",
        "category_id",
    )


def validate_make_id(make_id, *, required: bool = False, field_name: str = "make_id") -> str | None:
    normalized_make_id = _normalize_uuid(
        make_id,
        field_name=field_name,
        required=required,
    )
    if normalized_make_id is None:
        return None

    if get_make(normalized_make_id) is None:
        raise ValueError(f"Unknown {field_name}")

    return normalized_make_id


def create_make(*, category_id, name: str) -> dict:
    normalized_category_id = validate_category_id(
        category_id,
        required=True,
        field_name="category_id",
    )
    normalized_name = _normalize_name(name, "Make name")

    if lookups_db.make_name_exists(normalized_name):
        raise ValueError("Make already exists")

    try:
        row = lookups_db.create_make_row(
            category_id=normalized_category_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Make already exists") from exc

    return _serialize_lookup_row(row, "id", "category_id")


def update_make(*, make_id, category_id, name: str) -> dict:
    normalized_make_id = validate_make_id(
        make_id,
        required=True,
        field_name="make_id",
    )
    normalized_category_id = validate_category_id(
        category_id,
        required=True,
        field_name="category_id",
    )
    normalized_name = _normalize_name(name, "Make name")

    if lookups_db.make_name_exists(normalized_name, exclude_id=normalized_make_id):
        raise ValueError("Make already exists")

    try:
        row = lookups_db.update_make_row(
            normalized_make_id,
            category_id=normalized_category_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Make already exists") from exc

    if row is None:
        raise ValueError("Unknown make_id")

    return _serialize_lookup_row(row, "id", "category_id")


def delete_make(make_id) -> bool:
    normalized_make_id = validate_make_id(
        make_id,
        required=True,
        field_name="make_id",
    )
    try:
        return lookups_db.delete_make_row(normalized_make_id)
    except IntegrityError as exc:
        raise ValueError("Make cannot be deleted because it is in use") from exc


def list_models(make_id=None):
    normalized_make_id = None
    if make_id is not None and str(make_id).strip():
        normalized_make_id = _normalize_uuid(
            make_id,
            field_name="make_id",
            required=True,
        )

    return _serialize_lookup_rows(
        lookups_db.list_models(make_id=normalized_make_id),
        "id",
        "make_id",
        "category_id",
    )


def get_model(model_id):
    normalized_model_id = _normalize_uuid(model_id, field_name="model_id", required=True)
    return _serialize_lookup_row(
        lookups_db.get_model_row(normalized_model_id),
        "id",
        "make_id",
        "category_id",
    )


def validate_model_id(model_id, *, required: bool = False, field_name: str = "model_id") -> str | None:
    normalized_model_id = _normalize_uuid(
        model_id,
        field_name=field_name,
        required=required,
    )
    if normalized_model_id is None:
        return None

    if get_model(normalized_model_id) is None:
        raise ValueError(f"Unknown {field_name}")

    return normalized_model_id


def create_model(*, make_id, name: str) -> dict:
    normalized_make_id = validate_make_id(
        make_id,
        required=True,
        field_name="make_id",
    )
    normalized_name = _normalize_name(name, "Model name")

    if lookups_db.model_name_exists_in_make(normalized_name, normalized_make_id):
        raise ValueError("Model already exists for this make")

    try:
        row = lookups_db.create_model_row(
            make_id=normalized_make_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Model already exists for this make") from exc

    return _serialize_lookup_row(row, "id", "make_id")


def update_model(*, model_id, make_id, name: str) -> dict:
    normalized_model_id = validate_model_id(
        model_id,
        required=True,
        field_name="model_id",
    )
    normalized_make_id = validate_make_id(
        make_id,
        required=True,
        field_name="make_id",
    )
    normalized_name = _normalize_name(name, "Model name")

    if lookups_db.model_name_exists_in_make(
        normalized_name,
        normalized_make_id,
        exclude_id=normalized_model_id,
    ):
        raise ValueError("Model already exists for this make")

    try:
        row = lookups_db.update_model_row(
            normalized_model_id,
            make_id=normalized_make_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Model already exists for this make") from exc

    if row is None:
        raise ValueError("Unknown model_id")

    return _serialize_lookup_row(row, "id", "make_id")


def delete_model(model_id) -> bool:
    normalized_model_id = validate_model_id(
        model_id,
        required=True,
        field_name="model_id",
    )
    try:
        return lookups_db.delete_model_row(normalized_model_id)
    except IntegrityError as exc:
        raise ValueError("Model cannot be deleted because it is in use") from exc


def list_variants(model_id=None):
    normalized_model_id = None
    if model_id is not None and str(model_id).strip():
        normalized_model_id = _normalize_uuid(
            model_id,
            field_name="model_id",
            required=True,
        )

    return _serialize_lookup_rows(
        lookups_db.list_variants(model_id=normalized_model_id),
        "id",
        "model_id",
        "make_id",
        "category_id",
    )


def get_variant(variant_id):
    normalized_variant_id = _normalize_uuid(
        variant_id,
        field_name="variant_id",
        required=True,
    )
    return _serialize_lookup_row(
        lookups_db.get_variant_row(normalized_variant_id),
        "id",
        "model_id",
        "make_id",
        "category_id",
    )


def validate_variant_id(variant_id, *, required: bool = False, field_name: str = "variant_id") -> str | None:
    normalized_variant_id = _normalize_uuid(
        variant_id,
        field_name=field_name,
        required=required,
    )
    if normalized_variant_id is None:
        return None

    if get_variant(normalized_variant_id) is None:
        raise ValueError(f"Unknown {field_name}")

    return normalized_variant_id


def create_variant(*, model_id, name: str) -> dict:
    normalized_model_id = validate_model_id(
        model_id,
        required=True,
        field_name="model_id",
    )
    normalized_name = _normalize_name(name, "Variant name")

    if lookups_db.variant_name_exists_in_model(normalized_name, normalized_model_id):
        raise ValueError("Variant already exists for this model")

    try:
        row = lookups_db.create_variant_row(
            model_id=normalized_model_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Variant already exists for this model") from exc

    return _serialize_lookup_row(row, "id", "model_id")


def update_variant(*, variant_id, model_id, name: str) -> dict:
    normalized_variant_id = validate_variant_id(
        variant_id,
        required=True,
        field_name="variant_id",
    )
    normalized_model_id = validate_model_id(
        model_id,
        required=True,
        field_name="model_id",
    )
    normalized_name = _normalize_name(name, "Variant name")

    if lookups_db.variant_name_exists_in_model(
        normalized_name,
        normalized_model_id,
        exclude_id=normalized_variant_id,
    ):
        raise ValueError("Variant already exists for this model")

    try:
        row = lookups_db.update_variant_row(
            normalized_variant_id,
            model_id=normalized_model_id,
            name=normalized_name,
            label=normalized_name,
        )
    except IntegrityError as exc:
        raise ValueError("Variant already exists for this model") from exc

    if row is None:
        raise ValueError("Unknown variant_id")

    return _serialize_lookup_row(row, "id", "model_id")


def delete_variant(variant_id) -> bool:
    normalized_variant_id = validate_variant_id(
        variant_id,
        required=True,
        field_name="variant_id",
    )
    try:
        return lookups_db.delete_variant_row(normalized_variant_id)
    except IntegrityError as exc:
        raise ValueError("Variant cannot be deleted because it is in use") from exc
