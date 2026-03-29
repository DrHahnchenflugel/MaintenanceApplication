from time import monotonic
from uuid import UUID

from flask import request
from sqlalchemy.exc import IntegrityError

from app.db import sites as sites_db


PREFERRED_SITE_COOKIE_NAME = "preferred_site"
PREFERRED_SITE_COOKIE_MAX_AGE = 180 * 24 * 60 * 60
_SITE_CACHE_TTL_SECONDS = 300
_SITE_SNAPSHOT = None
_SITE_SNAPSHOT_EXPIRES_AT = 0.0


def _normalize_site_code(site_code: str | None) -> str:
    return (site_code or "").strip().upper()


def _normalize_site_id(site_id) -> str | None:
    if site_id is None:
        return None

    value = str(site_id).strip()
    if not value:
        return None

    try:
        return str(UUID(value))
    except ValueError:
        return None


def _clone_site(site: dict) -> dict:
    return dict(site)


def _build_site_snapshot(rows: list[dict]) -> tuple[dict, ...]:
    sites = []

    for row in rows:
        site = dict(row)
        site["id"] = str(site["id"])
        site["code"] = _normalize_site_code(site.get("shorthand"))
        sites.append(site)

    return tuple(sites)


def _get_site_snapshot(force_refresh: bool = False) -> tuple[dict, ...]:
    global _SITE_SNAPSHOT
    global _SITE_SNAPSHOT_EXPIRES_AT

    now = monotonic()
    if force_refresh or _SITE_SNAPSHOT is None or now >= _SITE_SNAPSHOT_EXPIRES_AT:
        _SITE_SNAPSHOT = _build_site_snapshot(sites_db.list_site_rows())
        _SITE_SNAPSHOT_EXPIRES_AT = now + _SITE_CACHE_TTL_SECONDS

    return _SITE_SNAPSHOT


def list_sites(force_refresh: bool = False) -> list[dict]:
    snapshot = _get_site_snapshot(force_refresh=force_refresh)
    return [_clone_site(site) for site in snapshot]


def get_site_catalog(force_refresh: bool = False) -> dict:
    sites = list_sites(force_refresh=force_refresh)
    by_id = {}
    by_code = {}

    for site in sites:
        by_id[site["id"]] = site
        if site["code"]:
            by_code[site["code"]] = site

    return {
        "sites": sites,
        "by_id": {site_id: _clone_site(site) for site_id, site in by_id.items()},
        "by_code": {code: _clone_site(site) for code, site in by_code.items()},
        "valid_site_ids": set(by_id.keys()),
        "valid_site_codes": set(by_code.keys()),
    }


def get_valid_site_codes(force_refresh: bool = False) -> set[str]:
    catalog = get_site_catalog(force_refresh=force_refresh)
    return set(catalog["valid_site_codes"])


def get_site(site_id):
    normalized_site_id = _normalize_site_id(site_id)
    if not normalized_site_id:
        return None

    site = get_site_catalog()["by_id"].get(normalized_site_id)
    return _clone_site(site) if site else None


def get_site_by_code(site_code: str | None):
    normalized_site_code = _normalize_site_code(site_code)
    if not normalized_site_code:
        return None

    site = get_site_catalog()["by_code"].get(normalized_site_code)
    return _clone_site(site) if site else None


def get_current_site(site_code: str | None = None):
    if site_code is None:
        site_code = request.cookies.get(PREFERRED_SITE_COOKIE_NAME)

    return get_site_by_code(site_code)


def _normalize_site_fullname(fullname: str | None) -> str:
    value = (fullname or "").strip()
    if not value:
        raise ValueError("Site name is required")
    return value


def validate_site_id(site_id, *, required: bool = False, field_name: str = "site_id") -> str | None:
    if site_id is None or str(site_id).strip() == "":
        if required:
            raise ValueError(f"Missing required field: {field_name}")
        return None

    try:
        normalized_site_id = str(UUID(str(site_id).strip()))
    except ValueError:
        raise ValueError(f"Invalid {field_name}, must be a UUID string")

    if normalized_site_id not in get_site_catalog()["valid_site_ids"]:
        raise ValueError(f"Unknown {field_name}")

    return normalized_site_id


def create_site(*, shorthand: str, fullname: str) -> dict:
    normalized_shorthand = _normalize_site_code(shorthand)
    normalized_fullname = _normalize_site_fullname(fullname)

    if not normalized_shorthand:
        raise ValueError("Site short code is required")

    if sites_db.site_shorthand_exists(normalized_shorthand):
        raise ValueError("Site short code already exists")

    try:
        row = sites_db.create_site_row(
            shorthand=normalized_shorthand,
            fullname=normalized_fullname,
        )
    except IntegrityError as exc:
        raise ValueError("Site short code already exists") from exc

    _get_site_snapshot(force_refresh=True)

    site = dict(row)
    site["id"] = str(site["id"])
    site["code"] = _normalize_site_code(site.get("shorthand"))
    return site


def update_site(*, site_id, shorthand: str, fullname: str) -> dict:
    normalized_site_id = validate_site_id(site_id, required=True, field_name="site_id")
    normalized_shorthand = _normalize_site_code(shorthand)
    normalized_fullname = _normalize_site_fullname(fullname)

    if not normalized_shorthand:
        raise ValueError("Site short code is required")

    if sites_db.site_shorthand_exists_for_other_site(
        normalized_shorthand,
        exclude_site_id=normalized_site_id,
    ):
        raise ValueError("Site short code already exists")

    try:
        row = sites_db.update_site_row(
            normalized_site_id,
            shorthand=normalized_shorthand,
            fullname=normalized_fullname,
        )
    except IntegrityError as exc:
        raise ValueError("Site short code already exists") from exc

    if row is None:
        raise ValueError("Unknown site_id")

    _get_site_snapshot(force_refresh=True)

    site = dict(row)
    site["id"] = str(site["id"])
    site["code"] = _normalize_site_code(site.get("shorthand"))
    return site


def delete_site(site_id) -> bool:
    normalized_site_id = validate_site_id(site_id, required=True, field_name="site_id")
    try:
        deleted = sites_db.delete_site_row(normalized_site_id)
    except IntegrityError as exc:
        raise ValueError("Site cannot be deleted because it is in use") from exc

    if deleted:
        _get_site_snapshot(force_refresh=True)
    return deleted


def _should_use_secure_cookie(req=None) -> bool:
    req = req or request
    if req.is_secure:
        return True

    forwarded_proto = req.headers.get("X-Forwarded-Proto", "")
    return any(part.strip().lower() == "https" for part in forwarded_proto.split(","))


def set_preferred_site_cookie(response, site_code: str | None, req=None):
    req = req or request
    normalized_site_code = _normalize_site_code(site_code)
    secure = _should_use_secure_cookie(req)

    if not normalized_site_code:
        response.delete_cookie(
            PREFERRED_SITE_COOKIE_NAME,
            path="/",
            samesite="Lax",
            secure=secure,
        )
        return response

    if get_site_by_code(normalized_site_code) is None:
        raise ValueError("Invalid site_code")

    response.set_cookie(
        PREFERRED_SITE_COOKIE_NAME,
        normalized_site_code,
        max_age=PREFERRED_SITE_COOKIE_MAX_AGE,
        samesite="Lax",
        secure=secure,
        httponly=False,
        path="/",
    )
    return response
