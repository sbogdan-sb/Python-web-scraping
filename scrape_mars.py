from bs4 import BeautifulSoup as bs
import requests
import json
import pandas as pd
from flask import Flask, render_template, redirect
from splinter import Browser

# MongoDB dependencies & setup
import pymongo
conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)



# Function to gather multiple Mars facts and images
def scrape():

    # Create browser instance to use for web-scraping 
    executable_path = {'executable_path': 'chromedriver.exe'}
    browser = Browser('chrome', **executable_path, headless=True)


    # Get Mars News

    mars_news_url = 'https://mars.nasa.gov/news/?page=0&per_page=40&order=publish_date+desc%2Ccreated_at+desc&search=&category=19%2C165%2C184%2C204&blank_scope=Latest'
    browser.visit(mars_news_url)

    soup = bs(browser.html, 'html.parser')

    news_title = soup.find('div', class_='content_title').text
    news_overview= soup.find('div', class_='article_teaser_body').text


    # Get JPL Featured Mars Image

    jpl_url = 'https://www.jpl.nasa.gov/spaceimages/?search=&category=Mars'
    browser.visit(jpl_url)

    browser.click_link_by_partial_text('FULL IMAGE')

    soup = bs(browser.html, 'html.parser')
    mars_image = soup.find('article')

    mars_image_url = "https://www.jpl.nasa.gov/spaceimages" + mars_image['style'].split('spaceimages')[1].split("');")[0]


    # Get Mars Weather

    mars_weather_url = 'https://twitter.com/marswxreport?lang=en'

    html = requests.get(mars_weather_url).text

    soup = bs(html, 'html.parser')

    mars_weather = soup.find('div', class_='js-tweet-text-container').p.text


    # Get Mars Facts

    mars_facts_url = 'https://space-facts.com/mars/'

    html = requests.get(mars_facts_url).text

    soup = bs(html, 'html.parser')

    table = soup.find('table')

    mars_facts_df = pd.read_html(str(table))[0]
    mars_facts_df.columns = ['Description', 'Value']

    mars_facts_table_string = mars_facts_df.to_html(index=False)    .replace('<tr style="text-align: right;">','<tr style="text-align: center;">')


    # Get Mars Hemisphere Images

    mars_hemispere_img_url = 'https://astrogeology.usgs.gov/search/results?q=hemisphere+enhanced&k1=target&v1=Mars'
    browser.visit(mars_hemispere_img_url)

    soup = bs(browser.html, 'html.parser')

    image_links = soup.find_all('div', class_='item')

    hemisphere_image_urls = []

    # Loop through all image links on initial page
    for link in image_links:
        # Get link text to click on
        link_text = link.h3.text
        browser.click_link_by_partial_text(link_text)
        
        # Parse out image link path and create url to the image
        soup = bs(browser.html, 'html.parser')
        image_link = 'https://astrogeology.usgs.gov' + soup.find('img', class_='wide-image')['src']
        
        # Add image description and url to dictionary
        hemisphere_image_urls.append({'title' : link_text, 'img_url' : image_link})
        
        # Return to initial page
        browser.back()


    #Create dictionary of all scraped data to return    
    mars_data = {}
    mars_data["mars_news"] = {"news_headline":news_title, "news_summary":news_overview}
    mars_data["JPL_featured_image"] = mars_image_url
    mars_data["mars_weather"] = mars_weather
    mars_data["mars_facts"] = mars_facts_table_string
    mars_data["mars_hemisphere_imgs"] = hemisphere_image_urls
    mars_data["test_tag"] = "test"

    return mars_data


################ Flask Section ##################

app = Flask(__name__)


@app.route("/")
def index():

    db = client["mars_data_store"]
    mars_dict = db.mars_info.find_one()

    return render_template("index.html", mars_dict=mars_dict)
    

@app.route("/scrape")
def do_scrape():
    # Call scrape function to gather Mars data and update Mongo data store dictionary returned by the function
    
    mars_data = scrape()
    db = client["mars_data_store"]

    # Upsert the mars data to keep just the most current data set in the database
    db.mars_info.replace_one({}, mars_data, True)
    return redirect('/')

   

if __name__ == "__main__":
    app.run(debug=True)

