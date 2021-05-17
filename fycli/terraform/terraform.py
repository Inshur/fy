#!/usr/bin/env python

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import Popen

from google.cloud import storage

from ..environment.environment import Environment

try:
    from sh import tfsec
except ImportError as error:
    for command in ["tfsec"]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"could not find {command}(1) in path, please install {command}!")
            exit(127)


@dataclass
class Terraform:
    environment: Environment

    def init(self):
        bucket = "".join(
            [
                f"{self.environment.org_id}-terraform-state-",
                f"{self.environment.region}",
                f"-{self.environment.environment}",
                f"-{self.environment.deployment}",
            ]
        )

        command = "".join(
            [
                f"terraform init -backend-config=bucket={bucket}",
                " -backend-config=prefix=terraform.state",
            ]
        )

        print(f"state: gs://{bucket}/terraform.state\n")
        self._exec(command)

    def modules_update(self):
        cwd = os.environ["PWD"]
        modules_file = Path(cwd, ".terraform/modules/modules.json")

        bucket_name = "".join(
            [
                f"{self.environment.org_id}-terraform-state",
                f"-{self.environment.region}",
                f"-{self.environment.environment}",
                f"-{self.environment.deployment}",
            ]
        )

        if modules_file.exists():
            self._upload_blob(
                bucket_name, str(modules_file), "terraform.modules/modules.json"
            )
        else:
            print(f"File not found: {modules_file}")
            print(f"Please generate modules file by running an apply")

    def validate(self):
        self._exec("terraform validate")

    def plan(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_PLAN"):
            self._exec(f"terraform plan {os.environ.get('TERRAFORM_CLI_ARGS_PLAN')}")
        else:
            self._exec("terraform plan")

    # FIXME
    # * probably replace this with --terraform-args argument?
    def apply(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_APPLY"):
            self._exec(f"terraform apply {os.environ.get('TERRAFORM_CLI_ARGS_APPLY')}")
        else:
            self._exec("terraform apply")

    def destroy(self):
        if os.environ.get("TERRAFORM_CLI_ARGS_DESTROY"):
            self._exec(
                f"terraform destroy {os.environ.get('TERRAFORM_CLI_ARGS_DESTROY')}"
            )
        else:
            self._exec("terraform destroy")

    def tfsec(self):
        # * ignore GCP002 error about unencrypted buckets since buckets are
        #   encrypted by default, see: https://github.com/liamg/tfsec/issues/137
        output = (
            tfsec(".", "--exclude=GCP002", _ok_code=[0, 1])
            .stdout.decode("UTF-8")
            .rstrip()
        )

        # trim this pointless output when no problems detected: '0 potential problems detected:'
        if output.find("No problems detected!") == -1:
            print(output)
        else:
            print("\nNo problems detected!")

    # NOTE
    # * using popen to try to fix github action output ordering..
    # * this can probably be changed back to use 'sh' since execution
    #    is now wrapped in script(1)
    def _exec(self, command):
        process = Popen(
            command,
            shell=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=self.environment.env,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        out, err = process.communicate()

        if process.returncode != 0:
            exit(process.returncode)

    def _upload_blob(self, bucket_name, source_file_name, destination_blob_name):
        """Uploads a file to the bucket."""
        # The ID of your GCS bucket
        # bucket_name = "your-bucket-name"
        # The path to your file to upload
        # source_file_name = "local/path/to/file"
        # The ID of your GCS object
        # destination_blob_name = "storage-object-name"

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)

        print(f"Uploaded module data to gs://{bucket_name}/{destination_blob_name}")
