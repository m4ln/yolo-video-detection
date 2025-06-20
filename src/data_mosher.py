#!/usr/bin/env python3

import os
import subprocess


class DataMosher:
    def __init__(self, video_path, start_frames, end_frames, fps, save_path, delta):
        self.video_path = video_path
        self.start_frames = start_frames
        self.end_frames = end_frames
        self.fps = fps
        self.save_path = save_path
        self.delta = delta

        if not os.path.exists(self.video_path):
            raise FileNotFoundError(
                f"Video file {self.video_path} does not exist in the data directory.")
        self.results_dir = os.path.join(
            os.path.dirname(__file__), '..', 'results')
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        self.input_avi = 'datamoshing_input.avi'
        self.output_avi = 'datamoshing_output.avi'
        self.in_file = None
        self.out_file = None

    def convert_to_avi(self):
        subprocess.call(
            f'ffmpeg -loglevel error -y -i {self.video_path} -crf 0 -pix_fmt yuv420p -bf 0 -b 10000k -r {self.fps} {self.input_avi}',
            shell=True
        )

    def get_fps(self):
        cmd = [
            "ffprobe", "-v", "0", "-of", "csv=p=0",
            "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate", self.video_path
        ]
        output = subprocess.check_output(cmd).decode().strip()
        num, denom = map(int, output.split('/'))
        return num / denom if denom != 0 else 0

    def open_files(self):
        self.in_file = open(self.input_avi, 'rb')
        self.out_file = open(self.output_avi, 'wb')

    def cleanup(self):
        if self.in_file:
            self.in_file.close()
        if self.out_file:
            self.out_file.close()
        if os.path.exists(self.input_avi):
            os.remove(self.input_avi)
        if os.path.exists(self.output_avi):
            os.remove(self.output_avi)

    def export_video(self):
        output_avi = os.path.join(
            self.results_dir, f"{self.save_path}_moshed.avi")
        self.final_output = os.path.join(
            self.results_dir, f"{self.save_path}_moshed.mp4")
        subprocess.call(
            f'ffmpeg -loglevel error -y -i {output_avi} -crf 18 -pix_fmt yuv420p -vcodec libx264 -acodec aac -b 10000k -r {self.fps} {self.final_output}',
            shell=True
        )
        os.remove(output_avi)
        print(f"Final video saved to {self.final_output}")

    def process_video(self):
        def in_any_range(idx, ranges):
            return any(start <= idx < end for start, end in ranges)

        def write_frame(frame):
            self.out_file.write(frame_start + frame)

        def mosh_delta_repeat(frames, n_repeat, ranges):
            repeat_frames = []
            repeat_index = 0
            for idx, frame in enumerate(frames):
                if not in_any_range(idx, ranges):
                    write_frame(frame)
                    continue
                if (frame[5:8] != iframe and frame[5:8] != pframe):
                    write_frame(frame)
                    continue
                if len(repeat_frames) < n_repeat and frame[5:8] != iframe:
                    repeat_frames.append(frame)
                    write_frame(frame)
                elif len(repeat_frames) == n_repeat:
                    write_frame(repeat_frames[repeat_index])
                    repeat_index = (repeat_index + 1) % n_repeat
                else:
                    write_frame(frame)

        def mosh_iframe_removal(frames, ranges):
            for idx, frame in enumerate(frames):
                if in_any_range(idx, ranges) and frame[5:8] == iframe:
                    continue  # Remove I-frames in the specified ranges
                write_frame(frame)

        # check if start_frames and end_frames are provided and same length
        if not self.start_frames or not self.end_frames:
            raise ValueError("start_frames and end_frames must be provided.")
        if len(self.start_frames) != len(self.end_frames):
            raise ValueError(
                "start_frames and end_frames must have the same length.")

        self.convert_to_avi()
        self.open_files()
        in_file_bytes = self.in_file.read()
        frame_start = bytes.fromhex('30306463')
        frames = in_file_bytes.split(frame_start)
        self.out_file = open(os.path.join(
            self.results_dir, f"{self.save_path}_moshed.avi"), 'wb')
        self.out_file.write(frames[0])
        frames = frames[1:]

        iframe = bytes.fromhex('0001B0')
        pframe = bytes.fromhex('0001B6')

        # get number of video frames
        self.n_video_frames = len(
            [frame for frame in frames if frame[5:8] == iframe or frame[5:8] == pframe])

        # if the end_frames are negative, set them to the total number of frames
        if any(end < 0 for end in self.end_frames):
            self.end_frames = [self.n_video_frames if end <
                               0 else end for end in self.end_frames]

        # Prepare a list of (start, end) tuples
        ranges = list(zip(self.start_frames, self.end_frames))
        print('Processing ranges:', ranges)

        if self.delta:
            mosh_delta_repeat(frames, self.delta, ranges)
        else:
            mosh_iframe_removal(frames, ranges)

        self.out_file.close()

        # Export the final video
        self.export_video()
        # Clean up temporary files
        self.cleanup()


def define_start_end_frame_ranges(def_video_path, step, offset, start_frame=2, end_frame=-1):
    from video_util import get_number_of_frames

    n_frames = get_number_of_frames(def_video_path)

    start = start_frame
    end = n_frames if end_frame == -1 else end_frame
    step = step if step >= 0 else 10  # Default step size if not provided
    offset = offset if offset >= 0 else 0  # Default offset if not provided

    if end <= start:
        raise ValueError("Invalid start or end values.")

    start_frames = [start + i * (step + offset)
                    for i in range((end - start) // (step + offset))]
    end_frames = [s + step for s in start_frames]

    return start_frames, end_frames


def main():
    import argparse

    def_video_path = os.path.join(data_dir, def_video)

    # Define start and end frames based on the video
    if not step <= 0 and not offset <= 0:
        def_start_frames, def_end_frames = define_start_end_frame_ranges(
            def_video_path, step=step, offset=offset, start_frame=2, end_frame=-1)
        def_out = f"{def_video.split('.')[0]}_{def_fps}_{step}_{offset}"

        print(
            f"Using step {step} and offset {offset} to define start and end frames.")
    else:
        print(
            f"Using default start frames {def_start_frames} and end frames {def_end_frames}.")

    parser = argparse.ArgumentParser()
    parser.add_argument('--video_path', type=str,
                        default=def_video_path, help='Path to video to be moshed')
    parser.add_argument('--start_frames', nargs='+', type=int,
                        required=False, default=def_start_frames, help='List of start frames (default: [2])')
    parser.add_argument('--end_frames', nargs='+', type=int,
                        required=False, default=def_end_frames, help='List of end frames (default: [-1])')
    parser.add_argument('--fps', '-f', default=def_fps, type=int,
                        help='fps to convert initial video to')
    parser.add_argument('--save_path', type=str, default=def_out,
                        help="Base path to save processed video.")
    parser.add_argument('--delta', '-d', default=def_delta, type=int,
                        help='number of delta frames to repeat')
    args = parser.parse_args()

    if len(args.start_frames) != len(args.end_frames):
        raise ValueError(
            "start_frames and end_frames must have the same length.")

    mosher = DataMosher(
        video_path=args.video_path,
        start_frames=args.start_frames,
        end_frames=args.end_frames,
        fps=args.fps,
        save_path=args.save_path,
        delta=args.delta
    )

    # fps check
    print(f"Video FPS: {mosher.get_fps()}")

    # data moshing
    mosher.process_video()

    # print number of total frames
    n_frames = mosher.n_video_frames
    print(f"Total frames count: {n_frames}")


if __name__ == "__main__":

    # == Default values ===

    def_fps = 30
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    def_video = 'dan_0614.mov'
    def_out = f"{def_video.split('.')[0]}_{def_fps}"
    def_start_frames = [2]
    def_end_frames = [-1]
    def_delta = 0
    step = 50  # set to zero if you want to use default start and end frames
    offset = 10  # set to zero if you want to use default start and end frames

    # == End of default values ===

    main()
