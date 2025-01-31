#!/bin/bash -f

set +o noglob
pwd
ls -la
printf "%.0s-" {1..120}; echo ''; echo ''
ls -la ./cdk.out
printf "%.0s-" {1..120}; echo ''; echo ''

FILE_PATTERN="./cdk.out/FACT-backend-Lambdas-*.template.json"

### ==============================================================================

printf "%.0s-" {1..120}; echo ''; echo ''
eval ls -la $FILE_PATTERN
printf "%.0s-" {1..120}; echo ''; echo ''
FILES=$( eval ls $FILE_PATTERN )
sleep 3

C1='./cdk.out/compressed.json'
CS2='./cdk.out/compressed-sorted.json'
OS3='./cdk.out/orig-sorted.json'

### ==============================================================================

# for CFT_FILE in $( ls ./cdk.out/FACT-backend-Lambdas-*.template.json ); do
for CFT_FILE in $FILES; do
    printf "compressing '$CFT_FILE' .. ..\t\t"

    rm -f $C1 $CS2 $OS3

    sed -e 's/^  *//' $CFT_FILE > $C1
    jq -S . $C1                 > $CS2
    jq -S . $CFT_FILE           > $OS3

    DIFF_COUNT=$( diff $CS2 $OS3 | wc -l )
    if [ $DIFF_COUNT -ne 0 ]; then echo 'compressing CFT-json failed'; exit 11; fi

    echo \
    mv -f $C1 $CFT_FILE
    mv -f $C1 $CFT_FILE
done

printf "%.0s-" {1..120}; echo ''
eval ls -la $FILE_PATTERN
printf "%.0s-" {1..120}; echo ''

### EoF
