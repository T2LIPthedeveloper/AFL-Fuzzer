package com.aflfuzzer.spring.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public class MutationRequest {
    @NotNull
    private SeedPayload seed;
    @Min(1) @Max(32)
    private int count = 1;

    public SeedPayload getSeed() { return seed; }
    public void setSeed(SeedPayload seed) { this.seed = seed; }
    public int getCount() { return count; }
    public void setCount(int count) { this.count = count; }
}
