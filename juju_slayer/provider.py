import logging
import os
import time

from juju_slayer.exceptions import ConfigError, ProviderError
from SoftLayer import Client, SshManager, CCIManager, config as client_conf

log = logging.getLogger("juju.slayer")


def factory():
    cfg = SoftLayer.get_config()
    return SoftLayer(cfg)


def validate():
    SoftLayer.get_config()


class SSHKey(dict):
    __slots__ = ()


class Instance(dict):
    __slots__ = ()


class SoftLayer(object):

    def __init__(self, config, client=None):
        self.config = config
        if client is None:
            client = Client(
                auth=self.config['auth'],
                endpoint_url=self.config['endpoint_url'])
        self.client = client
        self.ssh = SshManager(client)
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
        keys = self.ssh.list_keys()
        if 'ssh_key' in self.config:
            keys = [k for k in keys if k['label'] == self.config['ssh_key']]
        log.debug(
            "Using SL ssh keys: %s" % ", ".join(k['label'] for k in keys))
        return keys

    def get_instances(self):
        return self.instances.list_instances()

    def get_instance(self, instance_id):
        return self.client.get_instance(instance_id)

    def launch_instance(self, params):
        raise NotImplementedError()
        if not 'virtio' in params:
            params['virtio'] = True
        if not 'private_networking' in params:
            params['private_networking'] = True
        if 'ssh_key_ids' in params:
            params['ssh_key_ids'] = map(str, params['ssh_key_ids'])
        return self.client.create_droplet(**params)

    def terminate_instance(self, instance_id):
        self.client.cancel_instance(instance_id)

    def wait_on(self, instance):
        return self._wait_on(instance.event_id, instance.name)

    def _wait_on(self, event, name, event_type=1):
        loop_count = 0
        while 1:
            time.sleep(8)  # Takes on average 1m for a do instance.
            result = self.client.request("/events/%s" % event)
            event_data = result['event']
            if not event_data['event_type_id'] == event_type:
                raise ValueError(
                    "Waiting on invalid event type: %d for %s",
                    event_data['event_type_id'], name)
            elif event_data['action_status'] == 'done':
                log.debug("Instance %s ready", name)
                return
            elif result['status'] != "OK":
                log.warning("Unknown provider error %s", result)
            else:
                log.debug("Waiting on instance %s %s%%",
                          name, event_data.get('percentage') or '0')
            if loop_count > 8:
                # Its taking a long while (2m+), give the user some
                # diagnostics if in debug mode.
                log.debug("Diagnostics on instance %s event %s",
                          name, result)
            if loop_count > 25:
                # After 3.5m for instance, just bail as provider error.
                raise ProviderError(
                    "Failed to get running instance %s event: %s" % (
                        name, result))
            loop_count += 1
