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
import os
import psutil
import shutil
import subprocess
import sys
import traceback

def clean_output():
  if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)
  if os.path.exists(out_dir):
    raise RuntimeError('Failed to remove output files')

def validate_input(fname):
  if not os.path.isfile(fname):
    raise RuntimeError('Not a file: {}'.format(fname))

  state = 0
  n_site = 0
  n_day = 0
  sites = set()
  locations = set()
  sitedays = set()

  with open(fname, 'r', encoding='utf8') as f:
    for lnum, line in enumerate(f, start=1):
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

def prepare_inputs(dname):
  print('Looking for test cases...')
  inputs = []
  for name in os.listdir(dname):
    fname = os.path.join(dname, name)
    try:
      validate_input(fname)
      inputs.append((name, fname))
      print('Added input: {}'.format(name))
    except:
      print('Failed to add input: {}'.format(name))
      traceback.print_exc()
  print('There are {} test cases in total'.format(len(inputs)))
  return inputs

def validate_solver(dname):
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

def prepare_solvers(dname):
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

def subexec(cmd, cwd, stdin=None, stderr=subprocess.PIPE, timeout=None):
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

def do_compile(name, dname, fname_compile):
  succ, out, _ = subexec(['./compile'], dname, stderr=subprocess.STDOUT, \
      timeout=compile_timeout_sec)
  if out:
    fname_log = os.path.join(os.path.join(out_dir, name), 'compile.log')
    os.makedirs(os.path.dirname(fname_log), exist_ok=True)
    with open(fname_log, 'w', encoding='utf8') as f:
      f.write(out.decode('utf8'))
  if not succ:
    raise RuntimeError('Failed to compile')

def do_run(name, dname, fname_run, iname, stdin):
  succ, out, err = subexec(['./run'], dname, stdin, timeout=run_timeout_sec)
  res_dir = os.path.join(os.path.join(out_dir, name), iname)
  os.makedirs(res_dir, exist_ok=True)
  if out:
    fname_out = os.path.join(res_dir, 'run.out')
    with open(fname_out, 'w', encoding='utf8') as f:
      f.write(out.decode('utf8'))
  if err:
    fname_log = os.path.join(res_dir, 'run.log')
    with open(fname_log, 'w', encoding='utf8') as f:
      f.write(err.decode('utf8'))
  if not succ:
    raise RuntimeError('Runtime error')

def run(inputs, solvers):
  print('Compiling all solvers...', end='')
  skipped_solvers = set()
  for (name, dname) in solvers:
    try:
      fname_compile = os.path.join(dname, 'compile')
      if os.path.exists(fname_compile):
        do_compile(name, dname, fname_compile)
    except:
      skipped_solvers.add(name)
      print('Failed to compile solver {}'.format(name))
      traceback.print_exc()
  print(' Done')

  for (iname, ifname) in inputs:
    print('Running solvers for test: {}'.format(iname))
    try:
      with open(ifname, 'r', encoding='utf8') as f:
        stdin = f.read().encode('utf8')
    except:
      print('Failed to read input: {}'.format(iname))
      traceback.print_exc()

    for (name, dname) in solvers:
      if name in skipped_solvers:
        print('Skipped solver {} for test: {}'.format(name, iname))
        continue
      try:
        fname_run = os.path.join(dname, 'run')
        do_run(name, dname, fname_run, iname, stdin)
      except:
        print('Failed to run solver {} for test: {}'.format(name, iname))
        traceback.print_exc()

  print('All done')

def run_all():
  inputs = prepare_inputs(input_dir)
  solvers = prepare_solvers(solver_dir)

  run(inputs, solvers)

if __name__ == '__main__':
  opts, args = getopt.getopt(sys.argv[1:], "", ["clean"])
  is_clean = False
  for opt in opts:
    if opt[0] == "--clean":
      is_clean = True
  if is_clean:
    clean_output()
  else:
    run_all()
