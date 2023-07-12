"""Command-line application for deploying a Data Safe Haven from project files"""
# Standard library imports
from typing import List, Optional
from typing_extensions import Annotated

# Third party imports
import pytz
import typer

# Local imports
from data_safe_haven.config import Config, DotFileSettings
from data_safe_haven.exceptions import (
    DataSafeHavenConfigException,
    DataSafeHavenException,
    DataSafeHavenInputException,
)
from data_safe_haven.external import GraphApi
from data_safe_haven.functions import (
    password,
    validate_aad_guid,
    validate_email_address,
    validate_ip_address,
    validate_timezone,
)
from data_safe_haven.provisioning import SHMProvisioningManager
from data_safe_haven.pulumi import PulumiStack
from .base_command import BaseCommand


class DeploySHMCommand(BaseCommand):
    """Deploy a Safe Haven Management component"""

    def entrypoint(
        self,
        aad_tenant_id: Annotated[
            Optional[str],
            typer.Option(
                "--aad-tenant-id",
                "-a",
                help="The tenant ID for the AzureAD where users will be created, for example '10de18e7-b238-6f1e-a4ad-772708929203'.",
                callback=validate_aad_guid,
            ),
        ] = None,
        admin_email_address: Annotated[
            Optional[str],
            typer.Option(
                "--email",
                "-e",
                help="The email address where your system deployers and administrators can be contacted.",
                callback=validate_email_address,
            ),
        ] = None,
        admin_ip_addresses: Annotated[
            Optional[List[str]],
            typer.Option(
                "--ip-address",
                "-i",
                help="An IP address or range used by your system deployers and administrators. [*may be specified several times*]",
                callback=lambda ips: [validate_ip_address(ip) for ip in ips],
            ),
        ] = None,
        fqdn: Annotated[
            Optional[str],
            typer.Option(
                "--fqdn",
                "-f",
                help="The domain that SHM users will belong to.",
            ),
        ] = None,
        timezone: Annotated[
            Optional[str],
            typer.Option(
                "--timezone",
                "-t",
                help="The timezone that this Data Safe Haven deployment will use.",
                callback=validate_timezone,
            ),
        ] = None,
    ) -> None:
        """Typer command line entrypoint"""
        try:
            # Use dotfile settings to load the job configuration
            try:
                settings = DotFileSettings()
            except DataSafeHavenInputException as exc:
                raise DataSafeHavenInputException(
                    f"Unable to load project settings. Please run this command from inside the project directory.\n{str(exc)}"
                ) from exc
            config = Config(settings.name, settings.subscription_name)
            self.update_config(
                config,
                aad_tenant_id=aad_tenant_id,
                admin_email_address=admin_email_address,
                admin_ip_addresses=admin_ip_addresses,
                fqdn=fqdn,
                timezone=timezone,
            )

            # Add the SHM domain to AzureAD as a custom domain
            graph_api = GraphApi(
                tenant_id=config.shm.aad_tenant_id,
                default_scopes=[
                    "Application.ReadWrite.All",
                    "Domain.ReadWrite.All",
                    "Group.ReadWrite.All",
                ],
            )
            verification_record = graph_api.add_custom_domain(config.shm.fqdn)

            # Initialise Pulumi stack
            stack = PulumiStack(config, "SHM")
            # Set Azure options
            stack.add_option("azure-native:location", config.azure.location)
            stack.add_option(
                "azure-native:subscriptionId", config.azure.subscription_id
            )
            stack.add_option("azure-native:tenantId", config.azure.tenant_id)
            # Add necessary secrets
            stack.add_secret("password-domain-admin", password(20))
            stack.add_secret("password-domain-azure-ad-connect", password(20))
            stack.add_secret("password-domain-computer-manager", password(20))
            stack.add_secret("password-domain-ldap-searcher", password(20))
            stack.add_secret("password-update-server-linux-admin", password(20))
            stack.add_secret("verification-azuread-custom-domain", verification_record)

            # Deploy Azure infrastructure with Pulumi
            stack.deploy()

            # Add the SHM domain as a custom domain in AzureAD
            graph_api.verify_custom_domain(
                config.shm.fqdn, stack.output("fqdn_nameservers")
            )

            # Add Pulumi infrastructure information to the config file
            config.read_stack(stack.stack_name, stack.local_stack_path)

            # Upload config to blob storage
            config.upload()

            # Provision SHM with anything that could not be done in Pulumi
            manager = SHMProvisioningManager(
                subscription_name=config.subscription_name,
                stack=stack,
            )
            manager.run()
        except DataSafeHavenException as exc:
            raise DataSafeHavenException(
                f"Could not deploy Data Safe Haven Management environment.\n{str(exc)}"
            ) from exc

    def update_config(
        self,
        config: Config,
        aad_tenant_id: Optional[str] = None,
        admin_email_address: Optional[str] = None,
        admin_ip_addresses: Optional[List[str]] = None,
        fqdn: Optional[str] = None,
        timezone: Optional[str] = None,
    ) -> None:
        # Update AzureAD tenant ID
        print(config)
        if aad_tenant_id is not None:
            if config.shm.aad_tenant_id and (config.shm.aad_tenant_id != aad_tenant_id):
                self.logger.debug(
                    f"Overwriting existing AzureAD tenant ID {config.shm.aad_tenant_id}"
                )
            self.logger.info(
                f"Setting [bold]AzureAD tenant ID[/] to [green]{aad_tenant_id}[/]."
            )
            config.shm.aad_tenant_id = aad_tenant_id
        if not config.shm.aad_tenant_id:
            raise DataSafeHavenConfigException(
                "No AzureAD tenant ID was found. Use [bright_cyan]'--aad-tenant-id / -a'[/] to set one."
            )

        # Update admin email address
        if admin_email_address is not None:
            if config.shm.admin_email_address and (
                config.shm.admin_email_address != admin_email_address
            ):
                self.logger.debug(
                    f"Overwriting existing admin email address {config.shm.admin_email_address}"
                )
            self.logger.info(
                f"Setting [bold]admin email address[/] to [green]{admin_email_address}[/]."
            )
            config.shm.admin_email_address = admin_email_address
        if not config.shm.admin_email_address:
            raise DataSafeHavenConfigException(
                "No admin email address was found. Use [bright_cyan]'--email / -e'[/] to set one."
            )

        # Update admin IP addresses
        if admin_ip_addresses:
            if config.shm.admin_ip_addresses and (
                config.shm.admin_ip_addresses != admin_ip_addresses
            ):
                self.logger.debug(
                    f"Overwriting existing admin IP addresses {config.shm.admin_ip_addresses}"
                )
            self.logger.info(
                f"Setting [bold]admin IP addresses[/] to [green]{admin_ip_addresses}[/]."
            )
            config.shm.admin_ip_addresses = admin_ip_addresses
        if len(config.shm.admin_ip_addresses) == 0:
            raise DataSafeHavenConfigException(
                "No admin IP addresses were found. Use [bright_cyan]'--ip-address / -i'[/] to set one."
            )

        # Update FQDN
        if fqdn is not None:
            if config.shm.fqdn and (config.shm.fqdn != fqdn):
                self.logger.debug(
                    f"Overwriting existing fully-qualified domain name {config.shm.fqdn}"
                )
            self.logger.info(
                f"Setting [bold]fully-qualified domain name[/] to [green]{fqdn}[/]."
            )
            config.shm.fqdn = fqdn
        if not config.shm.fqdn:
            raise DataSafeHavenConfigException(
                "No fully-qualified domain name was found. Use [bright_cyan]'--fqdn / -f'[/] to set one."
            )

        # Update timezone if it passes validation
        if timezone is not None:
            if timezone not in pytz.all_timezones:
                self.logger.error(
                    f"Invalid value '{timezone}' provided for 'timezone'."
                )
            else:
                if config.shm.timezone and (config.shm.timezone != timezone):
                    self.logger.debug(
                        f"Overwriting existing timezone {config.shm.timezone}"
                    )
                self.logger.info(f"Setting [bold]timezone[/] to [green]{timezone}[/].")
                config.shm.timezone = timezone
        if not config.shm.timezone:
            raise DataSafeHavenConfigException(
                "No timezone was found. Use [bright_cyan]'--timezone / -t'[/] to set one."
            )
