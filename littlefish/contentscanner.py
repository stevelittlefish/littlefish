"""
"Scanner" to scan through front end content and:

- Generate a sitemap
- Check for missing meta tags
- Check for missing alt tags

Example Usage:

    BLUEPRINTS = ['main']
    SKIP = ['main.super_secret_test_stuff', 'main.site_map']

    scanner = ContentScanner(app, blueprints=BLUEPRINTS, skip=SKIP, scheme='https')
    
    # Add some argument functions for dynamic content
    @scanner.args_function('main.view_product_details')
    def view_product_details_args():
        products = Product.query.all()
        for product in products:
            yield {'url_name': product.url_name}

    @scanner.args_function('main.view_post')
    def view_post_args():
        news_posts = NewsPost.query.all()
        for post in news_posts:
            yield {'nice_name': post.nice_name}
    
    # Get the results
    results = scanner.scan(True, True, True, True, True)
"""

import logging
import re
import datetime
import urllib.parse

from werkzeug.wrappers import BaseResponse
from werkzeug.routing import parse_rule, BuildError
from flask import url_for
from bs4 import BeautifulSoup
import titlecase

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class ViewRaisedException(Exception):
    """
    The view function raised an unhandled exception when it was run
    """
    pass


class ConfigurationError(Exception):
    """
    There is an error in the scanner configuration
    """
    pass


class InvalidViewArguments(Exception):
    """
    The arguments passed into the url generator were incorrect
    """
    pass


class HtmlParsingError(Exception):
    """
    There was a problem parsing the HTML when inspecting the content
    """
    pass


class ScannerResult:
    def __init__(self, endpoint, args, url=None, status_code=None, mime_type=None, title=None,
                 meta_description=None, missing_alt_tags=[], last_modified=None):
        self.endpoint = endpoint
        self.args = args
        self.url = url
        self.status_code = status_code
        self.mime_type = mime_type
        self.title = title
        self.meta_description = meta_description
        self.missing_alt_tags = missing_alt_tags
        if last_modified:
            self.last_modified = last_modified
        else:
            self.last_modified = datetime.datetime.utcnow()
    
    @property
    def is_html(self):
        return 'html' in self.mime_type

    @property
    def needs_meta_description(self):
        if not self.is_html:
            return False
        
        if self.status_code != 200:
            return False

        return self.meta_description is None or len(self.meta_description) < 10


class SiteMapEntry(object):
    def __init__(self, url, modified, change_freq, priority, title):
        self.url = url
        self.modified = modified
        self.change_freq = change_freq
        self.priority = priority
        self.title = title


class ContentScanner:
    def __init__(self, app, blueprints=None, skip=[], scheme='http', server_name=None,
                 ignore_images_containing=[]):
        """
        :param app: The flask app
        :param blueprints: List of blueprints to scan, or None to scan all of them
        :param skip: List of endpoints to skip.  The list can contain regular expressions and strings
        :param scheme: http or https - for url generation
        :param server_name: The server name used for url generation.  If this is not specified we will attempt
                            to extract this from the SERVER_NAME variable in app.config
        :param ignore_images_containing: When scanning images, images with sources which contain
                                         any of the strings in this list will be ignored
        """
        self.app = app
        self.blueprints = blueprints
        self.skip_strings = [s for s in skip if isinstance(s, str)]
        self.skip_regexps = [r for r in skip if hasattr(r, 'search')]
        assert len(self.skip_strings) + len(self.skip_regexps) == len(skip), \
            'Skip list must only contain strings and regular expressions'
        self.scheme = scheme
        # Maps endpoint -> function to get arguments
        self.endpoint_argument_functions = {}
        if server_name is None:
            if not app.config.get('SERVER_NAME'):
                raise ValueError('No server name passed in and no SERVER_NAME specified in flask config')

            self.server_name = app.config['SERVER_NAME']
        else:
            self.server_name = server_name
        self.ignore_images_containing = ignore_images_containing

    def args_function(self, endpoint):
        """
        Decorator.

        This function must yield dicts with the kwargs that need to be passed into the view function

        :param endpoint: The endpoint that we are defining args for
        """
        if endpoint in self.endpoint_argument_functions:
            raise ConfigurationError('Added multiple arg functions for enpoint: {}'.format(endpoint))

        def decorator(f):
            self.endpoint_argument_functions[endpoint] = f
            return f

        return decorator

    def scan(self, generate_urls=False, inspect_content=False, inspect_meta_description=False,
             inspect_alt_tags=False, inspect_title=False):
        """
        Scan through the content.

        :param generate_urls: Whether or not to include urls in the result set
        :param inspect_content: If True, this will scan through for mime types and status codes. If any
                                of the other inspect_ parameters are set to True this will happen
                                automatically
        :param inspect_meta_description: Whether or not to collect meta description tags
        :param inspect_alt_tags: Whether or not to compile a list of img tags with no alt tags for each
                                 endpoint
        :param inspect_title: Whether or not to extract titles from the html
        """

        if not inspect_content:
            inspect_content = inspect_meta_description or inspect_alt_tags or inspect_title
        
        results = []

        for rule in self.app.url_map.iter_rules():
            endpoint_parts = rule.endpoint.split('.')
            blueprint_name = endpoint_parts[0] if len(endpoint_parts) > 1 else None

            if self.blueprints is not None and blueprint_name not in self.blueprints:
                log.debug('Skipping rule {} due to blueprint ({})'.format(
                    rule, blueprint_name
                ))
                continue
            
            skip = False

            if rule.endpoint in self.skip_strings:
                skip = True
            else:
                for regexp in self.skip_regexps:
                    if regexp.search(rule.endpoint):
                        skip = True
                        break

            if skip:
                log.debug('Skipping rule {}'.format(rule))
                continue

            log.debug('[{}] {} {} {}'.format(
                blueprint_name, rule.endpoint, rule.methods, rule
            ))

            results += self.scan_rule(rule, generate_urls, inspect_content, inspect_meta_description,
                                      inspect_alt_tags, inspect_title)

        return results

    def scan_rule(self, rule, generate_urls, inspect_content, inspect_meta_description, inspect_alt_tags,
                  inspect_title):

        inspect_html = inspect_meta_description or inspect_alt_tags or inspect_title

        view_function = self.app.view_functions[rule.endpoint]
        
        # Count up the number of arguments
        num_args = 0
        for converter, arguments, variable in parse_rule(str(rule)):
            if converter:
                num_args += 1

        if num_args > 0:
            # The function has args!
            args_function = self.endpoint_argument_functions.get(rule.endpoint)
            if not args_function:
                raise ConfigurationError('No args function for endpoint "{}". You need to use the '
                                         'args_function decorator to add a function that yields all of the '
                                         'combinations of arguments for this function'.format(rule.endpoint))
        else:
            def args_function():
                return [{}]
        
        results = []
        
        base_url = '{}://{}'.format(self.scheme, self.server_name)
        for kwargs in args_function():
            # We need the url_path
            full_url = url_for(rule.endpoint, **kwargs)
            parsed_url = urllib.parse.urlparse(full_url)
            url_path = parsed_url.path

            log.debug(' > args: {}'.format(kwargs))
            with self.app.test_request_context(url_path, base_url=base_url):
                result = ScannerResult(rule.endpoint, kwargs)
                
                if generate_urls:
                    try:
                        result.url = url_for(rule.endpoint, _external=True, _scheme=self.scheme, **kwargs)
                    except BuildError as e:
                        raise InvalidViewArguments('The arguments {} are not valid for endpoint {}'
                                                   .format(kwargs, rule.endpoint)) from e

                if inspect_content:
                    try:
                        response = view_function(**kwargs)
                    except Exception as e:
                        if kwargs:
                            error_message = 'Endpoint {} with args {} raised an exception'.format(
                                rule.endpoint, kwargs
                            )
                        else:
                            error_message = 'Endpoint {} raised an exception'.format(
                                rule.endpoint
                            )

                        raise ViewRaisedException(error_message) from e

                    if isinstance(response, str):
                        response_text = response
                        status_code = 200
                        mimetype = 'text/html'
                    elif isinstance(response, BaseResponse):
                        status_code = response.status_code
                        mimetype = response.mimetype
                        response_text = ''
                        if mimetype.startswith('text/'):
                            for response_part in response.response:
                                response_text += response_part.decode('utf-8')
                        if response.last_modified:
                            result.last_modified = response.last_modified
                    elif isinstance(response, tuple):
                        if len(response) != 2:
                            raise ValueError('Unhandled responstype: tuple with length {}'
                                             .format(len(response)))
                        response_text, status_code = response
                        if not isinstance(response_text, str):
                            raise ValueError('Unhandled response_type: tuple with non str as first item')
                        mimetype = 'text/html'
                    else:
                        raise ValueError('Unhandled response type: {}'.format(type(response)))
                    
                    truncated_response_text = response_text.replace('\n', '')[:30]
                    log.debug('{} ({}) {}...'.format(
                        status_code, mimetype, truncated_response_text
                    ))
                    result.status_code = status_code
                    result.mime_type = mimetype

                    if inspect_html and 'html' in result.mime_type:
                        soup = BeautifulSoup(response_text, 'html.parser')

                        if inspect_meta_description:
                            head = soup.find('head')
                            if head:
                                meta_desc_tags = head.find_all('meta', attrs={"name": re.compile(r"^\s*description\s*$", re.I)})
                                if len(meta_desc_tags) > 1:
                                    all_tags = '; '.join([str(t) for t in meta_desc_tags])
                                    raise HtmlParsingError(
                                        'Found multiple description tags for endpoint {}: {}'
                                        .format(rule.endpoint, all_tags)
                                    )
                                elif len(meta_desc_tags) == 1:
                                    result.meta_description = meta_desc_tags[0]['content']

                        if inspect_alt_tags:
                            missing_alt_tags = []
                            all_images = soup.find_all('img')
                            for image in all_images:
                                # Sometimes we may need to skip some images
                                if self.ignore_images_containing:
                                    src = image.get('src')
                                    skip = False
                                    for image_path_search in self.ignore_images_containing:
                                        if src and image_path_search in src:
                                            skip = True
                                            break
                                    if skip:
                                        continue

                                alt = image.get('alt')
                                if alt is None or not alt.strip():
                                    missing_alt_tags.append(str(image))
                            result.missing_alt_tags = missing_alt_tags

                        if inspect_title:
                            head = soup.find('head')
                            if head:
                                title_tag = head.find('title')
                                if title_tag:
                                    result.title = title_tag.text.strip()

                results.append(result)

        return results

    def scan_for_sitemap(self, priority_map={}, change_freq='daily', default_priority='0.5',
                         inspect_content=False, inspect_title=False):
        # Scan through the pages and return a list of sitemap entries
        results = self.scan(generate_urls=True, inspect_content=inspect_content, inspect_title=inspect_title)
        sitemap = []

        for result in results:
            if inspect_content:
                if result.status_code != 200:
                    continue

                if not result.is_html:
                    continue

            # priority_map maps endpoint -> priority
            priority = priority_map.get(result.endpoint, default_priority)
            title = result.title
            if not title:
                # Make one up!
                title = titlecase.titlecase(result.endpoint.split('.')[1].replace('_', ' '))

            sitemap.append(SiteMapEntry(result.url, result.last_modified, change_freq, priority, title))

        return sitemap

