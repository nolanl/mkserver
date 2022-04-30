import os, sys, subprocess, re

import util

_semver = re.compile('[0-9]+[.][0-9]+[.][0-9]+')
def _recent_version(program, needmajor, needminor, needpatch):
    verstr = subprocess.run([program, '--version'], capture_output=True).stdout.decode()
    major, minor, patch = [int(i) for i in _semver.search(verstr)[0].split('.')]
    return major > needmajor or (major == needmajor and minor > needminor) or \
        (major == needmajor and minor == needminor and patch >= needpatch)

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

    def _get_qemu_args(self, monsock=None, consock=None):
        assert(bool(consock) == bool(monsock)) #XXX Add support for only one being a socket.
        if consock or monsock:
            if monsock:
                pass #XXX
            if consock:
                pass #XXX
        else:
            qemu_args = self._qemu_args + ['-chardev', 'stdio,id=char0,mux=on,signal=off',
                                           '-serial', 'chardev:char0', '-serial', 'chardev:char0',
                                           '-mon', 'chardev=char0']

        qemu_args = util.posix_list2cmdline(qemu_args).replace('\\$nbd', '$nbd')

        #sdcards must be a power of 2.
        size = 16 * 1024 * 1024 * 1024

        recent_nbdkit, recent_qemu = _recent_version(self.nbdkit, 1, 27, 2), _recent_version(self.qemu, 6, 1, 0)
        if not recent_qemu:
            print('WARNING: Your qemu is too old to support soft rebooting rapsberry'
                  ' pis, so mkserver --update will not work. You need 6.1.0 or newer', file=sys.stderr)
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

        return args


    def exec(self, monsock=None):
        print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
        os.execvp(self.nbdkit, self._get_qemu_args(monsock = monsock))
