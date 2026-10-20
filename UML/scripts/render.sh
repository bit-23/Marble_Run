#!/usr/bin/env bash
# Uso: ./scripts/render.sh [caminho/plantuml.jar]
set -e
cd "$(dirname "$0")/.."
JAR="${1:-${PLANTUML_JAR:-plantuml.jar}}"
if command -v plantuml >/dev/null; then CMD="plantuml"; else CMD="java -jar $JAR"; fi
$CMD -tpng -o png diagrams/sequence/*.puml diagrams/class/*.puml
echo "PNGs gerados em diagrams/*/png/"
