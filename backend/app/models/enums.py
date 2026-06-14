# File: backend/app/models/enums.py
"""
Shared enumerations.

WHY: Using Python enums (mapped to SQL Enum columns) constrains values
at both the application and database level. This prevents typos like
'criticl' from ever being stored, which would silently break filtering
and correlation.
"""
import enum


class UserRole(str, enum.Enum):
    """Role-based access control roles. Checked before sensitive actions."""
    INVESTIGATION_OFFICER = "investigation_officer"
    ANALYST = "analyst"
    DISTRICT_ADMIN = "district_admin"
    SYSTEM_ADMIN = "system_admin"


class EntityType(str, enum.Enum):
    """The investigative artifact types the extractor produces."""
    UPI = "upi"
    BANK_ACCOUNT = "bank_account"
    IFSC = "ifsc"
    UTR = "utr"
    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    TELEGRAM = "telegram"
    CRYPTO_WALLET = "crypto_wallet"


class RiskLevel(str, enum.Enum):
    """Severity buckets assigned by the (future) risk-scoring engine."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(str, enum.Enum):
    """Auditable actions. 'VIEW' matters: who looked at what is core."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_USER = "create_user"
    CREATE_CASE = "create_case"
    UPLOAD_EVIDENCE = "upload_evidence"
    EXTRACT_ENTITIES = "extract_entities"
    VIEW_CASE = "view_case"
    VIEW_ENTITY = "view_entity"
    SEARCH = "search"
    EXPORT_REPORT = "export_report"
    EDIT_EVIDENCE_TEXT = "edit_evidence_text"
