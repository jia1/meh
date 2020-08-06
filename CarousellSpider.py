import json
import os
import requests
import scrapy

from pathlib import Path


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

# Remove this when done with debugging
# is_illegal('demo/caged-tiger.png')


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

#####################################################
################# CAROUSELL SPIDER ##################
#####################################################
class CarousellSpider(scrapy.Spider):
    name = 'CarousellSpider'
    allowed_domains = ['sg.carousell.com']
    custom_settings = {
        'AUTOTHROTTLE_ENABLED': True,
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
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
                callback=self.parse
            ) for search_term in search_terms
        ]

    # Thanks, Dexter! (https://youtu.be/mx_C-SN40O0)
    def parse(self, response):
        html = response.text
        lines = html.split('\n')[::-1] # A hack to reduce time taken
        for i in range(len(lines)):
            line = lines[i]
            if is_initial_state(line):
                data = json.loads(line.lstrip()[initial_state_start_index:initial_state_end_index])
                try:
                    collection_id = data['SearchListing']['collection']['id']
                    listings = ((listing_card['listingID'], listing_card['thumbnailURL'].encode('utf-8')) for listing_card in data['SearchListing']['listingCards'])
                    for listing in listings:
                        listing_id, thumbnail_url = listing
                        download_directory = f'{CarousellSpider.name}/{collection_id}/{listing_id}'
                        download_file_path = f'{download_directory}/0.jpg'
                        Path(download_directory).mkdir(parents=True, exist_ok=True)
                        download_image(thumbnail_url, download_file_path)
                        if is_illegal(download_file_path):
                            CarousellSpider.custom_settings['illegal_items'].append({
                                'url': get_carousell_listing_url(collection_id, listing_id),
                                'image_url': thumbnail_url
                            })
                except Exception as e:
                    print(e)
                    print('Listings were not processed because of missing keys or changed data structure.')
                    continue # Go to next listing (which is most likely going to fail as well)
                # TODO: Use Selenium to click "Load more" button
                break # Found initial state already. Can break.

    def closed(self, reason):
        print(f'Current CarousellSpider.custom_settings looks like: {str(CarousellSpider.custom_settings)}')
