package com.aflfuzzer.spring.triage;

import com.aflfuzzer.spring.model.SeedPayload;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class CrashTriageService {
    public static class CrashRecord {
        public String signature;
        public String path;
        public String method;
        public String status;
        public int count;
        public SeedPayload sample;
        public String responseText;
        public String errorText;
    }

    private final Map<String, CrashRecord> records = new ConcurrentHashMap<>();

    public CrashRecord record(
            String path,
            String method,
            String status,
            SeedPayload seed,
            String responseText,
            String errorText
    ) {
        String signature = signature(path, method, status, responseText, errorText);
        CrashRecord existing = records.get(signature);
        if (existing == null) {
            CrashRecord created = new CrashRecord();
            created.signature = signature;
            created.path = path;
            created.method = method;
            created.status = status;
            created.count = 1;
            created.sample = seed == null ? null : seed.copy();
            created.responseText = truncate(responseText);
            created.errorText = truncate(errorText);
            records.put(signature, created);
            return created;
        }
        existing.count++;
        return existing;
    }

    public List<CrashRecord> snapshot() {
        return new ArrayList<>(records.values());
    }

    public Map<String, Object> summary() {
        return Map.of("uniqueCrashes", records.size());
    }

    private String signature(String path, String method, String status, String responseText, String errorText) {
        String blob = method + "|" + path + "|" + status + "|" + truncate(responseText) + "|" + truncate(errorText);
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            return HexFormat.of().formatHex(md.digest(blob.getBytes(StandardCharsets.UTF_8))).substring(0, 16);
        } catch (Exception e) {
            return Integer.toHexString(blob.hashCode());
        }
    }

    private String truncate(String text) {
        if (text == null) {
            return "";
        }
        return text.length() <= 200 ? text : text.substring(0, 200);
    }
}
