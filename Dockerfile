# Installs the wheel from dist/: run `uv build` (or `mise run build`) first.
FROM python:3.15-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src
COPY pyproject.toml uv.lock ./
# Runtime dependencies exactly as locked, hashes checked. No dev group.
RUN uv sync --frozen --no-dev --no-install-project
COPY dist/*.whl /tmp/
RUN uv pip install --python /opt/venv/bin/python --no-deps /tmp/*.whl


FROM python:3.15-alpine

LABEL com.docker.desktop.mcp="true"
LABEL com.docker.desktop.mcp.name="lanis"

# Same base image as the builder, so the venv's python symlink resolves.
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# pip isn't needed at runtime, and its vendored copies of urllib3, msgpack
# and setuptools show up in vulnerability scans. apk upgrade pulls fixes for
# Alpine packages released after the base image.
# /data is owned by the unprivileged user, so a volume mounted there for
# LANIS_DATA_DIR is writable.
RUN apk upgrade --no-cache \
    && /usr/local/bin/python -m pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.*/ensurepip \
    && adduser -D -H -u 10001 lanis && mkdir /data && chown lanis:lanis /data
USER lanis

# `docker run udondan/lanis <command>` runs the CLI; without a command the
# image starts the MCP server, which is what the Docker MCP Toolkit expects.
ENTRYPOINT ["lanis"]
CMD ["mcp"]
