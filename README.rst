================================
collective.contentrules.mustread
================================

Content rule to define which content items need to be read by which users (local roles) before a certain deadline.

A notification email is sent to all users when the read confirmation is requested.

An optional reminder email is sent to all users that did not confirm their read-requests 2 days (configurable) before the deadline.

When read-requests for content items have expired, a notification email is sent to a configurable emailaddress that lists all unread documents and which users did not confirm the item as read in time.

Site-Administrators can view read-statistics (per content-item and site-wide) as well as download a CSV list of all read-requests.

The content rule allows to configure

* the number of days the users have time to read the content (deadline = today + nr-of-days),
* the number of days the reminder is sent out before the deadline,
* and the subject/text of the notification and reminder emails.

This addon depends on `collective.mustread <https://pypi.python.org/pypi/collective.mustread>`_.

To enable must-read actions on non-folderish ATContentTypes include archetypes.zcml (see Installation_).

Setup contentrule
-----------------

Add a new content rule.

Typically you'll use `Read confirmation requested` as the triggering event.

This is fired when a user calls the @@request-read-confirmation view on a content object
which is linked in the `actions` dropdown of content items if the user has the `Request read confirmation` permission.

You can also use other event triggers such as `Object added to this container` or `Workflow state changed` if this makes sense for your use-case.

As action choose `Request read confirmation` and configure it:


Email source
  The email address notifications and reminders get send from (``From:`` header)


Role
  Currently the users who get notified of the read request are defined by a global, acquired or local role you can chose (similiar to `collective.contentrules.mailtorole <https://pypi.python.org/pypi/collective.contentrules.mailtorole>`_

  We also support roles granted to groups and also support looking up users in nested groups

  Maybe we'll add support to alternatively choose groups and users directly in the future.


Acquired Roles
  Also notify users which acquired `Role` from a parent object


Global Roles
  Also notify users which have been granted `Role` in the user or group control panel.


Notification Subject
  Subject of notification email


Notification Message
  Text for the notification email. You can use all the replacement variables of plone.stringinterp and in addition
  the `Content action specific variables`_)


Reminder Subject
  Subject of reminder email


Reminder Message
  Text for the reminder mail.

  If empty, no reminder is sent


Deadline Delay
  Number of days a read request must be confirmed within.
  Will be used to compute the deadline of requests.


Reminder Delay
  Defines how many days before the deadline a reminder email will be sent.


Content action specific variables
'''''''''''''''''''''''''''''''''

This package defines some additional `plone.stringinterp` variables:

mustread_url
  URL of the item that marks the object as read (`/@@mustread-hit`)

  (available in other actions as well).

mustread_fullname
  Full Name of the person the read request is assigned to

  (only available in `Request read confirmation` action).

mustread_deadline
  Localized deadline of the read request

  (only available in `Request read confirmation` action).


Usage
-----

After `setting up the content rule <Setup contentrule>`_ you simply call the `@@request-read-confirmation` view on a content object.

This should be available in the `actions` dropdown of content items for users having the `Request read confirmation` permission.

For the users matching the role-filter defined in the action, a mustread database entry gets created and a notification email is sent out.

You'll see a satusmessage indicating which usernames got notified.

If you want your users to get notified again some days before the deadline, you'll want to `Setup a reminder`_.

You can also `Setup an expiration notification`_ (an email report of missed read requests - which documents have missed requests and which users did not read the document).

There is a csv export (`@@read-statistic-csv`) that lists all mustread records (useful as audit-log or doing advanced spreadsheet-magic).



Setup a reminder
----------------

The view `@@send-read-reminders` searches for (child-)objects with open read requests and notifies
users if today's date equals `deadline of the reminder - notification-delay` (which is specified in the action of the contentrule)

You can use a clockserver (similar to https://github.com/collective/collective.timedevents) or a cronjob (z3c.recipe.usercrontab) for this.

.. ATTENTION::
   make sure to call this view only once a day since the system does not keep records for sent notifications
   and users would get multiple reminder emails.


.. XXX decide for setup and document here

    * https://docs.plone.org/develop/plone/misc/asyncronoustasks.html
    * idea: use secrets as munin.zope does so we need no authentication in the cronjob

Setup an expiration notification
--------------------------------

The view `@@send-expired-notification` lists all documents having open read requests and notifies the portal's admin address.

You can configure the recipients in the registry record `collective.contentrules.mustread.interfaces.IMustReadSettings.expired_recipient`

Make sure to call it only once a day - similar to `Setup a reminder`_


Todos
-----

- Report View for objects - shows mustread records for an object or context including child-objects.

  * A heading for each object, links to mustread report for this object
  * Table listing with sortable columns:

    username, deadline, read-at, status (read, read too late, not read)

- Add cleanup options to report view

  * Remove a single mustread entry
  * Remove all mustread entries

- Report view for users (link usernames in report for object)

  Table listing all objects the user has read, not read, read too late.


- limitation of types that offer must-read actions is done by marker interface
  (see archetypes.zcml) - there might be nicer ways

- implement dexterity behaviour for ICanBeMarkedAsMustRead

- Idea: separate content-action for notifications so we can define multiple notifications with different delays and texts


Translations
------------

This product has been translated into

- English
- German


Installation
------------

Install collective.contentrules.mustread by adding it to your buildout::

    [buildout]

    ...

    eggs =
        collective.contentrules.mustread

    zcml =
        collective.contentrules.mustread-archetypes

.. ATTENTION:: when using atcontenttypes, also include archetypes.zcml or apply marker interface to your types

and then running ``bin/buildout``


Install it via the addon configuration panel (Plone/prefs_install_products_form)

And make sure to configure the Database for `collective.mustread <https://pypi.python.org/pypi/collective.mustread>`_


Contribute
----------

- Issue Tracker: https://github.com/collective/collective.contentrules.mustread/issues
- Source Code: https://github.com/collective/collective.contentrules.mustread

Support
-------

If you are having issues, please let us know `via the issue tracker <https://github.com/collective/collective.contentrules.mustread/issues>`_


License
-------

The project is licensed under the GPLv2.
