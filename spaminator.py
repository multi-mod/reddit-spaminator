import praw
import prawcore
import time
import ast
import os

#initializing praw
reddit = praw.Reddit(client_id='',
                     client_secret='',
                     password='',
                     user_agent='',
                     username='')

#functions
def percentage_check(total_submissions, domain_submissions, report, remove):
    
    if total_submissions < 3:
        return 'pass'
    
    percentage = int((domain_submissions / total_submissions) * 100)
    
    if remove == False:
        if percentage < report:
            return 'pass'
    if remove != False:
        if percentage < report and percentage < remove:
            return 'pass'
    
    if total_submissions >= 3 and total_submissions <= 5:
        if percentage >= 60:
            return 'report'
    
    elif total_submissions > 5 and total_submissions < 10:
        if percentage >= 50:
            return 'report'
    
    elif total_submissions >= 10:
        if remove == False:
            if percentage >= report:
                return 'report'
        if remove != False:
            if percentage >= remove:
                return 'remove'
    
    else:
        return 'pass'

def subreddit_list():

    subreddit_list = os.getcwd() + '\subreddit_list.txt'

    with open(subreddit_list) as f:
        subs = [x for x in f][0]
    subs = ast.literal_eval(subs)

    return(subs)
    
#classes
class spam_check:
      
    def __init__(self):
        
        self.log = {}
        self.settings = {}
    
    def get_settings(self, subreddit):
        
        self.subreddit = subreddit
        self.settings[self.subreddit] = {}
        
        try:
            self.wiki = reddit.subreddit(self.subreddit).wiki['spaminator'].content_md
            self.exists = True
        except prawcore.exceptions.NotFound:
            self.exists = False
        
        if self.exists is True:
            self.wiki = self.wiki.split('\n')
            self.wiki = [x.strip('\r') for x in self.wiki if x != '\r']
            
            try:
                self.settings[self.subreddit]['domain_whitelist'] = ast.literal_eval([x.split(' = ') for x in self.wiki if x.startswith('domain_whitelist') is True][0][1])
            except IndexError:
                self.settings[self.subreddit]['domain_whitelist'] = []
            try:
                self.settings[self.subreddit]['user_whitelist'] = ast.literal_eval([x.split(' = ') for x in self.wiki if x.startswith('user_whitelist') is True][0][1])
            except IndexError:
                self.settings[self.subreddit]['user_whitelist'] = []
            try:
                self.settings[self.subreddit]['report_percentage'] = int([x.split(' = ') for x in self.wiki if x.startswith('report_percentage') is True][0][1])
            except IndexError:
                self.settings[self.subreddit]['report_percentage'] = 20
            try:
                self.settings[self.subreddit]['watchers'] = ast.literal_eval([x.split(' = ') for x in self.wiki if x.startswith('watchers') is True][0][1])
            except IndexError:
                self.settings[self.subreddit]['watchers'] = ['submission','media','domain']
            try:
                self.settings[self.subreddit]['remove_percentage'] = int([x.split(' = ') for x in self.wiki if x.startswith('remove_percentage') is True][0][1])
            except IndexError:
                self.settings[self.subreddit]['remove_percentage'] = False
        
        if self.exists is False:
            self.settings[self.subreddit] = {}
            self.settings[self.subreddit]['domain_whitelist'] = []
            self.settings[self.subreddit]['user_whitelist'] = []
            self.settings[self.subreddit]['report_percentage'] = 20
            self.settings[self.subreddit]['remove_percentage'] = False
            self.settings[self.subreddit]['watchers'] = ['submission','media','domain']

    def new_posts(self, limit):
        
        self.limit = limit
        
        try:
            self.log[self.subreddit]
        except KeyError:
            self.log[self.subreddit] = []
        
        self.new = reddit.subreddit(self.subreddit).new(limit=self.limit)
        self.new = [x for x in self.new if x.id not in self.log[self.subreddit]]

        self.log[self.subreddit].extend([x.id for x in self.new])
        if len(self.log[self.subreddit]) > 50:
            self.log[self.subreddit] = self.log[self.subreddit][:-50]
    
    def submission_spam(self, limit):
        
        self.limit = limit
        
        if 'submission' not in self.settings[self.subreddit]['watchers']:
            return
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.domain in self.settings[self.subreddit]['domain_whitelist']:
                continue
            if post.author.name in self.settings[self.subreddit]['user_whitelist']:
                continue
            if post.is_self is True:
                continue
            
            self.author_submissions = post.author.submissions.new(limit=self.limit)
            self.author_submissions = [x for x in self.author_submissions]
            
            if len(self.author_submissions) == 0:
                continue
            
            self.submitted_domains = [x.domain for x in self.author_submissions]
            
            self.total_submissions = len(self.author_submissions)
            self.domain_submissions = self.submitted_domains.count(post.domain)
            
            self.check = percentage_check(self.total_submissions,
                                          self.domain_submissions,
                                          self.settings[self.subreddit]['report_percentage'],
                                          self.settings[self.subreddit]['remove_percentage'])
            
            if self.check == 'pass':
                continue
            
            if self.check == 'report':
                self.report_reason = 'domain spam: ' + post.domain + ' ' + str(int((self.domain_submissions / self.total_submissions)*100)) + '%'
                #print('/u/' + post.author.name + ', ' + self.report_reason)
                post.report(reason=self.report_reason)
            
            if self.check == 'remove':
                pass
    
    def media_spam(self, limit):
        
        self.limit = limit
        
        if 'media' not in self.settings[self.subreddit]['watchers']:
            return
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.is_self is True:
                continue
            if post.author.name in self.settings[self.subreddit]['user_whitelist']:
                continue
            if post.media is None:
                continue
            try:
                post.media['oembed']['author_name']
            except KeyError:
                continue

            self.author_submissions = post.author.submissions.new(limit=self.limit)
            self.author_submissions = [x for x in self.author_submissions]
            
            if len(self.author_submissions) == 0:
                continue
            
            self.media_submissions = [x.media for x in self.author_submissions if x.media is not None]
            
            if len(self.media_submissions) == 0:
                continue
            
            self.media_authors = []
            for submission in self.media_submissions:
                try:
                    self.media_authors.append(submission['oembed']['author_name'])
                except KeyError:
                    pass
                except TypeError:
                    pass
            
            self.total_submissions = len(self.author_submissions)
            self.media_author_submissions = self.media_authors.count(post.media['oembed']['author_name'])
            
            self.check = percentage_check(self.total_submissions,
                                          self.media_author_submissions,
                                          self.settings[self.subreddit]['report_percentage'],
                                          self.settings[self.subreddit]['remove_percentage'])
            
            if self.check == 'pass':
                continue
            
            if self.check == 'report':
                self.report_reason = 'media spam: ' + post.media['oembed']['author_name'] + ' ' + str(int((self.media_author_submissions / self.total_submissions)*100)) + '%'
                #print('/u/' + post.author.name + ', ' + self.report_reason)
                post.report(reason=self.report_reason)
            
            if self.check == 'remove':
                pass
    
    def suspicious_domain(self, limit):
        
        self.limit = limit
        
        if 'domain' not in self.settings[self.subreddit]['watchers']:
            return
        
        for post in self.new:
            
            try:
                reddit.redditor(post.author.name).id
            except AttributeError:
                continue
            if post.is_self is True:
                continue
            if post.author.name in self.settings[self.subreddit]['user_whitelist']:
                continue     
            if post.domain in self.settings[self.subreddit]['domain_whitelist']:
                continue
            
            self.domain_new = reddit.domain(post.domain).new(limit=self.limit)
            self.domain_new = [x for x in self.domain_new]
            
            if len(self.domain_new) == 0:
                continue
            
            self.domain_authors = [x.author.name for x in self.domain_new if x.author is not None]
            
            self.author_domain_connection = self.domain_authors.count(post.author.name)
            self.domain_submission_numbers = len(self.domain_new)
            self.percentage = int((self.author_domain_connection / self.domain_submission_numbers)*100)
            
            if self.domain_submission_numbers >= 3 and self.domain_submission_numbers <= 5:
                if self.percentage == 100:
                    self.report_reason = 'domain mostly submitted by user: ' + str(self.percentage) + '%'
                    #print('/u/' + post.author.name + ', ' + self.report_reason)
                    post.report(reason=self.report_reason)
            
            if self.domain_submission_numbers > 5:
                if self.percentage >= 50:
                    self.report_reason = 'domain mostly submitted by user: ' + str(self.percentage) + '%'
                    #print('/u/' + post.author.name + ', ' + self.report_reason)
                    post.report(reason=self.report_reason)
            
        
if __name__ == '__main__':

    analysis = spam_check()
    
    while True:
        
        try:
        
            subreddits = subreddit_list()
    
            for subreddit in subreddits:
                analysis.get_settings(subreddit)
                analysis.new_posts(limit=25)
                analysis.submission_spam(limit=1000)
                analysis.media_spam(limit=1000)
                analysis.suspicious_domain(limit=1000)
                time.sleep(10)
        
        except Exception:
           print('general exception, sleeping 60s')
           time.sleep(60)
        
        except praw.exceptions.PRAWException:
            print('praw exception, sleeping 60s')
            time.sleep(60)
        
        except prawcore.PrawcoreException:
            print('prawcore exception, sleeping 60s')
            time.sleep(60)