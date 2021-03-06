#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Rob Rennison'
SITENAME = u"Rob Rennison's Blog"
SITEURL = 'http://www.robren.net'
#SITEURL = ''

THEME = '../pelican-themes/pelican-bootstrap3/'

# Found out the hard way that this poorly documented step is 
# required to make some of the themes, including bootstrap3 work
JINJA_EXTENSIONS = ['jinja2.ext.i18n']

# The i18n_subsites is some "magic" needed to ensure that the fragile themes work
# without this, some "err undefined..." occurs when making the output
PLUGINS = ["i18n_subsites","extract_toc"]
PLUGIN_PATHS = ["../pelican-plugins/"]


PYGMENTS_STYLE = 'solarizedlight'
PATH = 'content'

## Theme configuration
BOOTSTRAP_THEME = 'readable'
DISPLAY_BREADCRUMBS = True
SHOW_DATE_MODIFIED = True


# Added to customize
# tell pelican where your custom.css file is in your content folder
STATIC_PATHS = ['extras/custom.css']
# tell pelican where it should copy that file to in your output folder
EXTRA_PATH_METADATA = {
'extras/custom.css': {'path':'static/custom.css'}
}
# tell the pelican-bootstrap-3 theme where to find the custom.css file in your output folder
CUSTOM_CSS = 'static/custom.css'

TIMEZONE = 'EST'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         )

# Social widget
SOCIAL = (('Github', 'https://github.com/robren'),
          )

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

# Would like to have used this TOC but it broke extension but it 
# broke the code text boxes, sigh!
#MD_EXTENSIONS = ['toc']
#MARKDOWN = {
#        'extension_configs' : {
#            'markdown.extensions.toc' : {},
#            'markdown.extensions.codehilite':{}
#        }
#}
#from markdown.extensions.toc import TocExtension
#from markdown.extensions.codehilite import CodeHiliteExtension

