subscription-manager
====================

The Subscription Manager package provides programs and libraries
to allow users to manage subscriptions and yum repositories
from the  Candlepin.

 - http://candlepinproject.org/
 - https://fedorahosted.org/subscription-manager/
 - https://github.com/candlepin/subscription-Manager

Vagrant
-------

`vagrant up` can be used to spin up various VMs set up for development work.
These VMs are all configured using the included ansible role "subman-devel".
The `PYTHONPATH` and `PATH` inside these environments is modified so that
running `subscription-manager` or `subscription-manager-gui` will use
scripts and modules from the source code.

Currently, the source is set up as a vagrant shared folder using rsync. This
means that it is necessary to use `vagrant rsync` to sync changes with the
host if desired.

The ansible role that provisions the VMs tries to find the IP address of
candlepin.example.com, so if the candlepin vagrant image is started first,
then the box can resolve it. (If it is started later, `vagrant provision` can
be used to update the VM's `hosts` file).

Additionally, the `Vagrantfile` is set up for sharing base VMs with
[katello/forklift](https://github.com/theforeman/forklift). Specifically,
forklift plugins can be added to a subscription-manager checkout beneath
`vagrant/plugins`in order to provide additional base images.

If RHEL-based images are added, then the Vagrantfile uses the values of
`SUBMAN_RHSM_USERNAME`, `SUBMAN_RHSM_PASSWORD`, and `SUBMAN_RHSM_HOSTNAME`
to register and auto-attach during provisioning (best done in `.bashrc` or
similar).
