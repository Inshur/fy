# Fy

F-Yeah!

## Description

A tool to wrap `vault(1)`, `terraform(1)`, `kubectl(1)` and various other tools to ease common deployment workflows.

## Install

### Dependency References

* [gcloud](https://cloud.google.com/sdk)
* [kubectl](https://cloud.google.com/sdk)
* [terraform](https://www.terraform.io/)
* [vault](https://www.vaultproject.io/)
* [kapp](https://get-kapp.io/)
* [tfsec](https://github.com/tfsec/tfsec)
* [kube-score](https://github.com/zegl/kube-score)
* [opa](https://www.openpolicyagent.org)

### OS-X

```shell
curl https://sdk.cloud.google.com | bash
gcloud components install kubectl alpha beta
brew tap vmware-tanzu/carvel
brew install tfsec vault tfenv kapp
brew install kube-score/tap/kube-score
brew install opa

# install via pypi
pip install fycli --upgrade

# or via pipx
pip install pipx
pipx install git+https://github.com/Inshur/fy --force
```

### Ubuntu 20.10+

```shell
# Get current version from https://github.com/Inshur/inshur-iac/blob/master/.fy.lock
export GOOGLE_CLOUD_SDK_VERSION=339.0.0
export TERRAFORM_VERSION=0.14.11
export KUBE_SCORE_VERSION=1.11.0
export TFSEC_VERSION=0.39.29
export KAPP_VERSION=0.35.0
export OPA_VERSION=0.40.0
# python3.9 
# Note: do not set this as default system python, use a venv
sudo apt-get install virtualenv
sudo apt-get install python3.9

# google sdk repo - run this only once
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

# google sdk
sudo apt-get update
sudo apt-mark unhold google-cloud-sdk
sudo apt-get install google-cloud-sdk=$GOOGLE_CLOUD_SDK_VERSION-0
sudo apt-mark hold google-cloud-sdk
sudo apt-get install kubectl

# tfenv
tfenv install "${TERRAFORM_VERSION}"

# kapp
curl -L "https://github.com/vmware-tanzu/carvel-kapp/releases/download/v${KAPP_VERSION}/kapp-linux-amd64" \
  > "${HOME}/bin/kapp" && chmod +x "${HOME}/bin/kapp"

# kube-score
curl -L "https://github.com/zegl/kube-score/releases/download/v${KUBE_SCORE_VERSION}/kube-score_${KUBE_SCORE_VERSION}_linux_amd64" \
  > ${HOME}/bin/kube-score \
  && chmod +x ${HOME}/bin/kube-score

# tfsec
curl -L "https://github.com/liamg/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64" \
  > "${HOME}/bin/tfsec" \
  && chmod +x "${HOME}/bin/tfsec"

# OPA
curl -L https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static \
  > /bin/opa \
  && chmod +x /bin/opa
  
# configure venv
/usr/bin/virtualenv -p /usr/bin/python3.9 venv
source venv/bin/activate
pip install fycli

```

## Release Instructions

Update the dependency versions in the `Dockerfile`.

Create a new release:
```shell
python -m venv venv
source venv/bin/activate
make build-deps
make version-patch
git commit -a -m "Added new version $(make version-show)"
git tag "$(make version-show)"
git push --tags
```

Push new version to `pypi` (requires auth):
```shell
make clean push
```

## Local Development
```shell
python -m venv venv
pip install pyyaml toml
make build-deps
poetry install
export PYTHON_PATH=${PWD}/fycli
python -m fycli -v
```
