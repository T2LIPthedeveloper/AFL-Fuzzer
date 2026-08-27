package com.aflfuzzer.spring.mutation;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

@Component
public class DictionaryMutator {
    private final List<String> tokens = new ArrayList<>(List.of(
            "../", "%00", "{{7*7}}", "' OR 1=1--", "null", "admin", "Bearer ", "application/json"
    ));

    public SeedPayload insert(SeedPayload seed) {
        SeedPayload next = seed.copy();
        Map<String, Object> body = next.getBody();
        String token = tokens.get(ThreadLocalRandom.current().nextInt(tokens.size()));
        if (body.isEmpty()) {
            body.put("dict", token);
            return next;
        }
        List<String> keys = new ArrayList<>(body.keySet());
        String key = keys.get(ThreadLocalRandom.current().nextInt(keys.size()));
        Object value = body.get(key);
        if (value instanceof String s) {
            int pos = ThreadLocalRandom.current().nextInt(0, s.length() + 1);
            body.put(key, s.substring(0, pos) + token + s.substring(pos));
        } else {
            body.put(key, token);
        }
        return next;
    }

    public void replaceTokens(List<String> incoming) {
        if (incoming != null && !incoming.isEmpty()) {
            tokens.clear();
            tokens.addAll(incoming);
        }
    }
}
