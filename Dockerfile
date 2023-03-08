FROM python:3.9.10-slim

ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin:/tfenv/bin
ENV GOOGLE_CLOUD_SDK_VERSION=402.0.0
ENV TERRAFORM_VERSION=1.2.9
ENV KUBE_SCORE_VERSION=1.11.0
ENV TFSEC_VERSION=1.27.6
ENV KAPP_VERSION=0.35.0
ENV OPA_VERSION=0.40.0

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
  && gcloud -q components install kubectl alpha beta

RUN \
  curl -L https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64 \
  > /bin/kubectl-argo-rollouts \
  && chmod +x /bin/kubectl-argo-rollouts

RUN \
  git clone https://github.com/tfutils/tfenv.git /tfenv \
  && tfenv install ${TERRAFORM_VERSION}

RUN \
  curl -L https://github.com/vmware-tanzu/carvel-kapp/releases/download/v${KAPP_VERSION}/kapp-linux-amd64 \
  > /bin/kapp \
  && chmod +x /bin/kapp


RUN \
  curl -L https://github.com/zegl/kube-score/releases/download/v${KUBE_SCORE_VERSION}/kube-score_${KUBE_SCORE_VERSION}_linux_amd64 \
  > /bin/kube-score \
  && chmod +x /bin/kube-score

RUN \
  curl -L https://github.com/liamg/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64 \
  > /bin/tfsec \
  && chmod +x /bin/tfsec

RUN \
  curl -L https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static \
  > /bin/opa \
  && chmod +x /bin/opa

RUN \
  mkdir fy

COPY . /fy

RUN \
  pip install poetry \
  && poetry config virtualenvs.create false \
  && cd fy \
  && poetry install
