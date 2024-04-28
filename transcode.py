#!/usr/bin/env python3
import argparse
import os
import json
from timecode import Timecode
import subprocess
from pathlib import Path
from datetime import datetime
import logging
import shutil

logging.basicConfig(format='%(asctime)s :: %(levelname)s :: %(funcName)s :: %(message)s', level=logging.DEBUG)




def TG4_AVCINTRA(infile, outfile, ar, scale_up=True, crop=False):
	vf = "colormatrix=bt601:bt709,setsar=sar=1/1,setdar=dar=4/3,scale=1440:1080:interl=1:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
	if ar == "16:9":
		if not crop:
			vf = "colormatrix=bt601:bt709,setsar=sar=1/1,setdar=dar=16/9,scale=1920:1080:interl=1:flags=lanczos"
		else:
			vf = "colormatrix=bt601:bt709,setsar=sar=1/1,setdar=dar=16/9,crop=1440:1080,scale=1920:1080:interl=1:flags=lanczos"
	if not scale_up:
		vf = "colormatrix=bt601:bt709,setsar=sar=1/1,setdar=dar=16/9"
	print(vf)
	ffmpeg_process = subprocess.Popen(
		['ffmpeg',
		 '-loglevel', 'debug',
		 '-i', infile,
		 '-ss', "60",
		 '-t', "30",
		 '-acodec', 'pcm_s24le',
		 '-vf', vf,
		 '-vcodec', 'libx264',
		 '-pix_fmt', 'yuv422p10le',
		 '-flags', '+ildct+ilme',
		 '-x264opts', 'colorprim=bt709',
		 '-x264opts', 'transfer=bt709',
		 '-x264opts', 'colormatrix=bt709',
		 '-x264opts', 'avcintra-class=100',
		'-f', 'mxf',
		'-y',outfile
		 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#for line in ffmpeg_process.stderr:
	#	print(line.decode('utf-8'), end='')
	ffmpeg_process.communicate()
	#print('ffmpeg_process.returncode', ffmpeg_process.returncode)

	return ffmpeg_process.returncode

def IMX(infile, outfile, ar, bitrate):
	br=bitrate*1000
	ffmpeg_process = subprocess.Popen(
		['ffmpeg',
		'-loglevel', 'debug',
		'-i', infile,
		'-ac', '4',
		'-r', '25',
		'-vf', 'scale=in_range=pc:out_range=pc,crop=w=720:h=576:x=0:y=32,pad=width=720:height=608:x=0:y=32:color=black',
		'-vcodec', 'mpeg2video',
		'-g', '0',
		'-flags', '+ildct+low_delay',
		'-dc', '10',
		'-non_linear_quant', '1',
		'-intra_vlc', '1',
		'-q:v', '1',
		'-ps', '1',
		'-qmin', '1',
		'-rc_max_vbv_use', '1',
		'-rc_min_vbv_use', '1',
		'-pix_fmt', 'yuv422p',
		'-minrate', str(br)+"k",
		'-maxrate', str(br)+"k",
		'-b:v', str(br)+"k",
		'-top', '1',
		'-bufsize', '2000000',
		'-rc_init_occupancy', '2000000',
		#'-rc_buf_aggressivity', '0.25',
		'-qmax', '3',
		'-f', 'mxf_d10',
		'-y', outfile
		 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	for line in ffmpeg_process.stderr:
		print(line.decode('utf-8'), end='')
	ffmpeg_process.communicate()
	#print('ffmpeg_process.returncode', ffmpeg_process.returncode)

	return ffmpeg_process.returncode

def writeAS11CoreMetadataFile(file, stem):
	f = open(file, "w")
	f.write("SeriesTitle: {}\n".format(stem))
	f.write("ProgrammeTitle: {}\n".format(stem))
	f.write("EpisodeTitleNumber: {}\n".format(stem))
	f.write("ShimName: {}\n".format("UK DPP HD"))
	f.write("ShimVersion: {}\n".format("1.1"))
	f.write("AudioTrackLayout: {}\n".format("3"))
	f.write("PrimaryAudioLanguage: {}\n".format("gle"))
	f.write("ClosedCaptionsPresent: {}\n".format("false"))
	f.close()

def writeAS11UKDPPMetadataFile(file, stem, start_clock_tc, start_programme_tc, duration_tc):
	f = open(file, "w")
	f.write("ProductionNumber: {}\n".format(stem))
	f.write("Synopsis: {}\n".format(stem))
	f.write("Originator: {}\n".format(stem))
	f.write("CopyrightYear: {}\n".format(datetime.now().strftime("%Y")))
	f.write("Distributor: {}\n".format("None"))
	f.write("PictureRatio: {}\n".format("16/9"))
	f.write("ThreeD: {}\n".format("false"))
	f.write("PSEPass: {}\n".format("2"))
	f.write("SecondaryAudioLanguage: {}\n".format("zxx"))
	f.write("TertiaryAudioLanguage: {}\n".format("zxx"))
	f.write("AudioLoudnessStandard: {}\n".format("0"))
	f.write("LineUpStart: {}\n".format(start_programme_tc))
	f.write("IdentClockStart: {}\n".format(start_clock_tc))
	f.write("TotalNumberOfParts: {}\n".format("1"))
	f.write("TotalProgrammeDuration: {}\n".format(duration_tc))
	f.write("AudioDescriptionPresent: {}\n".format("false"))
	f.write("OpenCaptionsPresent: {}\n".format("false"))
	f.write("SigningPresent: {}\n".format("1"))
	f.write("CompletionDate: {}\n".format(datetime.now().strftime("%Y-%m-%d")))
	f.write("ContactEmail: {}\n".format("None"))
	f.write("ContactTelephoneNumber: {}\n".format("None"))
	f.close()

def writeAS11SegmentMetadataFile(file, stem, start_clock_tc, start_programme_tc, duration_tc):
	f = open(file, "w")
	f.write("1/1\t{} {}\n".format(start_clock_tc, duration_tc))

	f.close()
def TG4_AS11_REWRAP(infile, outfile, ar, start_clock_tc, start_programme_tc, duration_tc, AS11CoreFile, AS11UKDPPFile, AS11SegmentFile):
	afd = 9;
	if ar == "16:9":
		afd = 10

	bmx_process = subprocess.Popen(
		['/Users/nextarchive/bmx/out/build/apps/bmxtranswrap/bmxtranswrap',
		 '--log-level', '0',
		 '-y', str(start_clock_tc),
		 '--ps-avcihead',
		 '--min-part',
		 '-t', 'as11op1a',
		 '--dm-file', 'as11', AS11CoreFile,
		 '--dm-file', 'dpp', AS11UKDPPFile,
		 '--seg', AS11SegmentFile,
		 '--transfer-ch', 'bt709',
		 '--coding-eq', 'bt709',
		 '--color-prim', 'bt709',
		 '--pass-anc', 'all',
		 '--afd', str(afd),
		 '-o', outfile,
		 infile
		 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#for line in bmx_process.stdout:
	#	print(line.decode('utf-8'))
	bmx_process.communicate()
	#print('bmx_process.returncode', bmx_process.returncode)
	os.remove(AS11CoreFile)
	os.remove(AS11UKDPPFile)
	os.remove(AS11SegmentFile)
	os.remove(infile)
	return bmx_process.returncode

def IMX_REWRAP(infile, outfile, ar):
	bmx_process = subprocess.Popen(
		['/Users/nextarchive/bmx/out/build/apps/bmxtranswrap/bmxtranswrap',
		 '--log-level', '0',
		 '-t', 'd10',
		 '-a', ar,
		 '--bsar',
		 '--body-part',
		 '-o', outfile,
		 infile
		 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#for line in bmx_process.stdout:
	#	print(line.decode('utf-8'))
	bmx_process.communicate()
	#print('bmx_process.returncode', bmx_process.returncode)
	os.remove(infile)
	return bmx_process.returncode

def getAspect(path):
	a = "4:3"
	if path.as_posix().find("4x3") > 0:
		a = "4:3"
	elif path.as_posix().find("16x9") > 0:
		a = "16:9"
	return a

def ffprobe(file_path):
	command_array = ["ffprobe",
					 "-v", "quiet",
					 "-print_format", "json",
					 "-show_format",
					 "-show_streams",
					 file_path]
	result = subprocess.run(command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	metadata = json.loads(result.stdout)
	return metadata

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Transcode raw captures into delivery files.')
	parser.add_argument('-i', '--inputdir', dest='input_dir', required=True, help='Directory containing MOV\'s')
	parser.add_argument('-o', '--outputdir', dest='output_dir', required=True, help='Directory containing outputs')
	parser.add_argument('-d', '--donedir', dest='done_dir', required=True, help='Directory containing processedf files')
	parser.add_argument('-p', '--project', dest='project_name', required=True, help='Project code')
	parser.add_argument('-s', '--scale_up', dest='scale_up', default=False, action='store_true', help='To scale up or not to scale up.')
	parser.add_argument('-c', '--crop', dest='crop', default=False, action='store_true', help='Crop to 1440:1080 to get rid of pillars.')

	#
	args = parser.parse_args()
	#
	input_dir = Path(args.input_dir)
	output_dir = Path(args.output_dir)
	done_dir = Path(args.done_dir)
	project_name = args.project_name
	scale_up = bool(args.scale_up)
	crop = bool(args.crop)

	logging.info("Input directory: {}".format(input_dir.as_posix()))
	logging.info("Output directory: {}".format(output_dir.as_posix()))
	logging.info("Done directory: {}".format(done_dir.as_posix()))
	logging.info("Selected Project: {}".format(project_name))
	logging.info("Scale up: {}".format(scale_up))
	logging.info("Crop: {}".format(crop))


	input_file_list = sorted(Path( input_dir ).rglob('*.mov'))

	for input_file in input_file_list:
		logging.info("Processing file: {}".format(input_file))

		ar = getAspect(input_file)
		stem = input_file.stem
		media_info = ffprobe(input_file)
		framerate = media_info["streams"][0]["r_frame_rate"]
		#timecode = media_info["streams"][0]["tags"]["timecode"]
		timecode = "00:00:00:00"
		duration_secs = media_info["streams"][0]["duration"]
		start_tc = Timecode(framerate, timecode)
		start_tc.set_fractional(False)
		duration = Timecode(framerate, "00:00:{}".format(duration_secs))
		duration = Timecode(framerate, "00:00:30:00")
		duration.set_fractional(False)

		if str(project_name) == "TG4":
			mxfTempFile = "{}/{}_temp.mxf".format(output_dir.as_posix(), stem)
			AS11CoreFile = "{}/{}_as11_core.txt".format(output_dir.as_posix(), stem)
			AS11UKDPPFile = "{}/{}_as11_ukdpp.txt".format(output_dir.as_posix(), stem)
			AS11SegmentFile = "{}/{}_as11_segment.txt".format(output_dir.as_posix(), stem)
			output_file = "{}/{}.mxf".format(output_dir.as_posix(), stem)
			writeAS11CoreMetadataFile(AS11CoreFile, stem)
			writeAS11UKDPPMetadataFile(AS11UKDPPFile, stem, start_tc, start_tc, duration )
			writeAS11SegmentMetadataFile(AS11SegmentFile, stem, start_tc, start_tc, duration )

			logging.info("Encoding file: {}".format(input_file))

			if TG4_AVCINTRA(input_file.as_posix(), mxfTempFile, ar, scale_up, crop) == 0:
				logging.info("Finished encoding file: {}".format(mxfTempFile))
			else:
				logging.info("Error encoding file: {}".format(mxfTempFile))

			logging.info("Rewrapping file: {}".format(mxfTempFile))
			if TG4_AS11_REWRAP(mxfTempFile, output_file, ar, start_tc, start_tc, duration, AS11CoreFile, AS11UKDPPFile, AS11SegmentFile ) == 0:
				logging.info("Finished rewrapping file: {}".format(output_file))
				shutil.move(input_file, done_dir.as_posix())
			else:
				logging.info("Error rewrapping file: {}".format(output_file))

		if project_name.find("IMX") != -1:
			print("IMX")
			bitrate = 50
			if str(project_name).find("30") != -1:
				bitrate = 30
			mxfTempFile = "{}/{}_temp.mxf".format(output_dir.as_posix(), stem)
			output_file = "{}/{}.mxf".format(output_dir.as_posix(), stem)

			logging.info("Encoding file: {}".format(input_file))
			if IMX(input_file.as_posix(), mxfTempFile, ar, bitrate) == 0:
				logging.info("Finished encoding file: {}".format(mxfTempFile))
			else:
				logging.info("Error encoding file: {}".format(mxfTempFile))

			logging.info("Rewrapping file: {}".format(mxfTempFile))
			if IMX_REWRAP(mxfTempFile, output_file, ar) == 0:
				logging.info("Finished rewrapping file: {}".format(output_file))
				shutil.move(input_file, done_dir.as_posix())
			else:
				logging.info("Error rewrapping file: {}".format(output_file))
