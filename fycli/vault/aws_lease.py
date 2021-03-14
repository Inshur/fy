#!/usr/bin/env python

from dataclasses import dataclass, field

from .vault_lease import VaultLease


@dataclass
class AWSVaultLease(VaultLease):
    account_name: str = field(init=False)
    aws_access_key_id: str = field(init=False)
    aws_secret_access_key: str = field(init=False)

    def init(self):
        self.set_lease(f"aws_{self.account_name}/creds/deploy")
        self.set_lease_id()
        self.set_credentials()
        self.configure_environment()

    def set_credentials(self):
        self.aws_access_key_id = self.lease["data"]["access_key"]
