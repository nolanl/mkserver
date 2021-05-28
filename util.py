import subprocess, os

def shell_escape(arg):
    dangerchars = ('\\', ' ', "'", '"', '`', '&', '|', ';', '#',
                   '$', '!', '(', ')', '[', ']', '<', '>', '\t')
    if len(arg) == 0:
        return "''"
    for char in dangerchars:
        arg = arg.replace(char, '\\%s' % char)
    return arg

def posix_list2cmdline(args):
    return ' '.join([shell_escape(arg) for arg in args])

def write_uboot_script(outdir, slotname, kernelver):
    slotcfgtxt = os.path.join(outdir, 'slotcfg.txt')

    with open(slotcfgtxt, 'w') as f:
        f.write('setenv slot %s\n' % slotname)
        f.write('setenv kernelver %s\n' % kernelver)

    subprocess.check_call(['mkimage', '-T', 'script', '-C', 'none', '-n', '%s slotcfg' % slotname,
                           '-d', slotcfgtxt, os.path.join(outdir, 'slotcfg.scr')])

    os.remove(slotcfgtxt)
