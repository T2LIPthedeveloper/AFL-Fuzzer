package com.aflfuzzer.spring.campaign;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

@Component
public class CrashHotIntensity {
    private final Map<String, Integer> crashCounts = new ConcurrentHashMap<>();

    public void noteCrash(String method, String path) {
        crashCounts.merge(method + ":" + path, 1, Integer::sum);
    }

    public int mutationCount(String method, String path, int min, int max) {
        boolean hot = crashCounts.getOrDefault(method + ":" + path, 0) > 0;
        double havocBias = hot ? 0.45 : 0.30;
        if (ThreadLocalRandom.current().nextDouble() < (1.0 - havocBias)) {
            return ThreadLocalRandom.current().nextInt(min, Math.max(min + 1, 4));
        }
        return ThreadLocalRandom.current().nextInt(4, Math.max(5, max + 3));
    }
}
