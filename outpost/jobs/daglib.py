import sys
import os
import time
import json
import mmap
import re
import paramiko
import logging
import io
import requests
import six
import importlib
from six import string_types
from pythonping import ping
import shlex, subprocess
from url_normalize import url_normalize
import threading
import datefinder
import datetime
import base64
from requests.auth import HTTPBasicAuth
import math
from pexpect import pxssh
from pexpect import TIMEOUT, EOF
import tempfile
import jwt as jwt_checker
import traceback



logger = logging.getLogger()

class jira:
    def __init__(self, daglib):
       self.dag = daglib

    def get_issuetype_id(self, issuetype):
        resp = self.dag.api("get", "jira", "issuetype", {})
        issuetype_array = json.loads(resp['api_resp_content'])
        for issuetype_obj in issuetype_array:
            if issuetype_obj['name'] == issuetype:
               return issuetype_obj['id']
        return None


    def create_issue(self, project, issuetype, summary, description):

        issuetype_id = self.get_issuetype_id(issuetype)

        payload = {
          "fields": {
            "summary": summary,
            "issuetype": {
              "id": issuetype_id
            },
            "project": {
              "key": project
            },
            "description": description
          }
        }

        return self.dag.api("post", "jira", "issue", payload)


class fileLineIter:
    def __init__(self, filehandle=None):
       self.filehandle = filehandle

    def __iter__(self):
       return self

    def __next__(self):
       line = self.filehandle.readline()
       if line:
          return line
       else:
          self.filehandle.close()
          raise StopIteration

class prolog:
    def __init__(self, lines=None, filename=None, filehandle=None):
        self.lines = []
        self.reverse = False
        self.tstp_formats = []
        self.init_tstp_regex_array()
        self.matching_regex_format = None

        if lines:
            self.lines = lines
        elif filehandle:
           #self.lines = fileLineIter(filehandle=filehandle)
           self.lines = self.reverseFileLineIter(filehandle=filehandle)
           self.reverse = True
        elif filename:
           filehandle = open(filename, "r")
           #self.lines = fileLineIter(filehandle=filehandle)
           self.lines = self.reverseFileLineIter(filehandle=filehandle)
           self.reverse = True

    def init_tstp_regex_array(self):
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d\*\d\d\d[\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d [A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d.\d\d\d [A-Z][A-Z]T)")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d \d\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/[A-Z][a-zA-Z][a-zA-Z]/\d\d\d\d:\d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d, \d\d\d\d \d?\d:\d?\d:\d?\d (AM|PM))")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d \d\d\d\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d \d\d\d\d)")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?([A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\dT\d?\d:\d?\d:\d?\d[\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\dT\d?\d:\d?\d:\d?\d.\d\d\d'[\+\-]\d\d\d\d')")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\dT\d?\d:\d?\d:\d?\d.\d\d\dZ)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d[\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d,\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d/\d?\d/\d?\d\*\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d [A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d.\d\d\d\*[A-Z][A-Z]T)")
        self.tstp_formats.append(r".*?(\d\d\d\d [A-Z][a-zA-Z][a-zA-Z] \d?\d \d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d,\d\d\d[\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d.\d\d\d[\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d'[\+\-]\d\d\d\d')")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d'T'\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d\*\d?\d:\d?\d:\d?\d:\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d-\d?\d-\d?\d\*\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d,\d\d\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d,\d\d\d)")
        self.tstp_formats.append(r".*?(\d\d-\d?\d-\d?\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d/\d?\d/\d?\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d?\d\d?\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d\d\d\d\d?\d\d?\d \d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\*\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\d\d\*\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\d\d\*\d?\d:\d?\d:\d?\d\*\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d \d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\d\d \d?\d:\d?\d:\d?\d [\+\-]\d\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d:\d?\d:\d?\d)")     
        self.tstp_formats.append(r".*?(\d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d:\d?\d:\d?\d,\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/[A-Z][a-zA-Z][a-zA-Z] \d?\d:\d?\d:\d?\d,\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/[A-Z][a-zA-Z][a-zA-Z]/\d\d\d\d:\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d/[A-Z][a-zA-Z][a-zA-Z]/\d\d\d\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d-[A-Z][a-zA-Z][a-zA-Z]-\d\d\d\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d-[A-Z][a-zA-Z][a-zA-Z]-\d\d\d\d \d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d [A-Z][a-zA-Z][a-zA-Z] \d\d\d\d \d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d [A-Z][a-zA-Z][a-zA-Z] \d\d\d\d \d?\d:\d?\d:\d?\d\*\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d\d?\d_\d?\d:\d?\d:\d?\d)")
        self.tstp_formats.append(r".*?(\d?\d\d?\d_\d?\d:\d?\d:\d?\d.\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\d\d \d?\d:\d?\d:\d?\d (AM|PM):\d\d\d)")
        self.tstp_formats.append(r".*?(\d?\d/\d?\d/\d\d\d\d \d?\d:\d?\d:\d?\d (AM|PM))")           

    def get_matching_tstp_regex_format(self, line):
        for idx, regex in enumerate(self.tstp_formats):
            if re.match(regex, line):
                self.matching_regex_format = regex
                break

    def rev_lines(self):
        if self.reverse and len(self.lines) > 0:
           self.lines.reverse()
           self.reverse = False

    def reverseFileLineIter(self, filehandle):
        segment = None
        offset = 0
        filehandle.seek(0, os.SEEK_END)
        file_size = remaining_size = filehandle.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + 8192)
            filehandle.seek(file_size - offset)
            buf = filehandle.read(min(remaining_size, 8192))
            remaining_size -= 8192
            lines = []
            if type(buf) is bytes:
               lines = buf.decode().split('\n')
            else:
               lines = buf.split('\n')
            # The first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # If the previous chunk starts right from the beginning of line
                # do not concat the segment to the last line of new chunk.
                # Instead, yield the segment first
                if buf[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if lines[index]:
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment

    def extract_tstp(self, line):
        #There is some weirdness with datefinder. If the line ends with a <number>\n, it is parsing as a date
        #If you strip the \n then not a problem
        try:
            matches = list(datefinder.find_dates(line.strip()))
            if len(matches) > 0:
                return datetime.datetime.timestamp(matches[0])
            else:
                return None
        except:
            return None

    def get_tstp(self, line):
        return extract_tstp(self, line)

    def get_tstp_old(self, line):
        # Earlier the extract_tstp function needed to be wrapped in our own regex to get a timestamp
        # We don't need this now. the datefinder library seems to have updated their regex
        start = 1000000000
        cur_tstp = None
        if not self.matching_tstp_regex_format:
            #We haven't yet identified the format of the tstp. Let's do that first
            self.get_matching_tstp_regex_format(line)

        if self.matching_tstp_regex_format:
            # Okay we have a matching format id
            m = re.match(self.matching_tstp_regex_format, line)
            if m:
                tstp = self.extract_tstp(m.group(1))
                if tstp and m.start(1) < start:
                    cur_tstp = tstp
                    start = m.start(1)

        return cur_tstp

    def is_in_last(self, line, sec):
        tstp = self.get_tstp(line)
        diff = (time.time() - tstp)
        return (diff >=0 and diff <= sec)

    def is_in_last_mins(self, line, min=1):
        self.is_in_last(line,min*60)

    def is_in_last_hrs(self, line, hr=1):
        self.is_in_last(line,hr*60*60)

    def is_in_last_days(self, line, day=1):
        val = self.is_in_last(line,day*60*60*24)
        return val


    def get_btwn(self, start, end):
        plg = prolog()

        start_tstp = start
        if type(start) is str:
            start_tstp = self.get_tstp(start)
        end_tstp = end
        if type(end) is str:
            end_tstp = self.get_tstp(end)

        filtered = []
        started = False
        for line in self.lines:
            tstp = self.get_tstp(line)
            print("Line: ", line, file=sys.stdout)
            print("Tstp: ", tstp, file=sys.stdout)
            print("start: ", start_tstp, " end_tstp: ", end_tstp, file=sys.stdout)
            sys.stdout.flush()

            if (tstp or started):
                print("Line is good", file=sys.stdout)
                sys.stdout.flush()
                if started or (tstp and (tstp >= start_tstp and tstp <= end_tstp)):
                    filtered.append(line)
                if self.reverse:
                   if tstp and (tstp <= end_tstp):
                      started = True
                   if tstp and (tstp <= start_tstp):
                      break
                else:
                   if tstp and (tstp >= start_tstp):
                      started = True
                   if tstp and (tstp >= end_tstp):
                      break
        plg.lines = filtered
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_after(self, start):
        return self.get_btwn(start, time.time())

    def get_before(self, end):
        return self.get_btwn(0, end)

    def get_in_last(self, sec):
        end = time.time()
        start = end - sec
        return self.get_btwn(start, end)


    def get_in_last_mins(self, min=1):
        return self.get_in_last(min*60)

    def get_in_last_hrs(self, hr=1):
        return self.get_in_last(hr*60*60)

    def get_in_last_days(self, day=1):
        return self.get_in_last(day*24*60*60)

    def get_containing_any(self, strings):
        plg = prolog()
        for line in self.lines:
            # print("Line: ", line, file=sys.stdout)
            # sys.stdout.flush()
            for string in strings:
                # print("String: ", string, file=sys.stdout)
                # sys.stdout.flush()
                if (string.lower() in line.lower()):
                    plg.lines.append(line)
                    # print("Found: ", string, file=sys.stdout)
                    # sys.stdout.flush()
                    break
        if self.reverse:
           plg.lines.reverse()
        return plg


    def get_containing_all(self, strings):
        plg = prolog()
        filtered = []
        for line in self.lines:
            match = True
            for string in strings:
                if (string.lower() not in line.lower()):
                    match = False
                    break
            if match:
                filtered.append(line)
        plg.lines = filtered
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_containing(self, string):
        plg = prolog()
        for line in self.lines:
            if (string.lower() in line.lower()):
               plg.lines.append(line)
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_ipv4_addr(self):
        plg = prolog()
        for line in self.lines:
            m = re.search('(\d+\.\d+\.\d+\.\d+)', line, flags=re.IGNORECASE)
            if m:
               plg.lines.append(m.group(1))
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_num_after(self, st):
        plg = prolog()
        for line in self.lines:
            m = re.search(st+'\s*(-?\d+\.?\d+)', line, flags=re.IGNORECASE)
            if m:
               if "." in m.group(1):
                  plg.lines.append(float(m.group(1)))
               else:
                  plg.lines.append(int(m.group(1)))
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_num_before(self, st):
        plg = prolog()
        for line in self.lines:
            m = re.search('(-?\d+\.?\d+)\s*'+st, line, flags=re.IGNORECASE)
            if m:
               if "." in m.group(1):
                  plg.lines.append(float(m.group(1)))
               else:
                  plg.lines.append(int(m.group(1)))
        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_col(self, col):
        plg = prolog()
        for line in self.lines:
            parts = line.split()
            if (col > 0) and (len(parts) >= col-1):
                  plg.lines.append(parts[col-1])
            else:
                  plg.lines.append("")

        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_table_cell(self, col, row):
        plg = prolog()
        col_id = col;
        label_cols = 0
        for l, line in enumerate(self.lines):
            parts = line.split()
            if type(col) is str and l == 0:
               label_cols = len(parts)
               col_id = 0
               #These are column labels
               for p, part in enumerate(parts):
                   if part.lower() == col.lower():
                      col_id = p+1
                      break
               continue
            else:
               if (label_cols > 0) and len(parts) == label_cols + 1:
                  col_id += 1

            if parts and (type(row) is str and row.lower() == parts[0].lower()) or (type(row) is int and row > 0 and l == row):
               #found a matching row
               logger.info("parts : " + json.dumps(parts))
               logger.info("l : " + str(l))
               logger.info("col_id : " + str(col_id))

               if (col_id > 0) and (len(parts) >= col_id-1):
                     plg.lines.append(parts[col_id-1])
               else:
                     plg.lines.append("")
               logger.info("lines : " + json.dumps(plg.lines))

        if self.reverse:
           plg.lines.reverse()
        return plg

    def get_between_patterns(self, start, end, must_include=None, max_duration=None, min_duration=None, incl_start=True, incl_end=True):
        plg = prolog()
        started = False
        found_must_include = False
        fits_max_duration = False
        fits_min_duration = False
        finish_pattern_found = False
        for line in self.lines:
           if self.reverse:
             if (not started) and (end.lower() in line.lower()):
                started = True
                #print("Started: ", line, file=sys.stdout)
                #sys.stdout.flush()
                if incl_end:
                   plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True
             elif started and (start.lower() in line.lower()):
                started = False
                finish_pattern_found = True
                #print("Ended: ", line, file=sys.stdout)
                #sys.stdout.flush()
                if incl_start:
                   plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True
                if len(plg.lines) > 1:
                   #Check duration of the snippet
                   start_tstp = self.get_tstp(plg.lines[-1])
                   end_tstp = self.get_tstp(plg.lines[0])
                   #print("line0: ", plg.lines[0], file=sys.stdout)
                   #print("lineEnd: ", plg.lines[-1], file=sys.stdout)
                   #print("diff: ", end_tstp-start_tstp, file=sys.stdout)
                   #print("max_duration: ", max_duration, file=sys.stdout)
                   #print("min_duration: ", min_duration, file=sys.stdout)
                   if (not max_duration) or ((end_tstp - start_tstp) <= max_duration):
                      fits_max_duration = True
                   #print("fits_max_duration: ", fits_max_duration, file=sys.stdout)
                   if (not min_duration) or ((end_tstp - start_tstp) >= min_duration):
                      fits_min_duration = True
                   #print("fits_min_duration: ", fits_min_duration, file=sys.stdout)
                   sys.stdout.flush()
                if (
                     ((not must_include) or found_must_include) and
                     ((not max_duration) or fits_max_duration) and
                     ((not min_duration) or fits_min_duration)
                ):
                   #print("Breaking: ", must_include, found_must_include, max_duration, fits_max_duration, min_duration, fits_min_duration, line, file=sys.stdout)
                   #sys.stdout.flush()

                   break
                else:
                   #print("Clearing: ", must_include, found_must_include, max_duration, fits_max_duration, min_duration, fits_min_duration, line, file=sys.stdout)
                   #sys.stdout.flush()
                   finish_pattern_found = False
                   fits_max_duration = False
                   fits_min_duration = False
                   found_must_include = False
                   plg.lines = []
             elif started:
                plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True
           else:
             if (not started) and (start.lower() in line.lower()):
                started = True
                if incl_start:
                   plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True
             elif started and (end.lower() in line.lower()):
                started = False
                finish_pattern_found = True
                if incl_end:
                   plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True
                if len(plg.lines) > 1:
                   #Check duration of the snippet
                   start_tstp = self.get_tstp(plg.lines[0])
                   end_tstp = self.get_tstp(plg.lines[-1])
                   if max_duration and ((end_tstp - start_tstp) <= max_duration):
                      fits_max_duration = True
                   if min_duration and ((end_tstp - start_tstp) >= min_duration):
                      fits_min_duration = True
                if (
                     ((not must_include) or found_must_include) and
                     ((not max_duration) or fits_max_duration) and
                     ((not min_duration) or fits_min_duration)
                ):
                   #print("Breaking: ", must_include, found_must_include, line, file=sys.stdout)
                   #sys.stdout.flush()

                   break
                else:
                   finish_pattern_found = False
                   fits_max_duration = False
                   fits_min_duration = False
                   found_must_include = False
                   plg.lines = []
             elif started:
                plg.lines.append(line)
                if must_include and (must_include.lower() in line.lower()):
                   found_must_include = True

        if not finish_pattern_found:
           plg.lines = []
        if self.reverse:
           plg.lines.reverse()
        return plg


    def remove_quotes(self):
        plg = prolog()
        for l, line in enumerate(self.lines):
           newline = line.replace("\"","")
           newline = newline.replace("\'","")
           plg.lines.append(newline)
        if self.reverse:
           plg.lines.reverse()
        return plg


    def count(self):
        return len(self.lines)
    def last(self):
        if self.lines:
           return self.lines[-1]
        else:
           return None

    def first(self):
        if self.lines:
           return self.lines[0]
        else:
           return None

class daglib:
    def __init__(self, state, user, jwt):
        self.allowed_vars = [
            '_problem', 
            '_exception_msg',
            'exception_msg',
            '_to_session', 
            '_to_ticket',
            '_super_node', 
            '_schedule', 
            '_dag_to_execute', 
            '_dag_id', 
            '_node_id', 
            '_params', 
            '_auto_remediate',
            '_resolve_ticket',
            '_proxy_label',
            '_traces',
            '_x_label',
            '_y_label',
            '_graph_title',
            '_summary',
            '_wait_for_user_input',
            '_exit_loop'
        ]
        self.version = 1.732
        self.verbose = True
        self.respq = None
        self.user = user
        self.jwt = jwt
        self.cmd_exec_url = os.environ.get('CMD_EXEC_URL', 'http://cmd-exec:7777/')
        if hasattr(state, 'respq'):
            self.respq = state.respq



    def is_jsonable(self, x):
       try:
           json.dumps(x)
           return True
       except:
           return False

    def only_jsonable(self, mydict):
        newdict = {}
        for key, value in mydict.items():
            if key in self.allowed_vars and self.is_jsonable(value):
               newdict[key] = value
        return newdict

    def formatLocals(self, tb):
        #logger.info("Dumping function info")
        func_info = {}
        while tb:
           #logger.info("Processing a frame")
           lcls = tb.tb_frame.f_locals
           if '_info' in lcls:
              #Create a datastructure
              func_name = lcls['_info'].function
              lineno = lcls['_info'].lineno
              nodename = lcls['nodename']
              lcls.pop('nodename')
              clean_lcls = self.only_jsonable(lcls)
              func_info[func_name] = {'nodename' : nodename, 'lineno':lineno, 'locals' : clean_lcls}
              #logger.info(func_info[func_name])
           tb = tb.tb_next
        return func_info


    def aws_get_time_points_period(self, period_str):
        period = period_str
        max_data_points = 1430

        tt = re.search("(\d+)\s*d|(\d+)\s*day|(\d+)\s*days", period_str, re.IGNORECASE)
        if tt:
            days = tt.group(1)
            period = int(days) * 3600 *24

        tt = re.search("(\d+)\s*h|(\d+)\s*hr|(\d+)\s*hrs|(\d+)\s*hour|(\d+)\s*hours", period_str, re.IGNORECASE)
        if tt:
            hours = tt.group(1)
            period = int(hours) * 3600

        tt = re.search("(\d+)\s*m|(\d+)\s*min|(\d+)\s*mins|(\d+)\s*minute|(\d+)\s*minutes", period_str, re.IGNORECASE)
        if tt:
            minutes = tt.group(1)
            period = int(minutes) * 60

        interval = 1
        if math.ceil(period) <= 1440:
            interval = 1
        elif math.ceil(period/5) <= 1440:
            interval = 5
        elif math.ceil(period/10) <= 1440:
            interval = 10
        elif math.ceil(period/30) <= 1440:
            interval = 30
        else:
            interval = math.ceil(period/max_data_points)
            interval = 60*math.ceil(interval/60)

        interval = str(interval)

        now = datetime.datetime.now().timestamp()
        end_time = datetime.datetime.now().isoformat()
        then = now - period
        start_time = datetime.datetime.fromtimestamp(then).isoformat()

        return start_time, end_time, interval

    def aws_ec2_instances(self):
        tmpReq = {}
        tmpReq['jwt'] = self.jwt
        tmpReq['user'] = self.user
        resp = requests.post(self.cmd_exec_url + 'getEc2Instances', json=tmpReq)
        print("Received this response: ", json.dumps(resp.json(), indent=4))
        sys.stdout.flush()
        return resp.json()


    def aws_cw_mem(self, instance_id, period_str):
        start_time, end_time, interval = self.aws_get_time_points_period(period_str)

        cmd1 = 'aws ec2 describe-instances --instance-ids ' + instance_id
        det = self.exe(None,cmd1)
        details = json.loads(det)
        image_id = details["Reservations"][0]["Instances"][0]["ImageId"]
        instance_type = details["Reservations"][0]["Instances"][0]["InstanceType"]

        cmd = 'aws cloudwatch get-metric-statistics --metric-name mem_used_percent'
        cmd += ' --start-time ' + start_time
        cmd += ' --end-time ' + end_time
        cmd += ' --period ' + interval
        cmd += ' --namespace CWAgent --statistics Average --dimensions'
        cmd += ' Name=InstanceId,Value=' + instance_id
        cmd += ' Name=ImageId,Value=' + image_id
        cmd += ' Name=InstanceType,Value=' + instance_type

        op = self.exe(None, cmd)

        exception_msg = ""
        try:
            jsn = json.loads(op)
        except Exception as e:
            exception_msg = "Got this exception: \n"
            exception_msg += str(e)
            exception_msg += "\n"
            exception_msg += op
            exception_msg += '\n command: '
            exception_msg += cmd

        trace = {}
        if not exception_msg:
            datapoints = sorted(jsn['Datapoints'], key = lambda i: i['Timestamp'])

            x = [x['Timestamp'] for x in datapoints]
            y = [x['Average'] for x in datapoints]

            trace['type'] = 'scatter'
            trace['mode'] = 'lines'
            trace['name'] = 'Memory util'
            trace['x'] = x
            trace['y'] = y

        _traces = []
        _traces.append(trace)
        _x_label = 'timestamp'
        _y_label = 'Memory % util'
        _graph_title = 'Memory util for instance: ' + str(instance_id)
        return _traces, _x_label, _y_label, _graph_title, exception_msg

    def aws_cw_cpu(self, instance_id, period_str):
        start_time, end_time, interval = self.aws_get_time_points_period(period_str)

        cmd = 'aws cloudwatch get-metric-statistics --metric-name CPUUtilization'
        cmd += ' --start-time ' + start_time
        cmd += ' --end-time ' + end_time
        cmd += ' --period ' + interval
        cmd += ' --namespace AWS/EC2 --statistics Maximum --dimensions Name=InstanceId,Value=' + instance_id

        op = self.exe(None, cmd)
        exception_msg = ""
        _traces = []
        _x_label = 'timestamp'
        _y_label = 'CPU % util'
        _graph_title = 'CPU util for instance: ' + str(instance_id)

        try:
            jsn = json.loads(op)
        except Exception as e:
            exception_msg = "Got this exception: \n"
            exception_msg += str(e)
            exception_msg += "\n"
            exception_msg += op
            exception_msg += '\ncommand: '
            exception_msg += cmd

        trace = {}
        if not exception_msg:
            datapoints = sorted(jsn['Datapoints'], key = lambda i: i['Timestamp'])

            x = [x['Timestamp'] for x in datapoints]
            y = [x['Maximum'] for x in datapoints]
            trace['type'] = 'scatter'
            trace['mode'] = 'lines'
            trace['name'] = 'CPU util'
            trace['x'] = x
            trace['y'] = y
            
            _traces.append(trace)

        return _traces, _x_label, _y_label, _graph_title, exception_msg

    def netbot(self, host, cmd):
        req_body = {}
        req_body['host'] = host
        req_body['cmd'] = cmd
        req_body['user'] = self.user
        req_headers = {"Accept":"application/json", "Content-Type":"application/json"}
        op = self.rest_api('post', 'netbot_dag_url', '', req_headers, req_body, 'netbot_dag_creds')
        return op.text

    def rest_api(self, method, url, endpoint, req_headers, req_body, cred_label):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['method'] = method
        tmpReq['url'] = url
        tmpReq['endpoint'] = endpoint
        tmpReq['req_headers'] = req_headers
        tmpReq['req_body'] = req_body
        tmpReq['cred_label'] = cred_label
        resp = requests.post(self.cmd_exec_url + 'executeApi', json=tmpReq)
        return resp

    def zrsh(self, host, socket, cmd):
        tmp_cmd = f'echo \"{cmd}\" | nc -U {socket}'
        resp = self.exe(host, tmp_cmd)
        return resp

    def get_creds(self, cred_label):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['cred_label'] = cred_label
        resp = requests.post(self.cmd_exec_url + 'getCreds', json=tmpReq)
        return resp.json()

    def exe(self, host, cmd, cred_label=None):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host'] = host
        tmpReq['cmd'] = cmd
        tmpReq['cred_label'] = cred_label
        resp = requests.post(self.cmd_exec_url + 'executeCommand', json=tmpReq)
        if 'msg' in resp.json():
           return resp.json()['msg']
        return ''

    def exeb(self, host, cmd, cred_label=None):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host'] = host
        tmpReq['cmd'] = cmd
        tmpReq['cred_label'] = cred_label
        tmpReq['background'] = True
        resp = requests.post(self.cmd_exec_url + 'executeCommand', json=tmpReq)
        if 'msg' in resp.json():
           return resp.json()['msg']
        return ''

    def exei(self, host, cmd, cred_label=None, timeout=1):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host'] = host
        tmpReq['cmd'] = cmd
        tmpReq['cred_label'] = cred_label
        tmpReq['timeout'] = timeout
        resp = requests.post(self.cmd_exec_url + 'executeCommandInteractive', json=tmpReq)
        if 'msg' in resp.json():
           return resp.json()['msg']
        return ''


    def exel(self, host_list, cmd, cred_label=None):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host_list'] = host_list
        tmpReq['cmd'] = cmd
        tmpReq['cred_label'] = cred_label
        resp = requests.post(self.cmd_exec_url + 'executeCommandHostList', json=tmpReq)
        return resp.json()

    def exeg(self, group, cmd, cred_label=None):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['group'] = group
        tmpReq['cmd'] = cmd
        tmpReq['cred_label'] = cred_label
        resp = requests.post(self.cmd_exec_url + 'executeCommandHostGroup', json=tmpReq)
        return resp.json()

    def get_ip_addr(self, host):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host'] = host
        resp = requests.post(self.cmd_exec_url + 'getIpAddr', json=tmpReq)
        return resp.json()

    def is_up(self, host):
        tmpReq = {}
        tmpReq['user'] = self.user
        tmpReq['jwt'] = self.jwt
        tmpReq['host'] = host
        resp = requests.post(self.cmd_exec_url + 'isUp', json=tmpReq)
        return resp.json()
