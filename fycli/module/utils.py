import builtins
import functools
import os
import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import call, run

try:
    import yaml
except ModuleNotFoundError:
    print(f"Error: Please install missing python pip module: pyyaml")
    exit(1)

try:
    import semver
except ModuleNotFoundError as error:
    print(f"Error: Please install missing python pip module: {error.name}")
    exit(1)

try:
    from colored import attr, fg
except ModuleNotFoundError as error:
    print(f"Error: Please install missing python pip module: {error.name}")
    exit(1)

try:
    from pyfiglet import Figlet
except ModuleNotFoundError as error:
    print(f"Error: Please install missing python pip module: {error.name}")
    exit(1)


def header(args, title):
    figlet = Figlet(font="pepper")

    indent = " " * 6

    print()
    print()
    builtins.print(figlet.renderText(indent + title))
    print()


def print_deployment_filters(args):
    region_filter = args.region if args.region else "all"
    print(f"[bold]regions[/bold]: {region_filter}")

    environment_filter = args.environment if args.environment else "all"
    print(f"[bold]environments[/bold]: {environment_filter}")

    deployment_filter = args.deployment if args.deployment else "all"
    print(f"[bold]deployments[/bold]: {deployment_filter}")

    print()


def bump_version(version):
    return semver.VersionInfo.parse(version).bump_minor()


def bump_module(app, version: str = None, target: str = None):
    if not app:
        raise Exception("[APP] missing")

    script = os.path.join(bin_dir(), "bump-module.py")

    args = ["python", script, "-a", app]

    if version:
        args.extend(["-v", version])

    if target:
        args.extend(["-t", target])

    call(args)


def template_module(app, version, environment: str = None):
    if not app:
        raise Exception("[APP] missing")

    if not version:
        raise Exception("[VERSION] missing")

    script = os.path.join(bin_dir(), "template.py")

    args = ["python", script, "-a", app, "-v", version]

    if environment:
        args.extend(["-e", environment])

    run(args, check=True)


def set_deployment(app, version, environment):
    if not app:
        raise Exception("[APP] missing")

    if not version:
        raise Exception("[VERSION] missing")

    if not environment:
        raise Exception("[ENVIRONMENT] missing")

    script = os.path.join(bin_dir(), "set-deployment.py")

    call(["python", script, "-a", app, "-v", version, "-e", environment])


def bin_dir():
    return os.path.join(iac_root_dir(), "bin")


def iac_root_dir():
    return Path(".")


def load_yaml(path):
    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def get_latest_version(app):
    app_glob = os.path.join("module/app", app, "*")

    files = Path(iac_root_dir()).glob(app_glob)

    versions = [x.name for x in files if x.is_dir() and _is_version(x.name)]

    compare = functools.cmp_to_key(semver.compare)

    versions.sort(key=compare)

    return versions[len(versions) - 1]


def _is_version(name: str):
    try:
        semver.parse(name)
        return True
    except ValueError:
        return False


def get_deployments(app: str = None, version: str = None, environment: str = None):
    deployment_dir = os.path.join(iac_root_dir(), "deployment")
    deployments = []

    paths = []

    for path, names, filenames in os.walk(deployment_dir, followlinks=True):
        for name in names:
            paths.append(Path(path, name))
        for name in filenames:
            paths.append(Path(path, name))

    for path in paths:
        if not is_app_path(path):
            continue

        deployment = Deployment(path)

        if app and app != deployment.app:
            continue

        if environment and environment != deployment.environment:
            continue

        if version and version != deployment.version:
            continue

        deployments.append(deployment)

    order = [
        "dev0",
        "dev200",
        "test0",
        "test1",
        "test2",
        "prod0",
        "prod1",
        "prod2",
        "prod200",
    ]

    return sorted(deployments, key=lambda d: order.index(d.environment))


def get_deployment_environment(path):
    matches = re.search(r"deployment/[^\/]+/([^\/]+)", str(path))

    if not matches:
        return None

    return matches.group(1)


def get_deployment(path):
    path = Path(path)

    name = path.name
    environment = get_deployment_environment(path)
    _, version, deployment_type = get_deployment_module(path)

    return name, environment, version, deployment_type


def get_deployment_module(deployment_path):
    if Path(deployment_path).is_symlink():
        module_path = Path(deployment_path).resolve()
        deployment_type = "symlink"
    elif Path(deployment_path, "kustomization.yaml").exists():
        kustomization_path = Path(deployment_path, "kustomization.yaml")
        contents = load_yaml(kustomization_path)
        module_path = contents.get("bases")[0]
        deployment_type = "kustomize"
    else:
        return None

    matches = re.search(r"module/app/([^\/]+)/([^\/]+)", str(module_path))

    if not matches:
        return None

    app = matches.group(1)
    version = matches.group(2)

    return app, version, deployment_type


def is_app_path(path):
    path = Path(path)

    if not path.match("deployment/*/*/*/*/*/*/*"):
        return False

    if Path(path, "kustomization.yaml").exists():
        return True

    if path.is_symlink() and "module/app" in str(path.resolve()):
        return True

    return False


def print_app(app, context):
    _app = f"{fg('83')}{app}{attr(0)}"
    _context = f"{fg('81')}{context}{attr(0)}"

    return f"{_app}{fg('blue')}@{attr(0)}{_context}"


@dataclass
class Deployment:
    app: str
    version: str
    environment: str
    type: str
    path: Path

    def __init__(self, path):
        self.path = Path(path)

        if not is_app_path(path):
            return

        self.refresh()

    def refresh(self):
        app, environment, version, _ = get_deployment(self.path)

        self.app = app
        self.environment = environment
        self.version = version
        self.type = self._type()

    def is_valid(self):
        return is_app_path(self.path)

    def _type(self):
        if self.path.is_symlink():
            return "symlink"

        if self.path.joinpath("kustomization.yaml").exists():
            return "kustomize"

    def __repr__(self):
        return f"{print_app(self.app, self.environment)}"


class Module:
    app: str
    version: str
    path: Path

    def __init__(self, path):
        self.path = Path(path)
