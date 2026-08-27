package com.aflfuzzer.spring.model;

public class TargetResponse {
    private int statusCode;
    private String body;
    private String error;
    private boolean interesting;
    private boolean crash;

    public int getStatusCode() { return statusCode; }
    public void setStatusCode(int statusCode) { this.statusCode = statusCode; }
    public String getBody() { return body; }
    public void setBody(String body) { this.body = body; }
    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
    public boolean isInteresting() { return interesting; }
    public void setInteresting(boolean interesting) { this.interesting = interesting; }
    public boolean isCrash() { return crash; }
    public void setCrash(boolean crash) { this.crash = crash; }
}
