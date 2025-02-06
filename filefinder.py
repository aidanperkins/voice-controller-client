from os import path
from glob import glob
from json import dump

def update_list(depth=5,dirs="C:/",exts=[".exe"],saveas="file_paths") :

    # Find all .exe files and shortcuts in the directories and their subdirectories up to max_depth
    exe_files =[]
    program_dict = {}
    for directory in dirs:
        for i in range(depth+1):
            for e in exts :
                search_path = path.join(directory, *["*"]*i, "*"+e)
                exe_files.extend(glob(search_path))

    # Print the full path of each .exe file found
    fp = open(saveas+".json","w")

    for exe_file in exe_files:
        file_path = path.abspath(exe_file)

        # To get program name from file path
        # get path ending
        file_name = str.split(str(file_path),sep="\\")
        file_name = file_name[len(file_name)-1]
        # reverse string
        file_name = file_name[::-1]
        # remove extension
        file_name = str.split(file_name,sep=".",maxsplit=1)[1]
        # reverse string again
        file_name = file_name[::-1]
        
        program_dict.update({file_name:file_path})

    dump(program_dict, fp=fp,indent=0)
    fp.close()