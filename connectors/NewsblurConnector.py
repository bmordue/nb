# from ddtrace import patch
# patch(requests=True)

import json
import requests
import requests.exceptions
from datadog import statsd
from bs4 import BeautifulSoup

from nb_exceptions.BlacklistedError import BlacklistedError
from utility import constants
from utility import nb_logging

from time import sleep

import rollbar

logger = nb_logging.setup_logger('NewsblurConnector')


class NewsblurConnector:
    def __init__(self):
        self.cookies = None

    def connect(self):
        """ make connection """
        r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS,
                          verify=constants.VERIFY)
        statsd.increment('nb.http_requests.post')
        self.cookies = r.cookies

    @statsd.timed('nb.NewsblurConnector.get_nb_hash_list')
    def get_nb_hash_list(self):
        """ get a list of story identifiers (hashes) from NewsBlur """
        hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                              cookies=self.cookies, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        return hashes.json()['starred_story_hashes']

    @statsd.timed('nb.NewsblurConnector.get_story_list')
    def get_story_list(self, batch):
        """ get a list of stories corresponding to a list of hashes """
        req_str = constants.NB_ENDPOINT + '/reader/starred_stories?'
        for a_hash in batch:
            req_str += 'h=' + a_hash + '&'
        stories = requests.get(req_str, cookies=self.cookies, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        story_list = []
        try:
            story_list = json.loads(stories.text)['stories']
        except ValueError as e:
            rollbar.report_exc_info()
            logger.error('Failed to get stories for request %s', req_str)
            logger.error(e)
            statsd.event('Failed to get stories', e.message, alert_type='error')
            logger.debug(stories.text)
        return story_list

    @statsd.timed('nb.NewsblurConnector.get_comment_count')
    def get_comment_count(self, hnurl):
        req = requests.Request('GET', hnurl, cookies=self.cookies)
        return self.parse_story(self.request_with_backoff(req))

    # Parse HN story to find how many comments there are
    @statsd.timed('nb.NewsblurConnector.parse_story')
    def parse_story(self, content):
        soup = BeautifulSoup(content, "html.parser")
        comment_count = len(soup.find_all("div", {"class": "comment"}))
        return comment_count

    @statsd.timed('nb.NewsblurConnector.check_if_starred')
    def check_if_starred(self, story_hash):
        hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                              cookies=self.cookies,
                              verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        hashlist = hashes.json()['starred_story_hashes']

        return bool(story_hash in hashlist)

    # TODO: move statsd bucket names to constants.py
    @statsd.timed('nb.NewsblurConnector.remove_star_with_backoff')
    def remove_star_with_backoff(self, story_hash):
        unstar_url = constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred'
        req = requests.Request('POST', unstar_url, params={'story_hash': story_hash}, cookies=self.cookies)
        return bool(self.request_with_backoff(req) is not None)

    @statsd.timed('nb.NewsblurConnector.remove_star_with_backoff')
    def request_with_backoff(self, req):
        sleep(1)
        backoff = constants.BACKOFF_START
        s = requests.Session()
        try:
            resp = s.send(req, verify=constants.VERIFY)
            statsd.increment('nb.http_requests.count')
            statsd.increment('nb.http_requests.status_' + str(resp.status_code))
            while resp.status_code != 200:
                if resp.status_code in [429, 500, 503]:  # exponential backoff
                    logger.info(
                        "Request for %s returned %s response", req.url, resp.status_code)
                    if backoff < constants.BACKOFF_MAX:
                        logger.info("Backing off %s seconds", backoff)
                        sleep(backoff)
                        backoff = backoff * constants.BACKOFF_FACTOR
                        resp = s.send(req, verify=constants.VERIFY)
                        statsd.increment('nb.http_requests.count')
                    else:
                        logger.warn("Giving up after %s seconds for %s", backoff, req.url)
                        return None
                elif resp.status_code == 403:
                    raise BlacklistedError("Received 403 response for {0}. Is this IP blacklisted?".format(req.url))
                elif resp.status_code == 520:
                    logger.warn("520 response, skipping %s", req.url)
                    return None
                else:
                    logger.error("Request for %s returned unhandled %s response",
                                 req.url, resp.status_code)
                    raise requests.exceptions.RequestException()
            return resp
        except requests.exceptions.RequestException as e:
                logger.info("url is: %s", req.url)
                logger.error(e)
                return None
