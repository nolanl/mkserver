import subprocess, os

def posix_list2cmdline(args):
    return ' '.join(["'%s'" % c for c in args]) #XXX Escape "'" in cmdlist elements

def write_uboot_script(outdir, slotname, kernelver):
    slotcfgtxt = os.path.join(outdir, 'slotcfg.txt')

    with open(slotcfgtxt, 'w') as f:
        f.write('setenv slot %s\n' % slotname)
        f.write('setenv kernelver %s\n' % kernelver)

    subprocess.check_call(['mkimage', '-T', 'script', '-C', 'none', '-n', '%s slotcfg' % slotname,
                           '-d', slotcfgtxt, os.path.join(outdir, 'slotcfg.scr')])

    os.remove(slotcfgtxt)
