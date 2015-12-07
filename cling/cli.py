# -*- coding: utf-8 -*-

import re
import sys
import time
import logging
from . import pexpect_ng as pexpect

from . import Error

__all__ = ['Cling']

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())

# attempt to load netsnmp Python bindings,
# this enables usage of personality auto discovery
try:
    import netsnmp
except ImportError:
    netsnmp = None

# PERSONALITIES define:
#    - prompt to expect
#    - list of the init commands to run upon login
#    - list of the exit commands to run upon logout
#    - pattern to match when using snmp for persn. auto discovery
PERSONALITIES = {
    'generic': {},

    'ios': {
        'init': ['terminal length 0'],
        'exit': ['exit'],
        'sys_descr': r'cisco ios (?! xr )'
    },

    'iosxr': {
        'init': ['terminal length 0'],
        'exit': ['exit'],
        'sys_descr': r'cisco ios xr'
    },

    'eos': {
        'init': ['terminal length 0'],
        'exit': ['exit'],
        'sys_descr': r'arista'
    },

    'ironware': {
        'init': ['skip-page-display'],
        'exit': ['exit', 'exit'],
        'sys_descr': r'brocade|foundry'
    },

    'junos': {
        'init': [
            'set cli complete-on-space off',
            'set cli screen-length 0',
            'set cli screen-width 0'
        ],
        'exit': ['exit'],
        'sys_descr': r'junos'
    },

    'webos': {
        'init': ['lines 0', 'verbose 1'],
        'exit': ['exit', 'n'],
        'sys_descr': r'alteon'
    },

    'acos': {
        'init': ['terminal length 0'],
        'exit': ['exit', 'exit', 'y'],
        'sys_descr': r'acos'
    },

    'netscaler': {
        'exit': ['exit'],
        'sys_descr': r'netscaler'
    },

    'tmos': {
        'init': ['tmsh', 'modify cli preference pager disabled'],
        'exit': ['quit', 'exit'],
        'sys_descr': r'\.f5'
    },

    'panos': {
        'init': ['set cli pager off'],
        'exit': ['exit'],
        'sys_descr': 'palo alto'
    },
}


class Cling(object):
    def __init__(self,
                 hostname=None,
                 personality='generic',
                 username='',
                 password='',
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
                 simulation=False):

        self.hostname = hostname
        self.username = username
        self.password = password
        self.personality = personality
        self.pexpect_timeout = pexpect_timeout
        self.pexpect_read_loop_timeout = pexpect_read_loop_timeout
        self.pexpect_maxread = pexpect_maxread
        self.pexpect_searchwindowsize = pexpect_searchwindowsize
        self.snmp_community = snmp_community
        self.snmp_version = snmp_version
        self.error_lookup_buffer = error_lookup_buffer  # Error lookup buffer
        self.max_login_attempts = max_login_attempts
        self.failed_login_retry_pause = failed_login_retry_pause
        self.pub_key_auth = pub_key_auth
        self.identity_path = identity_path
        self.extra_ssh_params = extra_ssh_params
        self.ssh_path = ssh_path
        self.simulation = simulation
        self.output_divider = '------------------\n'

        # Pexpect child object, initialised on login
        self.child = None

        # snmp personality auto discovery
        if self.personality == 'snmp':
            if netsnmp:
                self._snmp_discover_personality()
            else:
                raise Error('%s: Failed to load netsnmp' % self.hostname)

        # bail if the personality is not known
        if self.personality not in PERSONALITIES:
            raise Error('%s: Unknown personality %s' % (
                self.hostname, self.personality))

        # Spawn a device specific error handler
        self._error_handler = self._make_error_handler(self.personality)

        # set default personality traits
        prompt = r'[#>\$%] ?$'
        self.init_commands = []
        self.exit_commands = []

        # override default traits with specifics
        if 'prompt' in PERSONALITIES[self.personality]:
            prompt = PERSONALITIES[self.personality]['prompt']
        if 'init' in PERSONALITIES[self.personality]:
            self.init_commands = PERSONALITIES[self.personality]['init']
        if 'exit' in PERSONALITIES[self.personality]:
            self.exit_commands = PERSONALITIES[self.personality]['exit']

        # compile case insensitive prompt to use with pexpect
        self.prompt = re.compile(prompt, flags=re.I)

        # at this point we're ready for login()

    def send(self, s='', hide_text=False):
        '''Sends string to the child, does not wait for cli prompt
        to be returned, raises Error if child has terminated'''

        if not hide_text:
            LOG.debug('%s: Sending: %s' % (self.hostname, s.rstrip()))
        else:
            LOG.debug('%s: Sending: ***hidden***' % self.hostname)

        try:
            self.child.send(s)
        except pexpect.EOF:
            raise Error('%s: child terminated [%s]' % (
                self.hostname, self.child.before.rstrip()))

    def send_line(self, s='', hide_text=False):
        '''Sends string + lineseparator to child, does not wait for cli prompt
        to be returned '''

        if not hide_text:
            LOG.debug('%s: Sending: %s' % (self.hostname, s))
        else:
            LOG.debug('%s: Sending: ***hidden***' % self.hostname)

        try:
            self.child.sendline(s)
        except pexpect.EOF:
            raise Error('%s: child terminated [%s]' % (
                self.hostname, self.child.before.rstrip()))

    def _sleep_meta_command(self, command):
        '''Catch a sleep magic tag line '''

        m = re.search(r'^<sleep (\d+)>$', command, flags=re.I)
        if m:
            seconds = m.group(1)
            LOG.debug(
                '%s: <sleeping for %s seconds>' % (self.hostname, seconds))
            time.sleep(int(seconds))
            return True
        return False

    def run_command(self, command, force_execute=False):
        '''Command executor abstraction

        force_execute, bypasses the simulation mode if set to true and is
        shortcut for:

        ch.simulation = False
        ch.run_command('I command you')
        ch.simulation = True
        '''

        # real config mode / force execute mode
        if force_execute or not self.simulation:
            output = self._run_command(command)
            return output
        # simulation mode
        elif self.simulation:

            # Catch a sleep statement
            if self._sleep_meta_command(command):
                return ''
            LOG.debug('%s: Simulation-send: "%s"' % (self.hostname, command))
            output = ''
            return output

    def _run_command(self, command, ignore_err=False):
        '''Sends a command + newline to child, waits for cli prompt to be matched
        and returns output buffer minus the echoed command and cli prompt'''

        # Catch <sleep > magic tags
        if self._sleep_meta_command(command):
            return ''

        # <send>command will send command without newline
        m = re.search(r'^<send>(.+)$', command, flags=re.I)
        if m:
            command = m.group(1)
            LOG.debug('%s: Send: "%s"' % (self.hostname, command))
            try:
                self.send(command)
            except Error as e:
                raise Error(str(e))
            return ''

        # <force_exec>command will bypass the simulation mode
        m = re.search(r'^<force_exec>(.+)$', command, flags=re.I)
        if m:
            command = m.group(1)
            LOG.debug('%s: Forcing exec of: "%s"' % (self.hostname, command))
            return self._run_command(command)

        # <ignore_err>command will bypass the error checking
        m = re.search(r'^<ignore_err>(.+)$', command, flags=re.I)
        if m:
            command = m.group(1)
            LOG.debug('%s: Ignoring possible errors on command: "%s"' % (
                self.hostname, command))
            return self._run_command(command, ignore_err=True)

        # <send_line>command will send command
        m = re.search(r'^<send_line>(.+)$', command, flags=re.I)
        if m:
            command = m.group(1)

            LOG.debug('%s: Send: "%s"' % (self.hostname, command))

            try:
                self.send_line(command)
            except Error as e:
                raise Error(str(e))
            return ''

        # normal command execution
        self.send_line(command)
        self._expect(self.prompt)

        out = self.child.before
        if not ignore_err:
            self._catch_error(out)

        # for 'tmos' personality remove all <symbol><backspace> pairs
        # from the output, f5 inserts those when echoing command back
        if self.personality == 'tmos':
            out = re.sub(r'.%s' % chr(8), '', out)

        # attempt to remove echo-ed back command
        # .*? after command is needed as some devices
        # append the command with spaces for some reason
        out = re.sub(r'%s.*?\r\n' % re.escape(command), '', out)

        # attempt to remove last string (cli prompt)
        out = re.sub('[^\n]*?$', '', out)
        return out

    def _catch_error(self, out=None):
        '''Error catcher'''

        # Get the last self.error_lookup_buffer characters from the response buffer and
        # check if there is an error message in the response.
        # If so raise Exeption
        sample_out = out[-self.error_lookup_buffer:]
        LOG.debug(
            '%s: Looking for errors in %s' % (self.hostname, sample_out))
        if self._error_handler.has_error(sample_out):
            LOG.debug('%s: Oops... error condition met; %s' % (
                self.hostname, sample_out))
            raise Error('%s: Command error: %s' % (self.hostname, sample_out))
        return

    def login(self):
        for attempt in range(0, self.max_login_attempts):
            try:
                LOG.debug('%s: Attempt %s: Login to %s...' %
                          (self.hostname, attempt, self.hostname))
                self._dologin()
                LOG.debug('%s: Done logging-in to %s' % (
                    self.hostname, self.hostname))
                return
            except Error as e:
                if attempt >= self.max_login_attempts - 1:
                    LOG.debug(
                        '%s: All connection attempts to %s failed.' % (
                            self.hostname, self.hostname))
                    raise Error(str(e))
                else:
                    LOG.debug(
                        '%s: connection to %s failed, %i attempt(s) left'
                        % (
                            self.hostname,
                            self.hostname,
                            self.max_login_attempts - 1 - attempt
                        )
                    )
                    time.sleep(self.failed_login_retry_pause)

    def _dologin(self):
        '''Spawns ssh or telnet, logins to the host
        and runs the intialisation commands'''

        # build the ssh command to spawn
        ssh_command = [self.ssh_path]

        ssh_command.append('-o UserKnownHostsFile=/dev/null')
        ssh_command.append('-o StrictHostKeyChecking=no')

        pref_auth_str = ('-o PreferredAuthentications=password,'
                         'keyboard-interactive')
        if self.pub_key_auth:
            pref_auth_str += ',publickey'
        ssh_command.append(pref_auth_str)

        if self.pub_key_auth and self.identity_path:
            ssh_command.append('-i %s' % self.identity_path)

        ssh_command.append('%s@%s' % (self.username, self.hostname))

        if self.extra_ssh_params:
            ssh_command.append(self.extra_ssh_params)

        ssh_command = ' '.join(ssh_command)

        # spawn the process
        self.child = self._spawn(ssh_command)

        # if pub_key_auth is True, then we ignore the password prompt
        if not self.pub_key_auth:
            p = re.compile(r'password: ', re.I)

            try:
                self._expect(p)
            # raise "connection failed" if no "password" could be seen
            except Error as e:
                raise Error(
                    '%s: connection failed (%s)' % (self.hostname, e))

            try:
                self.send_line(self.password, hide_text=True)
                self._expect(self.prompt)
            # raise login failed if no cli prompt could be seen
            except Error as e:
                raise Error('%s: login failed (%s)' % (self.hostname, e))
        else:
            try:
                self._expect(self.prompt)
            except Error as e:
                raise Error('%s: login failed (%s)' % (self.hostname, e))

        # Set search window size - how many chars to look back for a matching prompt
        self.child.searchwindowsize = self.pexpect_searchwindowsize

        # run the init commands
        for s in self.init_commands:
            self.run_command(s)

    def logout(self):
        '''Sends  the exit commands to the terminal
        and closes the spawned process'''
        try:
            for s in self.exit_commands:
                self.send_line(s)
        except (pexpect.TIMEOUT, pexpect.EOF):
            pass

        try:
            self.child.close()
        except:
            pass

    def _spawn(self, command):
        '''Spawns the shell command and returns pexpect child object'''
        LOG.debug('%s: spawning "%s"' % (self.hostname, command))
        try:
            child = pexpect.spawn(
                command,
                maxread=self.pexpect_maxread,
                timeout=self.pexpect_timeout,
                read_loop_timeout=self.pexpect_read_loop_timeout
            )
            return child
        except pexpect.EOF:
            raise Error('%s: child terminated "%s"' % (
                self.hostname, self.child.before))

    def _expect(self, pattern):
        '''Waits for the pattern to be matched in the input stream
        If no match has occured raises "timeout pattern matching" error
        If child process dies raises "child terminated" error'''
        LOG.debug('%s: expecting %s' % (self.hostname, pattern.pattern))
        try:
            self.child.expect(pattern)
            LOG.debug(
                '%s: Before: "%s"' % (self.hostname, self.child.before))
            LOG.debug('%s: After: "%s"' % (self.hostname, self.child.after))
        except pexpect.TIMEOUT:
            raise Error(
                '%s: timeout pattern matching, search buffer was "%s"' % (
                    self.hostname, self.child.before)
            )
            # clean up and terminate
            self.logout()
        except pexpect.EOF:
            raise Error('%s: child terminated "%s"' % (self.hostname,
                                                       self.child.before.rstrip()))

    def _snmp_discover_personality(self):
        '''Loads netsnmp mod and attempts to discover the host's personality
        via snmp by querying sysDescr'''
        varbind = netsnmp.snmpget(
            netsnmp.Varbind('.1.3.6.1.2.1.1.1.0'),
            DestHost=self.hostname,
            Version=self.snmp_version,
            Community=self.snmp_community,
        )

        if varbind[0] is None:
            raise Error('%s: SNMP query failed' % self.hostname)

        sys_descr = varbind[0]

        for personality in PERSONALITIES:
            # skip generic personality
            if personality == 'generic':
                continue

            if re.search(
                    PERSONALITIES[personality]['sys_descr'], sys_descr,
                    flags=re.I
            ):
                self.personality = personality
                break
        else:
            raise Error(
                '%s: Unable to determine personality of "%s"' % (
                    self.hostname, sys_descr))

    def _run_command_ascii(self, command):
        '''Runs a command, prints the output buffer per byte and
        it's corresponding ascii code'''
        self.send_line(command)
        self._expect(self.prompt)
        for c in self.child.before:
            sys.stdout.write('%s <=> %i\n' % (c, ord(c)))

    def ts_line_login(self, line_name):
        '''Experimental terminal server handling'''
        self.send_line(line_name)
        p = re.compile(r'username: ', flags=re.I)
        self._expect(p)
        self.send_line(self.username)
        p = re.compile(r'password: ', flags=re.I)
        self._expect(p)
        self.send_line(self.password)
        # send extra '\r'
        self.send_line()

    def ts_line_logout(self):
        '''Experiemental terminal server handling '''
        self.send(chr(30) + 'x')
        self.send_line('disconnect')
        self.send_line()

    def _make_error_handler(self, personality):
        """
        Create an error handler.

        Spawn a device specific error handler to ease error handling. If a device
        handler is not available the default is selected - no error handling.
        """

        # Attempt to import error handler class. All device handlers are
        # in "error_handler.<devicename>" and in a class named
        # "<PERSONALITY>ErrorHAndler", with the first letter capitalized.
        class_name = "%sErrorHandler" % personality.capitalize()
        module_name = "cling.error_handler.%s" % personality
        try:
            dev_module_obj = __import__(module_name)
        except ImportError:
            class_name = "DefaultErrorHandler"
            module_name = "cling.error_handler.default"
            personality = 'default'
            dev_module_obj = __import__(module_name)
        handler_module_obj = getattr(
            getattr(dev_module_obj, "error_handler"), personality)
        class_obj = getattr(handler_module_obj, class_name)
        handler_obj = class_obj(personality)
        LOG.debug('%s: Invoking %s error handler' % (
            self.hostname, personality))
        return handler_obj
