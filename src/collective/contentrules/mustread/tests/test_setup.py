# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.contentrules.mustread.testing import COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING  # noqa
from plone import api

import unittest


class TestSetup(unittest.TestCase):
    """Test that collective.contentrules.mustread is properly installed."""

    layer = COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if collective.contentrules.mustread is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'collective.contentrules.mustread'))

    def test_browserlayer(self):
        """Test that ICollectiveContentrulesMustreadLayer is registered."""
        from collective.contentrules.mustread.interfaces import (
            ICollectiveContentrulesMustreadLayer)
        from plone.browserlayer import utils
        self.assertIn(
            ICollectiveContentrulesMustreadLayer,
            utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = COLLECTIVE_CONTENTRULES_MUSTREAD_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['collective.contentrules.mustread'])

    def test_product_uninstalled(self):
        """Test if collective.contentrules.mustread is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'collective.contentrules.mustread'))

    def test_browserlayer_removed(self):
        """Test that ICollectiveContentrulesMustreadLayer is removed."""
        from collective.contentrules.mustread.interfaces import \
            ICollectiveContentrulesMustreadLayer
        from plone.browserlayer import utils
        self.assertNotIn(
           ICollectiveContentrulesMustreadLayer,
           utils.registered_layers())
