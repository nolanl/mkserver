import os, sys, subprocess, re

import util

#XXX x86-64 support
qemu = os.environ.get('QEMU', 'qemu-system-aarch64')
nbdkit = os.environ.get('NBDKIT', 'nbdkit')
dtb_filename = os.environ.get('DTB', 'bcm2710-rpi-3-b.dtb')

semver = re.compile('[0-9]+[.][0-9]+[.][0-9]+')
def _recent_program(program, needmajor, needminor, needpatch):
    verstr = subprocess.run([program, '--version'], capture_output=True).stdout.decode()
    major, minor, patch = [int(i) for i in semver.search(verstr)[0].split('.')]
    return major > needmajor or (major == needmajor and minor > needminor) or \
        (major == needmajor and minor == needminor and patch >= needpatch)

def qemu_run(imgdir, cmd=None):
    dtb = os.path.join(imgdir, dtb_filename)

    kernel_args = ''
    if cmd is not None:
        kernel_args += 'XQEMUXcmd_to_eol=%s' % cmd

    #sdcards must be a power of 2.
    size = 16 * 1024 * 1024 * 1024

    qemu_args = [qemu, '-M', 'raspi3b', '-m', '1024',
                 '-kernel', os.path.join(imgdir, 'u-boot.bin'), '-dtb', dtb, '-append', kernel_args,
                 '-device', 'usb-net,netdev=net0',
                 '-netdev', 'user,id=net0,hostfwd=tcp::22222-:22',
                 '-drive', 'if=sd,format=raw,index=0,file=$nbd',
                 '-nographic', '-chardev', 'stdio,id=char0,mux=on,signal=off',
                 '-serial', 'chardev:char0', '-serial', 'chardev:char0', '-mon', 'chardev=char0']
    qemu_args = util.posix_list2cmdline(qemu_args).replace('\\$nbd', '$nbd')

    recent_nbdkit, recent_qemu = _recent_program(nbdkit, 1, 27, 2), _recent_program(qemu, 6, 1, 0)
    if recent_nbdkit and recent_qemu:
        args = [nbdkit, '-U', '-', '--filter=cow',
                'floppy', 'dir=%s' % imgdir, 'size=%s' % size,
                '--run', qemu_args]
    else:
        if not recent_nbdkit:
            print('WARNING: Your nbdkit is too old to support writing to the SDCard,'
                  ' so mkserver --update will not work. You need 1.27.2 or newer.', file=sys.stderr)
        if not recent_qemu:
            print('WARNING: Your qemu is too old to support soft rebooting rapsberry'
                  ' pis, so mkserver --update will not work. You need 6.1.0 or newer', file=sys.stderr)
        args = [nbdkit, '-U', '-', '--filter=truncate', '--filter=cow',
                'floppy', 'dir=%s' % imgdir, 'truncate=%s' % size,
                '--run', qemu_args]
    print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
    os.execvp(nbdkit, args)
