
from checks.munin import MuninPlugin

class PostgresMuninPlugin(MuninPlugin):

    @staticmethod
    def get_name():
        return "postgres"

    @staticmethod
    def parse_metric(check, section, mname, mvalue):
        """ Postgres metrics:
          - section: postgres_[metric type]_[optional database] """

        print section, mname

        ignore = mtype = db = None
        if section.count('_') == 1:
            ignore, mtype = section.split('_')
        else:
            ignore, mtype, db = section.split('_',2)

        print "db:", db, "mtype:", mtype
