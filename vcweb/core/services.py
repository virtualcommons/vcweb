from django.core.cache import cache
from vcweb.core.urls import foursquare_venue_search_url, foursquare_categories_url
import logging
import simplejson as json
import urllib2
logger = logging.getLogger(__name__)

def foursquare_venue_search(latitude=44.3, longitude=37.2, radius=1000, **kwargs):
    request_url = foursquare_venue_search_url(ll='%s,%s' % (latitude, longitude), radius=radius)
    api_request = urllib2.Request(request_url)
    raw_response = urllib2.urlopen(api_request)
    logger.debug("raw response: %s", raw_response)
    response_dict = json.load(raw_response)
    return response_dict['response']['venues']

FOURSQUARE_CATEGORIES_KEY = 'foursquare_categories'

def fetch_foursquare_categories(refresh=False, top_level_category_name=None):
    categories_json_string = cache.get(FOURSQUARE_CATEGORIES_KEY)
    if refresh or categories_json_string is None:
        api_request = urllib2.Request(foursquare_categories_url())
        raw_response = urllib2.urlopen(api_request)
        categories_json_string = raw_response.read()
# default timeout is 1 week in seconds = 604800 seconds
        cache.set(FOURSQUARE_CATEGORIES_KEY, categories_json_string, 604800)
    json_response = json.loads(categories_json_string)
    categories = json_response['response']['categories']
    if top_level_category_name is not None:
        for category in categories:
            if top_level_category_name in category['name']:
                return category
    return categories

