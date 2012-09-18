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

3. Build the UI installer in the `nsis` folder. (See `nsis/README.md`)

4. Build the CLI installer in the `wix` folder. (See `wix/README.md`)