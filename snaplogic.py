import urllib3, json
from checks import AgentCheck

class SnaplogicTest(AgentCheck):

  def _validate_instance(self, instance):
    for key in ['snaplogic_url', 'orgname', 'basic_auth_user', 'basic_auth_password']:
      if key not in instance:
        raise Exception("Config '{}' must be specified".format(key))


  def check(self, instances):
    self._validate_instance(instances)

    http = urllib3.PoolManager()

    snaplogic_url = instances['snaplogic_url']
    orgname = instances['orgname']
    full_url = "https://" + snaplogic_url + "/api/1/rest/public/snaplex/" + orgname

    basic_auth_string = '{user}:{password}'.format(user = instances['basic_auth_user'], password = instances['basic_auth_password'])

    headers = urllib3.make_headers(basic_auth=basic_auth_string)

    response = http.request('GET', full_url, headers = headers)

    data = json.loads(response.data)

    snaplogic_projects = data["response_map"].items()

    for project_key, project_value in snaplogic_projects:
      for project in project_value["cc_info"]["running"]:
        for stat_name, stat_value in project["stats"].items():
          metric_string = 'snaplogic.{stat_name}'.format(stat_name = stat_name)
          tags = ['project:{project}'.format(project = project_value["cc_info"]["label"]),'snaplogic_hostname:{hostname}'.format(hostname = project["hostname"])]
          if isinstance(stat_value, (str, float, int)) and stat_value != '':
            self.gauge(metric=metric_string, value=stat_value, tags=tags)

    for project_key, project_value in snaplogic_projects:
      for project in project_value["cc_info"]["running"]:
        for stat_name, stat_value in project["info_map"].items():
          metric_string = 'snaplogic.{stat_name}'.format(stat_name = stat_name)
          tags = ['project:{project}'.format(project = project_value["cc_info"]["label"]),'snaplogic_hostname:{hostname}'.format(hostname = project["hostname"])]
          if isinstance(stat_value, (str, float, int)) and stat_value != '':
            self.gauge(metric=metric_string, value=stat_value, tags=tags)

    for project_key, project_value in snaplogic_projects:
      for stat_name, stat_value in project_value["plex_info"].items():
        metric_string = 'snaplogic.{stat_name}'.format(stat_name = stat_name)
        tags = ['project:{project}'.format(project = project_value["cc_info"]["label"]),'snaplogic_hostname:{hostname}'.format(hostname = project["hostname"])]
        if isinstance(stat_value, (str, float)) and stat_value != '':
          self.gauge(metric=metric_string, value=stat_value, tags=tags)