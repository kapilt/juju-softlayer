from base import Base

from juju_slayer.constraints import solve_constraints


class ConstraintTests(Base):

    cases = [
        ("region=wdc, cpu-cores=4, mem=2000",
         {'datacenter': 'wdc01', 'memory': 2048, 'cpus': 4}),

        ("region=ams, root-disk=100G",
         {'datacenter': 'ams01', 'memory': 1024, 'cpus': 1, 'disks': [100]}),

        ("region=dal, mem=24G",
         {'datacenter': 'dal05', 'cpus': 1, 'memory': 32768}),

        ("region=sea, mem=24G, arch=amd64",
         {'datacenter': 'sea01', 'cpus': 1, 'memory': 32768}),
        ("", {'cpus': 1, 'memory': 1024})]

    def test_constraint_solving(self):
        for constraints, solution in self.cases:
            self.assertEqual(
                solve_constraints(constraints),
                solution)
