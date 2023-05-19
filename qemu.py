import os, sys, subprocess, re, atexit, psutil, socket, errno, time

import util

_semver = re.compile('[0-9]+[.][0-9]+[.][0-9]+')
def _recent_version(program, needmajor, needminor, needpatch):
    verstr = subprocess.run([program, '--version'], capture_output=True).stdout.decode()
    major, minor, patch = [int(i) for i in _semver.search(verstr)[0].split('.')]
    return major > needmajor or (major == needmajor and minor > needminor) or \
        (major == needmajor and minor == needminor and patch >= needpatch)

class OldDependency(Exception):
    pass

class Qemu:
    def __init__(self, imgdir, cmd=None):
        self.imgdir = imgdir

        #XXX x86-64 support
        self.qemu = os.environ.get('QEMU', 'qemu-system-aarch64')
        self.nbdkit = os.environ.get('NBDKIT', 'nbdkit')

        dtb_filename = os.environ.get('DTB', 'bcm2710-rpi-3-b.dtb')

        kernel_args = ''
        if cmd is not None:
            kernel_args += 'XQEMUXcmd_to_eol=%s' % cmd

        self._qemu_args = [self.qemu, '-M', 'raspi3b', '-m', '1024',
                           '-kernel', os.path.join(imgdir, 'u-boot.bin'),
                           '-dtb', os.path.join(imgdir, dtb_filename),
                           '-append', kernel_args,
                           '-device', 'usb-net,netdev=net0',
                           '-netdev', 'user,id=net0,hostfwd=tcp::22222-:22',
                           '-drive', 'if=sd,format=raw,index=0,file=$nbd',
                           '-nographic']

    def _get_qemu_args(self, monsock=None, confile=None):
        assert(bool(confile) == bool(monsock)) #XXX Add support for only one being specified.
        qemu_args = self._qemu_args
        if confile or monsock:
            if monsock:
                qemu_args += ['-chardev', 'socket,path=%s,server=on,wait=off,id=charmon' % monsock,
                              '-mon', 'charmon,mode=control']
            if confile:
                qemu_args += ['-chardev', 'file,path=%s,mux=on,id=charcon' % confile,
                              '-serial', 'chardev:charcon', '-serial', 'chardev:charcon']
        else:
            qemu_args += ['-chardev', 'stdio,id=char0,mux=on,signal=off',
                          '-serial', 'chardev:char0', '-serial', 'chardev:char0',
                          '-mon', 'chardev=char0']

        qemu_args = util.posix_list2cmdline(qemu_args).replace('\\$nbd', '$nbd')

        #sdcards must be a power of 2.
        size = 16 * 1024 * 1024 * 1024

        recent_nbdkit, recent_qemu = _recent_version(self.nbdkit, 1, 27, 2), _recent_version(self.qemu, 6, 1, 0)
        if not recent_qemu:
            print('WARNING: Your qemu is too old to support soft rebooting rapsberry'
                  ' pis, so mkserver --update will not work. You need 6.1.0 or newer', file=sys.stderr)
            raise OldDependency("qemu")
        if recent_nbdkit:
            args = [self.nbdkit, '-U', '-', '--filter=cow',
                    'floppy', 'dir=%s' % self.imgdir, 'size=%s' % size,
                    '--run', qemu_args]
        else:
            print('WARNING: Your nbdkit is too old to support writing to the SDCard,'
                  ' so mkserver --update will not work. You need 1.27.2 or newer.', file=sys.stderr)
            args = [self.nbdkit, '-U', '-', '--filter=truncate', '--filter=cow',
                    'floppy', 'dir=%s' % self.imgdir, 'truncate=%s' % size,
                    '--run', qemu_args]
            raise OldDependency("nbdkit")

        return args

    def run(self, monsock=None, confile=None):
        if not confile:
            print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
        self._qemu = subprocess.Popen(self._get_qemu_args(monsock=monsock, confile=confile))
        atexit.register(self.__del__)

    def wait_for_ssh(self):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 22222))
                    if len(s.recv(1)) == 1:
                        break
            except socket.error as err:
                if err.errno != errno.ECONNREFUSED:
                    raise err
            time.sleep(0.1)

    def ssh(self, *cmd):
        extra_ssh_args = os.environ.get('EXTRASSHARGS', '').split()
        if len(extra_ssh_args) == 0:
            extra_ssh_args = [ '-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no' ]
        p = subprocess.run(['ssh', *extra_ssh_args,
                            'root@localhost', '-p', '22222', *cmd], capture_output=True)
        return (p.returncode, p.stdout, p.stderr)

    def __del__(self):
        if hasattr(self, '_qemu'):
            parent = psutil.Process(self._qemu.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            delattr(self, '_qemu')

    def exec(self, monsock=None):
        print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
        os.execvp(self.nbdkit, self._get_qemu_args(monsock=monsock))
