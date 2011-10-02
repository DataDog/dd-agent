
.PHONY: clean dirs install install_deb deb install_rpm rpm

BUILD=build/package

FPM_BUILD=fpm -s dir -C $(BUILD) \
	 -e \
     -n "datadog-agent" \
     -a all \
     -m "Datadog Packages <package@datadoghq.com>" \
     --url "http://www.datadoghq.com/" \
     --description "`cat desc`"\
     -v "`PYTHONPATH=../.. python -c 'from config import get_version; print get_version()'`" \

clean:
	rm -rf build*
	rm -rf *.deb
	rm -rf *.rpm

dirs:
	mkdir -p $(BUILD)

install: dirs
	mkdir -p $(BUILD)/usr/share/datadog/agent
	mkdir -p $(BUILD)/etc/dd-agent/
	cp ../../ddagent.py $(BUILD)/usr/share/datadog/agent
	cp ../../transaction.py $(BUILD)/usr/share/datadog/agent

install_deb: install
	mkdir -p $(BUILD)/etc/supervisor/conf.d
	mkdir -p $(BUILD)/usr/bin
	cp deb/supervisor.conf $(BUILD)/etc/dd-agent/	
	ln -sf ../../dd-agent/supervisor_ddagent.conf $(BUILD)/etc/supervisor/conf.d/ddagent.conf
	ln -sf ../share/datadog/agent/ddagent.py $(BUILD)/usr/bin/dd-forwarder

install_rpm: install
	

deb: clean install_deb
	FPM_EDITOR="echo 'Pre-Depends: datadog-agent-base (>= 2.0)' >>" \
	$(FPM_BUILD) -t deb \
        -d "python (>= 2.6)" \
        -d "datadog-agent-base" \
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
	  -d "python26" \
	  -d "python26-tornado" \
	  -d "datadog-agent-base" \
	  -d "supervisor" \
      --post-install rpm/postinst \
      .
