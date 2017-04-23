# -*- coding: utf-8 -*-
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import collective.contentrules.mustread


class CollectiveContentrulesMustreadLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=collective.contentrules.mustread)
        self.loadZCML(package=collective.contentrules.mustread,
                      name='archetypes.zcml')

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'collective.contentrules.mustread:default')


COLLECTIVE_CONTENTRULES_MUSTREAD_FIXTURE = CollectiveContentrulesMustreadLayer()  # noqa


COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_CONTENTRULES_MUSTREAD_FIXTURE,),
    name='CollectiveContentrulesMustreadLayer:IntegrationTesting'
)


COLLECTIVE_CONTENTRULES_MUSTREAD_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(COLLECTIVE_CONTENTRULES_MUSTREAD_FIXTURE,),
    name='CollectiveContentrulesMustreadLayer:FunctionalTesting'
)


COLLECTIVE_CONTENTRULES_MUSTREAD_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        COLLECTIVE_CONTENTRULES_MUSTREAD_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='CollectiveContentrulesMustreadLayer:AcceptanceTesting'
)
