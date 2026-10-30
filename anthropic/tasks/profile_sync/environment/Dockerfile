FROM python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils binutils-x86-64-linux-gnu bsdextrautils file xxd \
    ca-certificates curl git nodejs npm \
    && rm -rf /var/lib/apt/lists/*
RUN npm install --global --omit=optional --ignore-scripts @anthropic-ai/claude-code@2.1.112
COPY runtime/requirements.txt /opt/static-tools/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/static-tools/requirements.txt
RUN groupadd --gid 1000 analyst && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash analyst \
    && mkdir -p /workspace/submission /logs/agent /logs/verifier /logs/artifacts /etc/claude-code \
    && chown -R 1000:1000 /workspace /logs
COPY runtime/ /opt/static-tools/
COPY claude-managed-settings.json /etc/claude-code/managed-settings.json
COPY profile_sync.elf /workspace/target.bin
COPY answer-shape.json /workspace/answer-shape.json
RUN chmod -R a-w /opt/static-tools /etc/claude-code \
    && chmod 0444 /workspace/target.bin /workspace/answer-shape.json
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
USER 1000:1000
