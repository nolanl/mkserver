import subprocess, os, io, hashlib, shutil, urllib.request, urllib.parse

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

class BadDigest(Exception):
    pass
def urlopen_cache(url, sha256):
    cachedir = os.path.expanduser('~/.cache/mkserver') #XXX use appdirs here?
    os.makedirs(cachedir, exist_ok=True)
    cachefname = os.path.join(cachedir, os.path.split(urllib.parse.urlsplit(url).path)[-1])

    if not os.path.exists(cachefname):
        partfname = cachefname + '.PART'
        inf = SHA256Pipe(urllib.request.urlopen(url))
        with open(partfname, 'wb') as outf:
            shutil.copyfileobj(inf, outf)
            if inf.hexdigest() != sha256:
                raise BadDigest('Downloaded file %s has wrong sha256' % partfname)
            os.rename(partfname, cachefname)
    else:
        h  = hashlib.sha256()
        mv = memoryview(bytearray(128*1024))
        with open(cachefname, 'rb', buffering=0) as f:
            for n in iter(lambda : f.readinto(mv), 0):
                h.update(mv[:n])
        if h.hexdigest() != sha256:
            raise BadDigest('Cached file %s has wrong sha256' % cachefname)

    return open(cachefname, 'rb')
