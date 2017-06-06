"""Scripts for generating a db from trimmed video files"""

import argparse
import os
import glob

# database
from tinydb import TinyDB, Query

def main(video_dir, output_db, url_prefix, extension='.mp4', frame_rate=24):
    """
    The main function for creating a mini database of videos
    """
    # open the db file (json)
    db = TinyDB(output_db)

    # list all video files
    video_files = sorted(glob.glob(os.path.join(
                                    video_dir, '*{:s}'.format(extension))))
    if len(video_files) == 0:
        return

    for video_file in video_files:
        # parse video info from names
        video_name = os.path.basename(video_file).split(extension)[0]
        tags = video_name.split('-')
        start_frame, end_frame = float(tags[-2]), float(tags[-1])
        base_video_name = '-'.join(tags[:-2])

        # create the data item
        video_item = {
            'url' : os.path.join(url_prefix, video_name + extension),
            'named' : False,
            'occluded' : False,
            'trimmed' : False,
            'video_src' : base_video_name,
            'src_start_time' : start_frame / frame_rate,
            'src_end_time' : end_frame / frame_rate,
            'start_time' : -1.0,
            'end_time' : -1.0,
            'action_verb' : '',
            'action_noun' : []
        }

        # check if the item is in db
        el = db.get(Query()['url'] == video_item['url'])
        if el is None:
            db.insert(video_item)


if __name__ == '__main__':
    description = 'Helper script for creating a database using trimmed videos.'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('video_dir', type=str,
                   help='Video folder with all mp4 videos.')
    p.add_argument('output_db', type=str,
                   help='Output file where the db will be saved.')
    p.add_argument('url_prefix', type=str,
                   help='URL prefix for all videos.')
    p.add_argument('-ext', '--extension', type=str, default='.mp4')
    p.add_argument('-fps', '--frame_rate', type=int, default=24)
    main(**vars(p.parse_args()))
