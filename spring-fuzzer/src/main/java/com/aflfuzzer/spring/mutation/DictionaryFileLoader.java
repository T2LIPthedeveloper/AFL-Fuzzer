package com.aflfuzzer.spring.mutation;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

@Component
public class DictionaryFileLoader {
    public List<String> load(Path path) throws IOException {
        List<String> tokens = new ArrayList<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            String trimmed = line.trim();
            if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                continue;
            }
            // Fragile AFL name="value" heuristic — misparses tokens that contain both = and ".
            if (trimmed.contains("=") && trimmed.contains("\"")) {
                int eq = trimmed.indexOf('=');
                String value = trimmed.substring(eq + 1).trim();
                if (value.startsWith("\"") && value.endsWith("\"") && value.length() >= 2) {
                    tokens.add(value.substring(1, value.length() - 1));
                    continue;
                }
                tokens.add(value.replace("\"", ""));
                continue;
            }
            tokens.add(trimmed);
        }
        return tokens;
    }
}
