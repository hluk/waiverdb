FROM registry.fedoraproject.org/fedora:38 as builder

# hadolint ignore=DL3033,SC2039
RUN mkdir -p /mnt/rootfs \
    # install builder dependencies
    && yum install -y \
        --setopt install_weak_deps=false \
        --nodocs \
        --disablerepo=* \
        --enablerepo=fedora,updates \
        gcc \
        git-core \
        krb5-devel \
        openldap-devel \
        perl-Digest-SHA \
        python3 \
        python3-devel \
    # install runtime dependencies
    && yum install -y \
        --installroot=/mnt/rootfs \
        --releasever=/ \
        --setopt install_weak_deps=false \
        --nodocs \
        --disablerepo=* \
        --enablerepo=fedora,updates \
        krb5-libs \
        openldap \
        python3 \
    && yum --installroot=/mnt/rootfs clean all \
    && rm -rf /mnt/rootfs/var/cache/* /mnt/rootfs/var/log/dnf* /mnt/rootfs/var/log/yum.*

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# https://pdm-project.org/latest/#installation
ADD https://pdm-project.org/install-pdm.py install-pdm.py
ADD https://pdm-project.org/install-pdm.py.sha256 install-pdm.py.sha256

# hadolint ignore=DL4006,SC3040
RUN set -exo pipefail \
    && shasum -a 256 -c install-pdm.py.sha256 \
    && python3 install-pdm.py \
    && rm install-pdm.py*

COPY . .

# hadolint ignore=SC1091
RUN set -ex \
    && export PATH=$HOME/.local/bin:$PATH \
    && python3 -m venv /venv \
    && . /venv/bin/activate \
    && pdm install --check --frozen-lockfile --production --no-editable \
    && pdm cache clear \
    && deactivate \
    && mv /venv /mnt/rootfs \
    && mkdir -p /mnt/rootfs/app /etc/waiverdb \
    && cp -v docker/docker-entrypoint.sh /mnt/rootfs/app/entrypoint.sh \
    && cp conf/settings.py.example /etc/waiverdb/settings.py \
    && cp conf/client.conf.example /etc/waiverdb/client.conf

# --- Final image
FROM scratch
ARG GITHUB_SHA
ARG EXPIRES_AFTER
LABEL \
    summary="WaiverDB application" \
    description="An engine for storing waivers against test results." \
    maintainer="Red Hat, Inc." \
    license="GPLv2+" \
    url="https://github.com/release-engineering/waiverdb" \
    vcs-type="git" \
    vcs-ref=$GITHUB_SHA \
    io.k8s.display-name="WaiverDB" \
    quay.expires-after=$EXPIRES_AFTER

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    WEB_CONCURRENCY=8

COPY --from=builder /mnt/rootfs/ /
COPY --from=builder \
    /etc/yum.repos.d/fedora.repo \
    /etc/yum.repos.d/fedora-updates.repo \
    /etc/yum.repos.d/
WORKDIR /app

USER 1001
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--enable-stdio-inheritance", "waiverdb.wsgi:app"]
