#!/usr/bin/python3
# vim:ts=2:sts=2:sw=2

import sys

# This functions shows how to read the data from stdin using the specified
# format, but it does not save any useful information other than the number
# of sites and the number of days. The data should be saved are marked
# between vvvvvv and ^^^^^^.
def read_all():
  state = 0
  n_site = 0
  n_day = 0

  for line in sys.stdin:
    ln = line.split()
    if not ln:
      continue
    if state == 0:
      # Ignore the line with column names of the first part
      # site avenue street desiredtime value
      state = 1
    elif state == 1:
      if ln[0][0].isdigit():
        # vvvvvv You may want to save these data
        site = int(ln[0])
        avenue = int(ln[1])
        street = int(ln[2])
        desired_time = int(ln[3])
        value = float(ln[4])
        # ^^^^^^
        n_site = max(n_site, site)
      else:
        # Ignore the line with column names of the second part
        # site day beginhour endhour
        state = 2
    elif state == 2:
      # vvvvvv You may want to save these data
      site = int(ln[0])
      day = int(ln[1])
      begin_hour = int(ln[2])
      end_hour = int(ln[3])
      # ^^^^^^
      n_day = max(n_day, day)

  return n_site, n_day

# Also, you may want to modify the following function. It does nothing but
# print #day lines, each of which contains #site numbers: 1 2 3 ... #site.
def main():
  n_site, n_day = read_all()
  for day in range(1, n_day + 1):
    sites_to_visit = [site for site in range(1, n_site + 1)]
    print(*sites_to_visit)

if __name__ == '__main__':
  main()
