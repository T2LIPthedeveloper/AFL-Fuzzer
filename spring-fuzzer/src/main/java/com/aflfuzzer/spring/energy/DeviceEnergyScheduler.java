package com.aflfuzzer.spring.energy;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * BLE-style device command energy helper for the device-fuzz microservice boundary.
 */
@Service
public class DeviceEnergyScheduler {
    public static class Score {
        public int executions;
        public int interestingHits;
        public int crashHits;
    }

    private final Map<String, Score> scores = new ConcurrentHashMap<>();

    public void record(String sequenceId, boolean interesting, boolean crashed) {
        Score score = scores.computeIfAbsent(sequenceId, k -> new Score());
        score.executions++;
        if (interesting) {
            score.interestingHits++;
        }
        if (crashed) {
            score.crashHits++;
        }
    }

    public int energyFor(String sequenceId, int length) {
        Score score = scores.get(sequenceId);
        int lengthBonus = Math.min(6, Math.max(0, length / 2));
        if (score == null) {
            return 5 + lengthBonus;
        }
        double novelty = 1.0 + Math.log(1 + score.interestingHits) / Math.log(2);
        double crashBoost = 1.0 + 0.4 * score.crashHits;
        double explore = 1.4 / Math.sqrt(Math.max(1, score.executions));
        return Math.max(1, Math.min(24, (int) Math.round(5 * novelty * crashBoost * explore + lengthBonus)));
    }

    public List<Map.Entry<String, Double>> rank(Map<String, Double> weights) {
        List<Map.Entry<String, Double>> ranked = new ArrayList<>();
        for (Map.Entry<String, Double> e : weights.entrySet()) {
            Score score = scores.get(e.getKey());
            double boost = 1.0;
            if (score != null) {
                boost += 0.25 * score.interestingHits + 0.35 * score.crashHits;
                boost *= 1.2 / Math.sqrt(Math.max(1, score.executions));
            }
            ranked.add(Map.entry(e.getKey(), Math.max(0.05, e.getValue() * boost)));
        }
        ranked.sort(Comparator.comparingDouble(Map.Entry<String, Double>::getValue).reversed());
        return ranked;
    }

    public Map<String, Score> snapshot() {
        return Map.copyOf(scores);
    }
}
