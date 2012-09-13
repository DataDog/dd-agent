# Building for Windows

*Run in the root `dd-agent` directory*

1. Build the executables for Windows. In the root agent directory run:
```python
python setup.py py2exe
```

2. Copy the files to the right place.
```bash
mv dist/*.exe packaging/datadog-agent/win32/install_files
```

3. Build the installer using NSIS GUI or command line, using the `agent_msi.nsi` file.

4. The install `DDAgentInstaller.exe` will be created.