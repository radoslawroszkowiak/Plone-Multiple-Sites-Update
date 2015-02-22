# -*- coding: utf-8 -*-
"""
Python script used to update many Plone Sites
within one Plone application at once.
Can be ran only as a Plone instance's script. Available features are:
    - reinstalling the products (matched by exact name or regexp)
    - updating the JS and CSS compositions
    - rebuilding the portal_catalog
    - updating workflow settings

Example usage:
$ ./bin/instance run multi_sites_update_tool.py -u reinstall,css -p my.product)

Author: Radosław Roszkowiak <radoslaw@roszkowiak.pl>
"""

import argparse
import datetime
import functools
import logging
import re
import timeit
import transaction

from zope.component.hooks import setSite

# setting up the logger

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)


def add_logger_file_handler():
    """
    Adds File Handler to the logger.
    """
    global logger
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M')
    log_filename = 'site_update_{}.log'.format(timestamp)
    fh = logging.FileHandler(
        log_filename,
        mode='w',
        encoding="utf-8"
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.info('Created Log file: %s' % log_filename)
    logger.addHandler(fh)

############


def log_execution(func):
    """
    The time measuring and logging decorator.
    """
    @functools.wraps(func)
    def _inner(self, *args, **kwargs):
        """
        Proxy, inner function of the log_execution decorator.
        """
        try:
            start = timeit.default_timer()
            result = func(self, *args, **kwargs)
            elapsed_time = timeit.default_timer() - start
            logger.info(
                '%s - executed for Plone Site: "%s" in %s seconds.' % (
                    func.__name__, self.site.id, str(elapsed_time))
            )
            return result
        except Exception as exc:
            logger.error(
                'An error occurred while executing "%s" on '
                'a "%s" Plone Site: "%s"' % (
                    func.__name__, self.site.id, exc.message
                ))
            raise exc
    return _inner


# parsing the command line arguments

ARG_FUNCTION_MAP = {
    'reinstall': 'reinstall_products',
    'javascript': 'save_javascripts',
    'css': 'save_css',
    'workflow': 'update_workflow',
    'catalog': 'rebuild_catalog',
}
ARG_FUNCTION_MAP['all'] = ','.join(ARG_FUNCTION_MAP.values())


def get_parameters():
    """
    Returns the command line parameters used to run the script as a dictionary.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--tools', dest="tools", default="all", type=str,
        help="Enter the elements to be updated (separated by coma). "
             "Available forms are: %s" % ', '.join(ARG_FUNCTION_MAP.keys())
    )
    parser.add_argument(
        '-p', '--products', dest="products", default='', type=str,
        help="Choose the product IDs to be reinstalled (separated by coma)."
    )
    parser.add_argument(
        '-r', '--products-regex', dest="products_regex", default='', type=str,
        help="Enter the python regexp to match multiple product IDs."
    )
    parser.add_argument(
        '-n', '--no-log', dest="no_log", action="store_true",
        help="Use this option if you don't want to have the log file created."
    )
    parser.add_argument('-c')  # Passed by the Plone instance

    update_args = parser.parse_args()
    chosen_products_args = getattr(update_args, 'products', '')
    chosen_products = chosen_products_args.split(',')
    result = {
        'update_args': update_args,
        'no_log_file': getattr(update_args, 'no_log'),
        'elements_to_update': getattr(update_args, 'tools', ''),
        'chosen_products_args': chosen_products_args,
        'chosen_products': chosen_products,
        'chosen_products_regex': getattr(
            update_args, 'products_regex', None),
    }
    if result['chosen_products_regex']:
        result['compiled_products_regex'] = re.compile(chosen_products_regex)
    return result

###############


def get_sites():
    """
    Returns the list of all the application's Plone Sites.
    """
    sites = []
    for _, obj in app.items():
        try:
            if obj.portal_type == 'Plone Site':
                sites.append(obj)
        except AttributeError:
            continue
    return sites


class SiteUpdater(object):
    """
    Plone single site update class.
    """

    def __init__(self, site, **kwargs):
        self.site = site
        self.elements_to_update = kwargs['elements_to_update']
        self.chosen_products = kwargs['chosen_products']
        self.chosen_products_regex = kwargs['chosen_products_regex']
        self.compiled_products_regex = kwargs['compiled_products_regex']

    def __call__(self):
        method_list = self.get_method_names_to_run()
        logger.info('Actions that will be taken for the "%s" site: %s.\n' % (
            self.site.id, ', '.join(sorted(method_list))
        ))
        for meth_name in method_list:
            getattr(self, meth_name)()
        transaction.commit()

    def get_method_names_to_run(self):
        """
        Returns the unique list of methods of the SiteUpdate class.
        """
        elements = self.elements_to_update.split(',')
        method_set = set()
        for element in elements:
            methods = ARG_FUNCTION_MAP[element]
            method_set.update(methods.split(','))
        return tuple(method_set)

    @log_execution
    def reinstall_products(self):
        """
        Reinstalls the given products within one Plone Site.
        """
        product_ids = self.get_products_to_reinstall()
        self.site.portal_quickinstaller.reinstallProducts(product_ids)
        logger.info('Reinstalled Products: %s' % ', '.join(product_ids))

    def get_products_to_reinstall(self):
        """
        Returns the IDs of the products to reinstall.
        """
        installed_products = \
            self.site.portal_quickinstaller.listInstalledProducts()

        installed_ids = []
        for product in installed_products:
            if product['status'] == 'installed':
                installed_ids.append(product['id'])

        matched_product_ids = set()
        for product_id in self.chosen_products:
            if product_id in installed_ids:
                matched_product_ids.add(product_id)

        if self.chosen_products_regex:
            for product_id in installed_ids:
                if self.compiled_products_regex.match(product_id):
                    matched_product_ids.add(product_id)
        return tuple(matched_product_ids)

    @log_execution
    def rebuild_catalog(self):
        """
        Rebuilds the portal catalog.
        """
        self.site.portal_catalog.manage_catalogRebuild()

    @log_execution
    def save_javascripts(self):
        """
        Saves the javascripts for all the sites.
        """
        self.site.portal_javascripts.cookResources()

    @log_execution
    def save_css(self):
        """
        Saves the stylesheet for all the sites.
        """
        self.site.portal_css.cookResources()

    @log_execution
    def update_workflow(self):
        """
        Updates the workflows settings.
        """
        self.site.portal_workflow.updateRoleMappings()


def trigger_update():
    """
    Main, starting method of the Multiple Plone Site Update Tool.
    """
    parameters = get_parameters()
    if not parameters['no_log_file']:
        add_logger_file_handler()
    sites = get_sites()
    for site in sites:
        logger.info('Starting update of the site: "%s"' % site.id)
        setSite(site)
        updater = SiteUpdater(site, **parameters)
        updater()
    logger.info('All done, Milord!')

if __name__ == '__main__':
    trigger_update()
