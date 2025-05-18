#!/usr/bin/env bash

# List of "directory|script|prefix" entries
SCRIPTS=(
  "frontend|run_server.sh|frontend"
  "backend|run_server.sh|backend"
  "digital-twin|run_server.sh|digital-twin"
  "ml-inference|run_server.sh|ml-inference"
)

# Colors for output prefixes
COLORS=(
  "\033[1;34m" # Blue
  "\033[1;32m" # Green
  "\033[1;33m" # Yellow
  "\033[1;35m" # Magenta
  "\033[1;36m" # Cyan
)
NC="\033[0m"

run_and_prefix() {
  local dir="$1"
  local script="$2"
  local prefix="$3"
  local color="$4"
  (
    cd "$dir" || { echo "Failed to cd to $dir"; exit 1; }
    bash "$script" 2>&1 | while IFS= read -r line; do
      printf "%b%-15s |%b %s\n" "$color" "$prefix" "$NC" "$line"
    done
  )
}

run_db() {
  local prefix="db"
  local color="\033[1;36m" # Cyan
  (
    docker compose up timescale 2>&1 | while IFS= read -r line; do
      printf "%b%-15s |%b %s\n" "$color" "$prefix" "$NC" "$line"
    done
  )
}

# Start db first, in the background
run_db &
DB_PID=$!

# Wait 3 seconds for db to initialize
sleep 3

# Start other services in parallel
PIDS=()
i=0
for entry in "${SCRIPTS[@]}"; do
  dir="${entry%%|*}"
  rest="${entry#*|}"
  script="${rest%%|*}"
  prefix="${rest#*|}"
  color="${COLORS[$((i % ${#COLORS[@]}))]}"
  run_and_prefix "$dir" "$script" "$prefix" "$color" &
  PIDS+=($!)
  ((i++))
done

# Wait for all scripts (including db) to finish
PIDS+=($DB_PID)
for pid in "${PIDS[@]}"; do
  wait "$pid"
done
