import os, sys, subprocess

import util

#XXX x86-64 support
qemu = os.environ.get('QEMU', 'qemu-system-aarch64')
nbdkit = os.environ.get('NBDKIT', 'nbdkit')
dtb_filename = os.environ.get('DTB', 'bcm2710-rpi-3-b.dtb')

def _recent_nbdkit():
    verstr = subprocess.run(['nbdkit', '--version'], capture_output=True).stdout.decode()[7:-1]
    major, minor, patch = [int(i) for i in verstr.split('.')]
    return major > 1 or (major == 1 and minor > 27) or (major == 1 and minor == 27 and patch > 8)

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
    if _recent_nbdkit():
        args = [nbdkit, '-U', '-', '--filter=cow',
                'floppy', 'dir=%s' % imgdir, 'size=%s' % size,
                '--run', qemu_args]
    else:
        print('WARNING: Your nbdkit is too old to support writing to the SDCard,'
              ' you need 1.27.9 or newer.', file=sys.stderr)
        args = [nbdkit, '-U', '-', '--filter=truncate', '--filter=cow',
                'floppy', 'dir=%s' % imgdir, 'truncate=%s' % size,
                '--run', qemu_args]
    print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
    os.execvp(nbdkit, args)
