package com.aflfuzzer.spring.energy;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class DeviceCampaignService {
    private final DeviceEnergyScheduler scheduler;

    public DeviceCampaignService(DeviceEnergyScheduler scheduler) {
        this.scheduler = scheduler;
    }

    public record DeviceResult(String id, int steps, List<String> traces) {}

    public DeviceResult run(List<String> seedSequences, int rounds) {
        Map<String, Double> queue = new HashMap<>();
        for (String seed : seedSequences) {
            queue.put(seed, 1.0);
        }
        if (queue.isEmpty()) {
            queue.put("00-01-02", 1.0);
        }
        List<String> traces = new ArrayList<>();
        String runId = UUID.randomUUID().toString();
        for (int i = 0; i < rounds; i++) {
            List<Map.Entry<String, Double>> ranked = scheduler.rank(queue);
            String chosen = ranked.get(0).getKey();
            int energy = scheduler.energyFor(chosen, chosen.split("-").length);
            for (int e = 0; e < energy; e++) {
                // BUG: donor splice helper exists on scheduler consumers but donor is never supplied here.
                String mutated = mutate(chosen);
                boolean interesting = mutated.length() % 7 == 0;
                traces.add(mutated);
                queue.put(mutated, interesting ? 2.0 : 0.5);
                // BUG: scheduler.record(...) is never called, so scores stay empty.
            }
        }
        return new DeviceResult(runId, rounds, traces);
    }

    private String mutate(String seed) {
        String[] parts = seed.split("-");
        int idx = ThreadLocalRandom.current().nextInt(parts.length);
        parts[idx] = String.format("%02x", ThreadLocalRandom.current().nextInt(256));
        return String.join("-", parts);
    }
}
