import json
import os
import requests
import scrapy

from pathlib import Path


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
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
initial_state_start_index = len('<script>window.initialState=')
initial_state_end_index = -len('</script>')


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

def get_carousell_listing_url(collection_id, product_id):
    return f'https://sg.carousell.com/api-service/related-listing/?collection_id={collection_id}&country_id=1880251&locale=en&product_id={product_id}'


#####################################################
################# CAROUSELL SPIDER ##################
#####################################################
class CarousellSpider(scrapy.Spider):
    name = 'CarousellSpider'
    allowed_domains = ['sg.carousell.com']
    custom_settings = {
        'AUTOTHROTTLE_ENABLED': True,
        'USER_AGENT': user_agent,
        'illegal_items': []
    }

    def start_requests(self):
        return [
            scrapy.Request(
                url=get_carousell_search_url(search_term=search_term),
                headers = {
                    'Accept': '*/*',
                    'Content-Type': 'application/json'
                },
                callback=self.parse,
                meta={
                    'illegal_entities': search_terms[search_term]
                }
            ) for search_term in search_terms
        ]

    # Thanks, Dexter! (https://youtu.be/mx_C-SN40O0)
    def parse(self, response):
        lines = response.text.split('\n')
        for i in range(len(lines)-1, -1, -1): # We expect to see initialState at the end of the HTML
            line = lines[i]
            if is_initial_state(line):
                data = json.loads(line.lstrip()[initial_state_start_index:initial_state_end_index])
                try:
                    collection_id = data['SearchListing']['collection']['id']
                    listings = ((listing_card['listingID'], listing_card['thumbnailURL'].encode('utf-8')) for listing_card in data['SearchListing']['listingCards'])
                    for listing_id, thumbnail_url in listings:
                        download_directory = f'{CarousellSpider.name}/{collection_id}/{listing_id}'
                        download_file_path = f'{download_directory}/0.jpg'
                        Path(download_directory).mkdir(parents=True, exist_ok=True)
                        download_image(thumbnail_url, download_file_path)
                        if is_illegal(download_file_path, response.meta['illegal_entities']):
                            CarousellSpider.custom_settings['illegal_items'].append({
                                'url': get_carousell_listing_url(collection_id, listing_id),
                                'image_url': thumbnail_url
                            })
                except Exception as e:
                    print(e)
                    print('Listings were not processed because of missing keys or changed data structure.')
                    continue # Go to next listing (which is most likely going to fail as well)
                break # Found initial state already. Can break.

    def closed(self, reason):
        print(f'Current CarousellSpider.custom_settings looks like: {str(CarousellSpider.custom_settings)}')
