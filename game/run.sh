#!/usr/bin/env bash
# Launch the Java Graphwar client that serves as the project's game body.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$HERE/graphwar.jar"

if ! command -v java >/dev/null 2>&1; then
  echo "java not found; install Java 8 or newer" >&2
  exit 1
fi
if [ ! -f "$JAR" ]; then
  echo "missing $JAR; see game/README.txt" >&2
  exit 1
fi

cd "$HERE"
exec java -jar graphwar.jar "$@"
