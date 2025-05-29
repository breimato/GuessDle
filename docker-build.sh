#!/bin/bash

CONTAINER_NAME=guessdle
IMAGE_NAME=guessdle:latest

CREATE_VOLUME=false
DB_PATH=""

DEFAULT_PORT=8000
PORT=${1:-$DEFAULT_PORT}

# Process the arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -v|--volume)
            CREATE_VOLUME=true
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                DB_PATH="$2"
                shift 2
            else
                DB_PATH="$(pwd)/data"
                mkdir -p "$DB_PATH"
                shift 1
            fi
            ;;
        *)
            echo "❌ Unknown argument: $1"
            echo "Usage: $0 [-p|--port <port>] [-v|--volume [<path>]]"
            exit 1
            ;;
    esac
done

echo "📦 Using port: $PORT"

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
    if [ "$CREATE_VOLUME" = true ]; then
        docker run -d \
            --name $CONTAINER_NAME \
            -p $PORT:8000 \
            --env-file .env \
            --restart unless-stopped \
            -v "$DB_PATH:/app/db.sqlite3" \
            $IMAGE_NAME
    else
        docker run -d \
            --name $CONTAINER_NAME \
            -p $PORT:8000 \
            --env-file .env \
            --restart unless-stopped \
            $IMAGE_NAME
    fi

    echo "✅ Container started correctly in port $PORT"

else
    echo "❌ Build failed. The current container was not stopped."
    exit 1
fi
