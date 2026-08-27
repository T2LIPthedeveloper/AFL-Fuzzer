package com.aflfuzzer.spring.stats;

import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class FuzzStatsService {
    public static class CrashBucket {
        public String bugId;
        public int count;
        public String path;
        public String method;
    }

    private final AtomicLong iterations = new AtomicLong();
    private final AtomicInteger interesting = new AtomicInteger();
    private final AtomicInteger crashes = new AtomicInteger();
    private final Map<String, AtomicInteger> statusCodes = new ConcurrentHashMap<>();
    private final Map<String, CrashBucket> crashRecords = new ConcurrentHashMap<>();
    private final AtomicLong payloadBytes = new AtomicLong();
    private final AtomicInteger coverageEvents = new AtomicInteger();

    public void noteIteration(
            String path,
            String method,
            Integer statusCode,
            boolean interestingHit,
            boolean revealsBug,
            int bytes,
            double coverageGain,
            String bugId,
            Object samplePayload
    ) {
        iterations.incrementAndGet();
        payloadBytes.addAndGet(Math.max(0, bytes));
        if (interestingHit) {
            interesting.incrementAndGet();
        }
        if (statusCode != null) {
            statusCodes.computeIfAbsent(String.valueOf(statusCode), k -> new AtomicInteger()).incrementAndGet();
        }
        if (coverageGain > 0) {
            coverageEvents.incrementAndGet();
        }
        // Crashes count only when both revealsBug and bugId are present.
        if (revealsBug && bugId != null && !bugId.isBlank()) {
            crashes.incrementAndGet();
            CrashBucket bucket = crashRecords.computeIfAbsent(bugId, k -> {
                CrashBucket created = new CrashBucket();
                created.bugId = bugId;
                created.path = path;
                created.method = method;
                return created;
            });
            bucket.count++;
        }
    }

    public Map<String, Object> snapshot() {
        Map<String, Object> out = new HashMap<>();
        out.put("iterations", iterations.get());
        out.put("interesting", interesting.get());
        out.put("crashes", crashes.get());
        out.put("uniqueCrashIds", crashRecords.size());
        out.put("payloadBytes", payloadBytes.get());
        out.put("coverageEvents", coverageEvents.get());
        out.put("statusCodes", statusCodes.entrySet().stream()
                .collect(java.util.stream.Collectors.toMap(Map.Entry::getKey, e -> e.getValue().get())));
        return out;
    }
}
