package com.aflfuzzer.spring.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "afl")
public class AflProperties {
    private String targetBaseUrl = "http://127.0.0.1:8000";
    private int defaultIterations = 50;
    private int mutationMin = 1;
    private int mutationMax = 3;

    public String getTargetBaseUrl() { return targetBaseUrl; }
    public void setTargetBaseUrl(String targetBaseUrl) { this.targetBaseUrl = targetBaseUrl; }
    public int getDefaultIterations() { return defaultIterations; }
    public void setDefaultIterations(int defaultIterations) { this.defaultIterations = defaultIterations; }
    public int getMutationMin() { return mutationMin; }
    public void setMutationMin(int mutationMin) { this.mutationMin = mutationMin; }
    public int getMutationMax() { return mutationMax; }
    public void setMutationMax(int mutationMax) { this.mutationMax = mutationMax; }
}
