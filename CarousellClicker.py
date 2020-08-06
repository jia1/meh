import os
import requests
import time

from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


#####################################################
#################### USER INPUTS ####################
#####################################################
# These can be made into command line arguments
# Source: http://image-net.org/challenges/LSVRC/2014/browse-synsets
# TODO: Build more robust mapping between illegal_entities and search_terms
illegal_entities = ['tiger cat', 'tiger']
search_terms = ['tiger']


#####################################################
############## GENERAL SPIDER HELPERS ###############
#####################################################
# TODO: Move this section to a helper file
def download_image(image_url, download_file_path):
    with open(download_file_path, 'wb') as f:
        f.write(requests.get(image_url).content)

def is_illegal(image_file_path):
    stream = os.popen(f'. predict.sh {image_file_path}')
    predictions = list(map(lambda s: s.split(':')[-1].strip(), stream.readlines()))
    # TODO: Add confidence threshold here
    # TODO: Can return tuple of (is_illegal, illegal_entity) for downstream processing
    return predictions[0] in illegal_entities # top 1 only


#####################################################
############# CAROUSELL SPIDER HELPERS ##############
#####################################################
def get_carousell_search_url(search_term):
    return f'https://sg.carousell.com/search/{search_term}' # ?sort_by=time_created,descending'

def is_initial_state(line):
    return line.lstrip().startswith('<script>window.initialState=')

initial_state_start_index = len('<script>window.initialState=')
initial_state_end_index = -len('</script>')

def get_carousell_listing_url(collection_id, product_id):
    return f'https://sg.carousell.com/api-service/related-listing/?collection_id={collection_id}&country_id=1880251&locale=en&product_id={product_id}'

def is_product_img(img_url):
    return img_url.startswith('https://media.karousell.com/media/photos/products/')

timeout = 10

def scroll_down(browser):
    per_scroll = 200
    max_height = browser.execute_script('return document.body.scrollHeight')
    new_height = per_scroll
    while max_height > new_height:
        browser.execute_script(f'window.scrollTo(0, {new_height})')
        time.sleep(1)
        max_height = browser.execute_script('return document.body.scrollHeight')
        new_height += per_scroll
    # https://stackoverflow.com/questions/22702277/crawl-site-that-has-infinite-scrolling-using-python
    # last_height = browser.execute_script('return document.body.scrollHeight')
    # while True:
    #     browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    #     time.sleep(timeout)
    #     new_height = browser.execute_script('return document.body.scrollHeight')
    #     if new_height == last_height:
    #         break
    #     last_height = new_height


#####################################################
################# CAROUSELL SPIDER ##################
#####################################################
default_search_term = search_terms[0]

browser = webdriver.Chrome()

imgs_to_download = []
illegal_items = []

try:
    browser.get(get_carousell_search_url(default_search_term))
    is_element_present = EC.presence_of_element_located((By.XPATH, '//button[text()="Load more"]'))
    # TODO: Fix scrolling
    WebDriverWait(browser, timeout).until(is_element_present)
    load_more_button = browser.find_element_by_xpath('//button[text()="Load more"]')
    load_more_button.click()
    time.sleep(timeout)
    scroll_down(browser)
    imgs = browser.find_elements_by_tag_name('img')
    for img in imgs:
        src = img.get_attribute('src')
        if is_product_img(src):
            imgs_to_download.append(src)
except TimeoutException:
    print('Timed out.')
finally:
    browser.quit()
    print(imgs_to_download) # Remove when not needed
    if imgs_to_download:
        download_directory = f'CarousellClicker'
        for i in range(len(imgs_to_download)):
            img_url = imgs_to_download[i]
            download_file_path = f'{download_directory}/{i}.jpg'
            Path(download_directory).mkdir(parents=True, exist_ok=True)
            download_image(img_url, download_file_path)
            if is_illegal(download_file_path):
                illegal_items.append(img_url)
    print(illegal_items)
