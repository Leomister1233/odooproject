import xmlrpc.client

from django.conf import settings as django_settings
from django.db import OperationalError, ProgrammingError

from .models import Client, ClientFeature, CompanyMembership, FeatureFlag
from .runtime import get_active_client


class OdooConfigurationError(Exception):
    pass


FEATURE_CATALOG = [
    {
        "key": "overview",
        "name": "Overview",
        "module": "core",
        "description": "Main workspace dashboard.",
        "default_enabled": True,
        "nav_href": "/dashboard",
        "nav_icon": "overview",
        "nav_title": "Overview",
        "nav_meta": "Shell and quick access",
        "nav_section": "Workspace",
        "nav_match_prefix": "/dashboard",
        "sort_order": 10,
    },
    {
        "key": "customers",
        "name": "Customers",
        "module": "accounting",
        "description": "Customer register and contact information.",
        "default_enabled": True,
        "nav_href": "/customers",
        "nav_icon": "customers",
        "nav_title": "Customers",
        "nav_meta": "Partners and fiscal data",
        "nav_section": "Workspace",
        "nav_match_prefix": "/customers",
        "sort_order": 20,
    },
    {
        "key": "invoices",
        "name": "Invoices",
        "module": "accounting",
        "description": "Customer invoicing workflow.",
        "default_enabled": True,
        "nav_href": "/invoices",
        "nav_icon": "invoices",
        "nav_title": "Invoices",
        "nav_meta": "Draft, post and collect",
        "nav_section": "Workspace",
        "nav_match_prefix": "/invoices",
        "sort_order": 30,
    },
    {
        "key": "payments",
        "name": "Payments",
        "module": "accounting",
        "description": "Receipts and settlement tracking.",
        "default_enabled": True,
        "nav_href": "/payments",
        "nav_icon": "payments",
        "nav_title": "Payments",
        "nav_meta": "Settlement and receipts",
        "nav_section": "Workspace",
        "nav_match_prefix": "/payments",
        "sort_order": 40,
    },
    {
        "key": "vendor_bills",
        "name": "Vendor Bills",
        "module": "accounting",
        "description": "Payables review and due dates.",
        "default_enabled": True,
        "nav_href": "/vendor-bills",
        "nav_icon": "bills",
        "nav_title": "Vendor Bills",
        "nav_meta": "Payables and due dates",
        "nav_section": "Workspace",
        "nav_match_prefix": "/vendor-bills",
        "sort_order": 50,
    },
    {
        "key": "journal_entries",
        "name": "Journal Entries",
        "module": "accounting",
        "description": "Manual and system journal entries.",
        "default_enabled": True,
        "nav_href": "/journal-entries",
        "nav_icon": "journal",
        "nav_title": "Journal Entries",
        "nav_meta": "Manual and system postings",
        "nav_section": "Workspace",
        "nav_match_prefix": "/journal-entries",
        "sort_order": 60,
    },
    {
        "key": "reports",
        "name": "Reports",
        "module": "accounting",
        "description": "Financial reporting views.",
        "default_enabled": True,
        "nav_href": "/reports",
        "nav_icon": "reports",
        "nav_title": "Reports",
        "nav_meta": "Tax and balances",
        "nav_section": "Workspace",
        "nav_match_prefix": "/reports",
        "sort_order": 70,
    },
    {
        "key": "inventory",
        "name": "Inventory",
        "module": "inventory",
        "description": "Inventory dashboard.",
        "default_enabled": True,
        "nav_href": "/inventory",
        "nav_icon": "inventory",
        "nav_title": "Inventory",
        "nav_meta": "Stock and transfers",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory",
        "sort_order": 80,
    },
    {
        "key": "inventory_receipts",
        "name": "Receipts",
        "module": "inventory",
        "description": "Inbound warehouse flow.",
        "default_enabled": True,
        "nav_href": "/inventory/receipts",
        "nav_icon": "receipts",
        "nav_title": "Receipts",
        "nav_meta": "Inbound warehouse flow",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/receipts",
        "sort_order": 90,
    },
    {
        "key": "inventory_products",
        "name": "Products",
        "module": "inventory",
        "description": "Product catalogue and stock quantities.",
        "default_enabled": True,
        "nav_href": "/inventory/products",
        "nav_icon": "inventory",
        "nav_title": "Products",
        "nav_meta": "Catalogue and quantities",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/products",
        "sort_order": 82,
    },
    {
        "key": "inventory_stock",
        "name": "Stock on Hand",
        "module": "inventory",
        "description": "Stock positions by location.",
        "default_enabled": True,
        "nav_href": "/inventory/stock",
        "nav_icon": "inventory",
        "nav_title": "Stock on Hand",
        "nav_meta": "Balances by location",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/stock",
        "sort_order": 84,
    },
    {
        "key": "inventory_transfers",
        "name": "Transfers",
        "module": "inventory",
        "description": "All warehouse transfer documents.",
        "default_enabled": True,
        "nav_href": "/inventory/transfers",
        "nav_icon": "internal_transfers",
        "nav_title": "Transfers",
        "nav_meta": "All stock movements",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/transfers",
        "sort_order": 86,
    },
    {
        "key": "inventory_locations",
        "name": "Locations",
        "module": "inventory",
        "description": "Warehouse and internal stock locations.",
        "default_enabled": True,
        "nav_href": "/inventory/locations",
        "nav_icon": "inventory",
        "nav_title": "Locations",
        "nav_meta": "Warehouse structure",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/locations",
        "sort_order": 88,
    },
    {
        "key": "inventory_deliveries",
        "name": "Deliveries",
        "module": "inventory",
        "description": "Outbound fulfillment flow.",
        "default_enabled": True,
        "nav_href": "/inventory/deliveries",
        "nav_icon": "deliveries",
        "nav_title": "Deliveries",
        "nav_meta": "Outbound fulfillment flow",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/deliveries",
        "sort_order": 100,
    },
    {
        "key": "inventory_internal_transfers",
        "name": "Internal Transfers",
        "module": "inventory",
        "description": "Warehouse internal moves.",
        "default_enabled": True,
        "nav_href": "/inventory/internal-transfers",
        "nav_icon": "internal_transfers",
        "nav_title": "Internal Transfers",
        "nav_meta": "Warehouse moves",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/internal-transfers",
        "sort_order": 110,
    },
    {
        "key": "inventory_adjustments",
        "name": "Adjustments",
        "module": "inventory",
        "description": "Stock adjustment counts.",
        "default_enabled": True,
        "nav_href": "/inventory/adjustments",
        "nav_icon": "adjustments",
        "nav_title": "Adjustments",
        "nav_meta": "Counted stock corrections",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/adjustments",
        "sort_order": 120,
    },
    {
        "key": "inventory_replenishment",
        "name": "Replenishment",
        "module": "inventory",
        "description": "Procurement and rules.",
        "default_enabled": True,
        "nav_href": "/inventory/replenishment",
        "nav_icon": "replenishment",
        "nav_title": "Replenishment",
        "nav_meta": "Rules and procurement",
        "nav_section": "Operations",
        "nav_match_prefix": "/inventory/replenishment",
        "sort_order": 130,
    },
    {
        "key": "fiscal_documents",
        "name": "Fiscal Documents",
        "module": "fiscal",
        "description": "Angola fiscal document and AGT submission tracking.",
        "default_enabled": True,
        "nav_href": "/fiscal/documents",
        "nav_icon": "invoices",
        "nav_title": "Fiscal Documents",
        "nav_meta": "AGT preparation and status",
        "nav_section": "Compliance",
        "nav_match_prefix": "/fiscal",
        "sort_order": 140,
    },
    {
        "key": "platform_admin",
        "name": "Platform Admin",
        "module": "platform",
        "description": "Client and version administration.",
        "default_enabled": True,
        "nav_href": "/platform-admin",
        "nav_icon": "reports",
        "nav_title": "Platform Admin",
        "nav_meta": "Clients, features and releases",
        "nav_section": "Administration",
        "nav_match_prefix": "/platform-admin",
        "sort_order": 1000,
    },
    {
        "key": "fiscal_submissions",
        "name": "AGT Submissions",
        "module": "fiscal",
        "description": "AGT submission attempts and responses.",
        "default_enabled": True,
        "nav_href": "/fiscal/submissions",
        "nav_icon": "reports",
        "nav_title": "AGT Submissions",
        "nav_meta": "Submission status and evidence",
        "nav_section": "Compliance",
        "nav_match_prefix": "/fiscal/submissions",
        "sort_order": 142,
    },
]


def sync_feature_catalog():
    try:
        existing = {feature.key: feature for feature in FeatureFlag.objects.all()}
    except (OperationalError, ProgrammingError):
        return

    for item in FEATURE_CATALOG:
        feature = existing.get(item["key"])
        if feature is None:
            FeatureFlag.objects.create(**item)
            continue

        updates = []
        for field, value in item.items():
            if getattr(feature, field) != value:
                setattr(feature, field, value)
                updates.append(field)
        if updates:
            feature.save(update_fields=updates)


def get_feature_definitions():
    sync_feature_catalog()
    try:
        features = list(FeatureFlag.objects.all())
        if features:
            return features
    except (OperationalError, ProgrammingError):
        pass
    return FEATURE_CATALOG


def get_current_client(hostname=None, session_slug=None):
    try:
        queryset = Client.objects.filter(is_active=True)
        if session_slug:
            client = queryset.filter(slug=session_slug).first()
            if client:
                return client
        if hostname:
            client = queryset.filter(domain__iexact=hostname).first()
            if client:
                return client
        client = queryset.filter(is_default=True).first()
        if client:
            return client
        return queryset.order_by("name").first()
    except (OperationalError, ProgrammingError):
        return None


def get_client_by_domain(hostname):
    if not hostname:
        return None
    try:
        return Client.objects.filter(is_active=True, domain__iexact=hostname).first()
    except (OperationalError, ProgrammingError):
        return None


def resolve_company_membership(user, company=None):
    queryset = CompanyMembership.objects.select_related("company").filter(
        user=user,
        is_active=True,
        company__is_active=True,
    )
    if company:
        membership = queryset.filter(company=company).first()
        if membership:
            return membership, ""
        return None, "This account is not registered for this client workspace."

    default_membership = queryset.filter(is_default=True).first()
    if default_membership:
        return default_membership, ""

    matches = list(queryset[:2])
    if len(matches) == 1:
        return matches[0], ""
    if len(matches) > 1:
        return None, "This account belongs to multiple workspaces. Use your company login URL."
    return None, "No company workspace is registered for this account."


def get_client_feature_map(client):
    feature_definitions = get_feature_definitions()
    if not client:
        return {
            (feature.key if hasattr(feature, "key") else feature["key"]): (
                feature.default_enabled if hasattr(feature, "default_enabled") else feature["default_enabled"]
            )
            for feature in feature_definitions
        }

    try:
        overrides = {
            override.feature.key: override.is_enabled
            for override in ClientFeature.objects.select_related("feature").filter(client=client)
        }
    except (OperationalError, ProgrammingError):
        overrides = {}

    feature_map = {}
    for feature in feature_definitions:
        key = feature.key if hasattr(feature, "key") else feature["key"]
        default_enabled = feature.default_enabled if hasattr(feature, "default_enabled") else feature["default_enabled"]
        feature_map[key] = overrides.get(key, default_enabled)
    return feature_map


def _normalize_feature(feature):
    if hasattr(feature, "key"):
        return {
            "key": feature.key,
            "name": feature.name,
            "module": feature.module,
            "description": feature.description,
            "default_enabled": feature.default_enabled,
            "nav_href": feature.nav_href,
            "nav_icon": feature.nav_icon,
            "nav_title": feature.nav_title,
            "nav_meta": feature.nav_meta,
            "nav_section": feature.nav_section,
            "nav_match_prefix": feature.nav_match_prefix,
            "sort_order": feature.sort_order,
        }
    return dict(feature)


def build_navigation_for_client(client, request_path):
    feature_map = get_client_feature_map(client)
    sections = []
    sections_by_name = {}

    for raw_feature in get_feature_definitions():
        feature = _normalize_feature(raw_feature)
        if not feature["nav_href"] or not feature_map.get(feature["key"], feature["default_enabled"]):
            continue

        section_name = feature["nav_section"] or "Workspace"
        section = sections_by_name.get(section_name)
        if section is None:
            section = {"label": section_name, "items": []}
            sections_by_name[section_name] = section
            sections.append(section)

        href = feature["nav_href"]
        match_prefix = feature["nav_match_prefix"] or href
        is_active = request_path == href or request_path.startswith(f"{match_prefix}/") or request_path == match_prefix
        section["items"].append(
            {
                "key": feature["key"],
                "module": feature["module"],
                "href": href,
                "icon_name": feature["nav_icon"],
                "title": feature["nav_title"] or feature["name"],
                "meta": feature["nav_meta"] or feature["description"],
                "is_active": is_active,
            }
        )

    active_items = [item for section in sections for item in section["items"] if item["is_active"]]
    if len(active_items) > 1:
        selected = max(active_items, key=lambda item: len(item["href"]))
        for item in active_items:
            item["is_active"] = item is selected
    return sections


def get_client_odoo_settings(client=None):
    client = client or get_active_client()
    if client is None:
        raise OdooConfigurationError("No company workspace is selected for this session.")

    registration = client.odoo_databases.filter(is_active=True, is_default=True).first()
    if registration is None:
        registration = client.odoo_databases.filter(is_active=True).order_by("id").first()
    if registration is None:
        raise OdooConfigurationError(
            f"No active Odoo database is registered for {client.name}. Contact the company administrator."
        )

    settings = {
        "url": django_settings.ODOO_SHARED_URL,
        "db": registration.database_name.strip(),
        "username": client.odoo_username.strip(),
        "password": client.get_odoo_password(),
        "company": registration.odoo_company.strip(),
        "client_slug": client.slug,
        "client_name": client.name,
        "registration_id": registration.pk,
    }
    if not all(settings[key] for key in ("url", "db", "username", "password")):
        raise OdooConfigurationError(
            f"The company Odoo credentials for {client.name} are incomplete. Contact the platform administrator."
        )
    return settings


def test_odoo_connection(odoo_settings):
    url = str(odoo_settings.get("url") or "").strip()
    db = str(odoo_settings.get("db") or "").strip()
    username = str(odoo_settings.get("username") or "").strip()
    password = str(odoo_settings.get("password") or "").strip()

    if not url or not db or not username or not password:
        raise Exception("Odoo URL, database, username, and password are required to test the connection.")

    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        version = common.version()
        uid = common.authenticate(db, username, password, {})
    except OSError as exc:
        raise Exception("Could not reach the Odoo server. Verify the URL and that the server is online.") from exc
    except xmlrpc.client.Fault as exc:
        raise Exception(f"Odoo API error: {exc.faultString}") from exc

    if not uid:
        raise Exception("Odoo authentication failed. Check the database, username, and password.")

    return {
        "server_version": version.get("server_version", "-"),
        "server_version_info": version.get("server_version_info", []),
        "protocol_version": version.get("protocol_version", "-"),
        "uid": uid,
        "url": url,
        "db": db,
        "username": username,
    }
