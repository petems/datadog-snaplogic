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
      project_tag = project_value["cc_info"]["label"]
      for project in project_value["cc_info"]["running"]:
        snaplogic_hostname_tag      = project["hostname"]
    
        stats_metrics = ["active_threads", "active_pipelines"]
        stats_metric_kv = {}
        for metric_name in stats_metrics:
          metric_string = 'snaplogic.cc_info.{metric_name}'.format(metric_name = metric_name)
          metric_value = project["stats"][metric_name]
          stats_metric_kv[metric_string] = metric_value
        
        info_map_metrics = ["jvm_max_mem_size"]
        info_map_metric_kv = {}
        for metric_name in info_map_metrics:
          metric_string = 'snaplogic.info_map.{metric_name}'.format(metric_name = metric_name)
          metric_value = project["info_map"][metric_name]
          info_map_metric_kv[metric_string] = metric_value

        tags = [os_name_tag, project_tag, snaplogic_hostname_tag]

        tags = [
          'project:{project}'.format(project = project_tag),
          'snaplogic_hostname:{hostname}'.format(hostname = snaplogic_hostname_tag)
        ]

        for key, value in info_map_metric_kv.items(): 
          self.gauge(name=key, value=value, tags=tags)

        for key, value in stats_metric_kv.items(): 
          self.gauge(name=key, value=value, tags=tags)

