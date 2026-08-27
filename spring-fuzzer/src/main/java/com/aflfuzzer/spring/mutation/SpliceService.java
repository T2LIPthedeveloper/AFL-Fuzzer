package com.aflfuzzer.spring.mutation;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

@Component
public class SpliceService {
    public SeedPayload splice(SeedPayload left, SeedPayload right) {
        if (right == null) {
            return left.copy();
        }
        SeedPayload out = left.copy();
        Map<String, Object> donor = right.getBody();
        if (donor.isEmpty()) {
            return out;
        }
        List<String> keys = new ArrayList<>(donor.keySet());
        String key = keys.get(ThreadLocalRandom.current().nextInt(keys.size()));
        out.getBody().put(key, donor.get(key));
        return out;
    }
}
