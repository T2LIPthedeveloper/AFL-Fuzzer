package com.aflfuzzer.spring.report;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.StringJoiner;

@Service
public class SessionReportService {
    public String renderHtml(String title, Map<String, Object> fuzzStats, Map<String, Object> corpus, Map<String, Object> coverage) {
        StringJoiner html = new StringJoiner("\n");
        html.add("<!DOCTYPE html>");
        html.add("<html><head><meta charset=\\\"utf-8\\\"/><title>" + esc(title) + "</title></head><body>");
        html.add("<h1>" + esc(title) + "</h1>");
        html.add("<p>Generated at " + Instant.now() + "</p>");
        html.add("<h2>Fuzz stats</h2>");
        html.add("<pre>" + esc(String.valueOf(fuzzStats)) + "</pre>");
        html.add("<h2>Corpus</h2>");
        html.add("<pre>" + esc(String.valueOf(corpus)) + "</pre>");
        html.add("<h2>Coverage</h2>");
        html.add("<pre>" + esc(String.valueOf(coverage)) + "</pre>");
        html.add("</body></html>");
        return html.toString();
    }

    private String esc(String value) {
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
