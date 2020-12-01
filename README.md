# Fy

F-Yeah!

## Description

A tool to wrap `vault(1)`, `terraform(1)`, `kubectl(1)` and various other tools to ease common deployment workflows.

## Install

```
pip install pipx
pipx install git+https://github.com/Inshur/fy --force
```

## Dependencies

* [GCloud](https://cloud.google.com/sdk)
* [Kubectl](https://cloud.google.com/sdk)
* [Terraform](https://www.terraform.io/)
* [Vault](https://www.vaultproject.io/)
* [Kapp](https://get-kapp.io/)
* [Tfsec](https://github.com/tfsec/tfsec)
* [Kube-score](https://github.com/zegl/kube-score)

Quick install dependencies:
```
curl https://sdk.cloud.google.com | bash
brew tap k14s/tap
brew install tfsec vault terraform kapp
brew install kube-score/tap/kube-score
```
