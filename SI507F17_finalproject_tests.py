import unittest
from SI507F17_finalproject import *
from secret_data import *

## class 1
class Tests_Class(unittest.TestCase):
	# Method 1
	def setUp(self):
		self.url = "https://api.twitter.com/1.1/search/tweets.json"
		self.params = {"q":"Donald Trump", "count":100}

		# API Fetch
		self.data = get_twitter_data(self.url,"Twitter",self.params)

		# Process into class
		self.cl = twitter_handler(self.data['statuses'][0])

		print("Setting up for Class tests")

	def test_class_constr_str_1(self):
	# method 2
		self.assertIsInstance(self.cl.tweet_id, str)
		self.assertIsInstance(self.cl.text, str)

	def test_class_constr_lists_2(self):
	# method 3
		self.assertIsInstance(self.cl.mentions, list)

	def test_class_sentiment_dict_method_3(self):
		self.assertIsInstance(self.cl.get_sentiment_score(), dict)

	def test_class_sentiment_keys_method_4(self):
		self.assertTrue(self.cl.get_sentiment_score()['score'])
		self.assertTrue(self.cl.get_sentiment_score()['classification'])
		self.assertTrue(self.cl.get_sentiment_score()['subjectivity'])

	def test_class_sentiment_vals_method_5(self):
		self.assertIsInstance(self.cl.get_sentiment_score()['score'], float)

	def test_class_sentiment_vals_method_6(self):
		self.assertIsInstance(self.cl.get_sentiment_score()['classification'], str)

	def test_class_sentiment_vals_method_7(self):
		self.assertTrue(self.cl.get_sentiment_score()['classification'] in ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'])

	def test_class_contains_method_8(self):
		self.assertTrue('Trump' in self.cl)

	def test_class_repr_method_9(self):
		self.assertTrue(repr(self.cl) == 'Tweet by {} With {} Retweets'.format(self.cl.user_screen_name, self.cl.retweet_count))

	def test_class_str_method_10(self):
		self.assertTrue(str(self.cl) == 'This is a tweet with ID: {}'.format(self.cl.tweet_id))

	def test_api_pull_11(self):
		self.assertTrue(len(self.data['statuses'])==100)

	def test_class_sentiment_subj_12(self):
		self.assertIsInstance(self.cl.get_sentiment_score()['subjectivity'], float)

class Tests_SQL(unittest.TestCase):
	def setUp(self):
		self.url = "https://api.twitter.com/1.1/search/tweets.json"
		self.params = {"q":"Donald Trump", "count":100}

		# API Fetch
		self.data = get_twitter_data(self.url,"Twitter",self.params)

		# db creds
		self.db_name = secret_data.db_name
		self.db_user = secret_data.db_user
		self.db_pass = secret_data.db_password

		setup_database(self.db_name, self.db_pass, self.db_user)
		insert_into_tweets(self.data['statuses'], self.db_name, self.db_pass, self.db_user)


		print("Setting Up for SQL Tests")

	def test_db_setup_12(self):
		print("STARTING 12")
		conn, cur = get_connection_and_cursor(self.db_name, self.db_pass, self.db_user)
		sql = "SELECT table_name FROM information_schema.tables WHERE table_name='tweets'"
		cur.execute(sql)
		resp = cur.fetchall()
		val = []
		for row in resp:
			val.append(row['table_name'])
		conn.commit()

		self.assertTrue(val[0] == 'tweets')

	def test_db_count_13(self):
		print("STARTING 13")
		conn, cur = get_connection_and_cursor(self.db_name, self.db_pass, self.db_user)
		sql = "SELECT COUNT(*) FROM tweets"
		cur.execute(sql)
		resp1 = cur.fetchall()
		val = []
		for row in resp1:
			val.append(int(row['count']))
		conn.commit()

		self.assertTrue(val[0] == 100)

	def test_db_data_14(self):
		print("STARTING 14")
		conn, cur = get_connection_and_cursor(self.db_name, self.db_pass, self.db_user)
		sql = "SELECT retweet_count FROM tweets LIMIT 1"
		cur.execute(sql)
		resp = cur.fetchall()
		val = []
		for row in resp:
			val.append(row['retweet_count'])
		conn.commit()

		self.assertIsInstance(val[0], int)

	def test_db_clear_15(self):
		conn, cur = get_connection_and_cursor(self.db_name, self.db_pass, self.db_user)
		sql = "SELECT COUNT(*) FROM trump_mentions"
		cur.execute(sql)
		resp = cur.fetchall()
		val = []
		for row in resp:
			val.append(row['count'])
		conn.commit()

		self.assertTrue(val[0] == 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
