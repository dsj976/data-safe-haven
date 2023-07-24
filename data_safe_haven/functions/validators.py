# Standard library imports
import ipaddress
import re
from typing import Optional

# Third-party imports
import pytz
import typer


def validate_aad_guid(aad_guid: Optional[str]) -> Optional[str]:
    if aad_guid is not None:
        if not re.match(
            r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
            aad_guid,
        ):
            raise typer.BadParameter(
                "Expected GUID, for example '10de18e7-b238-6f1e-a4ad-772708929203'"
            )
    return aad_guid


def validate_azure_location(azure_location: Optional[str]) -> Optional[str]:
    if azure_location is not None:
        if not re.match(r"^[a-z]+[0-9]?[a-z]*$", azure_location):
            raise typer.BadParameter(
                "Expected valid Azure location, for example 'uksouth'"
            )
    return azure_location


def validate_azure_vm_sku(azure_vm_sku: Optional[str]) -> Optional[str]:
    if azure_vm_sku is not None:
        if not re.match(r"^(Standard|Basic)_\w+$", azure_vm_sku):
            raise typer.BadParameter(
                "Expected valid Azure VM SKU, for example 'Standard_D2s_v4'"
            )
    return azure_vm_sku


def validate_email_address(email_address: Optional[str]) -> Optional[str]:
    if email_address is not None:
        if not re.match(r"^\S+@\S+$", email_address):
            raise typer.BadParameter(
                "Expected valid email address, for example 'sherlock@holmes.com'"
            )
    return email_address


def validate_ip_address(
    ip_address: Optional[str],
) -> Optional[str]:
    try:
        if ip_address:
            return str(ipaddress.ip_network(ip_address))
        return None
    except Exception:
        raise typer.BadParameter("Expected valid IPv4 address, for example '1.1.1.1'")


def validate_timezone(timezone: Optional[str]) -> Optional[str]:
    if timezone is not None:
        if timezone not in pytz.all_timezones:
            raise typer.BadParameter(
                "Expected valid timezone, for example 'Europe/London'"
            )
    return timezone
