# Fy

F-Yeah!

## Description

A tool to wrap `vault(1)`, `terraform(1)`, `kubectl(1)` and various other tools to ease common deployment workflows.

## Install

### Dependencies

* [gcloud](https://cloud.google.com/sdk)
* [kubectl](https://cloud.google.com/sdk)
* [terraform](https://www.terraform.io/)
* [vault](https://www.vaultproject.io/)
* [kapp](https://get-kapp.io/)
* [tfsec](https://github.com/tfsec/tfsec)
* [kube-score](https://github.com/zegl/kube-score)

### Quick Install

```
curl https://sdk.cloud.google.com | bash
brew tap k14s/tap
brew install tfsec vault terraform kapp
brew install kube-score/tap/kube-score

# install via pypi
pip install fycli --upgrade

# or via pipx
pip install pipx
pipx install git+https://github.com/Inshur/fy --force
```

### Releases

Update the dependency versions in the `Dockerfile`.

Create a new release:
```
python -m venv venv
source venv/bin/activate
make build-deps
make version-patch
git tag 2.0.15
git push --tags
```

Push new version to `pypi` (requires auth):
```
make clean push
```
