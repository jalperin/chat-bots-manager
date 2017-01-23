import tweepy
import re
import json

import random

from time import sleep

import sqlite3 as lite

import datetime, time, os, sys
import argparse, ConfigParser

import sys
import json
from TwitterChat import TwitterChat
from TwitterWeb import TwitterWeb

Config = ConfigParser.ConfigParser()
Config.read('config.cnf')

consumer_key = Config.get('surveysbot', 'consumer_key')
consumer_secret = Config.get('surveysbot', 'consumer_secret')
access_token = Config.get('surveysbot', 'access_token')
access_token_secret = Config.get('surveysbot', 'access_token_secret')

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
# set up access to the Twitter API
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

#this is the main account we're tweeting from
tweet = api.user_timeline(count = 1)[0]
main_user_id = tweet.user.id
del tweet

consumer_key = Config.get('twittersfupubresearch', 'consumer_key')
consumer_secret = Config.get('twittersfupubresearch', 'consumer_secret')
access_token = Config.get('twittersfupubresearch', 'access_token')
access_token_secret = Config.get('twittersfupubresearch', 'access_token_secret')

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
# set up access to the Twitter API
api2 = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

bot = {}
bot['api'] = TwitterChat('twitter-config')
bot['api'].start()
bot['sel'] = TwitterWeb('twitter-config')
bot['sel'].start()

method = 'api'

def test_mentions():
    t = 'ah ah ah ah staying alive @sfupubresearch, staying alive %s %s' % ( datetime.datetime.now().isoformat(), ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for x in range(8)]))
    testtweet = api.update_status(t)

    print 'Testing mentions at: %s' % datetime.datetime.now().isoformat(), 
    sys.stdout.flush()
    for i in [1,2,3]:
        print '.'*i + ' ', 
        sys.stdout.flush()
        time.sleep(30*i)
        mentions = api2.mentions_timeline(count = 5)
        for mention in mentions: 
            if mention.id == testtweet.id:
                print '%s was mentioned' % testtweet.id
                sys.stdout.flush()
                return True
    
    print 
    print 'mentions not working as of %s' % datetime.datetime.now().isoformat()
    sys.stdout.flush()
    return False

litecon = lite.connect('slate.db')

variants = range(1,7) + range(13,19)
random.shuffle(variants) # so that we don't test variant 1 more than the others on restarts

last_checked_mentions = datetime.datetime(1980, 5, 8) # some date in the past
num_with_method = 0

with litecon:
    litecur = litecon.cursor()
    litecur.execute("SELECT DISTINCT td.user_id_str, td.screen_name, MIN(td.id_str) FROM tweet_data td LEFT JOIN question_data qd ON (td.user_id_str = qd.user_id_str) WHERE qd.variant IS NULL GROUP BY 1, 2 ORDER BY td.created_at")

    users = litecur.fetchall()
    
    for i, user in enumerate(users): 
        #before we start, check mentions
        if (datetime.datetime.now() - last_checked_mentions > datetime.timedelta(hours=1)):
            while not test_mentions():
                time.sleep(60*60) # keep sleeping in 1 hour blocks until it works
            last_checked_mentions = datetime.datetime.now()    
            print 

        user_id_str = user[0]
        screen_name = user[1]
        tweet_id = user[2]

        variant = variants[i % len(variants)]

        tw = lead = question = prepend = append = ''
 
        if (variant <= 12):
            lead = "Please help us understand Slate readers."
        else:
            lead = "You recently tweeted a Slate article, could you tell us:"

        if (variant % 6 == 1 or variant % 6 == 2):
            question = "How do you usually find articles from Slate?"
            altText = "How do you usually find articles from Slate?"
            imageName = './A1.jpeg'

        elif (variant %6 == 3 or variant %6 == 4):
            question = "Is Twitter the way you usually find articles from Slate?"
            altText = "Is Twitter the way you usually find articles from Slate?"
            imageName = './A2.jpeg'

        elif (variant %6 == 5 or variant %6 == 0):
            question = "Do you read Slate Magazine often, sometimes, or never?"
            altText = "Do you read Slate Magazine often, sometimes, or never?"
            imageName = './A3.jpeg'

        if (variant %2 == 1):
            in_reply_to_status_id = tweet_id
            prepend = '@' + screen_name + ' '
            append = "Thanks!"

        else:
            in_reply_to_status_id = None
            append = "Thanks @" + screen_name + "!"

        if (variant % 12 <= 6 and variant % 12 > 0):
            tw = prepend + lead + " " + question + " " + append
        else:
            tw = prepend + lead + " " + append
            
    	try: 
            method = random.choice(['sel', 'api'])
            method = 'sel'

            if in_reply_to_status_id: 
                ret = bot[method].reply_message(tw, str(in_reply_to_status_id))

            else:
                ret = bot[method].send_message(tw)

            if ret == "OK":
                # get the last tweet
                tweet = api.user_timeline(id=main_user_id, count = 1)[0]
                try: 
                    assert(tweet.text == tw)
                except: 
                    sleep(45)
                    tweet = api.user_timeline(id=main_user_id, count = 1)[0]

                print "Just tweeted: %s" % tweet.id

                litecur.execute("INSERT INTO question_data (user_id_str, time_sent, variant, method, tweet_id) VALUES (?,?,?,?,?)", (user_id_str, datetime.datetime.now().isoformat(), variant, method, tweet.id_str))
                litecon.commit()
            else:
                print "PROBLEM: %s" % ret
                print "screen_name: %s" % screen_name
                print "tweet_id: %s" % tweet_id

                litecur.execute("INSERT INTO question_data (user_id_str, time_sent, variant, method) VALUES (?,?,?,?)", (user_id_str, datetime.datetime.now().isoformat(), -1, method))
                litecon.commit()

        except Exception as e: 
            print sys.exc_info()
            print str(e)
            print datetime.datetime.now().isoformat()
            raise

        time.sleep(random.randrange(3*60,5*60))

        if datetime.datetime.now().hour == 4:
            # even bots go to bed
            api.update_status('Goodnight @juancommander. %s' % datetime.datetime.now().isoformat())
            time.sleep(60*60*6)
            bot['sel'].start()
        
