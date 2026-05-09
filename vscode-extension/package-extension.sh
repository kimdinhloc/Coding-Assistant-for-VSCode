#!/usr/bin/env bash
set -euo pipefail
npm ci
npx @vscode/vsce package
