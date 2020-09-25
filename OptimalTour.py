#!/usr/bin/python3
# vim:ts=2:sts=2:sw=2

out_dir = './out'
input_dir = './tests'
solver_dir = './solvers'

max_n_site = 200
max_n_day = 10

compile_timeout_sec = 20
run_timeout_sec = 2

is_verbose = False

import getopt
import io
import os
import psutil
import shutil
import subprocess
import sys
import traceback

from typing import List, Optional, Tuple

def subexec(cmd: List[str], cwd: str, stdin: str = None, stderr: int = subprocess.PIPE, \
    timeout: Optional[float] = None) -> Tuple[int, bytes, bytes]:
  with subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, \
      stdout=subprocess.PIPE, stderr=stderr) as proc:
    try:
      out, err = proc.communicate(stdin, timeout=timeout)
      proc.stdin.close()
      if out:
        out = out.decode('utf8')
      if err:
        err = err.decode('utf8')
      return proc.returncode, out, err
    except:
      raise
    finally:
      try:
        psproc = psutil.Process(proc.pid)
        children = psproc.children(True)
        proc.kill()
        for child in children:
          child.kill()
        psutil.wait_procs(children)
      except:
        pass

def write_table(fname: str, tbl: List[List]):
  n_col = len(tbl[0])
  widths = [0 for i in range(n_col)]
  for i_row in range(len(tbl)):
    row = ['' if col is None else str(col) for col in tbl[i_row]]
    tbl[i_row] = row
    if n_col != len(row):
      raise RuntimeError('Invalid table')
    for col in range(n_col):
      widths[col] = max(widths[col], len(row[col]))

  formats = []
  fmt = ''
  for col in range(n_col):
    if col > 0:
      fmt += ' '
    formats.append(fmt + '{{0[{}]}}'.format(col))
    fmt += '{{0[{}]:<{}}}'.format(col, widths[col])

  with open(fname, 'w', encoding='utf8') as f:
    for row in tbl:
      idx = n_col
      while idx > 0 and len(str(row[idx - 1])) == 0:
        idx -= 1
      if idx > 0:
        f.write(formats[idx - 1].format(row))
      f.write('\n')

class RunResult:
  def __init__(self, solver, test):
    self.solver = solver
    self.test = test
    self.out_run = None
    self.err_run = None
    self.out_result = None
    self.out_summary = None
    self.score = 0.
    self.comment = None

class TestCase:
  def __init__(self, name: str, n_site: int, n_day: int, stdin: str):
    self.name = name
    self.stdin = stdin.encode('utf8')
    self.results = []
    self.out_summary = None
    self.x = [0 for i in range(n_site)]
    self.y = [0 for i in range(n_site)]
    self.val = [0. for i in range(n_site)]
    self.time = [0 for i in range(n_site)]
    self.beghr = [[0 for i in range(n_site)] for j in range(n_day)]
    self.endhr = [[0 for i in range(n_site)] for j in range(n_day)]
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

  def check_output(self, out: str) -> float:
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

  def save_summary(self):
    def key_res(res: RunResult):
      return res.score
    self.results = sorted(self.results, key=key_res, reverse=True)
    self.out_summary = os.path.join(out_dir, self.name + '_summary.txt')
    tbl = [['solver_name', 'score', 'comment']]
    for res in self.results:
      tbl.append([res.solver.name, res.score, res.comment])
    write_table(self.out_summary, tbl)

class Solver:
  def __init__(self, name: str, dname: str):
    self.name = name
    self.dname = dname
    self.out_dir = os.path.join(out_dir, name)
    self.results = []
    self.log_compile = None
    self.compilation_exn = RuntimeError('Not compiled yet')

  def do_compile(self):
    saved_exn = None
    out = None
    try:
      retv, out, _ = subexec(['./compile'], self.dname, stderr=subprocess.STDOUT, \
          timeout=compile_timeout_sec)
      if retv != 0:
        raise RuntimeError('./compile shall return 0, but actually returned {}'.format(retv))
    except Exception as exn:
      saved_exn = exn

    os.makedirs(self.out_dir, exist_ok=True)

    if out:
      self.log_compile = os.path.join(self.out_dir, 'compilation_output.txt')
      with open(self.log_compile, 'w', encoding='utf8') as f:
        f.write(out)

    if saved_exn is not None:
      raise saved_exn

  def compile(self):
    try:
      fname_compile = os.path.join(self.dname, 'compile')
      if os.path.exists(fname_compile):
        print('Compiling solver \'{}\'...'.format(self.name))
        self.do_compile()
      self.compilation_exn = None
    except Exception as exn:
      self.compilation_exn = exn
      print('  Failed to compile solver \'{}\': {}'.format(self.name, str(exn)))
      if is_verbose:
        traceback.print_exc()

  def do_run(self, test: TestCase):
    res = RunResult(self, test)
    self.results.append(res)
    test.results.append(res)

    saved_exn = None
    out = None
    err = None
    try:
      if self.compilation_exn is not None:
        raise RuntimeError('Compilation failed: {}'.format(str(self.compilation_exn)))
      retv, out, err = subexec(['./run'], self.dname, test.stdin, timeout=run_timeout_sec)
      if retv != 0:
        raise RuntimeError('./run shall return 0, but actually returned {}'.format(retv))
      if not out:
        raise RuntimeError('Your program did not output anything')
      res.score = test.check_output(out)
      res.comment = None
    except Exception as exn:
      saved_exn = exn

    res_dir = os.path.join(self.out_dir, test.name)
    os.makedirs(res_dir, exist_ok=True)

    if out:
      res.out_run = os.path.join(res_dir, 'stdout.txt')
      with open(res.out_run, 'w', encoding='utf8') as f:
        f.write(out)
    if err:
      res.err_run = os.path.join(res_dir, 'stderr.txt')
      with open(res.err_run, 'w', encoding='utf8') as f:
        f.write(err)

    if saved_exn is not None:
      res.score = 0.
      res.comment = str(saved_exn)

    res.out_result = os.path.join(res_dir, 'result.txt')
    with open(res.out_result, 'w', encoding='utf8') as f:
      if res.comment:
        f.write('{}\n{}\n'.format(res.score, res.comment))
      else:
        f.write('{}\n'.format(res.score))

    if saved_exn is not None:
      raise saved_exn

  def run(self, test: TestCase):
    try:
      if self.compilation_exn is not None:
        print('  Skipped test case \'{}\''.format(test.name))
      else:
        print('  Running on test case \'{}\''.format(test.name))
      self.do_run(test)
    except:
      if is_verbose:
        print('  Failed on test case \'{}\':'.format(test.name))
        traceback.print_exc()

  def save_summary(self):
    self.out_summary = os.path.join(self.out_dir, 'summary.txt')
    tbl = [['test_name', 'score', 'comment']]
    for res in self.results:
      tbl.append([res.test.name, res.score, res.comment])
    write_table(self.out_summary, tbl)

def clean_output():
  if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)
  if os.path.exists(out_dir):
    raise RuntimeError('Failed to remove output files')

def make_test(name: str, fname: str) -> TestCase:
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

  return TestCase(name, n_site, n_day, stdin)

def make_solver(name: str, dname: str):
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

  return Solver(name, dname)

def prepare_tests(dname: str) -> List[TestCase]:
  print('Looking for test cases...')
  tests = []
  for name in os.listdir(dname):
    fname = os.path.join(dname, name)
    try:
      test = make_test(name, fname)
      tests.append(test)
      print('  Added test case \'{}\''.format(name))
    except Exception as exn:
      print('  Failed to add test case \'{}\': {}'.format(name, str(exn)))
      if is_verbose:
        traceback.print_exc()
  print('There are {} test cases in total'.format(len(tests)))
  return tests

def prepare_solvers(dname: str) -> List[Solver]:
  print('Looking for solvers...')
  solvers = []
  for name in os.listdir(dname):
    subdname = os.path.join(dname, name)
    try:
      solver = make_solver(name, subdname)
      solvers.append(solver)
      print('  Added solver: {}'.format(name))
    except:
      print('  Failed to add solver: {}'.format(name))
      traceback.print_exc()
  print('There are {} solvers in total'.format(len(solvers)))
  return solvers

def run(tests: List[Tuple[str, TestCase]], solvers: List[Tuple[str, str]]):
  for solver in solvers:
    solver.compile()
    print('Running test cases for solver \'{}\''.format(solver.name))
    for test in tests:
      solver.run(test)
  print('Writing summaries...')
  for solver in solvers:
    solver.save_summary()
  for test in tests:
    test.save_summary()
  print('All done')

def run_all():
  tests = prepare_tests(input_dir)
  solvers = prepare_solvers(solver_dir)

  run(tests, solvers)

if __name__ == '__main__':
  opts, args = getopt.getopt(sys.argv[1:], '', ['clean', 'verbose'])
  is_clean = False
  for opt in opts:
    if opt[0] == '--clean':
      is_clean = True
    if opt[0] == '--verbose':
      is_verbose = True
  if is_clean:
    clean_output()
  else:
    run_all()
