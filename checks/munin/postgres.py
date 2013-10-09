
from checks.munin import MuninPlugin

class PostgresMuninPlugin(MuninPlugin):

    @staticmethod
    def get_name():
        return "postgres"

    @staticmethod
    def parse_metric(check, section, device, mname, mvalue, mgraph = None):
        """ Postgres metrics:
          - section: postgres_[metric type]_[optional database] """

        #remove postgres_ from begining, remove trailing _ if any
        mtype = section.split('_',1)[1]

        if device == "ALL" or mtype == 'connections_db' or device == mname:
            device = mname
            mname = "munin.postgres.%s" % mtype
        else:
            mname = "munin.postgres.%s.%s" % (mtype, mname)
      
        check.register_metric(mname)
        check.save_sample(mname,mvalue,device_name=device) 
