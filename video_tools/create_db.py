"""Scripts for generating a db from trimmed video files"""

import argparse
import os
import glob
import numpy as np
import math

# database (tinydb -> sqlite)
import sqlite3

def main(video_dir, output_db, url_prefix, extension='.mp4', pad=0.25):
    """
    The main function for creating a mini database of videos
    """
    # connect to db and get the cursor
    conn = sqlite3.connect(output_db)
    db_cursor = conn.cursor()

    # create the table if not exist
    db_cursor.execute('''CREATE TABLE IF NOT EXISTS video_db (
                     id integer primary key, 
                     url text, 
                     named integer, 
                     name_locked integer, 
                     name_lock_time real,
                     named_by_user text, 
                     occluded integer, 
                     trimmed integer, 
                     trim_locked integer,
                     trim_lock_time real,
                     trimmed_by_user text,
                     video_src text,
                     src_start_time integer,
                     src_end_time integer,
                     pad_start_frame integer,
                     pad_end_frame integer,
                     start_time real,
                     end_time real,
                     action_verb text,
                     action_noun text,
                     red_flag integer
                     )''')
    conn.commit()

    # list all video files
    video_files = sorted(glob.glob(
        os.path.join(video_dir, '*{:s}'.format(extension))))
    if len(video_files) == 0:
        return

    # make sure we insert video with random order
    # the user will thus get less context about the video
    rand_video_idx = np.random.permutation(len(video_files))
    permutated_video_files = [video_files[idx] for idx in rand_video_idx]
    
    # insert the item one by one
    num_new_items = 0
    for video_file in permutated_video_files:
        # parse video info from names
        video_name = os.path.basename(video_file).split(extension)[0]
        video_url = os.path.join(url_prefix, video_name + extension)
        tags = video_name.split('-')
        src_start_time, src_end_time = int(tags[-2]), int(tags[-1])
        base_video_name = '-'.join(tags[:-2])

        # re-calculate the offsets in frames
        fps = 24
        src_start_frame = int(math.floor(
                float(src_start_time)/1000 * fps))
        src_end_frame = int(math.ceil(
                float(src_end_time)/1000 * fps))
        duration = src_end_frame - src_start_frame + 1
        src_start_frame -= int(duration*pad)
        src_end_frame += int(duration*pad)

        # insert db item
        video_item = (
            video_url, 0, 0, 0.0, '', 
            0, 0, 0, 0.0, '', base_video_name, 
            src_start_time, src_end_time, 
            src_start_frame, src_end_frame,
            -1.0, -1.0, '', '', 0
        )

        db_cursor.execute('SELECT count(*) FROM video_db WHERE url=?', (video_url,))
        if db_cursor.fetchone()[0] == 0:
            # insert
            db_cursor.execute('''INSERT INTO video_db(
                url, named, name_locked, name_lock_time, named_by_user,
                occluded, trimmed, trim_locked, trim_lock_time, trimmed_by_user,
                video_src, src_start_time, src_end_time, 
                pad_start_frame, pad_end_frame, start_time, end_time,
                action_verb, action_noun, red_flag) VALUES 
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', video_item)
            conn.commit()
            num_new_items += 1
        else:
            print "Skipped {:s}".format(video_name)

    # print the final stats
    print "Inserted {:d} new video clips into DB".format(num_new_items)

if __name__ == '__main__':
    description = 'Helper script for creating a database using trimmed videos.'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('video_dir', type=str,
                   help='Video folder with all mp4 videos.')
    p.add_argument('output_db', type=str,
                   help='Output file where the db will be saved.')
    p.add_argument('-url', '--url_prefix', type=str,
                   default='http://webshare.ipat.gatech.edu/coc-rim-wall-lab/web/yli440/cropped_videos',
                   help='URL prefix for all videos.')
    p.add_argument('-ext', '--extension', type=str, default='.mp4')
    p.add_argument('-p', '--pad', type=float, default=0.25)
    main(**vars(p.parse_args()))
