package uk.gov.ons.ctp.test.perf;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import org.apache.http.client.HttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.LaxRedirectStrategy;

/**
 * This package holds some crude code which performs Http requests to exercise RH.
 * 
 * It basically reproduces the main thread in the Locust tests:
 *  - reads a UAC event data file
 *  - Gets the start page
 *  - Posts a UAC
 *  - Posts address confirmation to launch the survey
 *  
 * The load on the server is controlled by adjusting the NUM_THREADS constant.
 */

public class LoadRH {

  private static final int NUM_THREADS = 2;

  public static void main(String[] args) throws IOException {
    HttpClient client = HttpClientBuilder.create()
        .setRedirectStrategy(new LaxRedirectStrategy()).build();

    ArrayList<UACData> uacs = readEventData();
    
    AtomicLong requestCounter = new AtomicLong();
    
    for (int i = 0; i < NUM_THREADS; i++) {
      double uacsPerThread = ((double) uacs.size()) / (double) NUM_THREADS;
      int firstUacEntry = (int) ((double) i * uacsPerThread);
      int lastUacEntry = (int) ((double) (i+1) * uacsPerThread) -1;

      System.out.println(i + "  " + firstUacEntry + "..." + lastUacEntry);
      
      Runnable load = new LoadThread(i, client, requestCounter, uacs, firstUacEntry, lastUacEntry);
      Thread thread = new Thread(load);
      thread.setName(String.valueOf(i));
      thread.start();
    }

    long previousRequestTotal = 0;
    while (true) {
      try {
        Thread.sleep(1000);
      } catch (InterruptedException e) {
        e.printStackTrace();
      }
      long latestRequestTotal = requestCounter.get();
      long requestsMade = latestRequestTotal - previousRequestTotal;
      previousRequestTotal = latestRequestTotal;
      System.out.println("Progress update: " + latestRequestTotal + " +" + requestsMade);
    }
  }
  
  static ArrayList<UACData> readEventData() throws IOException {
    ArrayList<UACData> uacs= new ArrayList<>();
    
    List<String> allLines = Files.readAllLines(Paths.get("/Users/peterbochel/source/testing/census-rh-performance-test/test_data/event_data.txt"));
    boolean doneHeaderLine = false;
    for (String line : allLines) {
      if (!doneHeaderLine) { 
        doneHeaderLine = true;
        continue;
      }
      
      String[] parts = line.split(",");
      String uac = parts[0];
      String addressLine1 = parts[1];
      String postcode = parts[2];
      
      UACData uacData = new UACData(uac, addressLine1, postcode);
      uacs.add(uacData);
    }
    
    return uacs;
  }
}