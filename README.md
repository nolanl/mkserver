# mkserver

A tool for building bootable images for servers from containers.

Primarily intended for read-only rootfs images, it supports building simple images that run a single program (in the "init=/do_things.sh" sense) or images that run with a proper init (1). The command to run is taken from the container's "Cmd" attribute.

Dockerfiles to use as a base are available in docker/.

To generate a new image, use:
```
$ podman/docker save mycontainer | mkserver --make-bootable /path/to/mounted/sdcard
```

To test an image locally using qemu:
```
$ mkserver --run /path/to/imagedir
```
