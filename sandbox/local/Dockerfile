# Local Governed Sandbox scaffold for Projeto Omni.
# This is not the final runtime image and does not run Omni services.
# Keep this image minimal, conservative, and free of baked secrets.

FROM alpine:3.20

LABEL org.opencontainers.image.title="Projeto Omni Local Governed Sandbox"
LABEL org.opencontainers.image.description="Minimal scaffold for future local governed validation"

RUN addgroup -S omni && adduser -S -G omni -h /home/omni omni

WORKDIR /workspace

# Intentionally do not COPY the full repository by default.
# Future validation tasks may add reviewed, constrained mounts or copies.

USER omni

CMD ["/bin/sh"]
