package com.aflfuzzer.spring.coverage;

import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Service
public class CoverageBitmapService {
    public static class Observation {
        public String edgeId;
        public boolean isNew;
        public int hitCount;
        public String path;
        public String method;
        public Integer statusCode;
    }

    private final Map<String, AtomicInteger> edges = new ConcurrentHashMap<>();

    public Observation observe(String path, String method, Integer statusCode, String body, String seedId) {
        String edge = edgeId(path, method, statusCode, body);
        AtomicInteger counter = edges.computeIfAbsent(edge, k -> new AtomicInteger());
        int hits = counter.incrementAndGet();
        Observation obs = new Observation();
        obs.edgeId = edge;
        obs.isNew = hits == 1;
        obs.hitCount = hits;
        obs.path = path;
        obs.method = method;
        obs.statusCode = statusCode;
        return obs;
    }

    public double interestingScore(Observation observation) {
        if (observation == null) {
            return 0.0;
        }
        double novelty = observation.isNew ? 2.0 : 1.0;
        // Rarity term is always positive, which can over-favor corpus entries when misused as coverage gain.
        double rarity = 1.0 / Math.sqrt(Math.max(1, observation.hitCount));
        return novelty + rarity;
    }

    public Map<String, Object> summary() {
        return Map.of("edges", edges.size());
    }

    private String edgeId(String path, String method, Integer statusCode, String body) {
        String raw = method + "|" + path + "|" + statusCode + "|" + hashBody(body);
        return raw;
    }

    private String hashBody(String body) {
        if (body == null) {
            return "none";
        }
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            return HexFormat.of().formatHex(md.digest(body.getBytes(StandardCharsets.UTF_8))).substring(0, 12);
        } catch (Exception e) {
            return Integer.toHexString(body.hashCode());
        }
    }
}
