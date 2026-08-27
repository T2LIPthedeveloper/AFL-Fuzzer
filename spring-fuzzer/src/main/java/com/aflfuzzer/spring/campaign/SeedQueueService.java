package com.aflfuzzer.spring.campaign;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class SeedQueueService {
    private final CopyOnWriteArrayList<SeedPayload> seeds = new CopyOnWriteArrayList<>();

    public void replaceAll(List<SeedPayload> incoming) {
        seeds.clear();
        if (incoming == null || incoming.isEmpty()) {
            seeds.add(defaultSeed());
        } else {
            seeds.addAll(incoming);
        }
    }

    public SeedPayload choose() {
        if (seeds.isEmpty()) {
            seeds.add(defaultSeed());
        }
        int idx = ThreadLocalRandom.current().nextInt(seeds.size());
        return seeds.get(idx).copy();
    }

    public void addInteresting(SeedPayload seed) {
        seeds.add(seed.copy());
    }

    public List<SeedPayload> snapshot() {
        return new ArrayList<>(seeds);
    }

    public int size() {
        return seeds.size();
    }

    private SeedPayload defaultSeed() {
        SeedPayload seed = new SeedPayload();
        seed.setPath("/api/ping");
        seed.setMethod("GET");
        seed.getBody().put("probe", true);
        return seed;
    }
}
