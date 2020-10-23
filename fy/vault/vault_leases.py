#!/usr/bin/env python

from dataclasses import dataclass, field
from typing import List

from .gcp_lease import GCPVaultLease
from .vault_lease import VaultLease


@dataclass
class VaultLeases:
    leases: List[VaultLease] = field(default_factory=list)
    environment: any = None

    def login(self):
        print("not implemented!")
        pass

    def load(self):
        self._load_default_credentials()
        self._load_additional_credentials()

    def _load_default_credentials(self):
        lease = GCPVaultLease(
            environment=self.environment,
            project_id=self.environment.project_id,
            role=self.environment.vault_role,
        )
        self.leases.append(lease)
        lease.load()

    def _load_additional_credentials(self):
        for project in self.environment.additional_projects:
            lease = GCPVaultLease(
                environment=self.environment,
                project_id=project["project_id"],
                role=project["vault_role"],
            )
            self.leases.append(lease)
            lease.load()

    def read(self):
        self._read_default_credentials()
        self._read_additional_credentials()

    def _read_default_credentials(self):
        lease = GCPVaultLease(
            environment=self.environment,
            project_id=self.environment.project_id,
            role=self.environment.vault_role,
        )
        self.leases.append(lease)
        lease.read()

    def _read_additional_credentials(self):
        for project in self.environment.additional_projects:
            print()
            lease = GCPVaultLease(
                environment=self.environment,
                project_id=project["project_id"],
                role=project["vault_role"],
            )
            self.leases.append(lease)
            lease.read()

    def revoke(self):
        active_leases = [lease for lease in self.leases if lease.lease]
        if not active_leases:
            print("\nnothing to be done")
        else:
            for lease in active_leases:
                print
                lease.revoke()

    def list(self):
        active_leases = [lease for lease in self.leases if lease.lease]
        if not active_leases:
            print("no active leases")
        else:
            for lease in active_leases:
                print(lease)
