ARG FROM_PREFIX
FROM ${FROM_PREFIX}busybox:1.32.0-uclibc

ARG ICMD

COPY init /

RUN    mkdir -p /boot /newroot \
    && sed -i "s,XXXCMDXXX,${ICMD},g" /init
