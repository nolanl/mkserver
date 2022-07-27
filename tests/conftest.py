import pytest
import os, shutil, types

from testutil import build_container, build_imgdir, run_vm

#XXX Redirect stdout/stderr for cbuild and imgdirbuild.

@pytest.fixture(scope='class')
def dirs(request):
    #XXX Allow to override Dockerfile. request.module.var? request.node.get_closest_marker?
    ret = {}
    ret['testfile'] = os.path.basename(request.fspath)
    ret['testdir'] = os.path.dirname(request.fspath)
    ret['testname'] = ret['testfile'].lstrip('test_').rstrip('.py')
    ret['imagename'] = 'mkst_' + ret['testname']

    ret['dockerfile'] = os.path.join(ret['testdir'], 'Dockerfile.' + ret['testname'])
    ret['dockerpath'] = os.path.dirname(ret['dockerfile'])

    ret['outputdir'] = '/build/tests'
    ret['testoutputdir'] = (ret['outputdir'] + '/').join(ret['testdir'].rsplit('/tests/', 1))
    os.makedirs(ret['testoutputdir'], exist_ok=True)
    yield types.SimpleNamespace(**ret)

@pytest.fixture(scope='class')
def container(dirs):
    print('Building container image', dirs.imagename)

    #XXX Keep our own cache to prevent unneeded rebuilds?

    #XXX Support deps so we don't hard code this
    build_container('docker', 'docker/Dockerfile.raspi', 'mks_raspi')

    build_container(dirs.dockerpath, dirs.dockerfile, dirs.imagename)

    yield dirs.imagename

@pytest.fixture(scope='class')
def imgdir(dirs, container):
    imgdir = dirs.testoutputdir + '/' + dirs.testname + 'img'
    if 'NOREBUILDIMGDIR' not in os.environ or \
       not (os.path.isdir(imgdir) and os.path.isfile(imgdir + '/initcmd.txt')):
        print('building imgdir for', dirs.testname)
        shutil.rmtree(imgdir, ignore_errors=True)
        os.makedirs(imgdir, exist_ok=False)

        build_imgdir(dirs.imagename, imgdir, 'mkstest', 'localdomain')
    else:
        print('skipping rebuild of imgdir for', dirs.testname)

    yield imgdir

@pytest.fixture(scope='class')
def runvm(dirs, imgdir):
    vm = run_vm(imgdir,
                confile=dirs.testoutputdir + '/' + dirs.testname + '.console',
                monsock=dirs.testoutputdir + '/' + dirs.testname + '.monsock')
    vm.wait_for_ssh()
    yield vm
    del(vm)
