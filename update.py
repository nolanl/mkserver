import subprocess, os, shutil, sys
import util

def send_file(cmd, srcdir, filename, fout):
    fullfilename = os.path.join(srcdir, filename)
    fsize = os.path.getsize(fullfilename)
    fout.write(b'%s %s %d\n' % (cmd, filename.encode(), fsize))
    with open(fullfilename, 'rb') as f:
        shutil.copyfileobj(f, fout)
    fout.flush()

def readline(stdout):
    while True:
        ret = stdout.readline()
        if ret.startswith(b'__LOG__ '):
            print("RLOG", ret[8:].decode(), file=sys.stderr)
        else:
            return ret

def update_host(slotdir, layersdir, host, port):
    if 'DEBUG' in os.environ:
        extra_ssh_args = ['-o', 'UserKnownHostsFile=/dev/null', '-o', 'StrictHostKeyChecking=no']
    else:
        extra_ssh_args = []

    #XXX Does update belong in a per-slot bin dir? Seems unhelpful vs just /boot/bin/.
    #XXX Related, we need a way to update uboot and other stuff in /boot/.
    ssh = subprocess.Popen(['ssh', *extra_ssh_args, '-p', str(port), 'root@%s' % host, '/bin/sh', '-c',
                            "/boot/`cat /proc/cmdline | egrep -o 'root=[^ ]+' | cut -d'=' -f2`/bin/update"],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdin, stdout = ssh.stdin, ssh.stdout

    #Get current/new slot
    curslot, newslot = readline(stdout).split()
    print('Installing into slot', newslot.decode())

    #Get list of current layers
    cur_layers = []
    while True:
        layer = readline(stdout)
        if layer == b'__ENDLAYERS__\n':
            break
        cur_layers.append(layer[:-1].decode())

    #Upload new layers as needed
    with open(os.path.join(slotdir, 'layers'), 'r') as f:
        layers = [ l[:-1] for l in f.readlines() ]
    new_layers = set(layers) - set(cur_layers)
    for layer in new_layers:
        print('Uploading layer', layer)
        send_file(b'PUTLAYER', layersdir, '%s.sqfs' % layer, stdin)
        ret = readline(stdout)
        if ret != b'OK\n':
            raise Exception('Failed to PUTLAYER layer %s: %s' % (layer, ret))

    #Generate a new slotcfg.scr for this slot
    with open(os.path.join(slotdir, 'kver.txt'), 'r') as f:
        kernelver=f.read().strip()
    util.write_uboot_script(slotdir, newslot.decode(), kernelver)

    #Upload new bootslot files
    for fname in (os.path.join(d, x) for d, dirs, files in os.walk(slotdir) for x in files):
        relfname = fname[len(slotdir)+1:]
        print('Uploading slot file', relfname)
        send_file(b'PUTBOOTSLOT', slotdir, relfname, stdin)
        ret = readline(stdout)
        if ret != b'OK\n':
            raise Exception("Failed to PUTBOOTSLOT file %s: %s" % (fname, ret))

    #Finalize and cleanup
    stdin.write(b'FINALIZE\n')
    stdin.flush()
    ret = readline(stdout)
    if ret != b'OK\n':
        raise Exception('Failed to FINALIZE: %s' % ret)

    #Reboot
    stdin.write(b'REBOOT\n')
    stdin.flush()

    print('Finalized and rebooted')
