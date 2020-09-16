#!/usr/bin/python3
# vim:ts=2:sts=2:sw=2

out_dir = './out'
input_dir = './inputs'
solver_dir = './solvers'

max_n_site = 200
max_n_day = 10

compile_timeout_sec = 20
run_timeout_sec = 2

import getopt
import io
import os
import psutil
import shutil
import subprocess
import sys
import traceback

from typing import List, Optional, Tuple

class OptimalTour:
  def __init__(self, n_site: int, n_day: int, stdin: str):
    self.stdin = stdin.encode('utf8')
    self.x = [0] * n_site
    self.y = [0] * n_site
    self.val = [0.] * n_site
    self.time = [0] * n_site
    self.beghr = [[0] * n_site] * n_day
    self.endhr = [[0] * n_site] * n_day
    self.n_site = n_site
    self.n_day = n_day

    state = 0
    for line in stdin.split('\n'):
      ln = line.split()
      if not ln:
        continue
      if state == 0:
        # site avenue street desiredtime value
        state = 1
      elif state == 1:
        if ln[0][0].isdigit():
          site = int(ln[0]) - 1
          self.x[site] = int(ln[1])
          self.y[site] = int(ln[2])
          self.time[site] = int(ln[3])
          self.val[site] = float(ln[4])
        else:
          # site day beginhour endhour
          state = 2
      elif state == 2:
        site = int(ln[0]) - 1
        day = int(ln[1]) - 1
        self.beghr[day][site] = int(ln[2])
        self.endhr[day][site] = int(ln[3])

  def parse_output(self, out: str) -> float:
    lines = out.split('\n')
    while lines and not lines[-1]:
      lines.pop()
    if len(lines) != self.n_day:
      raise RuntimeError('Expected {} lines in your output but there are {} lines' \
        .format(self.n_day, len(lines)))

    tot_val = 0.
    visited_sites = set()
    for day, line in enumerate(lines):
      ln = line.split()
      now = 0
      x = 0
      y = 0
      is_first_site_of_day = True
      for site_s in ln:
        ssite = int(site_s)
        site = ssite - 1
        if not 0 <= site < self.n_site:
          raise RuntimeError('Site id {} should be between 1 and {}'.format(ssite, self.n_site))
        if site in visited_sites:
          raise RuntimeError('You have already visited site {}'.format(ssite))
        visited_sites.add(site)
        if not is_first_site_of_day:
          now += abs(x - self.x[site]) + abs(y - self.y[site])
        else:
          is_first_site_of_day = False
        x = self.x[site]
        y = self.y[site]
        now = max(now, self.beghr[day][site] * 60)
        if now + self.time[site] > self.endhr[day][site] * 60:
          raise RuntimeError('Insufficient time to visit site {}'.format(ssite))
        tot_val += self.val[site]

    return tot_val


def clean_output():
  if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)
  if os.path.exists(out_dir):
    raise RuntimeError('Failed to remove output files')

def parse_input(fname: str) -> OptimalTour:
  if not os.path.isfile(fname):
    raise RuntimeError('Not a file: {}'.format(fname))

  with open(fname, 'r', encoding='utf8') as f:
    stdin = f.read()

  state = 0
  n_site = 0
  n_day = 0
  sites = set()
  locations = set()
  sitedays = set()

  for lnum, line in enumerate(stdin.split('\n'), start=1):
    ln = line.split()
    if not ln:
      continue
    if state == 0:
      if ln != ['site', 'avenue', 'street', 'desiredtime', 'value']:
        raise RuntimeError('Invalid line {}'.format(lnum))
      state = 1
    elif state == 1:
      if ln[0][0].isdigit():
        if len(ln) != 5:
          raise RuntimeError('Invalid line {}'.format(lnum))
        site = int(ln[0])
        avenue = int(ln[1])
        street = int(ln[2])
        desired_time = int(ln[3])
        value = float(ln[4])
        n_site = max(n_site, site)
        if n_site > max_n_site:
          raise RuntimeError('#site is too large ({})'.format(n_site))
        if not 1 <= site:
          raise RuntimeError('Invalid site id at line {}'.format(lnum))
        if not 1 <= desired_time <= 1440:
          raise RuntimeError('Invalid desired time at line {}'.format(lnum))
        if not 0 < value:
          raise RuntimeError('Invalid value at line {}'.format(lnum))
        if site in sites:
          raise RuntimeError('Duplicated site id at line {}'.format(lnum))
        sites.add(site)
        if (avenue, street) in locations:
          raise RuntimeError('Duplicated site location at line {}'.format(lnum))
        locations.add((avenue, street))
      else:
        if ln != ['site', 'day', 'beginhour', 'endhour']:
          raise RuntimeError('Invalid line {}'.format(lnum))
        if len(sites) != n_site:
          raise RuntimeError('Mismatched #site and the first part of the input')
        state = 2
    elif state == 2:
      if len(ln) != 4:
        raise RuntimeError('Invalid line {}'.format(lnum))
      site = int(ln[0])
      day = int(ln[1])
      begin_hour = int(ln[2])
      end_hour = int(ln[3])
      n_day = max(n_day, day)
      if n_day > max_n_day:
        raise RuntimeError('#day is too large ({})'.format(n_day))
      if not 1 <= site <= n_site:
        raise RuntimeError('Invalid site id at line {}'.format(lnum))
      if not 0 <= begin_hour <= end_hour <= 23:
        raise RuntimeError('Invalid opening hours at line {}'.format(lnum))
      if (site, day) in sitedays:
        raise RuntimeError('Duplicated (site,day) pair at line {}'.format(lnum))
      sitedays.add((site, day))

  if state != 2:
    raise RuntimeError('Unexpected EOF at this point')

  if n_day * n_site != len(sitedays):
    raise RuntimeError('Mismatched #day, #site and the second part of the input')

  for site in range(1, n_site + 1):
    if site not in sites:
      raise RuntimeError('Missing site id {}'.format(site))
    for day in range(1, n_day + 1):
      if (site, day) not in sitedays:
        raise RuntimeError('Missing day {} for site {}'.format(day, site))

  return OptimalTour(n_site, n_day, stdin)

def prepare_inputs(dname: str):
  print('Looking for test cases...')
  inputs = []
  for name in os.listdir(dname):
    fname = os.path.join(dname, name)
    try:
      otp = parse_input(fname)
      inputs.append((name, otp))
      print('Added input: {}'.format(name))
    except:
      print('Failed to add input: {}'.format(name))
      traceback.print_exc()
  print('There are {} test cases in total'.format(len(inputs)))
  return inputs

def validate_solver(dname: str):
  if not os.path.isdir(dname):
    raise RuntimeError('Not a directory: {}'.format(dname))

  fname_compile = os.path.join(dname, 'compile')
  fname_run = os.path.join(dname, 'run')

  if os.path.exists(fname_compile):
    if not os.access(fname_run, os.X_OK):
      raise RuntimeError('{} is not executable'.format(fname_compile))

  if os.path.exists(fname_run):
    if not os.access(fname_run, os.X_OK):
      raise RuntimeError('{} is not executable'.format(fname_run))
  else:
    raise RuntimeError('No \'run\' file')

def prepare_solvers(dname: str):
  print('Looking for solvers...')
  solvers = []
  for name in os.listdir(dname):
    fname = os.path.join(dname, name)
    try:
      validate_solver(fname)
      solvers.append((name, fname))
      print('Added solver: {}'.format(name))
    except:
      print('Failed to add solver: {}'.format(name))
      traceback.print_exc()
  print('There are {} solvers in total'.format(len(solvers)))
  return solvers

def subexec(cmd: List[str], cwd: str, stdin: str = None, stderr: int = subprocess.PIPE, \
    timeout: Optional[float] = None):
  with subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, \
      stdout=subprocess.PIPE, stderr=stderr) as proc:
    try:
      out, err = proc.communicate(stdin, timeout=timeout)
      proc.stdin.close()
      return proc.returncode == 0, out, err
    except:
      raise
    finally:
      try:
        psproc = psutil.Process(proc.pid)
        children = psproc.children(True)
        for child in children:
          child.kill()
        psutil.wait_procs(children)
      except:
        pass

def do_compile(name: str, dname: str):
  succ, out, _ = subexec(['./compile'], dname, stderr=subprocess.STDOUT, \
      timeout=compile_timeout_sec)
  if out:
    out = out.decode('utf8')
    fname_log = os.path.join(os.path.join(out_dir, name), 'compile.log')
    os.makedirs(os.path.dirname(fname_log), exist_ok=True)
    with open(fname_log, 'w', encoding='utf8') as f:
      f.write(out)
  if not succ:
    raise RuntimeError('Failed to compile')

def do_run(name: str, dname: str, iname: str, otp: OptimalTour):
  succ, out, err = subexec(['./run'], dname, otp.stdin, timeout=run_timeout_sec)
  res_dir = os.path.join(os.path.join(out_dir, name), iname)
  os.makedirs(res_dir, exist_ok=True)
  if out:
    out = out.decode('utf8')
    fname_out = os.path.join(res_dir, 'run.out')
    with open(fname_out, 'w', encoding='utf8') as f:
      f.write(out)
  if err:
    err = err.decode('utf8')
    fname_log = os.path.join(res_dir, 'run.log')
    with open(fname_log, 'w', encoding='utf8') as f:
      f.write(err)

  if not succ:
    val = 0.
    comment = 'Runtime error'
  else:
    try:
      val = otp.parse_output(out)
      comment = 'The output looks fine'
    except Exception as exn:
      val = 0.
      comment = str(exn)

  fname_result = os.path.join(res_dir, 'result.out')
  with open(fname_result, 'w', encoding='utf8') as f:
    f.write('{}\n{}\n'.format(val, comment))

  if not succ:
    raise RuntimeError('Runtime error')

def run(inputs: List[Tuple[str, OptimalTour]], solvers: List[Tuple[str, str]]):
  for (name, dname) in solvers:
    try:
      fname_compile = os.path.join(dname, 'compile')
      if os.path.exists(fname_compile):
        print('Compiling solver: {}...'.format(name), end='')
        do_compile(name, dname)
        print(' Done')
      print('Running test cases for solver: {}'.format(name))
      for (iname, otp) in inputs:
        try:
          do_run(name, dname, iname, otp)
        except:
          print('Failed to run solver {} for test: {}'.format(name, iname))
          traceback.print_exc()
    except:
      print('Failed to compile solver: {}'.format(name))
      traceback.print_exc()
  print('All done')

def run_all():
  inputs = prepare_inputs(input_dir)
  solvers = prepare_solvers(solver_dir)

  run(inputs, solvers)

if __name__ == '__main__':
  opts, args = getopt.getopt(sys.argv[1:], '', ['clean'])
  is_clean = False
  for opt in opts:
    if opt[0] == '--clean':
      is_clean = True
  if is_clean:
    clean_output()
  else:
    run_all()
