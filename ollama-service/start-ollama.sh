
#!/bin/sh
set -eu

ollama serve &
OLLAMA_PID=$!

i=0
until ollama list >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "Ollama failed to start"
        exit 1
    fi
    sleep 2
done

ollama pull gemma3:1b

wait "$OLLAMA_PID"
