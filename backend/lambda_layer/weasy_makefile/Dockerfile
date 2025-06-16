# Use Ubuntu latest as base image
FROM ubuntu:latest

# Install necessary build tools, dependencies, and Docker
RUN apt-get update && apt-get install -y \
    make \
    build-essential \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/* \
    # Add Docker's official GPG key
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    # Add Docker repository
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    # Install Docker CLI
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# First, create the build directory
RUN mkdir -p build

# Copy only specific files&folders, excluding `build/`
COPY Dockerfile Makefile README.md lambda_layer_weasy.py requirements.txt ./
COPY fonts/ ./fonts/
COPY weasyprint/ ./weasyprint/

# Run the make command with specified parameters
CMD ["make", "CPU_ARCH=x86_64", "RUNTIME=3.12"]
