.PHONY: clean deb rpm archivedeb archiverpm archive all installdeb installrpm deb_repo incbuild resetbuild

PYTHON=python
INSTALL_LAYOUT_ARG=--install-layout=deb

VERSION=`cd .. && $(PYTHON) -c "from config import get_version; print get_version()"`

clean:
	rm -rf *.deb
	rm -rf *.rpm
	make -C datadog-agent-lib clean
	make -C datadog-agent-base clean
	make -C datadog-agent clean

deb:	ensurebuild
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent-lib deb
	cp datadog-agent-lib/*.deb .
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent-base deb
	cp datadog-agent-base/*.deb .
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent deb
	cp datadog-agent/*.deb .

rpm:	ensurebuild
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent-lib rpm
	cp datadog-agent-lib/*.rpm .
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent-base rpm
	cp datadog-agent-base/*.rpm .
	VERSION=$(VERSION) PYTHON=$(PYTHON) INSTALL_LAYOUT_ARG=$(INSTALL_LAYOUT_ARG) BUILDNUMBER=`cat build.number` make -C datadog-agent rpm
	cp datadog-agent/*.rpm .

archivedeb:
	mkdir -p ../artifacts
	cp *.deb ../artifacts

ensurebuild:
	if [ ! -f build.number ]; then echo 0 > build.number; fi

resetbuild:
	rm -f build.number
	echo 1 > build.number

incbuild:
	# version number
	if [ ! -f build.number ]; then echo 0 > build.number; fi
	awk '{ print $$0 + 1}' build.number > build.number.tmp
	mv build.number.tmp build.number

installdeb:
	dpkg -i --force-confdef --force-confnew `ls -t datadog-agent-lib_*.deb | head -1`
	dpkg -i --force-confdef --force-confnew `ls -t datadog-agent-base_*.deb | head -1`
	dpkg -i --force-confdef --force-confnew `ls -t datadog-agent_*.deb | head -1`

archiverpm:
	mkdir -p ../dist
	cp *.rpm ../dist

archive: archivedeb archiverpm

deb_repo:
	rm Packages.gz
	sudo dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

all: clean deb rpm archive

