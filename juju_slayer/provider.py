import logging
import os
import time
import itertools

from juju_slayer.exceptions import ConfigError, ProviderError
from SoftLayer import Client, SshKeyManager, CCIManager, config as client_conf

log = logging.getLogger("juju.slayer")


def factory():
    cfg = SoftLayer.get_config()
    return SoftLayer(cfg)


def validate():
    SoftLayer.get_config()


class SSHKey(dict):
    __slots__ = ()

    @property
    def id(self):
        return self['id']

    @property
    def name(self):
        return self['label']


class Instance(dict):
    __slots__ = ()

    @property
    def id(self):
        return self['id']

    @property
    def cpus(self):
        return self['maxCpu']

    @property
    def memory(self):
        return self['maxMemory']

    @property
    def name(self):
        return self['hostname']

    @property
    def status(self):
        return self['powerState']['name']

    @property
    def ip_address(self):
        return self.get('primaryIpAddress', '')


class SoftLayer(object):

    def __init__(self, config, client=None):
        self.config = config
        if client is None:
            client = Client(
                auth=self.config['auth'],
                endpoint_url=self.config['endpoint_url'])
        self.client = client
        self.ssh = SshKeyManager(client)
        self.instances = CCIManager(client)

    @classmethod
    def get_config(cls):
        provider_conf = client_conf.get_client_settings()
        if 'SL_SSH_KEY' in os.environ:
            provider_conf['ssh_key'] = os.environ['SL_SSH_KEY']
        if not ('auth' in provider_conf and 'endpoint_url' in provider_conf):
            raise ConfigError("Missing digital ocean api credentials")
        return provider_conf

    def get_ssh_keys(self):
        keys = map(SSHKey, self.ssh.list_keys())
        if 'ssh_key' in self.config:
            keys = [k for k in keys if k.name == self.config['ssh_key']]
        log.debug(
            "Using SoftLayer ssh keys: %s" % ", ".join(k.name for k in keys))
        return keys

    def get_instances(self):
        return map(Instance, self.instances.list_instances())

    def get_instance(self, instance_id):
        return Instance(self.instances.get_instance(instance_id))

    def launch_instance(self, params):
        return Instance(self.instances.create_instance(**params))

    def terminate_instance(self, instance_id):
        self.instances.cancel_instance(instance_id)

    def wait_on(self, instance):
        # Wait up to 5 minutes, in 30 sec increments
        result = self._wait_on_instance(instance, 30, 10)
        if not result:
            raise ProviderError("Could not provision instance before timeout")
        return result

    def _wait_on_instance(self, instance, limit, delay=10):
        # Redo cci.wait to give user feedback in verbose mode.
        for count, new_instance in enumerate(itertools.repeat(instance.id)):
            instance = self.get_instance(new_instance)
            if not instance.get('activeTransaction', {}).get('id') and \
               instance.get('provisionDate'):
                return True
            if count >= limit:
                return False
            if count and count % 3 == 0:
                log.debug("Waiting for instance:%s ip:%s waited:%ds" % (
                    instance.name, instance.ip_address, count*delay))
            time.sleep(delay)
