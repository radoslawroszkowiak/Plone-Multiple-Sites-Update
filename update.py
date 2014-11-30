# -*-coding=utf-8 -*-
import logging
import re

from Products.GenericSetup.tool import SetupTool


logger = logging.getLogger(__name__)


def getAllSites():
    """
    This method returns of all the top level sites (not the nested ones).
    """
    sites = []
    for item in app.items():
        try:
            p_type = item[0].portal_type
            if p_type == u'Plone Site':
                sites.append(item[0])
        except AttributeError:
            pass
    return sites

def getSetupTool(site):
    context_id = site.id
    setup_tool = SetupTool(context_id)
    return setup_tool

def getAvailableImportSteps(setup_tool):
    return setup_tool.getSortedImportSteps()

def saveJsAndCss(site, js=True, css=True):
    """
    The method saves JS and CSS
    """
    if js is True:
        site.portal_javascripts.cookResources()
    if css is True:
        site.portal_css.cookResources()

def clearAndRebuildCatalog(site):
    """
    Clears and rebuilds portal catalog.
    """
    return site.catalog.clearFindAndRebuild()

def getDesiredProfiles(site, pattern, search_scope='id'):
    setup_tool = site.portal_setup
    all_profiles = setup_tool.listProfileInfo()
    desired_profile_ids = []
    for profile in all_profiles:
        if re.match(pattern, profile[search_scope.lower()]):
            desired_profile_ids.append(profile['id'])
    return desired_profiles_ids

def importAllStepsFromProfiles(site, profile_ids):
    for profile_id in profile_ids
        setup_tool.runAllImportStepsFromProfile(profile_id)


if __name__ == '__main__':
    sites = getAllSites()
    for site in sites:
        profiles = getDesiredProfiles(site, '.+decernis.+')
        importAllStepsFromProfiles(site, profile_ids)
        saveJsAndCss(site)
        clearAndRebuildCatalog(site)
