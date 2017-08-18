reddit anti-spam bot

1) in spaminator.py add your account credentials

2) in the same directory as the bot, add a text file named "subreddit_list.txt" that contains the subreddits you want the bot to monitor in the following format:

['subreddit1', 'subreddit2', ...]

3) on each subreddit being monitored, create a wiki called "spaminator" and add the following lines:

	watchers = ['domain', 'submission', 'media']

	domain_whitelist = ['']

	user_whitelist = ['']

	report_percentage = 20

'watchers' tells the bot which anti-spam measures to use. 'domain' checks for suspicious domain activity, 'media' is the media channel spam check system, and 'submission' check for domain submissions at too high of a percentage. For the domain and user whitelist, format the list as ['item1','item2', ...]. report_percentage is the percentage at which a user with more than 10 total submissions will be reported if their submissions for a domain exceed that percentage.