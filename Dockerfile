FROM python:3.9.1-slim

ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin
ENV GOOGLE_CLOUD_SDK_VERSION=331.0.0
ENV TERRAFORM_VERSION=0.13.4
ENV VAULT_VERSION=1.2.3
ENV KUBE_SCORE_VERSION=1.9.0
ENV TFSEC_VERSION=0.39.6
ENV KAPP_VERSION=0.34.0

RUN \
  apt-get update \
  && apt-get -y install --no-install-recommends curl unzip git \
  && rm -rf /var/lib/apt/lists/*

RUN \
  curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${GOOGLE_CLOUD_SDK_VERSION}-linux-x86_64.tar.gz \
  > /tmp/google-cloud-sdk.tar.gz \
  && mkdir -p /usr/local/gcloud \
  && tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz \
  && /usr/local/gcloud/google-cloud-sdk/install.sh \
  && rm -v /tmp/google-cloud-sdk.tar.gz \
  && gcloud -q components install kubectl


RUN \
  curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
  > /tmp/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
  && unzip /tmp/terraform_${TERRAFORM_VERSION}_linux_amd64.zip -d /bin \
  && rm -f /tmp/terraform_${TERRAFORM_VERSION}_linux_amd64.zip

RUN \
  curl -L https://github.com/vmware-tanzu/carvel-kapp/releases/download/v${KAPP_VERSION}/kapp-linux-amd64 \
  > /bin/kapp \
  && chmod +x /bin/kapp

RUN \
  curl https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip \
  > /tmp/vault_${VAULT_VERSION}_linux_amd64.zip \
  && unzip -d /bin /tmp/vault_${VAULT_VERSION}_linux_amd64.zip \
  && rm -f vault_${VAULT_VERSION}_linux_amd64.zip

RUN \
  curl -L https://github.com/zegl/kube-score/releases/download/v${KUBE_SCORE_VERSION}/kube-score_${KUBE_SCORE_VERSION}_linux_amd64 \
  > /bin/kube-score \
  && chmod +x /bin/kube-score

RUN \
  curl -L https://github.com/liamg/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64 \
  > /bin/tfsec \
  && chmod +x /bin/tfsec

RUN \
  mkdir fy

COPY . /fy

RUN \
  pip install poetry \
  && poetry config virtualenvs.create false \
  && cd fy \
  && poetry install
