"""Script in order to get analytics about the process"""
import time
import json
from subprocess import Popen, PIPE
import os
import sqlite3


class SysInfo(object):
    """pass"""
    def __init__(self, path_file, interval, convert_js: bool):
        self.path_file = path_file
        self.interval = interval
        self.con = sqlite3.connect('sys_informer.db')
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        self.db_table = 'sys_info'
        self.json_file = 'system_analysis.json'
        self.convert_js = convert_js

    def check_table(self):
        """Checks if table exists or not"""
        try:
            self.cur.execute("""SELECT * FROM sys_info""")
        except sqlite3.OperationalError:
            self.cur.execute("""CREATE TABLE {}
                                (time datetime, rss bigint, vms bigint,
                                cpu double precision, fd_count bigint)""".format(self.db_table))
            self.con.commit()

    def start_process(self) -> int:
        """The process starts and returns PID number"""
        self.check_table()
        start_file = self.path_file.split()
        exec_file = Popen(start_file, stdout=PIPE, stderr=PIPE, shell=True)
        return exec_file.pid

    def get_process_info(self, pid: int) -> dict:
        """The method returns the information of cpu and memory"""
        exec_cmd = Popen(f"ps -p {pid} -o rss=,vsz=,%cpu=", stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = exec_cmd.communicate()
        if len(stdout) == 0:
            return {'status': False}
        else:
            result = stdout.splitlines()[0].decode().split()
            fd = self.get_file_descriptors(pid)
            result.append(str(fd))
            return {'status': True, 'data_process': dict(zip(['rss', 'vms', 'cpu', 'fd_count'], result))}

    def get_file_descriptors(self, pid: int) -> int:
        """The method returns the quantity of file descriptors for current process"""
        exec_fd = Popen(f"lsof -p {pid}", stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = exec_fd.communicate()
        fd = stdout.decode().splitlines()[1:]
        return len(fd)

    def add_to_db_table(self, pid: int) -> dict:
        """The method adds the rows to the database table, when the process ends, the method
        creates logic in order to finish the program and calls other method in order to convert
        the rows into json format"""
        data = self.get_process_info(pid)
        if data['status'] is False:
            if self.convert_js is True:
                return {'status': False, 'js': self.convert_info_to_json()}
            else:
                self.con.commit()
                self.con.close()
                return {'status': False}
        else:
            query = """INSERT INTO {} VALUES (DateTime('now'),?,?,?,?)""".format(self.db_table)
            self.cur.execute(query, tuple(data['data_process'].values()))
            self.con.commit()
            return {'status': True}

    def convert_info_to_json(self):
        """The method converts rows into json format and generates data file"""
        query = """SELECT * FROM {} ORDER BY time""".format(self.db_table)
        rows = self.cur.execute(query).fetchall()
        self.con.commit()
        self.con.close()
        f = open(self.json_file, 'w')
        f.write(json.dumps([dict(row) for row in rows]))
        f.close()


def main():
    """main process"""
    interval = 0
    enter = ""
    while os.path.isfile(enter) is False:
        print('enter `exit` in order to end program')
        enter = input('Enter path to init file: ')
        if enter == 'exit':
            return False
        if interval == 0:
            interval = float(input('Enter interval: '))

    proc = SysInfo(path_file=enter, interval=interval, convert_js=True)
    pid_number = proc.start_process()

    while True:
        info_to_db = proc.add_to_db_table(pid=pid_number)
        if info_to_db['status'] is False:
            return False

        time.sleep(interval)


if __name__ == '__main__':
    main()
