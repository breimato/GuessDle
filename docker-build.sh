#!/bin/bash

CONTAINER_NAME=guessdle
IMAGE_NAME=guessdle:latest

CREATE_DB_PATH=false
DB_PATH=""
CREATE_MEDIA_PATH=false
MEDIA_PATH=""

MEM_LIMIT=""
CPU_LIMIT=""

DEFAULT_PORT=8000
PORT=${1:-$DEFAULT_PORT}

# Process the arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--container-name)
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                CONTAINER_NAME="$2"
                shift 2
            else
                echo "❌ Error: --container-name requires a value."
                exit 1
            fi
            ;;
        -v|--volume)
            CREATE_DB_PATH=true
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                DB_PATH="$2"
                shift 2
            else
                DB_PATH="$(pwd)/data"
                mkdir -p "$DB_PATH"
                shift 1
            fi
            ;;
        -m|--media)
            CREATE_MEDIA_PATH=true
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                MEDIA_PATH="$2"
                shift 2
            else
                MEDIA_PATH="$(pwd)/media"
                mkdir -p "$MEDIA_PATH"
                shift 1
            fi
            ;;
        -M|--mem)
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                MEM_LIMIT="$2"
                shift 2
            else
                echo "❌ Error: --mem requires a value (e.g., 150m)"
                exit 1
            fi
            ;;
        -C|--cpu)
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                CPU_LIMIT="$2"
                shift 2
            else
                echo "❌ Error: --cpu requires a value (e.g., 0.25)"
                exit 1
            fi
            ;;
        *)
            echo "❌ Unknown argument: $1"
            echo "Usage: $0 [-p|--port <port>] [-v|--volume [<path>]] [-m|--media [<path>]] [-c|--container-name <name>] [-M|--mem <memory>] [-C|--cpu <cpus>]"
            exit 1
            ;;
    esac
done

echo "📦 Using port: $PORT"
echo "📦 Using container name: $CONTAINER_NAME"
[[ -n "$MEM_LIMIT" ]] && echo "📦 Memory limit: $MEM_LIMIT"
[[ -n "$CPU_LIMIT" ]] && echo "📦 CPU limit: $CPU_LIMIT"

echo "🔨 Building new image..."
if docker build -t $IMAGE_NAME .; then
    echo "✅ Build completed successfully."

    echo "🔍 Checking if container '$CONTAINER_NAME' is running..."
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        echo "🛑 Stopping the container..."
        docker stop $CONTAINER_NAME
    fi

    echo "🗑️ Removing container if it exists..."
    if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
        docker rm $CONTAINER_NAME
    fi

    echo "🚀 Running the container..."

    # Base docker run command
    DOCKER_CMD="docker run -d --name $CONTAINER_NAME -p $PORT:8000 --env-file .env --restart unless-stopped"

    # Append memory and CPU limits if provided
    [[ -n "$MEM_LIMIT" ]] && DOCKER_CMD+=" --memory $MEM_LIMIT"
    [[ -n "$CPU_LIMIT" ]] && DOCKER_CMD+=" --cpus $CPU_LIMIT"

    # Append volume mounts
    if [ "$CREATE_DB_PATH" = true ] && [ "$CREATE_MEDIA_PATH" = true ]; then
        DOCKER_CMD+=" -v \"$MEDIA_PATH:/app/media\" -v \"$DB_PATH:/app/db.sqlite3\""
    fi

    # Append image
    DOCKER_CMD+=" $IMAGE_NAME"

    # Eval final command
    eval $DOCKER_CMD

    echo "✅ Container started correctly on port $PORT"
else
    echo "❌ Build failed. The current container was not stopped."
    exit 1
fi
