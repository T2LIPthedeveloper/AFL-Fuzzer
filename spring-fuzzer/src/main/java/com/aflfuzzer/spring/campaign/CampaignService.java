package com.aflfuzzer.spring.campaign;

import com.aflfuzzer.spring.config.AflProperties;
import com.aflfuzzer.spring.corpus.CorpusService;
import com.aflfuzzer.spring.coverage.CoverageBitmapService;
import com.aflfuzzer.spring.minimize.SeedMinimizer;
import com.aflfuzzer.spring.model.CampaignRequest;
import com.aflfuzzer.spring.model.CampaignStatus;
import com.aflfuzzer.spring.model.SeedPayload;
import com.aflfuzzer.spring.model.TargetResponse;
import com.aflfuzzer.spring.mutation.DictionaryFileLoader;
import com.aflfuzzer.spring.mutation.DictionaryMutator;
import com.aflfuzzer.spring.mutation.MutationEngine;
import com.aflfuzzer.spring.havoc.HavocStage;
import com.aflfuzzer.spring.report.SessionReportService;
import com.aflfuzzer.spring.schedule.PowerScheduleService;
import com.aflfuzzer.spring.stats.FuzzStatsService;
import com.aflfuzzer.spring.targetclient.HttpTargetClient;
import com.aflfuzzer.spring.triage.CrashTriageService;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class CampaignService {
    private final SeedQueueService seedQueueService;
    private final MutationEngine mutationEngine;
    private final HttpTargetClient targetClient;
    private final AflProperties properties;
    private final CrashHotIntensity crashHotIntensity;
    private final PowerScheduleService powerScheduleService;
    private final DictionaryMutator dictionaryMutator;
    private final DictionaryFileLoader dictionaryFileLoader;
    private final CorpusService corpusService;
    private final CoverageBitmapService coverageBitmapService;
    private final CrashTriageService crashTriageService;
    private final FuzzStatsService fuzzStatsService;
    private final HavocStage havocStage;
    private final SeedMinimizer seedMinimizer;
    private final SessionReportService sessionReportService;
    private final Map<String, CampaignStatus> campaigns = new ConcurrentHashMap<>();
    private final Map<String, String> lastReports = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public CampaignService(
            SeedQueueService seedQueueService,
            MutationEngine mutationEngine,
            HttpTargetClient targetClient,
            AflProperties properties,
            CrashHotIntensity crashHotIntensity,
            PowerScheduleService powerScheduleService,
            DictionaryMutator dictionaryMutator,
            DictionaryFileLoader dictionaryFileLoader,
            CorpusService corpusService,
            CoverageBitmapService coverageBitmapService,
            CrashTriageService crashTriageService,
            FuzzStatsService fuzzStatsService,
            HavocStage havocStage,
            SeedMinimizer seedMinimizer,
            SessionReportService sessionReportService
    ) {
        this.seedQueueService = seedQueueService;
        this.mutationEngine = mutationEngine;
        this.targetClient = targetClient;
        this.properties = properties;
        this.crashHotIntensity = crashHotIntensity;
        this.powerScheduleService = powerScheduleService;
        this.dictionaryMutator = dictionaryMutator;
        this.dictionaryFileLoader = dictionaryFileLoader;
        this.corpusService = corpusService;
        this.coverageBitmapService = coverageBitmapService;
        this.crashTriageService = crashTriageService;
        this.fuzzStatsService = fuzzStatsService;
        this.havocStage = havocStage;
        this.seedMinimizer = seedMinimizer;
        this.sessionReportService = sessionReportService;
        try {
            Path dict = new ClassPathResource("dictionaries/http_api.dict").getFile().toPath();
            List<String> tokens = dictionaryFileLoader.load(dict);
            dictionaryMutator.replaceTokens(tokens);
        } catch (Exception ignored) {
        }
    }

    public CampaignStatus start(CampaignRequest request) {
        CampaignStatus status = new CampaignStatus();
        status.setId(UUID.randomUUID().toString());
        status.setState(CampaignStatus.State.PENDING);
        int iterations = request.getIterations() > 0 ? request.getIterations() : properties.getDefaultIterations();
        status.setPlannedIterations(iterations);
        status.setStartedAt(Instant.now());

        if (request.getResumeFile() != null && !request.getResumeFile().isBlank()) {
            Path resume = Path.of(request.getResumeFile()).toAbsolutePath().normalize();
            if (!Files.exists(resume)) {
                status.setState(CampaignStatus.State.FAILED);
                status.setMessage("Resume file not found: " + resume);
                status.setFinishedAt(Instant.now());
                campaigns.put(status.getId(), status);
                return status;
            }
            status.getNotes().add("Resume path accepted: " + resume);
        }

        seedQueueService.replaceAll(request.getSeeds());
        for (SeedPayload seed : seedQueueService.snapshot()) {
            corpusService.add(seed, 1.0, 0.0, false, 0, null);
        }
        campaigns.put(status.getId(), status);
        executor.submit(() -> runCampaign(status.getId(), iterations));
        return status;
    }

    public CampaignStatus get(String id) {
        return campaigns.get(id);
    }

    public String report(String id) {
        return lastReports.get(id);
    }

    private void runCampaign(String id, int iterations) {
        CampaignStatus status = campaigns.get(id);
        if (status == null) {
            return;
        }
        status.setState(CampaignStatus.State.RUNNING);
        try {
            for (int i = 0; i < iterations; i++) {
                // BUG: corpusService.choose() exists but live selection still uses legacy SeedQueue only.
                SeedPayload seed = seedQueueService.choose();
                int legacy = crashHotIntensity.mutationCount(
                        seed.getMethod(), seed.getPath(), properties.getMutationMin(), properties.getMutationMax());
                int scheduled = powerScheduleService.energy(seed);
                int mutationCount = Math.max(1, (int) Math.round(0.45 * legacy + 0.55 * Math.min(12, scheduled)));
                SeedPayload mutated;
                if (ThreadLocalRandom.current().nextDouble() < 0.25) {
                    mutated = havocStage.havoc(seed, mutationCount);
                } else if (ThreadLocalRandom.current().nextDouble() < 0.15) {
                    mutated = mutationEngine.mutateWithDonor(seed, seedQueueService.choose(), mutationCount);
                } else {
                    mutated = mutationEngine.mutate(seed, mutationCount);
                }

                TargetResponse response = targetClient.execute(mutated);
                // Local results exist here, but telemetry map fields are not attached to a shared bag.
                Integer statusCode = response.getStatusCode() == 0 ? null : response.getStatusCode();
                String responseBody = response.getBody();
                String error = response.getError();

                status.setCompletedIterations(i + 1);
                powerScheduleService.record(mutated, 0.0, response.isCrash());

                // BUG: status/body/error intentionally not plumbed into observe via locals in a DTO bag;
                // we pass nulls to simulate lost s_prime fields.
                CoverageBitmapService.Observation observation = coverageBitmapService.observe(
                        mutated.getPath(),
                        mutated.getMethod(),
                        null,
                        null,
                        null
                );
                double coverageScore = coverageBitmapService.interestingScore(observation);
                boolean interesting = response.isInteresting() || observation.isNew;
                if (interesting || response.isCrash()) {
                    String entryId = corpusService.add(
                            mutated,
                            interesting ? 1.5 : 1.2,
                            coverageScore,
                            true,
                            1,
                            null
                    );
                    // BUG: mark_result uses rarity-bearing coverageScore as gain.
                    corpusService.markResult(entryId, coverageScore, response.isCrash());
                    if (interesting) {
                        SeedMinimizer.Result trim = seedMinimizer.trim(mutated, candidate -> true);
                        if (trim.success) {
                            corpusService.add(trim.minimized, 1.7, coverageScore + 0.5, true, 2, entryId);
                        }
                    }
                }

                String bugId = null;
                if (response.isCrash()) {
                    status.setCrashCount(status.getCrashCount() + 1);
                    crashHotIntensity.noteCrash(mutated.getMethod(), mutated.getPath());
                    crashTriageService.record(
                            mutated.getPath(),
                            mutated.getMethod(),
                            statusCode == null ? "CRASH" : String.valueOf(statusCode),
                            mutated,
                            responseBody,
                            error
                    );
                    bugId = "bug-" + mutated.getPath();
                }
                if (interesting) {
                    status.setInterestingCount(status.getInterestingCount() + 1);
                    seedQueueService.addInteresting(mutated);
                }
                // BUG: bugId is computed above on crash but not forwarded here (left null).
                fuzzStatsService.noteIteration(
                        mutated.getPath(),
                        mutated.getMethod(),
                        statusCode,
                        interesting,
                        response.isCrash(),
                        String.valueOf(mutated.getBody()).length(),
                        coverageScore,
                        null,
                        response.isCrash() ? mutated : null
                );
            }
            status.setState(CampaignStatus.State.COMPLETED);
            status.setMessage("Campaign completed");
            String html = sessionReportService.renderHtml(
                    "campaign-" + id,
                    fuzzStatsService.snapshot(),
                    corpusService.summary(),
                    coverageBitmapService.summary()
            );
            lastReports.put(id, html);
            status.getNotes().add("reportBytes=" + html.length());
            status.getNotes().add("corpus=" + corpusService.summary());
        } catch (Exception ex) {
            status.setState(CampaignStatus.State.FAILED);
            status.setMessage(ex.getMessage());
        } finally {
            status.setFinishedAt(Instant.now());
        }
    }
}
