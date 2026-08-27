package com.aflfuzzer.spring.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.ArrayList;
import java.util.List;

public class CampaignRequest {
    @Min(1) @Max(10_000)
    private int iterations = 50;
    private List<SeedPayload> seeds = new ArrayList<>();
    private String resumeFile;

    public int getIterations() { return iterations; }
    public void setIterations(int iterations) { this.iterations = iterations; }
    public List<SeedPayload> getSeeds() { return seeds; }
    public void setSeeds(List<SeedPayload> seeds) { this.seeds = seeds; }
    public String getResumeFile() { return resumeFile; }
    public void setResumeFile(String resumeFile) { this.resumeFile = resumeFile; }
}
