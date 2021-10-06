"""The tool for making a backup of 'show running' configuration for a list of Eltex commutators and finding changes"""

import concurrent.futures
import hashlib
import os
import re
import threading
from time import time
from datetime import datetime
from Exscript import Account
from Exscript.protocols import SSH2
from Exscript.util.interact import read_login

cwd = os.getcwd()
acc = read_login()


def parser():
    """Creates a pool of tasks that write running configs to logfiles"""

    start_time = time()
    iplist = []
    with open('ips.txt', 'r') as switchlist:
        for line in switchlist:
            ip, name = line.split()
            iplist.append(f'{ip} {name} {datetime.strftime(datetime.now(), "%H-%M")}.txt')
    dirname = datetime.strftime(datetime.now(), "%Y.%m.%d")
    try:  # WinError occurs if folder already exists
        os.mkdir(dirname)
    except:
        pass
    os.chdir(dirname)
    print(dirname)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(exconnect, iplist)
    print('\nExecution time: {} sec'.format(int(time()-start_time)))


def exconnect(address_name):
    """Connects to the commutator and writes <show run> output to the file"""

    ip = address_name.split()[0]
    conn = SSH2()
    print(ip, 'Connecting')
    try:
        conn.connect(ip)
        conn.login(acc)
        conn.execute('terminal datadump')
        print(ip, 'Reading...')
        conn.execute('sh ru')
        log = conn.response
        print(ip, 'Reading is complete')
        conn.send('exit\r')
        conn.close()
        with open(address_name, 'w') as file:
            if log:
                file.write(log)
                print(ip, 'Log is ready')
            else:
                print(ip, 'Connection failed\n')
    except Exception as e:
        print(ip, e)
        return ''


def compare_files(file1, file2, name):
    """Compares md5 summ of 2 files to find changes"""

    print(name)
    # If previous file is empty, function logs it and stops comparison
    if not open(file1, 'rb').read():
        print(f'\n{name} Previous config file is empty')
        mismatch_list.append(f'\n{name} Previous file is empty')
        return None
    elif not open(file2, 'rb').read():
        print(f'\n{name} Current config file is empty')
        mismatch_list.append(f'\n{name} Current config file is empty')
        return None
    file1md5 = hashlib.md5(open(file1, 'rb').read()).hexdigest()
    file2md5 = hashlib.md5(open(file2, 'rb').read()).hexdigest()
    if file1md5 == file2md5:
        print('OK\n')
    else:
        print('Mismatch!\n')
        mismatch_list.append('\n' + name)
        file1sliced = fileslicer(file1)
        file2sliced = fileslicer(file2)
        for i in range(30):
            if file1sliced[i] != file2sliced[i]:
                mismatch_list.append('\nPrevious:')
                mismatch_list.extend(file1sliced[i])
                mismatch_list.append('\nCurrent:')
                mismatch_list.extend(file2sliced[i])


def fileslicer(file):
    """Separates a file to a few slices:
    [0] - general setup, [1]-[24] - gi interfaces, [25]-[28] - te interfaces, [29] - final block"""

    blocklist = ['interface gigabitethernet1/0/%d' % i for i in range(1, 25)] + \
                ['interface tengigabitethernet1/0/%d' % i for i in range(1, 5)] + ['interface vlan 102', '']
    with open(file, 'r') as f:
        f = iter(f.readlines())
        f_lines = [[] for _ in range(30)]
        for i in range(30):
            while True:
                try:
                    newline = next(f).strip()
                    if newline == '' or newline == '!':
                        continue
                    if newline != blocklist[i]:
                        f_lines[i].append(newline)
                    else:
                        f_lines[i + 1].append(newline)
                        break
                except StopIteration:
                    break
    return f_lines


if __name__ == "__main__":
    parser()
    # Comparison folder may be given in folder_1 to compare current config with a certain day
    folder_1 = ''
    os.chdir(cwd)
    # A list wheremismatching commutators will be written
    mismatch_list = []
    foldlist = (next(os.walk(os.getcwd()))[1])
    # leaves only folders with dates like YYYY.MM.DD or YYYY.M.D etc.
    foldlist = [folder for folder in foldlist if bool(re.match(r'\d{4}.\d{1,2}.\d{1,2}', folder))]
    # Choosing folders to compare
    if not folder_1:
        try:
            folder_1 = foldlist[-2]
        except IndexError:
            print('There are no previous folders! Exiting.')
            raise Exception
    folder_2 = foldlist[-1]
    print(f"\nFolders to be compared: {folder_1} and {folder_2}\n")
    with open('ips.txt', 'r') as switchlist:
        for line in switchlist:
            try:
                ip, name = line.split()
                os.chdir(cwd + '\\' + folder_1)
                filelist = (next(os.walk(os.getcwd()))[2])
                # Making dsfiles: list of files for a distinct switch. There may be few files for one switch in a folder
                dsfiles = []
                for filename in filelist:
                    if ip in filename:
                        dsfiles.append(filename)
                # Selecting the last (or the only) file for a commutator
                file_1 = dsfiles[-1]
                os.chdir(cwd + '\\' + folder_2)
                filelist = (next(os.walk(os.getcwd()))[2])
                dsfiles = []
                for filename in filelist:
                    if ip in filename:
                        dsfiles.append(filename)
                file_2 = dsfiles[-1]
                # Now comparing files
                file_1 = cwd + '\\' + folder_1 + '\\' + file_1
                file_2 = cwd + '\\' + folder_2 + '\\' + file_2
                compare_files(file_1, file_2, name)
            except IndexError:
                print(name, 'Unable to find two files')
    os.chdir(cwd)
    with open('log.txt', 'a') as report:
        report.write(datetime.strftime(datetime.now(), "%Y.%m.%d %H:%M\n"))
        if mismatch_list:
            print('Mismatch in commutators configs:')
            report.write('Mismatch in commutators configs:\n')
            for n in mismatch_list:
                print(n)
                report.write(n + '\n')
        else:
            print('No changes found!')
            report.write('No changes found!\n')
        report.write('\n')
