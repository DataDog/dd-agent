#! /usr/bin/python

import sys
import ConfigParser

def main():

    if len(sys.argv) != 3:
        return False

    source = sys.argv[1]
    dest = sys.argv[2]

    # Read config files
    new_config = ConfigParser.RawConfigParser()
    current_config = ConfigParser.RawConfigParser()

    new_config.read(source)
    current_config.read(dest)

    # Update sections from new_config to current_config
    for section in new_config.sections():
        if not current_config.has_section(section):
            current_config.add_section(section)
        for item in new_config.items(section):
            name, value = item
            current_config.set(section, name, value)

    # Write out config
    f = open(dest,'wb')
    current_config.write(f)
    f.close()

if __name__ == "__main__":
    main()
