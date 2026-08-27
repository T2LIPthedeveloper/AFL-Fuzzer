package com.aflfuzzer.spring.havoc;

import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.mutation.MutationEngine;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class HavocStage {
    private final MutationEngine mutationEngine;

    public HavocStage(MutationEngine mutationEngine) {
        this.mutationEngine = mutationEngine;
    }

    public SeedPayload havoc(SeedPayload seed, int stacked) {
        SeedPayload current = seed.copy();
        int rounds = Math.max(1, stacked);
        for (int i = 0; i < rounds; i++) {
            int burst = 1 + ThreadLocalRandom.current().nextInt(3);
            current = mutationEngine.mutate(current, burst);
            if (ThreadLocalRandom.current().nextDouble() < 0.2) {
                current.getBody().put("_havoc", ThreadLocalRandom.current().nextInt());
            }
        }
        return current;
    }

    public List<SeedPayload> havocBatch(SeedPayload seed, int variants, int stacked) {
        List<SeedPayload> out = new ArrayList<>();
        for (int i = 0; i < variants; i++) {
            out.add(havoc(seed, stacked));
        }
        return out;
    }
}
