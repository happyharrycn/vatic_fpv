"""Scripts for generating video clips based on ELAN annotations"""

import pympi.Elan as elan
import argparse
import os
import glob
import math
import shutil
import json

# for multi process
import subprocess

from joblib import delayed
from joblib import Parallel

def check_folders(video_dir, elan_dir, tmp_dir, output_dir):
    """
    Check all video / annotation folders
    Return valid video-annotation pairs
    """
    valid_files = []

    # do we have all the folders?
    if (not os.path.exists(video_dir)) \
        or (not os.path.exists(elan_dir)):
        print "Video or Elan folder does not exist"
        return valid_files

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    video_files = sorted(glob.glob(
        os.path.join(video_dir, '*.mp4')))

    for video_file in video_files:
        file_name = os.path.basename(video_file).split('.mp4')[0]
        elan_file = os.path.join(elan_dir, file_name + '.eaf')

        # make sure that annotation file exist
        if not os.path.exists(elan_file):
            print "Missing annotation {:s}.eaf".format(file_name)
        else:
            valid_files.append([video_file, elan_file])

    return valid_files

def trim_video(video_file, elan_file, tmp_dir, output_dir, pad):
    """
    Trim a video file using ELAN annotations
    Padded clips will be saved to output_dir
    (Quick and Dirty!)
    """

    # name / FPS
    video_id = os.path.basename(video_file).split('.mp4')[0]
    fps = 24
    status = False

    # load elan file and check the annotations
    eafob = elan.Eaf(elan_file)

    # check the default/side tier
    crop_list = []
    for tier_name in ['default', 'side']:
        for ant in eafob.get_annotation_data_for_tier(tier_name):
            # get start / ending frames
            start_frame = int(math.floor(
                float(ant[0])/1000 * fps))
            end_frame = int(math.ceil(
                float(ant[1])/1000 * fps))
            # add to crop list
            event = [start_frame, end_frame]
            crop_list.append(event)

    # repack the current video into frames
    tmp_video_dir = os.path.join(tmp_dir, video_id)
    if not os.path.exists(tmp_video_dir):
        os.mkdir(tmp_video_dir)

    command = ['ffmpeg',
               '-i', '{:s}'.format(video_file),
               '-r', '{:s}'.format(str(fps)),
               '-f', 'image2', '-q:v', '1',
               '{:s}/%010d.jpg'.format(tmp_video_dir)
              ]
    command = ' '.join(command)
    try:
        output = subprocess.check_output(command, shell=True,
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        return status, err.output

    # repack the frames into clips
    frame_list = sorted(glob.glob(
        os.path.join(tmp_video_dir, '*.jpg')))
    num_frames = len(frame_list)
    clip_counter = 0
    # crop the clip from the video
    for event in crop_list:
        print "Cropping clips {:d}-{:d} in {:s}.mp4".format(
            event[0], event[1], video_id)

        # padding / truncate the events
        start_frame, end_frame = event[0], event[1]
        duration = end_frame - start_frame + 1

        start_frame = max(start_frame - int(duration*pad), 0)
        end_frame = min(end_frame + int(duration*pad), num_frames - 1)
        duration = end_frame - start_frame + 1
        print "Padding ({:d}-{:d}) --> ({:d}-{:d})".format(
            event[0], event[1], start_frame, end_frame)

        # generate output clip
        output_clip_file = os.path.join(output_dir,
                                        '{:s}-{:d}-{:d}.mp4'.format(
                                            video_id, event[0], event[1]))
        command = ['ffmpeg',
                   '-r', '{:s}'.format(str(fps)),
                   '-start_number', '{:d}'.format(start_frame),
                   '-i', '{:s}/%010d.jpg'.format(tmp_video_dir),
                   '-vframes', '{:d}'.format(duration),
                   '-vcodec', 'libx264',
                   '-b:v', '1800k', '-an',
                   '{:s}'.format(output_clip_file)
                  ]
        command = ' '.join(command)

        if not os.path.exists(output_clip_file):
            try:
                output = subprocess.check_output(command, shell=True,
                                                 stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as err:
                return status, err.output
        else:
            print "Skipped {:s}".format(output_clip_file)

        if os.path.exists(output_clip_file):
            clip_counter += 1

    # Clean tmp dir.
    shutil.rmtree(tmp_video_dir)
    status = (clip_counter == len(crop_list))

    return status, 'Finished'

def trim_video_wrapper(file_pair, tmp_dir, output_dir, pad):
    """
    Wrapper for parallel processing
    """
    video_file, elan_file = file_pair[0], file_pair[1]
    video_id = os.path.basename(video_file).split('.mp4')[0]
    trimmed, log = trim_video(video_file, elan_file,
                              tmp_dir, output_dir, pad)
    status = tuple([video_id, trimmed, log])
    return status

def main(video_dir, elan_dir, output_dir,
         padding_format=0.1, num_jobs=1, 
         tmp_dir='/tmp/video_trim', check=False):
    """
    The main function for cropping videos in a folder
    """
    # Sanity check (if we have all files / folders)
    files = check_folders(video_dir, elan_dir, tmp_dir, output_dir)
    if len(files) == 0:
        return

    # parallel trim_video
    if num_jobs == 1:
        status_lst = []
        for file_pair in files:
            status_lst.append(trim_video_wrapper(file_pair, tmp_dir,
                                                 output_dir, padding_format))
    else:
        status_lst = Parallel(n_jobs=num_jobs)(delayed(trim_video_wrapper)(
            file, tmp_dir, output_dir, padding_format) for idx, file in files)

    # Clean tmp dir.
    shutil.rmtree(tmp_dir)

    # Print and save report
    for status in status_lst:
        print status

    with open('process_report.json', 'w') as fobj:
        fobj.write(json.dumps(status_lst))

if __name__ == '__main__':
    description = 'Helper script for trimming videos using ELAN annotations.'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('video_dir', type=str,
                   help='Video folder with all mp4 videos.')
    p.add_argument('elan_dir', type=str,
                   help='Annotation folder with all elan files')
    p.add_argument('output_dir', type=str,
                   help='Output directory where cropped videos will be saved.')
    p.add_argument('-p', '--padding-format', type=float, default=0.25,
                   help='This will pad the temporal axis of the video clips.')
    p.add_argument('-n', '--num-jobs', type=int, default=1)
    p.add_argument('-t', '--tmp-dir', type=str, default='/tmp/video_trim')
    main(**vars(p.parse_args()))
