import bisect

from juju_slayer.exceptions import ConstraintError


CPUS = (1, 2, 4, 8, 12, 16)
# Unit MB
MEM = (1024, 2048, 4096, 6144, 8192, 12288, 16384, 32768, 49152, 65536)
# Unit GB
ROOT_DISK = (25, 100)
IMAGE_MAP = {
    'precise': 'UBUNTU_12_64',
    '12.0.4': 'UBUNTU_12_64'}

# Record regions so we can offer nice aliases.
# ams01,dal01,dal05,dal06,sea01,sjc01,sng01,wdc01

REGIONS = [
    {'name': 'ams01', 'aliases': ['ams', 'ams1'], 'id': 'ams01'},
    {'name': 'dal01', 'aliases': ['dal1'], 'id': 'dal01'},
    {'name': 'dal05', 'aliases': ['dal5', 'dal'], 'id': 'dal05'},
    {'name': 'dal06', 'aliases': ['dal6'], 'id': 'dal06'},
    {'name': 'sea01', 'aliases': ['sea', 'sea1'], 'id': 'sea01'},
    {'name': 'sng01', 'aliases': ['sng', 'sng1'], 'id': 'sng01'},
    {'name': 'sjc01', 'aliases': ['sjc1', 'sjc'], 'id': 'sjc01'},
    {'name': 'wdc01', 'aliases': ['wdc1', 'wdc'], 'id': 'wdc01'}]

VALID_REGIONS = [r['name'] for r in REGIONS]

ARCHES = ['amd64']

# afaics, these are unavailable
#
#    {'name': 'Amsterdam 1 1', 'aliases': ['ams1']

SUFFIX_SIZES = {
    "m": 1,
    "g": 1024,
    "t": 1024 * 1024,
    "p": 1024 * 1024 * 1024}

VALID_CONSTRAINTS = set(['region', 'cpu-cores', 'root-disk', 'mem', 'arch'])


def converted_size(s):
    q = s[-1].lower()
    size_factor = SUFFIX_SIZES.get(q)
    if size_factor:
        if s[:-1].isdigit():
            return int(s[:-1]) * size_factor
        return None
    elif s.isdigit():
        return int(s)
    return None


def parse_constraints(constraints):
    """
    """
    c = {}
    parts = filter(None, constraints.split(","))
    for p in parts:
        k, v = p.split('=', 1)
        c[k.strip()] = v.strip()

    unknown = set(c).difference(
        set(['region', 'cpu-cores', 'root-disk', 'mem', 'arch']))
    if unknown:
        raise ConstraintError("Unknown constraints %s valid:%s" % (
            " ".join(unknown), ", ".join(VALID_CONSTRAINTS)))

    if 'mem' in c:
        d = c.pop('mem')
        q = converted_size(d)
        idx = bisect.bisect_left(MEM, q)
        if idx == len(MEM):
            raise ConstraintError(
                "Invalid memory size %s valid: %s" % d,
                ", ".join(["%sG" % (m/1024) for m in MEM]))
        c['memory'] = MEM[idx]
    else:
        c['memory'] = MEM[0]

    if 'root-disk' in c:
        d = c.pop('root-disk')
        q = converted_size(d)
        if q is None:
            raise ConstraintError("Unknown root disk size %s" % d)
        q = q / 1024
        idx = bisect.bisect_left(ROOT_DISK, q)
        if idx == len(ROOT_DISK):
            raise ConstraintError(
                "Invalid root-disk size %s valid: %s" % d,
                ", ".join(["%sG" % r for r in ROOT_DISK]))
        c['disks'] = [q]

    if 'cpu-cores' in c:
        d = c.pop('cpu-cores')
        if not d.isdigit():
            raise ConstraintError(
                "Unknown cpu-cores value %s valid: %s" % d, ", ".join(CPUS))
        d = int(d)
        if not d in CPUS:
            raise ConstraintError(
                "Unknown cpu-cores value %s valid: %s" % d, ", ".join(CPUS))
        c['cpus'] = d
    else:
        c['cpus'] = 1

    if 'arch' in c:
        d = c.pop('arch')
        if not d in ARCHES:
            raise ConstraintError("Unsupported arch %s" % d)

    if 'region' in c:
        d = c.pop('region')
        for r in REGIONS:
            if d == r['name']:
                c['datacenter'] = r['id']
                break
            elif d in r['aliases']:
                c['datacenter'] = r['id']
                break
        if not 'datacenter' in c:
            raise ConstraintError("Unknown datacenter %s valid: %s" % (
                d, ", ".join(VALID_REGIONS)))

    return c


def solve_constraints(constraints):
    """Return machine size and region.
    """
    params = parse_constraints(constraints)
    if not params:
        params.update(dict(cpus=1, memory=1))
    return params
