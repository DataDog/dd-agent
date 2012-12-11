# Builds the datadog agent distributions using fpm.


#============
# Constants
#============

BUILD=build/package
SRC=../
ROOT=root
BUILD_NUMBER ?= 0

VERSION=`PYTHONPATH=$(SRC) python -c "from config import get_version; print get_version()"`

FPM_BUILD=fpm -s dir -e -C $(BUILD) \
-a all -m "Datadog Packages <package@datadoghq.com>" \
--url "http://www.datadoghq.com/" \
--description "`cat desc`"\
-v $(VERSION) \
--vendor Datadog \
--iteration $(BUILD_NUMBER)


#=============
# COMMON
#=============

clean:
	rm -rf $(ROOT)
	rm -rf build
	rm -f *.deb *.rpm

# Copy the code + static files we want to deploy to our
# root directory.
source:
	mkdir -p $(ROOT)
	cp -r $(SRC)/checks $(ROOT)/
	cp -r $(SRC)/dogstream $(ROOT)/
	cp -r $(SRC)/pup $(ROOT)/
	cp -r $(SRC)/yaml $(ROOT)/
	cp -r $(SRC)/checks.d $(ROOT)/
	cp -r $(SRC)/compat $(ROOT)/
	cp -r $(SRC)/conf.d $(ROOT)/
	cp -r $(SRC)/resources $(ROOT)/
	cp -r $(SRC)/*.py $(ROOT)/
	cp -r $(SRC)/LICENSE* $(ROOT)/
	cp -r $(SRC)/datadog.conf.example $(ROOT)/
	find $(ROOT) -name "*.pyc" -exec rm {} \;


# Layout all of the files common to both versions of the agent in
# the build directory.
install_base: source
	mkdir -p $(BUILD)
	mkdir -p $(BUILD)/usr/share/datadog/agent
	mkdir -p $(BUILD)/etc/dd-agent
	mkdir -p $(BUILD)/usr/bin
	mkdir -p $(BUILD)/var/log/datadog
	# Install the common source & config.
	cp -r $(ROOT)/*		 $(BUILD)/usr/share/datadog/agent/
	cp    $(ROOT)/datadog.conf.example $(BUILD)/etc/dd-agent
	# Install the common executables.
	ln -sf ../share/datadog/agent/dogstatsd.py  $(BUILD)/usr/bin/dogstatsd
	ln -sf ../share/datadog/agent/agent.py      $(BUILD)/usr/bin/dd-agent
	chmod 755 $(BUILD)/usr/bin/dogstatsd
	chmod 755 $(BUILD)/usr/bin/dd-agent
	chmod 755 $(BUILD)/var/log/datadog

install_full: source
	# Install the forwarder.
	mkdir -p $(BUILD)/usr/bin
	ln -sf ../share/datadog/agent/ddagent.py $(BUILD)/usr/bin/dd-forwarder
	chmod 755 $(BUILD)/usr/bin/dd-forwarder

# =====================
# RPM
# =====================

install_base_rpm: install_base
	mkdir -p $(BUILD)/etc/init.d
	cp datadog-agent-base-rpm/datadog-agent-redhat $(BUILD)/etc/init.d/datadog-agent
	chmod 755 $(BUILD)/etc/init.d/datadog-agent


install_full_rpm: install_base_rpm install_full
	mkdir -p $(BUILD)/etc/dd-agent
	mkdir -p $(BUILD)/usr/share/datadog/agent
	cp datadog-agent-rpm/supervisor.conf $(BUILD)/etc/dd-agent/supervisor.conf
	cp datadog-agent-rpm/setup-supervisor.py $(BUILD)/usr/share/datadog/agent

datadog_agent_base_rpm: clean install_base_rpm
	FPM_EDITOR="echo '' >>" \
$(FPM_BUILD) -t rpm \
-n datadog-agent-base \
-d "python(abi) >= 2.4" \
-d "python-uuid" \
-d "sysstat" \
-d "pexpect" \
--replaces "datadog-agent-lib  < 3.4.0" \
--pre-install datadog-agent-base-rpm/pre_install \
--post-install datadog-agent-base-rpm/post_install \
--pre-uninstall datadog-agent-base-rpm/pre_uninstall \
.

datadog_agent_rpm: clean install_full_rpm
	FPM_EDITOR="echo ''>>"  \
$(FPM_BUILD) -t rpm \
-n "datadog-agent" \
-d "python(abi) >= 2.6" \
-d "python-tornado >= 2.3" \
-d "supervisor >= 3.0" \
-d "sysstat" \
-d "pexpect" \
--conflicts "datadog-agent < $(VERSION)" \
--replaces "datadog-agent-base < 3.4.0" \
--replaces "datadog-agent-lib  < 3.4.0" \
--pre-install	    datadog-agent-rpm/preinst \
--post-install	    datadog-agent-rpm/postinst \
--pre-uninstall	    datadog-agent-rpm/prerm \
--config-files "/etc/dd-agent/supervisor.conf" \
.


# =====================
# DEBIAN
# =====================

install_base_deb: install_base
	mkdir -p $(BUILD)/etc/init.d
	cp datadog-agent-base-deb/datadog-agent.init $(BUILD)/etc/init.d/datadog-agent
	chmod 755 $(BUILD)/etc/init.d/datadog-agent


# Install the forwarder and supervisor on debian.
install_full_deb: install_base_deb install_full
	# Install supervisor config.
	#   FIXME mattp: why do we need both of these?
	mkdir -p $(BUILD)/etc/supervisor/conf.d
	cp datadog-agent-deb/supervisor.conf $(BUILD)/etc/dd-agent/supervisor_ddagent.conf
	mkdir -p $(BUILD)/etc/supervisor/conf.d/
	cp datadog-agent-deb/supervisor.conf $(BUILD)/etc/supervisor/conf.d/ddagent.conf


# Make the datadog agent debian package that includes supervisor, the forwarder
# etc.
datadog_agent_deb: clean install_full_deb
	FPM_EDITOR="echo 'Replaces: datadog-agent (<= $(VERSION)), datadog-agent-base (<= $(VERSION)), datadog-agent-lib' >>" \
$(FPM_BUILD) -t deb \
-n datadog-agent \
-d "python (>= 2.6)" \
-d "python-tornado (>= 2.3)" \
-d "supervisor (>= 3.0)" \
-d "adduser" \
-d "sysstat" \
-d "python-pexpect" \
--config-files "/etc/dd-agent/supervisor_ddagent.conf" \
--post-install datadog-agent-deb/postinst \
--post-uninstall datadog-agent-deb/postrm \
--pre-uninstall  datadog-agent-deb/prerm \
.


# Make the database agent base debian package.
datadog_agent_base_deb: clean install_base_deb
	FPM_EDITOR="echo 'Replaces: datadog-agent-base (<= $(VERSION)), datadog-agent-lib' >>" \
$(FPM_BUILD) -t deb \
-n datadog-agent-base \
-d "python >= 2.4" \
-d "adduser" \
-d "sysstat" \
-d "python-pexpect" \
--post-install   datadog-agent-base-deb/postinst \
--post-uninstall datadog-agent-base-deb/postrm \
--pre-uninstall  datadog-agent-base-deb/prerm \
.

#===================
# JENKINS TARGETS
#===================

deb:
	mkdir -p ../artifacts
	make datadog_agent_base_deb
	cp *.deb ../artifacts
	make datadog_agent_deb
	cp *.deb ../artifacts

rpm:
	mkdir -p ../dist
	make datadog_agent_base_rpm
	cp *.rpm ../dist
	make datadog_agent_rpm
	cp *.rpm ../dist

installdeb:
	dpkg -i --force-confdef --force-confnew `ls -t ../artifacts/datadog-agent_*.deb | head -1`

deb_repo:
	rm Packages.gz
	sudo dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz

tmp:
	cp *.deb /tmp/shared || true
	cp *.rpm /tmp/shared || true

all: clean deb rpm


