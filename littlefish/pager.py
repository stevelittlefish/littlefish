"""
A simple class to help with paging result sets
"""

import logging

from flask import request, url_for, Markup

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class Pager(object):
    """
    Standard Pager used on back end of website.

    When viewing page 234 of 1000, the following page links will be displayed:
    
    1, 134, 184, 232, 233, 234, 235, 236, 284, 334, 1000
    """

    def __init__(self, page_size, page_number, query, total_items=None):
        """
        :param query: The SQLAlchemy query, or a list of items to be paged
        """
        self.page_size = page_size

        try:
            self.page_number = int(page_number)
        except ValueError:
            self.page_number = 1
        
        if self.page_number < 1:
            self.page_number = 1
        
        self.query = query
        
        # Do the paging here
        if total_items:
            self.total_items = total_items
        elif isinstance(query, list):
            self.total_items = len(query)
        else:
            self.total_items = query.count()

        self.total_pages = (self.total_items - 1) // page_size + 1
        
        if self.page_number > self.total_pages:
            self.page_number = self.total_pages
        
        self.offset = self.page_size * (self.page_number - 1)
        if self.offset < 0:
            self.offset = 1

        self.items = query[self.offset:self.offset + self.page_size]
    
    def get_first_item_from_next_page(self):
        if self.has_next:
            return self.query[self.offset + self.page_size]

        return None
    
    def get_last_item_from_previous_page(self):
        if self.has_prev:
            return self.query[self.offset - 1]

        return None

    @property
    def has_prev(self):
        return self.page_number > 1
    
    @property
    def has_next(self):
        return self.page_number < self.total_pages
    
    @property
    def prev(self):
        return self.page_number - 1
    
    @property
    def next(self):
        return self.page_number + 1
    
    @property
    def page_link_numbers(self):
        pages = [1]
        
        if self.total_pages <= 1:
            return pages
        
        if self.page_number > 103:
            pages.append(self.page_number - 100)
        
        if self.page_number > 53:
            pages.append(self.page_number - 50)
        
        if self.page_number > 3:
            pages.append(self.page_number - 2)
        
        if self.page_number > 2:
            pages.append(self.page_number - 1)
            
        if self.page_number != 1 and self.page_number != self.total_pages:
            pages.append(self.page_number)
            
        if self.page_number < self.total_pages - 1:
            pages.append(self.page_number + 1)

        if self.page_number < self.total_pages - 2:
            pages.append(self.page_number + 2)
        
        if self.page_number < self.total_pages - 52:
            pages.append(self.page_number + 50)

        if self.page_number < self.total_pages - 102:
            pages.append(self.page_number + 100)
        
        pages.append(self.total_pages)
        return pages

    @property
    def empty(self):
        return self.total_pages == 0
    
    def get_full_page_url(self, page_number, scheme=None):
        """Get the full, external URL for this page, optinally with the passed in URL scheme"""
        args = dict(
            request.view_args,
            _external=True,
        )

        if scheme is not None:
            args['_scheme'] = scheme
        
        if page_number != 1:
            args['page'] = page_number

        return url_for(request.endpoint, **args)

    def get_canonical_url(self, scheme=None):
        """Get the canonical page URL"""
        return self.get_full_page_url(self.page_number, scheme=scheme)

    def render_prev_next_links(self, scheme=None):
        """Render the rel=prev and rel=next links to a Markup object for injection into a template"""
        output = ''

        if self.has_prev:
            output += '<link rel="prev" href="{}" />\n'.format(self.get_full_page_url(self.prev, scheme=scheme))
        
        if self.has_next:
            output += '<link rel="next" href="{}" />\n'.format(self.get_full_page_url(self.next, scheme=scheme))

        return Markup(output)

    def render_canonical_link(self, scheme=None):
        """Render the rel=canonical link to a Markup object for injection into a template"""
        return Markup('<link rel="canonical" href="{}" />'.format(self.get_canonical_url(scheme=scheme)))

    def render_seo_links(self, scheme=None):
        """Render the rel=canonical, rel=prev and rel=next links to a Markup object for injection into a template"""
        out = self.render_prev_next_links(scheme=scheme)

        if self.total_pages == 1:
            out += self.render_canonical_link(scheme=scheme)

        return out

    @property
    def first_item_number(self):
        """
        :return: The first "item number", used when displaying messages to the user
        like "Displaying items 1 to 10 of 123" - in this example 1 would be returned
        """
        return self.offset + 1

    @property
    def last_item_number(self):
        """
        :return: The last "item number", used when displaying messages to the user
        like "Displaying items 1 to 10 of 123" - in this example 10 would be returned
        """
        n = self.first_item_number + self.page_size - 1
        if n > self.total_items:
            return self.total_items
        return n


class SimplePager(Pager):
    """
    Uses the same api as above, but displays a range of continuous page numbers.
    If you are on page 6 of 10 the following page numbers will be displayed:

    1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    """

    def __init__(self, page_size, page_number, query, max_pages=12):
        """
        :param max_pages: The maximum number of page links to display
        """
        super().__init__(page_size, page_number, query)

        self.max_pages = max_pages
    
    @property
    def page_link_numbers(self):
        start = self.page_number - self.max_pages // 2 + 1
        if start < 1:
            start = 1

        end = start + self.max_pages - 1
        if end > self.total_pages:
            end = self.total_pages

            if start > 1:
                start = end - self.max_pages + 1

        return range(start, end + 1)


class InMemoryPager(Pager):
    """
    Use this when you absolutely have to load everything and page in memory.  You can access
    all of the items through the all_items attribute after initialising this object
    """
    def __init__(self, page_size, page_number, query):
        self.page_size = page_size

        try:
            self.page_number = int(page_number)
        except ValueError:
            self.page_number = 1
        
        if self.page_number < 1:
            self.page_number = 1
        
        self.query = query
        # Load everything
        self.all_items = query.all()
        
        # Do the paging here
        self.total_items = len(self.all_items)
        self.total_pages = (self.total_items - 1) // page_size + 1
        
        if self.page_number > self.total_pages:
            self.page_number = self.total_pages
        
        self.offset = self.page_size * (self.page_number - 1)
        if self.offset < 0:
            self.offset = 1

        self.items = self.all_items[self.offset:self.offset + self.page_size]


class ViewAllPager(object):
    """
    Uses the same API as pager, but lists all items on a single page.  This is to allow
    easy implementation of a "view all" function on a listing page
    """
    def __init__(self, query):
        self.page_number = 1

        self.query = query

        # Do the paging here
        self.total_items = query.count()
        self.page_size = self.total_items
        self.total_pages = 1

        self.offset = 0

        self.items = query.all()

    @property
    def has_prev(self):
        return False

    @property
    def has_next(self):
        return False

    @property
    def prev(self):
        return self.page_number - 1

    @property
    def next(self):
        return self.page_number + 1

    @property
    def page_link_numbers(self):
        return [1]

