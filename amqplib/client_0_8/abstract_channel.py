"""
Code common to Connection and Channel objects.

"""
# Copyright (C) 2007-2008 Barry Pederson <bp@barryp.org>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301

import logging

from exceptions import METHOD_NAME_MAP
from serialization import AMQPWriter

__all__ =  [
            'AbstractChannel',
           ]

AMQP_LOGGER = logging.getLogger('amqplib')


class AbstractChannel(object):
    """
    Superclass for both the Connection, which is treated
    as channel 0, and other user-created Channel objects.

    The subclasses must have a _METHOD_MAP class property, mapping
    between AMQP method signatures and Python methods.

    """
    def __init__(self, connection, channel_id):
        self.connection = connection
        self.channel_id = channel_id
        connection.channels[channel_id] = self
        self.method_queue = [] # Higher level queue for methods
        self.auto_decode = False


    def _dispatch(self, method_sig, args, content):
        """
        Find and call a Python method to handle the given AMQP method.

        """
        amqp_method = self._METHOD_MAP.get(method_sig, None)

        if amqp_method is None:
            raise Exception('Unknown AMQP method (%d, %d)' % method_sig)

        if content is None:
            return amqp_method(self, args)
        else:
            return amqp_method(self, args, content)


    def _send_method(self, method_sig, args='', content=None):
        """
        Send a method for our channel.

        """
        if isinstance(args, AMQPWriter):
            args = args.getvalue()

        self.connection.method_writer.write_method(self.channel_id,
            method_sig, args, content)


    def wait(self, allowed_methods=None, timeout=None):
        """
        Wait for a method that matches our allowed_methods parameter (the
        default value of None means match any method), and dispatch to it.

        Unexpected methods are queued up for later calls to this Python
        method.

        """
        method_sig, args, content = self.connection._wait_method(
            self.channel_id, allowed_methods, timeout)

        if content \
        and self.auto_decode \
        and hasattr(content, 'content_encoding'):
            try:
                content.body = content.body.decode(content.content_encoding)
            except:
                pass

        return self._dispatch(method_sig, args, content)


    #
    # Placeholder, the concrete implementations will have to
    # supply their own versions of _METHOD_MAP
    #
    _METHOD_MAP = {}
