import logging
import time
import uuid
import yaml

from juju_slayer.constraints import IMAGE_MAP, solve_constraints
from juju_slayer.exceptions import ConfigError, PrecheckError
from juju_slayer import ops
from juju_slayer.runner import Runner


log = logging.getLogger("juju.slayer")


class BaseCommand(object):

    def __init__(self, config, provider, environment):
        self.config = config
        self.provider = provider
        self.env = environment
        self.runner = Runner()

    def solve_constraints(self):
        params = solve_constraints(self.config.constraints)
        params['os_code'] = IMAGE_MAP[self.config.series]
        params['domain'] = self.config.domain
        params['hourly'] = True
        params['nic_speed'] = 100
        return params

    def get_slayer_ssh_keys(self):
        return [k.id for k in self.provider.get_ssh_keys()]

    def check_preconditions(self):
        """Check for provider ssh key, and configured environments.yaml.
        """
        keys = self.get_slayer_ssh_keys()
        if not keys:
            raise ConfigError(
                "SSH Public Key must be uploaded to softlayer")

        env_name = self.config.get_env_name()
        with open(self.config.get_env_conf()) as fh:
            conf = yaml.safe_load(fh.read())
            if not 'environments' in conf:
                raise ConfigError(
                    "Invalid environments.yaml, no 'environments' section")
            if not env_name in conf['environments']:
                raise ConfigError(
                    "Environment %r not in environments.yaml" % env_name)
            env = conf['environments'][env_name]
            if not env['type'] in ('null', 'manual'):
                raise ConfigError(
                    "Environment %r provider type is %r must be 'null'" % (
                        env_name, env['type']))
            if env['bootstrap-host']:
                raise ConfigError(
                    "Environment %r already has a bootstrap-host" % (
                        env_name))
        return keys


class Bootstrap(BaseCommand):
    """
    Actions:
    - Launch an instance
    - Wait for it to reach running state
    - Update environment in environments.yaml with bootstrap-host address.
    - Bootstrap juju environment

    Preconditions:
    - named environment found in environments.yaml
    - environment provider type is null
    - bootstrap-host must be null
    - at least one ssh key must exist.
    - ? existing softlayer with matching env name does not exist.
    """
    def run(self):
        keys = self.check_preconditions()
        params = self.solve_constraints()
        log.info("Launching bootstrap host")

        params['ssh_keys'] = keys
        params['hostname'] = '%s-0' % self.config.get_env_name()

        op = ops.MachineAdd(self.provider, self.env, params)
        instance = op.run()

        log.info("Bootstrapping environment")
        try:
            self.env.bootstrap_jenv(instance.ip_address)
        except:
            self.provider.terminate_instance(instance.id)
            raise

    def check_preconditions(self):
        result = super(Bootstrap, self).check_preconditions()
        if self.env.is_running():
            raise PrecheckError(
                "Environment %s is already bootstrapped" % (
                self.config.get_env_name()))
        return result


class AddMachine(BaseCommand):

    def run(self):
        keys = self.check_preconditions()
        params = self.solve_constraints()
        log.info("Launching %d instances", self.config.num_machines)

        params['ssh_keys'] = keys
        template = dict(params)

        for n in range(self.config.num_machines):
            params = dict(template)
            params['hostname'] = "%s-%s" % (
                self.config.get_env_name(), uuid.uuid4().hex)
            self.runner.queue_op(
                ops.MachineRegister(
                    self.provider, self.env, params,
                    series=self.config.series))

        for (instance, machine_id) in self.runner.iter_results():
            log.info("Registered id:%s name:%s ip:%s as juju machine",
                     instance.id, instance.name, instance.ip_address)


class TerminateMachine(BaseCommand):

    def run(self):
        """Terminate machine in environment.
        """
        self.check_preconditions()
        self._terminate_machines(lambda x: x in self.config.options.machines)

    def _terminate_machines(self, remove_machines):
        log.debug("Checking for machines to terminate")
        status = self.env.status()
        machines = status.get('machines', {})

        # Using the api instance-id can be the provider id, but
        # else it defaults to ip, and we have to disambiguate.
        remove = []
        for m in machines:
            if remove_machines(m):
                if machines[m].get('life', '') == 'dead':
                    continue
                remove.append(
                    # Juju does a reverse ip lookup to dns name which softlayer
                    # has mapped to 198.23.106.29-static.reverse.softlayer.com
                    # alternatively we need to query public ip address for each
                    # machine from dns.
                    {'address': machines[m]['dns-name'].split('-')[0],
                     'instance_id': machines[m]['instance-id'],
                     'machine_id': m})

        address_map = dict([(d.ip_address, d.id) for
                            d in self.provider.get_instances()])
        if not remove:
            return status, address_map

        log.info("Terminating machines %s",
                 " ".join([m['machine_id'] for m in remove]))

        for m in remove:
            instance_id = address_map.get(m['address'])
            if instance_id is None:
                log.warning(
                    "Couldn't resolve machine %s's address %s to instance" % (
                        m['machine_id'], m['address']))
                continue
            self.runner.queue_op(
                ops.MachineDestroy(
                    self.provider, self.env, {
                        'machine_id': m['machine_id'],
                        'instance_id': instance_id}))
        for result in self.runner.iter_results():
            pass

        return status, address_map


class DestroyEnvironment(TerminateMachine):

    def run(self):
        """Destroy environment.
        """
        self.check_preconditions()

        # Manual provider needs machines removed prior to env destroy.
        def state_service_filter(m):
            if m == "0":
                return False
            return True

        env_status, instance_map = self._terminate_machines(
            state_service_filter)

        # sadness, machines are marked dead, but juju is async to
        # reality. either sleep (racy) or retry loop, 10s seems to
        # plenty of time.

        # Update: We forcefuly terminate the environment anyways.
        time.sleep(2)
        log.info("Destroying environment")
        self.env.destroy_environment()

        # Remove the state server.
        bootstrap_host = env_status.get(
            'machines', {}).get('0', {}).get('dns-name').split('-')[0]
        instance_id = instance_map.get(bootstrap_host)
        if instance_id:
            log.info("Terminating state server")
            self.provider.terminate_instance(instance_id)
