import scrapy
import re
BASE_URL = 'http://en.wikipedia.org'

def process_winner_li(w, country=None):
    wdata = {}
    wdata['link'] = BASE_URL + w.xpath('a/@href').extract()[0]
    text = ' '.join(w.xpath('descendant-or-self::text()').extract())

    # get comma-delineated name and strip trailing whitespace
    wdata['name'] = text.split(',')[0].strip()
    year = re.findall('\d{4}', text)
    
    if year:
        wdata['year'] = int(year[0])
    else:
        wdata['year'] = 0
        print('Oops, no year in ', text)
    
    category = re.findall(
        'Physics|Chemistry|Physiology or Medicine|Literature|Peace|Economics',
            text)
    
    if category:
        wdata['category'] = category[0]
    else:
        wdata['category'] = ''
        print('Oops, no category in ', text)
    if country:
        if text.find('*') != -1:
            wdata['country'] = ''
            wdata['born_in'] = country
        else:
            wdata['country'] = country
            wdata['born_in'] = ''
    # store a copy of the link's text string
    # for any manual corrections
    wdata['text'] = text
    return wdata


# Define the data to be scraped
class NWinnerItem(scrapy.Item):
    name = scrapy.Field()
    link = scrapy.Field()
    year = scrapy.Field()
    category = scrapy.Field()
    country = scrapy.Field()
    gender = scrapy.Field()
    born_in = scrapy.Field()
    date_of_birth = scrapy.Field()
    date_of_death = scrapy.Field()
    place_of_birth = scrapy.Field()
    place_of_death = scrapy.Field()
    text = scrapy.Field()

# Create a named spider
class NWinnerSpider(scrapy.Spider):

    name = 'nwinners_list'
    allowed_domains = ['en.wikipedia.org', 'www.wikidata.org']
    start_urls = ["https://en.wikipedia.org/wiki/List_of_Nobel_laureates_by_country"]
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'HTTPERROR_ALLOW_ALL': True,
        'REDIRECT_MAX_TIMES': 10
    }
    # C A parse method to deal with the HTTP response
    def parse(self, response):
        
        h3s = response.xpath('//h3')
        
        for h3 in h3s:
            country = h3.xpath('./text()').extract()
            if country:
                winners = h3.xpath('../following-sibling::ol[1]')
                for w in winners.xpath('li'):
                    wdata = process_winner_li(w, country[0])
                    #print(wdata) #Verificamos que los datos se estén extrayendo correctamente
                    request = scrapy.Request(wdata['link'],
                                             callback=self.parse_bio,
                                             dont_filter=True)
                    request.meta['item'] = NWinnerItem(**wdata)
                    yield request
    
    def errback_httpbin(self, failure):
        self.logger.error(f"Error en la solicitud: {failure.value.response.url}")

    def parse_bio(self, response):
        item = response.meta['item']
        href = response.xpath("//li[@id='t-wikibase']//a[contains(@href, 'wikidata.org')]/@href").get() #Intentemos extraer el enlace a wikidata
        #href = "https://www.wikidata.org/wiki/Q937" #Probamos con un link fijo para depurar el código
        print("Tenemos", href)

        if href:
            full_url = response.urljoin(href)  # Convierte URL relativa en absoluta
            full_url = re.sub(r'Special:EntityPage/', '', full_url) # Reemplazar "Special:EntityPage/" por la URL estándar de Wikidata
            print(f"Scrapy está solicitando: {full_url}")  

            request = scrapy.Request(full_url, callback=self.parse_wikidata, dont_filter=True, errback=self.errback_httpbin,
                                    meta={'handle_httpstatus_all': True,'redirect_max_times': 10, 'dont_redirect':False})
            request.meta['item'] = item
            yield request
        else:
            print(f"No se encontró URL de Wikidata para {item['name']}")
            yield item

    def parse_wikidata(self, response):
        print(f"Entrando a parse_wikidata con URL: {response.url}")
        item = response.meta['item']

        property_codes = [
            {'name': 'date_of_birth', 'code': 'P569'},
            {'name': 'date_of_death', 'code': 'P570'},
            {'name': 'place_of_birth', 'code': 'P19', 'link': True},
            {'name': 'place_of_death', 'code': 'P20', 'link': True},
            {'name': 'gender', 'code': 'P21', 'link': True}
        ]

        for prop in property_codes:
            if prop.get('link'):
                # Para propiedades enlazadas (place_of_birth, place_of_death, gender)
                xpath_query = f'//*[@id="{prop["code"]}"]//div[contains(@class, "wikibase-snakview-value")]//a/text()'
            else:
                # Para propiedades no enlazadas (date_of_birth, date_of_death)
                xpath_query = f'//*[@id="{prop["code"]}"]//div[contains(@class, "wikibase-snakview-value")]//text()'

            
            sel = response.xpath(xpath_query).getall()

            if sel:
                if prop['name'] in ['date_of_birth', 'date_of_death']:
                    date_candidates = [s.strip() for s in sel if re.search(r'\d{1,2} \w+ \d{4}', s)]
                    item[prop['name']] = date_candidates[0] if date_candidates else ''
                else:
                    item[prop['name']] = sel[0].strip()
                    print(f"No se encontró {prop['name']} para {item['name']}")
            else:
                item[prop['name']] = ''
                print(f"No se encontró {prop['name']} para {item['name']}")


        print("Datos finales del item:", item)
        yield item
    
