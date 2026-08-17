#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root_dir=$(cd -- "${script_dir}/.." && pwd)
config_file=${1:-templates-beta.json}
output_dir="${script_dir}/temp"

rm -rf "${output_dir}"
mkdir -p "${output_dir}"

python3 "${script_dir}/build_embedded_bundle.py" \
  --config "${script_dir}/${config_file}" \
  --template-root "${root_dir}" \
  --output-dir "${output_dir}"

echo "Created deterministic Action Server template bundle:"
sha256sum "${output_dir}/action-templates.zip"
