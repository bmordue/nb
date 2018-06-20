# from ddtrace import patch
# patch(requests=True)

import json
import requests
import requests.exceptions
from datadog import statsd
from bs4 import BeautifulSoup

from utility import constants
from utility import nb_logging

from time import sleep

import exceptions

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

    def get_nb_hash_list(self):
        """ get a list of story identifiers (hashes) from NewsBlur """
        hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                              cookies=self.cookies, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        return hashes.json()['starred_story_hashes']

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
            logger.error('Failed to get stories for request %s', req_str)
            logger.error(e)
            statsd.event('Failed to get stories', e.message, alert_type='error')
            logger.debug(stories.text)
        return story_list

    # eg request_with_backoff(url, on_success)
    # eg request_with_backoff(hnurl, parse_story)
    # Hmm. Falls down on POSTs. :-( Needs more treatment
    # TODO: cf requests PreparedRequest!
    @statsd.timed('nb.populate.get_with_backoff')
    def get_with_backoff(self, url, on_success):
        try:
            backoff = constants.BACKOFF_START
            resp = requests.get(url, verify=constants.VERIFY)
            statsd.increment('nb.http_requests.get')
            while resp.status_code != 200:
                if resp.status_code in [403, 500, 503]:  # exponential backoff
                    logger.debug("Request for %s returned %s response", url, resp.status_code)
                    if backoff < constants.BACKOFF_MAX:
                        logger.debug("Backing off %s seconds", backoff)
                        sleep(backoff)
                        resp = requests.get(url, verify=constants.VERIFY)
                        statsd.increment('nb.http_requests.get')
                        backoff = backoff * constants.BACKOFF_FACTOR
                    else:
                        logger.debug("Giving up after %s seconds for %s", backoff, url)
                        return None
                elif resp.status_code == 520:
                    logger.info("520 response, skipping %s and waiting %s sec", url, constants.BACKOFF_ON_520)
                    logger.debug("Response headers: %s", resp.headers)
                    logger.debug("Response body: %s", resp.text)
                    sleep(constants.BACKOFF_ON_520)
                    return None
                else:
                    logger.debug(
                        "Request for %s returned unhandled %s response", url, resp.status_code)
                    raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException as e:
            logger.error("url is: %s", url)
            logger.error(e)
            statsd.event('Request failed', e.message, alert_type='error')
            return None
    
        return on_success(resp)
    
    
    # TODO: DEPRECATE in favour of request_with_backoff()
    @statsd.timed('nb.populate.get_comment_count')
    def get_comment_count(self, hnurl):
        sleep(1)
        try:
            backoff = 5
            story = requests.get(hnurl, verify=constants.VERIFY)
            statsd.increment('nb.http_requests.get')
            while story.status_code != 200:
                if story.status_code in [429, 500, 503]:  # exponential backoff
                    logger.debug(
                        "Request for %s returned %s response", hnurl, story.status_code)
                    if backoff < constants.BACKOFF_MAX:
                        logger.debug("Backing off %s seconds", backoff)
                        sleep(backoff)
                        backoff *= constants.BACKOFF_FACTOR
                        story = requests.get(hnurl, verify=constants.VERIFY)
                        statsd.increment('nb.http_requests.get')
                    else:
                        logger.debug("Giving up after {0} seconds for {1}".format(backoff, hnurl))
                        return None
                elif story.status_code in [520]:
                    logger.debug(
                        "520 response for %s; waiting %s sec", hnurl, constants.BACKOFF_ON_520)
                    logger.debug("Response headers: %s", story.headers)
                    logger.debug("Response body: %s", story.text)
                    sleep(constants.BACKOFF_ON_520)
                    return None
                elif story.status_code in [403]:
                    raise BlacklistedError()      
                else:
                    logger.debug("Request for %s returned unhandled %s response",
                                 hnurl, story.status_code)
                    raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException as e:
            logger.error("hnurl: %s", hnurl)
            statsd.event('RequestException', e.message, alert_type='error')
            return None
    
        return self.parse_story(story.text)

    # Parse HN story to find how many comments there are
    @statsd.timed('nb.populate.parse_story')
    def parse_story(self, content):
        soup = BeautifulSoup(content, "html.parser")
        comment_count = len(soup.find_all("div", {"class": "comment"}))
        return comment_count

    @statsd.timed('nb.prune.check_if_starred')
    def check_if_starred(self, story_hash):
        hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=self.cookies,
                              verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        hashlist = hashes.json()['starred_story_hashes']

        return bool(story_hash in hashlist)

    # TODO: deprecate in favour of more generic function
    # TODO: move statsd bucket names to constants.py
    @statsd.timed('nb.prune.remove_star_with_backoff')
    def remove_star_with_backoff(self, story_hash):
        backoff = constants.BACKOFF_START
        unstar_url = constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred'
        try:
            resp = requests.post(unstar_url,
                                 {'story_hash': story_hash}, cookies=self.cookies, verify=constants.VERIFY)
            statsd.increment('nb.http_requests.post')
            while resp.status_code != 200:
                if resp.status_code in [403, 500, 503]:  # exponential backoff
                    logger.info("Request for %s returned %s response" % (unstar_url, resp.status_code))
                    if backoff < constants.BACKOFF_MAX:
                        logger.info("Backing off %s seconds", backoff)
                        sleep(backoff)
                        backoff = backoff * constants.BACKOFF_FACTOR
                        resp = requests.post(unstar_url,
                                             {'story_hash': story_hash}, cookies=mycookies,
                                             verify=constants.VERIFY)
                        statsd.increment('nb.http_requests.post')
                    else:
                        logger.warn("Giving up after %s seconds for %s", backoff, unstar_url)
                        return False
                elif resp.status_code == 520:
                    logger.warn("520 response, skipping %s", unstar_url)
                    return False
                else:
                    logger.error("Request for %s returned unhandled %s response",
                                 unstar_url, resp.status_code)
                    raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException as e:
            logger.info("url is: %s", unstar_url)
            logger.error(e)
            return False

        return True
