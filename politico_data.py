#!/usr/bin/env python
import sys
import requests
import us

from bs4 import BeautifulSoup

base_url = 'http://www.politico.com/2016-election/results/map/president/'
base_delimited = 'http://s3.amazonaws.com/origin-east-elections.politico.com/mapdata/2016/'

def fetch_state_html(state):

    url = base_url + state
    print 'fetching data for {} from {}'.format(state, url)
    r = requests.get(url)

    soup = BeautifulSoup(r.text)
    results_section = soup.find('section', class_='election-results')
    counties = results_section.find_all(attrs={'data-fips': True})
    county_data = [fetch_county(county) for county in counties]

    print county_data
    
def fetch_county_html(county):

    result_dict = {}
    
    results_header = county.find('header', class_='results-header')
    print results_header
    cty_title = results_header.find('h4').text.replace(' County', '')

    results_table = county.find('table', class_='results-table')
    rows = results_table.find_all('tr')

    result_dict[cty_title] = {'independent': {'popular': 0, 'percent': 0.0}}
    
    for row in rows:
        results_pct = row.find('td', class_='results-percentage')
        pct = float(results_pct.find('span', class_='number').text.replace('%', ''))
        popular = int(row.find('td', class_='results-popular').text.replace(',', ''))
        result = {'popular': popular,
                  'percent': pct}
        if row['class'] == 'type-republican':
            result_dict[cty_title]['republican'] = result
        elif row['class'] == 'type-democrat':
            result_dict[cty_title]['democrat'] = result
        elif row['class'] == 'type-independent':
            result_dict[cty_title]['independent']['popular'] += popular
            result_dict[cty_title]['independent']['percent'] += percent

    return result_dict

def fetch_state_delimited(state):

    state_obj = us.states.lookup(state)
    
    url = base_delimited + state_obj.abbr + '_20161108.xml'
    print url
    r = requests.get(url)
    data = r.text.split('\n')[4:]

    cty = parse_county(data[0])
    print cty


def parse_county(county_data):

    county, vote_data = county_data.split('||')
    fips = county.split(';')[3]
    cty_name = county.split(';')[4]

    votes = vote_data.split('|')

    result_dict = {}
    result_dict[fips] = {'name': cty_name, 'independent': {'popular': 0, 'percent': 0.0}}
    
    for vote in votes:
        # print vote
        party_vote = vote.split(';')
        party = party_vote[1]
        popular = int(party_vote[2])
        percent = float(party_vote[3])
        result = {'popular': popular, 'percent': percent}
        
        if party == 'GOP':
            result_dict[fips]['republican'] = result
        elif party  == 'Dem':
            result_dict[fips]['democrat'] = result
        else:
            result_dict[fips]['independent']['popular'] += popular
            result_dict[fips]['independent']['percent'] += percent

    return result_dict
            

if __name__ == '__main__':
        
    state = sys.argv[1]
    fetch_state_delimited(unicode(state))
