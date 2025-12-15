import re
from typing import Optional


def normalize_address(street: str) -> str:
    """
    Normalize street address for consistent matching.

    Examples:
        "123 Main Street, Apt. 4" → "123 MAIN ST APT 4"
        "456 Oak Avenue" → "456 OAK AVE"
        "789 First Blvd #100" → "789 FIRST BLVD UNIT 100"
    """
    if not street:
        return ""

    # Uppercase
    street = street.upper()

    # Standard abbreviations
    replacements = {
        " STREET": " ST",
        " AVENUE": " AVE",
        " BOULEVARD": " BLVD",
        " DRIVE": " DR",
        " LANE": " LN",
        " ROAD": " RD",
        " COURT": " CT",
        " CIRCLE": " CIR",
        " APARTMENT": " APT",
        " SUITE": " STE",
        " UNIT": " UNIT",
        " #": " UNIT ",
        "APT.": "APT",
        "STE.": "STE",
    }

    for full, abbr in replacements.items():
        street = street.replace(full, abbr)

    # Remove punctuation
    street = re.sub(r'[.,]', '', street)

    # Remove extra whitespace
    street = ' '.join(street.split())

    return street


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to digits only.

    Examples:
        "(555) 123-4567" → "5551234567"
        "555-123-4567" → "5551234567"
        "+1 555 123 4567" → "5551234567"
    """
    if not phone:
        return None

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Remove leading '1' if present (US country code)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Return None if not a valid 10-digit US phone
    if len(digits) != 10:
        return None

    return digits


def normalize_email(email: Optional[str]) -> Optional[str]:
    """
    Normalize email address to lowercase.

    Examples:
        "John@Email.COM" → "john@email.com"
        "TEST@EXAMPLE.COM" → "test@example.com"
    """
    if not email:
        return None

    return email.lower().strip()


def normalize_state(state: str) -> str:
    """
    Normalize state code to uppercase.

    Examples:
        "ca" → "CA"
        "Ca" → "CA"
    """
    if not state:
        return ""

    return state.upper().strip()


def normalize_zip(zip_code: str) -> str:
    """
    Normalize ZIP code (keep only first 5 digits).

    Examples:
        "90210-1234" → "90210"
        "90210" → "90210"
    """
    if not zip_code:
        return ""

    # Extract first 5 digits
    digits = re.sub(r'\D', '', zip_code)
    return digits[:5] if len(digits) >= 5 else digits
