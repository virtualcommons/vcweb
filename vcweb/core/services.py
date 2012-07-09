from django.core.cache import cache
from vcweb.core.models import ExperimentMetadata
from vcweb.core.urls import foursquare_venue_search_url, foursquare_categories_url
import logging
import simplejson as json
import urllib2
logger = logging.getLogger(__name__)

class ExperimentService(object):
    namespace = None
    def get_experiment_metadata(self):
        return ExperimentMetadata.objects.get(namespace=self.namespace)

def foursquare_venue_search(latitude=33.41, longitude=-111.9, radius=30, **kwargs):
    if latitude is None or longitude is None:
        logger.warning('no lat/long specified, aborting')
        return []
    request_url = foursquare_venue_search_url(ll='%s,%s' % (latitude, longitude), radius=radius, **kwargs)
    api_request = urllib2.Request(request_url)
    raw_response = urllib2.urlopen(api_request)
    logger.debug("raw response: %s", raw_response)
    response_dict = json.load(raw_response)
    return response_dict['response']['venues']

FOURSQUARE_CATEGORIES_KEY = 'foursquare_categories'

def fetch_foursquare_categories(refresh=False, parent_category_name=None):
    categories_json_string = cache.get(FOURSQUARE_CATEGORIES_KEY)
    if refresh or categories_json_string is None:
        api_request = urllib2.Request(foursquare_categories_url())
        raw_response = urllib2.urlopen(api_request)
        categories_json_string = raw_response.read()
# default timeout is 1 week in seconds = 604800 seconds
        cache.set(FOURSQUARE_CATEGORIES_KEY, categories_json_string, 604800)
    json_response = json.loads(categories_json_string)
    categories = json_response['response']['categories']
    if parent_category_name is not None:
        for category in categories:
            if parent_category_name in category['name']:
                return category
    return categories

