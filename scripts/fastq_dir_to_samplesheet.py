#!/usr/bin/env python
#
# Dựa trên bin/fastq_dir_to_samplesheet.py của nf-core/viralrecon (giấy phép MIT).
# Thay đổi so với bản gốc:
#   - Không báo KeyError khi có file R2 mà không có R1 cùng mẫu (in cảnh báo và bỏ qua).
#   - Cảnh báo khi số file R1 và R2 của một mẫu không bằng nhau.
# Gợi ý đặt tên mẫu: với tên file D1-879_S35_L001_R1_001.fastq.gz, mặc định tên mẫu là "D1-879_S35_L001"
# (mỗi lane một mẫu riêng). Để gộp nhiều lane thành một mẫu (technical replicates, pipeline tự nối),
# dùng:  -sn -si 2   (giữ 2 phần đầu tách theo "_"  ->  "D1-879_S35").
#

import os
import sys
import glob
import argparse


def parse_args(args=None):
    Description = "Generate nf-core/viralrecon samplesheet from a directory of FastQ files."
    Epilog = "Example usage: python fastq_dir_to_samplesheet.py <FASTQ_DIR> <SAMPLESHEET_FILE>"

    parser = argparse.ArgumentParser(description=Description, epilog=Epilog)
    parser.add_argument("FASTQ_DIR", help="Folder containing raw FastQ files.")
    parser.add_argument("SAMPLESHEET_FILE", help="Output samplesheet file.")
    parser.add_argument(
        "-r1",
        "--read1_extension",
        type=str,
        dest="READ1_EXTENSION",
        default="_R1_001.fastq.gz",
        help="File extension for read 1.",
    )
    parser.add_argument(
        "-r2",
        "--read2_extension",
        type=str,
        dest="READ2_EXTENSION",
        default="_R2_001.fastq.gz",
        help="File extension for read 2.",
    )
    parser.add_argument(
        "-se",
        "--single_end",
        dest="SINGLE_END",
        action="store_true",
        help="Single-end information will be auto-detected but this option forces paired-end FastQ files to be treated as single-end so only read 1 information is included in the samplesheet.",
    )
    parser.add_argument(
        "-sn",
        "--sanitise_name",
        dest="SANITISE_NAME",
        action="store_true",
        help="Whether to further sanitise FastQ file name to get sample id. Used in conjunction with --sanitise_name_delimiter and --sanitise_name_index.",
    )
    parser.add_argument(
        "-sd",
        "--sanitise_name_delimiter",
        type=str,
        dest="SANITISE_NAME_DELIMITER",
        default="_",
        help="Delimiter to use to sanitise sample name.",
    )
    parser.add_argument(
        "-si",
        "--sanitise_name_index",
        type=int,
        dest="SANITISE_NAME_INDEX",
        default=1,
        help="After splitting FastQ file name by --sanitise_name_delimiter all elements before this index (1-based) will be joined to create final sample name.",
    )
    return parser.parse_args(args)


def fastq_dir_to_samplesheet(
    fastq_dir,
    samplesheet_file,
    read1_extension="_R1_001.fastq.gz",
    read2_extension="_R2_001.fastq.gz",
    single_end=False,
    sanitise_name=False,
    sanitise_name_delimiter="_",
    sanitise_name_index=1,
):
    def sanitize_sample(path, extension):
        """Retrieve sample id from filename"""
        sample = os.path.basename(path).replace(extension, "")
        if sanitise_name:
            sample = sanitise_name_delimiter.join(
                os.path.basename(path).split(sanitise_name_delimiter)[:sanitise_name_index]
            )
        return sample

    def get_fastqs(extension):
        """
        Needs to be sorted to ensure R1 and R2 are in the same order
        when merging technical replicates. Glob is not guaranteed to produce
        sorted results.
        See also https://stackoverflow.com/questions/6773584/how-is-pythons-glob-glob-ordered
        """
        return sorted(glob.glob(os.path.join(fastq_dir, f"*{extension}"), recursive=False))

    read_dict = {}

    ## Get read 1 files
    for read1_file in get_fastqs(read1_extension):
        sample = sanitize_sample(read1_file, read1_extension)
        if sample not in read_dict:
            read_dict[sample] = {"R1": [], "R2": []}
        read_dict[sample]["R1"].append(read1_file)

    ## Get read 2 files
    if not single_end:
        for read2_file in get_fastqs(read2_extension):
            sample = sanitize_sample(read2_file, read2_extension)
            if sample not in read_dict:
                print(f"WARNING: {read2_file} có R2 nhưng không có R1 tương ứng, bỏ qua.", file=sys.stderr)
                continue
            read_dict[sample]["R2"].append(read2_file)

    ## Write to file
    if len(read_dict) > 0:
        out_dir = os.path.dirname(samplesheet_file)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(samplesheet_file, "w") as fout:
            header = ["sample", "fastq_1", "fastq_2"]
            fout.write(",".join(header) + "\n")
            for sample, reads in sorted(read_dict.items()):
                if not single_end and len(reads["R1"]) != len(reads["R2"]):
                    print(f"WARNING: mẫu {sample} có {len(reads['R1'])} file R1 nhưng {len(reads['R2'])} file R2.",
                          file=sys.stderr)
                for idx, read_1 in enumerate(reads["R1"]):
                    read_2 = ""
                    if idx < len(reads["R2"]):
                        read_2 = reads["R2"][idx]
                    sample_info = ",".join([sample, read_1, read_2])
                    fout.write(f"{sample_info}\n")
    else:
        error_str = "\nWARNING: No FastQ files found so samplesheet has not been created!\n\n"
        error_str += "Please check the values provided for the:\n"
        error_str += "  - Path to the directory containing the FastQ files\n"
        error_str += "  - '--read1_extension' parameter\n"
        error_str += "  - '--read2_extension' parameter\n"
        print(error_str)
        sys.exit(1)


def main(args=None):
    args = parse_args(args)

    fastq_dir_to_samplesheet(
        fastq_dir=args.FASTQ_DIR,
        samplesheet_file=args.SAMPLESHEET_FILE,
        read1_extension=args.READ1_EXTENSION,
        read2_extension=args.READ2_EXTENSION,
        single_end=args.SINGLE_END,
        sanitise_name=args.SANITISE_NAME,
        sanitise_name_delimiter=args.SANITISE_NAME_DELIMITER,
        sanitise_name_index=args.SANITISE_NAME_INDEX,
    )


if __name__ == "__main__":
    sys.exit(main())
