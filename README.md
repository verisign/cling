<p align="center">
  <img src="misc/logo.png"/>
</p>
<p align="center">Embrace Automation
</p>

## Cling

In the age of APIs and emerging SDN... CLI screen-scrapping remains the primary method for interacting with heterogeneous network infrastructures. 

Cling(**CLI** **n**ext **g**en) is a Python module for automating network device command line interface interaction.

## Dependencies

- [optional] Net-SNMP (with Python bindings)  http://www.net-snmp.org/

## Installation
git clone from github and:

```sudo python setup.py install```

or via PIP

```pip install cling```

## Synopsis
```python
import cling

try:
    ch = cling.Cling(hostname='router1.example.com',
                     personality='ios',
                     username='admin',
                     password='secret')
    ch.login()
    print ch.run_command('show version')
    ch.logout()
except cling.Error as e:
    print e
```
- This will:
    - spawn ssh command
    - login to router1.example.com
    - run a set of initialisation commands such as switch off paging(depending on the host's personality)
    * run "show version" command and print it's output
    * Logout from the device by running exit commands(personality dependent) and killing the spawned ssh process
    * Error message is printed if an error occurs

## API

```python
Cling(hostname=None,
      personality='generic',
      username=None,
      password=None,
      pexpect_timeout=10,
      pexpect_read_loop_timeout=0.1,
      snmp_community='public',
      snmp_version=2,
      pexpect_maxread=64000,
      pexpect_searchwindowsize=5,
      error_lookup_buffer=100,
      max_login_attempts=2,
      failed_login_retry_pause=3,
      pub_key_auth=False,
      identity_path=None,
      extra_ssh_params='',
      ssh_path='/usr/bin/ssh',
      simulation=False)
```

- `hostname` hostname or IP address to connect to
- `personality` device's personality we're connecting to, this sets a prompt to expect, initialisation commands to run upon login, such as switching off screen paging and exit commands to run upon logout
    - Personalities supported:
        - `generic`       Generic personality (does not run init or exit commands)
        - `ios`           Cisco IOS
        - `iosxe`         Cisco IOS XE
        - `iosxr`         Cisco IOS XR
        - `eos`           Arista switches
        - `ironware`      Brocade routers, switches and load balancers
        - `junos`         Juniper routers
        - `webos`         Radware Alteon
        - `acos`          A10 Networks ADX
        - `netscaler`     Citrix NetScaler ADX
        - `tmos`          F5 BIG-IP LTM/GTM
        - `panos`         PaloAlto PAN-OS
        - `cumulus`       Cumulus gear
        - `ftos`          Force 10
        - `checkpoint`    Checkpoint firewalls
        - `tripplite`     Tripplite terminal servers
        - `snmp`          attempt to automatically discover personality using snmp sysDescr, requires Net-SNMP Python bindings to be installed. After a successful detection `Cling.persnonality` is set to the detected personality

- `username` user name to use for login
- `password` password to use for login

- `pexpect_timeout` initial value of timeout in seconds, used when waiting for a pattern to be matched, i.e. when waiting for a prompt when logging in or executing a command. Increase if working with a slow connection or if a command takes a long time to output. The behaviour can be changed after a succesful login() by setting child.timeout variable, it can be increased on the fly when executing long-running commands, e.g. traceroute, and set back to the original value as needed.

- `pexpect_read_loop_timeout` when a command is issued (eg. ch.run_command('show running'), the response from the device (ie, the configuration) is read in chunks. The react_loop_timeout variable determines how often (in seconds) will the response buffer be polled for a new configuration chunk. Setting the value too low, eg. 0.0001 may result in configuration not being fetched - setting it to too high, eg. 5 may result in a pexpect_timeout reached. Default 0.1
In slow connections and **only** if problems occur, try to set it to something higher than 0.1, eg. 0.5 or 0.7 or even 1 (worst case).

- `snmp_community` community to use with `snmp` personality

- `snmp_version` snmp version to use with `snmp` personality

- `pexpect_maxread` readmax this much bytes at a time

- `pexpect_searchwindowsize` search for prompt in this many last bytes of the output

- `error_lookup_buffer` search for errors in this many last bytes of the output (default: 100)

- `max_login_attempts` login attempts after which the device is considered unreachable (default: 3)

- `pub_key_auth` set True to use public key authentication for ssh (default: False)

- `identity_path` path to private key to use with `pub_key_auth=True`, added as `-i <identity_path>` to the ssh command

- `extra_ssh_params` str added after username@hostname in the ssh command line

- `ssh_path` path to ssh binary

- `simulation` if set to True, commands are not applied to the device. An info-level logger eases logging (default: False)

### Methods

- `login()`

Spawns ssh logins to the host and runs the intialisation commands

- `run_command(command, force_execute=False)`

Sends a command + "line separator" to the child process, waits for cli prompt to be matched and returns output buffer minus the echoed command and the cli prompt
Error detection is carried on output buffer over the last `error_lookup_buffer` bytes (characters).

`force_execute` bypasses the simulation mode if set to true and is a shortcut for:

```python
ch.simulation = False
ch.run_command('I command you')
ch.simulation = True
```

- Magic command tags

The following "magic" command tags are supported:

- `<sleep X>`: Sleep for X seconds
- `<send>command`: will send command without line separator (eg. without \n)
- `<force_exec>command`: will execute the command regardless of the simulation state
- `<send_line>command`: will send command with line separator
- `<ignore_err>command`: bypasses error checking on command output
 
Example:
```python
# JunOS-based device
ch = cling.Cling(...,
                 simulation=True)
ch.login()
# Will not run the command
ch.run_command('edit private')
# Will run the command
ch.run_command('<force_exec>edit private')
ch.run_command('set hostname test.example.test')
ch.run_command('exit', force_exec=True)
ch.logout()
```

- `send(string)`

Sends string to the host, does not wait for the cli prompt to be matched

- `send_line(string)`

Sends string  + "line separator" to the host, does not wait for the cli prompt to be matched

- `logout()`

Runs exit commands (depending on personality selected) and kills the spawned process

### Reactor - running commands on multiple hosts

The reactor allows for execution of commands/configuration files on multiple hosts in parallel using the python multiprocessing module under the hood. The reactor is invoked in this way:

```python
import cling
reactor = cling.reactor.Reactor(tasks=hosts,
                                func=<applier_function>,
                                num_workers=2)
```                              
                              
"hosts" is a list of hostnames, eg.
```hosts = ['test1.example.com', 'test2.example.com']```

Applier function should apply configuration via cling. It should have a single param that indicates the device *hostname*. An example use case for the applier function is for parsing config files and apply the configuration to a device. So, in this example the applier should take care of log-in to a device, reading the config from file(s) applying it and exit. The reactor takes care of the rest, ie engaging the applier to multiple devices in a case where one would like to roll a new feature to many network devices.

`num_workers` is obvious, 1 means process the list of hosts in a serial manner. 2 or more implies parallel.


### Error handling
`cling.Error` is raised if an error has occurred, e.g connection has been closed by the remote host or timeout occurred waiting for a pattern to be matched. Under the error_handler directory there are device specific error detectors. Detectors act upon each command response and once certain patterns are matched (eg. "syntax error") the cling.Error exception is raised.

## pexpect_ng
*cling uses a modified version of pexpect 2.4, which is distributed under terms (looks like an MIT license) located in pexpect_ng.py*

pyexpect_ng is a modified version of pexpect 2.4. The main difference is in the way the response for the device is searched against matching prompt. 
Pexpect parses the device response and tries to match the prompt in expect() in every chunk of received data over the last *pexpect_searchwindowsize* characters. Pexpect_ng parses the whole response and then looks for a prompt over the last *pexpect_searchwindowsize* characters.
This saves the day in case prompt special chars (eg. #, >) are used in the output.

