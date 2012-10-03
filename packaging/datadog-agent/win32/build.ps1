# Variables
$version = $(python -c "from config import get_version; print get_version()")

# Remove old artifacts
rm build/*.exe
rm build/*.msi

# Build the agent.exe service
python setup.py py2exe
cp dist\agent.exe packaging\datadog-agent\win32\install_files\agent.exe

# Change to the packaging directory
cd packaging\datadog-agent\win32
mkdir build

# Copy checks.d files into the install_files
mkdir install_files\checks.d
cp ..\..\..\checks.d\* install_files\checks.d

# Copy the conf.d files into the install_files
mkdir install_files\conf.d
cp ..\..\..\conf.d\* install_files\conf.d

## Generate the UI install with NSIS

    # Assumes makensis.exe is within the PATH
    makensis /DVersion="$version" nsis/agent.nsi
    mv nsis/DDAgentInstall.exe ..\..\..\build\

## Generate the CLI installer with WiX

    # Generate fragments for the files in checks.d and conf.d
    heat dir install_files\checks.d -gg -dr INSTALLDIR -var var.InstallFilesChecksD -cg checks.d -o wix\checksd.wxs
    heat dir install_files\conf.d -gg -dr APPLIDATIONDATADIRECTORY -t wix\confd.xslt -var var.InstallFilesConfD -cg conf.d -o wix\confd.wxs

    # Create .wixobj files from agent.wxs, confd.wxs, checksd.wxs
    $opts = '-dInstallFiles=install_files', '-dWixRoot=wix', '-dInstallFilesChecksD=install_files\checks.d', '-dInstallFilesConfD=install_files\conf.d', "-dAgentVersion=$version"
    candle $opts wix\agent.wxs wix\checksd.wxs wix\confd.wxs

    # Light to create the msi
    light agent.wixobj checksd.wixobj confd.wixobj -o ..\..\..\build\ddagent.msi

# Clean up
rm *wixobj*
rm -r install_files\conf.d
rm -r install_files\checks.d

# Move back to the root workspace
cd ..\..\..\

# Sign the installers
# TODO

# Install the new version of the agent
msiexec /qn /i build\ddagent.msi
#rm -r build