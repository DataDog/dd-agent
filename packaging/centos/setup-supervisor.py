#! /usr/bin/python
import ConfigParser
import sys


def main():

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        return False

    source = sys.argv[1]
    dest = sys.argv[2]

    # Read config files
    new_config = ConfigParser.RawConfigParser()
    current_config = ConfigParser.RawConfigParser()

    new_config.read(source)
    current_config.read(dest)

    print "Cleaning up supervisord configuration"
    # Remove sections from new_config in current_config
    for section in new_config.sections():
        if current_config.has_section(section):
            if section != "supervisorctl" and section != "supervisord":
                current_config.remove_section(section)

    # Write out config
    f = open(dest,'wb')
    current_config.write(f)
    f.close()

if __name__ == "__main__":
    main()
