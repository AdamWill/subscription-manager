from __future__ import print_function, division, absolute_import

# Copyright (c) 2016 Red Hat, Inc.
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

"""
This module includes notifier using inotify. The notifier checks
for changes in /etc/pki/consumers for newly created or deleted
certificates.
"""

import logging
import pyinotify
import time

from subscription_manager import injection as inj

log = logging.getLogger(__name__)


class EventHandler(pyinotify.ProcessEvent):
    """
    Class used for reloading consumer certificate
    """
    def __init__(self, *args, **kwargs):
        super(EventHandler, self).__init__(*args, **kwargs)
        self.identity = inj.require(inj.IDENTITY)
        self.dir_watches = kwargs.pop("dir_watches", [])

    def process_IN_CREATE(self, event):
        """
        This method is executed every time new file is created
        in directory with certificates of consumer
        :param event: Inotify event
        :return: None
        """
        if event.pathname == self.identity.cert_dir_path + '/cert.pem':
            log.debug("New consumer certificate %s was created", event.pathname)
        if event.pathname == self.identity.cert_dir_path + '/key.pem':
            log.debug("New consumer key %s was created", event.pathname)
        self.identity.reload()

    def process_IN_DELETE(self, event):
        """
        This method is executed every time any file is deleted
        in directory with certificates of consumer
        :param event: Inotify event
        :return: None
        """
        if event.pathname == self.identity.cert_dir_path + '/cert.pem':
            log.debug("Existing consumer certificate %s was removed", event.pathname)
        if event.pathname == self.identity.cert_dir_path + '/key.pem':
            log.debug("Existing consumer key %s was removed", event.pathname)
        self.identity.reload()

    def process_default(self, event):
        """
        This method will check for a match of the event against all directories given to watch.
        :param event: Inotify event
        :return:
        """
        for dir_watch in self.dir_watches:
            if dir_watch.match_path(event.pathname) and dir_watch.match_mask(event.mask):
                dir_watch.notify()

    @classmethod
    def from_dir_watches(cls, dir_watches=None, changed_callback=None):
        return cls(dir_watches=dir_watches)


class Notifier(pyinotify.Notifier):

    def update(self):
        """
        Perform a single round of updates.
        :return:
        """
        if self.check_events():
            self.read_events()
        self.process_events()

    def sleep(self):
        self._sleep(time.time())


def inotify_cb(notifier):
    """
    This method check if notifier should be terminated or not
    :param notifier: Notifier object
    :return: True, when notifier should be terminated.
    """
    return notifier.server.terminate_loop


def inotify_worker(server, dir_watches=None):
    """
    Thread worker using inotify for checking changes in directory
    with consumer certificates
    :param server: Reference to instance of Server
    :param dir_watches: List of DirectoryWatches, used to
    :return None
    """
    watch_manager = pyinotify.WatchManager()
    # Create custom event handler
    handler = EventHandler.from_dir_watches(dir_watches=dir_watches)
    # Create notifier with timeout (one second).
    notifier = pyinotify.Notifier(watch_manager, handler, timeout=1000)
    # Add reference at server into notifier
    notifier.server = server
    # We are interested only newly created files (system was registered)
    # and deleted files (system was unregistered)
    mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE
    # Start to watch for events in directory with certificates of consumer
    watch_manager.add_watch(handler.identity.cert_dir_path, mask, rec=False)
    # Start loop. The loop can be stop in callback every second (timeout)
    notifier.loop(callback=inotify_cb)
