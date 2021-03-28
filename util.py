def posix_list2cmdline(args):
    return ' '.join(["'%s'" % c for c in args]) #XXX Escape "'" in cmdlist elements
