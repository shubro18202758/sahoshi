#!/usr/bin/env bash
# sahoshi_env.sh — the Sahoshi (argus) stack's host environment, in one place.
#
# SOURCE it from other scripts:
#     . "$SAHOSHI_ROOT/scripts/sahoshi_env.sh"
#   Loads ~/.config/sahoshi/sahoshi.env (explicitly exported variables always win),
#   then fills defaults for the repo root, the compose invocation
#   (`sahoshi_compose ...`), host ports, container names and runtime dirs.
#
# RUN it:
#     scripts/sahoshi_env.sh --write [--force]   write ~/.config/sahoshi/sahoshi.env from
#                                             this host's detected paths (--force
#                                             regenerates it, keeping every other line)
#     scripts/sahoshi_env.sh --set KEY VALUE     set one key in sahoshi.env
#     scripts/sahoshi_env.sh --set KEY -         …the value read from stdin (secrets:
#                                             never in argv or shell history)
#     scripts/sahoshi_env.sh --print             print the effective environment
#
# ~/.config/sahoshi/sahoshi.env (mode 0600) is plain KEY=VALUE lines: it is both
# the EnvironmentFile= of the systemd --user units (infra/systemd/ read
# %h/.config/sahoshi/sahoshi.env — hence this fixed path, never $XDG_CONFIG_HOME)
# and what this script loads, so a reboot, a unit restart and a manual run
# all see the same settings. Every KEY=VALUE line in it is exported. Besides
# the host paths and switches --write records, it is where the values
# compose interpolates belong (SAHOSHI_PERSIST_KEYS below: the operator gate's
# SAHOSHI_OPERATOR_PIN / SAHOSHI_SESSION_SECRET, a non-default POSTGIS_PASSWORD,
# the SAHOSHI_CESIUM_ION_TOKEN, …): a boot bring-up has no login shell to
# inherit them from, and a deck recreated without the PIN serves the LAN
# with the gate OFF. Secrets go in with `--set KEY -` (stdin).
#
# SAHOSHI_OSINT (0 by default; plan R7) switches the OSINT event-intelligence
# service on: with SAHOSHI_OSINT=1, SAHOSHI_COMPOSE_FILES also names
# infra/compose.osint-ingress.yml (sahoshi-osint-ingress, loopback :8193)
# and scripts/sahoshi_up.sh gates a 12th readiness component, osint. Any other
# value is off: the stack is exactly the 11 components and 3 compose files it
# was before the flag existed. The deploy sets it with
#     scripts/sahoshi_env.sh --set SAHOSHI_OSINT 1

# ─── loader (works when sourced or executed) ────────────────────────────────

SAHOSHI_ROOT="${SAHOSHI_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SAHOSHI_ENV_FILE="${SAHOSHI_ENV_FILE:-$HOME/.config/sahoshi/sahoshi.env}"

# The keys --write records and --print shows (sahoshi.env may carry others,
# e.g. the compose values above; the loader exports every line).
SAHOSHI_ENV_KEYS=(
    SAHOSHI_ROOT SAHOSHI_RUN_DIR SAHOSHI_LOG_DIR SAHOSHI_VENV_DIR SAHOSHI_MODELS_CONFIG
    POSTGIS_HOST_PORT DECIDER_SNAPSHOT_PATH LLAMA_SERVER_BIN GEMMA_GGUF
    BGE_M3_PATH SAHOSHI_DEMO SAHOSHI_OSINT SAHOSHI_CONVERGE_TIMEOUT
)

# Values compose interpolates into the stack that must survive a reboot:
# --write keeps them (from sahoshi.env, or from this shell when only it has
# them) and scripts/sahoshi_up.sh warns when this shell carries one sahoshi.env
# lacks. Any OTHER line already in sahoshi.env is carried over by --write too.
# The second group are compose PASS-THROUGH flags (infra/compose.argus-override.yml:
# a key with no value there reaches the container only when set here).
SAHOSHI_PERSIST_KEYS=(
    SAHOSHI_OPERATOR_PIN SAHOSHI_SESSION_SECRET SAHOSHI_SESSION_SECURE SAHOSHI_CESIUM_ION_TOKEN
    POSTGIS_PASSWORD VVIP_ESCORT_SIM_GPS VVIP_REQUIRE_OFFICER
    EMULATOR_LIVING_VIOLATORS EMULATOR_CITY_SEED EMULATOR_LIVING_DENSITY OSINT_MODE
    VVIP_ACCEPT_LIVE_ANPR VVIP_ADAPTIVE_ROBUST_INPUTS
    VVIP_ESCORT_SIM_SPEED_KMH VVIP_ESCORT_GPS_TIMEOUT_SEC VVIP_ESCORT_APPROVAL_TIMEOUT_SEC
    VVIP_CONFIDENCE_FLOOR DECIDER_TIER0_DISABLE INGRESS_CITY_SEED
)

sahoshi_env_load() {  # <file> — export KEY=VALUE lines not already set
    local file="$1" line key value
    [ -r "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]] || continue
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]] && value="${BASH_REMATCH[1]}"
        [ -n "${!key+x}" ] && continue          # explicit environment wins
        export "$key=$value"
    done < "$file"
}

sahoshi_env_load "$SAHOSHI_ENV_FILE"

# ─── defaults ───────────────────────────────────────────────────────────────

export SAHOSHI_ROOT
export SAHOSHI_COMPOSE_PROJECT="${SAHOSHI_COMPOSE_PROJECT:-sahoshi}"
export SAHOSHI_RUN_DIR="${SAHOSHI_RUN_DIR:-$SAHOSHI_ROOT/.run-models}"
export SAHOSHI_LOG_DIR="${SAHOSHI_LOG_DIR:-$SAHOSHI_RUN_DIR/logs}"
export SAHOSHI_VENV_DIR="${SAHOSHI_VENV_DIR:-$SAHOSHI_ROOT/.venvs}"
export SAHOSHI_MODELS_CONFIG_DIR="${SAHOSHI_MODELS_CONFIG_DIR:-$SAHOSHI_ROOT/models-config}"
export SAHOSHI_MODELS_CONFIG="${SAHOSHI_MODELS_CONFIG:-$SAHOSHI_MODELS_CONFIG_DIR/configs/sahoshi_models.yaml}"
export SAHOSHI_DEMO="${SAHOSHI_DEMO:-0}"
# 1 = the OSINT service (compose.osint-ingress.yml, readiness component 12)
export SAHOSHI_OSINT="${SAHOSHI_OSINT:-0}"

# host ports (fixed platform constants of the argus stack). Overridable for
# scripts aimed at a sandbox; scripts/sahoshi_up.sh does NOT trust an override:
# it re-reads the live stack's ports from the rendered compose files and
# probes exactly those (compose binds them, not these variables).
export POSTGIS_HOST_PORT="${POSTGIS_HOST_PORT:-15434}"
export VALKEY_HOST_PORT="${VALKEY_HOST_PORT:-6390}"
export NATS_HOST_PORT="${NATS_HOST_PORT:-4233}"
export NATS_MON_PORT="${NATS_MON_PORT:-8233}"
export ORACLE_PORT="${ORACLE_PORT:-8191}"
export BRAIN_PORT="${BRAIN_PORT:-8192}"
export EMULATOR_PORT="${EMULATOR_PORT:-8190}"
export DECK_PORT="${DECK_PORT:-5373}"
export MODEL_HOST_PORT="${MODEL_HOST_PORT:-8083}"
export LLAMA_PORT="${LLAMA_PORT:-8084}"
export EMBEDDING_PORT="${EMBEDDING_PORT:-8085}"
export OSINT_PORT="${OSINT_PORT:-8193}"

# container names (infra/compose.argus-override.yml)
export POSTGIS_CONTAINER="${POSTGIS_CONTAINER:-sahoshi-postgis}"
export VALKEY_CONTAINER="${VALKEY_CONTAINER:-sahoshi-valkey}"
export NATS_CONTAINER="${NATS_CONTAINER:-sahoshi-nats}"
export INGRESS_CONTAINER="${INGRESS_CONTAINER:-sahoshi-signal-ingress}"
export ORACLE_CONTAINER="${ORACLE_CONTAINER:-sahoshi-traffic-oracle}"
export BRAIN_CONTAINER="${BRAIN_CONTAINER:-sahoshi-convoy-brain}"
export DECK_CONTAINER="${DECK_CONTAINER:-sahoshi-command-deck}"
export EMULATOR_CONTAINER="${EMULATOR_CONTAINER:-sahoshi-event-emulator}"
export OSINT_CONTAINER="${OSINT_CONTAINER:-sahoshi-osint-ingress}"

# The one compose invocation of the argus stack.
SAHOSHI_COMPOSE_FILES=(
    -f "$SAHOSHI_ROOT/infra/compose.yml"
    -f "$SAHOSHI_ROOT/infra/compose.gb10-override.yml"
    -f "$SAHOSHI_ROOT/infra/compose.argus-override.yml"
)
# The OSINT service's own stanza, only with SAHOSHI_OSINT=1 (plan R7): with the
# flag at 0 the invocation is exactly the three files above.
if [ "$SAHOSHI_OSINT" = 1 ]; then
    SAHOSHI_COMPOSE_FILES+=(-f "$SAHOSHI_ROOT/infra/compose.osint-ingress.yml")
fi
sahoshi_compose() {
    docker compose -p "$SAHOSHI_COMPOSE_PROJECT" "${SAHOSHI_COMPOSE_FILES[@]}" "$@"
}

# ─── CLI (only when executed, not when sourced) ─────────────────────────────

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    set -euo pipefail

    detect() {  # <env-value> <candidate...> — first given/existing path
        local given="$1"; shift
        if [ -n "$given" ]; then printf '%s\n' "$given"; return; fi
        local c
        for c in "$@"; do
            if [ -e "$c" ]; then printf '%s\n' "$c"; return; fi
        done
        printf '%s\n' "$1"
    }

    # One unquoted token that this loader and systemd's EnvironmentFile=
    # parser read identically: no whitespace, quotes, $, ` or \.
    VALUE_RE='^[^[:space:]"'"'"'$`\]*$'

    env_target() {  # the file behind SAHOSHI_ENV_FILE (a symlinked sahoshi.env stays a symlink)
        mkdir -p "$(dirname "$SAHOSHI_ENV_FILE")"
        local t; t="$(readlink -f -- "$SAHOSHI_ENV_FILE" 2>/dev/null || true)"
        printf '%s\n' "${t:-$SAHOSHI_ENV_FILE}"
    }

    cmd_write() {
        local force="${1:-}"
        if [ -f "$SAHOSHI_ENV_FILE" ] && [ "$force" != "--force" ]; then
            echo "[sahoshi_env] $SAHOSHI_ENV_FILE exists — keeping it (use --write --force to regenerate, --set KEY VALUE to edit)"
            return 0
        fi
        local venvs="$SAHOSHI_ROOT/.venvs"
        if [ ! -x "$venvs/model-host/bin/python" ] && [ -x "$SAHOSHI_ROOT/models/.venvs/model-host/bin/python" ]; then
            # legacy location (VVIP/models symlink into the retired tree)
            venvs="$(cd "$SAHOSHI_ROOT/models/.venvs" && pwd -P)"
            echo "[sahoshi_env] WARN: model venvs found only in the retired tree ($venvs);" \
                 "rebuild under VVIP/.venvs with: SAHOSHI_VENV_DIR=$SAHOSHI_ROOT/.venvs infra/scripts/serve_models.sh build" >&2
        fi
        local decider gguf llama bge
        decider="$(detect "${DECIDER_SNAPSHOT_PATH:-}" \
            "$HOME/.cache/huggingface/hub/models--perplexity-ai--pplx-decider-v1-27b/snapshots/b01a5cbaca5391f73bd55103d4f27e8982cd5e60")"
        llama="$(detect "${LLAMA_SERVER_BIN:-}" "$HOME/llama.cpp/build/bin/llama-server")"
        gguf="$(detect "${GEMMA_GGUF:-}" "$HOME/models/q4-stack/v7h-merged-Q4_K_M.gguf")"
        bge="$(detect "${BGE_M3_PATH:-}" "$HOME/models/bge-m3")"

        # Everything else sahoshi.env already holds is carried over (a
        # regenerate must never drop the operator gate's PIN or session
        # secret — the deck would come back on the LAN with the gate OFF),
        # plus the compose-interpolated values only this shell carries.
        # This shell's value wins, as it does in the loader.
        local key value line carried="" seen=" "
        local recorded=" ${SAHOSHI_ENV_KEYS[*]} "
        add_carried() {  # <key> <value>
            if [[ "$2" =~ $VALUE_RE ]]; then
                carried="$carried$1=$2"$'\n'
            else
                echo "[sahoshi_env] WARN: $1 has spaces, quotes, \$, \` or \\ — not recorded; a boot bring-up will not see it" >&2
            fi
            seen="$seen$1 "
        }
        if [ -r "$SAHOSHI_ENV_FILE" ]; then
            while IFS= read -r line || [ -n "$line" ]; do
                line="${line#"${line%%[![:space:]]*}"}"
                [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]] || continue
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
                [[ "$recorded$seen" == *" $key "* ]] && continue
                [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]] && value="${BASH_REMATCH[1]}"
                add_carried "$key" "${!key-$value}"
            done < "$SAHOSHI_ENV_FILE"
        fi
        for key in "${SAHOSHI_PERSIST_KEYS[@]}"; do
            [[ "$seen" == *" $key "* ]] && continue
            [ -n "${!key:-}" ] || continue
            add_carried "$key" "${!key}"
        done

        local file tmp
        file="$(env_target)"
        tmp="$(mktemp "$file.XXXXXX")"
        cat > "$tmp" <<EOF
# Sahoshi stack host environment — written by scripts/sahoshi_env.sh --write on $(date -Is).
# EnvironmentFile= of the systemd --user units (infra/systemd/) and loaded by
# scripts/sahoshi_env.sh. Plain KEY=VALUE lines (one unquoted token each); mode 0600.

# repository and runtime state
SAHOSHI_ROOT=$SAHOSHI_ROOT
SAHOSHI_RUN_DIR=$SAHOSHI_RUN_DIR
SAHOSHI_LOG_DIR=$SAHOSHI_LOG_DIR
SAHOSHI_VENV_DIR=$venvs
SAHOSHI_MODELS_CONFIG=$SAHOSHI_MODELS_CONFIG

# corridor-store published on loopback (embedding-service DSN)
POSTGIS_HOST_PORT=$POSTGIS_HOST_PORT

# model weights and binaries — explicit host paths, never in the repo
DECIDER_SNAPSHOT_PATH=$decider
LLAMA_SERVER_BIN=$llama
GEMMA_GGUF=$gguf
BGE_M3_PATH=$bge

# 1 = demo mode on every bring-up and reboot: city signal-plan writer
# (VVIP_SIGNAL_POLICY_WRITER) + living-city emulation (EMULATOR_LIVING_CITY)
SAHOSHI_DEMO=${SAHOSHI_DEMO:-0}

# 1 = the OSINT event-intelligence service (infra/compose.osint-ingress.yml,
# readiness component 12); 0 = off, the stack as before the flag existed
SAHOSHI_OSINT=${SAHOSHI_OSINT:-0}

# values compose interpolates, when not the defaults, and every other line
# this file already carried (the operator gate's SAHOSHI_OPERATOR_PIN /
# SAHOSHI_SESSION_SECRET, POSTGIS_PASSWORD, SAHOSHI_CESIUM_ION_TOKEN, …) — set
# them with scripts/sahoshi_env.sh --set KEY - (value on stdin)
$carried
EOF
        chmod 600 "$tmp"
        mv -f "$tmp" "$file"
        echo "[sahoshi_env] wrote $SAHOSHI_ENV_FILE"
        local p
        for p in "$decider" "$llama" "$gguf" "$bge" "$venvs"; do
            [ -e "$p" ] || echo "[sahoshi_env] WARN: path does not exist yet: $p" >&2
        done
    }

    cmd_set() {
        local key="${1:-}" value="${2-}" from_stdin=0
        [[ "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]] || { echo "usage: $0 --set KEY VALUE | --set KEY -" >&2; exit 2; }
        if [ "$value" = - ]; then
            # the secret path: the value never appears in argv (ps) or history
            from_stdin=1
            if [ -t 0 ]; then
                printf '%s: ' "$key" >&2
                IFS= read -r -s value || true
                printf '\n' >&2
            else
                IFS= read -r value || true
            fi
            [ -n "$value" ] || { echo "[sahoshi_env] no value on stdin for $key" >&2; exit 2; }
        fi
        [[ "$value" =~ $VALUE_RE ]] || { echo "[sahoshi_env] refusing a value with spaces, quotes, \$, \` or \\ (KEY=$key)" >&2; exit 2; }
        [ -f "$SAHOSHI_ENV_FILE" ] || cmd_write
        local file tmp
        file="$(env_target)"
        tmp="$(mktemp "$file.XXXXXX")"
        # Replace the first KEY= line (drop repeats) or append one. awk reads
        # the value from its environment: nothing in it (& | /) is syntax.
        SAHOSHI_SET_KEY="$key" SAHOSHI_SET_VALUE="$value" awk '
            BEGIN { k = ENVIRON["SAHOSHI_SET_KEY"]; line = k "=" ENVIRON["SAHOSHI_SET_VALUE"] }
            index($0, k "=") == 1 { if (!done) print line; done = 1; next }
            { print }
            END { if (!done) print line }' "$file" > "$tmp"
        chmod 600 "$tmp"
        mv -f "$tmp" "$file"
        if [ "$from_stdin" = 1 ]; then
            echo "[sahoshi_env] $SAHOSHI_ENV_FILE: $key set (from stdin)"
            return
        fi
        case "$key" in
            *PASSWORD*|*TOKEN*|*SECRET*|*PIN*) echo "[sahoshi_env] $SAHOSHI_ENV_FILE: $key set" ;;
            *) echo "[sahoshi_env] $SAHOSHI_ENV_FILE: $key=$value" ;;
        esac
    }

    cmd_print() {
        echo "# effective Sahoshi environment (file: $SAHOSHI_ENV_FILE$([ -f "$SAHOSHI_ENV_FILE" ] || echo ' — absent'))"
        local k
        for k in "${SAHOSHI_ENV_KEYS[@]}" SAHOSHI_COMPOSE_PROJECT SAHOSHI_LOG_DIR SAHOSHI_MODELS_CONFIG_DIR \
                 VALKEY_HOST_PORT NATS_HOST_PORT NATS_MON_PORT ORACLE_PORT BRAIN_PORT \
                 EMULATOR_PORT DECK_PORT MODEL_HOST_PORT LLAMA_PORT EMBEDDING_PORT \
                 OSINT_PORT OSINT_CONTAINER; do
            printf '%s=%s\n' "$k" "${!k:-}"
        done | awk '!seen[$0]++'
        echo "# osint: SAHOSHI_OSINT=$SAHOSHI_OSINT ($([ "$SAHOSHI_OSINT" = 1 ] && echo "on: 12 components, + infra/compose.osint-ingress.yml" || echo "off: 11 components, 3 compose files"))"
        echo "# compose: docker compose -p $SAHOSHI_COMPOSE_PROJECT ${SAHOSHI_COMPOSE_FILES[*]}"
    }

    case "${1:-}" in
        --write) cmd_write "${2:-}" ;;
        --set)   cmd_set "${2:-}" "${3-}" ;;
        --print) cmd_print ;;
        *) echo "usage: $0 {--write [--force] | --set KEY VALUE | --set KEY - | --print}  (or source it)" >&2; exit 2 ;;
    esac
fi
