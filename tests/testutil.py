import subprocess, shutil
from qemu import Qemu

for runtime in ('podman', 'docker'):
    if shutil.which(runtime):
        CRUNTIME = runtime
PLATFORM = 'arm64' #XXX

def build_container(dockerpath, dockerfile, tag):
    subprocess.run([CRUNTIME, 'buildx', 'build', '--platform', PLATFORM, '-t', tag, '-f', dockerfile, dockerpath],
                   check=True)

def build_imgdir(image_name, imgdir, hostname, domainname):
    save = subprocess.Popen([CRUNTIME, 'save', image_name], stdout=subprocess.PIPE)
    #XXX Refactor so that this can just import and call mkserver code.
    mks = subprocess.run(['./mkserver', '--hostname', hostname, '--domain', domainname, '--cmd', '/bin/sh',
                          '--make-bootable', imgdir], check=True, stdin=save.stdout)
    save.wait()
    mks.check_returncode()

def run_vm(imgdir, confile, monsock):
    vm = Qemu(imgdir)
    vm.run(confile=confile, monsock=monsock)
    return vm

def do_update(image_name, hostname, domainname):
    save = subprocess.Popen([CRUNTIME, 'save', image_name], stdout=subprocess.PIPE)
    #XXX Refactor so that this can just import and call mkserver code.
    mks = subprocess.run(['./mkserver', '--hostname', hostname, '--domain', domainname, '--cmd', '/bin/sh',
                          '--sshport', '22222', '--update', 'localhost'], check=True, stdin=save.stdout)
    save.wait()
    mks.check_returncode()
