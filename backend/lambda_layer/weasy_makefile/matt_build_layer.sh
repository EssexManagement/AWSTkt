apt-get install -y dnf
dnf -y update

#!/bin/bash
# Don't forget to set these env variables in aws lambda
# GDK_PIXBUF_MODULE_FILE="/opt/lib/loaders.cache"
# XDG_DATA_DIRS="/opt/lib"
#FONTCONFIG_PATH="/opt/fonts"
set -e


echo "$0 : # of args = '$#'"
echo "$0 : 1st cli arg = '$1'"

if [ $# -ne 1 ]; then
  CPU_ARCH="x86_64"
  echo "$0 : !! NOT SPECIFIED .. CPU_ARCH !!! Defaulting to x86_64";
else
  CPU_ARCH=$1
  echo "$0 : Building for '${CPU_ARCH}' ..";
fi
CPU_ARCH=aarch64
dnf install -y rpmdevtools
dnf install -y dnf-plugins-core
cd /tmp
dnf install -y python3-pip pango gcc python3-devel gcc-c++ zlib-devel libjpeg-devel openjpeg2-devel libffi-devel
### Attention: Do -NOT- download latest versions automatically.
### Freeze the version#s, as shown 20-lines below.
# dnf download cairo
# dnf download gdk-pixbuf2
# dnf download libffi
# dnf download pango
# dnf download expat
# dnf download libmount
# dnf download libuuid
# dnf download libblkid
# dnf download glib2
# dnf download libthai
# dnf download fribidi
# dnf download harfbuzz
# dnf download libdatrie
# dnf download freetype
# dnf download graphite2
# dnf download libbrotli
# dnf download libpng
# dnf download fontconfig

printf "%.0s^" {1..120}; echo ''
echo 'DOWNLOADING STUFF'
dnf download cairo-1.17.6-2.amzn2023.0.1.${CPU_ARCH}
dnf download gdk-pixbuf2-2.42.10-1.amzn2023.0.1.${CPU_ARCH}
dnf download libffi-3.4.4-1.amzn2023.0.1.${CPU_ARCH}
dnf download pango-1.48.10-1.amzn2023.0.3.${CPU_ARCH}
dnf download expat-2.5.0-1.amzn2023.0.4.${CPU_ARCH}
dnf download libmount-2.37.4-1.amzn2023.0.4.${CPU_ARCH}
dnf download libuuid-2.37.4-1.amzn2023.0.4.${CPU_ARCH}
dnf download libblkid-2.37.4-1.amzn2023.0.4.${CPU_ARCH}
dnf download glib2-2.74.7-689.amzn2023.0.2.${CPU_ARCH}
dnf download libthai-0.1.28-6.amzn2023.0.2.${CPU_ARCH}
dnf download fribidi-1.0.11-3.amzn2023.0.2.${CPU_ARCH}
dnf download harfbuzz-7.0.0-2.amzn2023.0.1.${CPU_ARCH}
dnf download libdatrie-0.2.13-1.amzn2023.0.2.${CPU_ARCH}
dnf download freetype-2.13.0-2.amzn2023.0.1.${CPU_ARCH}
dnf download graphite2-1.3.14-7.amzn2023.0.2.${CPU_ARCH}
dnf download libbrotli-1.0.9-4.amzn2023.0.2.${CPU_ARCH}
dnf download libpng-2:1.6.37-10.amzn2023.0.6.${CPU_ARCH}
dnf download fontconfig-2.13.94-2.amzn2023.0.2.${CPU_ARCH}

printf "%.0s_" {1..120}; echo ''

# pixbuf need mime database
# https://www.linuxtopia.org/online_books/linux_desktop_guides/gnome_2.14_admin_guide/mimetypes-database.html
dnf download shared-mime-info

rpmdev-extract -- *rpm

mkdir /opt/lib
cp -P -r /tmp/*/usr/lib64/* /opt/lib
for f in $(find /tmp  -type f  -name 'lib*.so*'); do
  cp "$f" /opt/lib/$(python -c "import re; print(re.match(r'^(.*.so.\d+).*$', '$(basename $f)').groups()[0])");
done
# pixbuf need list loaders cache
# https://developer.gnome.org/gdk-pixbuf/stable/gdk-pixbuf-query-loaders.html
PIXBUF_BIN=$(find /tmp -name gdk-pixbuf-query-loaders-64)
GDK_PIXBUF_MODULEDIR=$(find /opt/lib/gdk-pixbuf-2.0/ -name loaders)
export GDK_PIXBUF_MODULEDIR
$PIXBUF_BIN > /opt/lib/loaders.cache

RUNTIME=$(grep AWS_EXECUTION_ENV "$LAMBDA_RUNTIME_DIR/bootstrap" | cut -d _ -f 5)
export RUNTIME
mkdir -p "/opt/python"
python -m pip install --platform manylinux2014_x86_64 --only-binary=:all: "weasyprint" -t "/opt/python"
pip uninstall cryptography
pip uninstall bcrypt
pip uninstall paramiko
pip install -r /asset-input/requirements.txt -t  "/opt/python"
pip install -U Pillow -t "/opt/python"
#python/lib/python3.12/site-packages/
### Note: The following error, requires use of above option "--only-binary=:all:"
### ERROR: When restricting platform and interpreter constraints using --python-version, --platform, --abi, or --implementation, either --no-deps must be set, or --only-binary=:all: must be set and --no-binary must not be set (or must be set to :none:).

cd /opt
ls -ltr
#zip -r9 /asset-input/layer.zip lib/* python/*
echo 'build_layer.sh --------------ZIPPED-------------------'
python  -V
#export PYTHONPATH=/opt/python
#python /asset-input/junk.py



#!/bin/bash
# don't forget to set FONTCONFIG_PATH="/opt/fonts" in your lambda
set -e

echo 'build_layer.sh: dnf install -y rpmdevtools'
dnf install -y rpmdevtools

cd /tmp
# download fonts
echo 'build_layer.sh: download some fonts'
dnf download dejavu-sans-fonts
dnf download dejavu-serif-fonts
dnf download dejavu-sans-mono-fonts

echo 'build_layer.sh: rpmdev-extract'
rpmdev-extract -- *rpm
echo 'build_layer.sh: mkdir /opt/fonts'
mkdir /opt/fonts
# dnf download urw-base35-nimbus-roman-fonts
# find /tmp/*/usr/share/fonts -name '*.afm' -delete -o -name '*.t1' -delete
echo 'build_layer.sh: cp -P'
cp -P -r /tmp/*/usr/share/fonts/* /opt/fonts
echo 'build_layer.sh: cat'
cat > /opt/fonts/fonts.conf <<EOF
<?xml version="1.0" ?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>/opt/fonts/</dir>
  <cachedir>/tmp/fonts-cache/</cachedir>

  <match target="pattern">
    <test qual="any" name="family">
      <string>mono</string>
    </test>
    <edit name="family" mode="assign" binding="same">
      <string>monospace</string>
    </edit>
  </match>

  <match target="pattern">
    <test qual="any" name="family">
      <string>sans serif</string>
    </test>
    <edit name="family" mode="assign" binding="same">
      <string>sans-serif</string>
    </edit>
  </match>

  <match target="pattern">
    <test qual="any" name="family">
      <string>sans</string>
    </test>
    <edit name="family" mode="assign" binding="same">
      <string>sans-serif</string>
    </edit>
  </match>

  <config></config>
</fontconfig>
EOF
echo 'build_layer.sh: cd /asset-output'
cd /asset-output
cp -r /opt/lib ./
cp -r /opt/python ./
cp -r /opt/fonts ./
echo 'COMPLETED build_layer.sh !!!!!!!!!!!!!!'
#zip -r9 layer.zip lib/* python/*  fonts/*
#zip -r9 /asset-input/font_layer.zip fonts/*

