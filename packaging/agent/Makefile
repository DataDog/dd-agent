# Builds the datadog agent distributions using fpm.


#
# Constants
#

BUILD=build/package
SRC=../..
ROOT=root

VERSION=`PYTHONPATH=$(SRC) python -c "from config import get_version; print get_version()"`

FPM_BUILD=fpm -s dir -e -C $(BUILD) \
-a all -m "Datadog Packages <package@datadoghq.com>" \
--url "http://www.datadoghq.com/" \
--description "`cat desc`"\
-v $(VERSION) \
--iteration $(BUILDNUMBER)


#
# Targets
#

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


# Layout all of the files common to both versions of the agent in
# the build directory.
install_base: source
	mkdir -p $(BUILD)
	mkdir -p $(BUILD)/usr/share/datadog/agent
	mkdir -p $(BUILD)/etc/dd-agent
	mkdir -p $(BUILD)/usr/bin
	# Install the common source.
	cp -r $(ROOT)/*		 $(BUILD)/usr/share/datadog/agent/
	# Install the common executables.
	ln -sf ../share/datadog/agent/dogstatsd.py  $(BUILD)/usr/bin/dogstatsd
	ln -sf ../share/datadog/agent/agent.py      $(BUILD)/usr/bin/dd-agent
	chmod 755 $(BUILD)/usr/bin/dogstatsd
	chmod 755 $(BUILD)/usr/bin/dd-agent


install_base_deb: install_base
	mkdir -p $(BUILD)/etc/init.d
	cp datadog-agent-base-deb/datadog-agent.init $(BUILD)/etc/init.d/datadog-agent
	chmod 755 $(BUILD)/etc/init.d/datadog-agent


# Install the forwarder and supervisor on debian.
install_full_deb: install_base_deb
	# Install the forwarder.
	mkdir -p $(BUILD)/usr/bin
	ln -sf ../share/datadog/agent/ddagent.py $(BUILD)/usr/bin/dd-forwarder
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
--config-files "/etc/dd-agent/supervisor_ddagent.conf" \
--post-install   datadog-agent-deb/postinst \
--post-uninstall datadog-agent-deb/postrm \
--pre-install    datadog-agent-deb/preinst \
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

#deb: clean install
#	FPM_EDITOR="echo 'Replaces: datadog-agent (<< 2.0), datadog-agent-base (<< $(VERSION))' >>" \
#$(FPM_BUILD) -t deb \
#-d "python (>= 2.4)" \
#.
#
#rpm: clean install
#	FPM_EDITOR="$(CWD)/rpm/inject.sh" \
#$(FPM_BUILD) -t rpm \
#-d "python" \
#.
