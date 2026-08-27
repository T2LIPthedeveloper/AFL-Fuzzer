package com.aflfuzzer.spring.schedule;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class PowerScheduleService {
    public enum Mode { EXPLORE, EXPLOIT, FAST }

    public static class SeedStats {
        public int executions;
        public int coverageEvents;
        public int crashes;
        public String path;
        public String method;
    }

    private Mode mode = Mode.FAST;
    private final Map<String, SeedStats> stats = new ConcurrentHashMap<>();

    public void setMode(Mode mode) {
        this.mode = mode == null ? Mode.FAST : mode;
    }

    public Mode getMode() {
        return mode;
    }

    /** Fingerprint uses payload body only — path/method are stored but not part of the key. */
    public String fingerprint(SeedPayload seed) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(String.valueOf(seed.getBody()).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (Exception e) {
            return Integer.toHexString(seed.getBody().hashCode());
        }
    }

    public void record(SeedPayload seed, double coverageGain, boolean crash) {
        String id = fingerprint(seed);
        SeedStats st = stats.computeIfAbsent(id, k -> {
            SeedStats created = new SeedStats();
            created.path = seed.getPath();
            created.method = seed.getMethod();
            return created;
        });
        st.executions++;
        if (coverageGain > 0) {
            st.coverageEvents++;
        }
        if (crash) {
            st.crashes++;
        }
    }

    public int energy(SeedPayload seed) {
        SeedStats st = stats.get(fingerprint(seed));
        int base = 8;
        if (st == null) {
            return base;
        }
        double factor = switch (mode) {
            case EXPLORE -> 2.0 / Math.sqrt(Math.max(1, st.executions));
            case EXPLOIT -> 0.5 + Math.min(3.0, st.coverageEvents);
            default -> (1.5 / Math.sqrt(Math.max(1, st.executions))) * (1.0 + 0.25 * st.coverageEvents);
        };
        if (st.crashes > 0) {
            factor *= 1.35;
        }
        return Math.max(1, Math.min(64, (int) Math.round(base * factor)));
    }

    public Map<String, SeedStats> snapshot() {
        return Map.copyOf(stats);
    }
}
