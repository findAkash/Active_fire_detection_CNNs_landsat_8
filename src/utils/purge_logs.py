"""
Delete the output log folder generated by the training, inference and evaluation;
"""

import os
import shutil

DELETE_TRAIN_LOG = False
DELETE_MANUAL_ANNOTATIONS_LOG = True

TRAIN_DIR = '../train/'
MANUAL_ANNOTATIONS_DIR = '../manual_annotations'


def delete_log_from_algorithms(base_path):
    folders = os.listdir(base_path)
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        
        if not os.path.isdir(folder_path):
            continue
        
        delete_log_from_architecture(folder_path)    

def delete_log_from_architecture(base_path):
    architectures = os.listdir(base_path)
    for architecture in architectures:
        folder_path = os.path.join(base_path, architecture)
        
        if not os.path.isdir(folder_path):
            continue
        
        delete_log_folder(folder_path)

def delete_log_folder(base_path):
    path = os.path.join(base_path, 'log')
    delete_folder(path)


def delete_folder(folder_path):
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        print('Deleting {}'.format(folder_path))
        shutil.rmtree(folder_path)


if DELETE_MANUAL_ANNOTATIONS_LOG:

    delete_log_folder(MANUAL_ANNOTATIONS_DIR)

    cnn_compare_folder = os.path.join(MANUAL_ANNOTATIONS_DIR, 'cnn_compare')
    delete_log_from_algorithms(cnn_compare_folder)

if DELETE_TRAIN_LOG:
    delete_log_from_algorithms(TRAIN_DIR)
