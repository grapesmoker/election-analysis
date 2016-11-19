#!/usr/bin/env python
from __future__ import division

import os
import argparse
import shapefile
import matplotlib.pyplot as mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
import pymongo
import json
import sys
import descartes
import numpy as np

from shapely.geometry import MultiPolygon
# from mpl_toolkits.basemap import Basemap
from matplotlib import cm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

client = pymongo.MongoClient()
db = client.election
counties_2016 = db.counties_2016
counties_2012 = db.counties_2012

def extract_fips(record):

    for item in record:
        if isinstance(item, str) and len(item) == 5:
            try:
                result = int(item)
                return item
            except ValueError:
                pass

def merge_vote_and_geography_2016(vote_file, shape_file):

    shape_data = shapefile.Reader(shape_file)
    vote_data = json.load(open(vote_file, 'r'))

    counties_json = []
    for state in vote_data:
        counties_json.extend(state['counties'])

    for item in shape_data.shapeRecords():
        geo_json = item.shape.__geo_interface__
        # geo_json['geom_type'] = 'Polygon'
        fips = extract_fips(item.record)
        name = item.record[5]
        # print fips, name
        try:
            county = [ct for ct in counties_json if ct['fips'] == fips][0]
            county['geo'] = geo_json
            counties_2016.insert_one(county)
        except IndexError:
            print 'could not locate county {} {}'.format(fips, name)

def merge_vote_and_geography_2012(vote_file, shape_file):

    shape_data = shapefile.Reader(shape_file)
    vote_data = json.load(open(vote_file, 'r'))

    counties_json = []
    for state, county in vote_data['counties'].items():
        new_counties = {}
        for candidate in county['candidates']:
            for fips, votes in zip(county['county_votes']['location_fips'],
                                   county['county_votes'][candidate['votes_field']]):
                if fips not in new_counties:
                    new_county = {'fips': str(fips),
                                  'results': {candidate['cand_shortname']: votes}}
                    new_counties[fips] = new_county
                else:
                    existing_county = new_counties[fips]
                    existing_county['results'][candidate['cand_shortname']] = votes


        counties_json.extend(cty for _, cty in new_counties.items())
    
    for item in shape_data.shapeRecords():
        geo_json = item.shape.__geo_interface__
        fips = extract_fips(item.record)
        name = item.record[5]
        try:
            county = [ct for ct in counties_json if ct['fips'] == fips][0]
            county['geo'] = geo_json
            counties_2012.insert_one(county)
        except IndexError:
            print 'could not locate county {} {}'.format(fips, name)

def draw_map(patches, colors, filename=None):

    fig = mpl.figure(figsize=(12, 8))
    ax = mpl.gca()
    # fig, ax = mpl.subplots()
    cmap = cm.get_cmap('seismic')

    ax.axis('scaled')
    patch_collection = PatchCollection(patches, cmap=cmap)
    patch_collection.set_array(np.array(colors))
    ax.add_collection(patch_collection)
    ax.set_xlim(-125, -65)
    ax.set_ylim(24, 50)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.05)
    mpl.colorbar(patch_collection, cax=cax)
    if filename:
        mpl.savefig(filename)
    else:
        mpl.show()

def plot_counties(year, output_file=None):

    if year == 2016:
        all_counties = counties_2016.find({})
    elif year == 2012:
        all_counties = counties_2012.find({})
        
    patches = []
    colors = []
    
    for county in all_counties:
        geo = county['geo']
        results = county['results']
        if year == 2016:
            clinton = results.get('clintonh', 0)
            trump = results.get('trumpd', 0)
            johnson = results.get('johnsong', 0)
            stein = results.get('steinj', 0)
            total = sum([clinton, trump, johnson, stein])
            d_pct = 100 * clinton / total
            r_pct = 100 * trump / total
        elif year == 2012:
            obama = results.get('Obama', 0)
            romney = results.get('Romney', 0)
            johnson = results.get('Johnson', 0)
            stein = results.get('Stein', 0)
            total = sum([obama, romney, johnson, stein])
            d_pct = 100 * obama / total
            r_pct = 100 * romney / total
        
        if geo['type'] == 'Polygon':
            arr = np.array(geo['coordinates'][0])
            polygon = Polygon(arr, True)
            patches.append(polygon)
            colors.append(r_pct)

        elif geo['type'] == 'MultiPolygon':
            arrays = [coords[0] for coords in geo['coordinates']]
            polygons = [Polygon(arr, True) for arr in arrays]
            patches.extend(polygons)
            colors.extend([r_pct for i in range(len(polygons))])

    draw_map(patches, colors, output_file)

def plot_differentials(output_file=None):

    all_counties_2016 = [ct for ct in counties_2016.find({})]
    all_counties_2012 = [ct for ct in counties_2012.find({})]

    county_pairs = []
    for ct_2012 in all_counties_2012:
        for ct_2016 in all_counties_2016:
            if ct_2016['fips'] == ct_2012['fips']:
                county_pairs.append((ct_2016, ct_2012))
    
    patches = []
    colors = []

    print len(county_pairs)
    
    for pair in county_pairs:
        geo = pair[0]['geo']
        results_2016 = pair[0]['results']
        results_2012 = pair[1]['results']

        clinton_2016 = results_2016.get('clintonh', 0)
        trump_2016 = results_2016.get('trumpd', 0)
        johnson_2016 = results_2016.get('johnsong', 0)
        stein_2016 = results_2016.get('steinj', 0)

        total_2016 = sum([clinton_2016, trump_2016, johnson_2016, stein_2016])
        d_pct_2016 = 100 * clinton_2016 / total_2016
        r_pct_2016 = 100 * trump_2016 / total_2016

        obama_2012 = results_2012.get('Obama', 0)
        romney_2012 = results_2012.get('Romney', 0)
        johnson_2012 = results_2012.get('Johnson', 0)
        stein_2012 = results_2012.get('Stein', 0)

        total_2012 = sum([obama_2012, romney_2012, johnson_2012, stein_2012])
        d_pct_2012 = 100 * obama_2012 / total_2012
        r_pct_2012 = 100 * romney_2012 / total_2012

        d_diff = d_pct_2016 - d_pct_2012
        r_diff = r_pct_2016 - r_pct_2012
        
        if geo['type'] == 'Polygon':
            arr = np.array(geo['coordinates'][0])
            polygon = Polygon(arr, True)
            patches.append(polygon)
            colors.append(r_diff)

        elif geo['type'] == 'MultiPolygon':
            arrays = [coords[0] for coords in geo['coordinates']]                
            polygons = [Polygon(arr, True) for arr in arrays]
            patches.extend(polygons)
            colors.extend([r_diff for i in range(len(polygons))])

    draw_map(patches, colors, output_file)
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--operation', type=str)
    parser.add_argument('-v', '--vote-file', type=str, nargs='?')
    parser.add_argument('-s', '--shape-file', type=str, nargs='?')
    parser.add_argument('-y', '--year', type=int, nargs='?')
    parser.add_argument('-of', '--output-file', type=str, nargs='?')
    
    args = parser.parse_args()

    if args.operation == 'merge-vote-2016':
        counties_2016.remove({})
        merge_vote_and_geography_2016(args.vote_file, args.shape_file)
    elif args.operation == 'merge-vote-2012':
        counties_2012.remove({})
        merge_vote_and_geography_2012(args.vote_file, args.shape_file)
    elif args.operation == 'plot-counties':
        plot_counties(args.year, args.output_file)
    elif args.operation == 'plot-diff':
        plot_differentials(args.output_file)
