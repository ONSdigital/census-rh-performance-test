package uk.gov.ons.ctp.test.perf;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import org.apache.http.Header;
import org.apache.http.HttpResponse;
import org.apache.http.NameValuePair;
import org.apache.http.ParseException;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.entity.UrlEncodedFormEntity;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.client.protocol.HttpClientContext;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.LaxRedirectStrategy;
import org.apache.http.message.BasicNameValuePair;
import org.apache.http.util.EntityUtils;

public class LoadThread implements Runnable {

  //private int threadNumber;
  private HttpClient client;
  AtomicLong requestCounter;
  private ArrayList<UACData> uacs;
  private int firstUacEntry;
  private int lastUacEntry;
  
  private HttpClientContext context;
  
  public LoadThread(int threadNumber, HttpClient client, AtomicLong requestCounter, ArrayList<UACData> uacs, int firstUacEntry, int lastUacEntry) {
    //this.threadNumber = threadNumber;
    this.client = HttpClientBuilder.create()
        .setRedirectStrategy(new LaxRedirectStrategy()).build();
    this.requestCounter = requestCounter;
    this.uacs = uacs;
    this.firstUacEntry = firstUacEntry;
    this.lastUacEntry = lastUacEntry;
    
    this.context = HttpClientContext.create();
  }
  
  @Override
  public void run() {
    while (true) {
      for (int i=firstUacEntry; i<=lastUacEntry; i++) {
        try {
          doGet(client);
          UACData uac = uacs.get(i);
          postUAC(client, uac.getUAC(), uac.getAddressLine1(), uac.getPostcode());
          launchSurvey(client);
        } catch (IOException e) {
          e.printStackTrace();
          System.out.println("Unexpected failure");
          System.exit(1);
        }
      }
    }
  }
  
  
  private void doGet(HttpClient client) throws ClientProtocolException, IOException {
    long startTime = System.currentTimeMillis();
    HttpResponse response = client.execute(new HttpGet("http://performance-rh.int.census-gcp.onsdigital.uk/en/start/"), context);
    long requestTime = System.currentTimeMillis() - startTime;
    requestCounter.incrementAndGet();
    int statusCode = response.getStatusLine().getStatusCode();
    String bodyAsString = EntityUtils.toString(response.getEntity());

    if (statusCode != 200) {
      String reason = "Expected 200 but got: " + statusCode;
      reportFailure("GET_start", requestTime, response, reason, bodyAsString);
    } 
  }
  
  
  private void postUAC(HttpClient client, String uac, String expectedAddress, String expectedPostcode) throws ClientProtocolException, IOException {
    expectedAddress = expectedAddress.replace("'", "&#39;");
    
    HttpPost httpPost = new HttpPost("https://performance-rh.int.census-gcp.onsdigital.uk/en/start/");
    
    List<NameValuePair> params = new ArrayList<NameValuePair>();
    params.add(new BasicNameValuePair("uac", uac));
    httpPost.setEntity(new UrlEncodedFormEntity(params));

    long startTime = System.currentTimeMillis();
    HttpResponse response = client.execute(httpPost, context);
    long requestTime = System.currentTimeMillis() - startTime;
    requestCounter.incrementAndGet();
    int statusCode = response.getStatusLine().getStatusCode();
    String bodyAsString = EntityUtils.toString(response.getEntity());

    if (statusCode != 200) {
      String reason = "Expected 200 but got: " + statusCode;
      reportFailure("POST_Uac", requestTime, response, reason, bodyAsString);
    }
    
    if (!bodyAsString.contains(expectedAddress)) {
      String reason = "Response doesn't contain address '" + expectedAddress + "'";
      reportFailure("POST_Uac", requestTime, response, reason, bodyAsString);
    }
    if (!bodyAsString.contains(expectedPostcode)) {
      String reason = "Response doesn't contain postcode '" + expectedPostcode + "'";
      reportFailure("POST_Uac", requestTime, response, reason, bodyAsString);
    }
  }
  

  private void launchSurvey(HttpClient client) throws ParseException, IOException {
    HttpPost httpPost = new HttpPost("https://performance-rh.int.census-gcp.onsdigital.uk/en/start/confirm-address/");
    
    List<NameValuePair> params = new ArrayList<NameValuePair>();
    params.add(new BasicNameValuePair("address-check-answer", "Yes"));
    httpPost.setEntity(new UrlEncodedFormEntity(params));
    
    long startTime = System.currentTimeMillis();
    try {
      HttpResponse response = client.execute(httpPost, context);
      long requestTime = System.currentTimeMillis() - startTime;
      requestCounter.incrementAndGet();
      String bodyAsString = EntityUtils.toString(response.getEntity());
      reportFailure("Launch", requestTime, response, "Didn't get redirect error", bodyAsString);
      throw new IllegalStateException("Not redirected to launch page");
    } catch (Exception e) {
      long requestTime = System.currentTimeMillis() - startTime;
      if (!e.getCause().getMessage().contains("Redirect URI does not specify a valid host name:")) {
        e.printStackTrace();
        reportFailure("LaunchSurvey", requestTime, null, e.getMessage(), e.getCause().getMessage());
      }
    }
  }


  private void reportFailure(String method, long requestTime, HttpResponse response, String reason, String bodyAsString) throws ParseException, IOException {
    System.out.println(bodyAsString);
    System.out.println("Failed for " + method + " due to: " + reason);
    System.out.println("Request time: " + requestTime);
    
    if (response != null) {
      System.out.println("Headers:");
      for (Header h : response.getAllHeaders()) {
        System.out.println("  " + h.getName() + " = " + h.getValue());
      }
    }
    
    System.exit(1);
  }
}