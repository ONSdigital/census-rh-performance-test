package uk.gov.ons.ctp.test.perf;

public class UACData {
  
  private String UAC;
  private String addressLine1;
  private String postcode;

  UACData(String UAC, String addressLine1, String postcode) {
    this.UAC = UAC;
    this.addressLine1 = addressLine1;
    this.postcode = postcode;
  }
  
  String getUAC() { 
    return UAC;
  }
  
  String getAddressLine1() { 
    return addressLine1;
  }

  String getPostcode() { 
    return postcode;
  }
}
