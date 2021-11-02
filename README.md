# datadog-snaplogic

A quick Proof-of-concept to take metrics from the snaplex API:

https://docs-snaplogic.atlassian.net/wiki/spaces/SD/pages/1438923/Snaplex+Monitoring+APIs

Example response from API:

```json
{
    "http_status_code": 200,
    "response_map": {
        "/Snaplogic/shared/Test Cloud": {
            "cc_info": {
                "container_type": "mixed",
                "down": [],
                "running": [
                    {},
                    {}
                ],
            },
            "plex_info": {}
        },
        "/snaplogic/shared/Test Groundplex": {
            "cc_info": {
                "container_type": null,
                "down": [],
                "running": [],
            },
            "plex_info": {}
        }
    }
}
```

## Running a test

```shell
sudo -u dd-agent -- dd-agent check snaplogic
2021-10-12 08:57:31,915 | WARNING | dd.collector | utils.hostname(hostname.py:35) | Hostname: .custom_check is not complying with RFC 1123
2021-10-12 08:57:31,927 | INFO | dd.collector | utils.dockerutil(dockerutil.py:145) | Docker features disabled: No running Docker instance detected. Will not retry since no docker_daemon configuration file was found.
2021-10-12 08:57:31,956 | INFO | dd.collector | utils.cloud_metadata(cloud_metadata.py:275) | Attempting to get OpenStack meta_data.json
2021-10-12 08:57:31,959 | INFO | dd.collector | utils.cloud_metadata(cloud_metadata.py:295) | Could not load meta_data.json, not OpenStack EC2 instance
2021-10-12 08:57:31,960 | INFO | dd.collector | config(config.py:1012) | no bundled checks.d path (checks provided as wheels): /opt/datadog-agent/agent/checks.d
2021-10-12 08:57:32,750 | INFO | dd.collector | config(config.py:1288) | initialized checks.d checks: ['ntp', 'disk', 'network', 'snaplogic']
2021-10-12 08:57:32,751 | INFO | dd.collector | config(config.py:1289) | initialization failed checks.d checks: []
2021-10-12 08:57:32,752 | INFO | dd.collector | checks.collector(collector.py:583) | Running check snaplogic
/opt/datadog-agent/embedded/lib/python2.7/site-packages/urllib3/connectionpool.py:847: InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
  InsecureRequestWarning)
Metrics:
[('snaplogic.disk_free',
  1634029055,
  81.89045333862305,
  {'hostname': 'i-0fc5jkwona097ed1',
   'tags': ('project:foo-bar-baz', 'snaplogic_hostname:e-qux-quz'),
   'type': 'gauge'}),
Events:
[]
Service Checks:
[]
Service Metadata:
[{}]
    snaplogic (5.32.8)
    ------------------
      - instance #0 [OK]
      - Collected 1 metrics, 0 events & 0 service checks


Check has run only once, if some metrics are missing you can run the command again with the 'check_rate' argument appended at the end to see any other metrics if available.
```