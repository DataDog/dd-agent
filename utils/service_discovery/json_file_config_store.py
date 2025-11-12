# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# std
import logging
import simplejson as json

# project
from utils.service_discovery.abstract_config_store import AbstractConfigStore, KeyNotFound

DEFAULT_FILE_PATH = '/etc/dd-agent/sd.json'
log = logging.getLogger(__name__)

class JsonStore(AbstractConfigStore):
    """Implementation of a config store client for flat json files"""
    def _extract_settings(self, config):
        """Extract settings from a config object"""
        settings = {
            'file_path': config.get('sd_json_file_path', DEFAULT_FILE_PATH),
        }
        return settings

    def get_client(self, reset=False):
        """Return a file client, create it if needed"""
        if self.client is None or reset is True:
            with open(self.settings.get('file_path')) as f:
                self.client = json.load(f)
        return self.client

    def client_read(self, path, **kwargs):
        """Retrieve a value from the json dict."""
        if kwargs.get('watch', False):
            # json file never reloads
            return 0

        if kwargs.get('all', False):
            # This wants a list of tuples with the first element of the tuple
            # being the path and the second element of the tuple being json.
            # This is 2 levels past the depth of the sd_template_dir
            return self._get_as_path_items(self.client, len(self.sd_template_dir.split("/")) + 2)
        else:
            res = self._get_nested_path(self.client, path)
            if res is not None:
                return json.dumps(res)
            else:
                raise KeyNotFound("The key %s was not found in the json file" % path)

    def _get_as_path_items(self, data, depth, prefix = ""):
        results = []
        if depth == 1:
            for key in data.iterkeys():
                keystr = prefix.lstrip("/") + "/" + key
                results.append((keystr, json.dumps(data[key])))
        else:
            for key in data.iterkeys():
                prefix = prefix + "/" + key
                results.extend(self._get_as_path_items(data[key], depth - 1, prefix))

        return results

    def _get_nested_path(self, data, path):
        path_elements = path.split('/')
        if data is None:
            return None
        elif len(path_elements) > 1:
            first_element = path_elements[0]
            return self._get_nested_path(data.get(first_element), "/".join(path_elements[1:]))
        else:
            return data.get(path_elements[0])
