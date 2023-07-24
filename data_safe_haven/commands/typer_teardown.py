"""Command-line application for tearing down a Data Safe Haven component, delegating the details to a subcommand"""
# Standard library imports
from typing import Annotated

# Third party imports
import typer

# Local imports
from data_safe_haven.commands.teardown_backend_command import TeardownBackendCommand
from data_safe_haven.commands.teardown_shm_command import TeardownSHMCommand
from data_safe_haven.commands.teardown_sre_command import TeardownSRECommand

teardown_command_group = typer.Typer()


@teardown_command_group.command(help="Tear down a deployed Data Safe Haven backend.")
def backend() -> None:
    TeardownBackendCommand()()


@teardown_command_group.command(help="Tear down a deployed a Safe Haven Management component.")
def shm() -> None:
    TeardownSHMCommand()()


@teardown_command_group.command(help="Tear down a deployed a Secure Research Environment component.")
def sre(
    name: Annotated[str, typer.Argument(help="Name of SRE to teardown.")],
) -> None:
    TeardownSRECommand()(name)
