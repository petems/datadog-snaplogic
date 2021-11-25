import urllib3, json, datetime, ssl, time, datetime
from checks import AgentCheck

class SnaplogicAlerts(AgentCheck):

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
      self.log.error("Error Connecting to {url}: {status} - {data}".format(url=response.geturl(), status=response.status, data=response.data))
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

    full_url = "https://" + snaplogic_url + "/api/1/rest/public/runtime/" + orgname + "?level=summary&last_hours=1&limit=1000"

    basic_auth_string = '{user}:{password}'.format(user = instances['basic_auth_user'], password = instances['basic_auth_password'])

    headers = urllib3.make_headers(basic_auth=basic_auth_string)

    failing_states = ["Failing", "Failed", "Suspended", "Suspending"]
    success_states = ["Queued","NoUpdate","Prepared","Started","Completed","Stopped","Stopping","Resuming"]
    all_states = failing_states + success_states
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
    #
    tags_array = ["pipe_id","has_lints","documents","user_id","ccid","child_has_lints","runtime_path_id","parent_ruuid","subpipes",
    "state_timestamp","error_documents","label","path_id","state",
    "create_time","invoker","duration","cc_label","id","runtime_label","mode"]

    tags_list = {}

    for state in all_states:
      state_url = full_url + "&state={state}".format(state=state)

      response = http.request('GET', state_url, headers = headers)

      self._check_connection(response)

      if response.status != 200:
        return

      data = json.loads(response.data)
      snaplogic_pipelines = data["response_map"]["entries"]

      if not snaplogic_pipelines:
        self.log.debug("No Pipeline in {state} found".format(state=state))
        pass

      for pipeline_response in snaplogic_pipelines:

        for tag in tags_array:
          tags_list[tag] = pipeline_response[tag]

        tags = self.dict_to_string_tags(tags_list)

        runtime_metrics = ["documents", "duration"]
        runtime_metric_kv = {}
        for metric_name in runtime_metrics:
          metric_string = 'snaplogic.runtime.{metric_name}'.format(metric_name = metric_name)
          metric_value = pipeline_response[metric_name]
          runtime_metric_kv[metric_string] = metric_value
        
        for key, value in runtime_metric_kv.items():
          self.gauge(name=key, value=value, tags=tags)

      total_count_url = "https://" + snaplogic_url + "/api/1/rest/public/runtime/" + orgname + "?level=summary&last_hours=1&limit=1" + "&state={state}".format(state=state)

      headers = urllib3.make_headers(basic_auth=basic_auth_string)

      total_count_response = http.request('GET', total_count_url, headers = headers)

      total_count_data = json.loads(total_count_response.data)

      total_count = total_count_data["response_map"]["total"]

      total_metric_string = 'snaplogic.runtime.{state}'.format(state = state.lower())

      self.gauge(name=total_metric_string, value=total_count, tags=["orgname={orgname}".format(orgname=orgname)])