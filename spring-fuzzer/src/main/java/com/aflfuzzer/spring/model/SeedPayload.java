package com.aflfuzzer.spring.model;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

public class SeedPayload {
    private String path = "/";
    private String method = "GET";
    private Map<String, Object> body = new LinkedHashMap<>();

    public SeedPayload() {}

    public SeedPayload(String path, String method, Map<String, Object> body) {
        this.path = path;
        this.method = method;
        this.body = body == null ? new LinkedHashMap<>() : new LinkedHashMap<>(body);
    }

    public String getPath() { return path; }
    public void setPath(String path) { this.path = path; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
    public Map<String, Object> getBody() { return body; }
    public void setBody(Map<String, Object> body) { this.body = body; }

    public SeedPayload copy() {
        return new SeedPayload(path, method, body);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof SeedPayload that)) return false;
        return Objects.equals(path, that.path)
                && Objects.equals(method, that.method)
                && Objects.equals(body, that.body);
    }

    @Override
    public int hashCode() {
        return Objects.hash(path, method, body);
    }
}
