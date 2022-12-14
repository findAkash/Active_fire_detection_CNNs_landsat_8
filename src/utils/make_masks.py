""" Generates new masks from the combination of masks generated by literature algorithms
The new masks are generated from the union, intersection and voting of the original masks
If a mask does not exist for a given algorithm, a "don't care" value is generated as a mask
"""

import pandas as pd
import numpy as np
import rasterio
from glob import glob
from functools import reduce
from tqdm import tqdm
import shutil
import cv2
import os
import sys

# Set this flag to True if you want to generate the computed mask for whole image (not the patch).
MASKS_FOR_COMPLETE_SCENE = True

# MASKS_DIR = '../../dataset/masks/patches'
# MASKS_ALGORITHMS = ['Schroeder', 'Murphy', 'Kumar-Roy']
# OUTPUT_DIR = '../../dataset/masks/'

MASKS_DIR = '../../dataset/manual_annotations/scenes/masks/'
MASKS_ALGORITHMS = ['Schroeder', 'Murphy', 'Kumar-Roy']
OUTPUT_DIR = '../../dataset/manual_annotations/scenes/masks/'

# OUTPUT_INTERSECTION = os.path.join(OUTPUT_DIR, 'intersection')
# OUTPUT_VOTING = os.path.join(OUTPUT_DIR, 'voting')

OUTPUT_INTERSECTION = OUTPUT_DIR
OUTPUT_VOTING = OUTPUT_DIR

NUM_VOTINGS = 2

IMAGE_SIZE = (256, 256)

def load_masks_in_dataframe():

    masks = glob(os.path.join(MASKS_DIR, '*.tif')) + glob(os.path.join(MASKS_DIR, '*.TIF'))

    print('Masks found: {}'.format(len(masks)))

    df = pd.DataFrame(masks ,columns=['masks_path'])
    df['original_name'] = df.masks_path.apply(os.path.basename)
    df['image_name'] = df.original_name.apply(remove_algorithms_name)

    print('Spliting masks...')
    total = 0
    dataframes = []

    # separa as imagens com base no nome dos algoritmos geradores máscaras
    for i, algorithm in enumerate(MASKS_ALGORITHMS):
        dataframes.append( df[ df['original_name'].str.contains(algorithm) ] )
    
        num_images = len(dataframes[i].index)
        total += num_images
        print('{} - Images: {}'.format(algorithm, num_images))

    return dataframes

def remove_algorithms_name(mask_name):
    """Remove o nome dos algoritmos do nome da máscara"""

    for algorithm in MASKS_ALGORITHMS:
        mask_name = mask_name.replace('_{}'.format(algorithm), '')

    return mask_name


def make_intersection_masks(dataframes):

    if not os.path.exists(OUTPUT_INTERSECTION):
        print('Creating output dir: {}'.format(OUTPUT_INTERSECTION))
        os.makedirs(OUTPUT_INTERSECTION)

    # create a temporary direcotry, it's ease to fix any issue if it's happen
    output_dir = OUTPUT_INTERSECTION
    if OUTPUT_INTERSECTION == OUTPUT_DIR:
        output_dir = os.path.join(OUTPUT_DIR, 'intersection')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    df_joinend = reduce(lambda x, y: pd.merge(x, y, on = 'image_name'), dataframes)
    print('Generating Intersection masks')
    print('Images to process: {}'.format( len(df_joinend.index) ))
    # recupera as colunas do dataframe que cotem os caminhos para as máscaras
    masks_columns = [col for col in df_joinend.columns if col.startswith('masks_path')]
    

    for index, row in tqdm(df_joinend.iterrows()):

        image_size = IMAGE_SIZE
        if MASKS_FOR_COMPLETE_SCENE:
            mask, _ = get_mask_arr(row[masks_columns[0]])
            image_size = mask.shape

        # mascara "dont care" toda Verdadeira
        final_mask = (np.ones(image_size) == 1)
        
        for mask_column in masks_columns:
            mask, profile = get_mask_arr(row[mask_column])
            
            # intersecao das máscaras
            final_mask = np.logical_and(final_mask, mask)
        
        has_fire = final_mask.sum() > 0
        if has_fire:
            write_mask(os.path.join(output_dir, row['image_name'].replace('_RT', '_RT_Intersection')), final_mask, profile)
    

    # move files from temporary dir to output dir
    if OUTPUT_INTERSECTION == OUTPUT_DIR:
        file_names = os.listdir(output_dir)
        for file_name in file_names:
            shutil.move(os.path.join(output_dir, file_name), OUTPUT_DIR)

        shutil.rmtree(output_dir)

    print('Intersection masks created')


def make_voting_masks(dataframes):
    if not os.path.exists(OUTPUT_VOTING):
        print('Creating output dir: {}'.format(OUTPUT_VOTING))
        os.makedirs(OUTPUT_VOTING)

    # create a temporary direcotry, it's ease to fix any issue if it's happen
    output_dir = OUTPUT_VOTING
    if OUTPUT_VOTING == OUTPUT_DIR:
        output_dir = os.path.join(OUTPUT_DIR, 'voting')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    df_joinend = reduce(lambda x, y: pd.merge(x, y, on = 'image_name', how='outer'), dataframes)
    print('Generating Voting masks')
    print('Images to process: {}'.format( len(df_joinend.index) ))

    # get the columns with the masks path
    masks_columns = [col for col in df_joinend.columns if col.startswith('masks_path')]

    for index, row in tqdm(df_joinend.iterrows()):
        # mascara "dont care" toda Falsa

        image_size = IMAGE_SIZE
        # Get the mask size for the complete scene
        if MASKS_FOR_COMPLETE_SCENE:
            for mask_column in masks_columns:
                if type(row[mask_column]) == str:
                    mask, _ = get_mask_arr(row[mask_column])
                    image_size = mask.shape
                    break

        final_mask = np.zeros(image_size)

        for mask_column in masks_columns:

            if type(row[mask_column]) != str:
                mask = (np.zeros(image_size) == 1)
            else:
                mask, profile = get_mask_arr(row[mask_column])

            final_mask += mask

        final_mask = (final_mask >= NUM_VOTINGS)

        has_fire = final_mask.sum() > 0
        if has_fire:
            write_mask(os.path.join(output_dir, row['image_name'].replace('_RT', '_RT_Voting')), final_mask, profile)
    

    if OUTPUT_VOTING == OUTPUT_DIR:
        file_names = os.listdir(output_dir)
        for file_name in file_names:
            shutil.move(os.path.join(output_dir, file_name), OUTPUT_DIR)

        shutil.rmtree(output_dir)

    print('Voting masks created!')


def get_mask_arr(path):
    with rasterio.open(path) as src:
        img = src.read().transpose((1, 2, 0))
        seg = np.array(img, dtype=int)

        return seg[:, :, 0], src.profile


def write_mask(mask_path, mask, profile={}):
    profile.update({'dtype': rasterio.uint8,'count': 1})

    with rasterio.open(mask_path, 'w', **profile) as dst:
        dst.write_band(1, mask.astype(rasterio.uint8))




if __name__ == '__main__':

    if MASKS_FOR_COMPLETE_SCENE:
        print('Will be computed the voting ({} votes) and the intersection masks for the complete scenes (not the patches)'.format(NUM_VOTINGS))
    else:
        print('Will be computed the masks for the patches')

    dataframes = load_masks_in_dataframe()
    make_intersection_masks(dataframes)
    make_voting_masks(dataframes)
