# -*- coding: utf-8 -*-

# default values for our content rule
# can be monkey patched by integrators

DEFAULT_DEADLINE_DELAY = 5
DEFAULT_REMINDER_DELAY = 2
DEFAULT_ACQUIRED_ROLES = True

DEFAULT_NOTIFICATION_SUBJECT = u'Read request'

DEFAULT_NOTIFICATION_TEXT = (
    u'Dear ${mustread_fullname}\n'
    u'${user_fullname} has requested you to read "${title}" before '
    u'${mustread_deadline} \n\n'
    u'${mustread_url}\n\n'
    u'Thanks in advance!')


DEFAULT_REMINDER_SUBJECT = u'Reminder: read request'

DEFAULT_REMINDER_TEXT = (
    u'Dear ${mustread_fullname}, please make sure to read "${title}" before '
    u'${mustread_deadline} \n\n'
    u'${mustread_url}')
