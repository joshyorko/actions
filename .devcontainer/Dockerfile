# syntax=docker/dockerfile:1

FROM node:22.18.0-bookworm-slim@sha256:752ea8a2f758c34002a0461bd9f1cee4f9a3c36d48494586f60ffce1fc708e0e AS node
FROM ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded AS uv
FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ARG POETRY_VERSION=2.1.1

LABEL org.opencontainers.image.source="https://github.com/joshyorko/actions" \
      org.opencontainers.image.title="Actions — Action Server" \
      org.opencontainers.image.version="1"

ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        git \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -sf /usr/local/lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack

COPY --from=uv /uv /uv
COPY --from=uv /uvx /uvx
RUN ln -sf /uv /usr/local/bin/uv \
    && ln -sf /uvx /usr/local/bin/uvx

RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash vscode \
    && HOME=/home/vscode uv tool install "poetry==${POETRY_VERSION}"

WORKDIR /workspaces/actions
USER vscode
