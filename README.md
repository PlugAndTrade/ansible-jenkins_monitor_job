# ansible-jenkins_monitor_job
An ansible module for creating and monitoring progress of a jenkins job.

## Installation
Clone the repository to a location of your choosing. In order for the module to be found the destination folder
needs to be included in the `ANSIBLE_LIBRARY`, be set in the `/etc/ansible/ansible.cfg` (global).

If using this module as a git submodule in a project it is required that the project has a local `ansible.cfg` file
with the path to your local library set in the `library` paramater.
Clone into project library:
```bash
git clone https://github.com/PlugAndTrade/ansible-jenkins_monitor_job.git /path/to/project/library/ansible-jenkins_monitor_job
```
Set library path in `ansible.cfg`
```yml
[defaults]
library = /usr/share/ansible:library
```

Here we add library to the path. Which make it possible for ansible to detect subdirectories within the library directory.
If copying just `jenkins_monitor_job.py` in to the `library` directory, then there's no need for an `ansible.cfg` file, it will be picked up automatically.

## usage

This module operates in two modes creating and wating for the job to be start, and monitoring the progress of the job.
When a job is created from this module the `cause` parameter for the jngob is set to an `uuid` in order to uniquely identify the job.
This is required since a creating a job does not guarentee that it will be started right away. So no job id is returned. In fact the job id
is only set once the job has begun executing. After the job has is started the job id will be used to monitor progress.

A successfull result is determined by the result of the jenkins job. A failed jenkins job will set the module result as failure,
success is success and so on.

### Examples

Start a job called `myjob` and wait for it to finish.

```yml
jenkins_monitor_job:
  url: http://localhost:8080 # jenkins url
  name: myjob # jobname
  user: myuser # uesrname
  password: myreallylongpasswordtoken # password, can be found in user settings
  state: finished # We wait for the job to finish
  crumb: yes # CSRF is enabled on jenkins
  token: abcdefghij # job token, can be found in the job configuration
```


Note that the `state` parameter was set to finish. We can if we like just start a job
and not care about the result by setting `state: present`.

To monitor an already started or finished job. I.e more or less query jenkins for a result on a job.
```yml
jenkins_monitor_job:
  url: http://localhost:8080
  name: myjob
  job_id: 1
  user: myuser
  password: myreallylongpasswordtoken # password, can be found in user settings
  state: finished
  crumb: yes
  token: abcdefghij
```

Create a job with parameters

```yml
jenkins_monitor_job:
  url: http://localhost:8080
  name: myjob
  user: myuser
  password: myreallylongpasswordtoken # password, can be found in user settings
  state: finished
  crumb: yes
  token: abcdefghij
  parameters:
    - { name: 'MYPARAMETER', value: 'value' }
```

parameters is a list with the parameter name as `name` and
value as `value`.

### Result format
TODO
