#!/bin/bash -f

### Uses Docker cli.

set -e

#docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.10" /bin/sh -c "pip install -r $PWD/layer/requirements.txt -t python/lib/python3.10/site-packages/; exit"
actual="$1"
cd $actual

cpu_arch="$2"

zipFileName="${3}"
# zipFileName=etl-layer-${cpu_arch}.zip
echo "zipFileName='${zipFileName}' within $0"

printf "%.0s-" {1..80}; printf "\n\n"
pwd
echo "PWD=$PWD"
echo "actual=$actual"

if [ "${cpu_arch}" == "amd64" ] || [ "${cpu_arch}" == "x86_64" ]; then
    export BUILDPLATFORM="linux/amd64";
else
    if [ "${cpu_arch}" == "arm64" ]; then
        export BUILDPLATFORM="linux/arm64";
    else
        echo "!! ERROR !! Unknown docker-platform '${cpu_arch}' within $0";
    fi
fi
export DOCKER_DEFAULT_PLATFORM="${BUILDPLATFORM}";
export TARGETPLATFORM="${DOCKER_DEFAULT_PLATFORM}";

printf "%.0s-" {1..80}; printf "\n\n"

docker run -v "$actual":/var/task               \
    "public.ecr.aws/sam/build-python3.10"       \
    /bin/sh -c "pip install -r /var/task/requirements.txt -t python/lib/python3.10/site-packages/"

echo $?
printf "%.0s-" {1..80}; printf "\n\n"
find ./python -name 'tests'|xargs -I {} rm -rf {}
(cd ./  && zip -qr ${zipFileName}  ./python)
rm -rf ./python
ls -ltr
echo "done with $0"

### EoScript
