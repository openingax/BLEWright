#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
archive=dist/sparkle/Sparkle.tar.xz
mkdir -p dist/sparkle
if [[ ! -f "$archive" ]]; then
  curl -fL https://github.com/sparkle-project/Sparkle/releases/download/2.10.1/Sparkle-2.10.1.tar.xz -o "$archive"
fi
echo "1a856d2a9edb8e628de88121d7be04cf0e2167f8641650b78fca00b14244cf27  $archive" | shasum -a 256 -c -
tar -xJf "$archive" -C dist/sparkle
