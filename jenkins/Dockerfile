FROM jenkins/jenkins:2.580.2-lts-jdk21

ARG DOCKER_VERSION=28.5.1
ARG BUILDX_VERSION=0.29.1
ARG KUBECTL_VERSION=1.37.0
ARG KIND_VERSION=0.33.0

USER root
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64) docker_arch=x86_64 ;; arm64) docker_arch=aarch64 ;; *) exit 1 ;; esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${docker_arch}/docker-${DOCKER_VERSION}.tgz" \
      | tar -xz --strip-components=1 -C /usr/local/bin docker/docker; \
    mkdir -p /usr/local/lib/docker/cli-plugins; \
    curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-buildx \
      "https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}/buildx-v${BUILDX_VERSION}.linux-${arch}"; \
    curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/${arch}/kubectl"; \
    curl -fsSL -o /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/v${KIND_VERSION}/kind-linux-${arch}"; \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx /usr/local/bin/kubectl /usr/local/bin/kind
USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY casc.yaml /usr/share/jenkins/ref/casc.yaml
