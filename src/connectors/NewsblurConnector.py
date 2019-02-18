import json

import requests
import requests.exceptions
import rollbar
from bs4 import BeautifulSoup
from datadog import statsd
from ddtrace import patch
from ddtrace import tracer
from time import sleep

from utility import nb_logging

patch(requests=True)

logger = nb_logging.setup_logger('NewsblurConnector')


class NewsblurConnector:

    def __init__(self, config, username, password):
        self.cookies = None
        self.config = config
        self.verify = config.get('VERIFY')
        self.nb_endpoint = config.get('NB_ENDPOINT')

        self.credentials = {'username': username, 'password': password}

    @statsd.timed('nb.NewsblurConnector.login')
    def login(self):
        """ log in and save cookies """
        r = requests.post(self.nb_endpoint + '/api/login', self.credentials)
        statsd.increment('nb.http_requests.post')
        self.cookies = r.cookies

    @statsd.timed('nb.NewsblurConnector.get_nb_hash_list')
    def get_nb_hash_list(self):
        """ get a list of story identifiers (hashes) from NewsBlur """

	hashes_req = requests.Request('GET', self.nb_endpoint + '/reader/starred_story_hashes',
				      cookies=self.cookies)
	hashes = self.request_with_backoff(hashes_req)

        try:
            return hashes.json()['starred_story_hashes']
        except ValueError as e:
            rollbar.report_exc_info()
            msg = 'Failed to decode JSON'
            logger.error(msg)
            logger.error(e)
            logger.debug(hashes)
            statsd.event(msg, e.message, alert_type='error')
	return []

    @statsd.timed('nb.NewsblurConnector.get_story_list')
    def get_story_list(self, batch):
        """ get a list of stories corresponding to a list of hashes """
        req_str = self.nb_endpoint + '/reader/starred_stories?'
        for a_hash in batch:
            req_str += 'h=' + a_hash + '&'
        stories = {}
	stories_req = requests.Request('GET', req_str, cookies=self.cookies)
        try:
            stories = self.request_with_backoff(stories_req)
        except requests.exceptions.ConnectionError as e:
            rollbar.report_exc_info()
            msg = 'Failed to get stories'
            logger.error(msg)
            logger.debug('Request string: %s', req_str)
            logger.error(e)
            statsd.event(msg, e.message, alert_type='error')
            logger.debug(stories.text)
        statsd.increment('nb.http_requests.get')
        story_list = []
        try:
            story_list = json.loads(stories.text)['stories']
        except ValueError as e:
            rollbar.report_exc_info()
            msg = 'Failed to parse stories response'
            logger.error(msg)
            logger.error(e)
            statsd.event(msg, e.message, alert_type='error')
            logger.debug(stories.text)
        return story_list

    @statsd.timed('nb.NewsblurConnector.get_comment_count')
    def get_comment_count(self, hnurl):
        req = requests.Request('GET', hnurl, cookies=self.cookies)
        resp = self.request_with_backoff(req)
        if resp is None:
            return None
        story_text = self.request_with_backoff(req).text
        return self.parse_story(story_text)

    # Parse HN story to find how many comments there are
    @statsd.timed('nb.NewsblurConnector.parse_story')
    def parse_story(self, content):
        soup = BeautifulSoup(content, "html.parser")
        comment_count = len(soup.find_all("div", {"class": "comment"}))
        return comment_count

    @statsd.timed('nb.NewsblurConnector.check_if_starred')
    def check_if_starred(self, story_hash):
	starred_req = requests.Request('GET', self.nb_endpoint + '/reader/starred_story_hashes', 
                                       cookies=self.cookies)
        hashes = self.request_with_backoff(starred_req)
        statsd.increment('nb.http_requests.get')
        hashlist = hashes.json()['starred_story_hashes']

        return bool(story_hash in hashlist)

    @statsd.timed('nb.NewsblurConnector.remove_star_with_backoff')
    def remove_star_with_backoff(self, story_hash):
        unstar_url = self.nb_endpoint + '/reader/mark_story_hash_as_unstarred'
        req = requests.Request('POST', unstar_url, params={'story_hash': story_hash},
                               cookies=self.cookies)
        return bool(self.request_with_backoff(req) is not None)

    @statsd.timed('nb.NewsblurConnector.request_with_backoff')
    def request_with_backoff(self, req):
        sleep(float(self.config.get('POLITE_WAIT')))
        backoff = self.config.get('BACKOFF_START')
        session = requests.Session()
        prepared_req = session.prepare_request(req)
        try:
            resp = session.send(prepared_req)
            statsd.increment('nb.http_requests.count')
            statsd.increment('nb.http_requests.status_' + str(resp.status_code))
            while resp.status_code != 200:
                if resp.status_code in [429, 500, 502, 503, 504]:  # exponential backoff
                    logger.info(
                        "Request for %s returned %s response", req.url, resp.status_code)
                    if backoff < self.config.get('BACKOFF_MAX'):
                        logger.info("Backing off %s seconds", backoff)
                        sleep(backoff)
                        backoff = backoff * self.config.get('BACKOFF_FACTOR')
                        resp = session.send(prepared_req)
                        statsd.increment('nb.http_requests.count')
            		statsd.increment('nb.http_requests.status_' + str(resp.status_code))
                    else:
                        logger.warn("Giving up after %s seconds for %s", backoff, req.url)
                        return None
                elif resp.status_code in [403, 520]:
                    logger.warn("%s response, skipping %s and waiting %ss", resp.status_code,
                                req.url, self.config.get('BACKOFF_START'))
		    sleep(self.config.get('BACKOFF_START'))
                    return None
                else:
                    logger.error("Request for %s returned unhandled %s response",
                                 req.url, resp.status_code)
                    raise requests.exceptions.RequestException()
            return resp
        except requests.exceptions.RequestException as e:
            rollbar.report_exc_info()
            logger.info("url is: %s", req.url)
            logger.error(e)
            return None
