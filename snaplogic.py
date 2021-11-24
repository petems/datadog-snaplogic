import urllib3, json, datetime, ssl, time, datetime
from checks import AgentCheck

class SnaplogicTest(AgentCheck):

  def _disable_ssl_verification(self):
    try:
      _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
      # Legacy Python that doesn't verify HTTPS certificates by default
      pass
    else:
      # Handle target environment that doesn't support HTTPS verification
      ssl._create_default_https_context = _create_unverified_https_context

  def _check_connection(self, response):
    if response.status != 200:
      self.log.error("Error Connecting to {url}: {status} - {data}".format(url=response.request_url, status=response.status, data=response.data))
      return

  def _validate_instance(self, instance):
    for key in ['snaplogic_url', 'orgname', 'basic_auth_user', 'basic_auth_password']:
      if key not in instance:
        raise Exception("Config '{}' must be specified".format(key))

  def dict_to_string_tags(self, dict_to_convert):
    array_of_tag_strings = []
    for key, value in dict_to_convert.items():
      metric_string = '{key}:{value}'.format(key = key, value = value)
      array_of_tag_strings.append(metric_string)
    return array_of_tag_strings

  def check(self, instances):
    self._validate_instance(instances)

    # appears to be a temporary cert issue sometimes:
    # https://community.snaplogic.com/t/snaplex-nodes-running-with-customer-signed-ssl-certificate-default-snaplogic-ssl-certificate-selected-and-returned-by-server-during-ssl-handshake/2675
    self._disable_ssl_verification()

    http = urllib3.PoolManager()

    snaplogic_url = instances['snaplogic_url']
    orgname = instances['orgname']

    # Default to snaplex if not found
    check_type = instances.get('check_type', 'snaplex')

    full_url = "https://" + snaplogic_url + "/api/1/rest/public/snaplex/" + orgname

    basic_auth_string = '{user}:{password}'.format(user = instances['basic_auth_user'], password = instances['basic_auth_password'])

    headers = urllib3.make_headers(basic_auth=basic_auth_string)

    response = http.request('GET', full_url, headers = headers)

    self._check_connection(response)

    if response.status != 200:
      return

    data = json.loads(response.data)

    snaplogic_projects = data["response_map"].items()

    tags_list = {}

    for _, project_value in snaplogic_projects:

      for project in project_value["cc_info"]["running"]:

        tags_list["snaplogic_hostname"] = project["hostname"]
        tags_list["snaplogic_availability"] = project["availability"]
        tags_list["snaplogic_container_type"] = project["container_type"]
        tags_list["snaplogic_create_time"] = project["create_time"]
        tags_list["snaplogic_heartbeat"] = project["last_heartbeat"]
        tags_list["snaplogic_version"] = project["version"]
        tags_list["snaplogic_pkg_comment"] = project["pkg_comment"]

        tags_list["snaplogic_os_name"] = project["info_map"]["os_name"]

        tags_list["snaplogic_alive_since_string"] = datetime.datetime.fromtimestamp(project["stats"]["alive_since"]/1000.0).strftime('%Y-%m-%d %H:%M:%S')

        stats_metrics = ["active_threads", "active_pipelines", "alive_since", "mem_used", "cpu_user", "leased_slots", "max_file_descriptors", "cpu_util", "cc_mem_total", "mem_used_absolute", "disk_free", "disk_total"]
        stats_metric_kv = {}
        for metric_name in stats_metrics:
          metric_string = 'snaplogic.cc_info.{metric_name}'.format(metric_name = metric_name)
          metric_value = project["stats"][metric_name]
          stats_metric_kv[metric_string] = metric_value

        info_map_metrics = ["total_mem_size", "total_swap_size", "jvm_max_mem_size"]
        info_map_metric_kv = {}
        for metric_name in info_map_metrics:
          metric_string = 'snaplogic.info_map.{metric_name}'.format(metric_name = metric_name)
          metric_value = project["info_map"][metric_name]
          info_map_metric_kv[metric_string] = metric_value

        tags = self.dict_to_string_tags(tags_list)

        for key, value in info_map_metric_kv.items():
          self.gauge(name=key, value=value, tags=tags)

        for key, value in stats_metric_kv.items():
          self.gauge(name=key, value=value, tags=tags)