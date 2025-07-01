#!/bin/bash

while getopts iu option ;do
    case ${option} in
        i) INTERACTIVE="SET" ;;
        u) SRC_UPDATE="SET" ;;
        *) echo "No option is added -i interactive mode for localstack";;
    esac
done

update_source() {
    echo "Replace build source to original source"
    source="$PWD/runtime"
    cd "$PWD/build"

    for dir in $(ls -d */); do
      echo "Copying sources $source/* to: $dir"
      cp -rf "$source"/* "$dir"
      ls -ltr "$dir"
    done
    cd ..
}

aws_status() {
    echo "check localstack aws status"
}

if [[ ${SRC_UPDATE} = "SET" ]]
    then
        update_source
        exit 0
fi

# sam build for the local test
echo "sam build"
sam build -t ./local-test-config/fact-sam.yaml -m runtime/requirements.txt -u -b ./build/ -s runtime/

# start localstat
echo "Start localstack"

if [[ ${INTERACTIVE} = "SET" ]]
    then
        docker-compose -f ./local-test-config/docker-compose.yaml up
    else
        docker-compose -f ./local-test-config/docker-compose.yaml up -d
        # wait until local stack is set
        sleep 15
        aws_status

        echo "Start aws sam local api gateway"
        #sam local start-api -t build/template.yaml --docker-network local-test-config_local_aws_network -p 4000
        sam local start-api -t build/template.yaml  -p 4000

fi

