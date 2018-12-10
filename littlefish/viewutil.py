"""
Utility functions for creating flask views
"""

import logging
import traceback

from flask import current_app, render_template

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


def internal_error(exception, template_path, is_admin, db=None):
    """
    Render an "internal error" page.  The following variables will be populated when rendering the
    template:
    
    title: The page title
    message: The body of the error message to display to the user
    preformat: Boolean stating whether to wrap the error message in a pre

    As well as rendering the error message to the user, this will also log the exception

    :param exception: The exception that was caught
    :param template_path: The template to render (i.e. "main/error.html")
    :param is_admin: Can the logged in user always view detailed error reports?
    :param db: The Flask-SQLAlchemy instance

    :return: Flask Response
    """
    if db:
        try:
            db.session.rollback()
        except:  # noqa: E722
            pass

    title = str(exception)
    message = traceback.format_exc()
    preformat = True
 
    log.error('Exception caught: {}\n{}'.format(title, message))

    if current_app.config.get('TEST_MODE'):
        show_detailed_error = True
        message = 'Note: You are seeing this error message because the server is in test mode.\n\n{}'.format(message)
    elif is_admin:
        show_detailed_error = True
        message = 'Note: You are seeing this error message because you are a member of staff.\n\n{}'.format(message)
    else:
        title = '500 Internal Server Error'
        message = 'Something went wrong while processing your request.'
        preformat = False
        show_detailed_error = False
    
    try:
        return render_template(template_path, title=title, message=message, preformat=preformat,
                               exception=exception, is_admin=is_admin,
                               show_detailed_error=show_detailed_error), 500
    except:  # noqa: E722
        log.exception('Error rendering error page!')
        return '500 Internal Server Error', 500
