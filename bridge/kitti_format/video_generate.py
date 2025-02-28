import cv2
import os
import argparse
"""Directly running this file will require two arguments: inpute directory and fps
"""
def image2video(input_dir, fps):
    # Sort to time sequence
    output = os.path.join(input_dir, '..', 'output.mp4')
    images = [img for img in os.listdir(input_dir) if img.endswith(".png") or img.endswith(".jpg")]
    images.sort()
    print(f"In total {len(images)} frames")

    # Read the first image to get the size (width, height)
    first_image = cv2.imread(os.path.join(input_dir, images[0]))
    height, width, layers = first_image.shape

    # Initialize video writer (use .mp4 or .avi format)
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')  # You can also use 'MP4V' for .mp4
    out = cv2.VideoWriter(output, fourcc, fps, (width, height))

    # Loop through images and add them to the video
    for image in images:
        img_path = os.path.join(input_dir, image)
        img = cv2.imread(img_path)
        out.write(img)  # Write the image to the video file
    return out

if __name__ == '__main__':
    print(__doc__)
    argparser = argparse.ArgumentParser(
        description=__doc__)
    argparser.add_argument(
        '-i','--input_dir',
        default=None,
        type = str,
        help='Input directory name')
    argparser.add_argument(
        '-f','--fps',
        default=1,
        type = int,
        help='Input directory name')
    # Auto not implemented yet
    argparser.add_argument(
        '-a', '--auto',
        action='store_true',
        default=False,
        help='Autogenerate 2 videos[semantic and rgb]')
    args = argparser.parse_args()
    gen_num = 1
    if os.path.exists(args.input_dir):
        out = image2video(args.input_dir, args.fps)
    else:
        print("No valid input")

