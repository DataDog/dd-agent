import datetime
import logging
from urlparse import urljoin

log = logging.getLogger('collector')

HEALTH_ENDPOINT = '/healthz'
DEFAULT_NAMESPACE = 'default'  # TODO: use agent's own ns
CM_ENDPOINT = '/namespaces/{namespace}/configmaps'
CM_NAME = 'datadog-leader-elector'
CREATOR_LABEL = 'creator'
ACQUIRE_TIME_LABEL = 'acquired_time'
# TODO: make lease duration configurable
DEFAULT_LEASE_DURATION = 5 * 60  # seconds

class LeaderElector:
    """
    Uses the Kubernetes ConfigMap API to elect a leader among agents.
    This is based on the mechanism described here:
    https://github.com/kubernetes/kubernetes/blob/v1.7.3/pkg/client/leaderelection/leaderelection.go

    The election process goes like this:
    - all agents share the same CM name that they will try and lock
    by overriding its metadata.
    - if the CM doesn't exist or if its last refresh is too old:
      create or replace it with fresh metadata and become the leader
    - if the CM is already locked, there is already a leader agent. Then do nothing

    This process should be triggered regularly (more frequently than the expiration period).
    The leader needs to refresh its status by overriding the acquire-time label in the CM meta.

    This mechanism doesn't ensure uniqueness of the leader because of clock skew.
    A clock sync between nodes in the cluster is highly recommended to minimize this issue.
    """

    def __init__(self, kubeutil):
        self.kubeutil = kubeutil
        self.apiserver_url = kubeutil.kubernetes_api_url
        self.last_acquire_time = None
        if not self._is_reachable():
            return

    def _is_reachable(self):
        health_url = urljoin(self.apiserver_url, HEALTH_ENDPOINT)
        try:
            self.kubeutil.retrieve_json_auth(health_url)
        except Exception as ex:
            log.error("API server is unreachable, disabling leader election. Error: %s" % str(ex))
            return False

    def try_acquire_or_refresh(self):
        """
        if this agent is leader, try and refresh the lock
        otherwise try and acquire it.
        """
        expiry_time = None
        if self.last_acquire_time:
            expiry_time = self.last_acquire_time + datetime.timedelta(seconds=DEFAULT_LEASE_DURATION)

        if self.kubeutil.is_leader:
            if expiry_time and expiry_time - datetime.timedelta(seconds=30) <= datetime.datetime.utcnow():
                self.kubeutil.is_leader = self._try_refresh()
        else:
            if (not expiry_time) or (expiry_time <= datetime.datetime.utcnow()):
                self.kubeutil.is_leader = self._try_acquire()

    def _try_acquire(self):
        """
        _try_acquire tries to acquire the CM lock and return leader status
        i.e. whether it succeeded or failed.
        """
        try:
            cm = self._get_cm()
            if not cm or self._is_lock_expired(cm):
                return self._try_lock_cm(cm)
            else:
                return False
        except Exception as ex:
            log.error("Failed to acquire leader status: %s" % str(ex))
            return False

    def _try_refresh(self):
        # TODO: implement refresh
        try:
            return False
        except Exception as ex:
            log.error("Failed to renew leader status: %s" % str(ex))
            return False

    def _get_cm(self):
        """
        _get_cm returns the ConfigMap if it exists, None if it doesn't
        and raises an exception if several CM with the reserved name exist
        """
        try:
            cm_filter = 'labelSelector=NAME%%3D%s' % CM_NAME
            cm_url = '{}?{}'.format(urljoin(self.apiserver_url, CM_ENDPOINT.format(namespace=DEFAULT_NAMESPACE)), cm_filter)
            res = self.kubeutil.retrieve_json_auth(cm_url).json().get('items')
        except Exception as ex:
            if ex.response.status_code == 404:
                return None
            log.error("Failed to get config map %s. Error: %s" % (CM_NAME, str(ex)))
            return
        if len(res) == 0:
            return None
        elif len(res) == 1:
            cm = res[0]
            acquired_time = cm['metadata'].get('labels', {}).get(ACQUIRE_TIME_LABEL)
            self.last_acquire_time = datetime.datetime.strptime(acquired_time, "%Y-%m-%dT%H:%M:%S.%f")
            return cm
        else:
            raise Exception("Found more than one config map named %s. Failing leader election." % CM_NAME)

    def _is_lock_expired(self, cm):
        acquired_time = cm['metadata'].get('labels', {}).get(ACQUIRE_TIME_LABEL)

        if not acquired_time:
            log.warning("aquired-time wasn't set correctly for the leader lock. Assuming"
                " it's expired so we can reset it correctly.")
            return True

        acquired_time = datetime.datetime.strptime(acquired_time, "%Y-%m-%dT%H:%M:%S.%f")

        if acquired_time + datetime.timedelta(seconds=DEFAULT_LEASE_DURATION) <= datetime.datetime.utcnow():
            return True
        return False

    def _try_lock_cm(self, cm):
        """
        Try and lock the ConfigMap in 2 steps:
            - delete it
            - post the new cm as a replacement. If the post failed,
              a concurrent agent won the race and we're not leader
        """
        create_pl = self._build_create_cm_payload(cm)
        cm_url = self.apiserver_url + CM_ENDPOINT.format(namespace=DEFAULT_NAMESPACE)
        if cm:
            try:
                del_url = '{}/{}'.format(cm_url, cm['metadata']['name'])
                self.kubeutil.delete_to_apiserver(del_url)
            except Exception as ex:
                if ex.response.status_code != 404:  # 404 means another agent removed it already
                    log.error("Couldn't delete config map %s. Error: %s" % (cm['metadata']['name'], str(ex)))
                    return False

        try:
            self.kubeutil.post_to_apiserver(cm_url, create_pl)
        except Exception as ex:
            if ex.response.reason == 'AlreadyExists':
                log.debug("ConfigMap lock '%s' already exists, another agent "
                    "acquired it." % ex.response.json().get('details', {}).get('name', ''))
                return False
            else:
                log.error("Failed to post the ConfigMap lock. Error: %s" % str(ex))
                return False
        return True

    def _build_create_cm_payload(self, cm):
        now = datetime.datetime.utcnow()
        pl = {
            'data': {},
            'metadata': {
                'labels': {
                    CREATOR_LABEL: self.kubeutil.host_name,
                    ACQUIRE_TIME_LABEL: datetime.datetime.strftime(now, "%Y-%m-%dT%H:%M:%S.%f")
                },
                'name': CM_NAME,
                'namespace': DEFAULT_NAMESPACE  # TODO: use agent namespace
            }
        }
        return pl

    def _build_update_cm_payload(self, cm):
        pl = {}
        return pl
