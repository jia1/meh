import os
import requests
import time

from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


#####################################################
#################### USER INPUTS ####################
#####################################################
# Source: http://image-net.org/challenges/LSVRC/2014/browse-synsets

# search_terms is a dictionary of search_term: list of illegal_entities
search_terms = {
    'tiger': {'tiger cat', 'tiger'}
}


#####################################################
################### DEFAULT INPUTS ##################
#####################################################
# Do not change unless you know what you are doing
download_directory = 'CarousellClicker'
load_more_button_xpath = '//button[text()="Load more"]'
wait_in_seconds = 10


#####################################################
############## GENERAL SPIDER HELPERS ###############
#####################################################
# TODO: Move this section to a helper file
def download_image(image_url, download_file_path):
    with open(download_file_path, 'wb') as f:
        f.write(requests.get(image_url).content)

def is_illegal(image_file_path, illegal_entities):
    stream = os.popen(f'. predict.sh {image_file_path}')
    predictions = list(map(lambda s: s.split(':')[-1].strip(), stream.readlines()))
    # TODO: Add confidence threshold here
    return predictions[0] in illegal_entities # Top 1 only


#####################################################
############# CAROUSELL SPIDER HELPERS ##############
#####################################################
def get_carousell_search_url(search_term):
    return f'https://sg.carousell.com/search/{search_term}' # ?sort_by=time_created,descending'

def is_initial_state(line):
    return line.lstrip().startswith('<script>window.initialState=')

def is_product_img(img_url):
    return img_url.startswith('https://media.karousell.com/media/photos/products/')

# https://www.hackerearth.com/practice/notes/praveen97uma/crawling-a-website-that-loads-content-using-javascript-with-selenium-webdriver-in-python
def page_down(browser, page_downs):
    body = browser.find_element_by_tag_name('body')
    while page_downs:
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1) # So that I can see that stuff really happened
        page_downs -= 1
    return browser

# NOT USING THIS FOR NOW.
# The website I'm crawling does not seem to react well to this scroll-down program. Perhaps it is
# too aggressive. Refactored from:
# https://stackoverflow.com/questions/22702277/crawl-site-that-has-infinite-scrolling-using-python
def scroll_down(browser):
    per_scroll = 200
    max_height = browser.execute_script('return document.body.scrollHeight')
    new_height = per_scroll
    while max_height > new_height:
        browser.execute_script(f'window.scrollTo(0, {new_height})')
        time.sleep(1) # So that I can see that stuff really happened
        max_height = browser.execute_script('return document.body.scrollHeight')
        new_height += per_scroll


#####################################################
################# CAROUSELL SPIDER ##################
#####################################################
Path(download_directory).mkdir(parents=True, exist_ok=True)

illegal_items = []
browser = webdriver.Chrome()

for search_term in search_terms:
    imgs_to_download = []
    try:
        browser.get(get_carousell_search_url(search_term))
        browser = page_down(browser, 4) # Arbitrary
        is_element_present = EC.presence_of_element_located((By.XPATH, load_more_button_xpath))
        WebDriverWait(browser, wait_in_seconds).until(is_element_present)
        load_more_button = browser.find_element_by_xpath(load_more_button_xpath)
        load_more_button.click()
        time.sleep(wait_in_seconds)
        browser = page_down(browser, 6) # Arbitrary
        for img in browser.find_elements_by_tag_name('img'):
            src = img.get_attribute('src')
            if is_product_img(src):
                imgs_to_download.append(src)
    except TimeoutException:
        print('Timed out.')
    print(imgs_to_download) # Remove when not needed
    if imgs_to_download:
        for i in range(len(imgs_to_download)):
            img_url = imgs_to_download[i]
            download_file_path = f'{download_directory}/{i}.jpg'
            download_image(img_url, download_file_path)
            if is_illegal(download_file_path, search_terms[search_term]):
                illegal_items.append(img_url)

browser.quit()
print(illegal_items)
