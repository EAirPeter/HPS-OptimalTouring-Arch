#include <algorithm>
#include <cctype>
#include <iostream>

using namespace std;

int nSite, nDay;

// This function shows how to read the data from stdin using the specified
// format, but it does not save any useful information other than the number
// of sites and the number of days. The data should be saved are marked
// between vvvvvv and ^^^^^^.
void ReadAll() {
  nSite = 0;
  nDay = 0;
  // First part
  {
    // Ignore the line with column names of the first part
    // site avenue street desiredtime value
    while (cin && !isdigit(cin.peek()))
      cin.ignore(1);
    // vvvvvv You may want to save these data
    int site, avenue, street, desiredTime;
    double value;
    while (cin >> site >> avenue >> street >> desiredTime >> value) {
    // ^^^^^^
      nSite = max(nSite, site);
    }
  }
  // Second part
  {
    // Ignore the line with column names of the second part
    // site day beginhour endhour
    cin.clear();
    while (cin && !isdigit(cin.peek()))
      cin.ignore(1);
    // vvvvvv You may want to save these data
    int site, day, beginHour, endHour;
    while (cin >> site >> day >> beginHour >> endHour) {
    // ^^^^^^
      nDay = max(nDay, day);
    }
  }
}

// Also, you may want to modify the following function. It does nothing but
// print #day lines, each of which contains #site numbers: 1 2 3 ... #site.
int main() {
  ReadAll();
  for (int day = 1; day <= nDay; ++day) {
    for (int site = 1; site <= nSite; ++site) {
      if (site > 1)
        cout << ' ';
      cout << site;
    }
    cout << endl;
  }
  return 0;
}
