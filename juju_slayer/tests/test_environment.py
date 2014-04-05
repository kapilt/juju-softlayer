
import mock
import os
import yaml

from juju_slayer.env import Environment

from juju_slayer.tests.base import Base


class EnvironmentTest(Base):

    def setUp(self):
        self.config = mock.MagicMock()

    @mock.patch('subprocess.check_output')
    def test_bootstrap_jenv(self, run_juju):
        # Setup some mocks
        self.config.get_env_name.return_value = "slayer"
        self.config.juju_home = juju_home = self.mkdir()
        self.config.get_env_conf.return_value = os.path.join(
            juju_home, "environments.yaml")
        # Setup juju home structure
        os.mkdir(os.path.join(juju_home, "environments"))
        os.mkdir(os.path.join(juju_home, "ssh"))
        with open(os.path.join(juju_home,
                               "ssh", "juju_id_rsa"), 'w') as fh:
            fh.write("Content")
        with open(os.path.join(juju_home,
                               "ssh", "juju_id_rsa.pub"), 'w') as fh:
            fh.write("Other Content")

        with open(os.path.join(juju_home, 'environments.yaml'), 'w') as fh:
            fh.write("# Some comment\n" + yaml.safe_dump(
                {"environments": {
                 "aws":
                    {"type": "ec2",
                     "region": "us-east-1",
                     "control-bucket": "rabbit-moon"},
                 "slayer":
                    {"type": "manual",
                     "bootstrap-user": "root",
                     "bootstrap-host": "manual"}}}))

        def verify_home(cmd, env, stderr=None):
            self.assertEqual(
                cmd, ['juju', 'bootstrap', '--debug', '--upload-tools'])
            self.assertTrue(env['JUJU_HOME'].startswith(juju_home))
            self.assertTrue(env['JUJU_HOME'].endswith('boot-slayer'))
            with open(os.path.join(env['JUJU_HOME'],
                                   'environments.yaml')) as fh:
                data = yaml.safe_load(fh.read())
                self.assertEqual(
                    data['environments'].keys(), ['slayer'])
                self.assertEqual(
                    data['environments']['slayer']['bootstrap-host'],
                    '1.1.1.1')

            with open(os.path.join(env['JUJU_HOME'],
                                   'environments', 'slayer.jenv'), 'w') as fh:
                fh.write('hello world')

        run_juju.side_effect = verify_home

        self.env = Environment(self.config)
        self.env.bootstrap_jenv('1.1.1.1')

        self.assertNotIn('boot-slayer', os.listdir(juju_home))
