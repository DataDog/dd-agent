.PHONY: clean deb rpm archivedeb archiverpm archive all installdeb installrpm deb_repo incbuild resetbuild

VERSION=`cd .. && python -c "from config import get_version; print get_version()"`

clean:
	rm -rf *.deb
	rm -rf *.rpm
	make -C agent clean

deb:
	VERSION=$(VERSION) make -C agent datadog_agent_deb
	cp agent/*.deb .
	VERSION=$(VERSION) make -C agent datadog_agent_base_deb
	cp agent/*.deb .

rpm:
	VERSION=$(VERSION) make -C agent datadog_agent_rpm
	cp agent/*.rpm .
	VERSION=$(VERSION) make -C agent datadog_agent_base_rpm
	cp agent/*.rpm .

archivedeb:
	mkdir -p ../artifacts
	cp *.deb ../artifacts

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

