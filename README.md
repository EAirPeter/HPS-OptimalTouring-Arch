HPS: Optimal Touring Architecture
=================================
Architecture by team `alias please='sudo'`

## Usage
1.  Put test cases into the [tests/](./tests/) directory. One file per test case, the format should
    be exactly the same as described
    [here](https://cs.nyu.edu/courses/fall20/CSCI-GA.2965-001/tour.html).
    * Note: the [sample](./tests/sample) test case is an identical copy of the
      [typical file](https://cs.nyu.edu/courses/fall20/CSCI-GA.2965-001/touringtest) on the course
      website.
2.  Put solvers into the [solvers/](./solvers/) directory. One directory per solver, the
    requirements of the directory are:
    * The directory name is the solver name. It should be your team name.
    * It shall contain a `run` file. This file is what will be executed to run tests. It can be
      your program itself, or a running script specifying how to run your program. This file shall
      have its execution bit set.
    * It should contain a `compile` file if your code needs compilation. If this file exists, it
      will be executed before the test driver running your program. This file shall have its
      execution bit set if exists.
3. Run tests: `./OptimalTour.py` or call your python interpreter explicitly.
    * For each solver, the driver will first compile it (if it needs), then run it with all test
      cases. The driver will also verify its output and calculate the score (the total value that
      your program got during the tour).
    * For solver with name `<solver_name>`, there will be a file
      `./out/<solver_name>/summary.txt`, showing the results of this solver with all test cases.
    * For test case with name `<test_name>`, there will be a file
      `./out/<test_name>_summary.txt`, showing the results of all solvers with this test case.
    * There is also a detailed record per test case and solver. For solver `<solver_name>` and test
      case `<test_name>`, a directory `./out/<solver_name>/<test_name>/` will be generated, the
      content of which is described as follows:
      * `compilation_output.txt`: Contains the output from `compile`. This could help you identify
        problems if `compile` failed. This file will not exist if `compile` does not write
        anything to `stdout` and `stderr`.
      * `stdout.txt`: Contains the content of `stdout` of `run`. This is what will be verified
        against the corresponding input. This file will not exist if `run` does not write anything
        to `stdout`.
      * `stderr.txt`: Contains the content of `stderr` of `run`. You can use this to debug your
        program (if you want). This file will not exist if `run` does not write anything to
        `stderr`.
      * `result.txt`: The first line contains a number, your score on this test case. If the driver
        fails to verify your output, there will be a second line, showing the reason why your
        output is illegal.

## Notes on Running the Driver `OptimalTour.py`
* Python 3: I am not sure what the lowest supported version is. The driver works fine over
  Python 3.8.5 .
* Python 3 Package: `psutil`
* Command line:
  * Without option: Run all solvers with all test cases.
  * With `--clean`: Remove the output directory.
  * With `--verbose`: Verbose mode.

## Notes on Composing Test Cases
* You can compose your own test case, as long as you follow the format described on the website.

## Notes on Writing Solvers
* About input:
  * Your solver should read input from `stdin`.
  * All tests will be exactly the same format as described on the course website.
* About output:
  * Your solver should write your output to `stdout`.
  * The output should contain exactly `K` lines, where `K` is the number of days in total.
  * The `i`-th line contains zero or more space delimited integers, indicating sites you want to
    visit on day `i`.
  * All integers in your output should be between `1` and `N` inclusive, where `N` is the number of
    sites in total.
  * You can visit a site at most once. That is, your output shall not contain any duplicated
    number.
* There are some sample solvers in the [solvers/](./solvers/) directory. They are only intended to
  show how to process the input in C++/Java/Python. You can use one of them for reference if you
  want.
