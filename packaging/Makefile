.PHONY: clean deb rpm archivedeb archiverpm archive all installdeb installrpm deb_repo incbuild resetbuild

VERSION=`cd .. && python -c "from config import get_version; print get_version()"`

clean:
	rm -rf *.deb
	rm -rf *.rpm
	make -C datadog-agent-lib clean
	make -C datadog-agent-base clean
	make -C datadog-agent clean

deb:
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent-lib deb
	cp datadog-agent-lib/*.deb .
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent-base deb
	cp datadog-agent-base/*.deb .
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent deb
	cp datadog-agent/*.deb .

rpm:
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent-lib rpm
	cp datadog-agent-lib/*.rpm .
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent-base rpm
	cp datadog-agent-base/*.rpm .
	VERSION=$(VERSION) BUILDNUMBER=`cat build.number` make -C datadog-agent rpm
	cp datadog-agent/*.rpm .

archivedeb:
	mkdir -p ../artifacts
	cp *.deb ../artifacts

resetbuild:
	rm -f build.number
	echo 1 > build.number

incbuild:
	# version number
	if [ ! -f build.number ]; then echo 0 > build.number; fi
	awk '{ print $$0 + 1}' build.number > build.number.tmp
	mv build.number.tmp build.number

installdeb:
	dpkg -i `ls -t datadog-agent-lib_*.deb | head -1`  --force-confdef --force-confnew
	dpkg -i `ls -t datadog-agent-base_*.deb | head -1` --force-confdef --force-confnew
	dpkg -i `ls -t datadog-agent_*.deb | head -1`	   --force-confdef --force-confnew

archiverpm:
	mkdir -p ../dist
	cp *.rpm ../dist

archive: archivedeb archiverpm

deb_repo:
	rm Packages.gz
	sudo dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

all: clean deb rpm archive

