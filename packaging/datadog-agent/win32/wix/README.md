# Building the WiX MSI

* Make sure the `agent.exe` executable is in `../install_files`. See `README.md` one level up for more info.

1. Generate the `.wixobj` file with `candle`
```
C:\path\to\WiX\bin\candle.exe agent.wxs
```

2. Link the `.wixobj` file with `light` to generate the `agent.msi` file.
```
C:\path\to\WiX\bin\light.exe agent.wixobj
```

# Installing the MSI from the command line

* Use `msiexec.exe` to install the Agent service
* Admin privillages are required to install the MSI.

* To install with a simple UI, use:

```
msiexec.exe /i agent.msi APIKEY="[YOUR API KEY HERE]"
```

* For a quiet install, use:

```
msiexec.exe /i agent.msi /qn APIKEY="[YOUR API KEY HERE]"
```