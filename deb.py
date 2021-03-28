import urllib.request, re, tarfile, os, shutil

#Extracts files matching path_regex from a deb from url. Directory structure
# is not preserved from the deb, all files end up in at toplevel in outdir.
def extract_files_from_deb_url(url, path_regex, outdir):
    regex = re.compile(path_regex)

    with urllib.request.urlopen(url) as f:
        assert(f.read(8) == b'!<arch>\n')
        while True:
            fname = f.read(16).rstrip()
            if fname == b'':
                break
            f.read(32)
            flen = int(f.read(10))
            assert(f.read(2) == b'`\n')
            if fname == b'data.tar.xz':
                tar = tarfile.open(fileobj=f, mode="r|*")
                for ti in tar:
                    if ti.isfile() and regex.match(ti.name):
                        tardata = tar.extractfile(ti)
                        with open(os.path.join(outdir, os.path.basename(ti.name)), 'wb') as outfile:
                            shutil.copyfileobj(tardata, outfile)
                break
            else:
                f.read(flen)
