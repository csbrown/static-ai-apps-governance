# The agent image, for every role: the maintainer and every IC and curator session. Part of the core:
# only the owner changes it, because agents run inside it with the Claude token.
# What differs between them is only what the container is given: mounts, environment, command.
FROM node:22-bookworm

# Match your user's ids, so files written to mounted folders stay owned by you.
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git jq ripgrep python3 python3-pip ca-certificates curl \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

# The same tools CI uses, so agents can test what CI will check.
RUN pip3 install --no-cache-dir pyyaml psutil playwright pyflakes actionlint-py shellcheck-py \
 && python3 -m playwright install --with-deps chromium \
 && chmod -R a+rX /ms-playwright

RUN npm install -g @anthropic-ai/claude-code

# The base image's `node` user (uid and gid 1000) becomes the sandbox user.
RUN if [ "$USER_GID" != "1000" ]; then groupmod -g "$USER_GID" node; fi \
 && if [ "$USER_UID" != "1000" ]; then usermod -u "$USER_UID" -g "$USER_GID" node; fi

COPY entrypoint.sh /usr/local/bin/sandbox-entry
RUN chmod 755 /usr/local/bin/sandbox-entry

USER node
WORKDIR /home/node
ENTRYPOINT ["sandbox-entry"]
CMD ["bash"]
