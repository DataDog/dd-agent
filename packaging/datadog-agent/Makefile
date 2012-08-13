
.PHONY: clean dirs install install_deb deb install_rpm rpm

BUILD=build/package

FPM_BUILD=fpm -s dir -C $(BUILD) \
-e \
-n "datadog-agent" \
-a all \
-m "Datadog Packages <package@datadoghq.com>" \
--url "http://www.datadoghq.com/" \
--description "`cat desc`"\
--iteration $(BUILDNUMBER) \
-v "$(VERSION)" \
--depends "datadog-agent-base >= $(VERSION)" \
--depends "datadog-agent-lib >= $(VERSION)"

clean:
	rm -rf build*
	rm -rf *.deb
	rm -rf *.rpm

dirs:
	mkdir -p $(BUILD)

install: dirs
	mkdir -p $(BUILD)/usr/share/datadog/agent
	mkdir -p $(BUILD)/etc/dd-agent/
	mkdir -p $(BUILD)/usr/bin
	cp ../../ddagent.py $(BUILD)/usr/share/datadog/agent
	cp ../../transaction.py $(BUILD)/usr/share/datadog/agent
	cp ../../dogstatsd.py $(BUILD)/usr/share/datadog/agent
	ln -sf ../share/datadog/agent/ddagent.py $(BUILD)/usr/bin/dd-forwarder
	ln -sf ../share/datadog/agent/dogstatsd.py $(BUILD)/usr/bin/dogstatsd

install_deb: install
	mkdir -p $(BUILD)/etc/supervisor/conf.d
	mkdir -p $(BUILD)/usr/bin
	cp deb/supervisor.conf $(BUILD)/etc/dd-agent/supervisor_ddagent.conf
	ln -sf ../../dd-agent/supervisor_ddagent.conf $(BUILD)/etc/supervisor/conf.d/ddagent.conf

install_rpm: install
	cp rpm/supervisor.conf $(BUILD)/etc/dd-agent/supervisor.conf
	cp rpm/setup-supervisor.py $(BUILD)/usr/share/datadog/agent

deb: clean install_deb
	FPM_EDITOR="echo 'Pre-Depends: datadog-agent-base (>= $(VERSION))' >>" \
$(FPM_BUILD) -t deb \
-d "python (>= 2.6)" \
-d "datadog-agent-base" \
-d "python-tornado" \
-d "supervisor (>= 3.0)" \
--post-install deb/postinst \
--post-uninstall deb/postrm \
--pre-install deb/preinst \
--pre-uninstall deb/prerm \
--config-files "/etc/dd-agent/supervisor_ddagent.conf" \
.

rpm: clean install_rpm
	FPM_EDITOR="echo '' >>" \
$(FPM_BUILD) -t rpm \
-d "python(abi) >= 2.6" \
-d "python-tornado" \
-d "datadog-agent-base >= $(VERSION)" \
-d "supervisor" \
--pre-install rpm/preinst \
--post-install rpm/postinst \
--pre-uninstall rpm/prerm \
--config-files "/etc/dd-agent/supervisor.conf" \
.
