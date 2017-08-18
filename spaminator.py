import praw
import prawcore
import time
import ast
import os
from collections import deque

#initializing praw
reddit = praw.Reddit(client_id='',
                     client_secret='',
                     password='',
                     user_agent='',
                     username='')

#functions
def subreddit_list():

    subreddit_list = os.path.join(os.getcwd(), 'subreddit_list.txt')

    with open(subreddit_list) as f:
        subs = [x for x in f][0]
    subs = ast.literal_eval(subs)

    return(subs)
    
#classes
class SpamCheck(object):
      
    def __init__(self, subreddit):
        
        self.subreddit = subreddit
        self.log = deque(maxlen=50)
    
    def get_settings(self):
        
        try:
            wiki = reddit.subreddit(self.subreddit).wiki['spaminator'].content_md
        except prawcore.exceptions.NotFound:
            pass
        
        wiki_settings = {}
        for line in wiki:
            setting_name, _, value = line.partition('=')
            wiki_settings[setting_name.strip()] = ast.literal_eval(value.strip())

        default_settings = {
            'domain_whitelist': [],
            'user_whitelist': [],
            'report_percentage': 20,
            'remove_percentage': None,
            'watchers': ['submission', 'media', 'domain'],
        }

        self.settings = {
            key: wiki_settings.get(key, default_settings[key])
            for key in default_settings
        }
        
        for setting in ['domain_whitelist','user_whitelist','watchers']:
            self.settings[setting] = set(self.settings[setting])

    def new_posts(self, limit):
        
        limit = limit
        
        new = reddit.subreddit(self.subreddit).new(limit=limit)
        self.new = [x for x in new if x.id not in self.log]

        self.log.extend([x.id for x in self.new])

    def call_watchers(self, limit):
        
        limit=limit
        watchers = self.settings['watchers']
        
        if 'submission' in watchers:
            self.submission_spam(limit=limit)
        if 'media' in watchers:
            self.media_spam(limit=limit)
        if 'domain' in watchers:
            self.suspicious_domain(limit=limit)
    
    def submission_spam(self, limit):
        
        limit = limit
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.domain in self.settings['domain_whitelist']:
                continue
            if post.author.name in self.settings['user_whitelist']:
                continue
            if post.is_self is True:
                continue
            
            author_submissions = list(post.author.submissions.new(limit=limit))
            
            if len(author_submissions) == 0:
                continue
            
            self.total_submissions = len(author_submissions)
            submitted_domains = [x.domain for x in author_submissions]
            domain_submissions = submitted_domains.count(post.domain)
            
            self.percentage = int((domain_submissions / self.total_submissions) * 100)
            
            if self.should_report():
                report_reason = 'domain spam: ' + post.domain + ' ' + str(self.percentage) + '%'
                post.report(reason=report_reason)
                        
            if self.should_remove():
                pass
    
    def media_spam(self, limit):
        
        limit = limit
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.is_self is True:
                continue
            if post.author.name in self.settings['user_whitelist']:
                continue
            if post.media is None:
                continue
            try:
                post.media['oembed']['author_name']
            except KeyError:
                continue

            author_submissions = list(post.author.submissions.new(limit=self.limit))
            
            if len(author_submissions) == 0:
                continue
            
            media_submissions = [x.media for x in author_submissions if x.media is not None]
            
            if len(media_submissions) == 0:
                continue
            
            media_authors = []
            for submission in media_submissions:
                try:
                    media_authors.append(submission['oembed']['author_name'])
                except KeyError:
                    pass
                except TypeError:
                    pass
            
            self.total_submissions = len(author_submissions)
            media_author_submissions = media_authors.count(post.media['oembed']['author_name'])
            
            self.percentage = int((media_author_submissions / self.total_submissions) * 100)
            
            if self.should_report():
                self.report_reason = 'media spam: ' + post.media['oembed']['author_name'] + ' ' + str(self.percentage) + '%'
                post.report(reason=self.report_reason)
                        
            if self.should_remove():
                pass
    
    def suspicious_domain(self, limit):
        
        limit = limit
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.is_self is True:
                continue
            if post.author.name in self.settings['user_whitelist']:
                continue     
            if post.domain in self.settings['domain_whitelist']:
                continue
            
            domain_new = list(reddit.domain(post.domain).new(limit=self.limit))
            
            if len(domain_new) == 0:
                continue
            
            domain_authors = [x.author.name for x in domain_new if x.author is not None]
            
            author_domain_connection = domain_authors.count(post.author.name)
            domain_submission_numbers = len(domain_new)
            
            percentage = int((author_domain_connection / domain_submission_numbers)*100)
            
            if 3 <= domain_submission_numbers <= 5:
                if percentage == 100:
                    report_reason = 'domain mostly submitted by user: ' + str(percentage) + '%'
                    post.report(reason=report_reason)
            
            if domain_submission_numbers > 5:
                if percentage >= 50:
                    report_reason = 'domain mostly submitted by user: ' + str(percentage) + '%'
                    post.report(reason=report_reason)
                    
    def should_report(self):
        
        if 3 <= self.total_submissions <= 5:
            if self.percentage >= 60:
                return True
        
        elif 5 < self.total_submissions < 10:
            if self.percentage >= 50:
                return True
        
        elif self.total_submissions >= 10:
            if self.settings['remove_percentage'] is None:
                if self.percentage >= self.settings['report_percentage']:
                    return True
            if self.settings['remove_percentage'] is not None:
                if self.percentage >= self.settings['remove_percentage']:
                    return False
        
        else:
            return False

    def should_remove(self):
        
        if self.settings['remove_percentage'] is None:
            return False
        
        elif self.total_submissions >= 10:
            if self.percentage >= self.settings['remove_percentage']:
                return True
        
        else:
            return False
        
if __name__ == '__main__':

    subreddits = None
    
    while True:
        
        try:
            if subreddits is None:
                subreddits = subreddit_list()
                spam_checkers = {subreddit: SpamCheck(subreddit) for subreddit in subreddits}
            else:
                new_list_check = subreddit_list()
                if new_list_check == subreddits:
                    continue
                spam_checkers = {subreddit: SpamCheck(subreddit) for subreddit in subreddits}
    
            for subreddit in subreddits:
                spam_checkers[subreddit].get_settings(subreddit)
                spam_checkers[subreddit].new_posts(limit=25)
                spam_checkers[subreddit].call_watchers(limit=1000)
                time.sleep(10)
        
        except KeyboardInterrupt:
           raise
        
        except:
            print('exception, sleeping 60s')
            time.sleep(60)
