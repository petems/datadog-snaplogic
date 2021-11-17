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

    if check_type == 'snaplex':

      full_url = "https://" + snaplogic_url + "/api/1/rest/public/snaplex/" + orgname

      basic_auth_string = '{user}:{password}'.format(user = instances['basic_auth_user'], password = instances['basic_auth_password'])

      headers = urllib3.make_headers(basic_auth=basic_auth_string)

      response = http.request('GET', full_url, headers = headers)

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
      
          stats_metrics = ["active_threads", "active_pipelines", "alive_since", "mem_used", "cpu_user", "max_file_descriptors", "cpu_util", "cc_mem_total", "mem_used_absolute", "disk_free", "disk_total"]
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

            
      
    elif check_type == 'runtime':

      full_url = "https://" + snaplogic_url + "/api/1/rest/public/runtime/" + orgname + "?level=summary&last_hours=1&limit=1000"

      basic_auth_string = '{user}:{password}'.format(user = instances['basic_auth_user'], password = instances['basic_auth_password'])

      headers = urllib3.make_headers(basic_auth=basic_auth_string)

      failing_states = ["Failing", "Failed", "Suspended", "Suspending"]

      non_failing_states = ["Queued","NoUpdate","Prepared","Started","Completed","Stopped","Stopping","Resuming"]

    # Response Example: https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438155/Pipeline+Monitoring+API
    # {
    #                 "pipe_id": "29cd6375-b460-4456-8fa7-08a85756394f",
    #                 "has_lints": false,
    #                 "documents": 1,
    #                 "user_id": "schelluri@snaplogic.com",
    #                 "ccid": "60af8acdf0bb32d4cf1a6371",
    #                 "child_has_lints": false,
    #                 "runtime_path_id": "snaplogic/rt/cloud/dev",
    #                 "parent_ruuid": "52e99318640a9a03d8681d0d_e929e44c-f513-4fe4-984e-a8a37533cc23",
    #                 "subpipes": {},
    #                 "state_timestamp": "2021-06-11T21:03:45.685000+00:00",
    #                 "error_documents": 0,
    #                 "label": "SUB - Generic Parameters for Pipelines",
    #                 "path_id": "/snaplogic/projects/projects-Production-VerizonProd",
    #                 "state": "Completed",
    #                 "create_time": "2021-06-11T21:03:45.685000+00:00",
    #                 "invoker": "nested_pipeline",
    #                 "duration": 0,
    #                 "cc_label": "pa22sl-jcc-04c336c2838755d63",
    #                 "id": "52e99318640a9a03d8681d0d_0daa1437-bc43-46ec-8858-1e95cc1887d2",
    #                 "runtime_label": "cloud-dev",
    #                 "mode": "standard"
    # }
      tags_array = ["pipe_id","has_lints","documents","user_id","ccid","child_has_lints","runtime_path_id","parent_ruuid","subpipes",
      "state_timestamp","error_documents","label","path_id","state",
      "create_time","invoker","duration","cc_label","id","runtime_label","mode"]

      tags_list = {}

      failing_pipelines = 0
      successful_pipelines = 0

      for non_failed_state in non_failing_states:

        non_failed_state_url = full_url + "&state={non_failed_state}".format(non_failed_state=non_failed_state)

        response = http.request('GET', non_failed_state_url, headers = headers)

        data = json.loads(response.data)

        snaplogic_pipelines = data["response_map"]["entries"]

        if not snaplogic_pipelines:
          self.log.debug("No Pipeline in {state} found".format(state=non_failed_state))  
          pass

        self.log.debug("- RESPONSE DEBUG START - ")

        self.log.debug(snaplogic_pipelines)

        self.log.debug("- RESPONSE DEBUG END - ")

        for pipeline_response in snaplogic_pipelines:
    
          for tag_name in tags_array:
            tags_list[tag_name] = pipeline_response[tag_name]

          self.event({
            'timestamp': int(time.time()),
            'event_type': 'Snaplogic',
            'alert_type': 'info',
            'msg_title': "Snaplogic: {pipe_id} - State is '{non_failed_state}'".format(
              pipe_id=pipeline_response["pipe_id"],
              non_failed_state=pipeline_response["state"],
            ),
            'tags': self.dict_to_string_tags(tags_list),
            'msg_text': json.dumps(pipeline_response),
            'aggregation_key': pipeline_response["pipe_id"],
          })

          successful_pipelines += 1

      for failed_state in failing_states:

        failed_state_url = full_url + "&state={failed_state}".format(failed_state=failed_state)

        response = http.request('GET', failed_state_url, headers = headers)

        data = json.loads(response.data)

        snaplogic_pipelines = data["response_map"]["entries"]

        if not snaplogic_pipelines:
          self.log.debug("No Pipeline in {state} found".format(state=failed_state))  
          pass

        self.log.debug("- RESPONSE DEBUG START - ")

        self.log.debug(snaplogic_pipelines)

        self.log.debug("- RESPONSE DEBUG END - ")

        for pipeline_response in snaplogic_pipelines:
    
          for tag_name in tags_array:
            tags_list[tag_name] = pipeline_response[tag_name]

          self.event({
                'timestamp': int(time.time()),
                'event_type': 'Snaplogic',
                'alert_type': 'error',
                'msg_title': "Snaplogic: {pipe_id} is failing - State is '{failed_state}'".format(
                    pipe_id=pipeline_response["pipe_id"],
                    failed_state=pipeline_response["state"],
                ),
                'tags': self.dict_to_string_tags(tags_list),
                'msg_text': json.dumps(pipeline_response),
                'aggregation_key': pipeline_response["pipe_id"],
          })

          failing_pipelines += 1
  
      self.gauge(name='snaplogic.runtime.failed_pipelines', value=failing_pipelines, tags=["service:snaplogic"])

      self.gauge(name='snaplogic.runtime.successful_pipelines', value=successful_pipelines, tags=["service:snaplogic"])

    else:
      raise Exception("check_type '{}' not known".format(check_type))


