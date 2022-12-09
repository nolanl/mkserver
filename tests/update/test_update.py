import time, os
from testutil import build_container, do_update

class TestUpdate:
    def test_update(self, dirs, runvm):
        #XXX Would be nice to overlap building updated container/imgdir with qemu booting.

        build_container(dirs.dockerpath, dirs.dockerpath + '/Dockerfile.updated', 'mkst_updated')

        ret = runvm.ssh('[', '-f', '/update', '-a', '!', '-f', '/updated', ']')
        assert(ret[0] == 0)

        do_update('mkst_updated', 'mkstest', 'localdomain')
        time.sleep(1) #Let the reboot get far enough that the old SSH is down.
        runvm.wait_for_ssh()

        ret = runvm.ssh('[', '-f', '/update', '-a', '-f', '/updated', ']')
        assert(ret[0] == 0)

    def test_cross_update(self, dirs, runvm):
        build_container(dirs.dockerpath, dirs.dockerpath + '/Dockerfile.cross_update', 'mkst_cross_upgrade')

        do_update('mkst_cross_upgrade', 'mkstest', 'localdomain')
        time.sleep(1) #Let the reboot get far enough that the old SSH is down.
        runvm.wait_for_ssh()

        ret = runvm.ssh('[', '-f', '/cross', '-a', '!', '-f', '/update', ']')
        assert(ret[0] == 0)

        #Verify that GC of the layers worked.
        ret = runvm.ssh('ls', '-1', '/boot/layers/*.sqfs')
        layers = [os.path.splitext(os.path.basename(i))[0] for i in ret[1].decode().split()]
        ret = runvm.ssh('cat', '/boot/slot*/layers')
        reflayers = set(ret[1].decode().split())
        reflayers.update(('identity', 'user_identity'))
        for i in reflayers:
            layers.remove(i)
        assert(len(layers) == 0)
