import os, tempfile, shutil, stat, glob, subprocess
from string import Template

from deb import extract_files_from_deb_url

class Initramfs:
    def __init__(self, busybox_url, init, initcmd):
        self.tmpdir_obj = tempfile.TemporaryDirectory(prefix='mks_initrd_')
        self.tmpdir = self.tmpdir_obj.name

        for d in ('boot', 'newroot', 'mods',
                  'bin', 'dev', 'etc', 'proc', 'sys', 'tmp', 'var'):
            os.makedirs(os.path.join(self.tmpdir, d))

        extract_files_from_deb_url(busybox_url, '^./bin/busybox', os.path.join(self.tmpdir, 'bin'))
        bbox = os.path.join(self.tmpdir, 'bin', 'busybox')
        os.chmod(bbox, stat.S_IRUSR | stat.S_IXUSR)
        buf = subprocess.check_output([bbox, '--list']).decode()
        for cmd in buf.split():
            if cmd != 'busybox':
                os.link(bbox, os.path.join(self.tmpdir, 'bin', cmd))

        with (open(init, 'r') as inf,
              open(os.path.join(self.tmpdir, 'init'), 'w') as outf):
            outf.write(Template(inf.read()).safe_substitute(initcmd=initcmd))
        os.chmod(os.path.join(self.tmpdir, 'init'), stat.S_IRUSR | stat.S_IXUSR)

    def copyin(self, files, destdir):
        for f in files:
            shutil.copy(f, os.path.join(self.tmpdir, destdir))

    def write_cpiofile(self, outfile):
        files = [ x[len(self.tmpdir)+1:]+'\n' for x in
                  glob.glob(os.path.join(self.tmpdir, '**'), recursive=True)
                  if len(x) != len(self.tmpdir)+1 ]

        with open(outfile, 'wb') as f:
            cpio = subprocess.Popen(['cpio', '-D', self.tmpdir, '-o', '--owner', '+0:+0', '-H', 'newc'],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            gzip = subprocess.Popen(['gzip'], stdin=cpio.stdout, stdout=f)
            cpio.stdin.write(''.join(files).encode())
            cpio.stdin.close()
            gzip.wait()
            cpio.wait()
            assert(gzip.returncode == 0)
            assert(cpio.returncode == 0)
