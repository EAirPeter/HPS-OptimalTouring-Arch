import java.util.Scanner;

public class Solver {

  static int nSite, nDay;

  // This function shows how to read the data from stdin using the specified
  // format, but it does not save any useful information other than the number
  // of sites and the number of days. The data should be saved are marked
  // between vvvvvv and ^^^^^^.
  static void readAll() {
    try (Scanner in = new Scanner(System.in)) {
      nSite = 0;
      nDay = 0;

      // Ignore the line with column names of the first part
      // site avenue street desiredtime value
      in.skip("\\D*");
      while (in.hasNextInt()) {
        // vvvvvv You may want to save these data
        int site = in.nextInt();
        int avenue = in.nextInt();
        int street = in.nextInt();
        int desiredTime = in.nextInt();
        double value = in.nextDouble();
        // ^^^^^^
        nSite = Math.max(nSite, site);
      }
      // Ignore the line with column names of the second part
      // site day beginhour endhour
      in.skip("\\D*");
      while (in.hasNextInt()) {
        // vvvvvv You may want to save these data
        int site = in.nextInt();
        int day = in.nextInt();
        int beginHour = in.nextInt();
        int endHour = in.nextInt();
        // ^^^^^^
        nDay = Math.max(nDay, day);
      }
    }
  }

  // Also, you may want to modify the following function. It does nothing but
  // print #day lines, each of which contains #site numbers: 1 2 3 ... #site.
  public static void main(String[] args) {
    readAll();
    for (int day = 1; day <= nDay; ++day) {
      for (int site = 1; site <= nSite; ++site) {
        if (site > 1)
          System.out.print(' ');
        System.out.print(site);
      }
      System.out.println();
    }
  }
}
