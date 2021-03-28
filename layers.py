import os, tarfile, json, re, subprocess, time
from io import BytesIO

def tar2sqfs_cmd(tarfile):
    #XXX xz for fast CPUs, lzo (or default gzip) for slow?
    return ['tar2sqfs', os.path.splitext(tarfile)[0] + '.sqfs']

#Takes a stream in "docker save" format, and extracts it to sqfs (by default) layers
# in outdir. Metadata is saved as well. putasides allow files matching a regex to
# be extracted to a directory, and either written to the sqfs, or not. It takes a
# list of tuples in the following format:
# ('^regex/of/files', (output_dir, swallow)). swallow is a boolean specifying if
# this file is to be swallowed (not also written into the squashfs).
#
# Note that files putaside do not preserve ownership/permissions from the tarfile.
class ContainerStream:
    def __init__(self, infp, outdir, putasides, cmd_func=tar2sqfs_cmd):
        putasides = [ (re.compile(i[0]), i[1]) for i in putasides ]
        def _match_pas(name):
            for pa in putasides:
                if pa[0].match(name):
                    return pa[1]
            return None

        self.jsonfiles = {}
        tar = tarfile.open(fileobj=infp, mode='r|')
        for tinfo in tar:
            name = tinfo.name

            if name.endswith('.json'):
                self.jsonfiles[name] = json.loads(tar.extractfile(tinfo).read().decode('utf-8'))

            if name.endswith('.tar') and not name.endswith('layer.tar'):
                innertar = tarfile.open(fileobj=tar.extractfile(tinfo), mode='r|')
                cmd = subprocess.Popen(cmd_func(os.path.join(outdir, name)), stdin=subprocess.PIPE)
                outtar = tarfile.open(fileobj=cmd.stdin, mode='w|')

                for innertinfo in innertar:
                    innername = innertinfo.name

                    m = _match_pas(innername)
                    swallow = False
                    if innertinfo.isfile():
                        innerstream = innertar.extractfile(innertinfo)
                    if m is not None:
                        padir, swallow = m
                        if padir != '':
                            if innertinfo.isfile():
                                data = innerstream.read()
                                with open(os.path.join(padir, os.path.basename(innername)), 'wb') as f:
                                    f.write(data)
                                innerstream = BytesIO(data) #in case we don't swallow the file.
                            else:
                                innertar.extract(innertinfo, outdir, set_attrs=False)

                    if not swallow:
                        if innertinfo.isfile():
                            outtar.addfile(innertinfo, innerstream)
                        else:
                            outtar.addfile(innertinfo)

                innertar.close()
                outtar.close()
                cmd.wait()
                assert(cmd.returncode == 0)

        tar.close()

        self.manifests = self.jsonfiles['manifest.json']
        self.config = self.jsonfiles[self.manifests[0]['Config']]

    def get_layernames(self):
        rootfs = self.config['rootfs']
        assert(rootfs['type'] == 'layers')
        return [ x.split(':')[1] for x in rootfs['diff_ids'] ]

    def get_architecture(self):
        return self.config['architecture']

    def get_cmdlist(self):
        return self.config['config']['Cmd']

    def get_tags(self):
        return self.manifests[0]['RepoTags']

#Converts a dict to a (by default) sqfs file. Keys are filenames, and the values
# are a tuple (filedata, mode). To encode symlinks, use ('SYMLINK:/path/to/dest', 0).
def dict_to_layer(d, layername, cmd_func=tar2sqfs_cmd):
    cmd = subprocess.Popen(cmd_func(layername + '.tar'), stdin=subprocess.PIPE)
    outtar = tarfile.open(fileobj=cmd.stdin, mode='w|')
    mtime = time.time()

    for name, (data, mode) in d.items():
        tinfo = tarfile.TarInfo(name)
        tinfo.mode = mode
        tinfo.mtime = mtime
        if data.startswith('SYMLINK:'):
            tinfo.type = tarfile.SYMTYPE
            tinfo.linkname = data[len('SYMLINK:'):]
            datastream = None
        else:
            tinfo.type = tarfile.REGTYPE
            if type(data) is str:
                data = data.encode()
            tinfo.size = len(data)
            datastream = BytesIO(data)
        outtar.addfile(tinfo, datastream)

    outtar.close()
    cmd.wait()
    assert(cmd.returncode == 0)
