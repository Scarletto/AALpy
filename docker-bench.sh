#!/usr/bin/env bash
#
# Build and run the AALpy benchmarking container.
#
# Resource limits (tuned for Ryzen 7 5700U / 14 GB RAM):
#   CPUs : 8   (half of 16 logical cores)
#   RAM  : 8 GB
#
# Usage:
#   ./docker-bench.sh                        # interactive bash shell
#   ./docker-bench.sh python Benchmarking/benchmark.py   # run a specific script
#
set -euo pipefail

IMAGE_NAME="aalpy-bench"
CONTAINER_NAME="aalpy-bench-run"

CPUS="8"
MEMORY="8g"

# ── Build ────────────────────────────────────────────────────────────────
echo "▶ Building image '${IMAGE_NAME}' …"
docker build -t "${IMAGE_NAME}" .

# ── Run ──────────────────────────────────────────────────────────────────
echo "▶ Starting container (cpus=${CPUS}, memory=${MEMORY}) …"
docker run --rm -it \
    --name "${CONTAINER_NAME}" \
    --cpus "${CPUS}" \
    --memory "${MEMORY}" \
    "${IMAGE_NAME}" \
    "${@:-bash}"
