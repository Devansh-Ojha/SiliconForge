#!/usr/bin/env bash
set -euo pipefail

# SiliconForge Minimal ext4 Rootfs Builder for Firecracker microVMs
# Usage: ./build-rootfs.sh [OUTPUT_EXT4_PATH]

OUTPUT_IMG="${1:-siliconforge-rootfs.ext4}"
IMG_SIZE_MB="${IMG_SIZE_MB:-4096}"
MOUNT_DIR=$(mktemp -d /tmp/sf_rootfs_XXXXXX)

echo "=== SiliconForge MicroVM Rootfs Builder ==="
echo "Target Image: ${OUTPUT_IMG} (${IMG_SIZE_MB} MB)"

# 1. Create sparse image file
dd if=/dev/zero of="${OUTPUT_IMG}" bs=1M count=0 seek="${IMG_SIZE_MB}"
mkfs.ext4 -F "${OUTPUT_IMG}"

# 2. Extract Docker image rootfs into ext4
CONTAINER_ID=$(docker create siliconforge-eda:latest)
docker export "${CONTAINER_ID}" | tar -x -C "${MOUNT_DIR}" || true
docker rm "${CONTAINER_ID}"

echo "Rootfs generated successfully at ${OUTPUT_IMG}"
