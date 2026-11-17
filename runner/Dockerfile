FROM ubuntu:24.04

ARG RUNNER_VERSION=2.338.0
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -q && apt-get install -y -q --no-install-recommends \
    ca-certificates \
    curl \
    gh \
    git \
    iproute2 \
    iputils-ping \
    jq \
    libicu-dev \
    libkrb5-3 \
    openssh-client \
    psmisc \
    python3 \
    python3-pip \
    python3-venv \
    rsync \
    sudo \
    tar \
    unzip \
    xz-utils \
    zlib1g \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Isolate Labgrid client, pytest, and RFC2217 serial dependencies in /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    labgrid==26.0 \
    pexpect \
    pyserial-labgrid \
    pytest \
    PyYAML \
    requests

WORKDIR /runner

RUN curl -fsSL "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
      -o "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" && \
    tar xzf "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" && \
    rm -f "actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

COPY entrypoint.sh /runner/entrypoint.sh
RUN chmod 0755 /runner/entrypoint.sh

ENTRYPOINT ["/runner/entrypoint.sh"]
