import os, subprocess

import util

#XXX x86-64 support
qemu = 'qemu-system-aarch64'
nbdkit = 'nbdkit'
dtb_filename = 'bcm2837-rpi-3-b.dtb'

SLOP = 256 * 1024 * 1024

def next_power_of_2(n):
    k = 1
    while k < n:
        k = k << 1
    return k

def qemu_run(imgdir, cmd=None):
    with open(os.path.join(imgdir, 'config.txt'), 'r') as cfgf:
        for l in cfgf.readlines():
            if l.startswith('kernel='):
                kernel = os.path.join(imgdir, l.split('=')[1]).strip()
            elif l.startswith('initramfs '):
                initrd = os.path.join(imgdir, l.split(' ')[1]).strip()
    dtb = os.path.join(imgdir, dtb_filename)

    with open(os.path.join(imgdir, 'cmdline.txt'), 'r') as cmdlinef:
        kernel_args = cmdlinef.readlines()[0].strip()
    if cmd is not None:
        kernel_args += ' cmd_to_eol=%s' % cmd

    #sdcards must be a power of 2, so we figure out the size of the dir, add some slop, then
    # pick the next highest power of 2.
    size = int(subprocess.check_output(['du', '-sb', imgdir], universal_newlines=True).split()[0])
    size = next_power_of_2(size + SLOP)

    qemu_args = [qemu, '-M', 'raspi3b', '-m', '1024',
                 '-kernel', kernel, '-dtb', dtb, '-initrd', initrd, '-append', kernel_args,
                 '-sd', '$nbd', '-nographic',
                 '-chardev', 'stdio,id=char0,mux=on,signal=off',
                 '-serial', 'chardev:char0', '-serial', 'chardev:char0', '-mon', 'chardev=char0']
    qemu_args = util.posix_list2cmdline(qemu_args).replace("'$nbd'", '$nbd')
    args = [nbdkit, '-U', '-', '--filter=truncate', '--filter=cow',
            'floppy', 'dir=%s' % imgdir, 'truncate=%s' % size,
            '--run', qemu_args]
    print('\n#####################\nctrl-a x to exit qemu\n#####################\n')
    os.execvp(nbdkit, args)
