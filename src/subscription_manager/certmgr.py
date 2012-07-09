#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import sys
sys.path.append("/usr/share/rhsm")

from subscription_manager.certlib import CertLib, ActionLock, HealingLib,\
     ConsumerIdentity, IdentityCertLib
from subscription_manager.repolib import RepoLib
from subscription_manager.factlib import FactLib
from subscription_manager.facts import Facts
from subscription_manager.cache import PackageProfileLib, InstalledProductsLib

import rhsm.connection as connection

import gettext
_ = gettext.gettext


class CertManager:
    """
    An object used to update the certficates, yum repos, and facts for
    the system.

    @ivar certlib: The RHSM I{entitlement} certificate management lib.
    @type certlib: L{CertLib}
    @ivar repolib: The RHSM repository management lib.
    @type repolib: L{RepoLib}
    """

    def __init__(self, lock=ActionLock(), uep=None):
        self.lock = lock
        self.uep = uep
        self.certlib = CertLib(self.lock, uep=self.uep)
        self.repolib = RepoLib(self.lock, uep=self.uep)
        self.factlib = FactLib(self.lock, uep=self.uep)
        self.profilelib = PackageProfileLib(self.lock, uep=self.uep)
        self.installedprodlib = InstalledProductsLib(self.lock, uep=self.uep)
        #healinglib requires a fact set in order to get socket count
        facts = Facts()
        self.healinglib = HealingLib(self.lock, uep=self.uep, facts_dict=facts.to_dict())
        self.idcertlib = IdentityCertLib(self.lock, uep=self.uep)

    def update(self, autoheal=False):
        """
        Update I{entitlement} certificates and corresponding
        yum repositiories.
        @return: The number of updates required.
        @rtype: int
        """
        updates = 0
        lock = self.lock
        try:
            lock.acquire()

            # WARNING: order is important here, we need to update a number
            # of things before attempting to autoheal, and we need to autoheal
            # before attempting to fetch our certificates:
            if autoheal:
                libset = [self.healinglib]
            else:
                libset = [self.idcertlib, self.repolib, self.factlib, self.profilelib, self.installedprodlib]

            for lib in libset:
                updates += lib.update()

            # WARNING
            # Certlib inherits DataLib as well as the above 'lib' objects,
            # but for some reason it's update method returns a tuple instead
            # of an int:
            ret = self.certlib.update()
            updates += ret[0]
            for e in ret[1]:
                print ' '.join(str(e).split('-')[1:]).strip()
        finally:
            lock.release()
        return updates


def main(options):
    if not ConsumerIdentity.existsAndValid():
        log.error('Either the consumer is not registered or the certificates' +
                  ' are corrupted. Certificate update using daemon failed.')
        sys.exit(-1)
    print _('Updating entitlement certificates & repositories')
    uep = connection.UEPConnection(cert_file=ConsumerIdentity.certpath(),
                                   key_file=ConsumerIdentity.keypath())
    mgr = CertManager(uep=uep)
    updates = mgr.update(options.autoheal)
    print _('%d updates required') % updates
    print _('done')


# WARNING: This is not a block of code used to test, this module is
# actually run as a script via cron to periodically update the system's
# certificates, yum repos, and facts.
if __name__ == '__main__':
    import logging
    import logutil
    from i18n_optparse import OptionParser

    logutil.init_logger()
    log = logging.getLogger('rhsm-app.' + __name__)

    parser = OptionParser()
    parser.add_option("--autoheal", dest="autoheal", action="store_true", default=False,
                  help="perform an autoheal check")
    (options, args) = parser.parse_args()
    try:
        main(options)
    except SystemExit:
        # sys.exit triggers an exception in older Python versions, which
        # in this case  we can safely ignore as we do not want to log the
        # stack trace.
        pass
    except Exception, e:
        log.error("Error while updating certificates using daemon")
        print _('Unable to update entitlement certificates & repositories')
        log.exception(e)
        sys.exit(-1)
