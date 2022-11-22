# Standard library imports
from typing import Any


class ResearchUser:
    def __init__(
        self,
        account_enabled: bool = None,
        country: str = None,
        email_address: str = None,
        given_name: str = None,
        phone_number: str = None,
        sam_account_name: str = None,
        surname: str = None,
        user_principal_name: str = None,
    ):
        self.account_enabled = account_enabled
        self.country = country
        self.email_address = email_address
        self.given_name = given_name
        self.phone_number = phone_number
        self.sam_account_name = sam_account_name
        self.surname = surname
        self.user_principal_name = user_principal_name

    @property
    def display_name(self) -> str:
        return f"{self.given_name} {self.surname}"

    @property
    def preferred_username(self) -> str:
        if self.user_principal_name:
            return self.user_principal_name
        return self.username

    @property
    def username(self) -> str:
        if self.sam_account_name:
            return self.sam_account_name
        return f"{self.given_name}.{self.surname}".lower()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ResearchUser):
            return any(
                [
                    self.username == other.username,
                    self.preferred_username == other.preferred_username,
                ]
            )
        return False

    def __str__(self) -> str:
        return f"{self.display_name} '{self.username}'."
