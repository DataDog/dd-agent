# stdlib
import requests
import time

# project
from checks import AgentCheck


class TeamCity(AgentCheck):
    headers = {'Accept': 'application/json'}
    server = None

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.last_build_ids = {}
        if self.init_config.get("server") is None:
            raise Exception("You must specify a server in teamcity.yaml")
        self.server = self.init_config["server"]

    def _initialize_if_required(self, instance_name, build_configuration):
        if self.last_build_ids.get(instance_name, None) is None:
            self.log.info("Initializing {0}".format(instance_name))
            request = requests.get(
                "http://{0}/guestAuth/app/rest/builds/?locator=buildType:{1},count:1".format(self.server,
                                                                                           build_configuration),
                timeout=30, headers=self.headers)
            if request.status_code != requests.codes.ok:
                raise Exception("TeamCity reported error on initialization. Status code: {0}".format(request.status_code))
            last_build_id = request.json()["build"][0]["id"]
            self.log.info("Last build id for {0} is {1}.".format(instance_name, last_build_id))
            self.last_build_ids[instance_name] = last_build_id

    def _build_and_send_event(self, new_build, instance_name, is_deployment, host, tags):
        self.log.info("Found new build with id {0}, saving and alerting.".format(new_build["id"]))
        self.last_build_ids[instance_name] = new_build["id"]

        output = {
            "timestamp": int(time.time()),
            "alert_type": "info",
            "tags": []
        }
        if is_deployment:
            output["event_type"] = "deployment"
            output["msg_title"] = "{0} deployed to {1}".format(instance_name, host)
            output["msg_text"] = "Build Number: {0}\n\nMore Info: {1}".format(new_build["number"], new_build["webUrl"])
            output["tags"].append("deployment")
        else:
            output["event_type"] = "build"
            output["msg_title"] = "Build for {0} successful".format(instance_name)
            output["msg_text"] = "Build Number: {0}\nDeployed To: {1}\n\nMore Info: {2}".format(new_build["number"], host,
                                                                                             new_build["webUrl"])
            output["tags"].append("build")

        if tags is not None:
            output["tags"].extend(tags)
        if host is not None:
            output["host"] = host

        self.event(output)

    def check(self, instance):
        instance_name = instance.get("name")
        if instance_name is None:
            raise Exception("Each instance must have a name")
        build_configuration = instance.get("build_configuration")
        if build_configuration is None:
            raise Exception("Each instance must have a build configuration")
        host = instance.get("host_affected")
        tags = instance.get("tags")
        is_deployment = instance.get("is_deployment")
        if type(is_deployment) is not bool:
            is_deployment = instance.get("is_deployment").lower() == "true"

        self._initialize_if_required(instance_name, build_configuration)

        request = requests.get(
            "http://{0}/guestAuth/app/rest/builds/?locator=buildType:{1},sinceBuild:id:{2},status:SUCCESS".format(
                self.server, build_configuration, self.last_build_ids[instance_name]), timeout=30,
            headers=self.headers)

        if request.status_code != requests.codes.ok:
            raise Exception("TeamCity reported error on check. Status code: {0}".format(request.status_code))

        new_builds = request.json()

        if new_builds["count"] == 0:
            self.log.info("No new builds found.")
        else:
            self._build_and_send_event(new_builds["build"][0], instance_name, is_deployment, host, tags)

