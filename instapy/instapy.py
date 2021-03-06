"""OS Modules environ method to get the setup vars from the Environment"""
import csv
import json
import logging
from contextlib import contextmanager
import re
from math import ceil
import os
from sys import platform
from platform import python_version
from datetime import datetime
import random

import selenium
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy, ProxyType
import requests

from .clarifai_util import check_image
from .comment_util import comment_image
from .like_util import check_link
from .like_util import verify_liking
from .comment_util import verify_commenting
from .like_util import get_links_for_tag
from .like_util import get_links_from_feed
from .like_util import get_tags
from .like_util import get_links_for_location
from .like_util import like_image
from .like_util import get_links_for_username
from .login_util import login_user
from .print_log_writer import log_follower_num
from .settings import Settings
from .print_log_writer import log_following_num
from .time_util import sleep
from .time_util import set_sleep_percentage
from .util import get_active_users
from .util import validate_username
from .util import web_address_navigator
from .util import interruption_handler
from .util import highlight_print
from .util import dump_record_activity
from .util import truncate_float
from .util import get_proxy
from .story_util import watch_story, watch_user_story
from .unfollow_util import get_given_user_followers
from .unfollow_util import get_given_user_following
from .unfollow_util import unfollow
from .unfollow_util import unfollow_user
from .unfollow_util import follow_user
from .unfollow_util import follow_given_user
from .unfollow_util import follow_restriction
from .unfollow_util import dump_follow_restriction
from .unfollow_util import set_automated_followed_pool
from .commenters_util import extract_information
from .commenters_util import users_liked
from .commenters_util import get_photo_urls_from_profile
from .relationship_tools import get_following
from .relationship_tools import get_followers
from .relationship_tools import get_unfollowers
from .relationship_tools import get_nonfollowers
from .relationship_tools import get_fans
from .relationship_tools import get_mutual_following
from .database_engine import get_database

class InstaPyError(Exception):
    """General error for InstaPy exceptions"""


class InstaPy:
    """Class to be instantiated to use the script"""

    def __init__(self,
                 username=None,
                 password=None,
                 nogui=False,
                 selenium_local_session=True,
                 use_firefox=False,
                 browser_profile_path=None,
                 page_delay=25,
                 show_logs=False,
                 headless_browser=False,
                 proxy_address=None,
                 proxy_chrome_extension=None,
                 proxy_port=0,
                 bypass_suspicious_attempt=False,
                 multi_logs=False,
                 settings=None,
                 igbooster=True):

        if nogui:
            self.display = Display(visible=0, size=(800, 600))
            self.display.start()

        self.igbooster = igbooster

        self.browser = None
        self.headless_browser = headless_browser
        self.proxy_address = proxy_address
        self.proxy_port = proxy_port
        self.proxy_chrome_extension = proxy_chrome_extension
        self.multi_logs = multi_logs
        self.selenium_local_session = selenium_local_session
        self.show_logs = show_logs

        self.username = username or os.environ.get('INSTA_USER')
        self.password = password or os.environ.get('INSTA_PW')
        self.nogui = nogui
        self.internal_usage = {}
        self.logfolder = Settings.log_location + os.path.sep
        if self.multi_logs == True:
            self.logfolder = '{0}{1}{2}{1}'.format(
                Settings.log_location, os.path.sep, self.username)
        if not os.path.exists(self.logfolder):
            os.makedirs(self.logfolder)

        self.page_delay = page_delay
        self.switch_language = True
        self.use_firefox = use_firefox
        self.browser_profile_path = browser_profile_path

        self.do_comment = False
        self.comment_percentage = 0
        self.comments = ['Cool!', 'Nice!', 'Looks good!']
        self.photo_comments = []
        self.video_comments = []

        self.followed = 0
        self.already_followed = 0
        self.liked_img = 0
        self.already_liked = 0
        self.already_Visited = 0
        self.inap_img = 0
        self.commented = 0
        self.followed_by = 0
        self.unfollowNumber = 0
        self.not_valid_users = 0

        self.stories_watched = 0
        self.reels_watched = 0

        self.mandatory_language = False
        self.mandatory_character = []
        self.check_letters = {}

        self.quotient_breach = False

        self.jumps = {"consequent": {"likes": 0, "comments": 0, "follows": 0, "unfollows": 0},
                      "limit": {"likes": 7, "comments": 3, "follows": 5, "unfollows": 4}}

        self.follow_times = 1
        self.do_follow = False
        self.follow_percentage = 0
        self.dont_include = set()
        self.white_list = set()
        self.blacklist = {'enabled': 'True', 'campaign': ''}
        self.automatedFollowedPool = {"all":[], "eligible":[]}
        self.do_like = False
        self.like_percentage = 0

        if settings.get('stories', False):
            self.do_story = True
            self.story_percentage = 100
        else:
            self.do_story = False
            self.story_percentage = 0
        self.story_simulate = False
        self.smart_hashtags = []

        self.dont_like = ['sex', 'nsfw']
        self.ignore_if_contains = []
        self.ignore_users = []

        self.user_interact_amount = 0
        self.user_interact_media = None
        self.user_interact_percentage = 0
        self.user_interact_random = False

        self.use_clarifai = False
        self.clarifai_api_key = None
        self.clarifai_img_tags = []
        self.clarifai_img_tags_skip = []
        self.clarifai_full_match = False

        self.potency_ratio = 1.3466
        self.delimit_by_numbers = True

        #self.max_followers = 2500
        #self.max_following = 4000
        self.min_followers = 50
        self.min_following = 50

        try:
            self.max_followers = int(settings['max_followers'])
        except Exception:
            self.max_followers = 2500

        try:
            self.max_following = int(settings['max_following'])
        except Exception:
            self.max_following = 4000

        self.delimit_liking = False
        self.liking_approved = True
        self.max_likes = 1000
        self.min_likes = 0

        self.delimit_commenting = False
        self.commenting_approved = True
        self.max_comments = 35
        self.min_comments = 0
        self.comments_mandatory_words = []
        self.max_posts = None
        self.min_posts = None
        self.skip_business_categories = []
        self.dont_skip_business_categories = []
        self.skip_business = False
        self.skip_no_profile_pic = False
        self.skip_private = False
        self.skip_business_percentage = 100
        self.skip_no_profile_pic_percentage = 100
        self.skip_private_percentage = 100

        self.relationship_data = {username:{"all_following":[], "all_followers":[]}}

        self.bypass_suspicious_attempt = bypass_suspicious_attempt

        self.simulation = {"enabled": True, "percentage": 100}

        self.aborting = False

        self.mandatory_words = []

        # Assign logger
        self.log_user = ('instapy_user_%s' % self.username)
        self.logger = self.get_instapy_logger(show_logs)
        self.path_for_igbooster = self.username

        if self.selenium_local_session == True:
            self.set_selenium_local_session()


    def get_instapy_logger(self, show_logs):
        """
        Handles the creation and retrieval of loggers to avoid re-instantiation.
        """

        existing_logger = Settings.loggers.get(self.log_user)
        if existing_logger is not None:
            return existing_logger
        else:
            # initialize and setup logging system for the InstaPy object
            logger = logging.getLogger(self.log_user)
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler('{}general.log'.format(self.logfolder))
            file_handler.setLevel(logging.DEBUG)
            extra = {"username": self.username}
            logger_formatter = logging.Formatter('%(levelname)s [%(asctime)s] [%(username)s]  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(logger_formatter)

            if Settings.is_debug:
                logger.addHandler(logging.StreamHandler())
            else:
                logger.addHandler(file_handler)

            if show_logs == True:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(logger_formatter)
                logger.addHandler(console_handler)

            logger = logging.LoggerAdapter(logger, extra)

            Settings.loggers[self.log_user] = logger
            Settings.logger = logger
            return logger

    def set_selenium_local_session(self):
        """Starts local session for a selenium server.
        Default case scenario."""
        if self.aborting:
            return self

        if self.use_firefox:
            if self.browser_profile_path is not None:
                firefox_profile = webdriver.FirefoxProfile(
                    self.browser_profile_path)
            else:
                firefox_profile = webdriver.FirefoxProfile()

            # permissions.default.image = 2: Disable images load,
            # this setting can improve pageload & save bandwidth
            firefox_profile.set_preference('permissions.default.image', 2)

            if self.proxy_address and self.proxy_port > 0:
                firefox_profile.set_preference('network.proxy.type', 1)
                firefox_profile.set_preference('network.proxy.http',
                                               self.proxy_address)
                firefox_profile.set_preference('network.proxy.http_port',
                                               self.proxy_port)
                firefox_profile.set_preference('network.proxy.ssl',
                                               self.proxy_address)
                firefox_profile.set_preference('network.proxy.ssl_port',
                                               self.proxy_port)

            self.browser = webdriver.Firefox(firefox_profile=firefox_profile)

        else:
            chromedriver_location = Settings.chromedriver_location
            chrome_options = Options()
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--dns-prefetch-disable')
            chrome_options.add_argument('--lang=en-US')
            chrome_options.add_argument('--disable-setuid-sandbox')

            if self.headless_browser:
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')

                #if disable_image_load:
                #    chrome_options.add_argument(
                #        '--blink-settings=imagesEnabled=false')

                user_agent = "Chrome"
                chrome_options.add_argument('user-agent={user_agent}'
                                        .format(user_agent=user_agent))

            capabilities = DesiredCapabilities.CHROME
            # Proxy for chrome
            # platform is part of sys lib. This condition is used because Mac OS sucks in this lib
            if platform != 'darwin':
                if self.proxy_address and self.proxy_port > 0:
                    prox = Proxy()
                    proxy = ":".join([self.proxy_address, str(self.proxy_port)])
                    prox.proxy_type = ProxyType.MANUAL
                    prox.http_proxy = proxy
                    prox.socks_proxy = proxy
                    prox.ssl_proxy = proxy
                    prox.add_to_capabilities(capabilities)
                # add proxy extension
                if self.proxy_chrome_extension and not self.headless_browser:
                    chrome_options.add_extension(self.proxy_chrome_extension)
            
            if self.browser_profile_path is not None:
                chrome_options.add_argument('user-data-dir={}'.format(self.browser_profile_path))

            chrome_prefs = {
                'intl.accept_languages': 'en-US'
            }
            chrome_options.add_experimental_option('prefs', chrome_prefs)
            try:
                self.browser = webdriver.Chrome(chromedriver_location,
                                                desired_capabilities=capabilities,
                                                chrome_options=chrome_options)
            except selenium.common.exceptions.WebDriverException as exc:
                self.logger.exception(exc)
                raise InstaPyError('ensure chromedriver is installed at {}'.format(
                    Settings.chromedriver_location))

            # prevent: Message: unknown error: call function result missing 'value'
            matches = re.match(r'^(\d+\.\d+)',
                               self.browser.capabilities['chrome']['chromedriverVersion'])
            if float(matches.groups()[0]) < Settings.chromedriver_min_version:
                raise InstaPyError('chromedriver {} is not supported, expects {}+'.format(
                    float(matches.groups()[0]), Settings.chromedriver_min_version))

        self.browser.implicitly_wait(self.page_delay)

        message = "Session started!"
        highlight_print(self.username, message, "initialization", "info", self.logger)
        print('')

        return self


    def set_selenium_remote_session(self, selenium_url=''):
        """Starts remote session for a selenium server.
         Useful for docker setup."""
        if self.aborting:
            return self

        if self.use_firefox:
            self.browser = webdriver.Remote(
                command_executor=selenium_url,
                desired_capabilities=DesiredCapabilities.FIREFOX)
        else:
            self.browser = webdriver.Remote(
                command_executor=selenium_url,
                desired_capabilities=DesiredCapabilities.CHROME)

        message = "Session started!"
        highlight_print(self.username, message, "initialization", "info", self.logger)
        print('')

        return self

    def login(self):
        """Used to login the user either with the username and password"""
        if not login_user(self.browser,
                          self.username,
                          self.password,
                          self.logfolder,
                          self.switch_language,
                          self.bypass_suspicious_attempt):
            message = "Wrong login data!"
            highlight_print(self.username, message, "login", "critical", self.logger)

            self.aborting = True
        else:
            message = "Logged in successfully!"
            highlight_print(self.username, message, "login", "info", self.logger)

        self.followed_by = log_follower_num(self.browser, self.username, self.logfolder)
        self.following_num = log_following_num(self.browser, self.username, self.logfolder)

        

        if self.aborting:
            self.end()

        return self

    def set_sleep_reduce(self, percentage):
        set_sleep_percentage(percentage)

        return self

    def set_do_comment(self, enabled=False, percentage=0):
        """Defines if images should be commented or not
        percentage=25 -> ~ every 4th picture will be commented"""
        if self.aborting:
            return self

        self.do_comment = enabled
        self.comment_percentage = percentage

        return self

    def set_comments(self, comments=None, media=None):
        """Changes the possible comments"""
        if self.aborting:
            return self

        if (media not in [None, 'Photo', 'Video']):
            self.logger.warning('Unkown media type! Treating as "any".')
            media = None

        self.comments = comments or []

        if media is None:
            self.comments = comments
        else:
            attr = '{}_comments'.format(media.lower())
            setattr(self, attr, comments)

        return self

    def set_do_follow(self, enabled=False, percentage=0, times=1):
        """Defines if the user of the liked image should be followed"""
        if self.aborting:
            return self

        self.follow_times = times
        self.do_follow = enabled
        self.follow_percentage = percentage

        return self

    def set_do_like(self, enabled=False, percentage=0):
        if self.aborting:
            return self

        self.do_like = enabled
        self.like_percentage = percentage

        return self

    def set_dont_like(self, tags=None):
        """Changes the possible restriction tags, if one of this
         words is in the description, the image won't be liked but user still might be unfollowed"""
        if self.aborting:
            return self

        if not isinstance(tags, list):
            self.logger.warning('Unable to use your set_dont_like '
                                'configuration!')
            self.aborting = True

        self.dont_like = tags or []

        return self

    def set_user_interact(self,
                          amount=10,
                          percentage=100,
                          randomize=False,
                          media=None):
        """Define if posts of given user should be interacted"""
        if self.aborting:
            return self

        self.user_interact_amount = amount
        self.user_interact_random = randomize
        self.user_interact_percentage = percentage
        self.user_interact_media = media

        return self

    def set_ignore_users(self, users=None):
        """Changes the possible restriction to users, if a user who posts
        is one of these, the image won't be liked"""
        if self.aborting:
            return self

        self.ignore_users = users or []

        return self

    def set_ignore_if_contains(self, words=None):
        """Ignores the don't likes if the description contains
        one of the given words"""
        if self.aborting:
            return self

        self.ignore_if_contains = words or []

        return self

    def set_dont_include(self, friends=None):
        """Defines which accounts should not be unfollowed"""
        if self.aborting:
            return self

        self.dont_include = set(friends) or set()
        self.white_list = set(friends) or set()

        return self

    def set_switch_language(self, option=True):
        self.switch_language = option
        return self

    def set_use_clarifai(self, enabled=False, api_key=None, full_match=False):
        """
        Defines if the clarifai img api should be used
        Which 'project' will be used (only 5000 calls per month)

        Raises:
            InstaPyError if os is windows
        """
        if self.aborting:
            return self

        #if os.name == 'nt':
        #    raise InstaPyError('Clarifai is not supported on Windows')

        self.use_clarifai = enabled

        if api_key is None and self.clarifai_api_key is None:
            self.clarifai_api_key = os.environ.get('CLARIFAI_API_KEY')
        elif api_key is not None:
            self.clarifai_api_key = api_key

        self.clarifai_full_match = full_match

        return self

    def set_smart_hashtags(self,
                           tags=None,
                           limit=3,
                           sort='top',
                           log_tags=True):
        """Generate smart hashtags based on https://displaypurposes.com/"""
        """ranking, banned and spammy tags are filtered out."""

        if tags is None:
            print('set_smart_hashtags is misconfigured')
            return

        for tag in tags:
            req = requests.get(
                u'https://d212rkvo8t62el.cloudfront.net/tag/{}'.format(tag))
            data = json.loads(req.text)

            if data['tagExists'] is True:
                if sort == 'top':
                    # sort by ranking
                    ordered_tags_by_rank = sorted(
                        data['results'], key=lambda d: d['rank'], reverse=True)
                    ranked_tags = (ordered_tags_by_rank[:limit])
                    for item in ranked_tags:
                        # add smart hashtag to like list
                        self.smart_hashtags.append(item['tag'])

                elif sort == 'random':
                    random_tags = random.sample(data['results'], limit)
                    for item in random_tags:
                        self.smart_hashtags.append(item['tag'])

                if log_tags is True:
                    for item in self.smart_hashtags:
                        print(u'[smart hashtag generated: {}]'.format(item))
            else:
                print(u'Too few results for #{} tag'.format(tag))

        # delete duplicated tags
        self.smart_hashtags = list(set(self.smart_hashtags))
        return self

    def clarifai_check_img_for(self, tags=None, tags_skip=None, comment=False, comments=None):
        """Defines the tags, the images should be checked for"""
        if self.aborting:
            return self

        if tags is None and not self.clarifai_img_tags:
            self.use_clarifai = False
        elif tags:
            self.clarifai_img_tags.append((tags, comment, comments))
            self.clarifai_img_tags_skip = tags_skip


        return self


    def follow_commenters(self, usernames, amount=10, daysold=365, max_pic=50, sleep_delay=300, interact=False, type_of_account='all', gender='all'):
        """ Follows users' commenters """

        if self.aborting:
            return self

        message = "Starting to follow commenters.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if not isinstance(usernames, list):
            usernames = [usernames]

        followed_all = 0
        followed_new = 0

        # hold the current global values for differentiating at the end
        already_followed_init = self.already_followed
        not_valid_users_init = self.not_valid_users
        liked_init = self.liked_img
        already_liked_init = self.already_liked
        commented_init = self.commented
        inap_img_init = self.inap_img

        relax_point = random.randint(7,
                                     14)  # you can use some plain value `10` instead of this quitely randomized score
        self.quotient_breach = False

        for username in usernames:
            if self.quotient_breach:
                break

            self.logger.info(
                "Following commenters of '{}' from {} pictures in last {} days...\nScrapping wall..".format(username,
                                                                                                            max_pic,
                                                                                                            daysold))
            commenters = extract_information(self.browser, username, daysold, max_pic)

            if len(commenters) > 0:
                self.logger.info("Going to follow top {} users.\n".format(amount))
                sleep(1)
                # This way of iterating will prevent sleep interference between functions
                random.shuffle(commenters)
                for commenter in commenters[:amount]:
                    if self.quotient_breach:
                        self.logger.warning(
                            "--> Follow quotient reached its peak!"
                            "\t~leaving Follow-Commenters activity\n")
                        break

                    with self.feature_in_feature("follow_by_list", True):
                        followed = self.follow_by_list(commenter,
                                                       self.follow_times,
                                                       sleep_delay,
                                                       interact)
                    if followed > 0:
                        followed_all += 1
                        followed_new += 1
                        self.logger.info("Total Follow: {}\n".format(str(followed_all)))
                        # Take a break after a good following
                        if followed_new >= relax_point:
                            delay_random = random.randint(
                                ceil(sleep_delay * 0.85),
                                ceil(sleep_delay * 1.14))
                            sleep_time = ("{} seconds".format(delay_random) if
                                          delay_random < 60 else
                                          "{} minutes".format(truncate_float(
                                              delay_random / 60, 2)))
                            self.logger.info("------=>  Followed {} new users ~sleeping about {}"
                                             .format(followed_new, sleep_time))
                            sleep(delay_random)
                            relax_point = random.randint(7, 14)
                            followed_new = 0
                            pass

            else:
                self.logger.info("Noone commented, noone to follow.\n")

            sleep(1)

        self.logger.info("Finished following Commenters!\n")

        # find the feature-wide action sizes by taking a difference
        already_followed = (self.already_followed - already_followed_init)
        not_valid_users = (self.not_valid_users - not_valid_users_init)
        liked = (self.liked_img - liked_init)
        already_liked = (self.already_liked - already_liked_init)
        commented = (self.commented - commented_init)
        inap_img = (self.inap_img - inap_img_init)

        # print results
        self.logger.info("Followed: {}".format(followed_all))
        self.logger.info("Already followed: {}".format(already_followed))
        self.logger.info("Not valid users: {}".format(not_valid_users))

        if interact == True:
            print('')
            # print results out of interactions
            self.logger.info("Liked: {}".format(liked))
            self.logger.info("Already Liked: {}".format(already_liked))
            self.logger.info("Commented: {}".format(commented))
            self.logger.info("Inappropriate: {}".format(inap_img))

        return self


    def follow_likers (self, usernames, urls=None, type_of_account='all', gender='all', amount=10, photos_grab_amount=3, follow_likers_per_photo=3, randomize=True, sleep_delay=300, interact=False):
        """ Follows users from urls """
        if urls:
            if not isinstance(urls, list):
                urls = [urls]
            for url in urls:
                try:
                    users_liked_list = users_liked(self.browser, url, amount)
                except Exception as e:
                    print(e)

                try:
                    self.follow_by_list(users_liked_list[:amount])
                except:
                    print('EEEEEH')

            return self

        """ Follows users' likers """

        message = "Starting to follow likers.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if not isinstance(usernames, list):
            usernames = [usernames]

        if photos_grab_amount > 12:
            self.logger.info("Sorry, you can only grab likers from first 12 photos for given username now.\n")
            photos_grab_amount = 12

        followed_all = 0
        followed_new = 0

        # hold the current global values for differentiating at the end
        already_followed_init = self.already_followed
        not_valid_users_init = self.not_valid_users
        liked_init = self.liked_img
        already_liked_init = self.already_liked
        commented_init = self.commented
        inap_img_init = self.inap_img

        relax_point = random.randint(7,
                                     14)  # you can use some plain value `10` instead of this quitely randomized score
        self.quotient_breach = False

        for username in usernames:
            if self.quotient_breach:
                break

            photo_urls = get_photo_urls_from_profile(self.browser, username, photos_grab_amount, randomize)
            sleep(1)
            if not isinstance(photo_urls, list):
                photo_urls = [photo_urls]

            for photo_url in photo_urls:
                if self.quotient_breach:
                    break

                likers = users_liked(self.browser, photo_url, follow_likers_per_photo)
                # This way of iterating will prevent sleep interference between functions
                random.shuffle(likers)

                for liker in likers[:follow_likers_per_photo]:
                    if self.quotient_breach:
                        self.logger.warning(
                            "--> Follow quotient reached its peak!"
                            "\t~leaving Follow-Likers activity\n")
                        break

                    with self.feature_in_feature("follow_by_list", True):
                        followed = self.follow_by_list(liker,
                                                       self.follow_times,
                                                       sleep_delay,
                                                       interact, type_of_account, gender)
                    if followed > 0:
                        followed_all += 1
                        followed_new += 1
                        self.logger.info("Total Follow: {}\n".format(str(followed_all)))
                        # Take a break after a good following
                        if followed_new >= relax_point:
                            delay_random = random.randint(
                                ceil(sleep_delay * 0.85),
                                ceil(sleep_delay * 1.14))
                            sleep_time = ("{} seconds".format(delay_random) if
                                          delay_random < 60 else
                                          "{} minutes".format(truncate_float(
                                              delay_random / 60, 2)))
                            self.logger.info("------=>  Followed {} new users ~sleeping about {}"
                                             .format(followed_new, sleep_time))
                            sleep(delay_random)
                            relax_point = random.randint(7, 14)
                            followed_new = 0
                            pass

        self.logger.info("Finished following Likers!\n")

        # find the feature-wide action sizes by taking a difference
        already_followed = (self.already_followed - already_followed_init)
        not_valid_users = (self.not_valid_users - not_valid_users_init)
        liked = (self.liked_img - liked_init)
        already_liked = (self.already_liked - already_liked_init)
        commented = (self.commented - commented_init)
        inap_img = (self.inap_img - inap_img_init)

        # print results
        self.logger.info("Followed: {}".format(followed_all))
        self.logger.info("Already followed: {}".format(already_followed))
        self.logger.info("Not valid users: {}".format(not_valid_users))

        if interact == True:
            print('')
            # print results out of interactions
            self.logger.info("Liked: {}".format(liked))
            self.logger.info("Already Liked: {}".format(already_liked))
            self.logger.info("Commented: {}".format(commented))
            self.logger.info("Inappropriate: {}".format(inap_img))

        return self

    def follow_by_list(self, followlist, times=1, sleep_delay=300, interact=False, type_of_account='all', gender='all', from_u=''):
        """Allows to follow by any scrapped list"""
        if not isinstance(followlist, list):
            followlist = [followlist]

        if self.aborting:
            self.logger.info(">>> self aborting prevented")
            # return self

        # standalone means this feature is started by the user
        standalone = True if "follow_by_list" not in self.internal_usage.keys() else False
        # skip validation in case of it is already accomplished
        users_validated = True if not standalone and not self.internal_usage["follow_by_list"]["validate"] else False

        self.follow_times = times or 0

        followed_all = 0
        followed_new = 0
        already_followed = 0
        not_valid_users = 0

        # hold the current global values for differentiating at the end
        liked_init = self.liked_img
        already_liked_init = self.already_liked
        commented_init = self.commented
        inap_img_init = self.inap_img

        relax_point = random.randint(7,
                                     14)  # you can use some plain value `10` instead of this quitely randomized score
        self.quotient_breach = False

        for acc_to_follow in followlist:
            if self.jumps["consequent"]["follows"] >= self.jumps["limit"]["follows"]:
                self.logger.warning("--> Follow quotient reached its peak!\t~leaving Follow-By-Tags activity\n")
                # reset jump counter before breaking the loop
                self.jumps["consequent"]["follows"] = 0
                # turn on `quotient_breach` to break the internal iterators of the caller
                self.quotient_breach = True if not standalone else False
                break

            if follow_restriction("read", acc_to_follow, self.follow_times, self.logger):
                print('')
                continue

            if not users_validated:
                # Verify if the user should be followed
                validation, details = self.validate_user_call(acc_to_follow, type_of_account, gender)
                if validation != True or acc_to_follow == self.username:
                    self.logger.info("--> Not a valid user: {}".format(details))
                    not_valid_users += 1
                    continue

            # Take a break after a good following
            if followed_new >= relax_point:
                delay_random = random.randint(
                    ceil(sleep_delay * 0.85),
                    ceil(sleep_delay * 1.14))
                sleep_time = ("{} seconds".format(delay_random) if
                              delay_random < 60 else
                              "{} minutes".format(truncate_float(
                                  delay_random / 60, 2)))
                self.logger.info("Followed {} new users  ~sleeping about {}\n"
                                 .format(followed_new, sleep_time))
                sleep(delay_random)
                followed_new = 0
                relax_point = random.randint(7, 14)
                pass

            if not follow_restriction("read", acc_to_follow, self.follow_times, self.logger):
                follow_state, msg = follow_user(self.browser,
                                                "profile",
                                                self.username,
                                                acc_to_follow,
                                                None,
                                                self.blacklist,
                                                self.logger,
                                                self.logfolder, action=['user', from_u])
                sleep(random.randint(1, 3))

                if follow_state == True:
                    followed_all += 1
                    followed_new += 1
                    # reset jump counter after a successful follow
                    self.jumps["consequent"]["follows"] = 0

                    if standalone:  # print only for external usage (internal callers have their printers)
                        self.logger.info("Total Follow: {}\n".format(str(followed_all)))

                    # Check if interaction is expected
                    if interact and self.do_like:
                        do_interact = random.randint(0, 100) <= self.user_interact_percentage
                        # Do interactions if any
                        if do_interact and self.user_interact_amount > 0:
                            original_do_follow = self.do_follow  # store the original value of `self.do_follow`
                            self.do_follow = False  # disable following temporarily cos the user is already followed above
                            self.interact_by_users(acc_to_follow,
                                                   self.user_interact_amount,
                                                   self.user_interact_random,
                                                   self.user_interact_media)
                            self.do_follow = original_do_follow  # revert back original `self.do_follow` value (either it was `False` or `True`)

                elif msg == "already followed":
                    already_followed += 1

                elif msg == "jumped":
                    # will break the loop after certain consecutive jumps
                    self.jumps["consequent"]["follows"] += 1

                sleep(1)

        if standalone:  # print only for external usage (internal callers have their printers)
            self.logger.info("Finished following by List!\n")
            # print summary
            self.logger.info("Followed: {}".format(followed_all))
            self.logger.info("Already followed: {}".format(already_followed))
            self.logger.info("Not valid users: {}".format(not_valid_users))

            if interact == True:
                print('')
                # find the feature-wide action sizes by taking a difference
                liked = (self.liked_img - liked_init)
                already_liked = (self.already_liked - already_liked_init)
                commented = (self.commented - commented_init)
                inap_img = (self.inap_img - inap_img_init)

                # print the summary out of interactions
                self.logger.info("Liked: {}".format(liked))
                self.logger.info("Already Liked: {}".format(already_liked))
                self.logger.info("Commented: {}".format(commented))
                self.logger.info("Inappropriate: {}".format(inap_img))

        # always sum up general objects regardless of the request size
        self.followed += followed_all
        self.already_followed += already_followed
        self.not_valid_users += not_valid_users

        return followed_all


    def set_relationship_bounds (self,
                                  enabled=None,
                                   potency_ratio=None,
                                    delimit_by_numbers=None,
                                     max_followers=None,
                                      max_following=None,
                                       min_followers=None,
                                        min_following=None):
        """Sets the potency ratio and limits to the provide an efficient activity between the targeted masses"""
        self.potency_ratio = potency_ratio if enabled==True else None
        self.delimit_by_numbers = delimit_by_numbers if enabled==True else None

        self.max_followers = max_followers
        self.min_followers = min_followers

        self.max_following = max_following
        self.min_following = min_following



    def set_delimit_liking(self,
                            enabled=None,
                             max=None,
                              min=None):

        self.delimit_liking = True if enabled==True else False
        self.max_likes = max
        self.min_likes = min



    def set_delimit_commenting(self,
                                enabled=False,
                                 max=None,
                                  min=None):

        self.delimit_commenting = True if enabled==True else False
        self.max_comments = max
        self.min_comments = min



    def set_simulation(self, enabled=True, percentage=100):
        """ Sets aside simulation parameters """
        if enabled not in [True, False]:
            self.logger.info("Invalid simulation parameter! Please use correct syntax with accepted values.")

        elif enabled == False:
            self.simulation["enabled"] = False

        else:
            percentage = 0 if percentage is None else percentage
            self.simulation = {"enabled":True, "percentage":percentage}



    def like_by_locations(self,
                          locations=None,
                          tags2=None,
                          amount=50,
                          media=None,
                          skip_top_posts=True, type_of_account='all', gender='all'):
        """Likes (default) 50 images per given locations"""
        if self.aborting:
            return self

        liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0

        locations = locations or []

        #check second tag list
        if tags2:
            tags2 = [tag.strip() for tag in tags2]
            tags2 = tags2 or []

        for index, location in enumerate(locations):
            self.logger.info('Location [{}/{}]'
                             .format(index + 1, len(locations)))
            if not tags2:            
                self.logger.info('--> {}'.format(location.encode('utf-8')))
            else:
                self.logger.info('--> {} with {}'.format(location.encode('utf-8'), tags2))

                if not os.path.exists('logs/{}/data_location_{}.csv'.format(self.username, location)):
                    list_for_statistics = []
                else:
                    with open('logs/{}/data_location_{}.csv'.format(self.username, location)) as csvfile:
                        f = csv.reader(csvfile, delimiter=';')
                        list_for_statistics = [i[1] for i in f]

            try:
                links = get_links_for_location(self.browser,
                                               location,
                                               amount,
                                               self.logger,
                                               media,
                                               skip_top_posts)
            except NoSuchElementException as exc:
                self.logger.warning("Error occured while getting images from location: {}  "
                                    "~maybe too few images exist\n\t{}\n".format(location, str(exc).encode("utf-8")))
                continue

            for i, link in enumerate(links):
                self.logger.info('[{}/{}]'.format(i + 1, len(links)))
                self.logger.info(link)

                try:
                    if tags2:
                        try:
                            inappropriate, user_name, is_video, reason, scope, contains_tag2 = (
                                check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger, tags2=tags2)
                            )
                            if not contains_tag2:
                                self.logger.info('Element from list 2 not found {}'.format(tags2))
                                continue
                            else:
                                if user_name not in list_for_statistics:
                                    if not os.path.exists('logs/{}/data_location_{}.csv'.format(self.username, location)):
                                        open('logs/{}/data_location_{}.csv'.format(self.username, location), 'w').close()

                                    with open('logs/{}/data_location_{}.csv'.format(self.username, location), 'a') as csvfile:
                                        f = csv.writer(csvfile, delimiter=';')
                                        f.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, link, contains_tag2])
                                    #print('Added {}'.format(user_name))
                                    list_for_statistics.append(user_name)
                        except Exception as e:
                            print(e)
                            continue
                    else:
                        inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                    if not inappropriate and self.delimit_liking:
                        self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                    if not inappropriate and self.liking_approved:
                        #validate user
                        validation, details = self.validate_user_call(user_name, type_of_account, gender)
                        if validation != True:
                            self.logger.info("--> Not a valid user: {}".format(details))
                            not_valid_users += 1
                            continue
                        else:
                            web_address_navigator(self.browser, link)

                        #try to like
                        liked = like_image(self.igbooster, self.path_for_igbooster,
                                        link,
                                        self.browser,
                                           user_name,
                                           self.blacklist,
                                           self.logger,
                                           self.logfolder)

                        if liked:
                            liked_img += 1
                            checked_img = True
                            temp_comments = []
                            commenting = random.randint(
                                0, 100) <= self.comment_percentage
                            following = random.randint(
                                0, 100) <= self.follow_percentage

                            if self.use_clarifai and (following or commenting):
                                try:
                                    checked_img, temp_comments = (
                                        check_image(self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                    )
                                except Exception as err:
                                    self.logger.error(
                                        'Image check error: {}'.format(err))

                            # comments
                            if (self.do_comment and
                                user_name not in self.dont_include and
                                checked_img and
                                    commenting):

                                if self.delimit_commenting:
                                    self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                if self.commenting_approved:
                                    if temp_comments:
                                        # Use clarifai related comments only!
                                        comments = temp_comments
                                    elif is_video:
                                        comments = (self.comments +
                                                    self.video_comments)
                                    else:
                                        comments = (self.comments +
                                                    self.photo_comments)
                                    commented += comment_image(self.igbooster, self.path_for_igbooster,
                                                                link,
                                                                self.browser,
                                                               user_name,
                                                               comments,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder)
                                else:
                                    self.logger.info(disapproval_reason)
                            else:
                                self.logger.info('--> Not commented')
                                sleep(1)

                            # following
                            if (self.do_follow and
                                user_name not in self.dont_include and
                                checked_img and
                                following and
                                not follow_restriction("read", user_name,
                                 self.follow_times, self.logger)):

                                follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder, action=['location', location])
                                if follow_state == True:
                                    followed += 1

                            else:
                                self.logger.info('--> Not following')
                                sleep(1)
                        else:
                            already_liked += 1
                    else:
                        self.logger.info(
                            '--> Image not liked: {}'.format(reason.encode('utf-8')))
                        inap_img += 1
                except NoSuchElementException as err:
                    self.logger.error('Invalid Page: {}'.format(err))

            self.logger.info('Location: {}'.format(location.encode('utf-8')))
            self.logger.info('Liked: {}'.format(liked_img))
            self.logger.info('Already Liked: {}'.format(already_liked))
            self.logger.info('Commented: {}'.format(commented))
            self.logger.info('Followed: {}'.format(followed))
            self.logger.info('Inappropriate: {}'.format(inap_img))
            self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.followed += followed
        self.liked_img += liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self

    def comment_by_locations(self,
                      locations=None,
                      amount=50,
                      media=None,
                      skip_top_posts=True, type_of_account='all', gender='all'):
        """Likes (default) 50 images per given locations"""
        if self.aborting:
            return self

        liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0

        locations = locations or []

        for index, location in enumerate(locations):
            self.logger.info('Location [{}/{}]'
                             .format(index + 1, len(locations)))
            self.logger.info('--> {}'.format(location.encode('utf-8')))

            try:
                links = get_links_for_location(self.browser,
                                               location,
                                               amount,
                                               self.logger,
                                               media,
                                               skip_top_posts)
            except NoSuchElementException:
                self.logger.warning('Too few images, skipping this location')
                continue

            for i, link in enumerate(links):
                self.logger.info('[{}/{}]'.format(i + 1, len(links)))
                self.logger.info(link)

                try:
                    inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                    if not inappropriate:
                        #validate user
                        validation, details = self.validate_user_call(user_name, type_of_account, gender)
                        if validation != True:
                            self.logger.info(details)
                            not_valid_users += 1
                            continue
                        else:
                            web_address_navigator(self.browser, link)

                        #try to comment
                        liked = True

                        self.logger.info('--> Image not liked: Likes are disabled for method \'comment_by_locations\'')

                        if liked:
                            liked_img += 1
                            checked_img = True
                            temp_comments = []
                            commenting = random.randint(
                                0, 100) <= self.comment_percentage
                            following = random.randint(
                                0, 100) <= self.follow_percentage

                            if self.use_clarifai and (following or commenting):
                                try:
                                    checked_img, temp_comments = (
                                        check_image(self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                    )
                                except Exception as err:
                                    self.logger.error(
                                        'Image check error: {}'.format(err))


                            if (self.do_comment and
                                user_name not in self.dont_include and
                                checked_img and
                                    commenting):

                                if self.delimit_commenting:
                                    self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                if self.commenting_approved:
                                    if temp_comments:
                                        # Use clarifai related comments only!
                                        comments = temp_comments
                                    elif is_video:
                                        comments = (self.comments +
                                                    self.video_comments)
                                    else:
                                        comments = (self.comments +
                                                    self.photo_comments)
                                    commented += comment_image(self.igbooster, self.path_for_igbooster,
                                                                link,
                                                                self.browser,
                                                               user_name,
                                                               comments,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder, action=['location', location])
                                else:
                                    self.logger.info(disapproval_reason)
                            else:
                                self.logger.info('--> Not commented')
                                sleep(1)

                            if (self.do_follow and
                                user_name not in self.dont_include and
                                checked_img and
                                following and
                                not follow_restriction("read", user_name,
                                 self.follow_times, self.logger)):

                                follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder, action=['location', location])
                                if follow_state == True:
                                    followed += 1

                            else:
                                self.logger.info('--> Not following')
                                sleep(1)
                        else:
                            already_liked += 1
                    else:
                        self.logger.info(
                            '--> Image not liked: {}'.format(reason.encode('utf-8')))
                        inap_img += 1
                except NoSuchElementException as err:
                    self.logger.error('Invalid Page: {}'.format(err))

        self.logger.info('Location: {}'.format(location.encode('utf-8')))
        self.logger.info('Liked: {}'.format(liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Followed: {}'.format(followed))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.followed += followed
        self.not_valid_users += not_valid_users

        return self

    def like_by_tags(self,
                     tags=None,
                     tags2=None,
                     locations=None,
                     amount=50,
                     skip_top_posts=True,
                     use_smart_hashtags=False,
                     interact=False,
                     randomize=False,
                     media=None, is_combo=False, type_of_account='all', gender='all'):
        """Likes (default) 50 images per given tag"""
        if self.aborting:
            return self

        liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0

        # if smart hashtag is enabled
        if use_smart_hashtags is True and self.smart_hashtags is not []:
            print('Using smart hashtags')
            tags = self.smart_hashtags

        # deletes white spaces in tags
        tags = [tag.strip() for tag in tags]

        tags = tags or []

        #check second tag list
        if tags2:
            tags2 = [tag.strip() for tag in tags2]
            tags2 = tags2 or []

        for index, tag in enumerate(tags):
            self.logger.info('Tag [{}/{}]'.format(index + 1, len(tags)))
            
            if not tags2 and not locations:
                self.logger.info('--> {}'.format(tag.encode('utf-8')))
            elif not tags2 and locations:
                self.logger.info('--> {} with {}'.format(tag.encode('utf-8'), locations))

                if not os.path.exists('logs/{}/data_tag_{}.csv'.format(self.username, tag)):
                    list_for_statistics = []
                else:
                    with open('logs/{}/data_tag_{}.csv'.format(self.username, tag)) as csvfile:
                        f = csv.reader(csvfile, delimiter=';')
                        list_for_statistics = [i[1] for i in f]
            else:
                if locations:
                    self.logger.info('--> {} with {} and {}'.format(tag.encode('utf-8'), tags2, locations))
                else:
                    self.logger.info('--> {} with {}'.format(tag.encode('utf-8'), tags2))

                if not os.path.exists('logs/{}/data_tag_{}.csv'.format(self.username, tag)):
                    list_for_statistics = []
                else:
                    with open('logs/{}/data_tag_{}.csv'.format(self.username, tag)) as csvfile:
                        f = csv.reader(csvfile, delimiter=';')
                        list_for_statistics = [i[1] for i in f]

            try:
                links = get_links_for_tag(self.browser,
                                          tag,
                                          amount,
                                          skip_top_posts,
                                          randomize,
                                          media,
                                          self.logger)
            except NoSuchElementException:
                self.logger.info('Too few images, skipping this tag')
                continue

            for i, link in enumerate(links):
                self.logger.info('[{}/{}]'.format(i + 1, len(links)))
                self.logger.info(link)

                try:
                    if tags2:
                        try:
                            if locations:
                                inappropriate, user_name, is_video, reason, scope, contains_tag2, contains_locations = (
                                    check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger, tags2=tags2, locations=locations)
                                )
                                if not contains_tag2 and not contains_locations:
                                    self.logger.info('Element from list 2 not found {}'.format(tags2))
                                    continue
                                else:
                                    if user_name not in list_for_statistics:
                                        if not os.path.exists('logs/{}/data_tag_{}.csv'.format(self.username, tag)):
                                            open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'w').close()

                                        with open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'a') as csvfile:
                                            f = csv.writer(csvfile, delimiter=';')
                                            f.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, link, contains_tag2])
                                        #print('Added {}'.format(user_name))
                                        list_for_statistics.append(user_name)
                            else:
                                inappropriate, user_name, is_video, reason, scope, contains_tag2 = (
                                    check_link(self.browser,
                                       link,
                                       self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger, tags2=tags2)
                                )
                                if not contains_tag2:
                                    self.logger.info('Element from list 2 not found {}'.format(tags2))
                                    continue
                                else:
                                    if user_name not in list_for_statistics:
                                        if not os.path.exists('logs/{}/data_tag_{}.csv'.format(self.username, tag)):
                                            open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'w').close()

                                        with open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'a') as csvfile:
                                            f = csv.writer(csvfile, delimiter=';')
                                            f.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, link, contains_tag2])
                                        #print('Added {}'.format(user_name))
                                        list_for_statistics.append(user_name)
                        except Exception as e:
                            print(e)
                            continue
                    elif locations:
                        try:
                            inappropriate, user_name, is_video, reason, scope, contains_locations = (
                                check_link(self.browser,
                                       link,
                                       self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                       self.logger, locations=locations)
                            )
                            if not contains_locations:
                                self.logger.info('Location not found {}'.format(locations))
                                continue
                            else:
                                if user_name not in list_for_statistics:
                                    if not os.path.exists('logs/{}/data_tag_{}.csv'.format(self.username, tag)):
                                        open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'w').close()

                                    with open('logs/{}/data_tag_{}.csv'.format(self.username, tag), 'a') as csvfile:
                                        f = csv.writer(csvfile, delimiter=';')
                                        f.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_name, link, 'Location: %s' % contains_locations])
                                    #print('Added {}'.format(user_name))
                                    list_for_statistics.append(user_name)
                        except Exception as e:
                            print(e)
                            continue
                    else:
                        inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))                            

                    if not inappropriate and self.delimit_liking:
                        self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                    if not inappropriate and self.liking_approved:
                        #validate user
                        validation, details = self.validate_user_call(user_name, type_of_account, gender)
                        if validation != True:
                            self.logger.info(details)
                            not_valid_users += 1
                            continue
                        else:
                            web_address_navigator(self.browser, link)

                        #try to like
                        liking = random.randint(0, 100) <= self.like_percentage
                        if self.do_like and liking:
                            liked = like_image(self.igbooster, self.path_for_igbooster,
                                        link,
                                        self.browser,
                                           user_name,
                                           self.blacklist,
                                           self.logger,
                                           self.logfolder, tag=tag)
                        else:
                            liked = False

                        if liked or is_combo:

                            if interact:
                                username = (self.browser.
                                    find_element_by_xpath(
                                        '//article/header/div[2]/'
                                        'div/div[1]/a'))

                                username = username.get_attribute("title")
                                name = []
                                name.append(username)

                                self.logger.info(
                                    '--> User followed: {}'
                                    .format(name))
                                self.like_by_users(
                                    name,
                                    self.user_interact_amount,
                                    self.user_interact_random,
                                    self.user_interact_media)

                            liked_img += 1
                            checked_img = True
                            temp_comments = []
                            commenting = (random.randint(0, 100) <=
                                          self.comment_percentage)
                            following = (random.randint(0, 100) <=
                                         self.follow_percentage)

                            if self.use_clarifai and (following or commenting):
                                try:
                                    checked_img, temp_comments = (
                                        check_image(self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                    )
                                except Exception as err:
                                    self.logger.error(
                                        'Image check error: {}'.format(err))

                            # comments
                            if (self.do_comment and
                                user_name not in self.dont_include and
                                checked_img and
                                    commenting):

                                if self.delimit_commenting:
                                    self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                if self.commenting_approved:
                                    if temp_comments:
                                        # Use clarifai related comments only!
                                        comments = temp_comments
                                    elif is_video:
                                        comments = (self.comments +
                                                    self.video_comments)
                                    else:
                                        comments = (self.comments +
                                                    self.photo_comments)
                                    commented += comment_image(self.igbooster, self.path_for_igbooster,
                                                                link,
                                                                self.browser,
                                                               user_name,
                                                               comments,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder, action=['tag', tag])
                                else:
                                    self.logger.info(disapproval_reason)
                            else:
                                self.logger.info('--> Not commented')
                                sleep(1)

                            # following
                            if (self.do_follow and
                                user_name not in self.dont_include and
                                checked_img and
                                following and
                                not follow_restriction("read", user_name,
                                 self.follow_times, self.logger)):

                                follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder, action=['tag', tag])
                                if follow_state == True:
                                    followed += 1
                            else:
                                self.logger.info('--> Not following')
                                sleep(1)
                        else:
                            already_liked += 1
                    else:
                        self.logger.info(
                            '--> Image not liked: {}'.format(reason.encode('utf-8')))
                        inap_img += 1
                except NoSuchElementException as err:
                    self.logger.error('Invalid Page: {}'.format(err))

        self.logger.info('Tag: {}'.format(tag.encode('utf-8')))
        self.logger.info('Liked: {}'.format(liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Followed: {}'.format(followed))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.liked_img += liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.followed += followed
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self

    def set_do_story(self, enabled = False, percentage = 0, simulate = False):
        """
            configure stories
            enabled: to add story to interact
            percentage: how much to watch
            simulate: if True, we will simulate watching (faster),
                      but nothing will be seen on the browser window
        """
        if self.aborting:
            return self

        self.do_story = enabled
        self.story_percentage = min(percentage,100)
        self.story_simulate = simulate

        return self

    def story_by_users(self, users = None):
        """ Watch stories for specific user(s)"""
        if self.aborting:
            return self

        if users is None:
            self.logger.info("No users passed to story_by_users")
        else:
            # iterate over available users
            for index, user in enumerate(users):
                # Quota Supervisor peak check
                if self.quotient_breach:
                    break

                # inform user whats happening
                if len(users) > 1:
                    self.logger.info('User [{}/{}]'.format(index + 1, len(users)))
                self.logger.info('Loading stories with User --> {}'.format(user.encode('utf-8')))

                try:
                    reels = watch_story(self.browser, user, self.logger, "user", self.story_simulate)
                except NoSuchElementException:
                    self.logger.info('No stories skipping this user')
                    continue
                if reels > 0:
                    self.stories_watched += 1
                    self.reels_watched += reels

    def story_by_tags(self, tags=None):
        """ Watch stories for specific tag(s) """
        if self.aborting:
            return self

        if tags is None:
            self.logger.info("No Tags set")
        else:
            # iterate over available tags
            for index, tag in enumerate(tags):
                # Quota Supervisor peak check
                if self.quotient_breach:
                    break

                # inform user whats happening
                if len(tags) > 1:
                    self.logger.info('Tag [{}/{}]'.format(index + 1, len(tags)))
                self.logger.info('Loading stories with Tag --> {}'.format(tag.encode('utf-8')))

                try:
                    reels = watch_story(self.browser, tag, self.logger, "tag", self.story_simulate)
                except NoSuchElementException:
                    self.logger.info('No stories skipping this tag')
                    continue
                if reels > 0:
                    self.stories_watched += 1
                    self.reels_watched += reels

    def like_by_users(self, usernames, amount=10, randomize=False, media=None, type_of_account='all', gender='all'):
        """Likes some amounts of images for each usernames"""
        if self.aborting:
            return self

        liked_img = 0
        total_liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0
        usernames = usernames or []

        for index, username in enumerate(usernames):

            self.logger.info(
                'Username [{}/{}]'.format(index + 1, len(usernames)))
            self.logger.info('--> {}'.format(username.encode('utf-8')))
            following = random.randint(0, 100) <= self.follow_percentage

            validation, details = self.validate_user_call(username, type_of_account, gender)
            if not validation:
                self.logger.info("--> not a valid user: {}".format(details))
                not_valid_users += 1
                continue

            try:
                links = get_links_for_username(
                    self.browser,
                    username,
                    amount,
                    self.logger,
                    randomize,
                    media)
            except NoSuchElementException:
                self.logger.error('Element not found, skipping this username')
                continue

            if (self.do_follow and
                username not in self.dont_include and
                following and
                not follow_restriction("read", username,
                 self.follow_times, self.logger)):
                follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder)
                if follow_state == True:
                    followed += 1
            else:
                self.logger.info('--> Not following')
                sleep(1)

            if links is False:
                continue

            # Reset like counter for every username
            liked_img = 0

            for i, link in enumerate(links):
                # Check if target has reached
                if liked_img >= amount:
                    self.logger.info('-------------')
                    self.logger.info("--> Total liked image reached it's "
                                     "amount given: {}".format(liked_img))
                    break

                self.logger.info('Post [{}/{}]'.format(liked_img + 1, amount))
                self.logger.info(link)

                try:
                    inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                    if not inappropriate and self.delimit_liking:
                        self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                    if not inappropriate and self.liking_approved:
                        liked = like_image(self.igbooster, self.path_for_igbooster,
                                        link,
                                        self.browser,
                                           user_name,
                                           self.blacklist,
                                           self.logger,
                                           self.logfolder)

                        if liked:
                            total_liked_img += 1
                            liked_img += 1
                            checked_img = True
                            temp_comments = []
                            commenting = random.randint(
                                0, 100) <= self.comment_percentage

                            if self.use_clarifai and (following or commenting):
                                try:
                                    checked_img, temp_comments = (
                                        check_image(self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                    )
                                except Exception as err:
                                    self.logger.error(
                                        'Image check error: {}'.format(err))


                            if (self.do_comment and
                                user_name not in self.dont_include and
                                checked_img and
                                    commenting):

                                if self.delimit_commenting:
                                    self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                if self.commenting_approved:
                                    if temp_comments:
                                        # use clarifai related comments only!
                                        comments = temp_comments
                                    elif is_video:
                                        comments = (self.comments +
                                                    self.video_comments)
                                    else:
                                        comments = (self.comments +
                                                    self.photo_comments)
                                    commented += comment_image(self.igbooster, self.path_for_igbooster,
                                                                link,
                                                                self.browser,
                                                               user_name,
                                                               comments,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder)
                                else:
                                    self.logger.info(disapproval_reason)

                            else:
                                self.logger.info('--> Not commented')
                                sleep(1)

                        else:
                            already_liked += 1

                    else:
                        self.logger.info(
                            '--> Image not liked: {}'.format(reason.encode('utf-8')))
                        inap_img += 1
                except NoSuchElementException as err:
                    self.logger.error('Invalid Page: {}'.format(err))

            if liked_img < amount:
                self.logger.info('-------------')
                self.logger.info("--> Given amount not fullfilled, "
                                 "image pool reached its end\n")

        self.logger.info('User: {}'.format(username.encode('utf-8')))
        self.logger.info('Liked: {}'.format(total_liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.liked_img += liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self

    def interact_by_users(self,
                          usernames,
                          amount=10,
                          randomize=False,
                          media=None, type_of_account='all', gender='all'):
        """Likes some amounts of images for each usernames"""
        if self.aborting:
            return self

        if not isinstance(usernames, list):
            usernames = [usernames]

        total_liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0

        for index, username in enumerate(usernames):
            self.logger.info(
                'Username [{}/{}]'.format(index + 1, len(usernames)))
            self.logger.info('--> {}'.format(username.encode('utf-8')))

            validation, details = self.validate_user_call(username, type_of_account, gender)
            if not validation:
                self.logger.info("--> not a valid user: {}".format(details))
                not_valid_users += 1
                continue

            try:
                links = get_links_for_username(self.browser,
                                               username,
                                               amount,
                                               self.logger,
                                               randomize,
                                               media)
            except NoSuchElementException:
                self.logger.error('Element not found, skipping this username')
                continue

            if links is False:
                continue

            # Reset like counter for every username
            liked_img = 0

            # Will we follow this user?
            following = random.randint(0, 100) <= self.follow_percentage

            for i, link in enumerate(links[:amount]):
                # Check if target has reached
                if liked_img >= amount:
                    self.logger.info('-------------')
                    self.logger.info("--> Total liked image reached it's "
                                     "amount given: {}".format(liked_img))
                    break

                self.logger.info('Post [{}/{}]'.format(liked_img + 1, len(links[:amount])))
                self.logger.info(link)

                try:
                    inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                    if not inappropriate:

                        if (self.do_follow and
                            username not in self.dont_include and
                            following and
                            not follow_restriction("read", username,
                             self.follow_times, self.logger)):

                            follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder)
                            if follow_state == True:
                                followed += 1

                            following = False
                        else:
                            self.logger.info('--> Not following')
                            sleep(1)

                        liking = random.randint(0, 100) <= self.like_percentage

                        if self.do_like and liking and self.delimit_liking:
                            self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                        if self.do_like and liking and self.liking_approved:
                            liked = like_image(self.igbooster, self.path_for_igbooster,
                                            self.browser,
                                               user_name,
                                               self.blacklist,
                                               self.logger,
                                               self.logfolder)
                            if liked:

                                total_liked_img += 1
                                liked_img += 1
                        else:
                            liked = True

                        if liked:
                            checked_img = True
                            temp_comments = []
                            commenting = random.randint(
                                0, 100) <= self.comment_percentage

                            if self.use_clarifai and (following or commenting):
                                try:
                                    checked_img, temp_comments = (
                                        check_image(self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                    )
                                except Exception as err:
                                    self.logger.error(
                                        'Image check error: {}'.format(err))

                            if (self.do_comment and
                                user_name not in self.dont_include and
                                checked_img and
                                    commenting):

                                if self.delimit_commenting:
                                    self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                if self.commenting_approved:
                                    if temp_comments:
                                        # use clarifai related comments only!
                                        comments = temp_comments
                                    elif is_video:
                                        comments = (self.comments +
                                                    self.video_comments)
                                    else:
                                        comments = (self.comments +
                                                    self.photo_comments)
                                    commented += comment_image(self.igbooster, self.path_for_igbooster,
                                                                link,
                                                                self.browser,
                                                               user_name,
                                                               comments,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder)
                                else:
                                    self.logger.info(disapproval_reason)
                            else:
                                self.logger.info('--> Not commented')
                                sleep(1)
                        else:
                            already_liked += 1

                    else:
                        self.logger.info(
                            '--> Image not liked: {}'.format(reason.encode('utf-8')))
                        inap_img += 1
                except NoSuchElementException as err:
                    self.logger.info('Invalid Page: {}'.format(err))

            if liked_img < amount:
                self.logger.info('-------------')
                self.logger.info("--> Given amount not fullfilled, image pool "
                                 "reached its end\n")

        self.logger.info('User: {}'.format(username.encode('utf-8')))
        self.logger.info('Liked: {}'.format(total_liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.liked_img += total_liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.followed += followed
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self
        
    def like_from_image(self, url, amount=50, media=None):
        """Gets the tags from an image and likes 50 images for each tag"""
        if self.aborting:
            return self

        try:
            if not url:
                urls = self.browser.find_elements_by_xpath(
                    "//main//article//div//div[1]//div[1]//a[1]")
                url = urls[0].get_attribute("href")
                self.logger.info("new url {}".format(url))
            tags = get_tags(self.browser, url)
            self.logger.info(tags)
            self.like_by_tags(tags, amount, media)
        except TypeError as err:
            self.logger.error('Sorry, an error occured: {}'.format(err))
            self.aborting = True
            return self

        return self

    def interact_user_followers(self, usernames, amount=10, randomize=False, type_of_account='all', gender='all'):

        if self.aborting:
            return self

        if self.do_follow != True and self.do_like != True:
            self.logger.info("Please enable following or liking in settings in order to do interactions.")
            return self
        elif self.user_interact_amount <= 0:
            self.logger.info("Please choose an amount higher than zero in `set_user_interact` in order to do interactions.")
            return self

        if not isinstance(usernames, list):
            usernames = [usernames]

        interacted_all = 0
        simulated_unfollow = 0
        not_valid_users_initial = self.not_valid_users
        not_valid_users = 0
        liked_img = self.liked_img
        already_liked = self.already_liked
        commented = self.commented
        followed = self.followed
        inap_img = self.inap_img

        for index, user in enumerate(usernames):
            self.logger.info("User '{}' [{}/{}]".format((user), index+1, len(usernames)))
            try:
                person_list, simulated_list = get_given_user_followers(self.browser,
                                                                        self.username,
                                                                        user,
                                                                        amount,
                                                                        self.dont_include,
                                                                        randomize,
                                                                        self.blacklist,
                                                                        self.follow_times,
                                                                        self.simulation,
                                                                        self.logger,
                                                                        self.logfolder)
            except (TypeError, RuntimeWarning) as err:

                if isinstance(err, RuntimeWarning):
                    self.logger.warning(
                        u'Warning: {} , skipping to next user'.format(err))
                    continue

                else:
                    self.logger.error(
                        'Sorry, an error occured: {}'.format(err))
                    self.aborting = True
                    return self

            self.logger.info("Grabbed {} usernames from {}'s `Followers` to do interaction.".format(len(person_list), user))

            interacted_personal = 0

            for index, person in enumerate(person_list):
                self.logger.info("User '{}' [{}/{}]".format((person), index+1, len(person_list)))

                if person in simulated_list:
                    validation, details = self.validate_user_call(person, type_of_account, gender)
                    if validation != True:
                        self.logger.info(details)
                        not_valid_users += 1
                        simulated_unfollow += 1
                        self.logger.info("Simulated unfollow: {}  ~not valid user".format(simulated_unfollow))
                        unfollow_user(self.browser, self.username, person, self.relationship_data, self.logger, self.logfolder)
                        continue
                # Do interactions if any
                do_interact = random.randint(0, 100) <= self.user_interact_percentage
                if do_interact==False:
                    self.logger.info("Skipping user '{}' due to the interaction percentage of {}".format(person, self.user_interact_percentage))
                    continue
                else:
                    interacted_all += 1
                    interacted_personal += 1
                    self.logger.info('Interaction [{}/{}]  |  Total Interaction: {}'.format(interacted_personal, len(person_list), interacted_all))
                    self.interact_by_users(person,
                                            self.user_interact_amount,
                                             self.user_interact_random,
                                              self.user_interact_media)
                    sleep(1)

        self.logger.info(
            "--> Interacted total of {} people\n".format(interacted_all))

        self.not_valid_users += not_valid_users

        #add summary logging to the console
        liked_img_sum = self.liked_img - liked_img
        already_liked_sum = self.already_liked - already_liked
        commented_sum = self.commented - commented
        followed_sum = self.followed - followed
        inap_img_sum = self.inap_img - inap_img
        not_valid_users_sum = self.not_valid_users - not_valid_users_initial

        self.logger.info('Liked: {}'.format(liked_img_sum))
        self.logger.info('Already Liked: {}'.format(already_liked_sum))
        self.logger.info('Commented: {}'.format(commented_sum))
        self.logger.info('Followed: {}'.format(followed_sum))
        self.logger.info('Inappropriate: {}'.format(inap_img_sum))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users_sum))

        return self


    def interact_user_following(self, usernames, amount=10, randomize=False, type_of_account='all', gender='all'):

        if self.aborting:
            return self

        if self.do_follow != True and self.do_like != True:
            self.logger.info("Please enable following or liking in settings in order to do interactions.")
            return self
        elif self.user_interact_amount <= 0:
            self.logger.info("Please choose an amount higher than zero in `set_user_interact` in order to do interactions.")
            return self

        if not isinstance(usernames, list):
            usernames = [usernames]

        interacted_all = 0
        simulated_unfollow = 0
        not_valid_users_initial = self.not_valid_users
        not_valid_users = 0
        liked_img = self.liked_img
        already_liked = self.already_liked
        commented = self.commented
        followed = self.followed
        inap_img = self.inap_img


        for index, user in enumerate(usernames):
            self.logger.info("User '{}' [{}/{}]".format((user), index+1, len(usernames)))
            try:
                person_list, simulated_list = get_given_user_following(self.browser,
                                                                        self.username,
                                                                        user,
                                                                        amount,
                                                                        self.dont_include,
                                                                        randomize,
                                                                        self.blacklist,
                                                                        self.follow_times,
                                                                        self.simulation,
                                                                        self.logger,
                                                                        self.logfolder)
            except (TypeError, RuntimeWarning) as err:

                if isinstance(err, RuntimeWarning):
                    self.logger.warning(
                        u'Warning: {} , skipping to next user'.format(err))
                    continue

                else:
                    self.logger.error(
                        'Sorry, an error occured: {}'.format(err))
                    self.aborting = True
                    return self

            print('')
            self.logger.info("Grabbed {} usernames from {}'s `Following` to do interaction.".format(len(person_list), user))

            interacted_personal = 0

            for index, person in enumerate(person_list):
                self.logger.info("User '{}' [{}/{}]".format((person), index+1, len(person_list)))

                if person in simulated_list:
                    validation, details = self.validate_user_call(person, type_of_account, gender)
                    if validation != True:
                        self.logger.info(details)
                        not_valid_users += 1
                        simulated_unfollow += 1
                        self.logger.info("Simulated unfollow: {}  ~not valid user".format(simulated_unfollow))
                        unfollow_user(self.browser, self.username, person, self.relationship_data, self.logger, self.logfolder)
                        continue
                # Do interactions if any
                do_interact = random.randint(0, 100) <= self.user_interact_percentage
                if do_interact==False:
                    self.logger.info("Skipping user '{}' due to the interaction percentage of {}".format(person, self.user_interact_percentage))
                    continue
                else:
                    interacted_all += 1
                    interacted_personal += 1
                    self.logger.info('Interaction [{}/{}]  |  Total Interaction: {}'.format(interacted_personal, len(person_list), interacted_all))
                    self.interact_by_users(person,
                                            self.user_interact_amount,
                                             self.user_interact_random,
                                              self.user_interact_media)
                    sleep(1)

        self.logger.info(
            "--> Interacted total of {} people\n".format(interacted_all))


        self.not_valid_users += not_valid_users

        #add summary logging to the console
        liked_img_sum = self.liked_img - liked_img
        already_liked_sum = self.already_liked - already_liked
        commented_sum = self.commented - commented
        followed_sum = self.followed - followed
        inap_img_sum = self.inap_img - inap_img
        not_valid_users_sum = self.not_valid_users - not_valid_users_initial

        self.logger.info('Liked: {}'.format(liked_img_sum))
        self.logger.info('Already Liked: {}'.format(already_liked_sum))
        self.logger.info('Commented: {}'.format(commented_sum))
        self.logger.info('Followed: {}'.format(followed_sum))
        self.logger.info('Inappropriate: {}'.format(inap_img_sum))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users_sum))

        return self

    def validate_user_call(self, user_name, type_of_account, gender):
        """Call the validate_username() function"""
        validation, details = validate_username(self.browser,
                                                user_name,
                                                self.username,
                                                self.ignore_users,
                                                self.blacklist,
                                                self.potency_ratio,
                                                self.delimit_by_numbers,
                                                self.max_followers,
                                                self.max_following,
                                                self.min_followers,
                                                self.min_following,
                                                self.min_posts,
                                                self.max_posts,
                                                self.skip_private,
                                                self.skip_private_percentage,
                                                self.skip_no_profile_pic,
                                                self.skip_no_profile_pic_percentage,
                                                self.skip_business,
                                                self.skip_business_percentage,
                                                self.skip_business_categories,
                                                self.dont_skip_business_categories,
                                                self.logger, type_of_account, gender)
        # Story watch
        if validation and watch_user_story(self.story_percentage, self.do_story):
            self.story_by_users([user_name])

        return validation, details

    def follow_user_followers(self,
                              usernames,
                              amount=10,
                              randomize=False,
                              interact=False,
                              sleep_delay=300, type_of_account='all', gender='all'):
        """ Follow the `Followers` of given users """

        message = "Starting to follow user `Followers`.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if not isinstance(usernames, list):
            usernames = [usernames]

        followed_all = 0
        followed_new = 0
        not_valid_users = 0

        # below, you can use some static value `10` instead of random ones..
        relax_point = random.randint(7, 14)

        # hold the current global values for differentiating at the end
        already_followed_init = self.already_followed
        liked_init = self.liked_img
        already_liked_init = self.already_liked
        commented_init = self.commented
        inap_img_init = self.inap_img

        self.quotient_breach = False

        for index, user in enumerate(usernames):
            if self.quotient_breach:
                break

            self.logger.info("User '{}' [{}/{}]".format((user), index + 1, len(usernames)))

            try:
                person_list, simulated_list = get_given_user_followers(
                    self.browser,
                    self.username,
                    user,
                    amount,
                    self.dont_include,
                    randomize,
                    self.blacklist,
                    self.follow_times,
                    self.simulation,
                    self.jumps,
                    self.logger,
                    self.logfolder)

            except (TypeError, RuntimeWarning) as err:
                if isinstance(err, RuntimeWarning):
                    self.logger.warning(
                        u'Warning: {} , skipping to next user'.format(err))
                    continue

                else:
                    self.logger.error(
                        'Sorry, an error occurred: {}'.format(err))
                    self.aborting = True
                    return self

            print('')
            self.logger.info(
                "Grabbed {} usernames from '{}'s `Followers` to do following\n"
                .format(len(person_list), user))

            followed_personal = 0
            simulated_unfollow = 0

            for index, person in enumerate(person_list):
                if self.quotient_breach:
                    self.logger.warning(
                        "--> Follow quotient reached its peak!"
                        "\t~leaving Follow-User-Followers activity\n")
                    break

                self.logger.info(
                    "Ongoing Follow [{}/{}]: now following '{}'..."
                    .format(index + 1,
                            len(person_list),
                            person))

                validation, details = self.validate_user_call(person, type_of_account, gender)
                if validation != True:
                    self.logger.info(details)
                    not_valid_users += 1

                    if person in simulated_list:
                        self.logger.warning(
                            "--> Simulated Unfollow {}: unfollowing"
                            " '{}' due to mismatching validation...\n"
                            .format(simulated_unfollow + 1, person))

                        unfollow_state, msg = unfollow_user(
                            self.browser,
                            "profile",
                            self.username,
                            person,
                            None,
                            None,
                            self.relationship_data,
                            self.logger,
                            self.logfolder)
                        if unfollow_state == True:
                            simulated_unfollow += 1
                    # skip this [non-validated] user
                    continue

                # go ahead and follow, then interact (if any)
                with self.feature_in_feature("follow_by_list", False):
                    followed = self.follow_by_list(person,
                                                   self.follow_times,
                                                   sleep_delay,
                                                   interact, from_u=user)
                sleep(1)

                if followed > 0:
                    followed_all += 1
                    followed_new += 1
                    followed_personal += 1

                self.logger.info("Follow per user: {}  |  Total Follow: {}\n"
                                 .format(followed_personal, followed_all))

                # take a break after a good following
                if followed_new >= relax_point:
                    delay_random = random.randint(
                        ceil(sleep_delay * 0.85),
                        ceil(sleep_delay * 1.14))
                    sleep_time = ("{} seconds".format(delay_random) if
                                  delay_random < 60 else
                                  "{} minutes".format(truncate_float(
                                      delay_random / 60, 2)))
                    self.logger.info(
                        "------=>  Followed {} new users ~sleeping about {}\n"
                        .format(followed_new, sleep_time))
                    sleep(delay_random)
                    relax_point = random.randint(7, 14)
                    followed_new = 0

        # final words
        self.logger.info("Finished following {} users' `Followers`! xD\n"
                         .format(len(usernames)))
        # find the feature-wide action sizes by taking a difference
        already_followed = (self.already_followed - already_followed_init)
        inap_img = (self.inap_img - inap_img_init)
        liked = (self.liked_img - liked_init)
        already_liked = (self.already_liked - already_liked_init)
        commented = (self.commented - commented_init)

        # print results
        self.logger.info("Followed: {}".format(followed_all))
        self.logger.info("Already followed: {}".format(already_followed))
        self.logger.info("Not valid users: {}".format(not_valid_users))

        if interact == True:
            print('')
            # print results out of interactions
            self.logger.info("Liked: {}".format(liked))
            self.logger.info("Already Liked: {}".format(already_liked))
            self.logger.info("Commented: {}".format(commented))
            self.logger.info("Inappropriate: {}".format(inap_img))

        self.not_valid_users += not_valid_users

        return self


    def follow_user_following(self,
                              usernames,
                              amount=10,
                              randomize=False,
                              interact=False,
                              sleep_delay=300, type_of_account='all', gender='all'):

        """ Follow the `Following` of given users """
        if self.aborting:
            return self

        message = "Starting to follow user `Following`.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        """ Follow the `Following` of given users """
        if self.aborting:
            return self

        message = "Starting to follow user `Following`.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if not isinstance(usernames, list):
            usernames = [usernames]

        followed_all = 0
        followed_new = 0
        not_valid_users = 0

        # hold the current global values for differentiating at the end
        already_followed_init = self.already_followed
        not_valid_users_init = self.not_valid_users
        liked_init = self.liked_img
        already_liked_init = self.already_liked
        commented_init = self.commented
        inap_img_init = self.inap_img

        # below, can use a static value instead of from random range..
        relax_point = random.randint(7, 14)
        self.quotient_breach = False

        for index, user in enumerate(usernames):
            if self.quotient_breach:
                break

            self.logger.info("User '{}' [{}/{}]".format((user),
                                                        index + 1,
                                                        len(usernames)))
            try:
                person_list, simulated_list = get_given_user_following(
                    self.browser,
                    self.username,
                    user,
                    amount,
                    self.dont_include,
                    randomize,
                    self.blacklist,
                    self.follow_times,
                    self.simulation,
                    self.jumps,
                    self.logger,
                    self.logfolder)

            except (TypeError, RuntimeWarning) as err:
                if isinstance(err, RuntimeWarning):
                    self.logger.warning(
                        u'Warning: {} , skipping to next user'.format(err))
                    continue

                else:
                    self.logger.error(
                        'Sorry, an error occurred: {}'.format(err))
                    self.aborting = True
                    return self

            print('')
            self.logger.info(
                "Grabbed {} usernames from '{}'s `Following` to do following\n"
                .format(len(person_list), user))

            followed_personal = 0
            simulated_unfollow = 0

            for index, person in enumerate(person_list):
                if self.quotient_breach:
                    self.logger.warning(
                        "--> Follow quotient reached its peak!"
                        "\t~leaving Follow-User-Following activity\n")
                    break

                self.logger.info(
                    "Ongoing Follow [{}/{}]: now following '{}'..."
                    .format(index + 1,
                            len(person_list),
                            person))

                validation, details = self.validate_user_call(person, type_of_account, gender)
                if validation != True:
                    self.logger.info(details)
                    not_valid_users += 1

                    if person in simulated_list:
                        self.logger.warning(
                            "--> Simulated Unfollow {}:"
                            " unfollowing '{}' due to mismatching validation...\n"
                            .format(simulated_unfollow + 1, person))

                        unfollow_state, msg = unfollow_user(
                            self.browser,
                            "profile",
                            self.username,
                            person,
                            None,
                            None,
                            self.relationship_data,
                            self.logger,
                            self.logfolder)
                        if unfollow_state == True:
                            simulated_unfollow += 1
                    # skip the [non-validated] user
                    continue

                # go ahead and follow, then interact (if any)
                with self.feature_in_feature("follow_by_list", False):
                    followed = self.follow_by_list(person,
                                                   self.follow_times,
                                                   sleep_delay,
                                                   interact, from_u=user)
                sleep(1)

                if followed > 0:
                    followed_all += 1
                    followed_new += 1
                    followed_personal += 1

                self.logger.info("Follow per user: {}  |  Total Follow: {}\n"
                                 .format(followed_personal, followed_all))

                # take a break after a good following
                if followed_new >= relax_point:
                    delay_random = random.randint(
                        ceil(sleep_delay * 0.85),
                        ceil(sleep_delay * 1.14))
                    sleep_time = ("{} seconds".format(delay_random) if
                                  delay_random < 60 else
                                  "{} minutes".format(truncate_float(
                                      delay_random / 60, 2)))
                    self.logger.info(
                        "------=>  Followed {} new users ~sleeping about {}\n"
                        .format(followed_new, sleep_time))
                    sleep(delay_random)
                    relax_point = random.randint(7, 14)
                    followed_new = 0

        # final words
        self.logger.info("Finished following {} users' `Following`! xD\n"
                         .format(len(usernames)))

        # find the feature-wide action sizes by taking a difference
        already_followed = (self.already_followed - already_followed_init)
        inap_img = (self.inap_img - inap_img_init)
        liked = (self.liked_img - liked_init)
        already_liked = (self.already_liked - already_liked_init)
        commented = (self.commented - commented_init)

        # print results
        self.logger.info("Followed: {}".format(followed_all))
        self.logger.info("Already followed: {}".format(already_followed))
        self.logger.info("Not valid users: {}".format(not_valid_users))

        if interact == True:
            print('')
            # print results out of interactions
            self.logger.info("Liked: {}".format(liked))
            self.logger.info("Already Liked: {}".format(already_liked))
            self.logger.info("Commented: {}".format(commented))
            self.logger.info("Inappropriate: {}".format(inap_img))

        self.not_valid_users += not_valid_users

        return self


    def unfollow_users(self,
                       amount=10,
                       customList=(False, [], "all"),
                       InstapyFollowed=(False, "all"),
                       nonFollowers=False,
                       allFollowing=False,
                       inactive=(False, 30),
                       style="FIFO",
                       unfollow_after=None,
                       sleep_delay=300,
                       jump4xfollowing=False):
        """Unfollows (default) 10 users from your following list"""

        if self.aborting:
            return self


        message = "Starting to unfollow users.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if unfollow_after is not None:
            if not python_version().startswith(('2.7', '3')):
                self.logger.warning("`unfollow_after` argument is not available for Python versions below 2.7")
                unfollow_after = None

        self.automatedFollowedPool = set_automated_followed_pool(
            self.username,
            unfollow_after,
            self.logger,
            self.logfolder)

        try:
            unfollowNumber = unfollow(self.browser,
                                      self.username,
                                      self.password,
                                      amount,
                                      customList,
                                      InstapyFollowed,
                                      nonFollowers,
                                      allFollowing,
                                      inactive,
                                      style,
                                      jump4xfollowing,
                                      self.automatedFollowedPool,
                                      self.relationship_data,
                                      self.dont_include,
                                      self.white_list,
                                      sleep_delay,
                                      self.jumps,
                                      self.logger,
                                      self.logfolder)
            self.logger.info(
                "--> Total people unfollowed : {}\n".format(unfollowNumber))
            self.unfollowNumber += unfollowNumber

        except Exception as exc:
            if isinstance(exc, RuntimeWarning):
                self.logger.warning(
                    u'Warning: {} , stopping unfollow_users'.format(exc))
                return self
            else:
                self.logger.error('Sorry, an error occured: {}'.format(exc))
                self.aborting = True
                return self

        return self


    def like_by_feed(self, **kwargs):
        """Like the users feed"""
        for i in self.like_by_feed_generator(**kwargs):
            pass
        return self


    def like_by_feed_generator(self,
                     amount=50,
                     randomize=False,
                     unfollow=False,
                     interact=False, type_of_account='all', gender='all'):
        """Like the users feed"""

        if self.aborting:
            return

        liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        skipped_img = 0
        num_of_search = 0
        not_valid_users = 0
        history = []
        link_not_found_loop_error = 0

        while liked_img < amount:
            try:
                # Gets another load of links to be tested
                links = get_links_from_feed(self.browser,
                                            amount,
                                            num_of_search,
                                            self.logger)

                if len(links) > 0:
                    link_not_found_loop_error = 0

                if len(links) == 0:
                    link_not_found_loop_error += 1
                    if link_not_found_loop_error >= 10:
                        self.logger.warning('Loop error, 0 links for for 10 times consecutively, exit loop')
                        break

            except NoSuchElementException:
                self.logger.warning('Too few images, aborting')
                self.aborting = True
                return

            num_of_search += 1

            for i, link in enumerate(links):
                if liked_img == amount:
                    break
                if randomize and random.choice([True, False]):
                    self.logger.warning('Post Randomly Skipped...\n')
                    skipped_img += 1
                    continue
                else:
                    if link in history:
                        self.logger.info('This link has already '
                                         'been visited: {}'
                                         .format(link))
                        continue
                    else:
                        self.logger.info('New link found...')
                        history.append(link)
                        self.logger.info('[{} posts liked /{} amount]'
                                         .format(liked_img, amount))
                        self.logger.info(link)

                        try:
                            inappropriate, user_name, is_video, reason, scope = (
                                check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                            if not inappropriate and self.delimit_liking:
                                self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                            if not inappropriate and self.liking_approved:
                                #validate user
                                validation, details = self.validate_user_call(user_name, type_of_account, gender)
                                if validation != True:
                                    self.logger.info(details)
                                    not_valid_users += 1
                                    continue
                                else:
                                    web_address_navigator(self.browser, link)

                                #try to like
                                liked = like_image(self.igbooster, self.path_for_igbooster,link,
                                                            self.browser,
                                                               user_name,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder)

                                if liked:
                                    username = (self.browser.
                                                find_element_by_xpath(
                                                    '//article/header/div[2]/'
                                                    'div/div[1]/a'))

                                    username = username.get_attribute("title")
                                    name = []
                                    name.append(username)

                                    if interact:
                                        self.logger.info(
                                            '--> User followed: {}'
                                            .format(name))
                                        self.like_by_users(
                                            name,
                                            self.user_interact_amount,
                                            self.user_interact_random,
                                            self.user_interact_media)

                                    liked_img += 1
                                    checked_img = True
                                    temp_comments = []
                                    commenting = random.randint(
                                        0, 100) <= self.comment_percentage
                                    following = random.randint(
                                        0, 100) <= self.follow_percentage

                                    if (self.use_clarifai and
                                            (following or commenting)):
                                        try:
                                            checked_img, temp_comments = (
                                                check_image(
                                                    self.browser,
                                                    self.clarifai_api_key,
                                                    self.clarifai_img_tags,
                                                    self.clarifai_img_tags_skip,
                                                    self.logger,
                                                    self.clarifai_full_match)
                                            )
                                        except Exception as err:
                                            self.logger.error(
                                                'Image check error:'
                                                ' {}'.format(err))

                                    # commenting
                                    if (self.do_comment and
                                        user_name not in self.dont_include and
                                            checked_img and
                                            commenting):
                                        if self.delimit_commenting:
                                            self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                                        if self.commenting_approved:
                                            if temp_comments:
                                                # use clarifai related
                                                # comments only!
                                                comments = temp_comments
                                            elif is_video:
                                                comments = (
                                                    self.comments +
                                                    self.video_comments)
                                            else:
                                                comments = (
                                                    self.comments +
                                                    self.photo_comments)
                                            commented += like_image(self.igbooster, self.path_for_igbooster,link,
                                                            self.browser,
                                                               user_name,
                                                               self.blacklist,
                                                               self.logger,
                                                               self.logfolder)
                                        else:
                                            self.logger.info(disapproval_reason)
                                    else:
                                        self.logger.info('--> Not commented')
                                        sleep(1)

                                    # following
                                    if (self.do_follow and
                                        user_name not in self.dont_include and
                                        checked_img and
                                        following and
                                        not follow_restriction("read", user_name,
                                         self.follow_times, self.logger)):
                                        follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder)
                                        if follow_state == True:
                                            followed += 1
                                    else:
                                        self.logger.info('--> Not following')
                                        sleep(1)

                                    yield self
                                else:
                                    already_liked += 1
                            else:
                                self.logger.info(
                                    '--> Image not liked: {}'.format(reason.encode('utf-8')))
                                inap_img += 1
                                if reason == 'Inappropriate' and unfollow:
                                    unfollow_user(self.browser, self.username, user_name, self.relationship_data, self.logger, self.logfolder)
                        except NoSuchElementException as err:
                            self.logger.error('Invalid Page: {}'.format(err))

        self.logger.info('Liked: {}'.format(liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Followed: {}'.format(followed))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}'.format(not_valid_users))
        self.logger.info('Randomly Skipped: {}\n'.format(skipped_img))

        self.liked_img += liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.followed += followed
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return

    def set_dont_unfollow_active_users(self, enabled=False, posts=4, boundary=500):
        """Prevents unfollow followers who have liked one of
        your latest X posts"""

        # do nothing
        if not enabled:
            return

        # list of users who liked our media
        active_users = get_active_users(self.browser,
                                        self.username,
                                        posts,
                                        boundary,
                                        self.logger)

        # include active user to not unfollow list
        self.dont_include.update(active_users)

    def set_blacklist(self, enabled, campaign):
        """Enable/disable blacklist. If enabled, adds users to a blacklist after
        interact with and adds users to dont_include list"""

        if enabled is False:
            return

        self.blacklist['enabled'] = True
        self.blacklist['campaign'] = campaign

        try:
            with open('{}blacklist.csv'.format(self.logfolder), 'r') as blacklist:
                reader = csv.DictReader(blacklist)
                for row in reader:
                    if row['campaign'] == campaign:
                        self.dont_include.add(row['username'])
        except:
            self.logger.info('Campaign {} first run'.format(campaign))


    def grab_followers(self, username=None, amount=None, live_match=False, store_locally=True):
        """ Gets and returns `followers` information of given user in desired amount, also, saves locally """

        message = "Starting to get the `Followers` data.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if username is None:
            self.logger.warning("Please provide a username to grab `Followers` data  ~e.g. your own username or somebody else's")
            return self
        elif amount is None:
            self.logger.warning("Please put amount to grab `Followers` data")
            return self
        elif amount != "full" and (type(amount) != int or ((type(amount) == int and amount <= 0))):
            self.logger.info("Please provide a valid amount bigger than zero (0) to grab `Followers` data")
            return self

        #Get `followers` data
        grabbed_followers = []
        grabbed_followers = get_followers(self.browser,
                                          username,
                                          amount,
                                          self.relationship_data,
                                          live_match,
                                          store_locally,
                                          self.logger,
                                          self.logfolder)
        return grabbed_followers


    def grab_following(self, username=None, amount=None, live_match=False, store_locally=True):
        """ Gets and returns `following` information of given user in desired amount, also, saves locally """

        message = "Starting to get the `Following` data.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if username is None:
            self.logger.warning("Please provide a username to grab `Following` data  ~e.g. your own username or somebody else's")
            return self
        elif amount is None:
            self.logger.warning("Please put amount to grab `Following` data")
            return self
        elif amount != "full" and (type(amount) != int or ((type(amount) == int and amount <= 0))):
            self.logger.info("Please provide a valid amount bigger than zero (0) to grab `Following` data")
            return self

        #Get `following` data
        grabbed_following = []
        grabbed_following = get_following(self.browser,
                                          username,
                                          amount,
                                          self.relationship_data,
                                          live_match,
                                          store_locally,
                                          self.logger,
                                          self.logfolder)
        return grabbed_following

    @contextmanager
    def feature_in_feature(self, feature, validate_users):
        """
         Use once a host feature calls a guest
        feature WHERE guest needs special behaviour(s)
        """

        try:
            # add the guest which is gonna be used by the host :)
            self.internal_usage[feature] = {"validate": validate_users}
            yield

        finally:
            # remove the guest just after using it
            self.internal_usage.pop(feature)

    def pick_unfollowers(self, username=None, compare_by="latest", compare_track="first", live_match=False, store_locally=True, print_out=True):
        """ Compares the `followers` stored in a latest local copy against
        either lively generated data or previous local copy and returns absent followers """

        message = "Starting to pick Unfollowers of {}..".format(username)
        highlight_print(self.username, message, "feature", "info", self.logger)

        #get all and active Unfollowers
        all_unfollowers, active_unfollowers = get_unfollowers(self.browser,
                                                               username,
                                                                compare_by,
                                                                 compare_track,
                                                                  self.relationship_data,
                                                                   live_match,
                                                                    store_locally,
                                                                     print_out,
                                                                      self.logger,
                                                                       self.logfolder)

        return all_unfollowers, active_unfollowers


    def pick_nonfollowers(self, username=None, live_match=False, store_locally=True):
        """ Returns Nonfollowers data of a given user """

        message = "Starting to pick Nonfollowers of {}..".format(username)
        highlight_print(self.username, message, "feature", "info", self.logger)

        #get Nonfollowers
        nonfollowers = get_nonfollowers(self.browser,
                                         username,
                                         self.password,
                                          self.relationship_data,
                                           live_match,
                                            store_locally,
                                             self.logger,
                                              self.logfolder)

        return nonfollowers




    def pick_fans(self, username=None, live_match=False, store_locally=True):
        """ Returns Fans data- all of the usernames who do follow
        the user WHOM user itself do not follow back"""

        message = "Starting to pick Fans of {}..".format(username)
        highlight_print(self.username, message, "feature", "info", self.logger)

        #get Fans
        fans = get_fans(self.browser,
                         username,
                          self.relationship_data,
                           live_match,
                            store_locally,
                             self.logger,
                              self.logfolder)

        return fans


    def pick_mutual_following(self, username=None, live_match=False, store_locally=True):
        """ Returns Mutual Following data- all of the usernames who do follow
        the user WHOM user itself also do follow back"""

        message = "Starting to pick Mutual Following of {}..".format(username)
        highlight_print(self.username, message, "feature", "info", self.logger)

        #get Mutual Following
        mutual_following = get_mutual_following(self.browser,
                                                 username,
                                                  self.relationship_data,
                                                   live_match,
                                                    store_locally,
                                                     self.logger,
                                                      self.logfolder)

        return mutual_following


    def end(self):
        """Closes the current session"""
        #with interruption_handler():
        #    dump_follow_restriction(self.username, self.logger, self.logfolder)
        #    dump_record_activity(self.username, self.logger, self.logfolder)

        try:
            self.browser.delete_all_cookies()
            self.browser.quit()
        except WebDriverException as exc:
            self.logger.warning('Could not locate Chrome: {}'.format(exc))

        if self.nogui:
            self.display.stop()

        message = "Session ended - {}".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        highlight_print(self.username, message, "end", "info", self.logger)
        print("\n\n")

        with open('{}followed.txt'.format(self.logfolder), 'w') as followFile:
            followFile.write(str(self.followed))


    def follow_by_tags(self,
                     tags=None,
                     amount=50,
                     skip_top_posts=True,
                     use_smart_hashtags=False,
                     randomize=False,
                     media=None, type_of_account='all', gender='all'):
        if self.aborting:
            return self

        inap_img = 0
        followed = 0
        not_valid_users = 0

        # if smart hashtag is enabled
        if use_smart_hashtags is True and self.smart_hashtags is not []:
            print('Using smart hashtags')
            tags = self.smart_hashtags

        # deletes white spaces in tags
        tags = [tag.strip() for tag in tags]
        tags = tags or []
        self.quotient_breach = False

        for index, tag in enumerate(tags):
            if self.quotient_breach:
                break

            self.logger.info('Tag [{}/{}]'.format(index + 1, len(tags)))
            self.logger.info('--> {}'.format(tag.encode('utf-8')))

            try:
                links = get_links_for_tag(self.browser,
                                          tag,
                                          amount,
                                          skip_top_posts,
                                          randomize,
                                          media,
                                          self.logger)
            except NoSuchElementException:
                self.logger.info('Too few images, skipping this tag')
                continue

            for i, link in enumerate(links):
                if (self.jumps["consequent"]["follows"]
                        >= self.jumps["limit"]["follows"]):
                    self.logger.warning("--> Follow quotient reached its peak!"
                                        "\t~leaving Follow-By-Tags activity\n")
                    self.quotient_breach = True
                    # reset jump counter after a breach report
                    self.jumps["consequent"]["follows"] = 0
                    break

                self.logger.info('[{}/{}]'.format(i + 1, len(links)))
                self.logger.info(link)

                try:
                    inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                    if not inappropriate:
                        # validate user
                        validation, details = self.validate_user_call(
                            user_name, type_of_account, gender)
                        if validation != True:
                            self.logger.info(details)
                            not_valid_users += 1
                            continue
                        else:
                            web_address_navigator(self.browser, link)

                        # try to follow
                        follow_state, msg = follow_user(self.browser,
                                                        "post",
                                                        self.username,
                                                        user_name,
                                                        None,
                                                        self.blacklist,
                                                        self.logger,
                                                        self.logfolder, action=['tag', tag])
                        if follow_state == True:
                            followed += 1
                            # reset jump counter after a successful follow
                            self.jumps["consequent"]["follows"] = 0

                        elif msg == "jumped":
                            # will break the loop after certain consecutive jumps
                            self.jumps["consequent"]["follows"] += 1

                    else:
                        self.logger.info(
                            '--> User not followed: {}'.format(reason))
                        inap_img += 1

                except NoSuchElementException as err:
                    self.logger.error('Invalid Page: {}'.format(err))

        self.logger.info('Followed: {}'.format(followed))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.followed += followed
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self



    def interact_by_URL(self,
                         urls=[],
                          randomize=False,
                           interact=False, type_of_account='all', gender='all'):
        """ Interact on posts at given URLs """

        if self.aborting:
            return self

        message = "Starting to interact by given URLs.."
        highlight_print(self.username, message, "feature", "info", self.logger)

        if not isinstance(urls, list):
            urls = [urls]

        if randomize == True:
            random.shuffle(urls)

        liked_img = 0
        already_liked = 0
        inap_img = 0
        commented = 0
        followed = 0
        not_valid_users = 0

        for index, url in enumerate(urls):
            if "https://www.instagram.com/p/" not in url:
                url = "https://www.instagram.com/p/"+url

            self.logger.info('URL [{}/{}]'.format(index + 1, len(urls)))
            self.logger.info('--> {}'.format(url.encode('utf-8')))

            try:
                inappropriate, user_name, is_video, reason, scope = (
                        check_link(self.browser,
                                   link,
                                   self.dont_like,
                                   self.mandatory_words,
                                   self.mandatory_language,
                                   self.is_mandatory_character,
                                   self.mandatory_character,
                                   self.check_character_set,
                                   self.ignore_if_contains,
                                   self.logger))

                if not inappropriate and self.delimit_liking:
                    self.liking_approved = verify_liking(self.browser, self.max_likes, self.min_likes, self.logger)

                if not inappropriate and self.liking_approved:
                    #validate user
                    validation, details = self.validate_user_call(user_name, type_of_account, gender)
                    if validation != True:
                        self.logger.info(details)
                        not_valid_users += 1
                        continue
                    else:
                        web_address_navigator(self.browser, url)

                    #try to like
                    liked = like_image(self.igbooster, self.path_for_igbooster,self.browser,
                                       user_name,
                                       self.blacklist,
                                       self.logger,
                                       self.logfolder)

                    if liked:
                        liked_img += 1
                        checked_img = True
                        temp_comments = []
                        commenting = (random.randint(0, 100) <=
                                      self.comment_percentage)
                        following = (random.randint(0, 100) <=
                                     self.follow_percentage)

                        if self.use_clarifai and (following or commenting):
                            try:
                                checked_img, temp_comments = (
                                    check_image(self.browser,
                                                self.clarifai_api_key,
                                                self.clarifai_img_tags,
                                                self.logger,
                                                self.clarifai_full_match)
                                )
                            except Exception as err:
                                self.logger.error(
                                    'Image check error: {}'.format(err))


                        if (self.do_comment and
                            user_name not in self.dont_include and
                            checked_img and
                                commenting):

                            if self.delimit_commenting:
                                self.commenting_approved, disapproval_reason = verify_commenting(self.browser, self.max_comments, self.min_comments, self.logger)

                            if self.commenting_approved:
                                if temp_comments:
                                    # Use clarifai related comments only!
                                    comments = temp_comments
                                elif is_video:
                                    comments = (self.comments +
                                                self.video_comments)
                                else:
                                    comments = (self.comments +
                                                self.photo_comments)
                                commented += like_image(self.igbooster, self.path_for_igbooster, link, self.browser,
                                                           user_name,
                                                           comments,
                                                           self.blacklist,
                                                           self.logger,
                                                           self.logfolder)
                            else:
                                self.logger.info(disapproval_reason)
                        else:
                            self.logger.info('--> Not commented')
                            sleep(1)

                        if (self.do_follow and
                            user_name not in self.dont_include and
                            checked_img and
                            following and
                            not follow_restriction("read", user_name,
                             self.follow_times, self.logger)):

                            follow_state, msg = follow_user(self.browser,
                                                                "post",
                                                                self.username,
                                                                user_name,
                                                                None,
                                                                self.blacklist,
                                                                self.logger,
                                                                self.logfolder, action=['link', url])
                            if follow_state == True:
                                followed += 1
                        else:
                            self.logger.info('--> Not following')
                            sleep(1)

                        # Check if interaction is expected
                        if interact == True:
                            do_interact = random.randint(0, 100) <= self.user_interact_percentage
                            # Do interactions if any
                            if do_interact and self.user_interact_amount>0:
                                self.logger.info(
                                        '--> Starting to interact {}..'
                                            .format(user_name))
                                self.interact_by_users(user_name,
                                                        self.user_interact_amount,
                                                         self.user_interact_random,
                                                          self.user_interact_media)

                    else:
                        already_liked += 1

                else:
                    self.logger.info(
                        '--> Image not liked: {}'.format(reason.encode('utf-8')))
                    inap_img += 1

            except NoSuchElementException as err:
                self.logger.error('Invalid Page: {}'.format(err))

        self.logger.info('URL: {}'.format(url.encode('utf-8')))
        self.logger.info('Liked: {}'.format(liked_img))
        self.logger.info('Already Liked: {}'.format(already_liked))
        self.logger.info('Commented: {}'.format(commented))
        self.logger.info('Followed: {}'.format(followed))
        self.logger.info('Inappropriate: {}'.format(inap_img))
        self.logger.info('Not valid users: {}\n'.format(not_valid_users))

        self.liked_img += liked_img
        self.already_liked += already_liked
        self.commented += commented
        self.followed += followed
        self.inap_img += inap_img
        self.not_valid_users += not_valid_users

        return self

    def is_mandatory_character(self, uchr):
        if self.aborting:
            return self
        try:
            return self.check_letters[uchr]
        except KeyError:
             return self.check_letters.setdefault(uchr, self.mandatory_character in unicodedata.name(uchr))

    def check_character_set(self, unistr):
        self.check_letters = {}
        if self.aborting:
            return self
        return all(self.is_mandatory_character(uchr)
               for uchr in unistr
               if uchr.isalpha())
