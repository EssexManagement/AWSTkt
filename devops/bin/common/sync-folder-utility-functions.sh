#!/bin/false

### Must be SOURCED !!!
### Must be SOURCED !!!
### Must be SOURCED !!!


### ===============================================================================

# set noglob
set +o noglob

### Use  this script to keep BACKEND & FRONTEND gir-repos in sync.. ..
###         .. .. specifically RE: the PIPELINE related-files only.
### In an ideal-world, we use a single massive MONO-REPO for entire-project (covering FRONTED, BACKEND and another components)

### ===============================================================================

### Bash-Shell functions useful in many scenarios.

removeUserHomeFldrFromPath() {
    echo "$1" | sed 's|/Users/..*/LocalDevelopment/||'
}

### .........................

### 1st param is a folder (The source) -- Currently this is IGNORED!
### 2nd param is also a folder (the destination)
### 3rd param is a simple-filename (under the source-folder a.k.a. param #1)
function myDiffCacheFilePath {
    SrcFldr="$1"
    DEST_FLDR_DIFF_CACHE="$2"
    SimpleFileName="$3"

    diffFldrPath="${DEST_FLDR_DIFF_CACHE}/$( removeUserHomeFldrFromPath "${SrcFldr}" )"
    # echo "${DestFldr}/.diff/${DEST_FLDR_DIFF_CACHE}/${SimpleFileName}"
    echo "${diffFldrPath}/${SimpleFileName}"
}

### .................................................................................

### 1st param is a folder (The source)
### 2nd param is also a folder (the destination)
### 3rd param is OPTIONAL - a simple-filename or a SUB-folder (under the source-folder a.k.a. param #1)
function myFileDiff {
    SrcFldr="$1"
    DestFldr="$2"
    SimpleFileName="$3"

    ### ----- Sanity checks -----
    if [ "${SimpleFileName}" == "" ] && [ "${SimpleFileName}" == ".." ]  && [ "${SimpleFileName}" == "." ]; then
        echo "   SimpleFileName = '${SimpleFileName}'"
        exit 55
    fi
    if [ ! -e "${SrcFldr}/${SimpleFileName}" ]; then
        echo "🛑  ${SimpleFileName} does not exist in ${SrcFldr} !!"
        exit 88
    fi

    ### ----- actual logic -----
    echo $( removeUserHomeFldrFromPath "${SrcFldr}/${SimpleFileName}" )
    diff   "${SrcFldr}/${SimpleFileName}"   "${DestFldr}/${SimpleFileName}" >& "${TMPDIFFOUTP}"
    if [ $? -ne 0 ]; then
        ### The file is DIFFERENT
        ExpectedDiffFilePath=$( myDiffCacheFilePath  ${SrcFldr}  ${DEST_FLDR_DIFF_CACHE}  ${SimpleFileName} )
        # echo "ExpectedDiffFilePath = '${ExpectedDiffFilePath}'"
        if [ ! -f "${ExpectedDiffFilePath}" ]; then
            YesAtleastOneFileChanged=1
            echo "comparing: '${SrcFldr}/${SimpleFileName}' '<-->' '${DestFldr}/${SimpleFileName}'"
            whetherToSaveFileDiffAsNormal "${TMPDIFFOUTP}" "${ExpectedDiffFilePath}" "${SrcFldr}/${SimpleFileName}" "${DestFldr}/${SimpleFileName}"
            return $?
        fi

        diff -wq    ${TMPDIFFOUTP}   ${ExpectedDiffFilePath} >& /dev/null
        if [ $? -ne 0 ]; then
            YesAtleastOneFileChanged=1
            ### The file is DIFFERENT in ways that was -NOT- anticipated.
            echo "🛑  ${SimpleFileName}"
            echo "🛑  src= '${SrcFldr}/${SimpleFileName}' dest = '${DestFldr}/${SimpleFileName}'"
            echo "    expected-diff= '${ExpectedDiffFilePath}' and actual-diff= '${TMPDIFFOUTP}'"
            echo ''
            echo \
            cp  -ip   ${SrcFldr}/${SimpleFileName}   ${DestFldr}/${SimpleFileName}
            echo ''
            return 41
        fi
        return 0
    else
        return 0
    fi
}

### .................................................................................

myDirDiff() {
    srcSubFldr="$1"
    SrcFolderPath="$2"
    DestFolderPath="$3"

    LocalFilesList=$( cd "${SrcFolderPath}/${srcSubFldr}" > /dev/null; ls -d * )
    subSubSubDirList=()

    ### 1st do all the PLAIN-files only.
    for aFileName in ${LocalFilesList[@]}; do
        # echo $( removeUserHomeFldrFromPath "${SrcFolderPath}/${srcSubFldr}/${aFileName}" )
        if [ -f "${SrcFolderPath}/${srcSubFldr}/${aFileName}" ]; then
            myFileDiff   "${SrcFolderPath}/${srcSubFldr}"   "${DestFolderPath}/${srcSubFldr}" "${aFileName}"
            ExitCode=$?
        else
            if [ -d "${SrcFolderPath}/${srcSubFldr}/${aFileName}" ]; then
                # diff -rwq   ${SrcFolderPath}/${aFileName}   ${DestFolderPath}/${aFileName}
                subSubSubDirList+=( "${aFileName}" )
                ExitCode=0
            else
                echo "do -NOT- know what to do w/ '${SrcFolderPath}/${srcSubFldr}/${aFileName}'   '${DestFolderPath}/${srcSubFldr}/${aFileName}'"
                exit 73
            fi
        fi
        if [ ${ExitCode} -ne 0 ]; then
            YesAtleastOneFileChanged=1
        fi
    done
    ### 2nd do all the sub-folders.
    for subF in ${subSubSubDirList[@]}; do
        if [ ! -e "${DestFolderPath}/${subF}" ]; then
            mkdir -p $( dirname "${DestFolderPath}/${subF}" )
            echo "👉🏾👉🏾 " \
            cp -ipr  "${SrcFolderPath}/${subF}"  "${DestFolderPath}/${subF}"
            cp -ipr  "${SrcFolderPath}/${subF}"  "${DestFolderPath}/${subF}"
        fi
        ### recursion alert!
        echo \
        myDirDiff    "${srcSubFldr}/${subF}"  ' .. under .. '   "${SrcFolderPath}"   "${DestFolderPath}"
        myDirDiff    "${srcSubFldr}/${subF}" "${SrcFolderPath}"   "${DestFolderPath}"
    done
}

### ..............................................................................................

whetherToSaveFileDiffAsNormal() {
    TmpDiffFile="$1"
    ExpectedDiffFilePath="$2"
    SrcPath="$3"
    DestPath="$4"

    while read -r -t 1; do read -r -t 1; done ### "read -r -t0" will return true if stdin-stream is NOT empty
    read -p "Files differ! "c" to COPY-from-src // 'y' to reset the DIFF-output to be the NEW-NORMAL >>" ANS
    if [ "${ANS}" == "c" ] || [ "${ANS}" == "C" ]; then
        echo \
        cp -ip "${SrcPath}" "${DestPath}"
        cp -ip "${SrcPath}" "${DestPath}"
    fi
    if [ "${ANS}" == "y" ] || [ "${ANS}" == "Y" ]; then
        mkdir -p  $( dirname -- "${ExpectedDiffFilePath}" )
        echo ''; echo \
        mv -i "${TmpDiffFile}" "${ExpectedDiffFilePath}"
        sleep 2;
        mv -i "${TmpDiffFile}" "${ExpectedDiffFilePath}"
    fi
    return 0
}

### ===============================================================================


# EoInfo
