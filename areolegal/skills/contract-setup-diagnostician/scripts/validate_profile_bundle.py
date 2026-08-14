#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

VALID_STATUS = {"Provisional", "Verified", "Superseded"}
VALID_REG_STATUS = {"Confirmed", "Likely", "Potential"}
VALID_LOGO_STATUS = {"Retrieved", "LocatedNotRetrieved", "NotFound", "Blocked"}
VALID_LOGO_SOURCE = {"OfficialBrandGuide", "OfficialWebsite", "OfficialInvestorRelations", "OtherOfficial"}
VALID_PALETTE_STATUS = {"Official", "Derived", "Unavailable"}
VALID_PALETTE_BASIS = {"OfficialBrandGuide", "OfficialWebsiteCSS", "OfficialLogoAsset", "None"}
PROHIBITED_KEYS = {
    "entity_map_ref", "authority_matrix_ref", "entity_map", "authority_matrix",
    "entities", "authority_rules", "contract_families", "signature_matrix",
    "approval_matrix"
}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def err(errors, msg):
    errors.append(msg)


def walk_keys(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, f"{path}.{key}"
            yield from walk_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk_keys(child, f"{path}[{i}]")


def validate_color(value, label, errors):
    if value is not None and not HEX_RE.fullmatch(str(value)):
        err(errors, f"{label} must be #RRGGBB")


def validate_brand(data, errors):
    brand = data.get("brand_identity")
    if not isinstance(brand, dict):
        err(errors, "profile missing brand_identity")
        return

    logo = brand.get("logo")
    if not isinstance(logo, dict):
        err(errors, "brand_identity missing logo")
    else:
        status = logo.get("status")
        if status not in VALID_LOGO_STATUS:
            err(errors, "brand_identity.logo invalid status")
        if not logo.get("checked_at"):
            err(errors, "brand_identity.logo missing checked_at")
        if status in {"Retrieved", "LocatedNotRetrieved"}:
            if not logo.get("source_url_or_ref") and not logo.get("source_refs"):
                err(errors, "located logo requires official source reference")
            if logo.get("source_type") not in VALID_LOGO_SOURCE:
                err(errors, "located logo requires valid official source_type")
        if status == "Retrieved":
            for key in ["asset_path", "format"]:
                if not logo.get(key):
                    err(errors, f"retrieved logo missing {key}")

    palette = brand.get("palette")
    if not isinstance(palette, dict):
        err(errors, "brand_identity missing palette")
    else:
        pstatus = palette.get("status")
        if pstatus not in VALID_PALETTE_STATUS:
            err(errors, "brand_identity.palette invalid status")
        if not palette.get("checked_at"):
            err(errors, "brand_identity.palette missing checked_at")
        if pstatus in {"Official", "Derived"}:
            if palette.get("source_basis") not in VALID_PALETTE_BASIS - {"None"}:
                err(errors, "available palette requires valid source_basis")
            if not palette.get("source_refs"):
                err(errors, "available palette requires source_refs")
            if not palette.get("primary_color"):
                err(errors, "available palette requires primary_color")
            validate_color(palette.get("primary_color"), "brand_identity.palette.primary_color", errors)
            for field in ["secondary_colors", "accent_colors", "neutral_colors"]:
                for i, color in enumerate(palette.get(field, []) or []):
                    validate_color(color, f"brand_identity.palette.{field}[{i}]", errors)
        if pstatus == "Official" and palette.get("source_basis") != "OfficialBrandGuide":
            err(errors, "Official palette requires OfficialBrandGuide source_basis")

    tokens = brand.get("playbook_brand_tokens")
    if not isinstance(tokens, dict):
        err(errors, "brand_identity missing playbook_brand_tokens")
    else:
        for field in ["primary_ui_color", "accent_ui_color", "surface_color", "text_color"]:
            validate_color(tokens.get(field), f"brand_identity.playbook_brand_tokens.{field}", errors)
        if logo and logo.get("status") == "Retrieved" and not tokens.get("logo_asset_path"):
            err(errors, "retrieved logo requires playbook_brand_tokens.logo_asset_path")
        if logo and logo.get("status") == "LocatedNotRetrieved" and not tokens.get("logo_source_url_or_ref"):
            err(errors, "located logo requires playbook_brand_tokens.logo_source_url_or_ref")


def validate_profile(data, errors):
    for key in ["schema_version", "core_version", "profile_id", "version", "status",
                "organization_name", "organization_type", "organization_type_basis",
                "source_log", "checked_at", "onboarding", "brand_identity"]:
        if key not in data or data[key] in (None, ""):
            err(errors, f"profile missing {key}")

    if data.get("status") not in VALID_STATUS:
        err(errors, "profile invalid status")

    for key, key_path in walk_keys(data):
        if key in PROHIBITED_KEYS:
            err(errors, f"prohibited setup field {key_path}")

    onboarding = data.get("onboarding", {})
    for key in ["company_question_asked", "company_identity_source"]:
        if key not in onboarding:
            err(errors, f"onboarding missing {key}")

    public_market = data.get("public_market", {}) or {}
    if public_market.get("is_public") is True:
        listings = public_market.get("listings", [])
        if not listings:
            err(errors, "public organization requires at least one listing")
        for i, listing in enumerate(listings):
            for key in ["exchange_or_market", "ticker", "source_refs"]:
                if not listing.get(key):
                    err(errors, f"public_market.listings[{i}] missing {key}")
        if data.get("status") == "Verified" and not public_market.get("securities_reporting_regulators"):
            err(errors, "Verified public organization requires securities_reporting_regulators")

    for i, reg in enumerate(data.get("regulatory_footprint", [])):
        for key in ["regulator_name", "jurisdiction", "domain", "applicability_status", "basis", "checked_at"]:
            if not reg.get(key):
                err(errors, f"regulatory_footprint[{i}] missing {key}")
        status = reg.get("applicability_status")
        if status not in VALID_REG_STATUS:
            err(errors, f"regulatory_footprint[{i}] invalid applicability_status")
        if status == "Confirmed" and not reg.get("official_source_refs"):
            err(errors, f"regulatory_footprint[{i}] Confirmed requires official_source_refs")

    validate_brand(data, errors)

    if data.get("status") == "Verified":
        if not data.get("source_log"):
            err(errors, "Verified profile requires source_log")
        if data.get("organization_type") == "Public company" and public_market.get("is_public") is not True:
            err(errors, "Public company requires public_market.is_public=true")


def main(arg):
    path = Path(arg)
    errors = []
    if path.is_dir():
        profile_path = path / "organization-profile.json"
        if not profile_path.exists():
            err(errors, "missing organization-profile.json")
        else:
            validate_profile(load(profile_path), errors)
    else:
        validate_profile(load(path), errors)

    if errors:
        print("INVALID")
        for item in errors:
            print("-", item)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_profile_bundle.py organization-profile.json|SETUP_DIR")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
