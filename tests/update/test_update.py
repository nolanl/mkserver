import time
from testutil import build_container, do_update

def test_foo(dirs, runvm):
    #XXX Would be nice to overlap building updated container/imgdir with qemu booting.

    build_container(dirs.dockerpath, dirs.dockerpath + '/Dockerfile.updated', 'mkst_updated')

    ret = runvm.ssh('[', '-f', '/update', '-a', '!', '-f', '/updated', ']')
    assert(ret[0] == 0)

    do_update('mkst_updated', 'mkstest', 'localdomain')
    time.sleep(1) #Let the reboot get far enough that the old SSH is down.
    runvm.wait_for_ssh()

    ret = runvm.ssh('[', '-f', '/update', '-a', '-f', '/updated', ']')
    assert(ret[0] == 0)
