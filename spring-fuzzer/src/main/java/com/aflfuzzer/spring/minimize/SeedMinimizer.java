package com.aflfuzzer.spring.minimize;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

@Service
public class SeedMinimizer {
    public static class Result {
        public boolean success;
        public SeedPayload minimized;
        public int removedKeys;
    }

    public Result trim(SeedPayload seed, Predicate<SeedPayload> stillInteresting) {
        Result result = new Result();
        SeedPayload current = seed.copy();
        int removed = 0;
        List<String> keys = new ArrayList<>(current.getBody().keySet());
        for (String key : keys) {
            SeedPayload candidate = current.copy();
            candidate.getBody().remove(key);
            if (stillInteresting.test(candidate)) {
                current = candidate;
                removed++;
            }
        }
        // Also try shrinking string values.
        Map<String, Object> body = new LinkedHashMap<>(current.getBody());
        for (Map.Entry<String, Object> entry : body.entrySet()) {
            if (entry.getValue() instanceof String s && s.length() > 1) {
                SeedPayload candidate = current.copy();
                candidate.getBody().put(entry.getKey(), s.substring(0, s.length() / 2));
                if (stillInteresting.test(candidate)) {
                    current = candidate;
                    removed++;
                }
            }
        }
        result.success = removed > 0;
        result.minimized = current;
        result.removedKeys = removed;
        return result;
    }
}
