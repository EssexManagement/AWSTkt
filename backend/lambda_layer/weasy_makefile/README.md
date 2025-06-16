# Lambda layers

The layers support only Amazon Linux 2023 runtimes, eg. python3.12.

Requires:
1. **docker**
   1. Uses the `public.ecr.aws/lambda/python` Container Image.
2. **make**
   1. Requires use of `dnf` and utilities like `rpmdev-extract`
   2. Assumes you are OK with some generic open-source fonts.  See more details in [fonts subfolder](./fonts/layer_builder.sh)
3. Generating Fonts _on the fly_ (under the `./fonnts/` subfolder)

ATTENTION !!<BR/>
Due to reasons 2 & 3 above, you can -NOT- replace the `Makefile` with ~~a simple Docker command~~!

## How to avoid re-building and re-deploying this Custom 𝜆-layer?

So far .. Not possible.

1. The Zip file has files with datetimestamp == when this `Makefile` was run!
2. The `dnf` commands will install different tiny-variations of the libraries' version#s, once every 24 hrs.
3. There is --NO-- equivalent of ` Pipfile.lock` here.  So, NO luck there.

<BR/> <BR/> <BR/>
<HR/> <HR/> <HR/>

## WeasyPrint

[WeasyPrint](https://weasyprint.org/) is python based pdf/png print service.

1.  Turn-OFF the VPN.
1.  Run `make` to build a layer, for details see commands below.
    *  Reference: docker lambda example's [readme](weasyprint/README.md).
1.  To test your build start container with `make test.start.container` ..
1.  .. and then run `make test.print.report`
in another terminal.
    *  The result is saved in `report.pdf`.


```bash
export CHIP_ARCH="x86_64";
# export CHIP_ARCH="arm64";
export BUILDPLATFORM="linux/${CHIP_ARCH}";
export DOCKER_DEFAULT_PLATFORM="${BUILDPLATFORM}";
export TARGETPLATFORM="${DOCKER_DEFAULT_PLATFORM}";

PYTHON_VERSION="3.12"

DOCKER_ZIPFILE_PATH="build/layer-wordsearch-whoosh-${PYTHON_VERSION}-${CHIP_ARCH}.zip"
rm -f "${PWD}/${DOCKER_ZIPFILE_PATH}"

make CPU_ARCH=x86_64 RUNTIME=3.12
    ### A simple `make` cmd withOUT any cli-args is equivalent to the above line.
```

<BR/> <BR/> <BR/>
<HR/> <HR/> <HR/>

# Location of the deployment package

`./${DOCKER_ZIPFILE_PATH}"`

`"${PWD}/${DOCKER_ZIPFILE_PATH}"`

<BR/> <BR/> <BR/>
<HR/> <HR/> <HR/>


<BR/> <BR/> <BR/>
<HR/> <HR/> <HR/>

# Appendix

/EoF
