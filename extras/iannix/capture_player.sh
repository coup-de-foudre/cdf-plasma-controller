#!/usr/bin/env bash
#
# End-to-end verification: run all 7 score players against a local OSC
# sink in parallel, capture each one's output for ~140 s (longer than
# 120 s loop so we observe the wraparound), and dump per-tube CSVs into
# scores/capture_player/.
#
# Used to confirm score_player.py reproduces the committed scores (and
# loops correctly). The output is overlaid against the original IanniX
# capture and the simplified score by extras/iannix/plot_scores.py.
#
# Run from the repo root:
#     bash extras/iannix/capture_player.sh
set -u

DURATION="${DURATION:-140}"
PYTHON="${PYTHON:-python3}"
OUT_DIR="${OUT_DIR:-scores/capture_player}"

mkdir -p "$OUT_DIR"

# Sink listens on 127.0.0.1:5005 and auto-stops after DURATION seconds.
"$PYTHON" extras/iannix/osc_sink.py \
    --out "$OUT_DIR" --duration "$DURATION" \
    > /tmp/sink_player.log 2>&1 &
SINK_PID=$!
sleep 1.0

# Each player gets a single "<Enter>" on stdin (= short press, start).
# Once stdin EOFs the player keeps running; we kill it after the sink
# exits.
PLAYER_PIDS=()
for tube in pwm1 pwm2 pwm3 pwm4 pwm5 pwm6 pwm7; do
    score="scores/${tube}.csv"
    if [ ! -f "$score" ]; then
        echo "skip $tube: $score not found" >&2
        continue
    fi
    echo "" | "$PYTHON" score_player.py \
        --mock-button \
        --root "$tube" \
        --score "$score" \
        --osc-target 127.0.0.1:5005 \
        > "/tmp/player_${tube}.log" 2>&1 &
    PLAYER_PIDS+=($!)
done

echo "running for ${DURATION}s; sink pid=$SINK_PID players=${PLAYER_PIDS[*]}"
wait "$SINK_PID"
echo "sink finished; stopping players"
for pid in "${PLAYER_PIDS[@]}"; do
    kill "$pid" 2>/dev/null
done
wait 2>/dev/null
echo "done; output in $OUT_DIR"
ls -la "$OUT_DIR"
