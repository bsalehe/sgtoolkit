#!/usr/bin/python

"""
PREPSEQ = reindex, join, quality filter, convert and merge!

This works with demultiplexed files from Illumina platform.
"""

import argparse, sys, os, argparse, shutil, subprocess, textwrap, logging, gzip, bz2

__author__ = "Hyun Soon Gweon"
__copyright__ = "Copyright 2015, The PIPITS Project"
__credits__ = ["Hyun Soon Gweon", "Anna Oliver", "Joanne Taylor", "Tim Booth", "Melanie Gibbs", "Daniel S. Read", "Robert I. Griffiths", "Karsten Schonrogge"]
__license__ = "GPL"
__maintainer__ = "Hyun Soon Gweon"
__email__ = "hyugwe@ceh.ac.uk"

Red = '\033[91m'
Green = '\033[92m'
Blue = '\033[94m'
Cyan = '\033[96m'
White = '\033[97m'
Yellow = '\033[93m'
Magenta = '\033[95m'
Grey = '\033[90m'
Black = '\033[90m'
Default = '\033[0m'

PEAR = "/home/hyugwe/shared/Software/pear-0.9.5-bin-64/pear-0.9.5-64"
FASTQJOIN = "fastq-join"
FASTX_FASTQ_QUALITY_FILTER = "/usr/bin/fastq_quality_filter"
FASTX_FASTQ_TO_FASTA = "/usr/bin/fastq_to_fasta"


def run_cmd(command, logger, verbose):
    logger.debug(command)
    FNULL = open(os.devnull, 'w')
    if verbose:
        p = subprocess.Popen(command, shell=True)
    else:
        p = subprocess.Popen(command, shell=True, stdout=FNULL)
    p.wait()
    FNULL.close()
    if p.returncode != 0:
        logger.error("None zero returncode: " + command)
        exit(1)


def count_sequences(options):
    logger.info("Counting sequences in rawdata")
    numberofsequences = 0
    for fr in fastqs_f:
        if extensionType == "gz":
            cmd = " ".join(["zcat", options.dataDir + "/" + fr, "|", "wc -l"])
        elif extensionType =="bz2":
            cmd = " ".join(["bzcat", options.dataDir + "/" + fr, "|", "wc -l"])
        elif extensionType =="fastq":
            cmd = " ".join(["cat", options.dataDir + "/" + fr, "|", "wc -l"])
        else:
            logger.error("Unknown extension type.")
            exit(1)
        logger.debug(cmd)
        p = subprocess.Popen(cmd, shell=True, stdout = subprocess.PIPE)
        numberofsequences += int(p.communicate()[0]) / 4
        p.wait()
    logger.info("Number of pairs of reads: " + str(numberofsequences))
    summary_file.write("Number of pairs of reads: " + str(numberofsequences) + "\n")


def reindex_fastq(options):

    print("Reindexing.")
    
    if not os.path.exists(tmpDir + "/001_reindexed"):
        os.mkdir(tmpDir + "/001_reindexed")
    else: 
        shutil.rmtree(tmpDir + "/001_reindexed")
        os.mkdir(tmpDir + "/001_reindexed") 

    for i in range(len(fastqs_l)):
        
        if extensionType == "gz":
            f = gzip.open(options.dataDir + "/" + fastqs_f[i], 'r')
            r = gzip.open(options.dataDir + "/" + fastqs_r[i], 'r')
        elif extensionType == "bz2":
            f = bz2.BZ2File(options.dataDir + "/" + fastqs_f[i], 'r')
            r = bz2.BZ2File(options.dataDir + "/" + fastqs_r[i], 'r')
        elif extensionType == "fastq":
            f = open(options.dataDir + "/" + fastqs_f[i], 'r')
            r = open(options.dataDir + "/" + fastqs_r[i], 'r')
        else:
            logger.error("Unknown extension found.")
            exit(1)
        
        f_outfile = open(tmpDir + "/001_reindexed" + "/" + fastqs_l[i] + "_F.fastq", "w")
        r_outfile = open(tmpDir + "/001_reindexed" + "/" + fastqs_l[i] + "_R.fastq" , "w")

        line_number = 1
        sequence_number = 1
        for line in f:
            if line_number % 4 == 1:
                f_outfile.write("@" + fastqs_l[i] + "_" + str(sequence_number) + "\n")
                sequence_number += 1
            else:
                f_outfile.write(line.rstrip() + "\n")
            line_number += 1
        f_outfile.close()

        line_number = 1
        sequence_number= 1
        for line in r:
            if line_number % 4 == 1:
                r_outfile.write("@" + fastqs_l[i] + "_" + str(sequence_number) + "\n")
                sequence_number += 1
            else:
                r_outfile.write(line.rstrip() + "\n")
            line_number += 1
        r_outfile.close()


def join(options):

    # Join paired-end reads                                                                                                                                                             
    logger.info("Joining paired-end reads" + " " + "[" + options.joiner_method + "]")
    if not os.path.exists(tmpDir + "/002_joined"):
        os.mkdir(tmpDir + "/002_joined")
    else:
        shutil.rmtree(tmpDir + "/002_joined")
        os.mkdir(tmpDir + "/002_joined")

    inputDir = options.dataDir

    for i in range(len(fastqs_l)):

        print(tmpDir + "/001_reindexed/" + fastqs_l[i] + "_F.fastq")

        # Check for empty files
        if os.stat(tmpDir + "/001_reindexed/" + fastqs_l[i] + "_F.fastq").st_size == 0 or os.stat(tmpDir + "/001_reindexed/" + fastqs_l[i] + "_R.fastq").st_size == 0:
            open(tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq", 'a').close()
            open(tmpDir + "/002_joined/" + fastqs_l[i] + ".discarded.fastq", 'a').close()
            open(tmpDir + "/002_joined/" + fastqs_l[i] + ".unassembled.forward.fastq", 'a').close()
            open(tmpDir + "/002_joined/" + fastqs_l[i] + ".unassembled.reverse.fastq", 'a').close()
            continue
    
        # If forwardreadsonly
        if options.forwardreadsonly:
            cmd = " ".join(["cp",
                            tmpDir + "/001_reindexed/" + fastqs_l[i] + "_F.fastq",
                            tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq"])
            run_cmd(cmd, logger, options.verbose)
            continue
            
        if options.joiner_method == "PEAR":
            cmd = " ".join([PEAR,
                            "-f", tmpDir + "/001_reindexed/" + fastqs_l[i] + "_F.fastq",
                            "-r", tmpDir + "/001_reindexed/" + fastqs_l[i] + "_R.fastq",
                            "-o", tmpDir + "/002_joined/" + fastqs_l[i],
                            "-j", options.threads,
                            "-b", options.base_phred_quality_score,
                            "-q 30",
                            "-p 0.0001"])
            run_cmd(cmd, logger, options.verbose)

            cmd = " ".join(["mv -f", 
                            tmpDir + "/002_joined/" + fastqs_l[i] + ".assembled.fastq", 
                            tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq"])
            run_cmd(cmd, logger, options.verbose)

        elif options.joiner_method == "FASTQJOIN":
            cmd = " ".join([FASTQJOIN,
                            tmpDir + "/001_reindexed/" + fastqs_f[i],
                            tmpDir + "/001_reindexed/" + fastqs_r[i],
                            "-o",
                            tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq"])
            run_cmd(cmd, logger, options.verbose)

            cmd = " ".join(["mv -f",
                            tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastqjoin",
                            tmpDir + "/002_joined/"+ fastqs_l[i] +".joined.fastq"])
            run_cmd(cmd, logger, options.verbose)

    # For summary:
    numberofsequences = 0
    for i in range(len(fastqs_l)):

        if os.stat(tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq").st_size == 0:
            continue

        cmd = " ".join(["wc -l", tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq", "| cut -f1 -d' '"])
        logger.debug(cmd)
        p = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
        numberofsequences += int(p.communicate()[0]) / 4
        p.wait()
    logger.info(       "Number of joined reads: " + str(numberofsequences))
    summary_file.write("Number of joined reads: " + str(numberofsequences) + "\n")


def qualityfilter(options):

    # Quality filter
    logger.info("Quality filtering [FASTX]")
    if not os.path.exists(tmpDir + "/003_fastqqualityfiltered"):
        os.mkdir(tmpDir + "/003_fastqqualityfiltered")
    else:
        shutil.rmtree(tmpDir + "/003_fastqqualityfiltered")
        os.mkdir(tmpDir + "/003_fastqqualityfiltered")


    for i in range(len(fastqs_f)):

        if os.stat(tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq").st_size == 0:
            open(tmpDir + "/003_fastqqualityfiltered/" + fastqs_l[i] + ".fastq", "a").close()
            continue

        cmd = " ".join([FASTX_FASTQ_QUALITY_FILTER,
                        "-i", tmpDir + "/002_joined/" + fastqs_l[i] + ".joined.fastq", 
                        "-o", tmpDir + "/003_fastqqualityfiltered/" + fastqs_l[i] + ".fastq", 
                        "-q", options.FASTX_fastq_quality_filter_q,
                        "-p", options.FASTX_fastq_quality_filter_p,
                        "-Q" + options.base_phred_quality_score])
        run_cmd(cmd, logger, options.verbose)

    # For summary:
    numberofsequences = 0
    for i in range(len(fastqs_l)):
#        cmd = " ".join(["cat", tmpDir + "/fastqqualityfiltered/" + fastqs_l[i] + ".fastq", "|", "wc -l"])
        cmd = " ".join(["wc -l", tmpDir + "/003_fastqqualityfiltered/" + fastqs_l[i] + ".fastq", "| cut -f1 -d' '"])
        p = subprocess.Popen(cmd, shell=True, stdout = subprocess.PIPE)
        numberofsequences += int(p.communicate()[0]) / 4
        p.wait()
    logger.info("Number of quality filtered reads: " + str(numberofsequences))
    summary_file.write("Number of quality filtered reads: " + str(numberofsequences) + "\n")


def convert(options):

    # Removing reads with \"N\" and FASTA conversion
    if options.FASTX_fastq_to_fasta_n:
        logger.info("Converting FASTQ to FASTA [FASTX] (also removing reads with \"N\" nucleotide")
    else:
        logger.info("Converting FASTQ to FASTA [FASTX]")

    if not os.path.exists(tmpDir + "/004_fastqtofasta"):
        os.mkdir(tmpDir + "/004_fastqtofasta")
    else:
        shutil.rmtree(tmpDir + "/004_fastqtofasta")
        os.mkdir(tmpDir + "/004_fastqtofasta")

    fastq_to_fasta_n = ""
    if options.FASTX_fastq_to_fasta_n:
        pass
    else:
        fastq_to_fasta_n = "-n"

    for i in range(len(fastqs_f)):

        if os.stat(tmpDir + "/003_fastqqualityfiltered/" + fastqs_l[i] + ".fastq").st_size == 0:
            open(tmpDir + "/004_fastqtofasta/" + fastqs_l[i] + ".fasta", "a").close()
            continue

        cmd = " ".join([FASTX_FASTQ_TO_FASTA, 
                        "-i", tmpDir + "/003_fastqqualityfiltered/" + fastqs_l[i] + ".fastq", 
                        "-o", tmpDir + "/004_fastqtofasta/" + fastqs_l[i] + ".fasta", 
                        "-Q33",
                        fastq_to_fasta_n])
        run_cmd(cmd, logger, options.verbose)


    # For summary 3:
    numberofsequences = 0
    for i in range(len(fastqs_l)):
        cmd = " ".join(["grep \"^>\"", tmpDir + "/004_fastqtofasta/" + fastqs_l[i] + ".fasta", "|", "wc -l"])
        p = subprocess.Popen(cmd, shell=True, stdout = subprocess.PIPE)
        numberofsequences += int(p.communicate()[0])
        p.wait()
    logger.info(       "Number of prepped sequences: " + str(numberofsequences))
    summary_file.write("Number of prepped sequences: " + str(numberofsequences) + "\n")


def merge(options):

    # Merge all into a file
    logger.info("Merging all into a single file")

    finaloutput = "prepped.fasta"
    outfileFinalFASTA = open(options.outputdir + "/" + finaloutput, "w")
    for i in range(len(fastqs_f)):
        line_index = 1
        logger.debug("Reading " + tmpDir + "/004_fastqtofasta/" + fastqs_l[i] + ".fasta")
        infile_fasta = open(tmpDir + "/004_fastqtofasta/" + fastqs_l[i] + ".fasta")
        for line in infile_fasta:
            outfileFinalFASTA.write(line.rstrip() + "\n")
    outfileFinalFASTA.close()



def clean(options):

    # Clean up tmp_directory
    if not options.retain:
        logger.info("Cleaning temporary directory")
        shutil.rmtree(tmpDir)

    logger.info("PREPSEQS completed.")
    summary_file.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = "PREPSEQS = reindex, join, quality filter, convert and merge!")
    parser.add_argument(
        "-i",
        action = "store",
        dest = "dataDir",
        metavar = "<DIR>",
        help = "[REQUIRED] Directory with raw sequences in gzipped FASTQ",
        required = True)
    parser.add_argument(
        "-o",
        action = "store",
        dest = "outputdir",
        metavar = "<DIR>",
        help = "[REQUIRED] Directory to output results",
        default = "sgtk_prepseqs",
        required = False)
    parser.add_argument(
        "-l",
        action = "store",
        dest = "listfile",
        metavar = "<FILE>",
        help = "Tap separated file with three columns for sample ids, forward-read filename and reverse-read filename. PIPITS_PREP will process only the files listed in this file.",
        required = False)
    parser.add_argument(
        "--FASTX-q",
        action = "store",
        dest = "FASTX_fastq_quality_filter_q",
        metavar = "<INT>",
        help = "FASTX FASTQ_QUALITY_FILTER - Minimum quality score to keep [default: 30]",
        default = "30",
        required = False)
    parser.add_argument(
        "--FASTX-p",
        action = "store",
        dest = "FASTX_fastq_quality_filter_p",
        metavar = "<INT>",
        help = "FASTX FASTQ_QUALITY_FILTER - Minimum percent of bases that must have q quality [default: 80]",
        default = "80",
        required = False)
    parser.add_argument(
        "--FASTX-n",
        action = "store_true",
        dest = "FASTX_fastq_to_fasta_n",
        help = "FASTX FASTQ_TO_FASTA - remove sequences with unknown (N) nucleotides [default: false]",
        required = False)
    parser.add_argument(
        "-b",
        action = "store",
        dest = "base_phred_quality_score",
        metavar = "<INT>",
        help = "Base PHRED quality score [default: 33]",
        default = "33",
        required = False)
    parser.add_argument(
        "--joiner_method",
        action = "store",
        dest = "joiner_method",
        help = "Joiner method: \"PEAR\" and \"FASTQJOIN\" [default: PEAR]",
        required = False,
        default = "PEAR",
        choices = ["PEAR", "FASTQJOIN"])

    parser.add_argument(
        "-r",
        action = "store_true",
        dest = "retain",
        help = "Retain intermediate files (Intermediate files use excessive disk space)",
        required = False)
    parser.add_argument(
        "-v",
        action = "store_true",
        dest = "verbose",
        help = "Verbose mode",
        required = False)
    parser.add_argument(
        "-t",
        action = "store",
        dest = "threads",
        metavar = "<INT>",
        help = "Number of Threads [default: 1]",
        default = "1",
        required = False)
    parser.add_argument(
        "--forwardreadsonly",
        action = "store_true",
        dest = "forwardreadsonly",
        help = "forwardreadsonly",
        required = False)    
    options = parser.parse_args()

    
    # Make directories (outputdir and tmpdir)                                                                                                                                                 
    if not os.path.exists(options.outputdir):
        os.mkdir(options.outputdir)

    tmpDir = options.outputdir + "/tmp"
    if not os.path.exists(tmpDir):
        os.mkdir(tmpDir)

    # Logging
    logger = logging.getLogger("prepseq")
    logger.setLevel(logging.DEBUG)

    streamLoggerFormatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    streamLogger = logging.StreamHandler()
    if options.verbose:
        streamLogger.setLevel(logging.DEBUG)
    else:
        streamLogger.setLevel(logging.INFO)
    streamLogger.setFormatter(streamLoggerFormatter)
    logger.addHandler(streamLogger)

    fileLoggerFormatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    fileLogger = logging.FileHandler(options.outputdir + "/log.txt", "w")
    fileLogger.setLevel(logging.DEBUG)
    fileLogger.setFormatter(fileLoggerFormatter)
    logger.addHandler(fileLogger)

    # Summary file
    summary_file = open(options.outputdir + "/summary.log", "w")

    # Start!
    logger.info("PREPSEQ started")


    # Check for the presence of rawdata directory
    logger.debug("Checking for presence of input directory")
    if not os.path.exists(options.dataDir):
        logger.error("Cannot find \"" + options.dataDir + "\" directory. Ensure you have the correct name of the directory where your Illumina sequences are stored")
        exit(1)

    fastqs_l = []
    fastqs_f = []
    fastqs_r = []

    # if list is provided...
    if options.listfile:
        logger.info("Processing user-provided listfile")
        try:
            listfile = open(options.listfile, "r")
        except IOError:
            logger.error("\"" + options.listfile + "\" not found.")
            exit(1)

        for l in listfile:
            if l.strip(" ").strip("\n") != "" and not l.startswith("#"):
                l = l.rstrip().split("\t")

                if l[0].find("_") != -1:
                    logger.error("\"_\" is not allowed in the sample id")
                    exit(1)

                fastqs_l.append(l[0])
                fastqs_f.append(l[1])
                fastqs_r.append(l[2])

        listfile.close()
    

    # if not provided
    if not options.listfile:
        logger.info(Default + "Getting list of fastq files and sample ID from input folder")
        fastqs = []
        for file in os.listdir(options.dataDir):
            if \
                    file.endswith(".fastq.gz") or \
                    file.endswith(".bz2") or \
                    file.endswith(".fastq"):
                fastqs.append(file)

        if len(fastqs) % 2 != 0:
            logger.error("There are missing pair(s) in the Illumina sequences. Check your files and labelling")
            exit(1)

        coin = True
        for fastq in sorted(fastqs):
            if coin == True:
                fastqs_f.append(fastq)
            else:
                fastqs_r.append(fastq)
            coin = not coin

        for i in range(len(fastqs_f)):
            if fastqs_f[i].split("_")[0] != fastqs_r[i].split("_")[0]:
                logger.error("Problem with labelling FASTQ files.")
                exit(1)
            fastqs_l.append(fastqs_f[i].split("_")[0])

    # Check
    if len(fastqs_f) != len(fastqs_r):
        logger.error("Different number of forward FASTQs and reverse FASTQs")
        exit(1)


    # Done loading. Now check the file extensions.
    filenameextensions = []
    for filename in (fastqs_f + fastqs_r):
        filenameextensions.append(filename.split(".")[-1].rstrip())
    if len(set(filenameextensions)) > 1:
        logger.error("More than two types of extensions")
        exit(1)
    extensionType = next(iter(filenameextensions))


    count_sequences(options)
    reindex_fastq(options)
    join(options)
    qualityfilter(options)
    convert(options)
    merge(options)
    clean(options)

    exit(0)
