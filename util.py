import subprocess, os, io, hashlib

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

#Wrapper that SHA256s the contents of the stream.
class SHA256Pipe(io.RawIOBase):
    def __init__(self, fd):
        self.fd = fd
        self.hasher = hashlib.sha256()
    def readinto(self, b):
        l = self.fd.readinto(b)
        if l > 0:
            self.hasher.update(b[0:l])
        return l
    def hexdigest(self):
        return self.hasher.hexdigest()
