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
    return predictions[0] in illegal_entities

# Remove this when done with debugging
# is_illegal('demo/caged-tiger.png')


#####################################################
############### SHOPEE SPIDER HELPERS ###############
#####################################################
default_search_term = search_terms[0]

def get_shopee_search_url(search_term=default_search_term, page_num=1):
    batch_size = 2 # Increase if needed to impress
    search_by = 'relevancy' # or ctime
    return f'https://shopee.sg/api/v2/search_items/?by={search_by}&keyword={search_term}&limit={batch_size}&newest={page_num * batch_size}&order=desc&page_type=search&version=2'

def get_shopee_search_referer_url(search_term=default_search_term, page_num=0):
    page_query_param = f'&page={page_num}' if page_num else ''
    return f'https://shopee.sg/search?keyword={search_term}{page_query_param}'

def get_shopee_item_referer_url(search_term=default_search_term):
    return f'https://shopee.sg/search?keyword={search_term}'

def get_shopee_item_url(item_id, shop_id):
    return f'https://shopee.sg/api/v2/item/get?itemid={item_id}&shopid={shop_id}'

def get_shopee_image_url(long_image_id):
    return f'https://cf.shopee.sg/file/{long_image_id}'


#####################################################
################### SHOPEE SPIDER ###################
#####################################################
class ShopeeSpider(scrapy.Spider):
    name = 'ShopeeSpider'
    allowed_domains = ['shopee.sg']
    # Shopee blocks Scrapy's default user-agent and checks for valid referer.
    custom_settings = {
        'AUTOTHROTTLE_ENABLED': True,
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
        'has_more': True,
        'page_num': 1,
        'page_lim': 2, # Because this is just a POC
        'illegal_items': []
    }

    def start_requests(self):
        # Cannot return yields. See:
        # https://stackoverflow.com/questions/8779964/python-yield-and-return-statements-and-scrapy-yielding-the-requests
        return [
            scrapy.Request(
                url=get_shopee_search_url(search_term=search_term),
                headers = {
                    'Accept': '*/*',
                    'Content-Type': 'application/json',
                    'Referer': get_shopee_search_referer_url()
                },
                callback=self.parse
            ) for search_term in search_terms
        ]

    def parse(self, response):
        # TODO: Remove page_lim in the future
        if not ShopeeSpider.custom_settings['has_more'] or ShopeeSpider.custom_settings['page_num'] > ShopeeSpider.custom_settings['page_lim']:
            return
        try:
            data = json.loads(response.text)
            if 'items' in data:
                for item in data['items']:
                    try:
                        item_id, shop_id = item['itemid'], item['shopid']
                        yield scrapy.Request(
                            url=get_shopee_item_url(item_id, shop_id),
                            headers = {
                                'Accept': '*/*',
                                'Content-Type': 'application/json',
                                'Referer': get_shopee_item_referer_url()
                            },
                            callback=self.parse
                        )
                    except Exception as e:
                        print(e)
                        print('Item was not processed either because of missing keys or scrapy request failure.')
                        continue
                try:
                    search_term = data['query_rewrite']['ori_keyword']
                    yield scrapy.Request(
                        url=get_shopee_search_url(search_term=search_term, page_num=ShopeeSpider.custom_settings['page_num']),
                        headers = {
                            'Accept': '*/*',
                            'Content-Type': 'application/json',
                            'Referer': get_shopee_search_referer_url(page_num=ShopeeSpider.custom_settings['page_num'] - 1)
                        },
                        callback=self.parse
                    )
                except Exception as e:
                    print(e)
                    print('Could not retrieve search_term from response. Consider storing search_term as a class/instance variable for one fewer point of failure.')
                ShopeeSpider.custom_settings['has_more'] = not data['nomore'] if 'nomore' in data else True
                ShopeeSpider.custom_settings['page_num'] = ShopeeSpider.custom_settings['page_num'] + 1
            elif 'item' in data:
                try:
                    item = data['item']
                    item_id, shop_id, images = item['itemid'], item['shopid'], item['images']
                    if not images:
                        print('Either there are no images to process or the correct key to query has changed.')
                        return
                    image_id = images[0]
                    download_directory = f'{ShopeeSpider.name}/{shop_id}/{item_id}'
                    download_file_path = f'{download_directory}/{image_id}.jpg'
                    Path(download_directory).mkdir(parents=True, exist_ok=True)
                    image_url = get_shopee_image_url(image_id)
                    download_image(image_url, download_file_path)
                    if is_illegal(download_file_path):
                        ShopeeSpider.custom_settings['illegal_items'].append({
                            'url': get_shopee_item_url(item_id, shop_id),
                            'image_url': image_url
                        })
                except Exception as e:
                    print(e)
                    print('Item was not processed either because of missing keys or scrapy request failure.')
                    return
        except Exception as e:
            print(e)
            print('Unable to load response.text as JSON.')
            return

    def closed(self, reason):
        print(f'Current ShopeeSpider.custom_settings looks like: {str(ShopeeSpider.custom_settings)}')
