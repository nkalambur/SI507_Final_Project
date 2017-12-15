import re
import psycopg2
import psycopg2.extras
import requests
import requests_oauthlib
import json
import secret_data
import webbrowser
from datetime import datetime
from textblob import TextBlob
import sys
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
import decimal


##### CACHING SETUP #####
##### NOTE: CACHING Code taken from class file oauth1_twitter_caching.py #####
##### NOTE: Code modified to meet project caching requirements #####
#--------------------------------------------------
# Caching constants
#--------------------------------------------------

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DEBUG = True
CACHE_FNAME = "data_cache.json"
CREDS_CACHE_FILE = "creds_cache.json"

#--------------------------------------------------
# Load cache files: data and credentials
#--------------------------------------------------
# Load data cache
try:
    with open(CACHE_FNAME, 'r') as cache_file:
        cache_json = cache_file.read()
        CACHE_DICTION = json.loads(cache_json)
except:
    CACHE_DICTION = {}

# Load creds cache
try:
    with open(CREDS_CACHE_FILE,'r') as creds_file:
        cache_creds = creds_file.read()
        CREDS_DICTION = json.loads(cache_creds)
except:
    CREDS_DICTION = {}

#---------------------------------------------
# Cache functions
#---------------------------------------------
def has_cache_expired(timestamp_str, expire_in_hrs=10):
    """Check if cache timestamp is over expire_in_hrs old"""
    # gives current datetime
    now = datetime.now()

    # datetime.strptime converts a formatted string into datetime object
    cache_timestamp = datetime.strptime(timestamp_str, DATETIME_FORMAT)

    # subtracting two datetime objects gives you a timedelta object
    delta = now - cache_timestamp
    delta_in_hrs = (delta.seconds)/3600
    print("Delta in hours calculated as {}".format(delta_in_hrs))


    # now that we have hours as integers, we can just use comparison
    # and decide if cache has expired or not
    if delta_in_hrs > expire_in_hrs:
        return True # It's been longer than expiry time
    else:
        return False # It's still a valid cache

def get_from_cache(identifier, dictionary):
    """If unique identifier exists in specified cache dictionary and has not expired, 
    return the data associated with it from the request, else return None"""
    identifier = identifier.upper() # Assuming none will differ with case sensitivity here
    if identifier in dictionary:
        data_assoc_dict = dictionary[identifier]
        if has_cache_expired(data_assoc_dict['timestamp'],data_assoc_dict["expire_in_hrs"]):
            if DEBUG:
                print("Cache has expired for {}".format(identifier))
            # also remove old copy from cache
            del dictionary[identifier]
            data = None
        else:
            print("Cache has not epired.")
            data = dictionary[identifier]['values']
    else:
        data = None
    return data


def set_in_data_cache(identifier, data, expire_in_hrs):
    """Add identifier and its associated values (literal data) to the data cache dictionary, and save the whole dictionary to a file as json"""
    identifier = identifier.upper()
    CACHE_DICTION[identifier] = {
        'values': data,
        'timestamp': datetime.now().strftime(DATETIME_FORMAT),
        'expire_in_hrs': expire_in_hrs
    }

    with open(CACHE_FNAME, 'w') as cache_file:
        cache_json = json.dumps(CACHE_DICTION)
        cache_file.write(cache_json)

def set_in_creds_cache(identifier, data, expire_in_hrs):
    """Add identifier and its associated values (literal data) to the credentials cache dictionary, and save the whole dictionary to a file as json"""
    identifier = identifier.upper() # make unique
    CREDS_DICTION[identifier] = {
        'values': data,
        'timestamp': datetime.now().strftime(DATETIME_FORMAT),
        'expire_in_hrs': expire_in_hrs
    }

    with open(CREDS_CACHE_FILE, 'w') as cache_file:
        cache_json = json.dumps(CREDS_DICTION)
        cache_file.write(cache_json)

##### END CACHE FUNCTIONS ####


#### BEGIN CODE TO FETCH DATA FROM API OR CACHE ####

## OAuth1 API Constants - vary by API
### Private data in a hidden secret_data.py file
CLIENT_KEY = secret_data.client_key # what Twitter calls Consumer Key
CLIENT_SECRET = secret_data.client_secret # What Twitter calls Consumer Secret

### Specific to API URLs, not private
REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
BASE_AUTH_URL = "https://api.twitter.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"


def get_tokens(client_key=CLIENT_KEY, client_secret=CLIENT_SECRET,request_token_url=REQUEST_TOKEN_URL,
	base_authorization_url=BASE_AUTH_URL,access_token_url=ACCESS_TOKEN_URL,verifier_auto=True):

    oauth_inst = requests_oauthlib.OAuth1Session(client_key,client_secret=client_secret)

    fetch_response = oauth_inst.fetch_request_token(request_token_url)

    resource_owner_key = fetch_response.get('oauth_token')
    resource_owner_secret = fetch_response.get('oauth_token_secret')

    auth_url = oauth_inst.authorization_url(base_authorization_url)
    # Open the auth url in browser:
    webbrowser.open(auth_url) # For user to interact with & approve access of this app -- enter verifier provided by twitter

    # Deal with required input, which will vary by API
    if verifier_auto: # if the input is default (True), like Twitter
        verifier = input("Please input the verifier:  ")
    else:
        redirect_result = input("Paste the full redirect URL here:  ")
        oauth_resp = oauth_inst.parse_authorization_response(redirect_result) # returns a dictionary -- you may want to inspect that this works and edit accordingly
        verifier = oauth_resp.get('oauth_verifier')

    # Regenerate instance of oauth1session class with more data
    oauth_inst = requests_oauthlib.OAuth1Session(client_key, client_secret=client_secret, resource_owner_key=resource_owner_key, resource_owner_secret=resource_owner_secret, verifier=verifier)

    oauth_tokens = oauth_inst.fetch_access_token(access_token_url) # returns a dictionary

    # Use that dictionary to get these things
    # Tuple assignment syntax
    resource_owner_key, resource_owner_secret = oauth_tokens.get('oauth_token'), oauth_tokens.get('oauth_token_secret')

    return client_key, client_secret, resource_owner_key, resource_owner_secret, verifier

def get_tokens_from_api(service_name_ident, expire_in_hrs=10): # Default: 1 hr for creds expiration
    creds_data = get_from_cache(service_name_ident, CREDS_DICTION)
    if creds_data:
        if DEBUG:
            print("Loading creds from cache...")
            print()
    else:
        if DEBUG:
            print("Fetching fresh credentials...")
            print("Prepare to log in via browser.")
            print()
        creds_data = get_tokens()
        set_in_creds_cache(service_name_ident, creds_data, expire_in_hrs=expire_in_hrs)
    return creds_data

def create_request_identifier(url, params_diction):
    sorted_params = sorted(params_diction.items(),key=lambda x:x[0])
    params_str = "_".join([str(e) for l in sorted_params for e in l]) # Make the list of tuples into a flat list using a complex list comprehension
    total_ident = url + "?" + params_str
    return total_ident.upper() # Creating the identifier

def get_twitter_data(request_url,service_ident, params_diction, expire_in_hrs=10):
    """Check in cache, if not found, load data, save in cache and then return that data"""
    ident = create_request_identifier(request_url, params_diction)
    data = get_from_cache(ident,CACHE_DICTION)
    if data:
        if DEBUG:
            print("Loading from data cache: {}... data".format(ident))
    else:
        if DEBUG:
            print("Fetching new data from {}".format(request_url))
        # Get credentials
        client_key, client_secret, resource_owner_key, resource_owner_secret, verifier = get_tokens_from_api(service_ident)
        # Create a new instance of oauth to make a request with
        oauth_inst = requests_oauthlib.OAuth1Session(client_key, client_secret=client_secret,resource_owner_key=resource_owner_key,
        	resource_owner_secret=resource_owner_secret)
        # Call the get method on oauth instance
        # Work of encoding and "signing" the request happens behind the sences, thanks to the OAuth1Session instance in oauth_inst
        resp = oauth_inst.get(request_url,params=params_diction)
        # Get the string data and set it in the cache for next time
        string_of_response = resp.text
        data = json.loads(string_of_response)
        set_in_data_cache(ident, data, expire_in_hrs)
    return data
#### END CODE TO FETCH DATA/TOKENS FROM API OR CACHE ####

#### BEGIN CODE TO DEFINE CLASS TO PROCESS DATA FETCHED FROM TWITTER ####

class twitter_handler(object):
	def __init__(self, dict_object):
		self.text = dict_object['text']
		self.tweet_id = dict_object['id_str']
		self.mentions = [x['screen_name'] for x in dict_object['entities']['user_mentions']]
		self.in_reply_to_screen_name = dict_object['in_reply_to_screen_name']
		self.user_screen_name = dict_object['user']['screen_name']
		self.user_name = dict_object['user']['name']
		self.retweet_count = dict_object['retweet_count']
		self.hashtags = [x for x in dict_object['entities']['hashtags']]
		self.timestamp_UTC = dict_object['created_at']

	def get_sentiment_score(self):
		# leverage textblob.TextBlob PatternAnalyzer approach
		# function should return a dict of Sentiment(polarity, classification)
		blob = TextBlob(self.text)

		sentiment_resp = {}
		sentiment_resp['score'] = blob.sentiment.polarity
		sentiment_resp['subjectivity'] = blob.sentiment.subjectivity
		#if 
		if sentiment_resp['score'] >= 0.5:
			sentiment_resp['classification'] = "Very Positive"
		elif sentiment_resp['score'] > 0 and sentiment_resp['score'] < 0.5:
			sentiment_resp['classification'] = "Positive"
		elif sentiment_resp['score'] <= -0.5:
			sentiment_resp['classification'] = "Very Negative"
		elif sentiment_resp['score'] < 0 and sentiment_resp['score'] > -0.5:
			sentiment_resp['classification'] = "Negative"
		elif sentiment_resp['score'] == 0:
			sentiment_resp['classification'] = "Neutral"
		#sentiment_resp['classification'] = classification

		return sentiment_resp

	def __contains__(self, input_str):
		if input_str in self.text:
			return True
		else:
			return False

	def __repr__(self):
		return 'Tweet by {} With {} Retweets'.format(self.user_screen_name, self.retweet_count)

	def __str__(self):
		return 'This is a tweet with ID: {}'.format(self.tweet_id)

#### BEGIN CODE FOR SQL FUNCTIONS ####
#### WILL BE CREATING 2 TABLES: TWEETS (W/ SENTIMENT SCORE) & trump_MENTIONS ####
DB_NAME = secret_data.db_name
DB_USER = secret_data.db_user
DB_PASSWORD = secret_data.db_password
#### CODE TO ESTABLISH CONNECTION & CURSOR #####
def get_connection_and_cursor(db_name, db_password, db_user):
    try:
        if db_password != "":
            db_connection = psycopg2.connect("dbname='{0}' user='{1}' password='{2}'".format(db_name, db_user, db_password))
            print("Success connecting to database")
        else:
            db_connection = psycopg2.connect("dbname='{0}' user='{1}'".format(db_name, db_user))
    except:
        print("Unable to connect to the database. Check server and credentials.")
        sys.exit(1) # Stop running program if there's no db connection.

    db_cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    return db_connection, db_cursor

#### CODE TO SET UP DATABASE WITH TABLES ####
def setup_database(db_name, db_password, db_user):
	conn, cur = get_connection_and_cursor(db_name, db_password, db_user)
	print("Connection Established")

	commands = [
		"""
		DROP TABLE IF EXISTS trump_mentions
		""",
		"""
		DROP TABLE IF EXISTS tweets
		""",
		"""
		CREATE TABLE tweets (
			id VARCHAR(50) UNIQUE,
			tweet_text VARCHAR(200),
			in_reply_to VARCHAR(200),
			sentiment_score NUMERIC,
			sentiment_classification VARCHAR(20),
			retweet_count INT,
			user_screen_name VARCHAR(50),
			user_name VARCHAR(50)
			)
		""",
		"""
		CREATE TABLE trump_mentions (
			parent_tweet_id VARCHAR(50) references tweets(id),
			user_screen_name VARCHAR(50)
			)
		"""
	]
			# user_name VARCHAR(50),
			# indices VARCHAR(15),
			# user_id INT
	# print("About to execute sql commands")
	for sql_command in commands:
		cur.execute(sql_command)
		# print("1 command executed")
	conn.commit()
	print("##### 2 SQL tables created #####")

def insert_into_tweets(dict_object, db_name, db_password, db_user):
	conn, cur = get_connection_and_cursor(db_name,db_password, db_user)
	#counter=0
	for tweet in dict_object:
		row = twitter_handler(tweet)
		cur.execute("""INSERT INTO tweets (id, tweet_text, in_reply_to, sentiment_score, sentiment_classification, retweet_count, user_screen_name, user_name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
			(row.tweet_id,
			row.text,
			row.in_reply_to_screen_name,
			row.get_sentiment_score()['score'],
			row.get_sentiment_score()['classification'],
			row.retweet_count,
			row.user_screen_name,
			row.user_name)
			)
		# counter=counter+1
	conn.commit()
	#print("{} Rows Inserted Into tweets table".format(counter))

def insert_into_trump_mentions(dict_object, db_name, db_password, db_user):
	conn, cur = get_connection_and_cursor(db_name, db_password, db_user)

	for tweet in dict_object:
		row = twitter_handler(tweet)
		for mention in row.mentions:
			cur.execute("""INSERT INTO trump_mentions (parent_tweet_id, user_screen_name) VALUES (%s, %s)""", 
				(row.tweet_id, 
				mention)
			)
		conn.commit()

### SOME SQL FUNCTIONS TO FETCH DATA ####
def fetch_avg_retweet_count_trump_tweets_by_classification(db_name, db_password, db_user):
	conn, cur = get_connection_and_cursor(db_name, db_password, db_user)
	sql = "SELECT sentiment_classification, AVG(retweet_count) FROM tweets WHERE user_screen_name = 'realDonaldTrump' GROUP BY sentiment_classification"
	cur.execute(sql)
	x_axis = []
	y_axis = []
	for row in cur.fetchall():
		x_axis.append(row['sentiment_classification'])
		y_axis.append(int(row['avg']))
	conn.commit()
	print(len(x_axis), 'records returned')
	return x_axis, y_axis

### Most recent 100 tweets about Trump - sentiment score plot vs retweets
def fetch_sentiment_retweets_abtrump(db_name, db_password, db_user):
	conn, cur = get_connection_and_cursor(db_name, db_password, db_user)
	sql = "SELECT sentiment_score, retweet_count FROM tweets WHERE user_screen_name <> 'realDonaldTrump'"
	cur.execute(sql)
	x_axis = []
	y_axis = []
	for row in cur.fetchall():
		x_axis.append(int(row['retweet_count']))
		y_axis.append(decimal.Decimal(row['sentiment_score']))
	conn.commit()
	print(len(x_axis), ' records returned')
	return x_axis, y_axis

if __name__ == "__main__":
	if not CLIENT_KEY or not CLIENT_SECRET:
		print("You need to fill in client_key and client_secret in the secret_data.py file.")
		exit()
	if not REQUEST_TOKEN_URL or not BASE_AUTH_URL:
		print("You need to fill in this API's specific OAuth2 URLs in this file.")
	if not DB_NAME or not DB_USER:
		print("You need to create a database named (default is 'SI507_Final_Project') and fill in the db_name and db_user in the secret_data.py file accordingly")
		exit()

    # Invoke functions
	twitter_search_term_baseurl = "https://api.twitter.com/1.1/search/tweets.json"
	twitter_search_term_params = {"q":"Donald Trump", "count":100}
	twitter_search_user_baseurl = "https://api.twitter.com/1.1/statuses/user_timeline.json"
	twitter_search_user_params = {"screen_name":"@realdonaldtrump", "count":199}

	print("#########\nFetching Tweets about Trump\n#########")
	twitter_search_trump = get_twitter_data(twitter_search_term_baseurl,"Twitter",twitter_search_term_params)
	print(len(twitter_search_trump['statuses']), 'tweets returned') # Default expire_in_hrs
	print("#########\nFetching Tweets by Trump\#########")
	twitter_by_trump = get_twitter_data(twitter_search_user_baseurl, "Twitter", twitter_search_user_params)
	print(len(twitter_by_trump), 'tweets returned')
	# t = twitter_handler(twitter_search_trump['statuses'][0])
	# print(t.get_sentiment_score()	)
	# print(type(t.get_sentiment_score()['score']))
	# print (repr(t))
	# print(str(t))

	# for tweet in twitter_search_trump['statuses']:
	# 	t = twitter_handler(tweet)
	# 	print(t.get_sentiment_score())
		# print(t.user_name, t.user_screen_name, t.tweet_id, t.in_reply_to_screen_name, t.retweet_count,t.get_sentiment_score()['score'],t.get_sentiment_score()['classification'])
		# print("#####################")
	# for tweet in twitter_by_trump:
	# 	tt = twitter_handler(tweet)
		# print(tt.mentions)
		# print(tt.text)
		# print(tt.get_sentiment_score()['classification'])
	print("#########\nClearing Database\n#########")
	setup_database(DB_NAME, DB_PASSWORD, DB_USER)
	print("#########\nDatabase Restaged\n#########\nInsert Tweets about Trump\n#########")
	insert_into_tweets(twitter_search_trump['statuses'], DB_NAME, DB_PASSWORD, DB_USER)
	print("#########\nInsert Tweets by Trump\n#########")
	insert_into_tweets(twitter_by_trump, DB_NAME, DB_PASSWORD, DB_USER)
	print("#########\nInserting Users Mentioned By Trump\n#########")
	insert_into_trump_mentions(twitter_by_trump, DB_NAME, DB_PASSWORD, DB_USER)
	print("#########\nSQL Tables Populated\n#########")
	## VISUALS ####
	## WILL NEED TO FETCH FROM SQL TO PUSH TO PLOTLY ####
	plotly.tools.set_credentials_file(username=secret_data.plotly_username, api_key=secret_data.plotly_api_key)
	
	#### STARTING WITH BAR CHART OF AVG RETWEET COUNT AGAINST CLASSIFIER FOR TRUMP TWEETS ####
	tweet_sentiment, avg_retweet = fetch_avg_retweet_count_trump_tweets_by_classification(DB_NAME, DB_PASSWORD, DB_USER)

	data = [go.Bar(
		x = tweet_sentiment,
		y = avg_retweet
		)]
	layout = go.Layout(title="Average Retweet Count by Sentiment Classification for Last 199 Tweets by President Trump",
		xaxis=dict(title='Sentiment Classification'),
		yaxis=dict(title='Average Retweet Count')
		)
	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='Avg Retweet Count by Sentiment Category')
	#### Sentiment scores vs retweet counts 
	x, y = fetch_sentiment_retweets_abtrump(DB_NAME, DB_PASSWORD, DB_USER)
	trace = go.Scatter(
		x = y,
		y = x,
		mode = 'markers',
		marker =dict(size='10')
		)
	layout2 = go.Layout(
		title="Retweet Counts vs Sentiment Scores for Last 100 Tweets about President Trump",
		xaxis=dict(title='Sentiment Score'),
		yaxis=dict(title='Retweet Count')
		)
	data2 = [trace]
	fig = go.Figure(data=data2, layout=layout2)
	py.plot(fig, filename="Sentiment Scores vs Retweet Counts for Last 100 Tweets about President Trump")


