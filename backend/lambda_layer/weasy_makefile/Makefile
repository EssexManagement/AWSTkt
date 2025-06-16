CPU_ARCH ?= x86_64
RUNTIME ?= 3.12
TEST_FILENAME ?= report.pdf

PLATFORM = linux/${CPU_ARCH}
# PLATFORM ?= linux/amd64  ### Did Not work for NCCR-on-CloudOne
# PLATFORM ?= linux/arm64  ### Did Not work for NCCR-on-CloudOne; `make` failed on GH-Actions
DOCKER_RUN=docker run --rm --platform=${PLATFORM}
LAMBDALAYER_NAME = weasyprint
LAMBDALAYER_ZIP_FILENAME = layer-${LAMBDALAYER_NAME}-${RUNTIME}-${CPU_ARCH}

### Define the default target
.DEFAULT_GOAL := all
# .DEFAULT_GOAL := build/${LAMBDALAYER_ZIP_FILENAME}.zip
# .DEFAULT_GOAL := build/weasyprint-layer-python$(RUNTIME).zip

.PHONY: stack.deploy.weasyprint clean test.start.container test.print.report all didSomethingChange

# all: build/${LAMBDALAYER_ZIP_FILENAME}.zip
# all: build/weasyprint-layer-python$(RUNTIME).zip
all: didSomethingChange

### Target to check for changes
didSomethingChange:
	./did-something-change.sh; \
	if [ $$? -eq 0 ]; then \
		$(MAKE) build/${LAMBDALAYER_ZIP_FILENAME}.zip CPU_ARCH=${CPU_ARCH} RUNTIME=${RUNTIME}; \
	else \
		exit 11; \
	fi

# build/weasyprint-layer-python$(RUNTIME).zip: weasyprint/layer_builder.sh
build/${LAMBDALAYER_ZIP_FILENAME}.zip: weasyprint/layer_builder.sh \
    build/fonts-${LAMBDALAYER_ZIP_FILENAME}.zip \
    | _build
	${DOCKER_RUN} \
	    -v `pwd`/weasyprint:/out \
			--entrypoint "/out/layer_builder.sh" \
	    -t public.ecr.aws/lambda/python:${RUNTIME} ${CPU_ARCH}
	mv -f ./weasyprint/layer.zip ./build/${LAMBDALAYER_ZIP_FILENAME}-no-fonts.zip
	cd build && rm -rf ./opt && mkdir opt \
	    && unzip fonts-${LAMBDALAYER_ZIP_FILENAME}.zip -d opt \
	    && unzip ${LAMBDALAYER_ZIP_FILENAME}-no-fonts.zip -d opt \
	    && cd opt && zip -r9 ../${LAMBDALAYER_ZIP_FILENAME}.zip .

# mv -f ./weasyprint/layer.zip ./build/weasyprint-layer-python${RUNTIME}-no-fonts.zip

# && unzip weasyprint-layer-python${RUNTIME}-no-fonts.zip -d opt \
# && cd opt && zip -r9 ../weasyprint-layer-python${RUNTIME}.zip .

build/fonts-${LAMBDALAYER_ZIP_FILENAME}.zip: fonts/layer_builder.sh | _build
	${DOCKER_RUN} \
	    -v `pwd`/fonts:/out \
	    --entrypoint "/out/layer_builder.sh" \
	    -t public.ecr.aws/lambda/python:${RUNTIME} ${CPU_ARCH}
	mv -f ./fonts/layer.zip $@

stack.diff:
	cd cdk-stacks && npm install && npm run build
	cdk diff --app ./cdk-stacks/bin/app.js --stack PrintStack --parameters uploadBucketName=${BUCKET}

stack.deploy:
	cd cdk-stacks && npm install && npm run build
	cdk deploy --app ./cdk-stacks/bin/app.js --stack PrintStack --parameters uploadBucketName=${BUCKET}

# test.start.container: build/weasyprint-layer-python$(RUNTIME).zip
test.start.container: build/${LAMBDALAYER_ZIP_FILENAME}.zip
	${DOCKER_RUN} \
	    -e GDK_PIXBUF_MODULE_FILE="/opt/lib/loaders.cache" \
	    -e FONTCONFIG_PATH="/opt/fonts" \
	    -e XDG_DATA_DIRS="/opt/lib" \
	    -v `pwd`/weasyprint:/var/task \
	    -v `pwd`/build/opt:/opt \
			-p 9000:8080 \
			public.ecr.aws/lambda/python:${RUNTIME} \
	    test_makefile_lambda_function.lambda_handler

test.print.report:
	which jq
	curl --fail -s -S -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
		-d '{"return": "base64", "filename": "${TEST_FILENAME}", "url": "https://kotify.github.io/cloud-print-utils/samples/report/"}' \
		| tail -1 | jq .body | tr -d '"' | base64 -d > ${TEST_FILENAME}
	@echo "Check ./${TEST_FILENAME}, eg.: xdg-open ${TEST_FILENAME}"


_build:
	@mkdir -p build

clean:
	rm -rf ./build

### EoF
