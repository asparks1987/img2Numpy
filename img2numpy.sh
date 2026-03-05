#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
IMAGE_LOCAL="img2numpy:latest"
IMAGE_REMOTE="172.16.120.5:5000/img2numpy:latest"
CONTAINER_NAME="img2numpy"
DEFAULT_WEBUI_PORT="8000"
DEFAULT_API_PORT="${IMG2NUMPY_API_PORT:-8585}"

usage() {
  cat <<EOF
Usage:
  bash ./${SCRIPT_NAME} /build [-a]
  bash ./${SCRIPT_NAME} /install [-p <webui_port>]
  bash ./${SCRIPT_NAME} /update [-p <webui_port>]

Commands:
  /build      Build the Docker image locally.
  /install    Run a container from latest local image.
  /update     Pull latest image from registry and recreate container.

Flags:
  -a          With /build, build multi-arch and push to ${IMAGE_REMOTE}.
  -p <port>   WebUI host port (API host port is IMG2NUMPY_API_PORT or 8585).
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

parse_webui_port() {
  local default_port="$1"
  local port="$default_port"
  shift
  while (($#)); do
    case "$1" in
      -p)
        if (($# < 2)); then
          echo "Missing value for -p" >&2
          exit 1
        fi
        port="$2"
        shift 2
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
  printf "%s" "$port"
}

stop_existing_container() {
  if docker ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
}

run_container() {
  local image="$1"
  local webui_port="$2"
  local api_port="${IMG2NUMPY_API_PORT:-$DEFAULT_API_PORT}"

  stop_existing_container

  local port_args=(-p "${api_port}:${api_port}")
  if [[ "${webui_port}" != "${api_port}" ]]; then
    port_args+=(-p "${webui_port}:${api_port}")
  fi

  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -e IMG2NUMPY_API_PORT="${api_port}" \
    "${port_args[@]}" \
    "${image}" >/dev/null

  echo "Container '${CONTAINER_NAME}' is running."
  echo "API:   http://127.0.0.1:${api_port}"
  echo "WebUI: http://127.0.0.1:${webui_port}"
}

build_local() {
  require_cmd docker
  docker build -t "${IMAGE_LOCAL}" .
  echo "Built ${IMAGE_LOCAL}"
}

build_all_arch_and_push() {
  require_cmd docker

  if ! docker buildx version >/dev/null 2>&1; then
    echo "Docker buildx is required for /build -a" >&2
    exit 1
  fi

  if ! docker buildx inspect img2numpy-builder >/dev/null 2>&1; then
    docker buildx create --name img2numpy-builder --driver docker-container --use >/dev/null
  else
    docker buildx use img2numpy-builder >/dev/null
  fi

  docker buildx inspect --bootstrap >/dev/null
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t "${IMAGE_REMOTE}" \
    --push \
    .
  echo "Built and pushed ${IMAGE_REMOTE}"
}

main() {
  if (($# == 0)); then
    usage
    exit 1
  fi

  local command="$1"
  shift || true

  case "${command}" in
    /build)
      if (($# == 1)) && [[ "$1" == "-a" ]]; then
        build_all_arch_and_push
      elif (($# == 0)); then
        build_local
      else
        echo "Invalid arguments for /build" >&2
        usage
        exit 1
      fi
      ;;
    /install)
      require_cmd docker
      local webui_port
      webui_port="$(parse_webui_port "${DEFAULT_WEBUI_PORT}" "$@")"
      run_container "${IMAGE_LOCAL}" "${webui_port}"
      ;;
    /update)
      require_cmd docker
      local webui_port
      webui_port="$(parse_webui_port "${DEFAULT_WEBUI_PORT}" "$@")"
      docker pull "${IMAGE_REMOTE}"
      run_container "${IMAGE_REMOTE}" "${webui_port}"
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
