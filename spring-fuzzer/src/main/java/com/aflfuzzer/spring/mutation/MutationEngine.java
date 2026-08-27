package com.aflfuzzer.spring.mutation;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class MutationEngine {
    private static final String[] SPECIAL = {"'", "\"", "<", ">", "&", ";", "|", "`", "$", "\0"};
    private final Random random = ThreadLocalRandom.current();

    public SeedPayload mutate(SeedPayload seed, int count) {
        SeedPayload current = seed.copy();
        int n = Math.max(1, count);
        for (int i = 0; i < n; i++) {
            current = applyOne(current);
        }
        return current;
    }

    public List<SeedPayload> mutateMany(SeedPayload seed, int count, int variants) {
        List<SeedPayload> out = new ArrayList<>();
        for (int i = 0; i < variants; i++) {
            out.add(mutate(seed, count));
        }
        return out;
    }

    private SeedPayload applyOne(SeedPayload seed) {
        String strategy = pick(List.of("bitflip", "special", "number", "delete_key"));
        SeedPayload next = seed.copy();
        Map<String, Object> body = next.getBody();
        if (body.isEmpty()) {
            body.put("fuzz", random.nextInt(1000));
            return next;
        }
        List<String> keys = new ArrayList<>(body.keySet());
        String key = keys.get(random.nextInt(keys.size()));
        Object value = body.get(key);
        switch (strategy) {
            case "special" -> {
                if (value instanceof String s) {
                    body.put(key, s + SPECIAL[random.nextInt(SPECIAL.length)]);
                } else {
                    body.put(key, SPECIAL[random.nextInt(SPECIAL.length)]);
                }
            }
            case "number" -> body.put(key, interestingNumber());
            case "delete_key" -> {
                if (keys.size() > 1) {
                    body.remove(key);
                }
            }
            default -> {
                if (value instanceof String s && !s.isEmpty()) {
                    char[] chars = s.toCharArray();
                    int idx = random.nextInt(chars.length);
                    chars[idx] = (char) (chars[idx] ^ (1 << random.nextInt(7)));
                    body.put(key, new String(chars));
                } else {
                    body.put(key, random.nextInt());
                }
            }
        }
        return next;
    }

    private int interestingNumber() {
        int[] values = {0, -1, 1, 255, 256, 0x7F, 0xFF, 0x7FFF};
        return values[random.nextInt(values.length)];
    }

    private <T> T pick(List<T> items) {
        return items.get(random.nextInt(items.size()));
    }
}
