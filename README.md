# SI507_Final_Project
Nikhil Kalambur's Final Project Repo for SI 507

# Overview
This project pulls data from Twitter related to President Donald Trump and runs a sentiment analysis on the text of tweets. The code pulls (1) the most recent 100 tweets with the search term "Donald Trump" and (2) the most recent 199 tweets posted by @realdonaldtrump. If the cache hasn't been expired (10 hrs), then the results may be <10 hours out of date. Both of these limits (100 & 199) are due to Twitter API limits on number of records per API call. 

The code pulls these tweets from the twitter API (OAuth) or from a cache, processes them in a class, then migrates them to a local postgres sql database (more on this later). This class also contains a method that conducts the sentiment classification of a tweet's text using the TextBlob module, which has a trained pattern analyzer. The code then translates sentiment scores as such:

- Very Negative - Score of -1 to -.5
- Negative - Score of -.4999 to 0
- Neutral - Score of 0
- Positive - Score of 0 to .5
- Very Positive - Score of .5 to 1

The code fetches the data, either from a cache or from the Twitter API, processes it in the class, then migrates to SQL. From sql, the data is then queried to show two data visualizations using plotly. The visuals show the a bar chart of the average retweet count for Donald Trump's 199 tweets by sentiment classification and a scatter plot showing raw retweet counts by actual sentiment score for the last 100 tweets that mention "Donald Trump". 

# Before you run the .py files, you must:
- Fork & clone this repository to your local computer. Or, you can download SI507F17_finalproject.py , SI507F17_finalproject_tests.py , requirements.txt , and secret_data.py. You will need all of these files. 
  - In the cloned repo on your computer, Run pip install -r requirements.txt -- this will get all of the required python modules, assuming you are running this in a virtual environment. 
  - The secret_data.py file includes references to credentials needed to:
    - (1) access Twitter API via OAuth. You must update the client_key and client_secret variables in this file with your own Twitter credentials to run this code. You MUST have a twitter account and set up a developer app to access the API with your credentials. Instructions on how to do this are in the secret_data.py file. 
    - (2) Access your local database. You must update this file with your database name and your user name for your computer. Additionally, if you would like to password protect the db, you can also insert a password. The default is for no password.
      - You must also create a database on your local postgres sql using the following command: createdb "SI507_Final_Project". You may change this to be whatever you want. If you do change this, you must update the secret_data.py file. 
    - (3) Push the visualization outputs back to my plotly account. Please note, I have included my plotly account information in case you do not have one. The code relies on valid plotly creds to actually run and push the visuals to plotly. You do not need an account to view the plotly results.
  
  - All URLs required to access APIs and retrieve access tokens have been hard coded into SI507F17_finalproject.py
  
# Running the code (What's happening & What to expect):
After you have (1) downloaded all required files, (2) pip installed from the requirements.txt file, (3) updated the secret_data.py with your credentials for Twitter and your database details, you can actually run the python files.

- From the command line, make sure you have navigated to where the python files are located. From here, you can execute: python SI507F17_finalproject.py. From here the code follows the following flow: 
  - It loads any relevant cache files (in .json format). These will be populated later otherwise
  - Then, the function get_twitter_data is run to pull data for tweets both by @realdonaldtrump and with "Donald Trump" in them. The function first checks if the access token has expired. The default for this has been set within the code to 10 hours. If the access token hasn't expired and there is data in the cache file, the function simply pulls from this json file. Otherwise, it runs a simple requests.get() call to fetch a live set of data from Twitter's API.
    - If the access token has expired or if this is the first time you are running the code (or you have gone into the code to change the search parameters), a twitter web page will open up. Click a button that says "Authorize App" and copy and paste the "verifier" code that appears. Return to the terminal and paste it as prompted. This new access token will then be stored in the credentials cache and remain valid for 10 hours. 
    - Whether from the API or Cache, the tweet data is returned to a variable for subsequent processing. 
  - After the data is pulled, a set of functions is called to push this data into sql databases. Remember, you should have created a db with a name of your choice (default = SI507_Final_Project") and updated the secret_data.py file accordingly. 
    - The first function (setup_database) wipes the database, and re-populates them with a tweets table and a trump_mentions table.
    - Two other functions (insert_into_tweets & insert_into_trump_mentions) are then run. These take the db creds and the fetched twitter data as inputs. The functions both leverage the class called twitter_handler which consists of constructor, a get_sentiment_score(), __contains__, __repr__, and __str__ methods. Class instances are created for each record pulled from twitter. The functions then execute insert statements via psycopg2 (which also calls to a funciton to get create the db connection (conn, cur). 
      - The trump_mentions table is child to the tweets table and contains a record for each mentioned twitter handle in a trump tweet. Each record of this table also has an ID field that refers back to the original tweet, as Pres. Trump often mentions more than 1 twitter use in a tweet. 
      
  - The terminal should render updates throughout this process notifying you that caches/API's were accessed, tables were created and populated, etc. 
  - The final set of code fetches data from the SQL tables and uses the plotly API to create visuals. This utilizes two functions to pull the data for each visual (fetch_avg_retweet_count_trump_tweets_by_classification & fetch_sentiment_retweets_abtrump). These functions establish db connections, execute custom queries, and fetch the results which are then passed as parameters to Plotly functions. 
    - The visuals, based on the datasets I passed them in the past few days, did indicate that the more negative President Trump's tweets were, the higher the average reteweet count was. The retweet counts for tweets that mention "Donald Trump" seemed reasonably varied with sentiment score. 
  - After the code hits this part of the code, the browser should pop open and you should see two tabs with the visuals. Again, you do not need to be logged in to view these, though you may have to click "x" or "cancel" on a pop up from plotly asking you to sign up/in (if you don't want to sign in). Screenshots have been included in this repo. 
  
Finally, the SI507F17_finalproject_tests.py runs 15 or so tests to ensure the code is excuted properly. Some additional notes, after creating the database mentioned above, you may have to execute: "pg_ctl -D /usr/local/var/postgres start" or something similar to kick start the sql server. Similarly, if any sql queries hang (or fail to execute in a timely manner), you can also run "pg_ctl -D /usr/local/var/postgres stop" then "pg_ctl -D /usr/local/var/postgres start" again to re-start the server. 
  
# Resources
- https://developer.twitter.com/en/docs/tweets/search/api-reference/get-search-tweets.html
- http://textblob.readthedocs.io/en/dev/index.html
- https://plot.ly/python/
- Additionally, I received help from Anand Doshi on re-thinking how to modify my data & credentials caching set up given how frequently the source API data would change. As such, I decided on 10 hours expiration of access tokens and updated the code used in the class OAuth twitter example. 
- Finally, I built on/modified some of the code from my project 6 to establish the postgres/psycopg2 database connection and set up the db.

  



