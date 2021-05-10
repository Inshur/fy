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

### Quick Install (OSX)

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

### Less Quick Install (Ubuntu)

```
Install tfenv: https://github.com/tfutils/tfenv

# Get current version from https://github.com/Inshur/inshur-iac/blob/master/.fy.lock
export GOOGLE_CLOUD_SDK_VERSION=339.0.0
export TERRAFORM_VERSION=0.14.11
export VAULT_VERSION=1.2.3
export KUBE_SCORE_VERSION=1.11.0
export TFSEC_VERSION=0.39.29
export KAPP_VERSION=0.35.0

# python3.9 - warning do not set this as default system python, use in a venv
sudo apt-get install python3.9

# google sdk
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-sdk=$GOOGLE_CLOUD_SDK_VERSION-0
sudo apt-get install kubectl

tfenv install $TERRAFORM_VERSION

curl https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip \
> /tmp/vault_${VAULT_VERSION}_linux_amd64.zip \
&& unzip -d $HOME/bin /tmp/vault_${VAULT_VERSION}_linux_amd64.zip \
&& rm -f vault_${VAULT_VERSION}_linux_amd64.zip

curl -L https://github.com/vmware-tanzu/carvel-kapp/releases/download/v${KAPP_VERSION}/kapp-linux-amd64 > $HOME/bin/kapp && chmod +x $HOME/bin/kapp

curl -L https://github.com/zegl/kube-score/releases/download/v${KUBE_SCORE_VERSION}/kube-score_${KUBE_SCORE_VERSION}_linux_amd64 \
> $HOME/bin/kube-score \
&& chmod +x $HOME/bin/kube-score

curl -L https://github.com/liamg/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64 \
> $HOME/bin/tfsec \
&& chmod +x $HOME/bin/tfsec

# setup venv
virtualenv -p /usr/bin/python3.9 venv
source venv/bin/activate
pip install fycli

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
