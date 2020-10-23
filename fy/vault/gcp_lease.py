#!/usr/bin/env python

import json
import os
import pathlib
from base64 import b64decode
from dataclasses import dataclass, field
from pathlib import Path

from .vault_lease import VaultLease


@dataclass
class GCPVaultLease(VaultLease):
    project_id: str
    role: str
    credentials: str = field(init=False)
    credentials_file: str = field(init=False)
    environment: any = None

    def read(self):
        self._set_path()
        self._set_filename()
        self._set_lease()
        self._set_lease_file()
        self._write_lease()
        self._set_credentials()
        self._set_credentials_file()
        self._write_credentials()
        self._set_lease_id()

    def load(self):
        self._set_path()
        self._set_filename()
        self._set_lease_file()
        self._load_vault_lease()
        self._load_credentials()
        if self.lease:
            self._set_lease_id(silent=True)

    def _load_vault_lease(self):
        try:
            with open(self.lease_file, "r") as vault_lease:
                self.lease = json.loads(vault_lease.read())
        except FileNotFoundError as error:
            self.lease = None
            print(
                f"failed to load vault lease for project '{self.project_id}': {error}'"
            )

    def _load_credentials(self):
        self.credentials_file = os.path.join(
            self.environment.credentials_dir, self.filename
        )
        try:
            with open(self.credentials_file, "r") as credentials:
                self.credentials = json.loads(credentials.read())
        except FileNotFoundError as error:
            print(
                f"failed to load credentials for project '{self.project_id}': {error}'"
            )

    def _set_path(self):
        self.path = f"gcp_{self.project_id}/key/{self.role}"

    def _set_filename(self):
        self.filename = f"{self.project_id}_deploy.json"

    def _set_credentials(self):
        private_key_data = self.lease["data"]["private_key_data"]
        self.credentials = json.loads(b64decode(private_key_data).decode("UTF-8"))

    def _set_credentials_file(self):
        self.credentials_file = os.path.join(
            self.environment.credentials_dir, f"{self.project_id}_{self.role}.json",
        )

    def _write_credentials(self):
        Path(self.environment.credentials_dir).mkdir(parents=True, exist_ok=True)
        with open(self.credentials_file, "w") as file:
            print(f"writing credentials file: {self.credentials_file}")
            file.write(json.dumps(self.credentials))

    def _set_lease_file(self):
        self.lease_file = os.path.join(
            self.environment.vault_dir, f"{self.project_id}_{self.role}.json",
        )

    def _write_lease(self):
        pathlib.Path(self.environment.vault_dir).mkdir(parents=True, exist_ok=True)
        with open(self.lease_file, "w") as file:
            print(f"writing lease file: {self.lease_file}")
            file.write(json.dumps(self.lease))

    def _revoke_cleanup(self):
        try:
            os.remove(self.lease_file)
            print(f"removed lease file: {self.lease_file}")
        except FileNotFoundError as error:
            print(error)

        try:
            os.remove(self.credentials_file)
            print(f"removed credentials file: {self.credentials_file}")
        except FileNotFoundError as error:
            print(error)
