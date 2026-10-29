FROM python:3.14-alpine AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir --prefix=/install .


FROM python:3.14-alpine

LABEL com.docker.desktop.mcp="true"
LABEL com.docker.desktop.mcp.name="lanis-mcp"

COPY --from=builder /install /usr/local

# /data is owned by the unprivileged user, so a volume mounted there for
# LANIS_DATA_DIR is writable.
RUN adduser -D -H -u 10001 lanis && mkdir /data && chown lanis:lanis /data
USER lanis

# `docker run udondan/lanis <command>` runs the CLI; without a command the
# image starts the MCP server, which is what the Docker MCP Toolkit expects.
ENTRYPOINT ["lanis"]
CMD ["mcp"]
