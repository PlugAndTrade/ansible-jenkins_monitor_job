#!/usr/bin/python

import base64
import requests
import uuid
import time

from itertools import chain
from functools import reduce
from ansible.module_utils.basic import *

DOCUMENTATION = """"""
RETURN = """"""

# Jenkins REST Endpoints
CRUMB_API = '/crumbIssuer/api/json'
BUILD_WITH_PARAMETERS_API = '/job/{name}/buildWithParameters'
ALL_BUILD_INFO = '/job/{name}/api/json?tree=builds[id,building,result,estimatedDuration,actions[causes[note]]]'
BUILD_INFO = '/job/{name}/{id}/api/json'


def auth_header(user, password):
    auth = base64.b64encode('{0}:{1}'.format(user, password))

    return {'Authorization': 'Basic {}'.format(auth)}


def prepare_params(params):
    if params is None:
        return {}

    return reduce(
        lambda acc, param:
        dict([(param['name'], param['value'])], **acc), params, {}
    )


def pick_from(current, keys={}):
    return {key: current[key] for key in keys}


class Jenkins(object):
    """
    Helper jenkins client to consume the job REST endpoints.
    """
    def __init__(self, module, **kwargs):
        self._module = module
        self._url = kwargs['url']
        self._user = kwargs['user']
        self._pass = kwargs['password']
        self._name = kwargs['name']
        self._token = kwargs['token']
        self._crumb_info = self.get_crumb_info()

    def _build_url(self, api, **kwargs):
        """
        """
        return self._url + api.format(**kwargs)

    def get_crumb_info(self):
        """
        Fetches crumb request header & value.
        If the request fails, we fail module execution
        """
        url = self._build_url(CRUMB_API)
        result = requests.get(url, headers=auth_header(self._user, self._pass))

        if result.status_code != 200:
            self._module.fail_json(msg=result.text)

        return result.json()

    def start_job(self, parameters=None):
        """
        Starts a jenkins job by calling the buildWithParameters endpoint.
        In order to properly monitor the job execution the cause message
        is set to an UUID.
        The UUID is returned together with the headers on success.
        """
        url = self._build_url(BUILD_WITH_PARAMETERS_API, name=self._name)
        job_uniq_id = str(uuid.uuid1())
        params = dict(
            {'token': self._token, 'cause': job_uniq_id},
            **prepare_params(parameters)
        )
        headers = dict([
                ('Content-Type', 'application-x-www-form-urlencoded'),
                (self._crumb_info['crumbRequestField'].encode('utf-8'), self._crumb_info['crumb'].encode('utf-8'))
            ], **auth_header(self._user, self._pass))

        result = requests.post(url, headers=headers, params=params)

        if result.status_code != 201:
            self._module.fail_json(msg=result.text)

        return (job_uniq_id, result.headers)

    def _find_id(self, build, job_id):
        """
        Search the provided build dict actions for a cause which includes a note equal to our custom job id.
        """
        actions = filter(lambda action: 'causes' in action, build['actions'])

        if len(actions) == 0:
            return False

        causes = list(chain.from_iterable(map(lambda action: action['causes'], actions)))

        return len(list(filter(lambda cause: 'note' in cause and cause['note'] == job_id, causes))) > 0

    def _search_jobs(self, job_id):
        """
        Fetches all build and tries to find the build which is to be monitored.
        This can take some time if the job is queued but not yet started.
        """
        url = self._build_url(ALL_BUILD_INFO, name=self._name)
        headers = auth_header(self._user, self._pass)

        builds = requests.get(url, headers=headers)
        # Should we fail on failed requests or note?
        if builds.status_code != 200:
            return False, False, None

        build = list(filter(lambda build: self._find_id(build, job_id), builds.json()['builds']))
        found = len(build) > 0

        return found, found, next(iter(build), None)

    def _monitor_job(self, job_id):
        """
        """
        url = self._build_url(BUILD_INFO, name=self._name, id=job_id)
        headers = auth_header(self._user, self._pass)

        req = requests.get(url, headers=headers)

        try:
            build = req.json()
        except ValueError:
            build = dict(result=None)

        if req.status_code != 200 or build['result'] == None:
            return False, False, None

        return True, build['result'].lower() == 'success', build

    def monitor(self, job_unique_id, seconds_between_retries=5, retry_time=70, func_name='_search_jobs'):
        """
        Monitors the job until the provided func returns that it is found, or that it is timed out.
        If a request to start a job has been sent, the func should be `_search_jobs`.
        As the build to monitor has not been found yet. If wanting to monitored a started job.
        I.e the id provided is assigned by jenkins it should be called with `_monitor_job`.
        """
        func = getattr(self, func_name)

        for _ in range(int(retry_time / seconds_between_retries)):
            found, success, job = func(job_unique_id)

            if found:
                break

            time.sleep(seconds_between_retries)

        if not found:
            self._module.fail_json(msg='Could not find the Jenkins job to monitor')

        if func_name == '_monitor_job':
            return success, job

        return self.monitor(
            job['id'],
            int(job['estimatedDuration'] / 4000),
            int(job['estimatedDuration'] / 1000) * 4,
            '_monitor_job'
            )


def main():
    module = AnsibleModule(argument_spec=dict(
        url        = dict(required=True, type='str'),
        user       = dict(required=True, type='str'),
        password   = dict(required=True, type='str'),
        crumb      = dict(required=False, type='bool', default=True),
        token      = dict(required=True, type='str'),
        job_id     = dict(required=False, type='str', default=None),
        name       = dict(required=True, type='str'),
        parameters = dict(required=False, type='list', default=None),
        state      = dict(default='present', choices=['present', 'finished'], type='str')
    ))

    state = module.params['state']
    id = module.params.get('job_id')
    parameters = module.params['parameters']

    jenkins = Jenkins(module, **module.params)
    job_id, result = (jenkins.start_job(parameters=parameters)
                      if not id
                      else (id, {})
                      )

    if state == 'present':
        module.exit_json(changed=False, meta=result)
    elif state == 'finished':
        func = '_monitor_job' if id else '_search_jobs'
        success, build = jenkins.monitor(job_id, func_name=func)

        if not success:
            msg = 'Jenkins build #{} failed. Full build name: {}' . format(build['id'], build['fullDisplayName'])
            return module.fail_json(msg=msg)

        module.exit_json(changed=False, **build)


if __name__ == '__main__':
    main()
