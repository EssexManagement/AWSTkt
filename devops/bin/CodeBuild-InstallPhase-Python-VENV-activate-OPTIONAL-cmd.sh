#!/bin/false

### Attention !! This must be SOURCED !!!
### Attention !! This must be SOURCED !!!
### Attention !! This must be SOURCED !!!

### Use-case: Each PHASE in CodeBuild, is a new bash-shell.  So, we need to (if appropriate) reactivate `.venv``

if [ -f requirements.txt ]; then
    if [ -d .venv ]; then
    echo "NEXT: activating the .venv (sourcing '.venv/bin/activate') .. ..";
    .   .venv/bin/activate;
    else
        echo '.venv MISSING !! ❌❌❌';
    fi

elif [ -f Pipfile.lock ]; then

    echo "For PIPENV .. Nothing to do";

else

    echo 'Both requirements.txt and Pipfile.lock are MISSING ❌❌❌';
    exit 111;

fi

### EoF
