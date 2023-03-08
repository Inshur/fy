#!/usr/bin/env python
#
# NOTE
# * this is probably the most difficult module in FY to get right
#   originally FY was designed to work with AWS and GCP deployments
#   but given that we are now primarily focused on GCP, AWS support
#   has been dropped
# * it may make sense to split out different subsets of environment
#   variables from this module at some point..
#

import json
import os
import re
import string
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePath

import yaml

try:
    from sh import gcloud
except ImportError as error:
    for command in ["gcloud"]:
        if re.search(r".*'" + command + "'.*", str(error)):
            print(f"Could not find {command}(1) in path, please install {command}!")
            exit(127)


class EnvironmentError(Exception):
    pass


@dataclass
class Environment:
    org_id: str = field(init=False)

    region: str = field(init=False)
    environment: str = field(init=False)
    deployment: str = field(init=False)

    environment_type: str = field(init=False)

    deployment_type: str = field(init=False)
    deployment_path: str = os.environ["PWD"]

    iac_root_dir: str = field(init=False)

    config_dir: str = os.path.join(os.environ["HOME"], ".config/fy")

    project_id: any = None
    project_number: any = None

    k8s_cluster: any = None
    k8s_app: any = None
    env: any = None

    credentials_dir: any = None
    gcp_account_original: any = None
    additional_projects: any = None
    google_application_credentials: any = None
    original_kube_context: any = None
    kubectl_context: any = None

    opa_config: dict = None

    # Bare minimum initialization that can be used for most basic operations
    def __post_init__(self):
        self._detect_iac_root()
        self._detect_deployment_type()
        self._configure_deployment_environment()
        self._set_gcp_account_original()
        self._set_env()

    #
    # Initializers
    #

    def initialize_skeleton(self):
        self._set_project_number()

    def initialize_gcp(self):
        self._set_org_id()
        self._set_project_id()

    def initialize_opa(self):
        self._set_opa_config()

    #
    # Common environment
    #

    def _detect_iac_root(self):
        source_path = Path(self.deployment_path)
        count = 0
        for dir in source_path.parts:
            if dir == "deployment":
                self.iac_root_dir = Path(*source_path.parts[:count])
                return
            count += 1
        raise EnvironmentError(
            "cannot detect iac root directory, does 'deployment' "
            "directory exist in current working directory path?"
        )

    def _detect_deployment_type(self):
        if PurePath(self.deployment_path).match("**/deployment/*/*/*/app/cluster/*"):
            self.deployment_type = "k8s_cluster"
        elif PurePath(self.deployment_path).match(
                "**/deployment/*/*/*/app/cluster/*/*"
        ):
            self.deployment_type = "k8s_app"
        elif PurePath(self.deployment_path).match("**/deployment/*/*/*/infra"):
            self.deployment_type = "infra"
        else:
            self.deployment_type = None

    def _configure_deployment_environment(self):
        deployment_path_elements = PurePath(self.deployment_path).parts

        if self.deployment_type == "infra":
            self.region = deployment_path_elements[-4]
            self.environment = deployment_path_elements[-3]
            self.deployment = deployment_path_elements[-2]
            self.environment_type = self.environment.rstrip(string.digits)
        elif self.deployment_type == "k8s_cluster":
            self.region = deployment_path_elements[-6]
            self.environment = deployment_path_elements[-5]
            self.deployment = deployment_path_elements[-4]
            self.environment_type = self.environment.rstrip(string.digits)
            self.k8s_cluster = deployment_path_elements[-1]
        elif self.deployment_type == "k8s_app":
            self.region = deployment_path_elements[-7]
            self.environment = deployment_path_elements[-6]
            self.deployment = deployment_path_elements[-5]
            self.environment_type = self.environment.rstrip(string.digits)
            self.k8s_cluster = deployment_path_elements[-2]
            self.k8s_app = deployment_path_elements[-1]
        else:
            raise EnvironmentError(
                f"Not in a valid deployment sub directory: {self.deployment_path}"
            )

    def _set_gcp_account_original(self):
        active = self._get_active_gcp_account()
        if active:
            self.gcp_account_original = active[0]

    #
    # Skeleton environment
    #

    def _set_project_number(self):
        project_data = json.loads(
            gcloud.projects.describe(
                "--format", "json", self.project_id, _env=self.env,
            ).stdout.decode("UTF-8")
        )
        self.project_number = project_data["projectNumber"]

    #
    # GKE
    #

    def activate_container_cluster_context(self):
        print(f"\n==> activate container cluster credentials\n")
        zone = self._detect_cluster_zone()
        print(
            gcloud.container.clusters(
                f"get-credentials",
                self.k8s_cluster,
                f"--region={zone}",
                f"--project={self.project_id}",
                _err_to_out=True,
                _env=self.env,
            )
            .stdout.decode("UTF-8")
            .rstrip()
        )
        self.kubectl_context = f"gke_{self.project_id}_{zone}_{self.k8s_cluster}"

    # FIXME
    # * this is shonky and assumes that there wont
    #   be multiple clusters with the same name in the
    #   same region
    # * gcp conflates "region" and "zone" which causes this
    #   issue.. it's often referred to as "location" but
    #   is specified with the "--region" flag
    def _detect_cluster_zone(self):
        zones = self._detect_region_zones()
        zones.append(self.region)

        for zone in zones:
            data = json.loads(
                gcloud.container.clusters.list(
                    f"--region={zone}",
                    f"--project={self.project_id}",
                    "--format=json",
                    _env=self.env,
                ).stdout.decode("UTF-8")
            )

            clusters = [
                cluster for cluster in data if cluster["name"] == self.k8s_cluster
            ]

            if clusters:
                return zone

    def _detect_region_zones(self):
        regions = json.loads(
            gcloud.compute.zones.list(
                "--format=json", f"--project={self.project_id}", _env=self.env,
            ).stdout.decode("UTF-8")
        )

        zones = [
            region["name"]
            for region in regions
            if region["name"].startswith(self.region)
        ]

        return zones

    #
    # GCP environment
    #

    def _set_project_id(self):
        self.project_id = f"{self.org_id}-{self.environment}-{self.deployment}"

    def _set_org_id(self):
        fyrc = Path(self.iac_root_dir, ".fyrc.yaml")
        try:
            self.org_id = yaml.safe_load(open(fyrc))["org_id"]
        except FileNotFoundError:
            print(f"Please create config file in iac root directory: {fyrc}")
            exit(1)
        #  FIXME: this looks wrong - shouldn't this be KeyError?
        except TypeError:
            print(f"Invalid fyrc file, is org_id set?")
            exit(1)

    #
    # OPA config
    #

    def _set_opa_config(self):
        fyrc = Path(self.iac_root_dir, ".fyrc.yaml")
        try:
            self.opa_config = yaml.safe_load(open(fyrc))["config"]["opa"]
        except FileNotFoundError:
            print(f"Please create config file in iac root directory: {fyrc}")
            exit(1)
        except TypeError:
            print(f"Invalid fyrc file, is config opa set?")
            exit(1)

    #
    # Environment output
    #

    def properties(self, obfuscate):
        properties = asdict(self)

        populated_properties = {
            key: value for (key, value) in asdict(self).items() if value is not None
        }

        properties = self._filter_keys(
            populated_properties,
            [ "credentials_dir", "env", "kubectl_context"],
        )

        if obfuscate:
            self._obfuscate_values(properties, ["vault_token"])

        return properties

    def pretty_print(self, args, obfuscate: False):
        self.initialize_gcp()

        padding = len(max(self.properties(obfuscate).keys(), key=len)) + 1

        print("\n==> environment\n")
        return "\n".join(
            f"{key.ljust(padding)}= {value}"
            for key, value in self.properties(obfuscate).items()
        )

    def sh(self, args, obfuscate: False):
        self.initialize_gcp()

        return "\n".join(
            f'{key.upper()}="{value}"'
            for key, value in self.properties(obfuscate).items()
        )

    def json(self, args, obfuscate: False):
        self.initialize_gcp()

        return json.dumps(self.properties(obfuscate))

    def json_upper_keys(self, obfuscate: False):
        return {key.upper(): value for key, value in self.properties(obfuscate).items()}

    def _filter_keys(self, properties, keys):
        return {key: value for key, value in properties.items() if key not in keys}

    def _obfuscate_values(self, properties, keys):
        for key in keys:
            if properties.get(key):
                properties[key] = "*" * len(properties[key])

    #
    # Common methods
    #

    def _set_env(self):
        self.env = {
            **os.environ.copy(),
            **{"TF_IN_AUTOMATION": "true"},
            **{"KUBECONFIG": os.path.join(self.config_dir, "kube_config.yaml")},
        }

    def _get_active_gcp_account(self):
        accounts = json.loads(
            gcloud.auth.list("--format", "json", _env=self.env).stdout.decode("UTF-8")
        )
        active = [
            account["account"] for account in accounts if account["status"] == "ACTIVE"
        ]
        return active
