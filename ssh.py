import os, subprocess, atexit, threading

def gen_host_keys():
    fifodir = '/run/user/%s/mkserver' % os.getuid()
    os.makedirs(fifodir, exist_ok=True)

    privfile = fifodir + '/hkey%s' % os.getpid()
    pubfile = privfile + '.pub'
    os.mkfifo(privfile)
    os.mkfifo(pubfile)
    atexit.register(lambda: [ os.remove(f) for f in (privfile, pubfile) ])

    keygen = subprocess.Popen(['ssh-keygen', '-q', '-N', '', '-f', privfile], stdin=subprocess.PIPE)
    keygen.stdin.write(b'y\n')
    keygen.stdin.flush()

    with open(privfile, 'r') as privfp, open(pubfile, 'r') as pubfp:
        l = []
        t = threading.Thread(target=lambda l: l.append(privfp.read()), args=(l,))
        t.start()
        pubkey = pubfp.read()
        t.join()
        privkey = l[0]
    keygen.wait()
    assert(keygen.returncode == 0)

    return (pubkey, privkey)
