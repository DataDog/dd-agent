
class PostgresMuninPlugin(MuninPlugin):

    def get_name(self):
        return "postgres"

    def parse_metrics(self, metrics):
        """ Postgres metrics:
          - section: postgres_[metric type]_[optional database] """

        #print section, metrics

        ignore = mtype = db = None
        if section.count('_') == 1:
            ignore, mtype = section.split('_')
        else:
            ignore, mtype, db = section.split('_',2)

        #print "db:", db

        ms = {}
        for m in metrics:
            if m == db:
                ms[mtype] = metrics[m]
            else:
                ms[mtype + '.' + m] = metrics[m]

        #print ms
        if db is not None:
            return 'postgres', { db: ms }
        else:
            return 'postgres', ms

