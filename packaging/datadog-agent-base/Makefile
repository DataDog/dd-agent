.PHONY: clean links dirs deb rpm install_deb install_rpm install

BUILD=build/package
CWD=$(shell pwd)

FPM_BUILD=fpm -s dir -C $(BUILD) -e -n "datadog-agent-base" \
-a all -m "Datadog Packages <package@datadoghq.com>" \
--url "http://www.datadoghq.com/" \
--config-files "/etc/init.d/datadog-agent" \
--config-files "/etc/dd-agent/datadog.conf.example" \
--description "`cat desc`"\
--iteration $(BUILDNUMBER) \
-d "datadog-agent-lib >= $(VERSION)" \
-v $(VERSION)

clean:
	rm -f resources compat
	rm -f agent.py daemon.py minjson.py util.py emitter.py config.py modules.py aggregator.py conf.d
	rm -rf *.pyc
	rm -rf build*
	rm -rf *.egg-info
	rm -rf dist
	rm -rf *.deb
	rm -rf *.rpm

links:
	ln -sf ../../resources  .
	ln -sf ../../compat     .
	ln -sf ../../agent.py   .
	ln -sf ../../daemon.py  .
	ln -sf ../../minjson.py .
	ln -sf ../../util.py    .
	ln -sf ../../emitter.py .
	ln -sf ../../config.py  .
	ln -sf ../../graphite.py  .
	ln -sf ../../modules.py  .
	ln -sf ../../aggregator.py .
	ln -sf ../../conf.d .
	ln -sf ../../dogstatsd.py .

dirs:
	mkdir -p $(BUILD)

install: dirs links
	PYTHONPATH=$(BUILD) python setup.py install --root=$(BUILD) --install-layout=deb --install-lib=/usr/share/datadog/agent --install-scripts=/usr/share/datadog/agent --no-compile
	mkdir -p $(BUILD)/usr/bin
	mkdir -p $(BUILD)/etc/init.d
	rm -rf $(BUILD)/home
	rm -rf $(BUILD)/usr/share/datadog/agent/*.egg-info
	chmod 644 $(BUILD)/usr/share/datadog/agent/config.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/util.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/daemon.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/minjson.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/emitter.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/graphite.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/modules.py
	chmod 644 $(BUILD)/usr/share/datadog/agent/aggregator.py
	ln -sf ../share/datadog/agent/agent.py $(BUILD)/usr/bin/dd-agent
	ln -sf ../share/datadog/agent/dogstatsd.py $(BUILD)/usr/bin/dogstatsd

install_deb: install
	cp deb/datadog-agent.init $(BUILD)/etc/init.d/datadog-agent
	chmod 755 $(BUILD)/etc/init.d/datadog-agent

install_rpm: install
	cp rpm/datadog-agent-redhat $(BUILD)/etc/init.d/datadog-agent
	chmod 755 $(BUILD)/etc/init.d/datadog-agent

deb: clean install_deb
	FPM_EDITOR="echo 'Replaces: datadog-agent (<= 3.2.3)' >>" \
$(FPM_BUILD) -t deb \
-d "python >= 2.4" \
-d "adduser" \
-d "sysstat" \
-d "python-pexpect" \
--post-install deb/postinst \
--post-uninstall deb/postrm \
--pre-uninstall deb/prerm \
.

rpm: clean install_rpm
	FPM_EDITOR="$(CWD)/rpm/inject.sh" \
$(FPM_BUILD) -t rpm \
-d "python(abi) >= 2.4" \
-d "python-uuid" \
-d "sysstat" \
-d "pexpect" \
--pre-install rpm/pre_install \
--post-install rpm/post_install \
--pre-uninstall rpm/pre_uninstall \
etc/init.d/datadog-agent \
etc/dd-agent/datadog.conf.example \
etc/dd-agent/conf.d \
usr/share/datadog \
usr/bin
