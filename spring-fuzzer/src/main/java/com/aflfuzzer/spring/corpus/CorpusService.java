package com.aflfuzzer.spring.corpus;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class CorpusService {
    public static class Entry {
        public String id;
        public SeedPayload seed;
        public double weight = 1.0;
        public boolean favored;
        public int depth;
        public double coverageScore;
        public int crashCount;
        public int execCount;
        public String parentId;
    }

    private final Map<String, Entry> entries = new ConcurrentHashMap<>();
    private final int maxSize;

    public CorpusService() {
        this(4000);
    }

    public CorpusService(int maxSize) {
        this.maxSize = maxSize;
    }

    public String add(SeedPayload seed, double weight, double coverageScore, boolean favored, int depth, String parentId) {
        Entry entry = new Entry();
        entry.seed = seed.copy();
        entry.weight = weight;
        entry.coverageScore = coverageScore;
        entry.favored = favored;
        entry.depth = depth;
        entry.parentId = parentId;
        entry.id = fingerprint(seed);
        entries.put(entry.id, entry);
        evictIfNeeded();
        return entry.id;
    }

    public void markResult(String id, double coverageGain, boolean crash) {
        Entry entry = entries.get(id);
        if (entry == null) {
            return;
        }
        entry.execCount++;
        if (coverageGain > 0) {
            entry.favored = true;
            entry.weight += coverageGain;
            entry.coverageScore += coverageGain;
        } else {
            entry.weight *= 0.97;
        }
        if (crash) {
            entry.crashCount++;
            entry.favored = true;
        }
    }

    public Optional<SeedPayload> choose() {
        if (entries.isEmpty()) {
            return Optional.empty();
        }
        List<Entry> ranked = new ArrayList<>(entries.values());
        ranked.sort(Comparator.comparingDouble((Entry e) -> e.weight * (e.favored ? 1.4 : 1.0)).reversed());
        return Optional.of(ranked.get(0).seed.copy());
    }

    public Map<String, Object> summary() {
        long favored = entries.values().stream().filter(e -> e.favored).count();
        return Map.of(
                "size", entries.size(),
                "favored", favored,
                "maxSize", maxSize
        );
    }

    public List<Entry> snapshot() {
        return new ArrayList<>(entries.values());
    }

    private void evictIfNeeded() {
        while (entries.size() > maxSize) {
            Entry weakest = entries.values().stream()
                    .min(Comparator.comparingDouble(e -> e.weight))
                    .orElse(null);
            if (weakest == null) {
                return;
            }
            entries.remove(weakest.id);
        }
    }

    private String fingerprint(SeedPayload seed) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            String blob = seed.getMethod() + "|" + seed.getPath() + "|" + seed.getBody();
            return HexFormat.of().formatHex(md.digest(blob.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            return Integer.toHexString(seed.hashCode());
        }
    }
}
